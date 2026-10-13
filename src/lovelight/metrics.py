"""In-process pipeline metrics: per-stage latency and per-outcome counters, served at /api/metrics."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager

STAGES = ("extract", "ledger", "match", "anomaly_scan")
COUNTS = (
    "received",
    "duplicate",
    "extracted",
    "posted",
    "pending_approval",
    "needs_review",
    "quarantined",
    "failed",
)
MAX_SAMPLES = 2048  # percentile window per stage; totals and max cover everything since reset

_STARTED = time.monotonic()


def _percentile(sorted_ms: list[float], q: float) -> float:
    """Nearest-rank percentile, so p50 <= p95 <= max always holds."""
    return sorted_ms[max(0, math.ceil(q * len(sorted_ms)) - 1)]


class _Stage:
    def __init__(self) -> None:
        self.count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0
        self.samples: deque[float] = deque(maxlen=MAX_SAMPLES)

    def add(self, ms: float) -> None:
        self.count += 1
        self.total_ms += ms
        self.max_ms = max(self.max_ms, ms)
        self.samples.append(ms)

    def snapshot(self) -> dict:
        s = sorted(self.samples)
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 1),
            "avg_ms": round(self.total_ms / self.count, 1) if self.count else 0.0,
            "p50_ms": round(_percentile(s, 0.50), 1) if s else 0.0,
            "p95_ms": round(_percentile(s, 0.95), 1) if s else 0.0,
            "max_ms": round(self.max_ms, 1),
        }


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._stages = {name: _Stage() for name in STAGES}
            self._counts = dict.fromkeys(COUNTS, 0)
            self._in_flight = 0
            self._max_in_flight = 0

    def incr(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1

    @contextmanager
    def timed(self, stage: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - t0) * 1000
            with self._lock:
                self._stages[stage].add(ms)

    @contextmanager
    def in_flight(self) -> Iterator[None]:
        with self._lock:
            self._in_flight += 1
            self._max_in_flight = max(self._max_in_flight, self._in_flight)
        try:
            yield
        finally:
            with self._lock:
                self._in_flight -= 1

    def snapshot(self, limit: int) -> dict:
        with self._lock:
            return {
                "stages": {name: st.snapshot() for name, st in self._stages.items()},
                "counts": dict(self._counts),
                "concurrency": {"limit": limit, "in_flight": self._in_flight, "max_in_flight": self._max_in_flight},
                "uptime_s": round(time.monotonic() - _STARTED, 1),
            }


METRICS = Metrics()
