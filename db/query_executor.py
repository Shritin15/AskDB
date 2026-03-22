"""Execute validated SQL queries against SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Union

from db.sql_guardrails import validate_select_only


def execute_query(db_path: Union[str, Path], sql: str, limit: int = 100) -> dict[str, Any]:
    """
    Execute a validated SELECT-only SQL query safely against SQLite.

    - Enforces SELECT-only via guardrails
    - Wraps query in subquery to safely apply LIMIT
    - Returns structured result dict
    """

    # Ensure db_path works whether passed as str or Path
    db_path = str(db_path)

    # 1) Validate query safety
    ok, reason = validate_select_only(sql)
    if not ok:
        return {
            "status": "rejected",
            "error": reason,
            "rows": [],
            "columns": [],
        }

    # 2) Fetch one extra row to detect truncation, then trim
    safe_sql = f"SELECT * FROM ({sql.rstrip(';')}) LIMIT {int(limit) + 1}"

    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(safe_sql)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
    except sqlite3.Error as exc:
        return {
            "status": "error",
            "error": str(exc),
            "rows": [],
            "columns": [],
            "truncated": False,
        }

    truncated = len(rows) > limit
    rows = rows[:limit]

    return {
        "status": "ok",
        "error": None,
        "rows": rows,
        "columns": columns,
        "truncated": truncated,
    }