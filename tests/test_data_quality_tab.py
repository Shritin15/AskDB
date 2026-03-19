from app.ui.data_quality_tab import render_data_quality_tab


def test_data_quality_tab_symbol_exists() -> None:
    assert callable(render_data_quality_tab)
