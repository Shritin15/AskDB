"""NL->SQL service orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any

from db.schema_introspector import get_schema_metadata
from db.pruner import prune_schema, strip_samples
from llm.client import LLMClient
from llm.prompts import nl_to_sql_prompt

logger = logging.getLogger(__name__)


def generate_sql_from_question(
    question: str,
    db_path: str,
    llm_client: LLMClient | None = None,
    error_context: str | None = None,
) -> dict[str, Any]:
    """
    Convert a natural-language question into a structured JSON response
    that contains a SELECT-only SQL query.

    Token optimisation pipeline:
      1. Load full schema (columns + sample rows + foreign keys)
      2. Prune to only relevant tables via semantic search or keyword fallback
         → typically reduces schema by 70-85%
      3. Strip sample rows from the pruned schema before sending to the LLM
         → saves an additional 40-60% of schema tokens
      4. Send the compact schema + question to the LLM
    """
    client = llm_client or LLMClient()

    # 1) Load full enriched schema from the SQLite DB
    full_schema = get_schema_metadata(db_path)
    logger.info("Full schema loaded: %d tables", len(full_schema))

    # 2) Prune to relevant tables only
    pruned_schema = prune_schema(question, full_schema)
    logger.info("Pruned schema: %d tables", len(pruned_schema))

    # 3) Strip sample rows — they've served their purpose for pruning
    lean_schema = strip_samples(pruned_schema)

    # 4) Build prompts and call the LLM
    system_prompt, user_prompt = nl_to_sql_prompt(
        question=question,
        schema_json=json.dumps(lean_schema),
        max_rows=100,
        error_context=error_context,
    )

    return client.generate_json(system_prompt, user_prompt)
