"""SQLite persistence: one table per entity, each row holds the pydantic model as JSON.

The `audit` table is append-only: UPDATE and DELETE are refused by triggers and it is never reset.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "lovelight.db"
TABLES = ("documents", "bank", "matches", "vouchers", "anomalies", "files", "corrections")
# Survive store.reset(): the audit log, the model outputs it hashes, and pending knowledge-base proposals.
DURABLE_TABLES = ("model_outputs", "kb_proposals")

AUDIT_DDL = (
    "CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit "
    "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit "
    "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END",
)

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def connect(path: str | Path | None = None) -> None:
    global _conn
    path = Path(path or os.environ.get("LOVELIGHT_DB") or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    for t in (*TABLES, *DURABLE_TABLES):
        _conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    for ddl in AUDIT_DDL:
        _conn.execute(ddl)
    _conn.commit()


def _db() -> sqlite3.Connection:
    if _conn is None:
        connect()
    return _conn


def reset() -> None:
    with _lock:
        for t in TABLES:
            _db().execute(f"DELETE FROM {t}")
        _db().commit()


def put(table: str, obj: BaseModel) -> None:
    put_raw(table, obj.id, obj.model_dump_json())


def put_raw(table: str, id: str, data: str) -> None:
    with _lock:
        _db().execute(
            f"INSERT INTO {table} (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (id, data),
        )
        _db().commit()


def get_raw(table: str, id: str) -> str | None:
    with _lock:
        row = _db().execute(f"SELECT data FROM {table} WHERE id = ?", (id,)).fetchone()
    return row[0] if row else None


def all_raw(table: str) -> list[str]:
    with _lock:
        return [r[0] for r in _db().execute(f"SELECT data FROM {table} ORDER BY rowid").fetchall()]


@contextmanager
def locked() -> Iterator[sqlite3.Connection]:
    """The connection under the store lock, for multi-statement read-then-write transactions."""
    with _lock:
        con = _db()
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise


def get[M: BaseModel](table: str, id: str, cls: type[M]) -> M | None:
    with _lock:
        row = _db().execute(f"SELECT data FROM {table} WHERE id = ?", (id,)).fetchone()
    return cls.model_validate_json(row[0]) if row else None


def all[M: BaseModel](table: str, cls: type[M]) -> list[M]:
    with _lock:
        rows = _db().execute(f"SELECT data FROM {table} ORDER BY rowid").fetchall()
    return [cls.model_validate_json(r[0]) for r in rows]


def count(table: str) -> int:
    with _lock:
        return _db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def delete(table: str, id: str) -> None:
    with _lock:
        _db().execute(f"DELETE FROM {table} WHERE id = ?", (id,))
        _db().commit()


def put_file(doc_id: str, path: Path) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO files (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (doc_id, str(path)),
        )
        _db().commit()


def get_file(doc_id: str) -> Path | None:
    with _lock:
        row = _db().execute("SELECT data FROM files WHERE id = ?", (doc_id,)).fetchone()
    return Path(row[0]) if row else None
