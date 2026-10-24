"""SQLite persistence and revision history for Qwantum QRAM 0.6."""
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any
from app.migrations import migrate_database


class SQLiteStore:
    """Small durable store: current cells plus append-only revision history."""

    def __init__(self, database_path: str = "data/qram.db", capacity: int = 1024):
        self.database_path = database_path
        self.capacity = capacity
        self._lock = RLock()
        db_path = Path(database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        migrate_database(self.database_path)

    def _validate_address(self, address: int):
        if not isinstance(address, int) or isinstance(address, bool):
            raise ValueError("address must be an integer")
        if address < 0 or address >= self.capacity:
            raise ValueError(f"address must be between 0 and {self.capacity - 1}")

    def write(self, address: int, value: str) -> dict[str, Any]:
        self._validate_address(address)
        if not isinstance(value, str) or not value:
            raise ValueError("value must be a non-empty string")
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT revision FROM cells WHERE address=?", (address,)).fetchone()
            revision = (row["revision"] if row else 0) + 1
            conn.execute("""
                INSERT INTO cells(address, value, revision, updated_at)
                VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                ON CONFLICT(address) DO UPDATE SET
                    value=excluded.value,
                    revision=excluded.revision,
                    updated_at=excluded.updated_at
            """, (address, value, revision))
            conn.execute(
                "INSERT INTO revisions(address, operation, value, revision) VALUES (?, 'write', ?, ?)",
                (address, value, revision),
            )
            return {"address": address, "value": value, "revision": revision, "written": True}

    def read(self, address: int) -> dict[str, Any]:
        self._validate_address(address)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT address, value, revision, updated_at FROM cells WHERE address=?", (address,)
            ).fetchone()
        if row is None:
            raise KeyError(f"address {address} is empty")
        return dict(row)

    def list_cells(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT address, value, revision, updated_at FROM cells ORDER BY address"
            ).fetchall()
        return [dict(row) for row in rows]

    def history(self, address: int, limit: int = 50) -> list[dict[str, Any]]:
        self._validate_address(address)
        limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, address, operation, value, revision, created_at
                FROM revisions WHERE address=? ORDER BY id DESC LIMIT ?
            """, (address, limit)).fetchall()
        return [dict(row) for row in rows]

    def reset(self) -> int:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT address, revision FROM cells").fetchall()
            for row in rows:
                next_revision = row["revision"] + 1
                conn.execute(
                    "INSERT INTO revisions(address, operation, value, revision) VALUES (?, 'delete', NULL, ?)",
                    (row["address"], next_revision),
                )
            count = len(rows)
            conn.execute("DELETE FROM cells")
            return count

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            used = conn.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
        return {"capacity": self.capacity, "used": used, "free": self.capacity - used}
