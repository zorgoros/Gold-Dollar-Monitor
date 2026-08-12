"""SQLite connection and the migration runner. Schema changes are never manual."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..domain.errors import DatabaseError

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def applied_versions(conn: sqlite3.Connection) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    return {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}


def migrate(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    """Apply every unapplied .sql file in name order. Returns what it applied."""
    directory = migrations_dir if migrations_dir is not None else MIGRATIONS_DIR
    done = applied_versions(conn)
    applied: list[str] = []
    for path in sorted(directory.glob("*.sql")):
        version = path.stem
        if version in done:
            continue
        # executescript() commits any open transaction before it runs, so the
        # BEGIN/COMMIT and the version row have to live inside the script itself
        # for the migration to be all-or-nothing.
        literal = version.replace("'", "''")
        script = (
            "BEGIN;\n"
            f"{path.read_text(encoding='utf-8')}\n"
            f"INSERT INTO schema_migrations (version) VALUES ('{literal}');\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise DatabaseError(f"migration {version} failed: {exc}") from exc
        applied.append(version)
    return applied


def open_migrated(db_path: Path) -> sqlite3.Connection:
    conn = connect(db_path)
    migrate(conn)
    return conn
