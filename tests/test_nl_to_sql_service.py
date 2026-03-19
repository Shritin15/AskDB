from llm.nl_to_sql_service import generate_sql_from_question


def test_nl_to_sql_service_callable() -> None:
    assert callable(generate_sql_from_question)
