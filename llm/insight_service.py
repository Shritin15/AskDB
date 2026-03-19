"""Insight generation service."""

from __future__ import annotations

import json
from typing import Any

from llm.client import LLMClient
from llm.prompts import insight_prompt


def generate_insight(
    question: str,
    sql: str,
    rows: list[tuple[Any, ...]],
    dq_confidence: str,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    """
    Generate a short BI-style narrative grounded in the query results.
    Returns JSON (headline, key_findings, caveats, confidence).
    """
    client = llm_client or LLMClient()

    # keep results small to reduce tokens
    result_json = json.dumps(rows[:50])

    system_prompt, user_prompt = insight_prompt(
        question=question,
        sql=sql,
        result_json=result_json,
        dq_confidence=dq_confidence,
    )

    return client.generate_json(system_prompt, user_prompt)