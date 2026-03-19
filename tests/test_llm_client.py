from llm.client import LLMClient


def test_llm_client_has_generate_sql() -> None:
    client = LLMClient()
    assert hasattr(client, "generate_sql")
