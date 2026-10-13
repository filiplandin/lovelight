"""Read-only Light connector (AR invoices + bank transactions), tested against httpx.MockTransport. No network.

Contract (lovelight.connectors.light):
- LightClient(api_key, base_url=DEFAULT_BASE_URL, transport=None, page_size=100)
- LightClient.request(method, path, params=None) -> dict   (raises ReadOnlyViolation for any method but GET)
- LightClient.invoices() -> list[Document]      GET INVOICES_PATH, cursor pagination
- LightClient.bank_transactions() -> list[BankTx]   GET BANK_PATH, cursor pagination
- Pages: {"data": [...], "next_cursor": str | None}; next page via query param "cursor".
- Auth: HTTP Basic, API key as username, empty password.
- from_env() -> LightClient | None   (None when LIGHT_API_KEY is unset; LIGHT_API_URL overrides the base URL)
"""

import base64
from datetime import date
from decimal import Decimal

import httpx
import pytest

from lovelight.connectors import light
from lovelight.models import BankTx, DocType, Document, Source

KEY = "test-light-key"

INVOICES = [
    {"id": "inv-1", "invoiceNumber": "INVOICE#00100", "customerName": "Onyx International AB", "amount": "12500.00",
     "netAmount": "10000.00", "currency": "SEK", "invoiceDate": "2026-09-01", "dueDate": "2026-10-01",
     "state": "OPEN", "description": "Design retainer September"},
    {"id": "inv-2", "invoiceNumber": "INVOICE#00101", "customerName": "Aurora Capital ApS", "amount": "1000.00",
     "netAmount": "1000.00", "currency": "EUR", "invoiceDate": "2026-09-15", "dueDate": "2026-10-15",
     "state": "PAID", "description": "Workshop"},
]
BANK = [
    {"id": "bt-1", "date": "2026-09-08", "amount": "12500.00", "currency": "SEK", "text": "BG INB ONYX",
     "reference": "INVOICE#00100"},
    {"id": "bt-2", "date": "2026-09-09", "amount": "-349.00", "currency": "SEK", "text": "CARD PURCHASE",
     "reference": None},
]


def _transport(seen: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "GET"
        rows = INVOICES if request.url.path.endswith(light.INVOICES_PATH) else BANK
        cursor = int(request.url.params.get("cursor") or 0)
        nxt = cursor + 1 if cursor + 1 < len(rows) else None
        return httpx.Response(200, json={"data": rows[cursor:cursor + 1], "next_cursor": str(nxt) if nxt else None})

    return httpx.MockTransport(handler)


@pytest.fixture
def client_and_requests():
    seen: list[httpx.Request] = []
    return light.LightClient(KEY, base_url="https://light.test", transport=_transport(seen), page_size=1), seen


def test_basic_auth_header(client_and_requests):
    client, seen = client_and_requests
    client.invoices()
    scheme, token = seen[0].headers["Authorization"].split(" ", 1)
    assert scheme == "Basic" and base64.b64decode(token).decode() == f"{KEY}:"


def test_invoices_paginate_and_map_to_documents(client_and_requests):
    client, seen = client_and_requests
    docs = client.invoices()
    assert len(seen) == 2 and seen[1].url.params["cursor"] == "1"
    assert [type(d) for d in docs] == [Document, Document]
    d = docs[0]
    assert d.source == Source.LIGHT_API and d.id == "light-api-inv-1"
    e = d.extraction
    assert e.doc_type == DocType.CUSTOMER_INVOICE and e.vendor == "Onyx International AB"
    assert (e.net, e.vat, e.gross) == (Decimal("10000.00"), Decimal("2500.00"), Decimal("12500.00"))
    assert e.vat_rate == Decimal("0.25") and e.suggested_account == "3001"
    assert e.date == date(2026, 9, 1) and e.due_date == date(2026, 10, 1)
    assert docs[1].extraction.currency == "EUR"


def test_bank_transactions_map_to_banktx(client_and_requests):
    client, _ = client_and_requests
    txs = client.bank_transactions()
    assert [type(t) for t in txs] == [BankTx, BankTx]
    assert txs[0].amount == Decimal("12500.00") and txs[0].reference == "INVOICE#00100"
    assert txs[1].amount == Decimal("-349.00") and txs[1].reference is None


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_refuses_writes(client_and_requests, method):
    client, seen = client_and_requests
    with pytest.raises(light.ReadOnlyViolation):
        client.request(method, light.INVOICES_PATH)
    assert not seen, "a refused write must never reach the network"


def test_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("LIGHT_API_KEY", raising=False)
    assert light.from_env() is None
    monkeypatch.setenv("LIGHT_API_KEY", KEY)
    monkeypatch.setenv("LIGHT_API_URL", "https://light.test")
    c = light.from_env()
    assert isinstance(c, light.LightClient) and c.base_url == "https://light.test"


def test_http_errors_propagate():
    t = httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "unauthorized"}))
    client = light.LightClient(KEY, base_url="https://light.test", transport=t)
    with pytest.raises(httpx.HTTPStatusError):
        client.invoices()
