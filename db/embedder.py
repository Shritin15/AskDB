"""
embedder.py — Semantic table selection using sentence embeddings.

WHY THIS EXISTS
───────────────
Keyword matching fails on business language:
  "sales rep"       → needs Employees       (zero keyword overlap)
  "revenue"         → needs Order Details   (zero keyword overlap)
  "top-performing"  → needs Orders          (zero keyword overlap)

Embeddings solve this because "sales representative" and "Employees.Title"
live close together in vector space even without shared words.

HOW IT WORKS
────────────
1. Each table is described as a short text:
     "Employees — columns: EmployeeID, LastName, Title [Sales Rep, Manager]"
2. All descriptions are embedded once and cached per schema.
3. At query time the question is embedded and cosine similarity selects
   the closest tables.
4. FK expansion still runs after, same as before.

MODEL
─────
all-MiniLM-L6-v2: ~80MB download (cached after first run), ~5ms per
embedding on CPU. No API key, no rate limits, fully local.
"""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_CACHE_VERSION = 1


# ---------------------------------------------------------------------------
# Model loader — lazy singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model '%s'...", _MODEL_NAME)
        model = SentenceTransformer(_MODEL_NAME)
        logger.info("Embedding model loaded.")
        return model
    except ImportError:
        return None


def is_available() -> bool:
    return _load_model() is not None


# ---------------------------------------------------------------------------
# Schema → text descriptions
# ---------------------------------------------------------------------------

def _table_to_text(table_name: str, table_info: dict) -> str:
    """
    Convert a table's metadata into a rich text description for embedding.
    Includes column names and sample values so semantic search understands
    business meaning (e.g. Title column with 'Sales Rep' values → sales queries).
    """
    cols = table_info.get("columns", [])
    sample_rows = table_info.get("sample", [])

    # Build lookup: column name → distinct sample values
    sample_lookup: dict = {}
    for row in sample_rows:
        for col_name, val in row.items():
            if val is not None and str(val).strip():
                sample_lookup.setdefault(col_name, [])
                val_str = str(val).strip()
                if val_str not in sample_lookup[col_name]:
                    sample_lookup[col_name].append(val_str)

    col_parts = []
    for col in cols:
        name = col["name"]
        dtype = col.get("type", "").upper()

        # Skip pure ID columns — values like [1, 2, 3] add noise
        is_id_col = name.upper().endswith("ID") and any(
            t in dtype for t in ("INT", "INTEGER")
        )
        if is_id_col:
            col_parts.append(name)
            continue

        samples = sample_lookup.get(name, [])[:3]
        if samples:
            col_parts.append(f"{name} [{', '.join(samples)}]")
        else:
            col_parts.append(name)

    return f"{table_name}: {', '.join(col_parts)}"


def _schema_fingerprint(schema: dict) -> str:
    table_names = sorted(schema.keys())
    payload = json.dumps({"tables": table_names, "v": _CACHE_VERSION})
    return hashlib.md5(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------

_embedding_cache: dict = {}


def _get_table_embeddings(schema: dict) -> Optional[dict]:
    model = _load_model()
    if model is None:
        return None

    fingerprint = _schema_fingerprint(schema)
    if fingerprint in _embedding_cache:
        return _embedding_cache[fingerprint]

    table_names = list(schema.keys())
    table_texts = [_table_to_text(name, schema[name]) for name in table_names]

    embeddings = model.encode(table_texts, normalize_embeddings=True, show_progress_bar=False)
    result = {"table_names": table_names, "embeddings": embeddings}
    _embedding_cache[fingerprint] = result
    logger.debug("Computed and cached embeddings for %d tables.", len(table_names))
    return result


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def find_relevant_tables(
    question: str,
    schema: dict,
    top_k: int = 5,
    min_similarity: float = 0.15,
) -> Optional[list[str]]:
    """
    Return names of the top_k tables most semantically relevant to the question.
    Returns None if sentence-transformers is not installed (caller falls back
    to keyword matching).
    """
    model = _load_model()
    if model is None:
        return None

    cached = _get_table_embeddings(schema)
    if cached is None:
        return None

    table_names: list[str] = cached["table_names"]
    table_embeddings: np.ndarray = cached["embeddings"]

    q_embedding = model.encode([question], normalize_embeddings=True)[0]
    similarities = table_embeddings @ q_embedding

    ranked_indices = np.argsort(similarities)[::-1]
    selected = [
        table_names[i]
        for i in ranked_indices[:top_k]
        if similarities[i] >= min_similarity
    ]

    all_scores = {table_names[i]: round(float(similarities[i]), 3) for i in ranked_indices}
    logger.info("Semantic table scores: %s", all_scores)
    logger.info("Selected (above %.2f): %s", min_similarity, selected)

    return selected if selected else None
