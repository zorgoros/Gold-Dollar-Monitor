"""Behaviour from TOML, secrets from the environment. No config library needed."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "default.toml"


def load_env(path: Path | None = None) -> None:
    """Read a .env file into the environment. Real environment variables win."""
    env_file = path if path is not None else ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _db_path(url: str) -> Path:
    """sqlite:///relative/path or sqlite:////absolute/path -> Path."""
    if not url.startswith("sqlite://"):
        raise ValueError(f"only sqlite URLs are supported in V1, got {url!r}")
    rest = url[len("sqlite://") :].lstrip("/")
    path = Path(rest)
    return path if path.is_absolute() else ROOT / path


@dataclass(frozen=True)
class Settings:
    config: dict[str, Any]
    db_path: Path
    telegram_token: str | None
    telegram_channel: str | None
    log_level: str

    @classmethod
    def load(cls, config_path: Path | None = None) -> Settings:
        load_env()
        path = config_path if config_path is not None else DEFAULT_CONFIG
        with path.open("rb") as fh:
            config = tomllib.load(fh)
        return cls(
            config=config,
            db_path=_db_path(os.environ.get("DATABASE_URL", "sqlite:///data/market.db")),
            telegram_token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
            telegram_channel=os.environ.get("TELEGRAM_CHANNEL_ID") or None,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    @property
    def model_version(self) -> str:
        return str(self.config["model_version"])

    @property
    def timezone(self) -> str:
        return str(self.config["timezone"])

    def section(self, name: str) -> dict[str, Any]:
        value: dict[str, Any] = self.config.get(name, {})
        return value
