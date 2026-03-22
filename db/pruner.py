"""
pruner.py — Schema pruning: filter to only the tables relevant to a question.

Problem: a database with 14 tables has a schema of ~1,500 tokens.
A question about customers has nothing to do with Territories or Shippers.
Sending irrelevant tables wastes tokens and confuses the model.

Solution: score each table by keyword overlap OR semantic similarity with
the question, pick the top matches, then expand via foreign keys so joins
still work. No extra LLM call needed.

Typical result: 14 tables → 2-4 tables = 70-85% fewer schema tokens.
"""

from __future__ import annotations

import logging
import re

from db import embedder as _embedder

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "not", "only", "same", "so", "than", "too", "very",
    "just", "but", "and", "or", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "me",
    "my", "give", "show", "list", "find", "get", "tell", "many", "much",
    "per", "between",
}


def prune_schema(question: str, schema: dict, max_tables: int = 5) -> dict:
    """
    Return a copy of the schema containing only the tables most relevant
    to the question, plus any tables they reference via foreign keys.

    Selection strategy (in priority order):
      1. Semantic search via sentence-transformers (if installed)
      2. Keyword scoring fallback

    Args:
        question:   The user's natural language question.
        schema:     Full schema dict from get_schema_metadata().
                    Format: {table_name: {"columns": [...], "sample": [...], "foreign_keys": [...]}}
        max_tables: Max seed tables before FK expansion (default 5).

    Returns:
        A pruned schema dict with fewer tables. Falls back to full schema
        if no confident match is found.
    """
    if len(schema) <= max_tables:
        logger.debug("Schema has %d tables — no pruning needed.", len(schema))
        return schema

    # --- Strategy 1: Semantic search (preferred) ---
    semantic_seeds = _embedder.find_relevant_tables(question, schema, top_k=max_tables)
    if semantic_seeds:
        logger.info("Semantic pruning selected tables: %s", semantic_seeds)
        seeds = set(semantic_seeds)
    else:
        # --- Strategy 2: Keyword scoring fallback ---
        logger.info("Falling back to keyword pruning.")
        question_tokens = _tokenize(question)
        if not question_tokens:
            logger.info("No question tokens — returning full schema.")
            return schema

        scores: dict[str, float] = {
            t: _score_table(question_tokens, t, info)
            for t, info in schema.items()
        }

        if max(scores.values()) == 0:
            logger.info("No keyword matches — returning full schema.")
            return schema

        ranked = sorted(scores, key=lambda t: scores[t], reverse=True)
        seeds = {t for t in ranked[:max_tables] if scores[t] > 0}
        if not seeds:
            return schema

    # --- Expand via outgoing foreign keys (one hop) ---
    selected = _expand_via_fk(seeds, schema)
    pruned = {t: schema[t] for t in schema if t in selected}

    logger.info(
        "Schema pruned: %d → %d tables (saved ~%d%% tokens)",
        len(schema),
        len(pruned),
        round((1 - len(pruned) / len(schema)) * 100),
    )
    return pruned


def strip_samples(schema: dict) -> dict:
    """
    Reduce sample rows to 1 per table before sending to the LLM.

    Keeping 1 sample row lets the LLM see the actual format of values
    (e.g. dates stored as "2013-06-17T00:00:00.000") so it generates
    correct expressions like SUBSTR(col, 1, 4) instead of hallucinating
    a non-existent 'year' column. Saves ~60% tokens vs sending all 3 rows.
    """
    return {
        table_name: {**table_info, "sample": table_info.get("sample", [])[:1]}
        for table_name, table_info in schema.items()
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    raw = re.findall(r"[a-z]+", text.lower())
    tokens: set[str] = set()
    for t in raw:
        if t in _STOP_WORDS or len(t) <= 2:
            continue
        tokens.add(t)
        if t.endswith("ies") and len(t) > 4:
            tokens.add(t[:-3] + "y")
        elif t.endswith("es") and len(t) > 4:
            tokens.add(t[:-2])
        elif t.endswith("s") and len(t) > 3:
            tokens.add(t[:-1])
    return tokens


def _score_table(question_tokens: set[str], table_name: str, table_info: dict) -> float:
    score = 0.0
    table_tokens = _tokenize(table_name)
    score += len(question_tokens & table_tokens) * 3.0
    for col in table_info.get("columns", []):
        col_tokens = _tokenize(col["name"])
        score += len(question_tokens & col_tokens) * 1.0
    return score


def _expand_via_fk(seeds: set[str], all_tables: dict) -> set[str]:
    extra: set[str] = set()
    for table_name in seeds:
        table_info = all_tables.get(table_name, {})
        for fk in table_info.get("foreign_keys", []):
            referenced_table = fk["references"].split(".")[0]
            if referenced_table in all_tables and referenced_table not in seeds:
                extra.add(referenced_table)
    return seeds | extra
