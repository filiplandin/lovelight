"""Light (light.inc) AR export → customer-invoice Documents."""

from __future__ import annotations

import csv
import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lovelight.models import DocStatus, DocType, Document, Extraction, Source


def load_rows(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dec(s: str | None) -> Decimal | None:
    try:
        return Decimal((s or "").strip()) if (s or "").strip() else None
    except InvalidOperation:
        return None


def parse_date(s: str | None) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def invoice_date(row: dict) -> date | None:
    return parse_date(row.get("Invoice Date")) or parse_date(row.get("Effective Invoice Date"))


def _received_at(row: dict) -> datetime:
    s = (row.get("Created At") or "").replace("Z", "+00:00")
    return datetime.fromisoformat(s) if s else datetime(2026, 1, 1)


def to_documents(rows: list[dict]) -> list[Document]:
    docs = []
    for row in rows:
        gross, net, d = dec(row.get("Amount")), dec(row.get("Net Amount")), invoice_date(row)
        if gross is None or net is None or d is None or net <= 0 or gross < net:
            continue
        vat = gross - net
        ext = Extraction(
            doc_type=DocType.CUSTOMER_INVOICE,
            vendor=(row.get("Customer Name") or "").strip() or "Unknown customer",
            vendor_org_nr=(row.get("Customer Vat Number") or row.get("Customer Business Reg Number") or None),
            invoice_number=(row.get("Invoice Number") or "").strip() or None,
            date=d,
            due_date=parse_date(row.get("Due Date")),
            currency=(row.get("Currency") or "SEK").strip().upper(),
            net=net, vat=vat, gross=gross,
            vat_rate=(vat / net).quantize(Decimal("0.01")),
            suggested_account="3001",
            description=(row.get("Description") or "").strip(),
            confidence=1.0,
        )
        docs.append(Document(
            id=f"light-{row['ID']}", source=Source.LIGHT_CSV, filename=f"light:{ext.invoice_number or row['ID']}",
            sha256=hashlib.sha256(row["ID"].encode()).hexdigest(), received_at=_received_at(row),
            status=DocStatus.EXTRACTED, extraction=ext,
        ))
    return docs
