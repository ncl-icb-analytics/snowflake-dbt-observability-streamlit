"""Alerts page - Current test and model failures."""

import streamlit as st
from services.alerts_service import get_current_test_failures, get_current_model_failures, get_alert_counts


def render(search_filter: str = ""):
    st.title("Alerts")

    # Filters
    filter_cols = st.columns([1, 2, 3])
    with filter_cols[0]:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d")

    # Alert counts summary
    counts = get_alert_counts(days)
    if counts.empty:
        st.info("No data available")
        return

    row = counts.iloc[0]
    failed_tests = int(row["FAILED_TESTS"] or 0)
    failed_models = int(row["FAILED_MODELS"] or 0)
    total_failures = failed_tests + failed_models

    if total_failures == 0:
        st.success("No current failures - all tests and models are passing")
        return

    # Summary metrics
    metric_cols = st.columns(3)
    with metric_cols[0]:
        st.metric("Total Failures", total_failures)
    with metric_cols[1]:
        st.metric("Test Failures", failed_tests)
    with metric_cols[2]:
        st.metric("Model Failures", failed_models)

    st.divider()

    # Side-by-side layout for tests and models
    test_col, model_col = st.columns(2)

    with test_col:
        st.subheader(f"Test Failures ({failed_tests})")
        _render_test_failures(days, search_filter)

    with model_col:
        st.subheader(f"Model Failures ({failed_models})")
        _render_model_failures(days, search_filter)


def _render_test_failures(days: int, search_filter: str):
    """Render test failures."""
    df = get_current_test_failures(days, search_filter)

    if df.empty:
        st.info("No test failures")
        return

    for _, row in df.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['TEST_NAME']}**")
            st.caption(f"{row['TABLE_NAME'] or 'N/A'} | {row['TEST_TYPE']}")

            with st.expander("Details"):
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Schema:** {row['SCHEMA_NAME']}")
                    st.markdown(f"**Status:** {row['STATUS']}")
                with cols[1]:
                    st.markdown(f"**Detected:** {row['DETECTED_AT']}")
                    if row["COLUMN_NAME"]:
                        st.markdown(f"**Column:** {row['COLUMN_NAME']}")

                if row["TEST_RESULTS_DESCRIPTION"]:
                    st.code(row["TEST_RESULTS_DESCRIPTION"], language=None)

                if row["TEST_RESULTS_QUERY"]:
                    st.markdown("**Debug Query:**")
                    st.code(row["TEST_RESULTS_QUERY"], language="sql")


def _render_model_failures(days: int, search_filter: str):
    """Render model failures."""
    df = get_current_model_failures(days, search_filter)

    if df.empty:
        st.info("No model failures")
        return

    for _, row in df.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['NAME']}**")
            schema = row['SCHEMA_NAME'] or 'unknown'
            st.caption(f"{schema} | {row['STATUS']}")

            with st.expander("Details"):
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Database:** {row['DATABASE_NAME']}")
                    st.markdown(f"**Schema:** {schema}")
                with cols[1]:
                    st.markdown(f"**Last Run:** {row['GENERATED_AT']}")
                    if row["EXECUTION_TIME"]:
                        st.markdown(f"**Time:** {row['EXECUTION_TIME']:.1f}s")

                if row.get("MESSAGE"):
                    st.error(row["MESSAGE"])

                st.caption(f"`{row['UNIQUE_ID']}`")
