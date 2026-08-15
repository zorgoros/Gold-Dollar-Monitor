"""The guard that stands between a bad run and an irrecoverable force-push.

`scripts/guard_db_growth.py` runs immediately before the `market-data` branch is
amended and force-pushed, so — as with the secret scan next to it — its *exit
code* is the contract and these drive the real script through a subprocess.

The failure it exists for: a run that starts from an empty database and pushes
it over a branch holding months of observations. There is no earlier commit to
restore from, so failing open here is the one outcome that cannot be undone.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "guard_db_growth.py"


def run(previous: Path, current: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(previous), str(current)],
        capture_output=True,
        text=True,
        check=False,
    )


def make_db(path: Path, snapshots: int, metrics: int = 0) -> Path:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY)")
    for table, rows in (("snapshots", snapshots), ("metrics", metrics)):
        connection.executemany(
            f"INSERT INTO {table} (id) VALUES (?)",  # noqa: S608 - name from this function
            [(i,) for i in range(rows)],
        )
    connection.commit()
    connection.close()
    return path


def test_an_appended_database_passes(tmp_path):
    previous = make_db(tmp_path / "previous.db", snapshots=100, metrics=900)
    current = make_db(tmp_path / "current.db", snapshots=101, metrics=910)
    result = run(previous, current)
    assert result.returncode == 0
    assert "history intact" in result.stdout


def test_an_unchanged_database_passes(tmp_path):
    """A run that collected nothing new still holds every row it started with."""
    previous = make_db(tmp_path / "previous.db", snapshots=100)
    current = make_db(tmp_path / "current.db", snapshots=100)
    assert run(previous, current).returncode == 0


def test_a_fresh_database_never_replaces_a_populated_one(tmp_path):
    """BUG-006: the exact shape of the loss this guard exists to stop."""
    previous = make_db(tmp_path / "previous.db", snapshots=4000, metrics=52000)
    current = make_db(tmp_path / "current.db", snapshots=0)
    result = run(previous, current)
    assert result.returncode == 1
    assert "REFUSING TO PUBLISH" in result.stdout
    assert "snapshots: 4000 -> 0" in result.stdout


def test_one_table_losing_rows_is_enough_to_stop_the_push(tmp_path):
    """Partial loss is still loss — growth elsewhere does not excuse it."""
    previous = make_db(tmp_path / "previous.db", snapshots=100, metrics=900)
    current = make_db(tmp_path / "current.db", snapshots=101, metrics=10)
    result = run(previous, current)
    assert result.returncode == 1
    assert "metrics: 900 -> 10" in result.stdout


def test_no_previous_database_is_not_an_error(tmp_path):
    """First run on a new branch: there is no history to lose yet."""
    current = make_db(tmp_path / "current.db", snapshots=1)
    assert run(tmp_path / "absent.db", current).returncode == 0


def test_a_missing_current_database_refuses(tmp_path):
    previous = make_db(tmp_path / "previous.db", snapshots=100)
    assert run(previous, tmp_path / "absent.db").returncode == 1


def test_an_unreadable_database_refuses_rather_than_passes(tmp_path):
    """A corrupt file is not evidence of growth — failing open would publish it."""
    previous = make_db(tmp_path / "previous.db", snapshots=100)
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite file")
    assert run(previous, corrupt).returncode == 1
