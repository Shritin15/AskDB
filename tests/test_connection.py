from db.connection import get_db_path


def test_db_path_suffix() -> None:
    assert str(get_db_path()).endswith("data\\app.db") or str(get_db_path()).endswith("data/app.db")
