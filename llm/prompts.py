"""Prompt templates for LLM tasks."""

from __future__ import annotations


def nl_to_sql_prompt(question: str, schema_json: str, max_rows: int = 100, error_context: str | None = None):
    system_prompt = """
You are a SQLite SQL generation engine that interprets natural language questions into SQL queries.

You must:
- Return VALID JSON only.
- Generate exactly ONE SELECT query.
- Use ONLY tables and columns that appear in the schema. NEVER invent or guess column names.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, or PRAGMA.
- Be flexible and creative — interpret vague or imprecise questions in the most reasonable way.
- For ranking questions ("top", "best", "most", "highest", "lowest", "worst") use ORDER BY + LIMIT.
- For percentage/proportion questions use CAST and a subquery or CTE to compute ratios.
- For count/volume questions use COUNT(*) or COUNT(DISTINCT col).
- For average/mean questions use AVG(col).
- For distribution questions use GROUP BY on a categorical column.
- For trend/over time questions GROUP BY the date/year column and ORDER BY it.
- For "show me something interesting" or "surprise me" generate a meaningful aggregation.
- For comparison questions ("vs", "compared to", "difference between") use CASE or subqueries.
- For "how many X per Y" questions use GROUP BY Y and COUNT or SUM on X.
- For "which X has the most/least Y" use GROUP BY X, ORDER BY Y DESC/ASC, LIMIT 1.
- Only reject if the question is truly unrelated to every table and column in the schema.

SQLite date handling rules (CRITICAL — read sample rows to confirm format):
- Dates are stored as TEXT strings (e.g. "2013-06-17T00:00:00.000" or "2013-06-17").
- To extract year: SUBSTR(col, 1, 4) or strftime('%Y', col).
- To extract month: SUBSTR(col, 6, 2) or strftime('%m', col).
- To extract day: SUBSTR(col, 9, 2) or strftime('%d', col).
- NEVER assume year/month/day are separate columns unless explicitly in the schema.
- Always inspect the sample row to understand the actual date format.

Output format:
{
  "status": "ok" | "rejected",
  "sql": "SELECT ...",
  "reason": "brief explanation if rejected"
}
""".strip()

    error_section = ""
    if error_context:
        error_section = f"\n\nPrevious SQL attempt failed with this error:\n{error_context}\nPlease fix the query — check column names carefully against the schema."

    user_prompt = f"""
Question:
{question}

Available Schema (JSON):
{schema_json}

Row limit: {max_rows}{error_section}
""".strip()

    return system_prompt, user_prompt


def insight_prompt(question: str, sql: str, result_json: str, dq_confidence: str):
    system_prompt = """
You are a business analyst assistant.

Return JSON only.

Rules:
- Base your findings ONLY on the data provided in Query Result.
- NEVER state or imply that the data ends at a specific year or date based on what you see in the results — the results may be truncated to a row limit and do not represent the full dataset.
- NEVER invent numbers, percentages, or figures not present in the result rows.
- If results look truncated (e.g. exactly 100 rows, or data suspiciously stops), note this as a caveat.
- Be precise: quote actual values from the data, do not round or approximate unless necessary.

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
Query Result (may be limited to 100 rows — full dataset may have more): {result_json}
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