#!/usr/bin/env python3
"""Fail if the database about to be pushed holds less history than the one on the branch.

The `market-data` branch is a single commit that every run amends and
force-pushes, so there is no earlier commit to recover from: one push of a
wrong database ends the dataset. The observation tables are append-only —
nothing in `src/` deletes a row and nothing runs VACUUM — so a count that fell
means the file was replaced rather than added to, and the push must stop.

This is the second line. The first is the workflow refusing to treat a failed
fetch as a missing branch (BUG-006); this catches every other way an empty or
foreign database could reach the push step.

Exit 0 when every table grew or held, 1 on a shrink or an unreadable database.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Append-only by construction. `instruments` is a fixed lookup and `reports`
# holds one row per delivery, so they belong here too — none of them ever
# legitimately loses a row.
TRACKED = ("snapshots", "quotes", "snapshot_quotes", "metrics", "signals", "reports", "job_runs")


def counts(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        present = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        return {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608
            for table in TRACKED
            if table in present
        }
    finally:
        connection.close()


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} <previous-database> <current-database>")
        return 1
    previous, current = Path(sys.argv[1]), Path(sys.argv[2])
    if not previous.exists():
        # First run on a new branch: there is no history to lose yet.
        print(f"no previous database at {previous} — nothing to compare")
        return 0
    if not current.exists():
        print(f"REFUSING TO PUBLISH — no database at {current}")
        return 1
    try:
        before, after = counts(previous), counts(current)
    except sqlite3.DatabaseError as exc:
        print(f"cannot read a database: {type(exc).__name__} — refusing to publish")
        return 1

    shrunk = {t: (n, after.get(t, 0)) for t, n in before.items() if after.get(t, 0) < n}
    if shrunk:
        print("REFUSING TO PUBLISH — the database lost history:")
        for table, (was, now) in sorted(shrunk.items()):
            print(f"  {table}: {was} -> {now}")
        return 1

    print(
        "history intact: "
        + ", ".join(f"{t} {before.get(t, 0)}->{n}" for t, n in sorted(after.items()))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
