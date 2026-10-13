from decimal import Decimal as D
from pathlib import Path

from lovelight.light_csv import load_rows, to_documents
from lovelight.models import DocType

CSV = Path(__file__).parents[1] / "data" / "invoiceReceivables.csv"


def test_light_export_converts_without_crashing():
    rows = load_rows(CSV)
    docs = to_documents(rows)
    assert 0 < len(docs) < len(rows)  # zero/unusable rows are skipped
    kund_b = next(d for d in docs if d.extraction.invoice_number == "INVOICE#00099")
    e = kund_b.extraction
    assert e.doc_type == DocType.CUSTOMER_INVOICE and e.vat == D("45418.75") and e.vat_rate == D("0.25")
