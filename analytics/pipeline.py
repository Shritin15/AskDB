from llm.nl_to_sql_service import generate_sql_from_question
from db.query_executor import execute_query


def ask_question(question: str, db_path: str, limit: int = 100) -> dict:
    """
    End-to-end pipeline:
    1) NL → SQL (via LLM)
    2) Validate + execute SQL safely
    3) Return structured response
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

    # 2️ Execute safely
    query_result = execute_query(db_path, sql, limit=limit)

    return {
        "status": query_result["status"],
        "sql": sql,
        "columns": query_result["columns"],
        "rows": query_result["rows"],
        "error": query_result["error"],
        "llm_response": llm_response,
    }