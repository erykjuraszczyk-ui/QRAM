"""SQLite-backed experiment registry with durable metadata and event history."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
from typing import Any
from app.migrations import migrate_database


class ExperimentNotFound(KeyError):
    pass


class ExperimentStore:
    def __init__(self, database_path: str = "data/qram.db"):
        self.database_path = database_path
        self._lock = RLock()
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        migrate_database(database_path)

    def _connect(self):
        conn = sqlite3.connect(self.database_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def create(self, experiment_id: str, label: str, qubits: int, shots: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute("""INSERT INTO experiments
                (experiment_id,label,qubits,shots,status,created_at,updated_at,result_json,error,backend,metadata_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (experiment_id, label, qubits, shots, "queued", now, now, None, None, None, json.dumps({"requested_qubits": qubits, "shots": shots})))
            conn.execute("INSERT INTO experiment_events(experiment_id,event_type,status,event_at,detail_json) VALUES (?,?,?,?,?)",
                         (experiment_id, "created", "queued", now, json.dumps({"label": label, "qubits": qubits, "shots": shots})))
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        if row is None:
            raise ExperimentNotFound(experiment_id)
        return self._to_dict(row)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC, experiment_id DESC LIMIT ?", (limit,)).fetchall()
        return [self._to_dict(row) for row in rows]

    def start_if_queued(self, experiment_id: str) -> dict[str, Any]:
        """Atomically claim a queued experiment so concurrent clients won't run it twice."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            cursor = conn.execute("UPDATE experiments SET status='running', updated_at=? WHERE experiment_id=? AND status='queued'", (now, experiment_id))
            if cursor.rowcount:
                conn.execute("INSERT INTO experiment_events(experiment_id,event_type,status,event_at,detail_json) VALUES (?,?,?,?,?)",
                             (experiment_id, "started", "running", now, None))
        return self.get(experiment_id)

    def update(self, experiment_id: str, *, status: str, result: dict | None = None,
               error: str | None = None, backend: str | None = None,
               metadata: dict | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        result_json = json.dumps(result, ensure_ascii=False) if result is not None else None
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None
        with self._lock, self._connect() as conn:
            current = conn.execute("SELECT experiment_id FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if current is None:
                raise ExperimentNotFound(experiment_id)
            conn.execute("""UPDATE experiments SET status=?, updated_at=?, result_json=?, error=?, backend=COALESCE(?, backend),
                           metadata_json=COALESCE(?, metadata_json) WHERE experiment_id=?""",
                         (status, now, result_json, error, backend, metadata_json, experiment_id))
            detail = {"error": error} if error else (metadata or {})
            conn.execute("INSERT INTO experiment_events(experiment_id,event_type,status,event_at,detail_json) VALUES (?,?,?,?,?)",
                         (experiment_id, "status_changed", status, now, json.dumps(detail, ensure_ascii=False)))
        return self.get(experiment_id)

    def history(self, experiment_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        if not self.exists(experiment_id):
            raise ExperimentNotFound(experiment_id)
        with self._connect() as conn:
            rows = conn.execute("SELECT id, experiment_id, event_type, status, event_at, detail_json FROM experiment_events WHERE experiment_id=? ORDER BY id DESC LIMIT ?", (experiment_id, limit)).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            raw = item.pop("detail_json")
            item["details"] = json.loads(raw) if raw else None
            output.append(item)
        return output

    def exists(self, experiment_id: str) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1 FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone() is not None

    @staticmethod
    def _to_dict(row) -> dict[str, Any]:
        result = dict(row)
        raw = result.pop("result_json", None)
        metadata_raw = result.pop("metadata_json", None)
        result["result"] = json.loads(raw) if raw else None
        result["metadata"] = json.loads(metadata_raw) if metadata_raw else None
        return result
