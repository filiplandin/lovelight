"""Bank reconciliation: deterministic scoring of bank transactions against extracted documents."""

from __future__ import annotations

import re
from itertools import combinations

from rapidfuzz import fuzz

from lovelight import confidence, knowledge
from lovelight.ledger import to_sek
from lovelight.models import BankTx, Confidence, DocType, Document, Match

AMOUNT_TOLERANCE = 1  # SEK, absorbs rounding to whole kronor
FX_TOLERANCE = 0.025  # non-SEK docs: card FX markup (~1.75 %) and bank FX spread
DATE_WINDOW_DAYS = 10
MIN_CONFIDENCE = 0.6
MAX_SUBSET = 4
MAX_SUBSET_POOL = 12



def _expand(text: str) -> str:
    """Bank texts are truncated/abbreviated; add the KB vendor's name and aliases when a bank pattern matches."""
    hit = knowledge.load().lookup(bank_text=text)
    if not hit:
        return text
    entry = next(v for v in knowledge.load().vendors if v.id == hit.entry_id)
    return " ".join([text, entry.name, *entry.aliases])


def name_score(vendor: str, tx_text: str) -> float:
    """0..1 similarity, robust to bank-side truncation and abbreviations known to the knowledge base."""
    v, t = knowledge.normalize(vendor), knowledge.normalize(_expand(tx_text))
    if not v or not t:
        return 0.0
    return max(fuzz.token_set_ratio(v, t), fuzz.partial_ratio(v, t)) / 100


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def ref_tokens(tx: BankTx) -> set[str]:
    parts = re.split(r"[;,]|\s+", f"{tx.reference or ''};{tx.text}")
    return {d for p in parts if len(d := _digits(p)) >= 4}


def reference_hit(doc: Document, tx: BankTx) -> bool:
    e = doc.extraction
    tokens = ref_tokens(tx)
    for ref in (e.ocr_reference, e.invoice_number):
        d = _digits(ref)
        if len(d) >= 4 and any(d == t or (len(d) >= 6 and d in t) for t in tokens):
            return True
    return False


def tolerance(doc: Document) -> float:
    e = doc.extraction
    if e.currency.upper() == "SEK":
        return AMOUNT_TOLERANCE
    return max(AMOUNT_TOLERANCE, FX_TOLERANCE * abs(float(to_sek(e.gross, e.currency))))


def signed_sek(doc: Document) -> float:
    e = doc.extraction
    gross = to_sek(e.gross, e.currency)
    return float(gross if e.doc_type == DocType.CUSTOMER_INVOICE else -gross)


def date_gap(doc: Document, tx: BankTx) -> int:
    e = doc.extraction
    return min(abs((tx.date - d).days) for d in (e.date, e.due_date) if d is not None)


def eligible(doc: Document, tx: BankTx) -> str | None:
    """Deterministic pairing rules; returns the method name, or None if the pair is not a candidate."""
    expected = signed_sek(doc)
    if expected * float(tx.amount) <= 0:
        return None
    name = name_score(doc.extraction.vendor, tx.text)
    ref = reference_hit(doc, tx)
    if abs(expected - float(tx.amount)) > tolerance(doc):
        # Partial payment: reference + payer name agree, amount is a fraction of the invoice.
        if ref and name >= 0.7 and abs(float(tx.amount)) < abs(expected):
            return "ocr_reference+name (partial)"
        return None
    if ref:
        return "ocr_reference+amount"
    if date_gap(doc, tx) > DATE_WINDOW_DAYS and name < 0.8:
        return None
    return "amount+date+name" if name >= 0.8 else "amount+date"


def _match(tx: BankTx, docs: list[Document], method: str, conf: Confidence | None = None) -> Match:
    conf = conf or confidence.score_group(docs, tx)
    return Match(id=f"m-{tx.id}", bank_tx_id=tx.id, document_ids=[d.id for d in docs], confidence=conf.score,
                 method=method, confidence_detail=conf)


def match(docs: list[Document], txs: list[BankTx]) -> list[Match]:
    docs = [d for d in docs if d.extraction is not None]
    by_id = {d.id: d for d in docs}
    tx_by_id = {t.id: t for t in txs}
    candidates = []
    for tx in txs:
        for d in docs:
            if (method := eligible(d, tx)) and (c := confidence.score_match(d, tx)).score >= MIN_CONFIDENCE:
                candidates.append((c.score, tx.id, d.id, method, c))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    used_tx: set[str] = set()
    used_doc: set[str] = set()
    out: list[Match] = _multi_reference_matches(docs, txs, used_tx, used_doc)
    for _, tx_id, doc_id, method, conf in candidates:
        if tx_id in used_tx or doc_id in used_doc:
            continue
        used_tx.add(tx_id)
        used_doc.add(doc_id)
        out.append(_match(tx_by_id[tx_id], [by_id[doc_id]], method, conf))

    out.extend(_subset_matches(docs, txs, used_tx, used_doc))
    return sorted(out, key=lambda m: m.id)


def _multi_reference_matches(docs: list[Document], txs: list[BankTx], used_tx: set[str], used_doc: set[str]) -> list[Match]:
    """One payment whose reference lists several invoice/OCR numbers that together sum to the amount."""
    out = []
    for tx in sorted(txs, key=lambda t: t.id):
        hits = [d for d in docs if d.id not in used_doc and reference_hit(d, tx)]
        if len(hits) < 2:
            continue
        total = sum(signed_sek(d) for d in hits)
        if abs(total - float(tx.amount)) <= sum(tolerance(d) for d in hits):
            used_tx.add(tx.id)
            used_doc.update(d.id for d in hits)
            out.append(_match(tx, sorted(hits, key=lambda d: d.id), f"ocr_reference x{len(hits)}+amount"))
    return out


def _subset_matches(docs: list[Document], txs: list[BankTx], used_tx: set[str], used_doc: set[str]) -> list[Match]:
    """One payment settling several supplier invoices from the same vendor."""
    out = []
    open_inv = [d for d in docs if d.id not in used_doc and d.extraction.doc_type == DocType.SUPPLIER_INVOICE]
    for tx in sorted(txs, key=lambda t: t.id):
        if tx.id in used_tx or tx.amount >= 0:
            continue
        pool = [d for d in open_inv if d.id not in used_doc and name_score(d.extraction.vendor, tx.text) >= 0.8]
        pool = sorted(pool, key=lambda d: d.id)[:MAX_SUBSET_POOL]
        found = None
        for n in range(2, min(MAX_SUBSET, len(pool)) + 1):
            for combo in combinations(pool, n):
                if abs(sum(signed_sek(d) for d in combo) - float(tx.amount)) <= AMOUNT_TOLERANCE:
                    found = combo
                    break
            if found:
                break
        if not found:
            continue
        used_tx.add(tx.id)
        used_doc.update(d.id for d in found)
        out.append(_match(tx, list(found), f"subset_sum({len(found)})+name"))
    return out
