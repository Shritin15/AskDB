from llm.nl_to_sql_service import generate_sql_from_question
from db.query_executor import execute_query


def ask_question(question: str, db_path: str, limit: int = 100) -> dict:
    """
    End-to-end pipeline:
    1) NL → SQL (via LLM)
    2) Validate + execute SQL safely
    3) If SQL fails, retry once with the error as context
    4) Return structured response
    """

    # 1️ Get SQL from LLM
    llm_response = generate_sql_from_question(question, db_path)

    if llm_response.get("status") != "ok":
        return {
            "status": "rejected",
            "reason": llm_response.get("reason", "LLM rejected request"),
            "llm_response": llm_response,
        }

    sql = llm_response.get("sql")

    if not sql:
        return {
            "status": "error",
            "reason": "LLM did not return SQL",
            "llm_response": llm_response,
        }

    # Use a higher limit for aggregation queries (GROUP BY) so we don't truncate groups
    effective_limit = _smart_limit(sql, limit)

    # 2️ Execute safely
    query_result = execute_query(db_path, sql, limit=effective_limit)

    # 3️ Retry once if SQL errored (e.g. wrong column name)
    # Pass both the error AND the failing SQL so the LLM can see exactly what went wrong
    if query_result["status"] == "error":
        error_context = {
            "error": query_result.get("error", "unknown error"),
            "sql": sql,
        }
        retry_response = generate_sql_from_question(
            question, db_path, error_context=error_context
        )
        if retry_response.get("status") == "ok" and retry_response.get("sql"):
            retry_sql = retry_response["sql"]
            retry_limit = _smart_limit(retry_sql, limit)
            retry_result = execute_query(db_path, retry_sql, limit=retry_limit)
            if retry_result["status"] == "ok":
                return {
                    "status": "ok",
                    "sql": retry_sql,
                    "columns": retry_result["columns"],
                    "rows": retry_result["rows"],
                    "error": None,
                    "llm_response": retry_response,
                }

    return {
        "status": query_result["status"],
        "sql": sql,
        "columns": query_result["columns"],
        "rows": query_result["rows"],
        "error": query_result["error"],
        "truncated": query_result.get("truncated", False),
        "llm_response": llm_response,
    }


def _smart_limit(sql: str, default: int) -> int:
    """Use a higher row limit for aggregation queries so we don't cut off groups."""
    upper = sql.upper()
    if "GROUP BY" in upper:
        return 500
    return default
