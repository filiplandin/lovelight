"""Ingestion pipeline and in-process event bus (fan-out to SSE subscribers)."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import logging
import os
import random
import re
import uuid
import weakref
from collections.abc import Awaitable, Callable, Iterable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from lovelight import audit, store
from lovelight.metrics import METRICS
from lovelight.models import (
    VAT_RATES,
    Anomaly,
    AnomalyKind,
    BankTx,
    Classification,
    Correction,
    DocStatus,
    DocType,
    Document,
    Extraction,
    History,
    HistoryEntry,
    KBMatch,
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

AUTO_APPROVE_MATCH = 0.95
MINUTES_PER_DOC = 4  # assumed manual keying time per document; an illustrative constant, not a measurement
MAX_CONCURRENCY = max(1, int(os.environ.get("LOVELIGHT_MAX_CONCURRENCY") or 4))
MAX_FILE_BYTES = 20 * 1024 * 1024  # larger files are quarantined before any model call

# Transient model errors (rate limit, overload, 5xx, network) are retried per document with exponential backoff.
RETRY_ATTEMPTS = 3
RETRY_BASE_S = 1.0
TRANSIENT_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}

# Why a document was quarantined; recorded as the anomaly rule and in the audit event.
QUARANTINE_REASONS = {
    "injection_suspected": "Instructions embedded in document (possible prompt injection)",
    "sender_not_allowlisted": "Sender not on allowlist",
    "file_too_large": f"File exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB",
    "unsupported_file_type": "File content is not a PDF, image or text document",
    "empty_file": "File is empty",
}

# Magic-byte signatures → MIME type. File extensions are never trusted.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_TEXT_CONTROL = frozenset(b"\t\n\r\f")
_TEXT_SUFFIXES = (".html", ".htm", ".txt", ".eml")
MIME_SUFFIXES = {  # first entry is the canonical suffix
    "application/pdf": (".pdf",),
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/gif": (".gif",),
    "image/webp": (".webp",),
    "text/html": _TEXT_SUFFIXES,
    "text/plain": (".txt", *_TEXT_SUFFIXES),
}

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


def sniff_mime(data: bytes) -> str | None:
    """MIME type from content (magic bytes / text heuristics); None when unsupported."""
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    head = data[:4096]
    if any(b < 0x20 and b not in _TEXT_CONTROL for b in head):  # binary (zip/docx, executables, ...)
        return None
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError as e:
        if e.start < len(head) - 4:  # not merely a multi-byte char cut at the 4 KB boundary
            return None
        text = head[: e.start].decode("utf-8")
    lowered = text.lstrip().lower()
    if lowered.startswith(("<!doctype html", "<html")) or "<html" in lowered[:1024]:
        return "text/html"
    return "text/plain"


def safe_name(data: bytes, name: str) -> str:
    """`name` with an extension that matches its content, so downstream media types follow the bytes."""
    mime = sniff_mime(data)
    name = Path(name).name or "document"
    if mime is None or Path(name).suffix.lower() in MIME_SUFFIXES[mime]:
        return name
    return f"{name}{MIME_SUFFIXES[mime][0]}"


def _preflight(path: Path) -> str | None:
    """Quarantine reason code for files that must never reach the model, else None."""
    size = path.stat().st_size
    if size == 0:
        return "empty_file"
    if size > MAX_FILE_BYTES:
        return "file_too_large"
    with path.open("rb") as f:
        head = f.read(4096)
    return None if sniff_mime(head) else "unsupported_file_type"


def _raw_text(path: Path, email_body: str | None) -> str:
    parts = [re.sub(r"<[^>]+>", " ", email_body)] if email_body else []
    with path.open("rb") as f:
        mime = sniff_mime(f.read(4096))
    if mime == "application/pdf":
        from pypdf import PdfReader

        parts.append("\n".join(p.extract_text() or "" for p in PdfReader(path).pages))
    elif mime and mime.startswith("text/"):
        parts.append(re.sub(r"<[^>]+>", " ", path.read_text(errors="replace")))
    return "\n".join(parts)


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


def _add_anomalies(found: list[Anomaly], emit_events: bool) -> list[Anomaly]:
    """Store anomalies not already on file; each new one is audited. Returns the new ones."""
    existing = {_anomaly_key(a) for a in store.all("anomalies", Anomaly)}
    existing_ids = {a.id for a in store.all("anomalies", Anomaly)}
    added = []
    for a in found:
        if _anomaly_key(a) in existing:
            continue
        if a.id in existing_ids:
            a = a.model_copy(update={"id": _new_id("an")})
        existing.add(_anomaly_key(a))
        existing_ids.add(a.id)
        store.put("anomalies", a)
        audit.append("system", "anomaly.found", "anomaly", a.id, a.model_dump(mode="json"))
        added.append(a)
        if emit_events:
            emit("anomaly.found", a)
    return added


def _high_anomalies(doc: Document) -> list[Anomaly]:
    """High-severity document anomalies (duplicate, changed payment details, ...) that concern `doc`."""
    from lovelight import anomalies

    found = anomalies.scan_documents(
        store.all("documents", Document), store.all("bank", BankTx), store.all("matches", Match)
    )
    return [a for a in found if a.document_id == doc.id and a.severity == "high"]


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


class MatchBlocked(ValueError):
    """A match whose documents are not yet in the books (in review, quarantined or unposted)."""


def match_blockers(match: Match) -> list[str]:
    """Why a payment cannot be booked yet: every document must be posted and none may be in review."""
    vouchers = store.all("vouchers", Voucher)
    out = []
    for doc_id in match.document_ids:
        d = store.get("documents", doc_id, Document)
        if d is None:
            out.append(f"{doc_id}: document missing")
        elif d.status in (DocStatus.NEEDS_REVIEW, DocStatus.QUARANTINED):
            out.append(f"{d.filename}: {d.status.value.replace('_', ' ')}")
        elif not any(v.document_id == d.id and not v.bank_tx_id and v.status == "posted" for v in vouchers):
            out.append(f"{d.filename}: voucher not posted")
    return out


def approve_match(match: Match, emit_events: bool = True, actor: str = "system") -> Match:
    from lovelight import ledger

    if match.approved:
        return match
    if blockers := match_blockers(match):
        raise MatchBlocked("; ".join(blockers))
    match.approved = True
    store.put("matches", match)
    docs = [d for i in match.document_ids if (d := store.get("documents", i, Document))]
    tx = store.get("bank", match.bank_tx_id, BankTx)
    v = ledger.payment_voucher(match, docs, tx, _next_voucher_number())
    if v is not None:
        ledger.validate(v)
        v.status = "posted"
        store.put("vouchers", v)
        _voucher_event("voucher.posted", v, actor, match_id=match.id)
        if emit_events:
            emit("voucher.posted", v)
    for d in docs:
        if d.status not in (DocStatus.NEEDS_REVIEW, DocStatus.QUARANTINED):
            d.status = DocStatus.MATCHED
            store.put("documents", d)
    audit.append(
        actor,
        "match.approved",
        "match",
        match.id,
        {
            "document_ids": match.document_ids,
            "bank_tx_id": match.bank_tx_id,
            "confidence": match.confidence,
            "method": match.method,
            "payment_voucher_id": v.id if v else None,
            "payment_voucher_lines": _lines(v) if v else None,
        },
    )
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
        approve_ready_matches(emit_events)
        return
    existing_ids = {m.id for m in matches}
    for m in matching.match(docs, txs):
        if m.id in existing_ids:
            m = m.model_copy(update={"id": _new_id("m")})
        existing_ids.add(m.id)
        store.put("matches", m)
        audit.append(
            "system",
            "match.found",
            "match",
            m.id,
            {
                "document_ids": m.document_ids,
                "bank_tx_id": m.bank_tx_id,
                "confidence": m.confidence,
                "method": m.method,
                "confidence_detail": m.confidence_detail,
            },
        )
        if emit_events:
            emit("match.found", m)
    approve_ready_matches(emit_events)


def approve_ready_matches(emit_events: bool = True) -> list[str]:
    """Auto-approve pending matches at or above AUTO_APPROVE_MATCH whose documents are all posted."""
    approved = []
    for m in store.all("matches", Match):
        if m.approved or m.confidence < AUTO_APPROVE_MATCH or match_blockers(m):
            continue
        try:
            approve_match(m, emit_events)
            approved.append(m.id)
        except Exception:
            log.exception("auto-approve failed for match %s", m.id)
    return approved


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
            audit.append("system", "anomaly.resolved", "anomaly", a.id,
                         {"kind": a.kind, "bank_tx_id": a.bank_tx_id, "reason": "bank transaction matched"})
    for a in _add_anomalies(found, emit_events):
        if a.severity == "high" and a.document_id:
            _hold_for_anomaly(a, emit_events)


def _hold_for_anomaly(a: Anomaly, emit_events: bool) -> None:
    """A high-severity anomaly found after posting: reverse the system-posted, unpaid voucher and send to review."""
    from lovelight import ledger

    doc = store.get("documents", a.document_id, Document)
    if doc is None or doc.status != DocStatus.POSTED:  # paid, in review or quarantined: flag only
        return
    if doc.classification and doc.classification.source == "correction":
        return  # booked by a person; the flag is shown, the booking stays
    original = next((v for v in reversed(store.all("vouchers", Voucher))
                     if v.document_id == doc.id and not v.bank_tx_id and not v.reverses_id and v.status == "posted"),
                    None)
    if original is not None:
        reversal = ledger.reverse(original, _next_voucher_number())
        store.put("vouchers", reversal)
        original.status = "reversed"
        store.put("vouchers", original)
        _voucher_event("voucher.posted", reversal, reason=f"anomaly:{a.kind}", anomaly_id=a.id)
        if emit_events:
            emit("voucher.posted", reversal)
    _needs_review(doc, f"{a.title}. Auto-posting withdrawn; {a.explanation}", f"anomaly:{a.kind}")


# ---------- ingestion ----------
#
# Three phases per document:
#   1. claim   (ledger lock)  sha256 dedupe + Document row; identical bytes in flight are claimed once
#   2. extract (slot)         model call in a worker thread, at most MAX_CONCURRENCY at a time, retried on
#                             transient errors with exponential backoff (slot released while waiting)
#   3. post    (ledger lock)  knowledge-base lookup, classification, confidence, then quarantine or voucher;
#                             voucher numbers are assigned here, serially
# then rematch + anomaly scan (once per document, or once per batch inside run_batch).
# Every state change appends a hash-chained audit event (lovelight.audit).


def _extract_gold_first(path: Path, email_body: str | None):
    """Demo replay: use the deterministic gold extraction when available, else the live extractor."""
    from lovelight import extract

    try:
        # saved uploads/attachments carry an 8-hex prefix; gold.json is keyed by the original name
        return extract._from_gold(path.with_name(re.sub(r"^[0-9a-f]{8}_", "", path.name))), "gold-cache"
    except Exception:
        log.warning("no gold extraction for %s; using live extractor", path.name)
        return extract.extract(path, email_body)


def is_transient(e: BaseException) -> bool:
    """Rate limits, overload, 5xx and network errors from the Anthropic SDK (or any error carrying such a status)."""
    try:
        import anthropic

        if isinstance(e, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
            return True
    except ImportError:
        pass
    status = getattr(e, "status_code", None)
    return status in TRANSIENT_STATUS


async def _extract_with_retry(
    extractor: Callable[[Path, str | None], tuple[Extraction, str]],
    doc: Document,
    path: Path,
    email_body: str | None,
) -> tuple[Extraction, str]:
    sync = _sync()
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            async with sync.slots:
                with METRICS.in_flight(), METRICS.timed("extract"):
                    return await asyncio.to_thread(extractor, path, email_body)
        except Exception as e:
            if attempt == RETRY_ATTEMPTS or not is_transient(e):
                raise
            delay = RETRY_BASE_S * 2 ** (attempt - 1) * (1 + random.random() / 4)
            log.warning(
                "transient extraction error for %s (attempt %d/%d): %s; retrying in %.1fs",
                doc.filename, attempt, RETRY_ATTEMPTS, e, delay,
            )
            METRICS.incr("retried")
            audit.append(
                "system", "doc.extract_retry", "document", doc.id,
                {"attempt": attempt, "error": type(e).__name__, "status_code": getattr(e, "status_code", None),
                 "delay_s": round(delay, 2)},
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


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

    if code := _preflight(path):
        async with sync.ledger:
            _quarantine(doc, code, QUARANTINE_REASONS[code])
        return store.get("documents", doc.id, Document) or doc

    try:
        extractor = _extract_gold_first if gold else extract.extract
        extraction, model = await _extract_with_retry(extractor, doc, path, email_body)
        METRICS.incr("extracted")
    except Exception as e:  # one bad document must never stop the batch
        async with sync.ledger:
            _fail(doc, path, e, "extraction_failed")
        return doc

    async with sync.ledger:
        try:
            with METRICS.timed("ledger"):
                settle = _post(doc, extraction, model, path, email_body)
        except Exception as e:
            _fail(doc, path, e, "posting_failed")
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
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    existing = next(
        (d for d in store.all("documents", Document) if d.sha256 == sha and d.source != Source.LIGHT_CSV), None
    )
    if existing is not None:  # idempotent intake: identical bytes are one document
        log.info("skipping %s: same sha256 as %s", path.name, existing.id)
        METRICS.incr("duplicate")
        audit.append(
            "system", "doc.duplicate_skipped", "document", existing.id,
            {"filename": path.name, "source": source}, input_sha256=sha,
        )
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
    audit.append(
        "system", "doc.received", "document", doc.id,
        {"filename": doc.filename, "source": source, "sender": sender, "bytes": len(data),
         "mime": sniff_mime(data[:4096])},
        input_sha256=sha,
    )
    emit("doc.received", doc)
    return doc, True


def _fail(doc: Document, path: Path, e: Exception, code: str) -> None:
    log.error("ingest failed for %s", path, exc_info=e)
    METRICS.incr("failed")
    doc.status = DocStatus.NEEDS_REVIEW
    doc.note = f"Processing error: {e}"
    store.put("documents", doc)
    audit.append(
        "system", "doc.needs_review", "document", doc.id,
        {"reason_code": code, "error": type(e).__name__, "message": str(e)[:500]},
    )
    emit("doc.needs_review", doc)


def _quarantine(doc: Document, code: str, reason: str) -> None:
    doc.status = DocStatus.QUARANTINED
    doc.note = reason
    store.put("documents", doc)
    METRICS.incr("quarantined")
    audit.append("system", "doc.quarantined", "document", doc.id, {"reason_code": code, "reason": reason})
    emit("doc.quarantined", doc)


def _lines(v: Voucher) -> list[dict]:
    return [{"account": ln.account, "debit": ln.debit, "credit": ln.credit} for ln in v.lines]


def _voucher_event(action: str, v: Voucher, actor: str = "system", **extra: Any) -> None:
    audit.append(
        actor, action, "voucher", v.id,
        {"document_id": v.document_id, "number": v.number, "date": v.date, "status": v.status,
         "lines": _lines(v), "reverses_id": v.reverses_id, **extra},
    )


def model_output(extraction: Extraction) -> dict:
    """The schema-validated model output as stored and hashed (code-set confidence_detail excluded)."""
    return extraction.model_dump(mode="json", exclude={"confidence_detail"})


def _kb():
    from lovelight import knowledge

    return knowledge.load()


def _account_name(account: str) -> str:
    return _kb().accounts.get(account, "")


def _lookup(doc: Document, ext: Extraction) -> KBMatch | None:
    return _kb().lookup(vendor=ext.vendor, email=doc.sender, org_nr=ext.vendor_org_nr)


def _vendor_key(doc: Document) -> str | None:
    from lovelight import knowledge

    e = doc.extraction
    return knowledge.vendor_key(e.vendor, doc.kb_match, e.vendor_org_nr) if e else None


def _classify(ext: Extraction, kb_match: KBMatch | None, history_: History) -> Classification:
    from lovelight import classify, ledger

    if ext.doc_type == DocType.CUSTOMER_INVOICE:
        return Classification(
            account=ledger.SALES,
            account_name=_account_name(ledger.SALES),
            activity=None,
            source="policy",
            rationale=f"Customer invoices book net revenue to {ledger.SALES} and output VAT to {ledger.OUTPUT_VAT}.",
            policy_consistent=True,
        )
    from lovelight import knowledge

    key = knowledge.vendor_key(ext.vendor, kb_match, ext.vendor_org_nr)
    return classify.classify(ext, kb_match, history_, vendor_key=key, kb=_kb())


def _failed_checks(conf) -> str:
    failed = [c for c in conf.components if c.passed is False]
    parts = [f"{c.name} ({c.detail})" if c.detail else c.name for c in failed]
    gates = f"; gates: {', '.join(conf.gates)}" if conf.gates else ""
    return (", ".join(parts) or "no single check failed") + gates


def _post(doc: Document, extraction: Extraction, model: str, path: Path, email_body: str | None) -> bool:
    """Classify, score, then quarantine or propose/post a voucher. Returns True when the books changed."""
    from lovelight import confidence, extract, knowledge, ledger

    output = model_output(extraction)
    output_sha = audit.sha256_json(output)
    store.put_raw("model_outputs", doc.id, json.dumps({"model": model, "output": output, "output_sha256": output_sha}))
    prov = extract.provenance(doc.sha256)
    cache_hit = prov.get("cache_hit", model == "gold-cache")
    audit.append(
        f"cache:{model}" if cache_hit and model != "gold-cache" else f"model:{model}", "doc.extracted", "document",
        doc.id,
        {"model": model, "prompt_version": extract.PROMPT_VERSION,
         "prompt_sha256": prov.get("prompt_sha256") or extract.PROMPT_SHA256,
         "prompt_sha256_scope": "exact prompt sent" if prov.get("prompt_sha256") else "base prompt (no KB context)",
         "kb_context": prov.get("kb_context", []), "cache_hit": cache_hit, "input_sha256": doc.sha256,
         "output_sha256": output_sha, "doc_type": extraction.doc_type, "vendor": extraction.vendor,
         "gross": extraction.gross, "currency": extraction.currency},
        input_sha256=doc.sha256,
    )

    kb_match = _lookup(doc, extraction)
    if kb_match:
        audit.append("system", "kb.hit", "document", doc.id, kb_match.model_dump(mode="json"))
    else:
        audit.append("system", "kb.miss", "document", doc.id, {"vendor": extraction.vendor, "sender": doc.sender})
    past = history()
    cls = _classify(extraction, kb_match, past)
    conf = confidence.score_extraction(
        extraction,
        past,
        activity=cls.activity,
        account=cls.account,
        expected_vat_rates=cls.expected_vat_rates or None,
        received=doc.received_at.date(),
        classification=cls,
        vendor_key=knowledge.vendor_key(extraction.vendor, kb_match, extraction.vendor_org_nr),
    )
    extraction.confidence_detail = conf
    doc.extraction, doc.kb_match, doc.classification = extraction, kb_match, cls
    doc.status = DocStatus.EXTRACTED
    store.put("documents", doc)
    audit.append(
        "system", "doc.classified", "document", doc.id,
        {"classification": cls, "confidence": {"score": conf.score, "version": conf.version, "gates": conf.gates,
                                               "components": [c.model_dump(mode="json") for c in conf.components]}},
    )
    emit("doc.extracted", doc)

    unknown_sender = doc.source == Source.EMAIL and not sender_allowed(doc.sender)
    if extraction.injection_suspected or unknown_sender:
        if extraction.injection_suspected:
            code = "injection_suspected"
            snippet = injection_snippet(path, email_body)
            reason = QUARANTINE_REASONS[code] + (f': "{snippet}"' if snippet else "")
        else:
            code = "sender_not_allowlisted"
            reason = f"Sender {doc.sender!r} not on allowlist"
        _quarantine(doc, code, reason)
        _add_anomalies(
            [
                Anomaly(
                    id=_new_id("an"),
                    kind=AnomalyKind.INJECTION,
                    severity="high",
                    title=(
                        f"Quarantined: {doc.filename}" if extraction.injection_suspected
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
    voucher = ledger.propose_voucher(_booked(doc), _next_voucher_number(), model, extract.PROMPT_VERSION)
    ledger.validate(voucher)
    store.put("vouchers", voucher)
    _voucher_event("voucher.proposed", voucher, account=cls.account, classification_source=cls.source)
    emit("voucher.proposed", voucher)

    act = _kb().activities.get(cls.activity) if cls.activity else None
    flags = _add_anomalies(_high_anomalies(doc), emit_events=True)
    if error:
        _needs_review(doc, error, "validation_failed")
    elif flags:
        a = flags[0]
        _needs_review(doc, f"{a.title}. Voucher awaits approval: {a.explanation}", f"anomaly:{a.kind}")
    elif act and act.requires_review:
        _needs_review(doc, f"Activity '{act.id}' always needs an accountant: {(act.vat_note or act.description).strip()} "
                           "Voucher awaits approval.", "policy:requires_review")
    elif voucher.reverse_charge == "unknown":
        _needs_review(doc, "Reverse-charge VAT self-assessed at 25 %, but the supplier's country is unknown: confirm "
                           "EU (VAT box 21) or non-EU (box 22). Voucher awaits approval.", "reverse_charge_country")
    elif conf.score >= confidence.AUTO_POST_THRESHOLD:
        voucher.status = "posted"
        store.put("vouchers", voucher)
        doc.status = DocStatus.POSTED
        store.put("documents", doc)
        METRICS.incr("posted")
        _voucher_event("voucher.posted", voucher, confidence=conf.score, threshold=confidence.AUTO_POST_THRESHOLD)
        emit("voucher.posted", voucher)
    else:
        _needs_review(
            doc,
            f"Confidence {conf.score:.2f} below {confidence.AUTO_POST_THRESHOLD:.2f}: {_failed_checks(conf)}. "
            "Voucher awaits approval.",
            "low_confidence",
        )
    return True


def _booked(doc: Document, account: str | None = None) -> Document:
    """A copy of `doc` whose cost account is the classified (or given) one; the stored extraction is untouched."""
    account = account or (doc.classification.account if doc.classification else None)
    if not account or doc.extraction.doc_type == DocType.CUSTOMER_INVOICE:
        return doc
    return doc.model_copy(update={"extraction": doc.extraction.model_copy(update={"suggested_account": account})})


def _needs_review(doc: Document, note: str, code: str) -> None:
    doc.status = DocStatus.NEEDS_REVIEW
    doc.note = note
    store.put("documents", doc)
    METRICS.incr("needs_review")
    audit.append("system", "doc.needs_review", "document", doc.id, {"reason_code": code, "note": note})
    emit("doc.needs_review", doc)


def _settle() -> None:
    """Rematch bank transactions and rescan anomalies. Caller holds the ledger lock."""
    try:
        with METRICS.timed("match"):
            rematch()
        with METRICS.timed("anomaly_scan"):
            rescan_anomalies()
    except Exception:  # a scan failure must not lose the documents already posted
        log.exception("matching/anomaly scan failed")


# ---------- memory: posted history and accountant corrections ----------


def corrections() -> list[Correction]:
    return [Correction.model_validate_json(r) for r in store.all_raw("corrections")]


def history() -> History:
    """Posted cost documents (with their booked account) plus every accountant correction, oldest first."""
    entries = [
        HistoryEntry(
            vendor=d.extraction.vendor,
            account=d.classification.account if d.classification else d.extraction.suggested_account,
            vat_rate=d.extraction.vat_rate,
            date=d.extraction.date,
            document_id=d.id,
            vendor_key=_vendor_key(d),
        )
        for d in store.all("documents", Document)
        if d.extraction
        and d.source != Source.LIGHT_CSV
        and d.extraction.doc_type != DocType.CUSTOMER_INVOICE
        and d.status in (DocStatus.POSTED, DocStatus.MATCHED)
    ]
    return History(entries=entries, corrections=corrections())


def kb_proposals() -> list[dict]:
    return [json.loads(r) for r in store.all_raw("kb_proposals")]


class CorrectionError(ValueError):
    """Raised for a correction the books cannot accept; `status` is the HTTP status to report."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def correct(doc_id: str, account: str, reason: str, user: str = "accountant") -> dict:
    """Re-book a document to another account without editing history. Caller holds the ledger lock.

    A posted voucher is reversed (mirror voucher) and a corrected voucher is posted; an unposted proposal is marked
    superseded and replaced. A document that was in review stays in review: its corrected voucher is only proposed
    and still needs /approve, so a correction never bypasses the reason for review. The correction is stored as
    classification memory and turned into a knowledge-base proposal.
    """
    from lovelight import knowledge, ledger

    doc = store.get("documents", doc_id, Document)
    if doc is None:
        raise CorrectionError(404, "document not found")
    reason, user, account = reason.strip(), (user or "accountant").strip() or "accountant", account.strip()
    if not reason:
        raise CorrectionError(422, "a reason is required")
    kb = _kb()
    if account not in kb.accounts:
        raise CorrectionError(422, f"account {account} is not in the chart of accounts")
    if doc.extraction is None or doc.extraction.doc_type == DocType.CUSTOMER_INVOICE:
        raise CorrectionError(422, "only cost documents can be re-booked to another account")
    original = next(
        (
            v for v in reversed(store.all("vouchers", Voucher))
            if v.document_id == doc.id and not v.bank_tx_id and not v.reverses_id and v.status in ("posted", "proposed")
        ),
        None,
    )
    if original is None:
        raise CorrectionError(409, "document has no voucher to correct")
    if not kb.is_cost(account):
        raise CorrectionError(422, f"{account} is a {kb.account_type(account)} account, not a cost account")
    if doc.status == DocStatus.QUARANTINED:
        raise CorrectionError(409, "document is quarantined; reject it or review the original first")
    previous = doc.classification.account if doc.classification else doc.extraction.suggested_account
    if account == previous:
        raise CorrectionError(422, f"document is already booked to {account}")

    reversal = None
    if original.status == "posted":
        reversal = ledger.reverse(original, _next_voucher_number())
        store.put("vouchers", reversal)
        original.status = "reversed"
    else:
        original.status = "superseded"
    store.put("vouchers", original)

    in_review = doc.status == DocStatus.NEEDS_REVIEW
    corrected = ledger.propose_voucher(
        _booked(doc, account), _next_voucher_number(), original.model, original.prompt_version
    )
    corrected.description = f"Correction of #{original.number}: {corrected.description}"
    corrected.status = "proposed" if in_review else "posted"
    store.put("vouchers", corrected)

    today = date.today()
    c = Correction(
        vendor=doc.extraction.vendor, account=account, previous_account=previous, date=today,
        reason=reason, user=user, document_id=doc.id, vendor_key=_vendor_key(doc), org_nr=doc.extraction.vendor_org_nr,
    )
    store.put_raw("corrections", _new_id("corr"), c.model_dump_json())
    current_activity = doc.classification.activity if doc.classification else doc.extraction.activity
    proposal = knowledge.propose_from_correction(c, kb, current_activity, doc.sender)
    proposal_id = _new_id("kbp")
    store.put_raw("kb_proposals", proposal_id, json.dumps(to_json({"id": proposal_id, **proposal})))

    prior = doc.classification
    doc.classification = Classification(
        account=account,
        account_name=kb.accounts[account],
        activity=prior.activity if prior else doc.extraction.activity,
        source="correction",
        rationale=f"Corrected by {user} on {today.isoformat()}: {reason}",
        policy_consistent=prior.policy_consistent if prior else False,
        overridden_model_account=previous,
        expected_vat_rates=prior.expected_vat_rates if prior else [],
        vat_ambiguous=prior.vat_ambiguous if prior else False,
    )
    if in_review:
        doc.note = f"Corrected to {account} by {user}; voucher #{corrected.number} awaits approval. Was: {doc.note}"
    store.put("documents", doc)

    actor = f"user:{user}"
    if reversal:
        _voucher_event("voucher.posted", reversal, actor)
    _voucher_event("voucher.proposed" if in_review else "voucher.posted", corrected, actor)
    audit.append(
        actor, "voucher.corrected", "document", doc.id,
        {
            "before": {"account": previous, "voucher_id": original.id},
            "after": {"account": account, "voucher_id": corrected.id},
            "reason": reason,
            "reversal_voucher_id": reversal.id if reversal else None,
            "corrected_voucher_id": corrected.id,
            "original_status": original.status,
        },
    )
    audit.append(actor, "kb.proposed", "document", doc.id, {"proposal_id": proposal_id, **proposal})
    if reversal:
        emit("voucher.posted", reversal)
    emit("voucher.proposed" if in_review else "voucher.posted", corrected)
    emit("voucher.corrected", {"document_id": doc.id, "before": previous, "after": account})
    if not in_review:
        approve_ready_matches()
    return to_json({"reversal": reversal, "corrected": corrected, "correction": c, "kb_proposal": proposal})


def _proposed_voucher(doc: Document) -> Voucher | None:
    return next(
        (v for v in reversed(store.all("vouchers", Voucher))
         if v.document_id == doc.id and not v.bank_tx_id and not v.reverses_id and v.status == "proposed"),
        None,
    )


def approve_document(doc_id: str, user: str = "accountant", note: str | None = None) -> dict:
    """Accountant approves the proposed voucher of a document in review: it is posted. Caller holds the ledger lock."""
    doc = store.get("documents", doc_id, Document)
    if doc is None:
        raise CorrectionError(404, "document not found")
    if doc.status != DocStatus.NEEDS_REVIEW:
        raise CorrectionError(409, f"document is {doc.status.value}, not awaiting review")
    if doc.extraction and (error := _validation_error(doc)):
        raise CorrectionError(409, f"extraction fails validation ({error}); correct or reject it")
    voucher = _proposed_voucher(doc)
    if voucher is None:
        raise CorrectionError(409, "document has no proposed voucher to approve")
    user = (user or "accountant").strip() or "accountant"
    actor = f"user:{user}"
    reason_for_review = doc.note
    voucher.status = "posted"
    store.put("vouchers", voucher)
    doc.status, doc.note = DocStatus.POSTED, None
    store.put("documents", doc)
    _voucher_event("voucher.posted", voucher, actor)
    audit.append(actor, "voucher.approved", "voucher", voucher.id,
                 {"document_id": doc.id, "number": voucher.number, "review_reason": reason_for_review,
                  "note": (note or "").strip() or None})
    emit("voucher.posted", voucher)
    approve_ready_matches()
    return to_json({"document": doc, "voucher": voucher})


def reject_document(doc_id: str, reason: str, user: str = "accountant") -> dict:
    """Accountant rejects a document in review or quarantine: its proposed voucher is never posted."""
    doc = store.get("documents", doc_id, Document)
    if doc is None:
        raise CorrectionError(404, "document not found")
    reason = (reason or "").strip()
    if not reason:
        raise CorrectionError(422, "a reason is required")
    if doc.status not in (DocStatus.NEEDS_REVIEW, DocStatus.QUARANTINED):
        raise CorrectionError(409, f"document is {doc.status.value}; posted documents are corrected, not rejected")
    user = (user or "accountant").strip() or "accountant"
    voucher = _proposed_voucher(doc)
    if voucher is not None:
        voucher.status = "rejected"
        store.put("vouchers", voucher)
    previous = doc.status
    doc.status, doc.note = DocStatus.REJECTED, f"Rejected by {user}: {reason}"
    store.put("documents", doc)
    audit.append(f"user:{user}", "doc.rejected", "document", doc.id,
                 {"reason": reason, "previous_status": previous, "voucher_id": voucher.id if voucher else None})
    emit("doc.rejected", doc)
    return to_json({"document": doc, "voucher": voucher})


# ---------- startup state ----------


def bootstrap() -> None:
    """Reset DB and metrics to initial state: bank feed + Light AR invoices posted. Emits nothing.

    The audit log is never reset; the reset itself is appended to it.
    """
    from lovelight import anomalies, ledger, light_csv

    store.reset()
    METRICS.reset()
    bank = load_bank(BANK_CSV) if BANK_CSV.exists() else []
    if not bank:
        log.warning("bank feed missing: %s (run scripts/generate_data.py)", BANK_CSV)
    for tx in bank:
        store.put("bank", tx)

    rows = light_csv.load_rows(LIGHT_CSV)
    ar_anomalies = anomalies.scan_ar(rows)
    held: dict = {}
    for a in sorted(ar_anomalies, key=lambda a: ("high", "medium", "low").index(a.severity)):
        held.setdefault(a.document_id, a)
    posted: list[str] = []
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
        _voucher_event("voucher.posted", v, source="light_csv")
        posted.append(v.id)
        doc.status = DocStatus.POSTED
        store.put("documents", doc)
    _add_anomalies(ar_anomalies, emit_events=False)
    audit.append(
        "system", "books.reset", "books", "books",
        {
            "bank_csv_sha256": _file_sha(BANK_CSV), "bank_txs": len(bank),
            "light_csv_sha256": _file_sha(LIGHT_CSV), "ar_vouchers_posted": posted,
            "ar_held_for_review": sorted(held),
        },
    )
    rematch(emit_events=False)


def bootstrap_if_empty() -> bool:
    """Bootstrap only a fresh database, so a restart or deploy never wipes the books. Returns True if it ran."""
    if store.count("documents"):
        return False
    bootstrap()
    return True


def _file_sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


# ---------- read model ----------


def state() -> dict:
    from lovelight import ledger
    from lovelight.models import CLIENT_NAME, CLIENT_ORG_NR

    docs = store.all("documents", Document)
    vouchers = store.all("vouchers", Voucher)
    ingested = [d for d in docs if d.source != Source.LIGHT_CSV]
    ingested_ids = {d.id for d in ingested}
    live = {(v.id, v.document_id) for v in vouchers if v.status == "posted" and not v.bank_tx_id and not v.reverses_id}
    # auto-posted = a document voucher posted by the system itself (not approved or corrected by a person)
    auto_ids = {
        e.data.get("document_id") for e in audit.events()
        if e.action == "voucher.posted" and e.actor == "system" and (e.entity_id, e.data.get("document_id")) in live
    }
    auto = len(auto_ids & ingested_ids)
    bad = ledger.validate_all(vouchers)
    reportable = [v for v in vouchers if v.id != bad] if bad else vouchers
    return to_json(
        {
            "client": {"name": CLIENT_NAME, "org_nr": CLIENT_ORG_NR},
            "documents": docs,
            "bank": store.all("bank", BankTx),
            "matches": [{**m.model_dump(mode="json"), "blocked_by": [] if m.approved else match_blockers(m)}
                        for m in store.all("matches", Match)],
            "vouchers": vouchers,
            "anomalies": store.all("anomalies", Anomaly),
            "reports": {
                "pnl": ledger.pnl(reportable),
                "balance_sheet": ledger.balance_sheet(reportable),
                "vat_return": ledger.vat_return(reportable),
            },
            "integrity": {"ledger_ok": bad is None, "first_bad_voucher": bad},
            "stats": {
                "docs_total": len(ingested),
                "auto_posted_pct": round(100 * auto / len(ingested), 1) if ingested else 0.0,
                "minutes_saved": len(ingested) * MINUTES_PER_DOC,
                "minutes_saved_assumption": f"{MINUTES_PER_DOC} min of manual keying per document (assumption)",
            },
        }
    )
