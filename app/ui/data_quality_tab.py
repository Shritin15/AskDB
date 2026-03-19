"""UI tab for data quality profiling."""

from __future__ import annotations

import streamlit as st

from db.connection import get_db_path
from db.schema_introspector import get_schema_metadata
from data_quality.profiler import profile_table
from data_quality.scoring import confidence_from_profile


def render_data_quality_tab() -> None:
    st.subheader("Data Quality")

    try:
        schema = get_schema_metadata(get_db_path())
    except Exception as exc:
        st.error(f"Could not inspect database schema: {exc}")
        return

    tables = sorted(schema.keys())
    if not tables:
        st.warning("No tables found. Run scripts/create_db.py first.")
        return

    selected_table = st.selectbox("Select a table", tables)

    if st.button("Run Profile", key="dq_profile"):
        profile = profile_table(get_db_path(), selected_table)
        confidence = confidence_from_profile(profile)
        st.json({"profile": profile, "confidence": confidence})
