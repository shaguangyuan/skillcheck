from __future__ import annotations

from pathlib import Path


def default_data_dir() -> Path:
    return Path.home() / ".skillcheck"


def default_database_path() -> Path:
    return default_data_dir() / "skillcheck.sqlite"
