"""The guard that stands between a publisher bug and a public repository.

`scripts/scan_db_for_secrets.py` is the last thing to run before the database is
force-pushed to the `market-data` branch by an unattended job, so its *exit
code* is the contract, not its return value. These drive the real script through
a subprocess for that reason.

The planted tokens below are shape-accurate and entirely synthetic.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "scan_db_for_secrets.py"
FAKE_TOKEN = "1234567890:AA" + "x" * 33


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False
    )


def make_db(path: Path, value: str | bytes) -> Path:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE job_runs (id INTEGER PRIMARY KEY, detail)")
    connection.execute("INSERT INTO job_runs (detail) VALUES (?)", (value,))
    connection.commit()
    connection.close()
    return path


def test_a_clean_database_passes(tmp_path):
    result = run(make_db(tmp_path / "clean.db", "collected 8 quotes, published id 42"))
    assert result.returncode == 0
    assert "clean" in result.stdout


@pytest.mark.parametrize(
    "planted",
    [
        FAKE_TOKEN,
        f"POST https://api.telegram.org/bot{FAKE_TOKEN}/sendMessage",
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345",
    ],
    ids=["bare token", "full api url", "bearer header"],
)
def test_credential_shaped_data_stops_the_push(tmp_path, planted):
    result = run(make_db(tmp_path / "poisoned.db", planted))
    assert result.returncode == 1
    assert "REFUSING TO PUBLISH" in result.stdout


def test_the_match_itself_is_never_printed(tmp_path):
    """This output lands in a public build log, so it may name the table only."""
    result = run(make_db(tmp_path / "poisoned.db", FAKE_TOKEN))
    assert "job_runs" in result.stdout
    assert FAKE_TOKEN not in result.stdout + result.stderr
    assert "AAxxx" not in result.stdout + result.stderr


def test_a_token_hiding_in_a_blob_column_is_still_found(tmp_path):
    """Quotes carry raw provider payloads; a BLOB must not be a blind spot."""
    result = run(make_db(tmp_path / "blob.db", FAKE_TOKEN.encode()))
    assert result.returncode == 1


def test_an_unreadable_database_refuses_rather_than_passes(tmp_path):
    """A corrupt file is not evidence of safety — failing open would publish it."""
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite file")
    assert run(corrupt).returncode == 1


def test_a_missing_database_is_not_an_error(tmp_path):
    """A run that died before creating the file has nothing to leak."""
    assert run(tmp_path / "absent.db").returncode == 0
