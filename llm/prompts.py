"""Prompt templates for LLM tasks."""

from __future__ import annotations


def schema_to_prompt_text(schema: dict) -> str:
    """
    Convert a schema dict into a readable text block for the LLM prompt.
    Includes column types, range hints (min/max), sample rows, and foreign keys.
    Much clearer than raw JSON and more token-efficient.
    """
    import json as _json
    lines = []
    for table, info in schema.items():
        lines.append(f"TABLE: {table}")
        lines.append("  COLUMNS:")
        stats = info.get("stats", {})
        for col in info.get("columns", []):
            pk        = " [PK]" if col.get("pk") else ""
            notnull   = " NOT NULL" if col.get("notnull") else ""
            col_stats = stats.get(col["name"])
            stat_hint = f" [range: {col_stats['min']} to {col_stats['max']}]" if col_stats else ""
            lines.append(f"    - {col['name']} ({col['type'] or 'TEXT'}){pk}{notnull}{stat_hint}")
        fks = info.get("foreign_keys", [])
        if fks:
            lines.append("  FOREIGN KEYS:")
            for fk in fks:
                lines.append(f"    - {fk['column']} → {fk['references']}")
        samples = info.get("sample", [])
        if samples:
            lines.append(f"  SAMPLE ROW:")
            lines.append(f"    {_json.dumps(samples[0])}")
        lines.append("")
    return "\n".join(lines)


def nl_to_sql_prompt(question: str, schema_json: str, max_rows: int = 100, error_context: str | None = None):
    system_prompt = """
You are a SQLite SQL generation engine that interprets natural language questions into SQL queries.

GENERAL RULES:
- Return VALID JSON only.
- Generate exactly ONE SELECT query.
- Use ONLY tables and columns that appear in the schema. NEVER invent or guess column names.
- Always wrap table and column names in double quotes: "table_name", "column_name".
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, or PRAGMA.
- Only output CANNOT_ANSWER if the required tables/columns are completely absent from the schema.
  Never refuse because you are uncertain — generate the SQL and let the result speak for itself.

QUESTION PATTERNS:
- Ranking ("top", "best", "most", "highest", "lowest", "worst"): ORDER BY + LIMIT.
- Percentage/proportion: use CAST and a subquery or CTE to compute ratios.
- Count/volume: COUNT(*) or COUNT(DISTINCT col).
- Average/mean: AVG(col).
- Distribution: GROUP BY on a categorical column.
- Trend over time: GROUP BY year/date column and ORDER BY it.
- "Year over year change" / "how has X changed": use a CTE with LAG() window function.
- Comparison ("vs", "compared to", "difference between"): use CASE or subqueries.
- "How many X per Y": GROUP BY Y and COUNT or SUM on X.
- "Which X has the most/least Y": GROUP BY X, ORDER BY Y DESC/ASC, LIMIT 1.
- "Show me something interesting" / "surprise me": meaningful aggregation on most interesting columns.

SQLITE-SPECIFIC RULES (STRICT):
- Do NOT use QUALIFY — SQLite does not support it.
  Instead wrap window functions in a CTE and filter in the outer query:
    WITH ranked AS (SELECT ..., ROW_NUMBER() OVER (...) AS rn FROM ...)
    SELECT ... FROM ranked WHERE rn = 1
- Window functions (LAG, LEAD, ROW_NUMBER, RANK, SUM OVER, etc.) ARE supported
  but ONLY inside subqueries or CTEs, never directly with QUALIFY.
- For "year over year" use LAG() in a CTE:
    WITH yearly AS (SELECT SUBSTR("date_col",1,4) AS yr, COUNT(*) AS cnt FROM "table" GROUP BY yr)
    SELECT yr, cnt, cnt - LAG(cnt) OVER (ORDER BY yr) AS change FROM yearly ORDER BY yr
- Do NOT use ILIKE — use LIKE instead (SQLite LIKE is case-insensitive for ASCII).
- Do NOT use :: for type casting — use CAST(value AS type) instead.
- Do NOT use FULL OUTER JOIN.

DATE HANDLING (CRITICAL — always check sample row for actual format):
- Dates are TEXT strings (e.g. "2013-06-17T00:00:00.000" or "2013-06-17").
- Extract year: SUBSTR("col", 1, 4) or strftime('%Y', "col").
- Extract month: SUBSTR("col", 6, 2) or strftime('%m', "col").
- Use [range: X to Y] hints in the schema to write accurate WHERE clauses.
- NEVER assume year/month/day are separate columns unless explicitly in the schema.

Output format:
{
  "status": "ok" | "rejected",
  "sql": "SELECT ...",
  "reason": "brief explanation if rejected"
}
""".strip()

    error_section = ""
    if error_context:
        error_section = f"\n\nPrevious SQL attempt failed with this error:\n{error_context['error']}\n\nFailing query was:\n```sql\n{error_context.get('sql', '')}\n```\nFix the query — check column names and SQLite syntax carefully."

    user_prompt = f"""
Question:
{question}

Available Schema:
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