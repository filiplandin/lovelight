"""Ingestion pipeline and in-process event bus (fan-out to SSE subscribers)."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import logging
import os
import re
import uuid
import weakref
from collections.abc import Awaitable, Iterable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from lovelight import store
from lovelight.metrics import METRICS
from lovelight.models import (
    VAT_RATES,
    Anomaly,
    AnomalyKind,
    BankTx,
    DocStatus,
    Document,
    Match,
    Source,
    Voucher,
)

log = logging.getLogger("lovelight.pipeline")

ROOT = store.ROOT
DATA = ROOT / "data"
GENERATED = DATA / "generated"
INBOX = GENERATED / "inbox"
BANK_CSV = GENERATED / "bank.csv"
LIGHT_CSV = DATA / "invoiceReceivables.csv"
INCOMING = DATA / "incoming"

AUTO_POST_CONFIDENCE = 0.9
AUTO_APPROVE_MATCH = 0.95
MAX_CONCURRENCY = max(1, int(os.environ.get("LOVELIGHT_MAX_CONCURRENCY") or 4))

_subscribers: set[asyncio.Queue] = set()


# ---------- concurrency ----------


@dataclass
class _Sync:
    ledger: asyncio.Lock  # serialises every write to the books (voucher numbers, matches, anomalies)
    slots: asyncio.Semaphore  # bounds concurrent extractions (model calls)


# asyncio primitives bind to the first loop that waits on them; keep one set per loop
# so the same process can serve several loops (e.g. TestClient plus asyncio.run in tests).
_sync_by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _Sync] = weakref.WeakKeyDictionary()

# Set while a batch runs: per-document rematch/anomaly scan is skipped and done once at the end.
_batch_active: ContextVar[bool] = ContextVar("lovelight_batch_active", default=False)


def _sync() -> _Sync:
    loop = asyncio.get_running_loop()
    if (s := _sync_by_loop.get(loop)) is None:
        s = _sync_by_loop[loop] = _Sync(asyncio.Lock(), asyncio.Semaphore(MAX_CONCURRENCY))
    return s


def ledger_lock() -> asyncio.Lock:
    """The lock every mutation of the books must hold."""
    return _sync().ledger


# ---------- event bus ----------


def _plain(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def to_json(obj: Any) -> Any:
    """JSON-safe form; Decimals become strings to keep exact öre amounts."""
    return jsonable_encoder(_plain(obj))


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def emit(type_: str, payload: Any = None) -> None:
    event = {"type": type_, "payload": to_json(payload)}
    for q in list(_subscribers):
        q.put_nowait(event)


# ---------- helpers ----------


def sender_allowed(sender: str | None) -> bool:
    raw = os.environ.get("SENDER_ALLOWLIST", "").strip()
    if not raw:
        return True  # no allowlist configured → demo mode, accept all
    allowed = {s.strip().lower() for s in raw.split(",") if s.strip()}
    if not sender:
        return False
    sender = sender.lower()
    return sender in allowed or any(a.startswith("@") and sender.endswith(a) for a in allowed)


def _next_voucher_number() -> int:
    return max((v.number for v in store.all("vouchers", Voucher)), default=0) + 1


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _validation_error(doc: Document) -> str | None:
    e = doc.extraction
    if abs(e.net + e.vat - e.gross) > Decimal("0.01"):
        return f"net {e.net} + vat {e.vat} != gross {e.gross}"
    if e.vat_rate not in VAT_RATES:
        return f"VAT rate {e.vat_rate} not allowed (25/12/6/0%)"
    return None


def _raw_text(path: Path, email_body: str | None) -> str:
    if email_body:
        return re.sub(r"<[^>]+>", " ", email_body)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if path.suffix.lower() in (".html", ".htm", ".txt", ".eml"):
        return re.sub(r"<[^>]+>", " ", path.read_text(errors="replace"))
    return ""


def injection_snippet(path: Path, email_body: str | None) -> str | None:
    """The line of raw document text holding the embedded instruction, for the Trust Center."""
    from lovelight.anomalies import INJECTION_RE

    try:
        text = _raw_text(path, email_body)
    except Exception:  # best-effort evidence; quarantine proceeds regardless
        log.exception("could not read raw text of %s", path)
        return None
    for line in text.splitlines():
        if INJECTION_RE.search(line):
            return " ".join(line.split())[:400]
    return None


def _anomaly_key(a: Anomaly) -> tuple:
    if a.kind == AnomalyKind.INJECTION:  # quarantine step and document scan both flag injections
        return (a.kind, a.document_id)
    return (a.kind, a.document_id, a.bank_tx_id, a.invoice_number, a.rule)


def _add_anomalies(found: list[Anomaly], emit_events: bool) -> None:
    existing = {_anomaly_key(a) for a in store.all("anomalies", Anomaly)}
    existing_ids = {a.id for a in store.all("anomalies", Anomaly)}
    for a in found:
        if _anomaly_key(a) in existing:
            continue
        if a.id in existing_ids:
            a = a.model_copy(update={"id": _new_id("an")})
        existing.add(_anomaly_key(a))
        existing_ids.add(a.id)
        store.put("anomalies", a)
        if emit_events:
            emit("anomaly.found", a)


def load_bank(path: Path) -> list[BankTx]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    txs = []
    for i, r in enumerate(rows, 1):
        r = {k: (v if v != "" else None) for k, v in r.items()}
        r.setdefault("id", None)
        r["id"] = r["id"] or f"tx_{i:04d}"
        txs.append(BankTx.model_validate({k: v for k, v in r.items() if v is not None}))
    return txs


# ---------- matching ----------


def approve_match(match: Match, emit_events: bool = True) -> Match:
    from lovelight import ledger

    if match.approved:
        return match
    match.approved = True
    store.put("matches", match)
    docs = [d for i in match.document_ids if (d := store.get("documents", i, Document))]
    tx = store.get("bank", match.bank_tx_id, BankTx)
    v = ledger.payment_voucher(match, docs, tx, _next_voucher_number())
    if v is not None:
        ledger.validate(v)
        v.status = "posted"
        store.put("vouchers", v)
        if emit_events:
            emit("voucher.posted", v)
    for d in docs:
        if d.status not in (DocStatus.NEEDS_REVIEW, DocStatus.QUARANTINED):
            d.status = DocStatus.MATCHED
            store.put("documents", d)
    if emit_events:
        emit("match.approved", match)
    return match


def rematch(emit_events: bool = True) -> None:
    from lovelight import matching

    matches = store.all("matches", Match)
    matched_docs = {d for m in matches for d in m.document_ids}
    matched_txs = {m.bank_tx_id for m in matches}
    docs = [
        d
        for d in store.all("documents", Document)
        if d.id not in matched_docs and d.extraction and d.status != DocStatus.QUARANTINED
    ]
    txs = [t for t in store.all("bank", BankTx) if t.id not in matched_txs]
    if not docs or not txs:
        return
    existing_ids = {m.id for m in matches}
    for m in matching.match(docs, txs):
        if m.id in existing_ids:
            m = m.model_copy(update={"id": _new_id("m")})
        existing_ids.add(m.id)
        store.put("matches", m)
        if emit_events:
            emit("match.found", m)
        if m.confidence >= AUTO_APPROVE_MATCH:
            try:
                approve_match(m, emit_events)
            except Exception:
                log.exception("auto-approve failed for match %s", m.id)


def rescan_anomalies(emit_events: bool = True) -> None:
    from lovelight import anomalies

    found = anomalies.scan_documents(
        store.all("documents", Document), store.all("bank", BankTx), store.all("matches", Match)
    )
    # missing-receipt flags resolve once the bank tx gets matched
    still_missing = {a.bank_tx_id for a in found if a.kind == AnomalyKind.MISSING_RECEIPT}
    for a in store.all("anomalies", Anomaly):
        if a.kind == AnomalyKind.MISSING_RECEIPT and a.bank_tx_id not in still_missing:
            store.delete("anomalies", a.id)
    _add_anomalies(found, emit_events)


# ---------- ingestion ----------
#
# Three phases per document:
#   1. claim   (ledger lock)  sha256 dedupe + Document row; identical bytes in flight are claimed once
#   2. extract (slot)         model call in a worker thread, at most MAX_CONCURRENCY at a time
#   3. post    (ledger lock)  quarantine or voucher; voucher numbers are assigned here, serially
# then rematch + anomaly scan (once per document, or once per batch inside run_batch).


def _extract_gold_first(path: Path, email_body: str | None):
    """Demo replay: use the deterministic gold extraction when available, else the live extractor."""
    from lovelight import extract

    try:
        return extract._from_gold(path), "gold-cache"
    except Exception:
        log.warning("no gold extraction for %s; using live extractor", path.name)
        return extract.extract(path, email_body)


async def ingest(
    path: Path,
    source: Source,
    sender: str | None = None,
    email_body: str | None = None,
    gold: bool = False,
) -> Document:
    from lovelight import extract

    path, source = Path(path), Source(source)
    sync = _sync()
    async with sync.ledger:
        doc, is_new = _claim(path, source, sender)
    if not is_new:
        return doc

    try:
        extractor = _extract_gold_first if gold else extract.extract
        async with sync.slots:
            with METRICS.in_flight(), METRICS.timed("extract"):
                extraction, model = await asyncio.to_thread(extractor, path, email_body)
        METRICS.incr("extracted")
    except Exception as e:  # one bad document must never stop the batch
        async with sync.ledger:
            _fail(doc, path, e)
        return doc

    async with sync.ledger:
        try:
            with METRICS.timed("ledger"):
                settle = _post(doc, extraction, model, path, email_body)
        except Exception as e:
            _fail(doc, path, e)
            return doc
        if settle and not _batch_active.get():
            _settle()
    return store.get("documents", doc.id, Document) or doc


async def run_batch(jobs: Iterable[Awaitable[Any]]) -> list[Any]:
    """Run ingest coroutines concurrently, then rematch + anomaly-scan the books once.

    Results (or exceptions) are returned in input order.
    """
    token = _batch_active.set(True)
    try:
        results = await asyncio.gather(*jobs, return_exceptions=True)  # tasks inherit the flag
    finally:
        _batch_active.reset(token)
    async with ledger_lock():
        _settle()
    return results


def _claim(path: Path, source: Source, sender: str | None) -> tuple[Document, bool]:
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    existing = next(
        (d for d in store.all("documents", Document) if d.sha256 == sha and d.source != Source.LIGHT_CSV), None
    )
    if existing is not None:  # idempotent intake: identical bytes are one document
        log.info("skipping %s: same sha256 as %s", path.name, existing.id)
        METRICS.incr("duplicate")
        return existing, False
    doc = Document(
        id=_new_id("doc"),
        source=source,
        filename=path.name,
        sha256=sha,
        sender=sender,
        received_at=datetime.now(UTC),
    )
    store.put("documents", doc)
    store.put_file(doc.id, path)
    METRICS.incr("received")
    emit("doc.received", doc)
    return doc, True


def _fail(doc: Document, path: Path, e: Exception) -> None:
    log.error("ingest failed for %s", path, exc_info=e)
    METRICS.incr("failed")
    doc.status = DocStatus.NEEDS_REVIEW
    doc.note = f"Processing error: {e}"
    store.put("documents", doc)
    emit("doc.needs_review", doc)


def _post(doc: Document, extraction, model: str, path: Path, email_body: str | None) -> bool:
    """Quarantine or propose/post a voucher. Returns True when the books changed and need a rematch."""
    from lovelight import extract, ledger

    doc.extraction = extraction
    doc.status = DocStatus.EXTRACTED
    store.put("documents", doc)
    emit("doc.extracted", doc)

    unknown_sender = doc.source == Source.EMAIL and not sender_allowed(doc.sender)
    if extraction.injection_suspected or unknown_sender:
        if extraction.injection_suspected:
            snippet = injection_snippet(path, email_body)
            reason = "Instructions embedded in document (possible prompt injection)" + (
                f': "{snippet}"' if snippet else ""
            )
        else:
            reason = f"Sender {doc.sender!r} not on allowlist"
        doc.status = DocStatus.QUARANTINED
        doc.note = reason
        store.put("documents", doc)
        METRICS.incr("quarantined")
        emit("doc.quarantined", doc)
        _add_anomalies(
            [
                Anomaly(
                    id=_new_id("an"),
                    kind=AnomalyKind.INJECTION,
                    severity="high",
                    title=(
                        f"Quarantined: {doc.filename}"
                        if extraction.injection_suspected
                        else "Unknown sender — quarantined"
                    ),
                    explanation=f"{reason}. Never auto-posted; requires accountant review.",
                    rule="injection_suspected" if extraction.injection_suspected else "sender_allowlist",
                    document_id=doc.id,
                    invoice_number=extraction.invoice_number,
                )
            ],
            emit_events=True,
        )
        return False

    error = _validation_error(doc)
    voucher = ledger.propose_voucher(doc, _next_voucher_number(), model, extract.PROMPT_VERSION)
    ledger.validate(voucher)
    store.put("vouchers", voucher)
    emit("voucher.proposed", voucher)

    if error:
        doc.status = DocStatus.NEEDS_REVIEW
        doc.note = error
        store.put("documents", doc)
        METRICS.incr("needs_review")
        emit("doc.needs_review", doc)
    elif extraction.confidence >= AUTO_POST_CONFIDENCE:
        voucher.status = "posted"
        store.put("vouchers", voucher)
        doc.status = DocStatus.POSTED
        store.put("documents", doc)
        METRICS.incr("posted")
        emit("voucher.posted", voucher)
    else:
        doc.note = f"Low confidence ({extraction.confidence:.2f}); voucher awaits approval"
        store.put("documents", doc)
        METRICS.incr("pending_approval")
    return True


def _settle() -> None:
    """Rematch bank transactions and rescan anomalies. Caller holds the ledger lock."""
    try:
        with METRICS.timed("match"):
            rematch()
        with METRICS.timed("anomaly_scan"):
            rescan_anomalies()
    except Exception:  # a scan failure must not lose the documents already posted
        log.exception("matching/anomaly scan failed")


# ---------- startup state ----------


def bootstrap() -> None:
    """Reset DB and metrics to initial state: bank feed + Light AR invoices posted. Emits nothing."""
    from lovelight import anomalies, ledger, light_csv

    store.reset()
    METRICS.reset()
    if BANK_CSV.exists():
        for tx in load_bank(BANK_CSV):
            store.put("bank", tx)
    else:
        log.warning("bank feed missing: %s (run scripts/generate_data.py)", BANK_CSV)

    rows = light_csv.load_rows(LIGHT_CSV)
    ar_anomalies = anomalies.scan_ar(rows)
    held: dict = {}
    for a in sorted(ar_anomalies, key=lambda a: ("high", "medium", "low").index(a.severity)):
        held.setdefault(a.document_id, a)
    for doc in light_csv.to_documents(rows):
        store.put("documents", doc)
        store.put_file(doc.id, LIGHT_CSV)
        if doc.extraction is None:
            continue
        if doc.id in held:
            # Flagged invoices are held for accountant review, never auto-posted.
            doc.status = DocStatus.NEEDS_REVIEW
            doc.note = held[doc.id].title
            store.put("documents", doc)
            continue
        v = ledger.propose_voucher(doc, _next_voucher_number(), None, None)
        ledger.validate(v)
        v.status = "posted"
        store.put("vouchers", v)
        doc.status = DocStatus.POSTED
        store.put("documents", doc)
    _add_anomalies(ar_anomalies, emit_events=False)
    rematch(emit_events=False)


# ---------- read model ----------


def state() -> dict:
    from lovelight import ledger
    from lovelight.models import CLIENT_NAME, CLIENT_ORG_NR

    docs = store.all("documents", Document)
    vouchers = store.all("vouchers", Voucher)
    posted = [v for v in vouchers if v.status == "posted"]
    ingested = [d for d in docs if d.source != Source.LIGHT_CSV]
    posted_doc_ids = {v.document_id for v in posted}
    auto = sum(1 for d in ingested if d.id in posted_doc_ids)
    return to_json(
        {
            "client": {"name": CLIENT_NAME, "org_nr": CLIENT_ORG_NR},
            "documents": docs,
            "bank": store.all("bank", BankTx),
            "matches": store.all("matches", Match),
            "vouchers": vouchers,
            "anomalies": store.all("anomalies", Anomaly),
            "reports": {
                "pnl": ledger.pnl(vouchers),
                "balance_sheet": ledger.balance_sheet(vouchers),
                "vat_return": ledger.vat_return(vouchers),
            },
            "stats": {
                "docs_total": len(ingested),
                "auto_posted_pct": round(100 * auto / len(ingested), 1) if ingested else 0.0,
                "minutes_saved": len(ingested) * 4,
            },
        }
    )
