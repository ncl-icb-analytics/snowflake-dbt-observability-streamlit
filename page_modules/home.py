"""Home page - Overview dashboard with KPIs."""

import streamlit as st
from services.metrics_service import get_dashboard_kpis, get_recent_runs, get_top_failures


def _format_timestamp(ts):
    """Format timestamp handling both datetime and string types."""
    if ts is None:
        return "N/A"
    try:
        return ts.strftime("%Y-%m-%d %H:%M")
    except AttributeError:
        return str(ts)[:16] if ts else "N/A"


def render(search_filter: str = ""):
    st.title("dbt Project Health")

    kpis = get_dashboard_kpis()
    if kpis.empty:
        st.warning("No data available")
        return

    row = kpis.iloc[0]
    failed_tests = int(row["FAILED_TESTS"] or 0)
    failed_models = int(row["FAILED_MODELS"] or 0)
    total_failures = failed_tests + failed_models

    # Hero section - overall health status
    if total_failures == 0:
        st.success("All systems healthy - no current failures")
    else:
        st.error(f"{total_failures} active failures need attention")

    st.divider()

    # KPI cards in a row
    cols = st.columns(4)
    with cols[0]:
        st.metric("Failed Tests", failed_tests)
    with cols[1]:
        st.metric("Failed Models", failed_models)
    with cols[2]:
        avg_time = row["AVG_EXECUTION_TIME"]
        st.metric("Avg Runtime", f"{avg_time:.1f}s" if avg_time else "N/A")
    with cols[3]:
        st.metric("Last Run", _format_timestamp(row["LAST_RUN_TIME"]))

    st.divider()

    # Main content area - 3 column layout
    col_failures, col_runs, col_stats = st.columns([2, 2, 1])

    with col_failures:
        st.subheader("Needs Attention")
        failures = get_top_failures()
        if failures.empty:
            st.info("No current failures")
        else:
            for _, f_row in failures.iterrows():
                icon = ":test_tube:" if f_row["TYPE"] == "test" else ":package:"
                schema = f_row["SCHEMA_NAME"] or "unknown"
                with st.container(border=True):
                    st.markdown(f"{icon} **{f_row['NAME']}**")
                    st.caption(f"{schema} | {_format_timestamp(f_row['FAILED_AT'])}")

    with col_runs:
        st.subheader("Recent Runs")
        runs = get_recent_runs(limit=5)
        if runs.empty:
            st.info("No recent runs")
        else:
            for _, r_row in runs.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{_format_timestamp(r_row['GENERATED_AT'])}**")
                    st.caption(f"{r_row['COMMAND']} | {r_row['TARGET_NAME']}")

    with col_stats:
        st.subheader("Summary")
        total_tests = int(row.get("TOTAL_TESTS_RUN") or 0)
        total_models = int(row.get("TOTAL_MODELS_RUN") or 0)
        st.metric("Tests Run", total_tests)
        st.metric("Models Run", total_models)
        if total_tests > 0:
            pass_rate = ((total_tests - failed_tests) / total_tests) * 100
            st.metric("Test Pass Rate", f"{pass_rate:.0f}%")
