"""Prompt templates for LLM tasks."""

from __future__ import annotations


def nl_to_sql_prompt(question: str, schema_json: str, max_rows: int = 100):
    system_prompt = """
You are a SQLite SQL generation engine.

You must:
- Return VALID JSON only.
- Generate exactly ONE SELECT query.
- Use only tables and columns provided in the schema.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, or PRAGMA.
- If the question cannot be answered using the schema, return:
  {"status": "rejected", "reason": "explanation"}

Output format:
{
  "status": "ok" | "rejected",
  "sql": "SELECT ...",
  "reason": "brief explanation"
}
""".strip()

    user_prompt = f"""
Question:
{question}

Available Schema (JSON):
{schema_json}

Row limit: {max_rows}
""".strip()

    return system_prompt, user_prompt


def insight_prompt(question: str, sql: str, result_json: str, dq_confidence: str):
    system_prompt = """
You are a business analyst assistant.

Return JSON only.

Output format:
{
  "headline": "short summary",
  "key_findings": ["point 1", "point 2"],
  "caveats": ["limitations"],
  "confidence": "High|Medium|Low"
}
""".strip()

    user_prompt = f"""
Question: {question}
SQL Used: {sql}
Query Result: {result_json}
Data Quality Confidence: {dq_confidence}
""".strip()

    return system_prompt, user_prompt


def dq_summary_prompt(profile_json: str, score_json: str):
    system_prompt = """
You are a data quality auditor.

Return JSON only.

Output format:
{
  "overall_confidence": "High|Medium|Low",
  "issues": [
    {
      "type": "missing|duplicate|outlier|drift",
      "severity": "high|medium|low",
      "description": "what is wrong"
    }
  ],
  "summary": "short summary"
}
""".strip()

    user_prompt = f"""
Profile Metrics:
{profile_json}

Scoring:
{score_json}
""".strip()

    return system_prompt, user_prompt