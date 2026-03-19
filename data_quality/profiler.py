"""Basic data quality profiling utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def profile_table(db_path: Path, table_name: str) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        # Duplicate estimate across full rows.
        duplicate_count = cur.execute(
            f"SELECT COUNT(*) FROM (SELECT *, COUNT(*) c FROM {table_name} GROUP BY * HAVING c > 1)"
        ).fetchone()[0]

        columns = [row[1] for row in cur.execute(f"PRAGMA table_info('{table_name}')").fetchall()]
        missing: dict[str, int] = {}
        for col in columns:
            missing[col] = cur.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL"
            ).fetchone()[0]

    return {
        "table": table_name,
        "row_count": count,
        "duplicate_groups": duplicate_count,
        "missing_values": missing,
    }
