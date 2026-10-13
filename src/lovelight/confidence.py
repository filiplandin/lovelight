"""Explainable confidence: named deterministic checks, explicit weights, hard gates.

score = sum(weight * value) / sum(weight) over applicable checks (passed is not None), then capped at GATE_CAP
when a gate check failed. The model's own confidence is one check among several and can neither force nor
fully block auto-posting on its own.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from lovelight import knowledge
from lovelight.models import (
    VAT_RATES,
    BankTx,
    Classification,
    Confidence,
    ConfidenceComponent,
    DocType,
    Document,
    Extraction,
    History,
)

VERSION = "conf-v2"
METHOD = "weighted_mean+gates"
AUTO_POST_THRESHOLD = 0.9
GATE_CAP = 0.5
EXTRACTION_WEIGHTS = {
    "arithmetic": 0.10,  # also a gate, so its weight only matters when it passes
    "vat_rate_legal": 0.10,
    "vat_activity": 0.10,
    "required_fields": 0.10,
    "identifier_checksum": 0.10,  # a failed org nr / bankgiro checksum alone blocks auto-posting
    "date_plausible": 0.10,
    "model_self_report": 0.20,
    "vendor_history": 0.10,
    "classification": 0.10,  # gate when the account is a fallback guess
}
EXTRACTION_GATES = ("arithmetic", "vat_rate_legal")
MATCH_WEIGHTS = {"amount": 0.40, "reference": 0.30, "name": 0.20, "date": 0.10}
REFERENCE_AMOUNT_FLOOR = 0.95
SUM_TOLERANCE = Decimal("0.01")
VAT_TOLERANCE = Decimal("0.05")
MAX_DAYS_AFTER_RECEIPT = 1
MAX_PAYMENT_TERMS_DAYS = 120
MODEL_PASS = 0.5


def _pct(r: Decimal) -> str:
    return f"{r * 100:.0f} %"


def _component(name: str, weights: dict[str, float], passed: bool | None, detail: str, value: float | None = None):
    v = value if value is not None else (1.0 if passed else 0.0)
    return ConfidenceComponent(name=name, value=max(0.0, min(1.0, v)), weight=weights[name], passed=passed, detail=detail)


def _aggregate(components: list[ConfidenceComponent], gates: tuple[str, ...] = (), floors=()) -> Confidence:
    applicable = [c for c in components if c.passed is not None]
    total = sum(c.weight for c in applicable)
    score = sum(c.weight * c.value for c in applicable) / total if total else 0.0
    failed = [c.name for c in components if c.name in gates and c.passed is False]
    if failed:
        score = min(score, GATE_CAP)
    applied = []
    for label, cond, floor in floors:
        if cond and not failed and score < floor:
            score, applied = floor, [*applied, label]
    return Confidence(score=score, components=components, method=METHOD, version=VERSION, gates=failed + applied)


# ---------- identifiers ----------


def luhn_ok(digits: str) -> bool:
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _iban_ok(iban: str) -> bool:
    s = re.sub(r"\s", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    return int("".join(str(int(ch, 36)) for ch in s[4:] + s[:4])) % 97 == 1


def _identifiers(e: Extraction) -> list[tuple[str, str, bool]]:
    out = []
    # Swedish org/personal numbers only (10 digits, or 12 with century); foreign company ids use other schemes.
    org = e.vendor_org_nr or ""
    if org and not re.match(r"\s*(?!SE)[A-Z]{2}", org.upper()) and len(d := re.sub(r"\D", "", org)) in (10, 12):
        out.append(("org nr", org, luhn_ok(d[-10:])))
    if e.bankgiro:
        d = re.sub(r"\D", "", e.bankgiro)
        out.append(("bankgiro", e.bankgiro, 7 <= len(d) <= 8 and luhn_ok(d)))
    if e.ocr_reference:
        d = re.sub(r"\D", "", e.ocr_reference)
        out.append(("OCR", e.ocr_reference, len(d) >= 2 and luhn_ok(d)))
    if e.iban:
        out.append(("IBAN", e.iban, _iban_ok(e.iban)))
    return out


# ---------- extraction ----------


def score_extraction(
    ext: Extraction,
    history: History | None = None,
    *,
    activity: str | None = None,
    account: str | None = None,
    expected_vat_rates: list[Decimal] | None = None,
    received: date | None = None,
    classification: Classification | None = None,
    vendor_key: str | None = None,
) -> Confidence:
    """Score an extraction. activity/account/expected_vat_rates default to the extraction's and the activity's."""
    W = EXTRACTION_WEIGHTS
    e = ext
    received = received or date.today()
    activity = activity or e.activity
    account = account or e.suggested_account
    comps: list[ConfidenceComponent] = []

    # arithmetic: net + VAT = gross, and VAT = net x rate
    sum_diff = abs(e.net + e.vat - e.gross)
    rate_diff = abs(e.net * e.vat_rate - e.vat)
    ok = sum_diff <= SUM_TOLERANCE and rate_diff <= VAT_TOLERANCE
    detail = f"{e.net} + {e.vat} = {e.net + e.vat}" + (" = " if sum_diff <= SUM_TOLERANCE else " ≠ ") + f"{e.gross}"
    detail += f"; {e.net} × {_pct(e.vat_rate)} = {e.net * e.vat_rate:.2f} vs VAT {e.vat}"
    comps.append(_component("arithmetic", W, ok, detail))

    legal = e.vat_rate in VAT_RATES
    comps.append(_component("vat_rate_legal", W, legal,
                            f"{_pct(e.vat_rate)} {'is' if legal else 'is not'} a Swedish VAT rate (25/12/6/0 %)"))

    kb = knowledge.load()
    act = kb.activities.get(activity) if activity else None
    rates = list(expected_vat_rates) if expected_vat_rates else (list(act.vat_rates) if act else [])
    if e.doc_type == DocType.CUSTOMER_INVOICE or not rates:
        comps.append(_component("vat_activity", W, None, "no activity: VAT policy not applicable"))
    else:
        fits = e.vat_rate in rates
        allowed = "/".join(_pct(r) for r in sorted(rates, reverse=True))
        detail = f"{_pct(e.vat_rate)} {'within' if fits else 'outside'} {allowed} for {activity or 'this vendor'}"
        if fits and len(rates) > 1:
            detail += " (several legal rates: ambiguous, not guessed)"
        comps.append(_component("vat_activity", W, fits, detail))

    missing = [] if e.vendor.strip() else ["vendor"]
    if e.gross == 0:
        missing.append("gross amount")
    if e.doc_type != DocType.RECEIPT and not (e.invoice_number or "").strip():
        missing.append("invoice number")
    comps.append(_component("required_fields", W, not missing,
                            f"missing {', '.join(missing)}" if missing else f"all required fields present for {e.doc_type.value}"))

    ids = _identifiers(e)
    if ids:
        good = sum(ok for *_, ok in ids)
        detail = "; ".join(f"{kind} {val} {'valid' if ok else 'fails'} checksum" for kind, val, ok in ids)
        comps.append(_component("identifier_checksum", W, good == len(ids), detail))  # one bad id fails the check
    else:
        comps.append(_component("identifier_checksum", W, None, "no org nr, bankgiro, OCR or IBAN to check"))

    problems = []
    if e.date > received + timedelta(days=MAX_DAYS_AFTER_RECEIPT):
        problems.append(f"dated {e.date}, after receipt on {received}")
    if e.due_date and not e.date <= e.due_date <= e.date + timedelta(days=MAX_PAYMENT_TERMS_DAYS):
        problems.append(f"due {e.due_date} not within {MAX_PAYMENT_TERMS_DAYS} days after {e.date}")
    comps.append(_component("date_plausible", W, not problems,
                            "; ".join(problems) or f"dated {e.date}, received {received}"
                            + (f", due {e.due_date}" if e.due_date else "")))

    comps.append(_component("model_self_report", W, e.confidence >= MODEL_PASS,
                            f"model reported {e.confidence:.2f}", e.confidence))

    from lovelight.classify import same_key

    key = vendor_key or knowledge.vendor_key(e.vendor, None, e.vendor_org_nr)
    past = [h for h in (history.entries if history else []) if same_key(h.vendor_key, h.vendor, key, e.vendor)]
    if e.doc_type == DocType.CUSTOMER_INVOICE or not past:
        comps.append(_component("vendor_history", W, None, "no posted history for this vendor"))
    else:
        counts = Counter(h.account for h in past)
        share = counts[account] / len(past)
        seen = ", ".join(f"{a} ×{n}" for a, n in counts.most_common())
        comps.append(_component("vendor_history", W, share >= 0.5,
                                f"account {account} vs history {seen} ({len(past)} posted)", share))

    gates = EXTRACTION_GATES
    cls = classification
    if cls is None or e.doc_type == DocType.CUSTOMER_INVOICE:
        comps.append(_component("classification", W, None, "no classification to check"))
    else:
        problems = []
        if cls.source == "fallback":
            problems.append("account is a fallback guess (unknown vendor and activity)")
            gates = (*gates, "classification")
        if not cls.policy_consistent:
            problems.append(f"{cls.account} is outside the activity policy" if cls.activity
                            else "no activity policy confirms the account")
        if not kb.is_cost(cls.account):
            problems.append(f"{cls.account} is not a cost account")
        comps.append(_component("classification", W, not problems, "; ".join(problems)
                                or f"{cls.account} fits activity '{cls.activity}' (source: {cls.source})"))

    return _aggregate(comps, gates)


# ---------- matching ----------


def score_match(doc: Document, tx: BankTx) -> Confidence:
    """Confidence that one bank transaction settles one document."""
    return score_group([doc], tx)


def score_group(docs: list[Document], tx: BankTx) -> Confidence:
    """Confidence that one bank transaction settles these documents together (1:N payments)."""
    from lovelight import matching

    W = MATCH_WEIGHTS
    expected = sum(matching.signed_sek(d) for d in docs)
    tol = sum(matching.tolerance(d) for d in docs)
    diff = abs(expected - float(tx.amount))
    comps = []
    if diff < 0.01:
        comps.append(_component("amount", W, True, f"{tx.amount} SEK equals documents' {expected:.2f} SEK"))
    elif diff <= tol:
        comps.append(_component("amount", W, True, f"{tx.amount} SEK within {tol:.2f} SEK of {expected:.2f} SEK "
                                                    "(rounding or FX spread)", 0.9))
    else:
        comps.append(_component("amount", W, False, f"{tx.amount} SEK vs {expected:.2f} SEK: partial or different "
                                                     "amount", 0.5 if abs(float(tx.amount)) < abs(expected) else 0.0))

    hits = [d for d in docs if matching.reference_hit(d, tx)]
    with_ref = [d for d in docs if d.extraction.ocr_reference or d.extraction.invoice_number]
    if hits:
        comps.append(_component("reference", W, True, f"bank reference quotes {len(hits)}/{len(docs)} document "
                                                      "reference(s)", len(hits) / len(docs)))
    elif with_ref and matching.ref_tokens(tx):
        comps.append(_component("reference", W, False, "bank reference does not match the document's OCR/invoice no"))
    else:
        comps.append(_component("reference", W, None, "no payment reference to compare"))

    name = min(matching.name_score(d.extraction.vendor, tx.text) for d in docs)
    comps.append(_component("name", W, name >= 0.8, f"'{tx.text}' vs '{docs[0].extraction.vendor}': {name:.2f}", name))

    gap = max(matching.date_gap(d, tx) for d in docs)
    window = matching.DATE_WINDOW_DAYS
    comps.append(_component("date", W, gap <= window, f"{gap} day(s) from document/due date (window {window})",
                            max(0.0, 1 - gap / window)))

    floor = ("floor:reference+amount", bool(hits) and len(hits) == len(docs) and diff <= tol, REFERENCE_AMOUNT_FLOOR)
    return _aggregate(comps, floors=[floor])
