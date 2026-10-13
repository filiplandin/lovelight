"""Read-only Light (light.inc) connector: customer invoices (AR) and bank transactions.

Unverified contract: Light's public API was not available to us. The base URL, paths, pagination
(`{"data": [...], "next_cursor": ...}` with `?cursor=`), page-size parameter and JSON field names
(the Light CSV export columns in camelCase) are our assumptions, kept as module constants so they
can be corrected in one place. The client is tested only against httpx.MockTransport, never
against the live service.

Read-only by construction: `request` refuses every method except GET before any I/O happens.

CLI: `uv run python -m lovelight.connectors.light sync --dry-run` fetches and prints counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

import httpx

from lovelight.light_csv import dec, parse_date
from lovelight.models import BankTx, DocStatus, DocType, Document, Extraction, Source

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.light.inc"  # assumption, unverified
INVOICES_PATH = "/v1/invoices/receivable"  # assumption, unverified
BANK_PATH = "/v1/bank/transactions"  # assumption, unverified
PAGE_SIZE_PARAM = "limit"  # assumption, unverified
CURSOR_PARAM = "cursor"
TIMEOUT_S = 20.0
REVENUE_ACCOUNT = "3001"
ID_PREFIX = "light-api-"


class ReadOnlyViolation(Exception):
    """Raised when code attempts a non-GET request through the read-only client."""


def _row_sha256(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _received_at(row: dict[str, Any], fallback_day) -> datetime:
    created = (row.get("createdAt") or "").replace("Z", "+00:00")
    return datetime.fromisoformat(created) if created else datetime.combine(fallback_day, time(), UTC)


def invoice_to_document(row: dict[str, Any]) -> Document | None:
    """Map one invoice record; None when amounts or dates are unusable (same rule as the CSV import)."""
    gross, net, day = dec(row.get("amount")), dec(row.get("netAmount")), parse_date(row.get("invoiceDate"))
    if gross is None or net is None or day is None or net <= 0 or gross < net:
        return None
    vat = gross - net
    number = (row.get("invoiceNumber") or "").strip() or None
    ext = Extraction(
        doc_type=DocType.CUSTOMER_INVOICE,
        vendor=(row.get("customerName") or "").strip() or "Unknown customer",
        vendor_org_nr=row.get("customerVatNumber") or row.get("customerBusinessRegNumber") or None,
        invoice_number=number,
        date=day,
        due_date=parse_date(row.get("dueDate")),
        currency=(row.get("currency") or "SEK").strip().upper(),
        net=net,
        vat=vat,
        gross=gross,
        vat_rate=(vat / net).quantize(Decimal("0.01")),
        suggested_account=REVENUE_ACCOUNT,
        description=(row.get("description") or "").strip(),
        confidence=1.0,  # structured system-of-record data, not a model reading
    )
    return Document(
        id=f"{ID_PREFIX}{row['id']}",
        source=Source.LIGHT_API,
        filename=f"light-api:{number or row['id']}",
        sha256=_row_sha256(row),
        received_at=_received_at(row, day),
        status=DocStatus.EXTRACTED,
        extraction=ext,
    )


def bank_row_to_tx(row: dict[str, Any]) -> BankTx:
    return BankTx(
        id=f"{ID_PREFIX}{row['id']}",
        date=parse_date(row["date"]),
        amount=Decimal(str(row["amount"])),
        currency=(row.get("currency") or "SEK").strip().upper(),
        text=row.get("text") or "",
        reference=row.get("reference") or None,
    )


class LightClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        page_size: int = 100,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self._http = httpx.Client(
            base_url=self.base_url, auth=httpx.BasicAuth(api_key, ""), transport=transport, timeout=TIMEOUT_S
        )

    def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict:
        if method.upper() != "GET":
            raise ReadOnlyViolation(f"{method.upper()} {path} refused: the Light connector is read-only")
        resp = self._http.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        params: dict[str, Any] = {PAGE_SIZE_PARAM: self.page_size}
        while True:
            page = self.request("GET", path, params)
            rows += page.get("data") or []
            cursor = page.get("next_cursor")
            if not cursor:
                return rows
            params = {PAGE_SIZE_PARAM: self.page_size, CURSOR_PARAM: cursor}

    def invoices(self) -> list[Document]:
        rows = self._paginate(INVOICES_PATH)
        docs = [d for d in map(invoice_to_document, rows) if d is not None]
        if skipped := len(rows) - len(docs):
            log.warning("skipped %d Light invoice(s) with unusable amounts or dates", skipped)
        return docs

    def bank_transactions(self) -> list[BankTx]:
        return [bank_row_to_tx(r) for r in self._paginate(BANK_PATH)]


def from_env() -> LightClient | None:
    """Client from LIGHT_API_KEY (+ optional LIGHT_API_URL); None when no key is configured."""
    key = os.environ.get("LIGHT_API_KEY")
    if not key:
        return None
    return LightClient(key, base_url=os.environ.get("LIGHT_API_URL") or DEFAULT_BASE_URL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lovelight.connectors.light", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="fetch invoices and bank transactions from Light")
    sync.add_argument("--dry-run", action="store_true", help="fetch and report counts; write nothing")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print("Only --dry-run is implemented: posting API data goes through the audited pipeline (roadmap).")
        return 2

    from dotenv import load_dotenv

    from lovelight.store import ROOT

    load_dotenv(ROOT / ".env")
    client = from_env()
    if client is None:
        print("Light connector disabled: LIGHT_API_KEY is not set. Nothing fetched. See .env.example.")
        return 0
    invoices, bank = client.invoices(), client.bank_transactions()
    print(
        json.dumps(
            {"dry_run": True, "base_url": client.base_url, "invoices": len(invoices), "bank_transactions": len(bank)}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
