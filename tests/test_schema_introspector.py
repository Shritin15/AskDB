from db.schema_introspector import get_schema_metadata


def test_schema_introspector_callable() -> None:
    assert callable(get_schema_metadata)
