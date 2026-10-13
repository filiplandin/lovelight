"""Append-only, hash-chained audit log.

Each event commits to its predecessor: hash = sha256(prev_hash + canonical_json(event without "hash")),
with prev_hash = GENESIS for the first event. Editing, dropping or reordering any past event breaks every
later hash, so `verify` pinpoints the first bad link. SQLite triggers additionally refuse UPDATE/DELETE on the
table; someone with raw write access to the file can still drop them and rewrite the whole chain, which is why
the head hash should be anchored outside the database (see SECURITY.md).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from lovelight import store
from lovelight.models import AuditEvent

GENESIS = "0" * 64


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def _json_default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, (Decimal, date, datetime)):
        return str(obj) if isinstance(obj, Decimal) else obj.isoformat()  # Decimals stay exact strings
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")


def _hash(event: AuditEvent) -> str:
    body = event.model_dump(mode="json", exclude={"hash"})
    return hashlib.sha256(event.prev_hash.encode() + canonical_json(body)).hexdigest()


def append(
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    data: dict | None = None,
    input_sha256: str | None = None,
) -> AuditEvent:
    """Append one event. Reading the tail and inserting happen in one locked transaction, so seq stays gap-free."""
    payload = json.loads(json.dumps(data or {}, default=_json_default))  # JSON-native, so the hash is stable
    with store.locked() as con:
        row = con.execute("SELECT data FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prev = AuditEvent.model_validate_json(row[0]) if row else None
        event = AuditEvent(
            seq=prev.seq + 1 if prev else 1,
            ts=datetime.now(UTC),
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            data=payload,
            input_sha256=input_sha256,
            prev_hash=prev.hash if prev else GENESIS,
            hash="",
        )
        event.hash = _hash(event)
        con.execute("INSERT INTO audit (seq, data) VALUES (?, ?)", (event.seq, event.model_dump_json()))
    return event


def _concerns(event: AuditEvent, entity_id: str) -> bool:
    d = event.data
    return (
        event.entity_id == entity_id
        or d.get("document_id") == entity_id
        or entity_id in (d.get("document_ids") or [])
    )


def events(entity_id: str | None = None) -> list[AuditEvent]:
    with store.locked() as con:
        rows = con.execute("SELECT data FROM audit ORDER BY seq").fetchall()
    out = [AuditEvent.model_validate_json(r[0]) for r in rows]
    return out if entity_id is None else [e for e in out if _concerns(e, entity_id)]


def _chain(chain: list[AuditEvent]) -> dict:
    prev_hash = GENESIS
    for i, e in enumerate(chain, 1):
        if e.seq != i or e.prev_hash != prev_hash or e.hash != _hash(e):
            return {"ok": False, "events": len(chain), "head": chain[-1].hash, "first_bad_seq": e.seq}
        prev_hash = e.hash
    return {"ok": True, "events": len(chain), "head": prev_hash, "first_bad_seq": None}


def _norm_lines(lines: list) -> list[tuple[str, Decimal, Decimal]]:
    def get(ln, k):
        return ln[k] if isinstance(ln, dict) else getattr(ln, k)

    return sorted((get(ln, "account"), Decimal(str(get(ln, "debit"))), Decimal(str(get(ln, "credit")))) for ln in lines)


def verify_ledger(chain: list[AuditEvent]) -> str | None:
    """First voucher in the books that is unbalanced or differs from its latest voucher.* audit event, else None.

    The vouchers table is mutable storage; the hash chain is the record. Every posted or reversed voucher must
    balance and carry exactly the lines of the last audited state, and a reversed voucher needs its reversal.
    """
    from lovelight import ledger
    from lovelight.models import Voucher

    latest: dict[str, AuditEvent] = {}
    for e in chain:
        if e.entity == "voucher" and e.action in ("voucher.posted", "voucher.proposed"):
            latest[e.entity_id] = e
    vouchers = store.all("vouchers", Voucher)
    reversed_ids = {v.reverses_id for v in vouchers if v.reverses_id and v.status == "posted"}
    for v in sorted(vouchers, key=lambda v: v.number):
        if v.status not in ledger.REPORTED_STATUSES:
            continue
        e = latest.get(v.id)
        try:
            ledger.validate(v)
        except ledger.UnbalancedVoucher:
            return v.id
        if (
            e is None
            or e.action != "voucher.posted"
            or e.data.get("document_id") != v.document_id
            or _norm_lines(e.data.get("lines") or []) != _norm_lines(v.lines)
            or (v.status == "reversed" and v.id not in reversed_ids)
        ):
            return v.id
    return None


def verify(events_: list[AuditEvent] | None = None) -> dict:
    """Recompute the chain; for the live log also check the books against it.

    Returns {ok, events, head, first_bad_seq} plus {chain_ok, ledger_ok, first_bad_voucher} for the live log.
    """
    if events_ is not None:
        return _chain(events_)
    chain = events()
    out = _chain(chain)
    bad = verify_ledger(chain)
    return {**out, "chain_ok": out["ok"], "ledger_ok": bad is None, "first_bad_voucher": bad,
            "ok": out["ok"] and bad is None}


def count(action: str) -> int:
    return sum(1 for e in events() if e.action == action)
