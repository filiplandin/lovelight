"""Pitch-demo acceptance: deterministic inbox replay -> match -> books/SIE4 -> Trust Center.

Replays data/generated/inbox twice (gold extraction, no network) against a tmp DB and
asserts the invariants the 3-minute demo relies on.
"""

import asyncio
import csv
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from lovelight import pipeline

PLANTED_DOC_KINDS = {"injection", "iban_change", "duplicate", "vat_mismatch", "missing_receipt"}
INBOX_DOCS = len(json.loads((pipeline.GENERATED / "gold.json").read_text()))


def _replay(server) -> None:
    asyncio.run(server._replay())


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from lovelight import server  # import first: server load_dotenv() would refill env vars

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LOVELIGHT_DB", str(tmp_path_factory.mktemp("acc") / "acceptance.db"))
        for var in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "ANTHROPIC_API_KEY", "SENDER_ALLOWLIST"):
            mp.delenv(var, raising=False)
        mp.setattr(server, "REPLAY_DELAY_S", 0)
        with TestClient(server.app) as client:
            _replay(server)
            first = client.get("/api/state").json()
            _replay(server)
            state = client.get("/api/state").json()
            sie = client.get("/api/export/sie4")
            yield {"first": first, "state": state, "sie": sie, "client": client}


def _inbox_docs(state):
    return [d for d in state["documents"] if d["source"] != "light_csv"]


def _non_light_anomalies(state):
    return [a for a in state["anomalies"] if not (a.get("document_id") or "").startswith("light-")]


def test_replay_ingests_all_inbox_docs(demo):
    assert len(_inbox_docs(demo["state"])) == INBOX_DOCS


def test_replay_is_idempotent(demo):
    assert len(demo["first"]["documents"]) == len(demo["state"]["documents"])
    assert len(_inbox_docs(demo["first"])) == INBOX_DOCS
    assert len(demo["first"]["anomalies"]) == len(demo["state"]["anomalies"])
    assert len(demo["first"]["vouchers"]) == len(demo["state"]["vouchers"])


def test_exactly_planted_doc_anomalies(demo):
    kinds = [a["kind"] for a in _non_light_anomalies(demo["state"])]
    assert set(kinds) == PLANTED_DOC_KINDS, kinds
    assert len(kinds) == len(PLANTED_DOC_KINDS), kinds


def test_quarantined_doc_not_posted_and_shows_injection(demo):
    state = demo["state"]
    quarantined = [d for d in state["documents"] if d["status"] == "quarantined"]
    assert len(quarantined) == 1
    doc = quarantined[0]
    assert "ignore previous instructions" in (doc["note"] or "").lower()
    assert not any(v["document_id"] == doc["id"] and v["status"] == "posted" for v in state["vouchers"])


def test_every_voucher_balanced(demo):
    for v in demo["state"]["vouchers"]:
        debit = sum(Decimal(str(line["debit"])) for line in v["lines"])
        credit = sum(Decimal(str(line["credit"])) for line in v["lines"])
        assert debit == credit, v["id"]


def test_balance_sheet_balances(demo):
    bs = demo["state"]["reports"]["balance_sheet"]
    assets = sum(Decimal(str(x)) for x in bs["assets"].values())
    le = sum(Decimal(str(x)) for x in bs["liabilities_equity"].values())
    assert assets == le, (assets, le)


def test_planted_light_ar_rows_flagged_and_held(demo):
    with pipeline.LIGHT_CSV.open(newline="", encoding="utf-8") as f:
        planted = {r["Invoice Number"] for r in csv.DictReader(f) if r["Invoice Number"].startswith("INV-")}
    assert len(planted) >= 9
    state = demo["state"]
    flagged = {a["invoice_number"] for a in state["anomalies"] if a.get("invoice_number") in planted}
    assert flagged == planted, sorted(planted - flagged)

    docs_by_inv = {
        d["extraction"]["invoice_number"]: d
        for d in state["documents"]
        if d["source"] == "light_csv" and d.get("extraction")
    }
    posted_doc_ids = {v["document_id"] for v in state["vouchers"] if v["status"] == "posted"}
    posted_planted = sorted(inv for inv in planted if inv in docs_by_inv and docs_by_inv[inv]["id"] in posted_doc_ids)
    assert not posted_planted, posted_planted


def test_sie4_export(demo):
    r = demo["sie"]
    assert r.status_code == 200
    text = r.content.decode("cp437")
    assert text.startswith("#FLAGGA")
    assert "#VER" in text


def test_bt014_matched_to_three_docs(demo):
    matches = [m for m in demo["state"]["matches"] if m["bank_tx_id"] == "BT014"]
    assert len(matches) == 1
    assert len(matches[0]["document_ids"]) == 3


def _drain(q) -> list[str]:
    types = []
    while not q.empty():
        types.append(q.get_nowait()["type"])
    return types


def _assert_books_balance(state) -> None:
    bs = state["reports"]["balance_sheet"]
    assets = sum(Decimal(str(x)) for x in bs["assets"].values())
    le = sum(Decimal(str(x)) for x in bs["liabilities_equity"].values())
    assert assets == le, (assets, le)


def test_approve_all_round_trip(demo):
    client = demo["client"]
    before = client.get("/api/state").json()
    pending = [
        m for m in before["matches"]
        if not m["approved"] and m["confidence"] >= pipeline.AUTO_APPROVE_MATCH and not m["blocked_by"]
    ]
    q = pipeline.subscribe()
    try:
        r = client.post("/api/matches/approve-all")
        events = _drain(q)
    finally:
        pipeline.unsubscribe(q)
    assert r.status_code == 200
    assert set(r.json()["approved"]) == {m["id"] for m in pending}
    if pending:
        assert "match.approved" in events, events
    after = client.get("/api/state").json()
    high = [m for m in after["matches"] if m["confidence"] >= pipeline.AUTO_APPROVE_MATCH and not m["blocked_by"]]
    assert high and all(m["approved"] for m in high)
    # a payment never posts against a document that is not itself in the books
    blocked = [m for m in after["matches"] if m["blocked_by"]]
    assert not any(m["approved"] for m in blocked)
    in_review = {d["id"] for d in after["documents"] if d["status"] in ("needs_review", "quarantined")}
    assert not any(v["bank_tx_id"] and v["document_id"] in in_review for v in after["vouchers"])
    _assert_books_balance(after)
    payment_doc_ids = {v["document_id"] for v in after["vouchers"] if v["status"] == "posted"}
    assert any(d in payment_doc_ids for m in high for d in m["document_ids"])


def test_approve_single_low_confidence_match(demo):
    client = demo["client"]
    before = client.get("/api/state").json()
    low = [m for m in before["matches"] if not m["approved"] and m["confidence"] < pipeline.AUTO_APPROVE_MATCH]
    assert low, "demo data needs at least one sub-0.95 match to review"
    m = low[0]
    n_ver_before = client.get("/api/export/sie4").content.decode("cp437").count("#VER")
    q = pipeline.subscribe()
    try:
        r = client.post(f"/api/matches/{m['id']}/approve")
        events = _drain(q)
    finally:
        pipeline.unsubscribe(q)
    assert r.status_code == 200 and r.json()["approved"] is True
    assert "match.approved" in events, events
    after = client.get("/api/state").json()
    assert next(x for x in after["matches"] if x["id"] == m["id"])["approved"]
    _assert_books_balance(after)
    if "voucher.posted" in events:
        assert client.get("/api/export/sie4").content.decode("cp437").count("#VER") == n_ver_before + 1
    assert client.post("/api/matches/nope/approve").status_code == 404


def test_unknown_email_sender_quarantined(demo, tmp_path, monkeypatch):
    from lovelight.models import Source

    monkeypatch.setenv("SENDER_ALLOWLIST", "@trusted.se")
    src = next(p for p in sorted(pipeline.INBOX.iterdir()) if p.suffix == ".pdf")
    path = tmp_path / src.name
    path.write_bytes(src.read_bytes() + b"\n%unknown-sender")
    doc = asyncio.run(pipeline.ingest(path, Source.EMAIL, sender="evil@phish.example", gold=True))
    assert doc.status == "quarantined"
    state = demo["client"].get("/api/state").json()
    an = [a for a in state["anomalies"] if a.get("document_id") == doc.id]
    assert len(an) == 1 and an[0]["title"] == "Unknown sender — quarantined", an
    assert not any(v["document_id"] == doc.id and v["status"] == "posted" for v in state["vouchers"])


def test_same_bytes_ingested_once(demo, tmp_path):
    from lovelight.models import Source

    src = next(p for p in sorted(pipeline.INBOX.iterdir()) if p.suffix == ".pdf")
    path = tmp_path / src.name
    path.write_bytes(src.read_bytes() + b"\n%idempotency")
    n_before = len(demo["client"].get("/api/state").json()["documents"])
    first = asyncio.run(pipeline.ingest(path, Source.UPLOAD, gold=True))
    second = asyncio.run(pipeline.ingest(path, Source.UPLOAD, gold=True))
    assert first.id == second.id
    assert len(demo["client"].get("/api/state").json()["documents"]) == n_before + 1
