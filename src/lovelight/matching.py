"""Bank reconciliation: deterministic scoring of bank transactions against extracted documents."""

from __future__ import annotations

import re
from itertools import combinations

from rapidfuzz import fuzz

from lovelight.ledger import to_sek
from lovelight.models import BankTx, DocType, Document, Match

AMOUNT_TOLERANCE = 1  # SEK, absorbs öre rounding
FX_TOLERANCE = 0.025  # non-SEK docs: card FX markup (~1.75 %) and bank FX spread
DATE_WINDOW_DAYS = 10
MIN_CONFIDENCE = 0.6
MAX_SUBSET = 4
MAX_SUBSET_POOL = 12

# Bank texts are truncated/abbreviated; map known bank-text tokens to the vendor's legal name.
ALIASES: dict[str, str] = {
    "sl access": "storstockholms lokaltrafik",
    "sl ": "storstockholms lokaltrafik",
    "sj ab": "sj",
    "aws emea": "amazon web services",
    "amzn": "amazon",
    "msft": "microsoft",
    "google *": "google",
    "goog": "google",
    "kjell": "kjell & company",
    "taxi sthlm": "taxi stockholm",
    "skatteverket": "skatteverket",
}


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(ab|aktiebolag|inc|ltd|llc|gmbh|a/s|aps|as|oy|publ)\b", " ", s)
    return re.sub(r"[^a-z0-9åäö& ]+", " ", s).strip()


def _expand(text: str) -> str:
    t = " " + text.lower() + " "
    extra = [full for alias, full in ALIASES.items() if f" {alias}" in t]
    return " ".join([text, *extra])


def name_score(vendor: str, tx_text: str) -> float:
    """0..1 similarity, robust to bank-side truncation ("STORSTOCKHOLMS LOK") and aliases ("SL ACCESS")."""
    v, t = _norm(vendor), _norm(_expand(tx_text))
    if not v or not t:
        return 0.0
    return max(fuzz.token_set_ratio(v, t), fuzz.partial_ratio(v, t)) / 100


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def _ref_tokens(tx: BankTx) -> set[str]:
    parts = re.split(r"[;,]|\s+", f"{tx.reference or ''};{tx.text}")
    return {d for p in parts if len(d := _digits(p)) >= 4}


def reference_hit(doc: Document, tx: BankTx) -> bool:
    e = doc.extraction
    tokens = _ref_tokens(tx)
    for ref in (e.ocr_reference, e.invoice_number):
        d = _digits(ref)
        if len(d) >= 4 and any(d == t or (len(d) >= 6 and d in t) for t in tokens):
            return True
    return False


def _tolerance(doc: Document) -> float:
    e = doc.extraction
    if e.currency.upper() == "SEK":
        return AMOUNT_TOLERANCE
    return max(AMOUNT_TOLERANCE, FX_TOLERANCE * abs(float(to_sek(e.gross, e.currency))))


def _signed_sek(doc: Document) -> float:
    e = doc.extraction
    gross = to_sek(e.gross, e.currency)
    return float(gross if e.doc_type == DocType.CUSTOMER_INVOICE else -gross)


def _date_gap(doc: Document, tx: BankTx) -> int:
    e = doc.extraction
    return min(abs((tx.date - d).days) for d in (e.date, e.due_date) if d is not None)


def score(doc: Document, tx: BankTx) -> tuple[float, str] | None:
    expected = _signed_sek(doc)
    if expected * float(tx.amount) <= 0:
        return None
    amount_diff = abs(expected - float(tx.amount))
    name = name_score(doc.extraction.vendor, tx.text)
    ref = reference_hit(doc, tx)
    if amount_diff > _tolerance(doc):
        # Partial payment: reference + payer name agree, amount is a fraction of the invoice.
        if ref and name >= 0.7 and abs(float(tx.amount)) < abs(expected):
            return round(0.8 + 0.1 * name, 3), "ocr_reference+name (partial)"
        return None
    gap = _date_gap(doc, tx)
    if ref:
        return round(0.95 + 0.04 * name, 3), "ocr_reference+amount"
    if gap > DATE_WINDOW_DAYS and name < 0.8:
        return None
    conf = 0.5
    conf += 0.05 if amount_diff < 0.01 else 0.0
    conf += 0.3 * max(0.0, (name - 0.5) / 0.5)
    conf += 0.12 * max(0.0, 1 - gap / DATE_WINDOW_DAYS)
    method = "amount+date+name" if name >= 0.8 else "amount+date"
    return round(min(conf, 0.98), 3), method


def match(docs: list[Document], txs: list[BankTx]) -> list[Match]:
    docs = [d for d in docs if d.extraction is not None]
    candidates = []
    for tx in txs:
        for d in docs:
            s = score(d, tx)
            if s and s[0] >= MIN_CONFIDENCE:
                candidates.append((s[0], tx.id, d.id, s[1]))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    used_tx: set[str] = set()
    used_doc: set[str] = set()
    out: list[Match] = _multi_reference_matches(docs, txs, used_tx, used_doc)
    for conf, tx_id, doc_id, method in candidates:
        if tx_id in used_tx or doc_id in used_doc:
            continue
        used_tx.add(tx_id)
        used_doc.add(doc_id)
        out.append(Match(id=f"m-{tx_id}", bank_tx_id=tx_id, document_ids=[doc_id], confidence=conf, method=method))

    out.extend(_subset_matches(docs, txs, used_tx, used_doc))
    return sorted(out, key=lambda m: m.id)


def _multi_reference_matches(docs: list[Document], txs: list[BankTx], used_tx: set[str], used_doc: set[str]) -> list[Match]:
    """One payment whose reference lists several invoice/OCR numbers that together sum to the amount."""
    out = []
    for tx in sorted(txs, key=lambda t: t.id):
        hits = [d for d in docs if d.id not in used_doc and reference_hit(d, tx)]
        if len(hits) < 2:
            continue
        total = sum(_signed_sek(d) for d in hits)
        if abs(total - float(tx.amount)) <= sum(_tolerance(d) for d in hits):
            used_tx.add(tx.id)
            used_doc.update(d.id for d in hits)
            out.append(Match(id=f"m-{tx.id}", bank_tx_id=tx.id, document_ids=sorted(d.id for d in hits),
                             confidence=0.97, method=f"ocr_reference x{len(hits)}+amount"))
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
                if abs(sum(_signed_sek(d) for d in combo) - float(tx.amount)) <= AMOUNT_TOLERANCE:
                    found = combo
                    break
            if found:
                break
        if not found:
            continue
        ref = any(reference_hit(d, tx) for d in found)
        used_tx.add(tx.id)
        used_doc.update(d.id for d in found)
        out.append(Match(
            id=f"m-{tx.id}", bank_tx_id=tx.id, document_ids=[d.id for d in found],
            confidence=0.96 if ref else 0.9, method=f"subset_sum({len(found)})+name",
        ))
    return out
