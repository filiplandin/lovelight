"""Shared domain contract. All modules exchange these types; change only with coordination."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

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
    REJECTED = "rejected"


class Source(StrEnum):
    EMAIL = "email"
    UPLOAD = "upload"
    LIGHT_CSV = "light_csv"
    LIGHT_API = "light_api"


class ConfidenceComponent(BaseModel):
    """One deterministic check behind a confidence score."""

    name: str  # stable id, e.g. "arithmetic", "vat_rate_legal", "model_self_report"
    value: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    passed: bool | None = None  # None = not applicable; excluded from the weighted mean
    detail: str = ""  # human-readable evidence, e.g. "1000.00 + 60.00 = 1060.00"


class Confidence(BaseModel):
    """Explainable composite score: weighted mean of applicable components, then hard gates."""

    score: float = Field(ge=0, le=1)
    components: list[ConfidenceComponent]
    method: str  # e.g. "weighted_mean+gates"
    version: str  # scoring-rule version; bump when weights or checks change
    gates: list[str] = []  # names of failed hard gates that capped the score


class AccountCandidate(BaseModel):
    account: str  # BAS account, e.g. "5800"
    name: str = ""  # English account name, e.g. "Travel"
    probability: float = Field(ge=0, le=1)
    rationale: str = ""


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
    confidence: float = Field(ge=0, le=1)  # model self-report; the composite lives in confidence_detail.score
    injection_suspected: bool = False  # model saw instructions inside the document
    activity: str | None = None  # activity id from knowledge/activities.yaml, e.g. "local_transport"
    vendor_profile: str | None = None  # one line on what the vendor does
    account_candidates: list[AccountCandidate] = []  # model's ranked BAS options
    confidence_detail: Confidence | None = None  # set by code (confidence.score_extraction), never by the model


class KBMatch(BaseModel):
    """A knowledge-base vendor entry retrieved for a document."""

    entry_id: str
    vendor_name: str
    activity: str
    vendor_profile: str
    matched_on: Literal["org_nr", "alias", "bank_pattern", "email_domain"]
    matched_value: str  # the input text that matched
    score: float = Field(ge=0, le=1)
    vat_rates: list[Decimal] = []  # vendor-specific legal rates, narrower than the activity's; empty = activity's set


class Classification(BaseModel):
    """The BAS account the code chose, and why. Deterministic given (extraction, KB, history)."""

    account: str
    account_name: str
    activity: str | None = None
    source: Literal["correction", "policy", "model", "fallback"]
    rationale: str
    policy_consistent: bool
    overridden_model_account: str | None = None  # model's top account when policy or a correction overrode it
    expected_vat_rates: list[Decimal] = []
    vat_ambiguous: bool = False  # activity allows several legal rates (e.g. 6 % ride vs 25 % vehicle hire)


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
    kb_match: KBMatch | None = None
    classification: Classification | None = None


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
    confidence_detail: Confidence | None = None  # confidence == confidence_detail.score when set


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
    status: str = "proposed"  # proposed | posted | reversed | superseded | rejected
    reverses_id: str | None = None
    reverse_charge: str | None = None  # "eu" | "non_eu": self-assessed VAT on a foreign purchase (VAT boxes 21/22/30)
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


class Correction(BaseModel):
    """An accountant's account correction; feeds classification memory and KB proposals."""

    vendor: str
    account: str  # corrected BAS account
    previous_account: str
    date: date  # day the correction was made
    reason: str
    user: str
    document_id: str | None = None
    vendor_key: str | None = None  # knowledge.vendor_key: KB entry, org nr or exact normalized name
    org_nr: str | None = None


class HistoryEntry(BaseModel):
    """A posted cost document, as seen by classification and confidence."""

    vendor: str
    account: str
    vat_rate: Decimal
    date: date
    document_id: str | None = None
    vendor_key: str | None = None


class History(BaseModel):
    entries: list[HistoryEntry] = []
    corrections: list[Correction] = []


class AuditEvent(BaseModel):
    """One link in the append-only, hash-chained audit log.

    hash = sha256(prev_hash + canonical_json(event without "hash")), canonical_json = sorted keys, no spaces, UTF-8.
    """

    seq: int  # 1-based, gap-free
    ts: datetime
    actor: str  # "system" | "model:<id>" | "user:<name>"
    action: str  # e.g. "doc.received", "doc.extracted", "voucher.posted", "voucher.corrected"
    entity: str  # "document" | "voucher" | "match" | "books" | ...
    entity_id: str
    data: dict[str, Any] = {}
    input_sha256: str | None = None
    prev_hash: str  # "0" * 64 for seq 1
    hash: str
