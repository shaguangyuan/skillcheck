from __future__ import annotations

from pathlib import Path


def default_data_dir() -> Path:
    return Path.home() / ".skill-health"


def default_database_path() -> Path:
    return default_data_dir() / "skill-health.sqlite"
