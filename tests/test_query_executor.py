from db.query_executor import execute_query


def test_query_executor_callable() -> None:
    assert callable(execute_query)
