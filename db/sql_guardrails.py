"""SQL guardrails for safe query execution."""

from __future__ import annotations

import re

FORBIDDEN_KEYWORDS = {
    "DELETE",
    "UPDATE",
    "DROP",
    "ALTER",
    "INSERT",
    "TRUNCATE",
    "REPLACE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
}


def validate_select_only(sql: str) -> tuple[bool, str]:
    normalized = sql.strip().rstrip(";")
    if not normalized:
        return False, "SQL is empty."

    if not re.match(r"^SELECT\b", normalized, flags=re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    upper_sql = normalized.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return False, f"Query contains forbidden keyword: {keyword}"

    return True, "OK"
