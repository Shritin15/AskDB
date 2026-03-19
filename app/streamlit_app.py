"""Main Streamlit application entrypoint."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.ask_data_tab import render_ask_data_tab
from app.ui.data_quality_tab import render_data_quality_tab


def main() -> None:
    st.set_page_config(page_title="LLM Analytics Copilot", layout="wide")
    st.title("LLM Analytics Copilot + Data Quality Guardian")

    ask_tab, dq_tab = st.tabs(["Ask the Data", "Data Quality"])

    with ask_tab:
        render_ask_data_tab()

    with dq_tab:
        render_data_quality_tab()


if __name__ == "__main__":
    main()
