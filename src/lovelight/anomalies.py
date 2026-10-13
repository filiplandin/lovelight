"""Deterministic anomaly rules. Every finding names the rule that fired so an accountant can audit it."""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal
from statistics import median

from rapidfuzz import fuzz

from lovelight import knowledge
from lovelight.ledger import FX_TO_SEK, to_sek
from lovelight.light_csv import dec, invoice_date, parse_date
from lovelight.models import VAT_RATES, Anomaly, AnomalyKind, BankTx, DocType, Document, Match, Source

DUPLICATE_WINDOW_DAYS = 45
BANK_FEE_LIMIT = Decimal("50")
NO_DOC_TEXT_RE = re.compile(r"skatt|\bskv\b|\bl[oö]n\b|avgift|kortavg|\bfee\b|prispaket", re.I)
VAT_TOLERANCE = Decimal("0.05")
INJECTION_RE = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|disregard .{0,30}instructions|system prompt"
    r"|you are now|approve (this|the) (invoice|payment)|mark (this|it) as (paid|approved)|change .{0,20}(iban|bankgiro)"
    r"|<\s*/?\s*(system|instruction)",
    re.I,
)
AR_CURRENCIES = {"SEK", "EUR", "USD", "GBP", "DKK", "NOK"}
CURRENCY_HINTS = {"JPY": r"¥|\bJPY\b|\byen\b", "USD": r"\$|\bUSD\b", "EUR": r"€|\bEUR\b", "GBP": r"£|\bGBP\b"}
OUTLIER_MULTIPLE = 10
OUTLIER_ABS_SEK = Decimal("10000000")
DUP_HINT_RE = re.compile(r"\b(resubmi\w*|revised|duplicate|re-?issued|copy)\b", re.I)


def _same_vendor(a: str, b: str) -> bool:
    return fuzz.token_set_ratio(a.lower(), b.lower()) >= 90


def _fmt(x: Decimal, cur: str = "SEK") -> str:
    return f"{x:,.2f} {cur}".replace(",", " ")


def scan_documents(docs: list[Document], txs: list[BankTx], matches: list[Match]) -> list[Anomaly]:
    out: list[Anomaly] = []
    docs = [d for d in docs if d.extraction is not None and d.source != Source.LIGHT_CSV]
    by_date = sorted(docs, key=lambda d: (d.extraction.date, d.id))

    for i, a in enumerate(by_date):
        for b in by_date[i + 1:]:
            ea, eb = a.extraction, b.extraction
            if (eb.date - ea.date).days > DUPLICATE_WINDOW_DAYS:
                break
            if not _same_vendor(ea.vendor, eb.vendor):
                continue
            same_file = a.sha256 == b.sha256
            # Recurring charges (rent, subscriptions) share amount but not description, so require both.
            same_desc = fuzz.ratio(ea.description.lower(), eb.description.lower()) >= 90
            if same_file or (ea.gross == eb.gross and ea.invoice_number != eb.invoice_number and same_desc):
                how = "the exact same file was submitted twice" if same_file else (
                    f"invoice numbers differ ({ea.invoice_number or '—'} vs {eb.invoice_number or '—'})")
                out.append(Anomaly(
                    id=f"a-dup-{b.id}", kind=AnomalyKind.DUPLICATE, severity="high",
                    title=f"Possible duplicate: {eb.vendor} {_fmt(eb.gross, eb.currency)}",
                    explanation=f"Same supplier and amount as {a.filename} within {DUPLICATE_WINDOW_DAYS} days, "
                                f"but {how}. Paying both would double-pay the supplier.",
                    rule=f"duplicate: same vendor+gross+description within {DUPLICATE_WINDOW_DAYS}d with different invoice no, or same sha256",
                    document_id=b.id, invoice_number=eb.invoice_number,
                ))

    seen: dict[str, tuple[Document, str]] = {}
    for d in by_date:
        e = d.extraction
        acct = (e.iban or e.bankgiro or "").replace(" ", "")
        if not acct:
            continue
        key = next((k for k in seen if _same_vendor(k, e.vendor)), e.vendor)
        if key in seen and seen[key][1] != acct:
            prev = seen[key][0]
            out.append(Anomaly(
                id=f"a-iban-{d.id}", kind=AnomalyKind.IBAN_CHANGE, severity="high",
                title=f"Payment details changed for {e.vendor}",
                explanation=f"{d.filename} asks for payment to {acct}, but {prev.filename} used {seen[key][1]}. "
                            "Verify the change by phone with a known contact before paying — classic invoice fraud.",
                rule="iban_change: bankgiro/IBAN differs from earlier document of same vendor",
                document_id=d.id, invoice_number=e.invoice_number,
            ))
        seen[key] = (d, acct)

    for d in docs:
        e = d.extraction
        if e.injection_suspected or (d.note and INJECTION_RE.search(d.note)):
            out.append(Anomaly(
                id=f"a-inj-{d.id}", kind=AnomalyKind.INJECTION, severity="high",
                title=f"Hidden instructions in {d.filename}",
                explanation="The document contains text addressed to an AI system rather than a human reader. "
                            "It was quarantined and nothing was posted; review the original before trusting any field.",
                rule="injection: extraction.injection_suspected or instruction-like regex on raw text",
                document_id=d.id, invoice_number=e.invoice_number,
            ))
        out.extend(_vat_checks(d))

    matched_tx = {m.bank_tx_id for m in matches}
    for tx in txs:
        if tx.amount < 0 and tx.id not in matched_tx and -tx.amount >= BANK_FEE_LIMIT and not NO_DOC_TEXT_RE.search(tx.text):
            out.append(Anomaly(
                id=f"a-miss-{tx.id}", kind=AnomalyKind.MISSING_RECEIPT, severity="medium",
                title=f"Missing receipt: {tx.text} {_fmt(-tx.amount)}",
                explanation=f"Money left the account on {tx.date} but no receipt or invoice explains it. "
                            "Without a verification the cost is not deductible and VAT cannot be reclaimed.",
                rule=f"missing_receipt: outgoing tx >= {BANK_FEE_LIMIT} SEK without match (tax/salary/fee texts excluded)",
                bank_tx_id=tx.id,
            ))
    return out


def _expected_vat(d: Document) -> tuple[list[Decimal], str]:
    """Legal VAT rates for this document: classification, else a KB lookup, else the model's activity."""
    e = d.extraction
    if d.classification and d.classification.expected_vat_rates:
        return list(d.classification.expected_vat_rates), f"Activity '{d.classification.activity}'"
    kb = knowledge.load()
    hit = kb.lookup(vendor=e.vendor, org_nr=e.vendor_org_nr, email=d.sender)
    if hit:
        rates = hit.vat_rates or kb.activities[hit.activity].vat_rates
        return list(rates), f"{hit.vendor_name} ({hit.activity})"
    if e.activity in kb.activities:
        return list(kb.activities[e.activity].vat_rates), f"Activity '{e.activity}'"
    return [], ""


def _vat_checks(d: Document) -> list[Anomaly]:
    e = d.extraction
    problems = []
    if e.vat_rate not in VAT_RATES:
        problems.append(f"VAT rate {e.vat_rate:.0%} is not a Swedish rate (25/12/6/0 %).")
    rates, basis = _expected_vat(d)
    if e.doc_type != DocType.CUSTOMER_INVOICE and rates and e.vat_rate in VAT_RATES and e.vat_rate not in rates:
        allowed = "/".join(f"{r:.0%}" for r in sorted(rates, reverse=True))
        problems.append(f"{basis} carries {allowed} VAT, but {e.vat_rate:.0%} was charged.")
    if abs(e.net * e.vat_rate - e.vat) > VAT_TOLERANCE:
        problems.append(f"VAT {e.vat} does not equal net {e.net} × {e.vat_rate:.0%} = {e.net * e.vat_rate:.2f}.")
    if not problems:
        return []
    return [Anomaly(
        id=f"a-vat-{d.id}", kind=AnomalyKind.VAT_MISMATCH, severity="medium",
        title=f"VAT looks wrong on {e.vendor}", explanation=" ".join(problems) + " Check before reclaiming input VAT.",
        rule="vat_mismatch: rate in {25,12,6,0}; rate in the activity/vendor VAT policy; |net*rate-vat|<=0.05",
        document_id=d.id, invoice_number=e.invoice_number,
    )]


# ---------- Light AR export ----------

def _row_sek(row: dict) -> Decimal | None:
    amount, cur = dec(row.get("Amount")), (row.get("Currency") or "").upper()
    if amount is None or cur not in FX_TO_SEK:
        return None
    return to_sek(amount, cur)


INVOICE_NUMBER_RE = re.compile(r"[A-Za-z0-9-]+(#\d+)?")


def _ar(row: dict, kind: AnomalyKind, severity: str, title: str, explanation: str, rule: str) -> Anomaly:
    inv = (row.get("Invoice Number") or "").strip() or None
    return Anomaly(
        id=f"a-ar-{kind.value}-{row['ID']}", kind=kind, severity=severity, title=title, explanation=explanation,
        rule=rule, document_id=f"light-{row['ID']}", invoice_number=inv,
    )


def scan_ar(rows: list[dict]) -> list[Anomaly]:
    out: list[Anomaly] = []
    by_customer: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_customer[(r.get("Customer Name") or "").strip()].append(r)

    for r in rows:
        cust = (r.get("Customer Name") or "").strip()
        cur = (r.get("Currency") or "").strip().upper()
        amount, net = dec(r.get("Amount")), dec(r.get("Net Amount"))
        label = f"{cust} ({(r.get('Invoice Number') or '').strip() or 'draft'})"
        sek = _row_sek(r)

        # Amount outliers: absolute ceiling, or >10x this customer's typical invoice.
        if sek is not None and amount and amount > 0:
            peers = [s for p in by_customer[cust] if p is not r and (s := _row_sek(p)) and s > 0]
            typical = Decimal(median(peers)) if len(peers) >= 2 else None
            if sek > OUTLIER_ABS_SEK or (typical and sek > OUTLIER_MULTIPLE * typical):
                ctx = f"about {sek / typical:.0f}× this customer's typical invoice ({_fmt(to_sek_back(typical, cur), cur)})" \
                    if typical else f"above the {_fmt(OUTLIER_ABS_SEK)} sanity ceiling"
                out.append(_ar(r, AnomalyKind.AMOUNT_OUTLIER, "high" if sek > Decimal("1000000") else "medium", f"Implausible amount: {_fmt(amount, cur)} to {label}",
                               f"This invoice is {ctx}. Likely extra zeros or a quantity typo — confirm before sending.",
                               "amount_outlier: >10M SEK or >10x customer median"))

        # Malformed invoice number: whitespace, slashes or stray characters break matching and reference lookups.
        raw_inv = r.get("Invoice Number") or ""
        if raw_inv and not INVOICE_NUMBER_RE.fullmatch(raw_inv):
            out.append(_ar(r, AnomalyKind.ROUNDING, "medium", f"Malformed invoice number {raw_inv.strip()!r}",
                           "The invoice number contains whitespace, slashes or stray characters. Customers will quote "
                           "it inconsistently and payments will not match; reissue with a clean number.",
                           "malformed_invoice_number: not [A-Za-z0-9-]+ (optionally #digits)"))

        # Zero / near-zero / rounding.
        if amount is not None and amount <= Decimal("1"):
            out.append(_ar(r, AnomalyKind.ROUNDING, "medium", f"Near-zero invoice: {_fmt(amount, cur)} to {label}",
                           "An invoice for (almost) nothing is usually a test or a waived fee entered as a charge. "
                           "Void it or issue a proper credit instead.",
                           "rounding: amount <= 1 unit"))
        elif amount is not None and net is not None and net > 0 and amount > net:
            vat = amount - net
            if amount % 1 == Decimal("0.99") and net % 1 == Decimal("0.99"):
                out.append(_ar(r, AnomalyKind.ROUNDING, "low", f"Back-calculated totals on {label}",
                               f"Net {net} and total {amount} both end in .99: the net was likely derived from a target "
                               "price, so per-line VAT rounding can drift by fractions of a cent. Recompute from line items.",
                               "rounding: net and gross both end in .99"))
            elif Decimal("0.005") <= min(abs(net * r_ - vat) for r_ in VAT_RATES) <= Decimal("0.02"):
                out.append(_ar(r, AnomalyKind.ROUNDING, "low", f"VAT off by a cent on {label}",
                               f"VAT {vat} differs from net × standard rate by about one cent — a rounding inconsistency.",
                               "rounding: |net*rate - vat| in [0.005, 0.02]"))

        # Impossible dates.
        inv_d, due_d = invoice_date(r), parse_date(r.get("Due Date"))
        for name, d in (("invoice date", inv_d), ("due date", due_d)):
            if d and not 2000 <= d.year <= 2030:
                out.append(_ar(r, AnomalyKind.DATE_INVALID, "high", f"Impossible {name} {d} on {label}",
                               f"A {name} in {d.year} cannot be right — likely a system default or a typo. "
                               "It would land in the wrong fiscal year.",
                               "date_invalid: year < 2000 or > 2030"))
                break
        else:
            if inv_d and due_d and due_d < inv_d:
                out.append(_ar(r, AnomalyKind.DATE_INVALID, "medium", f"Due before issued on {label}",
                               f"Due date {due_d} is {(inv_d - due_d).days} days before the invoice date {inv_d}; "
                               "the customer would be overdue on day one.",
                               "date_invalid: due_date < invoice_date"))

        # FX suspicious.
        desc = r.get("Description") or ""
        if cur and cur not in AR_CURRENCIES:
            out.append(_ar(r, AnomalyKind.FX_SUSPICIOUS, "medium", f"Unusual currency {cur} on {label}",
                           f"{cur} is not one of the company's invoicing currencies; check the currency field.",
                           "fx_suspicious: currency not in SEK/EUR/USD/GBP/DKK/NOK"))
        else:
            hinted = [c for c, rx in CURRENCY_HINTS.items() if c != cur and re.search(rx, desc)]
            if hinted:
                out.append(_ar(r, AnomalyKind.FX_SUSPICIOUS, "high", f"Currency mismatch on {label}",
                               f"The description refers to {', '.join(hinted)} but the invoice is booked in {cur}; "
                               "the amount was probably entered without converting.",
                               "fx_suspicious: description currency hint != invoice currency"))

    out.extend(_ar_duplicates(rows))
    return out


def to_sek_back(sek: Decimal, cur: str) -> Decimal:
    return (sek / FX_TO_SEK[cur]).quantize(Decimal("1"))


def _ar_duplicates(rows: list[dict]) -> list[Anomaly]:
    out = []
    seen: dict[tuple, dict] = {}
    for r in sorted(rows, key=lambda r: r.get("Created At") or ""):
        cust = (r.get("Customer Name") or "").strip()
        amount = dec(r.get("Amount"))
        desc = (r.get("Description") or "").strip()
        d = parse_date(r.get("Effective Invoice Date")) or invoice_date(r)
        if DUP_HINT_RE.search(desc):
            out.append(_ar(r, AnomalyKind.DUPLICATE, "high", f"Re-issued invoice without credit note: {cust}",
                           "The invoice says it replaces an earlier one, but nothing voids the original — "
                           "the customer may be billed twice. Issue a credit note for the old invoice.",
                           "duplicate: description indicates resubmission/revision"))
            continue
        if not amount or amount <= 0 or d is None:
            continue
        key = (cust, amount, desc, (r.get("Currency") or "").upper())
        prev = seen.get(key)
        if prev is not None:
            prev_d = parse_date(prev.get("Effective Invoice Date")) or invoice_date(prev)
            if prev_d and abs((d - prev_d).days) <= 7:
                prev_no = (prev.get("Invoice Number") or "").strip() or "an unnumbered draft"
                out.append(_ar(r, AnomalyKind.DUPLICATE, "high",
                               f"Duplicate invoice: {cust} {_fmt(amount, key[3])}",
                               f"Same customer, amount and description as {prev_no} dated {prev_d}. "
                               "Delete one before sending, or the customer is invoiced twice.",
                               "duplicate: same customer+amount+description within 7d"))
        seen[key] = r
    return out
