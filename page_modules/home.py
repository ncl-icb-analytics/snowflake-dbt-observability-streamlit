"""Home page - Overview dashboard with KPIs."""

import streamlit as st
from services.metrics_service import get_dashboard_kpis, get_recent_runs, get_top_failures, get_project_totals, get_total_execution_time


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

    # Get total project counts (all models/tests, not just recent runs)
    totals = get_project_totals()
    if not totals.empty:
        total_models = int(totals.iloc[0]["TOTAL_MODELS"] or 0)
        total_tests = int(totals.iloc[0]["TOTAL_TESTS"] or 0)
    else:
        total_models = 0
        total_tests = 0

    row = kpis.iloc[0]
    failed_tests = int(row["FAILED_TESTS"] or 0)
    failed_models = int(row["FAILED_MODELS"] or 0)
    total_failures = failed_tests + failed_models
    models_run = int(row.get("TOTAL_MODELS_RUN") or 0)
    tests_run = int(row.get("TOTAL_TESTS_RUN") or 0)

    # Health status banner
    if total_failures == 0:
        st.success("All systems healthy")
    else:
        st.error(f"{total_failures} active failures need attention")

    st.divider()

    # Get total execution time
    exec_time_df = get_total_execution_time()
    total_exec_time = exec_time_df.iloc[0]["TOTAL_TIME"] if not exec_time_df.empty else 0

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
        if total_exec_time:
            st.metric("Total Runtime", f"{total_exec_time / 60:.1f} min")
        else:
            st.metric("Total Runtime", "N/A")
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
                name = _truncate(f_row["NAME"])
                unique_id = f_row["UNIQUE_ID"]

                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"{icon} **{name}**")
                        # Show test namespace and model for tests, schema for models
                        if f_row["TYPE"] == "test":
                            test_ns = f_row.get("TEST_NAMESPACE") or ""
                            model = f_row.get("MODEL_NAME") or ""
                            info_parts = [p for p in [test_ns, model] if p]
                            st.caption(" | ".join(info_parts) if info_parts else "")
                        else:
                            schema = f_row["SCHEMA_NAME"] or "unknown"
                            st.caption(schema)
                        st.caption(_format_timestamp(f_row['FAILED_AT']))
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
                    # Use created_at (TIMESTAMP_NTZ) for display
                    st.markdown(f"**{_format_timestamp(r_row['CREATED_AT'])}**")
                    cmd = r_row["COMMAND"] or "dbt"
                    target = r_row["TARGET_NAME"] or ""
                    warehouse = r_row.get("WAREHOUSE") or ""
                    models_run = int(r_row.get("MODELS_RUN") or 0)
                    success = int(r_row.get("SUCCESS_COUNT") or 0)
                    fail = int(r_row.get("FAIL_COUNT") or 0)
                    duration = r_row.get("DURATION_SECONDS") or 0

                    # First line: command, target, warehouse
                    info_parts = [cmd, target]
                    if warehouse:
                        info_parts.append(warehouse)
                    st.caption(" | ".join(p for p in info_parts if p))

                    # Second line: run stats (use markdown for emoji rendering)
                    if models_run > 0:
                        # Format duration nicely
                        if duration and duration > 0:
                            if duration >= 3600:
                                time_str = f"{duration / 3600:.1f}h"
                            elif duration >= 60:
                                time_str = f"{duration / 60:.1f}m"
                            else:
                                time_str = f"{duration:.0f}s"
                        else:
                            time_str = ""
                        if fail > 0:
                            st.markdown(f"{models_run} models | :green_circle: {success} :red_circle: {fail} | {time_str}")
                        else:
                            st.markdown(f"{models_run} models | :green_circle: {success} | {time_str}")

    st.divider()

    # Summary cards section
    st.subheader("Summary")
    summary_cols = st.columns(4)
    with summary_cols[0]:
        with st.container(border=True):
            st.markdown("**Models**")
            st.caption(f"{total_models} total")
            if failed_models > 0:
                st.markdown(f":red_circle: {failed_models} failed")
            else:
                st.markdown(":green_circle: All healthy")
    with summary_cols[1]:
        with st.container(border=True):
            st.markdown("**Tests**")
            st.caption(f"{total_tests} total")
            if tests_run > 0:
                pass_rate = ((tests_run - failed_tests) / tests_run) * 100
                st.caption(f"{pass_rate:.0f}% passing")
    with summary_cols[2]:
        with st.container(border=True):
            st.markdown("**Alerts**")
            if total_failures > 0:
                st.markdown(f":red_circle: {total_failures} active")
            else:
                st.markdown(":green_circle: None")
    with summary_cols[3]:
        with st.container(border=True):
            st.markdown("**Performance**")
            if total_exec_time:
                st.caption(f"{total_exec_time / 60:.1f} min total")
