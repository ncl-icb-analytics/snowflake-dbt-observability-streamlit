"""Alerts page - Current test and model failures."""

import streamlit as st
from services.alerts_service import get_current_test_failures, get_current_model_failures, get_alert_counts
from config import DEFAULT_LOOKBACK_DAYS


def render(search_filter: str = ""):
    st.title("Alerts")
    st.caption("Shows only current failures (hidden if fixed by a more recent successful run)")

    # Filters
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days")

    # Alert counts summary
    counts = get_alert_counts(days)
    if not counts.empty:
        row = counts.iloc[0]
        failed_tests = int(row["FAILED_TESTS"] or 0)
        failed_models = int(row["FAILED_MODELS"] or 0)

        if failed_tests == 0 and failed_models == 0:
            st.success("No current failures")
            return

        st.metric(
            "Current Failures",
            failed_tests + failed_models,
            delta=f"{failed_tests} tests, {failed_models} models",
            delta_color="off",
        )

    # Tabs for tests vs models
    tab_tests, tab_models = st.tabs(["Test Failures", "Model Failures"])

    with tab_tests:
        _render_test_failures(days, search_filter)

    with tab_models:
        _render_model_failures(days, search_filter)


def _render_test_failures(days: int, search_filter: str):
    """Render test failures table with expandable details."""
    df = get_current_test_failures(days, search_filter)

    if df.empty:
        st.success("No test failures")
        return

    st.write(f"**{len(df)} test failures**")

    for _, row in df.iterrows():
        with st.expander(f":red_circle: {row['TEST_NAME']} on {row['TABLE_NAME'] or 'N/A'}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Schema:** {row['SCHEMA_NAME']}")
                st.markdown(f"**Type:** {row['TEST_TYPE']}")
                st.markdown(f"**Status:** {row['STATUS']}")
            with col2:
                st.markdown(f"**Detected:** {row['DETECTED_AT']}")
                if row["COLUMN_NAME"]:
                    st.markdown(f"**Column:** {row['COLUMN_NAME']}")

            if row["TEST_RESULTS_DESCRIPTION"]:
                st.markdown("**Description:**")
                st.code(row["TEST_RESULTS_DESCRIPTION"], language=None)

            if row["TEST_RESULTS_QUERY"]:
                st.markdown("**Debug Query:**")
                st.code(row["TEST_RESULTS_QUERY"], language="sql")


def _render_model_failures(days: int, search_filter: str):
    """Render model failures table with expandable details."""
    df = get_current_model_failures(days, search_filter)

    if df.empty:
        st.success("No model failures")
        return

    st.write(f"**{len(df)} model failures**")

    for _, row in df.iterrows():
        with st.expander(f":red_circle: {row['NAME']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Schema:** {row['SCHEMA_NAME']}")
                st.markdown(f"**Database:** {row['DATABASE_NAME']}")
                st.markdown(f"**Status:** {row['STATUS']}")
            with col2:
                st.markdown(f"**Last Run:** {row['GENERATED_AT']}")
                if row["EXECUTION_TIME"]:
                    st.markdown(f"**Execution Time:** {row['EXECUTION_TIME']:.1f}s")

            st.markdown(f"**Unique ID:** `{row['UNIQUE_ID']}`")
