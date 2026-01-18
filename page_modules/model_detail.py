"""Model detail page - Full view of a single model."""

import streamlit as st
from services.models_service import (
    get_model_details,
    get_model_run_history,
    get_model_execution_trend,
    get_model_row_count_history,
    get_model_latest_row_count,
)
from services.tests_service import get_tests_for_model
from components.charts import execution_time_chart, run_status_timeline, row_count_trend_chart
from config import DEFAULT_LOOKBACK_DAYS


def _format_row_count(count) -> str:
    """Format row count with K/M/B suffixes."""
    if count is None:
        return "N/A"
    count = int(count)
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def render(unique_id: str):
    """Render full model detail page."""
    # Back button
    if st.button("← Back to Models"):
        st.session_state["selected_model"] = None
        st.rerun()

    # Get model details
    details_df = get_model_details(unique_id)
    if details_df.empty:
        st.error(f"Model not found: {unique_id}")
        return

    details = details_df.iloc[0]

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(details["NAME"])
        st.caption(f"`{unique_id}`")
    with col2:
        schema = details.get("SCHEMA_NAME") or "unknown"
        st.markdown(f"**Schema:** {schema}")
        if details.get("DATABASE_NAME"):
            st.markdown(f"**Database:** {details['DATABASE_NAME']}")

    st.divider()

    # Metadata section
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.markdown(f"**Materialization**")
        st.write(details.get("MATERIALIZATION") or "N/A")
    with meta_cols[1]:
        st.markdown(f"**Owner**")
        st.write(details.get("OWNER") or "N/A")
    with meta_cols[2]:
        st.markdown(f"**Tags**")
        st.write(details.get("TAGS") or "None")
    with meta_cols[3]:
        st.markdown(f"**Path**")
        st.code(details.get("ORIGINAL_PATH") or "N/A", language=None)

    if details.get("DESCRIPTION"):
        st.markdown("**Description:**")
        st.markdown(details["DESCRIPTION"])

    st.divider()

    # Run history section
    days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="model_detail_days")

    history_df = get_model_run_history(unique_id, days)

    if history_df.empty:
        st.info("No runs in this time range")
        return

    # Stats row
    latest = history_df.iloc[0]
    total_runs = len(history_df)
    success_runs = len(history_df[history_df["STATUS"] == "success"])
    avg_time = history_df["EXECUTION_TIME"].mean()

    # Get latest row count (only for table models)
    latest_row_count_df = get_model_latest_row_count(details["NAME"])
    has_row_count = not latest_row_count_df.empty

    stat_cols = st.columns(5)
    with stat_cols[0]:
        status = latest["STATUS"].upper()
        st.metric("Last Status", status)
    with stat_cols[1]:
        st.metric("Avg Time", f"{avg_time:.1f}s" if avg_time else "N/A")
    with stat_cols[2]:
        st.metric("Run Count", total_runs)
    with stat_cols[3]:
        pass_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0
        st.metric("Success Rate", f"{pass_rate:.0f}%")
    with stat_cols[4]:
        if has_row_count:
            row_data = latest_row_count_df.iloc[0]
            row_count = row_data["ROW_COUNT"]
            row_change = row_data.get("ROW_CHANGE")
            change_pct = row_data.get("CHANGE_PCT")

            # Format delta string with sign
            if row_change is not None and change_pct is not None:
                delta_str = f"{'+' if row_change >= 0 else ''}{_format_row_count(int(row_change))} ({change_pct:+.1f}%)"
                delta_color = "normal" if row_change >= 0 else "inverse"
                st.metric("Row Count", _format_row_count(row_count), delta=delta_str, delta_color=delta_color)
            else:
                st.metric("Row Count", _format_row_count(row_count))
        else:
            st.metric("Row Count", "N/A")

    st.caption(f"Last run: {latest['GENERATED_AT']}")

    # Run history timeline
    st.subheader("Run History")
    st.altair_chart(run_status_timeline(history_df), use_container_width=True)

    # Recent runs with details
    for _, row in history_df.head(10).iterrows():
        status_icon = "🟢" if row["STATUS"] == "success" else "🔴"
        time_str = f"{row['EXECUTION_TIME']:.1f}s" if row["EXECUTION_TIME"] else "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon} **{row['STATUS'].upper()}**")
            with cols[1]:
                st.caption(f"{time_str}")
            with cols[2]:
                st.caption(str(row["GENERATED_AT"])[:16])

            if row.get("MESSAGE") and row["STATUS"] in ("fail", "error"):
                st.error(row["MESSAGE"])

    # Execution trend
    trend_df = get_model_execution_trend(unique_id, days)
    if not trend_df.empty and len(trend_df) > 1:
        st.subheader("Execution Time Trend")
        st.altair_chart(execution_time_chart(trend_df), use_container_width=True)

    # Row count trend (only for table models with row count data)
    if has_row_count:
        row_count_df = get_model_row_count_history(details["NAME"], days)
        if not row_count_df.empty and len(row_count_df) > 1:
            st.subheader("Row Count Trend")
            st.altair_chart(row_count_trend_chart(row_count_df), use_container_width=True)

    # Related tests
    st.divider()
    st.subheader("Related Tests")
    tests_df = get_tests_for_model(details["NAME"])
    if tests_df.empty:
        st.info("No tests found for this model")
    else:
        for _, test_row in tests_df.iterrows():
            latest_status = (test_row.get("LATEST_STATUS") or "").lower()
            icon = "🟢" if latest_status == "pass" else "🔴"

            if st.button(f"{icon} {test_row['TEST_NAME']}", key=f"test_{test_row['TEST_UNIQUE_ID']}"):
                st.session_state["selected_test"] = test_row["TEST_UNIQUE_ID"]
                st.session_state["selected_model"] = None
                st.rerun()
