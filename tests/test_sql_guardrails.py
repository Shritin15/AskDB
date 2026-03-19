from db.sql_guardrails import validate_select_only


def test_sql_guardrails_blocks_delete() -> None:
    ok, _ = validate_select_only("DELETE FROM users")
    assert ok is False
