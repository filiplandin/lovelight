from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from lovelight.anomalies import scan_ar, scan_documents
from lovelight.light_csv import load_rows
from lovelight.models import AnomalyKind, BankTx, DocType, Document, Extraction, Source

CSV = Path(__file__).parents[1] / "data" / "invoiceReceivables.csv"


def test_planted_ar_anomalies_are_caught_from_data_fields():
    found = {(a.invoice_number, a.kind) for a in scan_ar(load_rows(CSV))}
    expected = {
        ("INV-FATFINGER-45M", AnomalyKind.AMOUNT_OUTLIER),
        ("INV-QTY-FATFINGER-009", AnomalyKind.AMOUNT_OUTLIER),
        ("INV-FX-JPY-USD-006", AnomalyKind.FX_SUSPICIOUS),
        ("INV-EPOCH-1970-005", AnomalyKind.DATE_INVALID),
        ("INV-YEAR-2099-004", AnomalyKind.DATE_INVALID),
        ("INV-INVERTED-DATE-003", AnomalyKind.DATE_INVALID),
        ("INV-PENNY-DIV0-002", AnomalyKind.ROUNDING),
        ("INV-SUBPENNIES-007", AnomalyKind.ROUNDING),
        ("INV-DUP-REVISED-010", AnomalyKind.DUPLICATE),
    }
    assert expected <= found
    flagged_normal = {n for n, _ in found if n and n.startswith("INVOICE#000") and n not in {"INVOICE#00099", "INVOICE#00056"}}
    assert not flagged_normal


def _doc(doc_id, vendor, gross, vat_rate, d, inv, bankgiro=None, injection=False, desc="Tryck"):
    gross, rate = D(gross), D(vat_rate)
    net = (gross / (1 + rate)).quantize(D("0.01"))
    ext = Extraction(doc_type=DocType.SUPPLIER_INVOICE, vendor=vendor, invoice_number=inv, date=d, net=net,
                     vat_rate=rate, vat=gross - net, gross=gross, bankgiro=bankgiro, suggested_account="5800",
                     description=desc, confidence=0.9, injection_suspected=injection)
    return Document(id=doc_id, source=Source.EMAIL, filename=f"{doc_id}.pdf", sha256=doc_id,
                    received_at=datetime(2026, 10, 1), extraction=ext)


def test_document_rules():
    docs = [
        _doc("a", "Byrå Nord AB", "5000.00", "0.25", date(2026, 9, 1), "101", bankgiro="123-4567"),
        _doc("b", "Byrå Nord AB", "5000.00", "0.25", date(2026, 9, 20), "102", bankgiro="999-0000"),
        _doc("rent1", "Fastighets AB", "9000.00", "0.25", date(2026, 8, 25), "H1", desc="Hyra september"),
        _doc("rent2", "Fastighets AB", "9000.00", "0.25", date(2026, 9, 25), "H2", desc="Hyra oktober"),
        _doc("c", "Taxi Stockholm", "318.00", "0.25", date(2026, 9, 5), "7"),
        _doc("d", "Hacker AB", "10.00", "0.25", date(2026, 9, 6), "8", injection=True),
    ]
    txs = [BankTx(id="t1", date=date(2026, 9, 9), amount=D("-1200"), text="CLAS OHLSON"),
           BankTx(id="t2", date=date(2026, 9, 9), amount=D("-25"), text="AVGIFT")]
    kinds = {(a.kind, a.document_id or a.bank_tx_id) for a in scan_documents(docs, txs, [])}
    assert kinds == {
        (AnomalyKind.DUPLICATE, "b"), (AnomalyKind.IBAN_CHANGE, "b"), (AnomalyKind.VAT_MISMATCH, "c"),
        (AnomalyKind.INJECTION, "d"), (AnomalyKind.MISSING_RECEIPT, "t1"),
    }
