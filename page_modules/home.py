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


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


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
    total_tests = int(row.get("TOTAL_TESTS_RUN") or 0)
    total_models = int(row.get("TOTAL_MODELS_RUN") or 0)

    # Health status banner
    if total_failures == 0:
        st.success("All systems healthy")
    else:
        st.error(f"{total_failures} active failures need attention")

    st.divider()

    # KPI row - 6 metrics
    cols = st.columns(6)
    with cols[0]:
        st.metric("Failed Tests", failed_tests)
    with cols[1]:
        st.metric("Failed Models", failed_models)
    with cols[2]:
        st.metric("Total Models", total_models)
    with cols[3]:
        st.metric("Total Tests", total_tests)
    with cols[4]:
        avg_time = row["AVG_EXECUTION_TIME"]
        st.metric("Avg Runtime", f"{avg_time:.1f}s" if avg_time else "N/A")
    with cols[5]:
        st.metric("Last Run", _format_timestamp(row["LAST_RUN_TIME"]))

    st.divider()

    # Two column layout: Needs Attention + Recent Runs
    col_failures, col_runs = st.columns(2)

    with col_failures:
        st.subheader("Needs Attention")
        failures = get_top_failures(limit=8)
        if failures.empty:
            st.info("No current failures")
        else:
            for _, f_row in failures.iterrows():
                icon = ":test_tube:" if f_row["TYPE"] == "test" else ":package:"
                schema = f_row["SCHEMA_NAME"] or "unknown"
                name = _truncate(f_row["NAME"])
                unique_id = f_row["UNIQUE_ID"]

                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"{icon} **{name}**")
                        st.caption(f"{schema} | {_format_timestamp(f_row['FAILED_AT'])}")
                    with col2:
                        if f_row["TYPE"] == "test":
                            if st.button("View", key=f"home_test_{unique_id}"):
                                st.session_state["selected_test"] = unique_id
                                st.session_state["selected_model"] = None
                                st.rerun()
                        else:
                            if st.button("View", key=f"home_model_{unique_id}"):
                                st.session_state["selected_model"] = unique_id
                                st.session_state["selected_test"] = None
                                st.rerun()

    with col_runs:
        st.subheader("Recent Runs")
        runs = get_recent_runs(limit=8)
        if runs.empty:
            st.info("No recent runs")
        else:
            for _, r_row in runs.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{_format_timestamp(r_row['GENERATED_AT'])}**")
                    cmd = r_row["COMMAND"] or "dbt"
                    target = r_row["TARGET_NAME"] or ""
                    st.caption(f"{cmd} | {target}")

    st.divider()

    # Quick links section
    st.subheader("Quick Links")
    link_cols = st.columns(4)
    with link_cols[0]:
        with st.container(border=True):
            st.markdown("**Models**")
            st.caption(f"{total_models} total")
            if failed_models > 0:
                st.caption(f":red_circle: {failed_models} failed")
    with link_cols[1]:
        with st.container(border=True):
            st.markdown("**Tests**")
            st.caption(f"{total_tests} total")
            if total_tests > 0:
                pass_rate = ((total_tests - failed_tests) / total_tests) * 100
                st.caption(f"{pass_rate:.0f}% passing")
    with link_cols[2]:
        with st.container(border=True):
            st.markdown("**Alerts**")
            st.caption(f"{total_failures} active")
    with link_cols[3]:
        with st.container(border=True):
            st.markdown("**Performance**")
            avg = row["AVG_EXECUTION_TIME"]
            st.caption(f"Avg: {avg:.1f}s" if avg else "N/A")
