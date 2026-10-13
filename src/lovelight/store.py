"""SQLite persistence: one table per entity, each row holds the pydantic model as JSON."""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "lovelight.db"
TABLES = ("documents", "bank", "matches", "vouchers", "anomalies", "files")

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def connect(path: str | Path | None = None) -> None:
    global _conn
    path = Path(path or os.environ.get("LOVELIGHT_DB") or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    for t in TABLES:
        _conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
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
    with _lock:
        _db().execute(
            f"INSERT INTO {table} (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (obj.id, obj.model_dump_json()),
        )
        _db().commit()


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
