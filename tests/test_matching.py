from datetime import date, datetime
from decimal import Decimal as D

from lovelight.matching import match
from lovelight.models import BankTx, DocType, Document, Extraction, Source


def doc(doc_id, vendor, gross, d, doc_type=DocType.SUPPLIER_INVOICE, currency="SEK", ocr=None):
    gross = D(gross)
    ext = Extraction(
        doc_type=doc_type, vendor=vendor, date=d, currency=currency, net=gross, vat_rate=D("0"), vat=D("0"),
        gross=gross, ocr_reference=ocr, suggested_account="5410", confidence=0.9,
    )
    return Document(id=doc_id, source=Source.UPLOAD, filename=f"{doc_id}.pdf", sha256=doc_id,
                    received_at=datetime(2026, 10, 1), extraction=ext)


def tx(tx_id, amount, d, text, ref=None):
    return BankTx(id=tx_id, date=d, amount=D(amount), text=text, reference=ref)


def test_alias_ocr_and_fx_matching():
    docs = [
        doc("sl", "Storstockholms Lokaltrafik", "1060.00", date(2026, 10, 1), DocType.RECEIPT),
        doc("aws", "Amazon Web Services EMEA SARL", "100.00", date(2026, 10, 3), currency="EUR"),
        doc("tele", "Telia Sverige AB", "499.00", date(2026, 10, 5), ocr="7712345678"),
        doc("decoy", "Telia Sverige AB", "499.00", date(2026, 9, 5)),
    ]
    txs = [
        tx("t1", "-1060.00", date(2026, 10, 2), "SL ACCESS"),
        tx("t2", "-1144.69", date(2026, 10, 20), "AWS EMEA"),
        tx("t3", "-499.00", date(2026, 10, 30), "BG 5050-1055", ref="7712345678"),
    ]
    ms = {m.bank_tx_id: m for m in match(docs, txs)}
    assert ms["t1"].document_ids == ["sl"]
    assert ms["t2"].document_ids == ["aws"]
    assert ms["t3"].document_ids == ["tele"] and ms["t3"].confidence >= 0.95


def test_one_payment_settles_several_invoices():
    docs = [
        doc("a", "Grafikbyrån Nord AB", "1250.00", date(2026, 9, 1)),
        doc("b", "Grafikbyrån Nord AB", "3750.00", date(2026, 9, 15)),
        doc("c", "Grafikbyrån Nord AB", "999.00", date(2026, 9, 20)),
    ]
    ms = match(docs, [tx("t9", "-5000.00", date(2026, 10, 1), "GRAFIKBYRAN NORD")])
    assert len(ms) == 1 and sorted(ms[0].document_ids) == ["a", "b"] and ms[0].id == "m-t9"
