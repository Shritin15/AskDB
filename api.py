"""
api.py — FastAPI backend for AskDB.Ai
Exposes the analytics pipeline as REST endpoints for the React frontend.
Supports multiple databases via an optional db_path parameter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analytics.pipeline import ask_question
from analytics.visualization import rows_to_df, decide_viz
from db.schema_introspector import get_schema_metadata
from data_quality.profiler import profile_table
from data_quality.scoring import confidence_from_profile
from llm.insight_service import generate_insight

app = FastAPI(title="AskDB.Ai API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_DB = PROJECT_ROOT / "data" / "datasets" / "chinook.sqlite"


def resolve_db(db_path: Optional[str]) -> Path:
    """Resolve db_path string to an absolute Path, falling back to default."""
    if db_path:
        p = Path(db_path)
        return p if p.is_absolute() else PROJECT_ROOT / p
    return DEFAULT_DB


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    db_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def get_schema(db_path: Optional[str] = Query(default=None)):
    try:
        path = resolve_db(db_path)
        schema = get_schema_metadata(path)
        return {
            "tables": {
                name: [c["name"] for c in info["columns"]]
                for name, info in schema.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


META_KEYWORDS = [
    # Help / usage
    "what can i ask", "what questions", "what should i ask",
    "help me", "how do i use", "what can you do", "example questions",
    "give me examples", "what do you answer", "guide me", "what topics",
    # Database description
    "tell me about", "describe this", "describe the", "what is this",
    "about this database", "about the database", "what tables", "what data",
    "overview", "summarize the database", "what does this db",
    "what is in", "what's in", "whats in", "show me the tables",
    "list the tables", "what columns", "database structure",
    # Greetings / conversation
    "hello", "hi ", "hey ", "good morning", "good afternoon",
    "who are you", "what are you", "introduce yourself",
    # Vague starters
    "show me something", "surprise me", "give me insight",
    "what's interesting", "what is interesting", "anything interesting",
    "show me anything", "i don't know", "i dont know", "not sure what to ask",
]

def _is_meta(q: str) -> bool:
    ql = q.lower().strip()
    return any(kw in ql for kw in META_KEYWORDS)

def _build_meta_response(db_path: Optional[str]) -> dict:
    """Build a dynamic help response based on the actual schema."""
    try:
        path = resolve_db(db_path)
        schema = get_schema_metadata(path)
        tables = list(schema.keys())
        # Build example questions from actual table/column names
        examples = []
        for table in tables[:4]:
            cols = [c["name"] for c in schema[table]["columns"]]
            # Count question
            examples.append(f"How many records are in {table}?")
            # Find numeric-ish columns for aggregation
            num_cols = [c for c in cols if any(x in c.lower() for x in
                ["total", "amount", "count", "price", "age", "year", "date", "revenue", "salary"])]
            text_cols = [c for c in cols if any(x in c.lower() for x in
                ["name", "type", "category", "status", "gender", "race", "city", "country", "genre"])]
            if num_cols and text_cols:
                examples.append(f"Show {num_cols[0]} by {text_cols[0]} in {table}")
            elif text_cols:
                examples.append(f"What are the most common {text_cols[0]} values in {table}?")
        if len(tables) > 1:
            examples.append(f"Show top 10 records from {tables[0]}")
        table_list = ", ".join(tables)
    except Exception:
        tables = []
        examples = [
            "Show top 10 records", "How many rows are in each table?",
            "What are the most common values?", "Show a summary of the data",
        ]
        table_list = "unknown"

    return {
        "status": "ok",
        "sql": None,
        "columns": [],
        "rows": [],
        "viz": {"kind": "none", "x": None, "y": None},
        "insight": {
            "headline": f"Here's what you can explore! 🚀 Tables: {table_list}",
            "key_findings": examples[:7],
            "caveats": ["Try asking about specific tables, counts, trends, or comparisons"],
            "confidence": "High",
        },
    }


@app.post("/query")
def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Handle meta / help questions without hitting the LLM
    if _is_meta(body.question):
        return _build_meta_response(body.db_path)

    db = resolve_db(body.db_path)

    try:
        result = ask_question(body.question, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == "rejected":
        return {"status": "rejected", "reason": result.get("reason")}

    if result["status"] != "ok":
        return {"status": "error", "error": result.get("error", "Unknown error")}

    df = rows_to_df(result["columns"], result["rows"])
    viz = decide_viz(df)

    try:
        insight = generate_insight(
            question=body.question,
            sql=result["sql"],
            rows=result["rows"],
            dq_confidence="High",
        )
    except Exception:
        insight = None

    return {
        "status": "ok",
        "sql": result["sql"],
        "columns": result["columns"],
        "rows": result["rows"],
        "viz": {"kind": viz.kind, "x": viz.x, "y": viz.y},
        "insight": insight,
    }


@app.get("/data-quality/{table_name}")
def data_quality(table_name: str, db_path: Optional[str] = Query(default=None)):
    try:
        path = resolve_db(db_path)
        prof = profile_table(path, table_name)
        conf = confidence_from_profile(prof)
        return {"profile": prof, "confidence": conf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
