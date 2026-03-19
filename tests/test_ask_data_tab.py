from app.ui.ask_data_tab import render_ask_data_tab


def test_ask_data_tab_symbol_exists() -> None:
    assert callable(render_ask_data_tab)
