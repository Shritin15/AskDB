from llm.prompts import nl_to_sql_prompt


def test_prompt_contains_question() -> None:
    prompt = nl_to_sql_prompt("Q", "{}")
    assert "Question: Q" in prompt
