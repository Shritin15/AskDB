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
    "what can i ask", "what questions", "what should i ask",
    "help me", "how do i use", "what can you do", "example questions",
    "give me examples", "what do you answer", "guide me", "what topics",
]

def _is_meta(q: str) -> bool:
    ql = q.lower()
    return any(kw in ql for kw in META_KEYWORDS)


@app.post("/query")
def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Handle meta / help questions without hitting the LLM
    if _is_meta(body.question):
        return {
            "status": "ok",
            "sql": None,
            "columns": [],
            "rows": [],
            "viz": {"kind": "none", "x": None, "y": None},
            "insight": {
                "headline": "Here are some great questions to ask! 🚀",
                "key_findings": [
                    "Show total sales by country",
                    "Who are the top 5 customers by spending?",
                    "What percentage of tracks belong to each media type?",
                    "Show revenue by month for 2013",
                    "Top 10 artists by number of albums",
                    "How many tracks belong to each genre?",
                    "Which employee has the highest total sales?",
                ],
                "caveats": ["Results depend on the currently selected database"],
                "confidence": "High",
            },
        }

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
