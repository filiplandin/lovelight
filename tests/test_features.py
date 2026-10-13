"""Acceptance tests for parallel batch ingest, /api/health and /api/metrics. No network.

Contract (builders implement against this):
- POST /api/upload runs extraction for the batch with bounded concurrency
  (`pipeline.MAX_CONCURRENCY`, default from env LOVELIGHT_MAX_CONCURRENCY); ledger writes stay serialized.
- GET /api/health -> {"status": "ok", "version": str, "docs": int, "vouchers": int,
                      "extraction_mode": "live" | "gold-cache"}
- GET /api/metrics -> see METRIC_STAGES / METRIC_COUNTS below; reset by POST /api/demo/reset.
"""

import re
import threading
import time
from collections import Counter
from datetime import date
from decimal import Decimal
from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient

from lovelight import extract
from lovelight.models import DocType, Extraction

TERMINAL = {"posted", "matched", "needs_review", "quarantined"}
METRIC_STAGES = {"extract", "ledger", "match", "anomaly_scan"}
STAGE_FIELDS = {"count", "total_ms", "p50_ms", "p95_ms", "max_ms"}
METRIC_COUNTS = {"received", "extracted", "posted", "needs_review", "quarantined", "failed"}
SLEEP_S = 0.25
N_FILES = 8


class FakeExtractor:
    """Blocking, sleep-based stand-in for extract.extract that records peak concurrency."""

    def __init__(self, sleep_s: float):
        self.sleep_s = sleep_s
        self.in_flight = 0
        self.peak = 0
        self.calls = 0
        self._lock = threading.Lock()

    def __call__(self, path, email_body=None):
        with self._lock:
            self.in_flight += 1
            self.calls += 1
            self.peak = max(self.peak, self.in_flight)
        try:
            time.sleep(self.sleep_s)
            i = int(re.search(r"rcpt_(\d+)", path.name).group(1))
            net = Decimal(f"{311 + i}.08")  # x.08 * 0.25 is exact to the öre
            vat = net * Decimal("0.25")
            return (
                Extraction(
                    doc_type=DocType.RECEIPT,
                    vendor=f"Testleverantör {i} AB",
                    date=date(2026, 10, 1),
                    net=net,
                    vat_rate=Decimal("0.25"),
                    vat=vat,
                    gross=net + vat,
                    suggested_account="6110",
                    activity="office_supplies",
                    confidence=0.99,
                ),
                "fake-model",
            )
        finally:
            with self._lock:
                self.in_flight -= 1


@pytest.fixture
def client(tmp_path, monkeypatch):
    from lovelight import pipeline, server  # import first: server load_dotenv() would refill env vars

    monkeypatch.setenv("LOVELIGHT_DB", str(tmp_path / "features.db"))
    for var in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "ANTHROPIC_API_KEY", "SENDER_ALLOWLIST"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(pipeline, "INCOMING", tmp_path / "incoming")
    with TestClient(server.app) as c:
        yield c


def _files(n: int, start: int = 0) -> list[tuple]:
    return [
        ("files", (f"rcpt_{i}.pdf", f"%PDF-1.4 receipt {i}".encode(), "application/pdf"))
        for i in range(start, start + n)
    ]


def _uploads(state: dict) -> list[dict]:
    return [d for d in state["documents"] if d["source"] == "upload"]


def _wait_until_done(client, n: int, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = client.get("/api/state").json()
        ups = _uploads(state)
        if len(ups) >= n and all(d["status"] in TERMINAL for d in ups):
            return state
        time.sleep(0.02)
    raise AssertionError(f"{n} uploads not processed within {timeout}s")


def _assert_balanced(state: dict) -> None:
    for v in state["vouchers"]:
        debit = sum(Decimal(str(line["debit"])) for line in v["lines"])
        credit = sum(Decimal(str(line["credit"])) for line in v["lines"])
        assert debit == credit, v["id"]


def _fingerprint(state: dict) -> dict:
    """Order-independent summary of the books: equal for sequential and parallel ingest."""
    return {
        "uploads": len(_uploads(state)),
        "vouchers": len(state["vouchers"]),
        "statuses": Counter(d["status"] for d in _uploads(state)),
        "voucher_statuses": Counter(v["status"] for v in state["vouchers"]),
        "anomaly_kinds": Counter(a["kind"] for a in state["anomalies"]),
        "reports": state["reports"],
    }


# ---------- (a) parallel batch ingest ----------


def test_batch_upload_extracts_concurrently_and_bounded(client, monkeypatch):
    from lovelight import pipeline

    fake = FakeExtractor(SLEEP_S)
    monkeypatch.setattr(extract, "extract", fake)

    t0 = time.monotonic()
    r = client.post("/api/upload", files=_files(N_FILES))
    assert r.status_code == 200 and r.json()["accepted"] == N_FILES
    state = _wait_until_done(client, N_FILES)
    wall = time.monotonic() - t0

    assert fake.calls == N_FILES
    assert wall < N_FILES * SLEEP_S * 0.6, f"batch took {wall:.2f}s; extraction is not overlapping"
    assert 2 <= fake.peak <= pipeline.MAX_CONCURRENCY, f"peak in-flight {fake.peak}"
    _assert_balanced(state)


def test_parallel_batch_books_equal_sequential(client, monkeypatch):
    monkeypatch.setattr(extract, "extract", FakeExtractor(0.05))

    client.post("/api/upload", files=_files(N_FILES))
    parallel = _wait_until_done(client, N_FILES)

    client.post("/api/demo/reset")
    for k, f in enumerate(_files(N_FILES), 1):
        client.post("/api/upload", files=[f])
        sequential = _wait_until_done(client, k)

    assert _fingerprint(parallel) == _fingerprint(sequential)
    numbers = [v["number"] for v in parallel["vouchers"]]
    assert len(numbers) == len(set(numbers)), "voucher numbers must stay unique under concurrency"
    _assert_balanced(parallel)


def test_identical_bytes_in_one_batch_become_one_document(client, monkeypatch):
    monkeypatch.setattr(extract, "extract", FakeExtractor(0.05))
    same = b"%PDF-1.4 receipt 1"
    files = [
        ("files", (name, same, "application/pdf")) for name in ("rcpt_1.pdf", "rcpt_1_copy.pdf", "rcpt_1_again.pdf")
    ]

    client.post("/api/upload", files=files)
    _wait_until_done(client, 1)
    time.sleep(0.3)  # let any racing duplicates land
    assert len(_uploads(client.get("/api/state").json())) == 1


# ---------- (b) health + metrics ----------


def test_health_contract(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == version("lovelight")
    state = client.get("/api/state").json()
    assert body["docs"] == len(state["documents"])
    assert body["vouchers"] == len(state["vouchers"])
    assert body["extraction_mode"] == "gold-cache"


def test_health_reports_live_mode_when_api_key_set(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    assert client.get("/api/health").json()["extraction_mode"] == "live"


def _assert_metrics_shape(m: dict) -> None:
    assert set(m) >= {"stages", "counts", "concurrency", "uptime_s"}
    assert set(m["stages"]) >= METRIC_STAGES
    for name in METRIC_STAGES:
        stage = m["stages"][name]
        assert set(stage) >= STAGE_FIELDS, name
        assert stage["count"] >= 0
        if stage["count"]:
            assert 0 <= stage["p50_ms"] <= stage["p95_ms"] <= stage["max_ms"] <= stage["total_ms"], name
    assert set(m["counts"]) >= METRIC_COUNTS
    assert set(m["concurrency"]) >= {"limit", "max_in_flight"}
    assert m["uptime_s"] >= 0


def test_metrics_shape_on_fresh_start(client):
    m = client.get("/api/metrics").json()
    _assert_metrics_shape(m)
    assert all(m["stages"][s]["count"] == 0 for s in METRIC_STAGES)
    assert all(v == 0 for k, v in m["counts"].items() if k in METRIC_COUNTS)


def test_metrics_track_batch_and_reset(client, monkeypatch):
    from lovelight import pipeline

    monkeypatch.setattr(extract, "extract", FakeExtractor(0.1))
    client.post("/api/upload", files=_files(3))
    _wait_until_done(client, 3)

    m = client.get("/api/metrics").json()
    _assert_metrics_shape(m)
    ex = m["stages"]["extract"]
    assert ex["count"] == 3
    assert ex["total_ms"] >= 3 * 100 * 0.9
    assert ex["max_ms"] >= 100 * 0.9
    assert m["counts"]["received"] == 3
    assert m["counts"]["extracted"] == 3
    assert m["counts"]["posted"] == 3
    assert m["counts"]["failed"] == 0
    assert m["concurrency"]["limit"] == pipeline.MAX_CONCURRENCY
    assert 1 <= m["concurrency"]["max_in_flight"] <= m["concurrency"]["limit"]

    client.post("/api/demo/reset")
    after = client.get("/api/metrics").json()
    assert after["stages"]["extract"]["count"] == 0
    assert after["counts"]["received"] == 0


def test_metrics_count_failed_extractions(client, monkeypatch):
    def boom(path, email_body=None):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(extract, "extract", boom)
    client.post("/api/upload", files=_files(2))
    _wait_until_done(client, 2)
    m = client.get("/api/metrics").json()
    assert m["counts"]["received"] == 2
    assert m["counts"]["failed"] == 2
