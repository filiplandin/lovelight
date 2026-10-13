"""Acceptance for the TRUST layer: hash-chained audit log, audit API, append-only corrections. No network.

Contract:
- audit.append(actor, action, entity, entity_id, data=None, input_sha256=None) -> AuditEvent
- audit.events(entity_id=None) -> list[AuditEvent]   (entity_id filter also matches data.document_id / data.document_ids)
- audit.verify(events=None) -> {"ok": bool, "events": int, "head": str, "first_bad_seq": int | None}
- hash = sha256(prev_hash + canonical_json(event without "hash")); genesis prev_hash = "0" * 64
- SQLite table `audit(seq INTEGER PRIMARY KEY, data TEXT NOT NULL)`, UPDATE/DELETE blocked by triggers,
  never cleared by store.reset() / POST /api/demo/reset.
"""

import asyncio
import hashlib
import json
import shutil
import sqlite3
import time
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from lovelight import extract
from lovelight.models import DocType, Extraction, Source

GENESIS = "0" * 64
SL_RECEIPT = "kvitto_sl_30dagar_sep.pdf"  # gold receipt; bank feed has its card payment (SL ACCESS, 1060.00)


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@pytest.fixture
def env(tmp_path, monkeypatch):
    from lovelight import pipeline, server  # import first: server load_dotenv() would refill env vars

    db = tmp_path / "audit.db"
    monkeypatch.setenv("LOVELIGHT_DB", str(db))
    for var in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "ANTHROPIC_API_KEY", "SENDER_ALLOWLIST"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(pipeline, "INCOMING", tmp_path / "incoming")
    monkeypatch.setattr(server, "REPLAY_DELAY_S", 0)
    with TestClient(server.app) as c:
        yield {"client": c, "db": db, "tmp": tmp_path}


def _receipt(vendor: str, account: str, net: str = "800.00", activity: str | None = "office_supplies") -> Extraction:
    n = Decimal(net)
    return Extraction(
        doc_type=DocType.RECEIPT, vendor=vendor, date=date(2026, 10, 1), net=n, vat_rate=Decimal("0.25"),
        vat=n * Decimal("0.25"), gross=n * Decimal("1.25"), suggested_account=account, confidence=0.99,
        activity=activity,
    )


def _upload(client, name: str, extraction: Extraction, monkeypatch) -> dict:
    monkeypatch.setattr(extract, "extract", lambda path, email_body=None: (extraction, "test-model"))
    client.post("/api/upload", files=[("files", (name, f"%PDF-1.4 {name}".encode(), "application/pdf"))])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        docs = [d for d in client.get("/api/state").json()["documents"] if d["filename"].endswith(name)]
        if docs and docs[0]["status"] in {"posted", "matched", "needs_review", "quarantined"}:
            return docs[0]
        time.sleep(0.03)
    raise AssertionError(f"{name} not processed")


def _ingest_gold(env, filename: str):
    from lovelight import pipeline

    path = env["tmp"] / filename
    shutil.copy(pipeline.INBOX / filename, path)
    return asyncio.run(pipeline.ingest(path, Source.UPLOAD, gold=True))


def _actions(events: list[dict]) -> list[str]:
    return [e["action"] for e in events]


def _is_subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(any(h == n for h in it) for n in needle)


# ---------- hash chain ----------


def test_append_builds_gap_free_hash_chain_with_pinned_formula(env):
    from lovelight import audit

    for i in range(3):
        audit.append("user:maja", "note.added", "document", f"doc_{i}", {"amount": "12.50", "i": i})
    events = audit.events()
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert events[0].prev_hash == GENESIS
    for prev, e in zip([None, *events], events, strict=False):
        if prev is not None:
            assert e.prev_hash == prev.hash
        body = e.model_dump(mode="json", exclude={"hash"})
        assert e.hash == hashlib.sha256(e.prev_hash.encode() + canonical(body)).hexdigest(), e.seq
    tail = events[-1]
    assert (tail.actor, tail.action, tail.entity_id, tail.data["i"]) == ("user:maja", "note.added", "doc_2", 2)


def test_verify_detects_tampering_of_any_past_event(env):
    from lovelight import audit

    for i in range(4):
        audit.append("system", "note.added", "document", f"doc_{i}", {"i": i})
    events = audit.events()
    assert audit.verify(events)["ok"] is True
    for k in range(len(events)):
        forged = [e.model_copy(deep=True) for e in events]
        forged[k].data = {**forged[k].data, "forged": True}
        result = audit.verify(forged)
        assert result["ok"] is False and result["first_bad_seq"] == forged[k].seq, k
    dropped = events[:1] + events[2:]
    assert audit.verify(dropped)["ok"] is False


def test_audit_table_is_append_only_and_tampering_shows_in_api(env):
    from lovelight import audit

    client, db = env["client"], env["db"]
    for i in range(3):
        audit.append("system", "note.added", "document", f"doc_{i}", {"i": i})
    ok = client.get("/api/audit/verify").json()
    events = audit.events()
    assert ok == {"ok": True, "events": len(events), "head": events[-1].hash, "first_bad_seq": None,
                  "chain_ok": True, "ledger_ok": True, "first_bad_voucher": None}

    victim = events[-2]
    con = sqlite3.connect(db)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            con.execute("UPDATE audit SET data = data WHERE seq = ?", (victim.seq,))
        with pytest.raises(sqlite3.DatabaseError):
            con.execute("DELETE FROM audit WHERE seq = ?", (victim.seq,))
        # An attacker with file access can drop the triggers; the hash chain must still catch the edit.
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'audit'"):
            con.execute(f'DROP TRIGGER "{name}"')
        forged = victim.model_dump(mode="json")
        forged["data"]["i"] = 999
        con.execute("UPDATE audit SET data = ? WHERE seq = ?", (json.dumps(forged), victim.seq))
        con.commit()
    finally:
        con.close()
    bad = client.get("/api/audit/verify").json()
    assert bad["ok"] is False and bad["first_bad_seq"] == victim.seq


def test_editing_a_posted_voucher_in_the_database_is_detected(env):
    client, db = env["client"], env["db"]
    assert client.get("/api/audit/verify").json()["ledger_ok"] is True
    con = sqlite3.connect(db)
    try:
        vid, raw = next(
            (i, d) for i, d in con.execute("SELECT id, data FROM vouchers") if json.loads(d)["status"] == "posted"
        )
        v = json.loads(raw)
        v["lines"][0]["debit"] = "12.00" if v["lines"][0]["debit"] not in ("0", "0.00") else v["lines"][0]["debit"]
        v["lines"][0]["credit"] = "12.00" if v["lines"][0]["credit"] not in ("0", "0.00") else v["lines"][0]["credit"]
        con.execute("UPDATE vouchers SET data = ? WHERE id = ?", (json.dumps(v), vid))
        con.commit()
    finally:
        con.close()
    bad = client.get("/api/audit/verify").json()
    assert bad["ok"] is False and bad["ledger_ok"] is False and bad["first_bad_voucher"] == vid
    assert client.get("/api/export/sie4").status_code == 409


def test_demo_reset_never_clears_the_audit_log(env):
    from lovelight import audit

    client = env["client"]
    audit.append("system", "note.added", "document", "doc_x")
    before = audit.verify()["events"]
    client.post("/api/demo/reset")
    after = client.get("/api/audit/verify").json()
    assert after["ok"] is True and after["events"] >= before
    assert any(e.entity_id == "doc_x" for e in audit.events())


# ---------- ingest emits ordered, evidence-carrying events ----------


def test_ingest_emits_received_extracted_posted_approved_in_order(env):
    from lovelight import audit

    doc = _ingest_gold(env, SL_RECEIPT)
    events = env["client"].get("/api/audit", params={"entity_id": doc.id}).json()
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs)
    actions = _actions(events)
    assert _is_subsequence(["doc.received", "doc.extracted", "voucher.posted", "match.approved"], actions), actions

    extracted = next(e for e in events if e["action"] == "doc.extracted")
    assert extracted["actor"].startswith("model:"), extracted["actor"]
    assert extracted["input_sha256"] == doc.sha256
    data = extracted["data"]
    assert data["model"] == "gold-cache"
    assert data["prompt_version"] == extract.PROMPT_VERSION
    assert data["prompt_sha256"] == extract.PROMPT_SHA256
    assert data["input_sha256"] == doc.sha256
    stored = env["client"].get("/api/state").json()
    ext = next(d for d in stored["documents"] if d["id"] == doc.id)["extraction"]
    ext.pop("confidence_detail", None)
    assert data["output_sha256"] == hashlib.sha256(canonical(ext)).hexdigest()

    approved = next(e for e in events if e["action"] == "match.approved")
    assert doc.id in approved["data"]["document_ids"]
    assert audit.verify()["ok"] is True


def test_quarantined_upload_logs_quarantine_and_no_posting(env, monkeypatch):
    evil = _receipt("Evil AB", "6540").model_copy(update={"injection_suspected": True})
    doc = _upload(env["client"], "evil.pdf", evil, monkeypatch)
    actions = _actions(env["client"].get("/api/audit", params={"entity_id": doc["id"]}).json())
    assert _is_subsequence(["doc.received", "doc.extracted", "doc.quarantined"], actions), actions
    assert "voucher.posted" not in actions


def test_kb_hits_and_misses_are_audited(env, monkeypatch):
    hit = _ingest_gold(env, SL_RECEIPT)
    miss = _upload(env["client"], "ateljé.pdf", _receipt("Ateljé Nordljus AB", "6110"), monkeypatch)
    client = env["client"]
    hit_events = client.get("/api/audit", params={"entity_id": hit.id}).json()
    miss_events = client.get("/api/audit", params={"entity_id": miss["id"]}).json()
    assert any(e["action"] == "kb.hit" and e["data"].get("entry_id") for e in hit_events)
    assert any(e["action"] == "kb.miss" for e in miss_events)
    stats = client.get("/api/knowledge").json()["stats"]
    assert stats["hits"] >= 1 and stats["misses"] >= 1


# ---------- corrections: reversal + corrected voucher, never an edit ----------


def _vouchers_for(state: dict, doc_id: str) -> list[dict]:
    return [v for v in state["vouchers"] if v["document_id"] == doc_id and not v.get("bank_tx_id")]


def _lines(v: dict) -> list[tuple]:
    return [(ln["account"], Decimal(str(ln["debit"])), Decimal(str(ln["credit"]))) for ln in v["lines"]]


def _assert_balanced(state: dict) -> None:
    for v in state["vouchers"]:
        assert sum(Decimal(str(ln["debit"])) for ln in v["lines"]) == sum(Decimal(str(ln["credit"])) for ln in v["lines"])
    bs = state["reports"]["balance_sheet"]
    assert sum(Decimal(str(x)) for x in bs["assets"].values()) == sum(
        Decimal(str(x)) for x in bs["liabilities_equity"].values()
    )


def test_correction_reverses_and_reposts_with_user_audit_event(env, monkeypatch):
    from lovelight import audit

    client = env["client"]
    doc = _upload(client, "monitor.pdf", _receipt("Ateljé Nordljus AB", "6110"), monkeypatch)
    before = client.get("/api/state").json()
    [original] = _vouchers_for(before, doc["id"])
    assert original["status"] == "posted" and any(a == "6110" for a, _, _ in _lines(original))
    exp_before = {k: Decimal(str(v)) for k, v in before["reports"]["pnl"]["expenses"].items()}

    r = client.post(
        f"/api/documents/{doc['id']}/correct",
        json={"account": "5410", "reason": "A monitor is equipment, not office supplies", "user": "maja"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"reversal", "corrected", "correction"}

    after = client.get("/api/state").json()
    by_id = {v["id"]: v for v in after["vouchers"]}
    assert _lines(by_id[original["id"]]) == _lines(original), "original voucher lines must never change"
    assert by_id[original["id"]]["status"] == "reversed"
    reversal, corrected = by_id[body["reversal"]["id"]], by_id[body["corrected"]["id"]]
    assert reversal["reverses_id"] == original["id"] and reversal["status"] == "posted"
    assert sorted(_lines(reversal)) == sorted((a, c, d) for a, d, c in _lines(original))
    assert corrected["status"] == "posted" and ("5410", Decimal("800.00"), Decimal("0")) in _lines(corrected)
    assert corrected["number"] > reversal["number"] > original["number"]

    exp_after = {k: Decimal(str(v)) for k, v in after["reports"]["pnl"]["expenses"].items()}
    assert exp_after.get("6110", Decimal(0)) == exp_before.get("6110", Decimal(0)) - Decimal("800.00")
    assert exp_after.get("5410", Decimal(0)) == exp_before.get("5410", Decimal(0)) + Decimal("800.00")
    _assert_balanced(after)

    events = client.get("/api/audit", params={"entity_id": doc["id"]}).json()
    ev = next(e for e in events if e["action"] == "voucher.corrected")
    assert ev["actor"] == "user:maja"
    assert ev["data"]["before"]["account"] == "6110" and ev["data"]["after"]["account"] == "5410"
    assert ev["data"]["reason"] == "A monitor is equipment, not office supplies"
    assert {ev["data"]["reversal_voucher_id"], ev["data"]["corrected_voucher_id"]} == {reversal["id"], corrected["id"]}
    assert audit.verify()["ok"] is True

    proposals = client.get("/api/knowledge").json()["proposals"]
    assert any(p["vendor"] == "Ateljé Nordljus AB" and p["account"] == "5410" for p in proposals), proposals


def test_correction_is_remembered_for_the_next_document_from_that_vendor(env, monkeypatch):
    client = env["client"]
    first = _upload(client, "a1.pdf", _receipt("Ateljé Nordljus AB", "6110"), monkeypatch)
    client.post(f"/api/documents/{first['id']}/correct", json={"account": "5410", "reason": "equipment", "user": "maja"})

    second = _upload(client, "a2.pdf", _receipt("Atelje Nordljus", "6110", net="400.00"), monkeypatch)
    cls = second["classification"]
    assert cls["account"] == "5410" and cls["source"] == "correction"
    assert f"learned from correction on {date.today().isoformat()}" in cls["rationale"]
    [v] = _vouchers_for(client.get("/api/state").json(), second["id"])
    assert any(a == "5410" for a, _, _ in _lines(v))


def test_correction_rejects_bad_input(env, monkeypatch):
    client = env["client"]
    doc = _upload(client, "x.pdf", _receipt("Ateljé Nordljus AB", "6110"), monkeypatch)
    assert client.post("/api/documents/nope/correct", json={"account": "5410", "reason": "x"}).status_code == 404
    assert client.post(f"/api/documents/{doc['id']}/correct", json={"account": "5410", "reason": " "}).status_code == 422
    assert client.post(f"/api/documents/{doc['id']}/correct", json={"account": "9999", "reason": "x"}).status_code == 422
