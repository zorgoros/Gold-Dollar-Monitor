#!/usr/bin/env python3
"""Fail if the database contains anything that looks like a credential.

The `market-data` branch is pushed unattended to a public repository, so what
goes onto it is checked rather than trusted. The database is meant to hold
public market data only; a bot token reaching it means a logging or persistence
bug upstream, and the push must stop rather than publish it.

Precedent: v1.0 shipped with httpx logging the Telegram URL, which embeds the
token. That was fixed, but the class of defect is what this guards against.

Exit 0 clean, 1 on a match or an unreadable database. Never prints a match.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

PATTERNS = {
    "telegram bot token": re.compile(rb"\d{8,12}:AA[\w-]{30,}"),
    "telegram api url": re.compile(rb"api\.telegram\.org"),
    "bot method path": re.compile(rb"/bot\d{6,}"),
    "generic bearer token": re.compile(rb"(?i)\b(?:bearer|authorization:)\s*\S{16,}"),
}


def scan(path: Path) -> int:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.text_factory = bytes
    tables = [
        row[0].decode()
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    ]
    found: dict[str, set[str]] = {}
    for table in tables:
        for row in connection.execute(f"SELECT * FROM {table}"):  # noqa: S608 - name from schema
            for cell in row:
                if not isinstance(cell, bytes):
                    continue
                for label, pattern in PATTERNS.items():
                    if pattern.search(cell):
                        found.setdefault(label, set()).add(table)
    connection.close()

    if not found:
        print(f"clean: {len(tables)} tables, no credential pattern matched")
        return 0

    # Report where, never what — this output lands in a public build log.
    print("REFUSING TO PUBLISH — credential-shaped data in the database:")
    for label, where in sorted(found.items()):
        print(f"  {label}: {', '.join(sorted(where))}")
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <path-to-database>")
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        # A run that never got as far as creating the file has nothing to leak.
        print(f"no database at {path} — nothing to scan")
        return 0
    try:
        return scan(path)
    except sqlite3.DatabaseError as exc:
        print(f"cannot read {path}: {type(exc).__name__} — refusing to publish it")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
