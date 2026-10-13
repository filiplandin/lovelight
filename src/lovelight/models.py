"""Shared domain contract. All modules exchange these types; change only with coordination."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

CLIENT_NAME = "Lovelight Design AB"
CLIENT_ORG_NR = "559123-4567"
VAT_RATES = {Decimal("0.25"), Decimal("0.12"), Decimal("0.06"), Decimal("0")}


class DocType(StrEnum):
    RECEIPT = "receipt"
    SUPPLIER_INVOICE = "supplier_invoice"
    CUSTOMER_INVOICE = "customer_invoice"


class DocStatus(StrEnum):
    RECEIVED = "received"
    EXTRACTED = "extracted"
    MATCHED = "matched"
    POSTED = "posted"
    NEEDS_REVIEW = "needs_review"
    QUARANTINED = "quarantined"


class Source(StrEnum):
    EMAIL = "email"
    UPLOAD = "upload"
    LIGHT_CSV = "light_csv"


class Extraction(BaseModel):
    doc_type: DocType
    vendor: str  # counterparty: supplier for costs, customer for customer invoices
    vendor_org_nr: str | None = None
    invoice_number: str | None = None
    date: date
    due_date: date | None = None
    currency: str = "SEK"
    net: Decimal
    vat_rate: Decimal  # 0.25 / 0.12 / 0.06 / 0
    vat: Decimal
    gross: Decimal
    bankgiro: str | None = None
    iban: str | None = None
    ocr_reference: str | None = None
    suggested_account: str  # BAS account, e.g. "5800"
    description: str = ""
    confidence: float = Field(ge=0, le=1)
    injection_suspected: bool = False  # model saw instructions inside the document


class Document(BaseModel):
    id: str
    source: Source
    filename: str
    sha256: str
    sender: str | None = None
    received_at: datetime
    status: DocStatus = DocStatus.RECEIVED
    extraction: Extraction | None = None
    note: str | None = None  # review/quarantine reason


class BankTx(BaseModel):
    id: str
    date: date
    amount: Decimal  # signed SEK: negative = money out
    currency: str = "SEK"
    text: str
    reference: str | None = None


class Match(BaseModel):
    id: str
    bank_tx_id: str
    document_ids: list[str]  # 1:N supported
    confidence: float
    method: str  # e.g. "amount+date+name", "ocr_reference"
    approved: bool = False


class VoucherLine(BaseModel):
    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class Voucher(BaseModel):
    id: str
    number: int
    date: date
    description: str
    lines: list[VoucherLine]
    document_id: str | None = None
    bank_tx_id: str | None = None
    status: str = "proposed"  # proposed | posted | reversed
    reverses_id: str | None = None
    model: str | None = None
    prompt_version: str | None = None


class AnomalyKind(StrEnum):
    DUPLICATE = "duplicate"
    IBAN_CHANGE = "iban_change"
    INJECTION = "injection"
    MISSING_RECEIPT = "missing_receipt"
    VAT_MISMATCH = "vat_mismatch"
    AMOUNT_OUTLIER = "amount_outlier"
    DATE_INVALID = "date_invalid"
    FX_SUSPICIOUS = "fx_suspicious"
    ROUNDING = "rounding"


class Anomaly(BaseModel):
    id: str
    kind: AnomalyKind
    severity: str  # "high" | "medium" | "low"
    title: str
    explanation: str
    rule: str  # deterministic rule that fired
    document_id: str | None = None
    bank_tx_id: str | None = None
    invoice_number: str | None = None
