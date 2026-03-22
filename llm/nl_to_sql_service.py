"""NL->SQL service orchestration."""

from __future__ import annotations

import logging
from typing import Any

from db.schema_introspector import get_schema_metadata
from db.pruner import prune_schema, strip_samples
from llm.client import LLMClient
from llm.prompts import nl_to_sql_prompt, schema_to_prompt_text

logger = logging.getLogger(__name__)


def generate_sql_from_question(
    question: str,
    db_path: str,
    llm_client: LLMClient | None = None,
    error_context: dict | None = None,
) -> dict[str, Any]:
    """
    Convert a natural-language question into a structured JSON response
    that contains a SELECT-only SQL query.

    Token optimisation pipeline:
      1. Load full schema (columns + sample rows + stats + foreign keys)
      2. Prune to only relevant tables via semantic search or keyword fallback
         → typically reduces schema by 70-85%
      3. Strip to 1 sample row from the pruned schema
      4. Convert schema to readable text (not raw JSON) — clearer for the LLM
      5. Send the compact schema + question to the LLM
    """
    client = llm_client or LLMClient()

    # 1) Load full enriched schema from the SQLite DB
    full_schema = get_schema_metadata(db_path)
    logger.info("Full schema loaded: %d tables", len(full_schema))

    # 2) Prune to relevant tables only
    pruned_schema = prune_schema(question, full_schema)
    logger.info("Pruned schema: %d tables", len(pruned_schema))

    # 3) Reduce to 1 sample row per table
    lean_schema = strip_samples(pruned_schema)

    # 4) Convert to readable text (includes range hints from stats)
    schema_text = schema_to_prompt_text(lean_schema)

    # 5) Build prompts and call the LLM
    system_prompt, user_prompt = nl_to_sql_prompt(
        question=question,
        schema_json=schema_text,
        max_rows=100,
        error_context=error_context,
    )

    return client.generate_json(system_prompt, user_prompt)
