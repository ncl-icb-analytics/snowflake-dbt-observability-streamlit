"""Runs page - View dbt invocations and model execution waterfall."""

import streamlit as st
import pandas as pd
import altair as alt
from services.runs_service import (
    get_invocations,
    get_invocations_count,
    get_invocation_details,
    get_invocation_models,
    get_invocation_tests,
)


def _format_duration(seconds) -> str:
    """Format duration in human-readable form."""
    if not seconds or seconds <= 0:
        return ""
    seconds = int(seconds)
    if seconds >= 3600:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    elif seconds >= 60:
        mins = seconds // 60
        secs = seconds % 60
        if secs > 0 and mins < 10:
            return f"{mins}m {secs}s"
        return f"{mins}m"
    else:
        return f"{seconds}s"


def _format_timestamp(ts):
    """Format timestamp for display."""
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
    # Check if viewing invocation detail
    if st.session_state.get("selected_invocation"):
        _render_invocation_detail(st.session_state["selected_invocation"])
        return

    st.title("Runs")

    # Filters
    col1, col2 = st.columns([1, 4])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="runs_days")

    # Get count and paginate
    count_df = get_invocations_count(days)
    total_runs = int(count_df.iloc[0]["TOTAL"]) if not count_df.empty else 0

    page_size = 20
    total_pages = max(1, (total_runs + page_size - 1) // page_size)

    if "runs_page" not in st.session_state:
        st.session_state["runs_page"] = 0

    current_page = st.session_state["runs_page"]
    if current_page >= total_pages:
        current_page = 0
        st.session_state["runs_page"] = 0

    offset = current_page * page_size
    df = get_invocations(days=days, limit=page_size, offset=offset)

    if df.empty:
        st.info("No runs found in this time range")
        return

    # Header with pagination
    header_cols = st.columns([3, 2])
    with header_cols[0]:
        st.write(f"**{total_runs} invocations**")
    with header_cols[1]:
        if total_pages > 1:
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button("← Prev", disabled=current_page == 0, key="runs_prev"):
                    st.session_state["runs_page"] = current_page - 1
                    st.rerun()
            with nav_cols[1]:
                st.caption(f"Page {current_page + 1} of {total_pages}")
            with nav_cols[2]:
                if st.button("Next →", disabled=current_page >= total_pages - 1, key="runs_next"):
                    st.session_state["runs_page"] = current_page + 1
                    st.rerun()

    # Render invocations list
    for _, row in df.iterrows():
        success = int(row["SUCCESS_COUNT"] or 0)
        fail = int(row["FAIL_COUNT"] or 0)
        skipped = int(row["SKIPPED_COUNT"] or 0)
        models_run = int(row["MODELS_RUN"] or 0)
        duration = row["DURATION_SECONDS"] or 0

        # Status icon
        if fail > 0:
            status_icon = "🔴"
        elif skipped > 0 and success == 0:
            status_icon = "⚪"
        else:
            status_icon = "🟢"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon} **{_format_timestamp(row['CREATED_AT'])}**")
                cmd = row["COMMAND"] or "dbt"
                target = row["TARGET_NAME"] or ""
                warehouse = row.get("WAREHOUSE") or ""
                info_parts = [cmd, target]
                if warehouse:
                    info_parts.append(warehouse)
                st.caption(" | ".join(p for p in info_parts if p))
                if row.get("SELECTED"):
                    st.caption(_truncate(row["SELECTED"], 60))
            with cols[1]:
                st.caption("Models")
                if fail > 0:
                    st.write(f"🟢 {success} 🔴 {fail}")
                else:
                    st.write(f"🟢 {success}")
            with cols[2]:
                st.caption("Duration")
                st.write(_format_duration(duration))
            with cols[3]:
                if st.button("View", key=f"run_{row['INVOCATION_ID']}"):
                    st.session_state["selected_invocation"] = row["INVOCATION_ID"]
                    st.rerun()


def _render_invocation_detail(invocation_id: str):
    """Render detail view for a specific invocation."""
    # Back button
    if st.button("← Back to Runs"):
        st.session_state["selected_invocation"] = None
        st.rerun()

    # Get invocation details
    details_df = get_invocation_details(invocation_id)
    if details_df.empty:
        st.error(f"Invocation not found: {invocation_id}")
        return

    details = details_df.iloc[0]

    # Header
    st.title(f"Run: {_format_timestamp(details['CREATED_AT'])}")
    st.caption(f"`{invocation_id}`")

    st.divider()

    # Metadata
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.markdown("**Command**")
        st.write(details.get("COMMAND") or "N/A")
    with meta_cols[1]:
        st.markdown("**Target**")
        st.write(details.get("TARGET_NAME") or "N/A")
    with meta_cols[2]:
        st.markdown("**Warehouse**")
        st.write(details.get("WAREHOUSE") or "N/A")
    with meta_cols[3]:
        st.markdown("**Duration**")
        st.write(_format_duration(details.get("DURATION_SECONDS") or 0))

    if details.get("SELECTED"):
        st.markdown("**Selection:**")
        st.code(details["SELECTED"], language=None)

    st.divider()

    # Tabs for models and tests
    tab_models, tab_tests, tab_waterfall = st.tabs(["Models", "Tests", "Timeline"])

    with tab_models:
        _render_invocation_models(invocation_id)

    with tab_tests:
        _render_invocation_tests(invocation_id)

    with tab_waterfall:
        _render_waterfall_chart(invocation_id, details)


def _render_invocation_models(invocation_id: str):
    """Render models for an invocation."""
    df = get_invocation_models(invocation_id)

    if df.empty:
        st.info("No model runs in this invocation")
        return

    # Summary
    success = len(df[df["STATUS"] == "success"])
    fail = len(df[df["STATUS"].isin(["fail", "error"])])
    skipped = len(df[df["STATUS"] == "skipped"])

    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Total Models", len(df))
    with summary_cols[1]:
        st.metric("Success", success)
    with summary_cols[2]:
        st.metric("Failed", fail)
    with summary_cols[3]:
        st.metric("Skipped", skipped)

    st.divider()

    # Model list - show failures first
    df_sorted = df.sort_values(
        by="STATUS",
        key=lambda x: x.map({"fail": 0, "error": 0, "skipped": 1, "success": 2})
    )

    for _, row in df_sorted.iterrows():
        status = row["STATUS"].lower()
        if status == "success":
            status_icon = "🟢"
        elif status == "skipped":
            status_icon = "⚪"
        else:
            status_icon = "🔴"

        time_str = f"{row['EXECUTION_TIME']:.1f}s" if row["EXECUTION_TIME"] else ""

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon} **{row['NAME']}**")
                if row.get("MODEL_PATH"):
                    st.caption(_truncate(row["MODEL_PATH"], 60))
            with cols[1]:
                st.caption("Status")
                st.write(status.upper())
            with cols[2]:
                if time_str:
                    st.caption("Time")
                    st.write(time_str)
            with cols[3]:
                if st.button("View", key=f"inv_model_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_invocation"] = None
                    st.rerun()

            if row.get("MESSAGE") and status in ("fail", "error"):
                st.error(row["MESSAGE"])


def _render_invocation_tests(invocation_id: str):
    """Render tests for an invocation."""
    df = get_invocation_tests(invocation_id)

    if df.empty:
        st.info("No test runs in this invocation")
        return

    # Summary
    passed = len(df[df["STATUS"] == "pass"])
    failed = len(df[df["STATUS"].isin(["fail", "error"])])
    warned = len(df[df["STATUS"] == "warn"])

    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Total Tests", len(df))
    with summary_cols[1]:
        st.metric("Passed", passed)
    with summary_cols[2]:
        st.metric("Failed", failed)
    with summary_cols[3]:
        st.metric("Warned", warned)

    st.divider()

    for _, row in df.iterrows():
        status = row["STATUS"].lower()
        if status == "pass":
            status_icon = "🟢"
        elif status == "warn":
            status_icon = "🟡"
        else:
            status_icon = "🔴"

        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon} **{row['MODEL_NAME'] or 'N/A'}**")
                test_ns = row.get("TEST_NAMESPACE") or ""
                st.caption(f"{row['TEST_NAME']} | {test_ns}" if test_ns else row["TEST_NAME"])
            with cols[1]:
                st.caption("Status")
                st.write(status.upper())
            with cols[2]:
                if st.button("View", key=f"inv_test_{row['TEST_UNIQUE_ID']}"):
                    st.session_state["selected_test"] = row["TEST_UNIQUE_ID"]
                    st.session_state["selected_invocation"] = None
                    st.rerun()

            if row.get("TEST_RESULTS_DESCRIPTION") and status in ("fail", "error", "warn"):
                if status == "warn":
                    st.warning(row["TEST_RESULTS_DESCRIPTION"])
                else:
                    st.error(row["TEST_RESULTS_DESCRIPTION"])


def _render_waterfall_chart(invocation_id: str, details):
    """Render a waterfall/Gantt chart of model execution."""
    df = get_invocation_models(invocation_id)

    if df.empty:
        st.info("No model timing data available")
        return

    # Filter to models with timing data
    timing_df = df[df["EXECUTE_STARTED_AT"].notna() & df["EXECUTE_COMPLETED_AT"].notna()].copy()

    if timing_df.empty:
        st.info("No execution timing data available for waterfall chart")
        return

    # Convert to datetime (remove timezone to avoid tz-naive/tz-aware mismatch)
    timing_df["START"] = pd.to_datetime(timing_df["EXECUTE_STARTED_AT"]).dt.tz_localize(None)
    timing_df["END"] = pd.to_datetime(timing_df["EXECUTE_COMPLETED_AT"]).dt.tz_localize(None)

    # Get run start time as reference
    run_start = pd.to_datetime(details.get("RUN_STARTED_AT"))
    if hasattr(run_start, 'tz_localize'):
        run_start = run_start.tz_localize(None) if run_start.tzinfo else run_start
    elif hasattr(run_start, 'tzinfo') and run_start.tzinfo is not None:
        run_start = run_start.replace(tzinfo=None)
    if pd.isna(run_start):
        run_start = timing_df["START"].min()

    # Calculate relative times in seconds from run start
    timing_df["START_SEC"] = (timing_df["START"] - run_start).dt.total_seconds()
    timing_df["END_SEC"] = (timing_df["END"] - run_start).dt.total_seconds()

    # Color by status
    status_colors = {
        "success": "#28a745",
        "fail": "#dc3545",
        "error": "#dc3545",
        "skipped": "#6c757d",
    }
    timing_df["COLOR"] = timing_df["STATUS"].map(lambda x: status_colors.get(x, "#6c757d"))

    st.subheader("Execution Timeline")
    st.caption(f"{len(timing_df)} models with timing data")

    # Create Gantt-style chart
    chart = alt.Chart(timing_df).mark_bar().encode(
        x=alt.X("START_SEC:Q", title="Seconds from run start"),
        x2=alt.X2("END_SEC:Q"),
        y=alt.Y("NAME:N", title="Model", sort=alt.EncodingSortField(field="START_SEC", order="ascending")),
        color=alt.Color(
            "STATUS:N",
            scale=alt.Scale(
                domain=["success", "fail", "error", "skipped"],
                range=["#28a745", "#dc3545", "#dc3545", "#6c757d"]
            ),
            legend=alt.Legend(title="Status")
        ),
        tooltip=[
            alt.Tooltip("NAME:N", title="Model"),
            alt.Tooltip("STATUS:N", title="Status"),
            alt.Tooltip("EXECUTION_TIME:Q", title="Duration (s)", format=".1f"),
            alt.Tooltip("START_SEC:Q", title="Start (s)", format=".1f"),
            alt.Tooltip("END_SEC:Q", title="End (s)", format=".1f"),
        ]
    ).properties(
        height=max(200, len(timing_df) * 20)
    )

    st.altair_chart(chart, use_container_width=True)

    # Show summary stats
    total_time = timing_df["EXECUTION_TIME"].sum()
    max_end = timing_df["END_SEC"].max()
    parallelism = total_time / max_end if max_end > 0 else 1

    stat_cols = st.columns(3)
    with stat_cols[0]:
        st.metric("Total Model Time", _format_duration(total_time))
    with stat_cols[1]:
        st.metric("Wall Clock Time", _format_duration(max_end))
    with stat_cols[2]:
        st.metric("Avg Parallelism", f"{parallelism:.1f}x")
