"""Versioned, idempotent SQLite migrations for Qwantum QRAM."""
from __future__ import annotations
import sqlite3
from pathlib import Path

LATEST_SCHEMA_VERSION = 3


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migration_1(conn: sqlite3.Connection) -> None:
    # Compatible with QRAM 0.6–0.9 databases: CREATE IF NOT EXISTS preserves rows.
    conn.execute("""CREATE TABLE IF NOT EXISTS cells (
        address INTEGER PRIMARY KEY, value TEXT NOT NULL, revision INTEGER NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, address INTEGER NOT NULL, operation TEXT NOT NULL,
        value TEXT, revision INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS experiments (
        experiment_id TEXT PRIMARY KEY, label TEXT NOT NULL, qubits INTEGER NOT NULL,
        shots INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, result_json TEXT, error TEXT
    )""")


def _migration_2(conn: sqlite3.Connection) -> None:
    # Additive columns: safe for existing 0.9 data and future result metadata.
    columns = _columns(conn, "experiments")
    if "backend" not in columns:
        conn.execute("ALTER TABLE experiments ADD COLUMN backend TEXT")
    columns = _columns(conn, "experiments")
    if "metadata_json" not in columns:
        conn.execute("ALTER TABLE experiments ADD COLUMN metadata_json TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_revisions_address_id ON revisions(address, id DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cells_updated_at ON cells(updated_at DESC)")


def _migration_3(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS experiment_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        status TEXT NOT NULL,
        event_at TEXT NOT NULL,
        detail_json TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_events_id ON experiment_events(experiment_id, id DESC)")


_MIGRATIONS = [(1, _migration_1), (2, _migration_2), (3, _migration_3)]


def migrate_database(database_path: str) -> int:
    """Apply each unapplied migration transactionally; return current schema version."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        )""")
        conn.commit()
        descriptions = {
            1: "base QRAM memory and experiment tables",
            2: "experiment metadata and query indexes",
            3: "experiment lifecycle audit events",
        }
        for version, migrate in _MIGRATIONS:
            found = conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone()
            if found:
                continue
            conn.execute("BEGIN IMMEDIATE")
            try:
                migrate(conn)
                conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at, description) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?)",
                    (version, descriptions[version]),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
        current_version = int(row[0])
        if current_version > LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than this application supports "
                f"(latest supported: {LATEST_SCHEMA_VERSION}). Upgrade the application before opening this database."
            )
        return current_version
    finally:
        conn.close()
