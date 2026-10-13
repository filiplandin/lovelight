from datetime import date, datetime
from decimal import Decimal as D

import pytest

from lovelight.ledger import (
    UnbalancedVoucher,
    balance_sheet,
    payment_voucher,
    pnl,
    propose_voucher,
    reverse,
    validate,
    vat_return,
)
from lovelight.models import BankTx, DocType, Document, Extraction, Match, Source, Voucher, VoucherLine


def make_doc(doc_type, net, vat, rate, account="5410", currency="SEK", doc_id="d1"):
    ext = Extraction(
        doc_type=doc_type, vendor="Kjell & Company", date=date(2026, 10, 1), currency=currency,
        net=D(net), vat_rate=D(rate), vat=D(vat), gross=D(net) + D(vat),
        suggested_account=account, confidence=0.9,
    )
    return Document(id=doc_id, source=Source.UPLOAD, filename="x.pdf", sha256="s",
                    received_at=datetime(2026, 10, 1), extraction=ext)


def lines(v):
    return {(ln.account, ln.debit, ln.credit) for ln in v.lines}


def test_receipt_credits_bank_and_splits_vat():
    v = propose_voucher(make_doc(DocType.RECEIPT, "100.00", "25.00", "0.25"), 1, "m", "v1")
    assert lines(v) == {("5410", D("100.00"), 0), ("2640", D("25.00"), 0), ("1930", 0, D("125.00"))}
    validate(v)


def test_customer_invoice_in_eur_is_converted_and_balanced():
    v = propose_voucher(make_doc(DocType.CUSTOMER_INVOICE, "1440.00", "360.00", "0.25", "3001", "EUR"), 2, None, None)
    debit = sum(ln.debit for ln in v.lines)
    assert debit == sum(ln.credit for ln in v.lines) == D("1800") * D("11.25")
    assert {ln.account for ln in v.lines} == {"1510", "3001", "2611"}


def test_supplier_payment_and_receipt_payment():
    inv = make_doc(DocType.SUPPLIER_INVOICE, "800.00", "200.00", "0.25", "6540")
    tx = BankTx(id="t1", date=date(2026, 10, 30), amount=D("-1000.00"), text="KJELL")
    m = Match(id="m-t1", bank_tx_id="t1", document_ids=["d1"], confidence=0.97, method="x")
    pv = payment_voucher(m, [inv], tx, 3)
    assert lines(pv) == {("2440", D("1000.00"), 0), ("1930", 0, D("1000.00"))}
    rec = make_doc(DocType.RECEIPT, "800.00", "200.00", "0.25")
    assert payment_voucher(m, [rec], tx, 4) is None


def test_validate_rejects_unbalanced():
    v = Voucher(id="v", number=1, date=date(2026, 1, 1), description="x",
                lines=[VoucherLine(account="1930", debit=D("1")), VoucherLine(account="3001", credit=D("2"))])
    with pytest.raises(UnbalancedVoucher):
        validate(v)


def test_reports_count_posted_only_and_reversal_nets_out():
    sale = propose_voucher(make_doc(DocType.CUSTOMER_INVOICE, "1000.00", "250.00", "0.25", "3001"), 1, None, None)
    cost = propose_voucher(make_doc(DocType.RECEIPT, "400.00", "100.00", "0.25", "5410", doc_id="d2"), 2, None, None)
    draft = propose_voucher(make_doc(DocType.RECEIPT, "999.00", "0", "0", "5410", doc_id="d3"), 3, None, None)
    sale.status = cost.status = "posted"
    vs = [sale, cost, draft]
    assert pnl(vs) == {"revenue": D("1000.00"), "expenses": {"5410": D("400.00")}, "result": D("600.00")}
    assert vat_return(vs) == {"05": D("1000.00"), "10": D("250.00"), "48": D("100.00"), "49": D("150.00")}
    bs = balance_sheet(vs)
    assert sum(bs["assets"].values()) == sum(bs["liabilities_equity"].values())
    rev = reverse(cost, 4)
    assert pnl(vs + [rev])["result"] == D("1000.00")
