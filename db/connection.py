"""Database connection helpers for SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "app.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    return sqlite3.connect(path)
