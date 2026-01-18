"""Alerts page - Current test and model failures with click navigation."""

import streamlit as st
from services.alerts_service import get_current_test_failures, get_current_model_failures, get_alert_counts


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def render(search_filter: str = ""):
    st.title("Alerts")

    # Filters
    col1, _ = st.columns([1, 4])
    with col1:
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

    # Side-by-side layout
    test_col, model_col = st.columns(2)

    with test_col:
        st.subheader(f"Test Failures ({failed_tests})")
        _render_test_failures(days, search_filter)

    with model_col:
        st.subheader(f"Model Failures ({failed_models})")
        _render_model_failures(days, search_filter)


def _render_test_failures(days: int, search_filter: str):
    """Render test failures with click navigation."""
    df = get_current_test_failures(days, search_filter)

    if df.empty:
        st.info("No test failures")
        return

    for _, row in df.iterrows():
        # Use short_name if available, fall back to test_name
        short_name = row.get("SHORT_NAME") or row["TEST_NAME"]
        name = _truncate(short_name)
        model = row["TABLE_NAME"] or "N/A"
        test_ns = row.get("TEST_NAMESPACE") or row["TEST_TYPE"] or ""

        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"🔴 **{name}**")
                st.caption(f"{model} | {test_ns}" if test_ns else model)
                st.caption(f"{row['SCHEMA_NAME']} | {str(row['DETECTED_AT'])[:16]}")
            with cols[1]:
                if st.button("View", key=f"alert_test_{row['TEST_UNIQUE_ID']}"):
                    st.session_state["selected_test"] = row["TEST_UNIQUE_ID"]
                    st.session_state["selected_model"] = None
                    st.rerun()


def _render_model_failures(days: int, search_filter: str):
    """Render model failures with click navigation."""
    df = get_current_model_failures(days, search_filter)

    if df.empty:
        st.info("No model failures")
        return

    for _, row in df.iterrows():
        name = _truncate(row["NAME"])
        schema = row["SCHEMA_NAME"] or "unknown"

        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"🔴 **{name}**")
                st.caption(f"{schema} | {row['STATUS']}")
                if row["EXECUTION_TIME"]:
                    st.caption(f"{row['EXECUTION_TIME']:.1f}s | {str(row['GENERATED_AT'])[:16]}")
                else:
                    st.caption(str(row["GENERATED_AT"])[:16])
            with cols[1]:
                if st.button("View", key=f"alert_model_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()
