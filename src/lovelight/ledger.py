"""Deterministic double-entry bookkeeping (BAS chart, Swedish VAT). The LLM never touches this math."""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from lovelight.models import BankTx, DocType, Document, Match, Voucher, VoucherLine

if TYPE_CHECKING:
    from lovelight.knowledge import KnowledgeBase

# Fixed demo rates (SEK per unit). FX revaluation is out of scope.
FX_TO_SEK: dict[str, Decimal] = {
    "SEK": Decimal("1"),
    "EUR": Decimal("11.25"),
    "USD": Decimal("10.60"),
    "GBP": Decimal("13.40"),
    "DKK": Decimal("1.505"),
    "NOK": Decimal("1.00"),
}

BANK = "1930"
AR = "1510"
AP = "2440"
INPUT_VAT = "2640"
OUTPUT_VAT = "2611"
RC_OUTPUT_VAT = "2614"  # output VAT, reverse charge (self-assessed on purchases from abroad)
RC_INPUT_VAT = "2645"  # input VAT on purchases from abroad
RC_RATE = Decimal("0.25")
EU_COUNTRIES = frozenset(
    "AT BE BG CY CZ DE DK EE ES FI FR GR EL HR HU IE IT LT LU LV MT NL PL PT RO SI SK".split()
)  # Sweden excluded: a Swedish supplier never triggers reverse charge on services
SALES = "3001"
ROUNDING = "3740"
FX_GAIN = "3960"
FX_LOSS = "7960"
YEAR_RESULT = "2099"
REPORTED_STATUSES = {"posted", "reversed"}  # a reversed voucher was posted; its reversal offsets it
ZERO = Decimal("0")
ORE = Decimal("0.01")


class UnbalancedVoucher(ValueError):
    pass


def to_ore(x: Decimal) -> Decimal:
    return Decimal(x).quantize(ORE, rounding=ROUND_HALF_UP)


def to_sek(amount: Decimal, currency: str) -> Decimal:
    rate = FX_TO_SEK.get(currency.upper())
    if rate is None:
        raise ValueError(f"No demo FX rate for {currency}")
    return to_ore(Decimal(amount) * rate)


def _sek_parts(doc: Document) -> tuple[Decimal, Decimal, Decimal]:
    """(net, vat, gross) in SEK; vat is derived so net + vat == gross exactly."""
    e = doc.extraction
    gross = to_sek(e.gross, e.currency)
    net = to_sek(e.net, e.currency)
    return net, gross - net, gross


def _line(account: str, amount: Decimal) -> VoucherLine:
    """Positive amount = debit, negative = credit."""
    return VoucherLine(account=account, debit=amount if amount > 0 else ZERO, credit=-amount if amount < 0 else ZERO)


def _compact(entries: list[tuple[str, Decimal]]) -> list[VoucherLine]:
    return [_line(a, to_ore(x)) for a, x in entries if to_ore(x) != 0]


def reverse_charge_region(doc: Document, kb: KnowledgeBase) -> str | None:
    """'eu' | 'non_eu' | 'unknown' for a 0 % purchase under an activity that self-assesses VAT, else None.

    Country comes from the supplier's VAT id prefix, then its IBAN, then the knowledge-base vendor entry.
    Currency is never used: an Irish entity may bill in USD and a US entity in EUR.
    """
    e = doc.extraction
    activity = (doc.classification.activity if doc.classification else None) or e.activity
    act = kb.activities.get(activity) if activity else None
    if e.doc_type == DocType.CUSTOMER_INVOICE or e.vat_rate != 0 or not (act and act.reverse_charge_when_zero):
        return None
    country = None
    for ident in (e.vendor_org_nr, e.iban):
        if ident and (m := re.match(r"\s*([A-Za-z]{2})", ident)):
            country = m.group(1).upper()
            break
    if country is None and doc.kb_match:
        entry = next((v for v in kb.vendors if v.id == doc.kb_match.entry_id), None)
        country = entry.country.upper() if entry and entry.country else None
    if country is None:
        return "unknown"
    if country == "SE":
        return None
    return "eu" if country in EU_COUNTRIES else "non_eu"


def propose_voucher(
    doc: Document, number: int, model: str | None, prompt_version: str | None, kb: KnowledgeBase | None = None
) -> Voucher:
    """Voucher for one document. Cost documents book only the deductible share of input VAT to 2640/2645; the rest
    is part of the cost. A 0 % purchase from abroad under a reverse-charge activity adds D 2645 / C 2614 at 25 %."""
    e = doc.extraction
    if e is None:
        raise ValueError(f"Document {doc.id} has no extraction")
    net, vat, gross = _sek_parts(doc)
    rc = None
    if e.doc_type == DocType.CUSTOMER_INVOICE:
        entries = [(AR, gross), (SALES, -net), (OUTPUT_VAT, -vat)]
    else:
        if kb is None:
            from lovelight import knowledge

            kb = knowledge.load()
        account = e.suggested_account
        share = kb.input_vat_deductible(account)
        reclaim = to_ore(vat * share)
        counter = BANK if e.doc_type == DocType.RECEIPT else AP
        entries = [(account, net + vat - reclaim), (INPUT_VAT, reclaim), (counter, -gross)]
        if rc := reverse_charge_region(doc, kb):
            rc_vat = to_ore(net * RC_RATE)
            rc_reclaim = to_ore(rc_vat * share)
            entries += [(RC_INPUT_VAT, rc_reclaim), (account, rc_vat - rc_reclaim), (RC_OUTPUT_VAT, -rc_vat)]
    merged: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for a, x in entries:
        merged[a] += x
    label = " ".join(p for p in (e.vendor, e.invoice_number) if p)
    v = Voucher(
        id=f"V{number}", number=number, date=e.date, description=f"{e.doc_type.value.replace('_', ' ')}: {label}",
        lines=_compact(list(merged.items())), document_id=doc.id, model=model, prompt_version=prompt_version,
        reverse_charge=rc,
    )
    validate(v)
    return v


def payment_voucher(match: Match, docs: list[Document], tx: BankTx, number: int) -> Voucher | None:
    """Settle AP/AR against the bank. Receipts are already credited to 1930, so they need no payment voucher."""
    payable = [d for d in docs if d.extraction and d.extraction.doc_type != DocType.RECEIPT]
    if not payable:
        return None
    entries: list[tuple[str, Decimal]] = [(BANK, to_ore(tx.amount))]
    for d in payable:
        gross = _sek_parts(d)[2]
        if d.extraction.doc_type == DocType.SUPPLIER_INVOICE:
            entries.append((AP, gross))
        else:
            entries.append((AR, -gross))
    diff = -sum((x for _, x in entries), ZERO)  # positive = needs debit (loss), negative = needs credit (gain)
    if diff != 0:
        acct = ROUNDING if abs(diff) <= 1 else (FX_LOSS if diff > 0 else FX_GAIN)
        entries.append((acct, diff))
    merged: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for a, x in entries:
        merged[a] += x
    names = ", ".join(sorted({d.extraction.vendor for d in payable}))
    v = Voucher(
        id=f"V{number}", number=number, date=tx.date, description=f"payment: {names}",
        lines=_compact(list(merged.items())), bank_tx_id=tx.id,
        document_id=payable[0].id if len(payable) == 1 else None,
    )
    validate(v)
    return v


def validate(v: Voucher) -> None:
    if len(v.lines) < 2:
        raise UnbalancedVoucher(f"{v.id}: needs at least 2 lines")
    for ln in v.lines:
        if ln.debit < 0 or ln.credit < 0:
            raise UnbalancedVoucher(f"{v.id}: negative amount on {ln.account}")
    debit = sum((ln.debit for ln in v.lines), ZERO)
    credit = sum((ln.credit for ln in v.lines), ZERO)
    if debit != credit:
        raise UnbalancedVoucher(f"{v.id}: debit {debit} != credit {credit}")


def reverse(v: Voucher, number: int) -> Voucher:
    """Append-only correction: a posted mirror voucher with debit/credit swapped."""
    r = Voucher(
        id=f"V{number}", number=number, date=v.date, description=f"Reversal of #{v.number}: {v.description}",
        lines=[VoucherLine(account=ln.account, debit=ln.credit, credit=ln.debit) for ln in v.lines],
        document_id=v.document_id, bank_tx_id=v.bank_tx_id, status="posted", reverses_id=v.id,
        reverse_charge=v.reverse_charge,
    )
    validate(r)
    return r


def balances(vouchers: list[Voucher]) -> dict[str, Decimal]:
    """Debit-minus-credit per account over reportable vouchers."""
    out: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for v in vouchers:
        if v.status not in REPORTED_STATUSES:
            continue
        for ln in v.lines:
            out[ln.account] += ln.debit - ln.credit
    return dict(sorted(out.items()))


def pnl(vouchers: list[Voucher]) -> dict:
    b = balances(vouchers)
    revenue = to_ore(-sum((x for a, x in b.items() if a.startswith("3")), ZERO))
    expenses = {a: to_ore(x) for a, x in b.items() if a[0] in "45678" and x != 0}
    return {"revenue": revenue, "expenses": expenses, "result": to_ore(revenue - sum(expenses.values(), ZERO))}


def balance_sheet(vouchers: list[Voucher]) -> dict:
    b = balances(vouchers)
    assets = {a: to_ore(x) for a, x in b.items() if a.startswith("1") and x != 0}
    le = {a: to_ore(-x) for a, x in b.items() if a.startswith("2") and x != 0}
    result = pnl(vouchers)["result"]
    if result != 0:
        le[YEAR_RESULT] = le.get(YEAR_RESULT, ZERO) + result
    return {"assets": assets, "liabilities_equity": le}


def vat_return(vouchers: list[Voucher]) -> dict[str, Decimal]:
    """Swedish VAT return boxes: 05 sales, 10 output VAT, 21/22 reverse-charge purchase base (EU / non-EU),
    30 self-assessed output VAT, 48 input VAT, 49 VAT to pay (negative = refund)."""
    b = balances(vouchers)
    sales = to_ore(-sum((x for a, x in b.items() if a.startswith("30")), ZERO))
    output = to_ore(-sum((x for a, x in b.items() if a in ("2610", "2611", "2612", "2613")), ZERO))
    rc_output = to_ore(-b.get(RC_OUTPUT_VAT, ZERO))
    input_ = to_ore(sum((x for a, x in b.items() if a.startswith("264")), ZERO))
    base: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for v in vouchers:
        if v.status in REPORTED_STATUSES and v.reverse_charge:
            rc = sum((ln.credit - ln.debit for ln in v.lines if ln.account == RC_OUTPUT_VAT), ZERO)
            base[v.reverse_charge] += rc / RC_RATE
    out = {
        "05": sales, "10": output, "21": to_ore(base["eu"]), "22": to_ore(base["non_eu"]), "30": rc_output,
        "48": input_, "49": to_ore(output + rc_output - input_),
    }
    if base["unknown"]:
        out["rc_unassigned"] = to_ore(base["unknown"])  # supplier country unknown: box 21 or 22 decided on review
    return out


def validate_all(vouchers: list[Voucher]) -> str | None:
    """Id of the first reportable voucher that does not balance, else None."""
    for v in vouchers:
        if v.status in REPORTED_STATUSES:
            try:
                validate(v)
            except UnbalancedVoucher:
                return v.id
    return None
