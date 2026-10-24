import sqlite3
import tempfile
from app.migrations import migrate_database, LATEST_SCHEMA_VERSION


def test_migrations_are_versioned_and_idempotent():
    db = tempfile.mktemp(suffix=".db")
    assert migrate_database(db) == LATEST_SCHEMA_VERSION == 3
    assert migrate_database(db) == 3
    with sqlite3.connect(db) as conn:
        versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert versions == [1, 2, 3]


def test_migration_preserves_legacy_memory_data():
    db = tempfile.mktemp(suffix=".db")
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE cells (address INTEGER PRIMARY KEY, value TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL DEFAULT 'legacy')")
        conn.execute("INSERT INTO cells(address,value,revision) VALUES (5,'kept',2)")
        conn.execute("CREATE TABLE revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, address INTEGER NOT NULL, operation TEXT NOT NULL, value TEXT, revision INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT 'legacy')")
        conn.execute("CREATE TABLE experiments (experiment_id TEXT PRIMARY KEY,label TEXT NOT NULL,qubits INTEGER NOT NULL,shots INTEGER NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,result_json TEXT,error TEXT)")
        conn.execute("INSERT INTO experiments VALUES ('old-exp','hadamard_all',2,10,'completed','t','t','{\"ok\":true}',NULL)")
    migrate_database(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT value FROM cells WHERE address=5").fetchone()[0] == "kept"
        assert conn.execute("SELECT experiment_id FROM experiments WHERE experiment_id='old-exp'").fetchone()[0] == "old-exp"
        cols = {r[1] for r in conn.execute("PRAGMA table_info(experiments)")}
        assert "backend" in cols and "metadata_json" in cols


def test_newer_database_schema_fails_fast():
    db = tempfile.mktemp(suffix=".db")
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, description TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_migrations VALUES (99, 'now', 'future schema')")
    try:
        migrate_database(db)
    except RuntimeError as exc:
        assert "newer than this application supports" in str(exc)
    else:
        raise AssertionError("future schema should not be opened silently")
