from pathlib import Path
import streamlit as st

from analytics.pipeline import ask_question
from analytics.visualization import rows_to_df, decide_viz
from llm.insight_service import generate_insight


def render_ask_data_tab():
    st.header("Ask the Data")

    question = st.text_input(
        "Enter a business question",
        placeholder="e.g., Show total orders by status",
    )

    if st.button("Submit") and question.strip():
        db_path = Path("data/datasets/chinook.sqlite")

        with st.spinner("Generating SQL and executing query..."):
            result = ask_question(question, db_path)

        if result["status"] == "ok":
            st.success("Query executed successfully")

            st.subheader("Generated SQL")
            st.code(result["sql"], language="sql")

            # Convert to DataFrame
            df = rows_to_df(result["columns"], result["rows"])

            st.subheader("Results")
            st.dataframe(df, use_container_width=True)

            # Auto chart
            st.subheader("Chart")
            decision = decide_viz(df)

            if decision.kind == "metric":
                st.metric(label=decision.y, value=df.iloc[0][decision.y])
            elif decision.kind == "bar":
                st.bar_chart(df.set_index(decision.x)[decision.y])
            elif decision.kind == "line":
                # For line chart, try to sort by x if it's datetime-like
                df_sorted = df.copy()
                df_sorted[decision.x] = df_sorted[decision.x].astype(str)
                st.line_chart(df_sorted.set_index(decision.x)[decision.y])
            else:
                st.info("No clear chart pattern detected for this result.")

            # BI insight
            with st.spinner("Generating business insights..."):
                insight = generate_insight(
                    question=question,
                    sql=result["sql"],
                    rows=result["rows"],
                    dq_confidence="High",  # placeholder for now
                )

            if insight:
                st.subheader("AI Business Insight")
                st.markdown(f"### {insight.get('headline', '')}")

                findings = insight.get("key_findings", [])
                if findings:
                    st.markdown("**Key Findings:**")
                    for f in findings:
                        st.write(f"- {f}")

                caveats = insight.get("caveats", [])
                if caveats:
                    st.markdown("**Caveats:**")
                    for c in caveats:
                        st.write(f"- {c}")

                st.markdown(f"**Confidence:** {insight.get('confidence', 'N/A')}")

        elif result["status"] == "rejected":
            st.warning("Request rejected by LLM")
            st.write(result.get("reason"))

        else:
            st.error("Error executing query")
            st.write(result.get("error"))