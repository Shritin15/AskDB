from llm.insight_service import generate_insight


def test_insight_service_callable() -> None:
    assert callable(generate_insight)
