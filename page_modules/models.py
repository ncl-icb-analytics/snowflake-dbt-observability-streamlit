"""Models page - Run history and performance."""

import streamlit as st
from services.models_service import (
    get_models_summary,
    get_model_run_history,
    get_model_execution_trend,
    get_model_details,
)
from components.charts import execution_time_chart, run_status_timeline
from config import DEFAULT_LOOKBACK_DAYS


def render(search_filter: str = ""):
    st.title("Models")

    # Filters in compact row
    filter_cols = st.columns([1, 1, 2, 2])
    with filter_cols[0]:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="models_days")
    with filter_cols[1]:
        show_all = st.checkbox("Show all", value=False, help="By default only shows models with issues")
    with filter_cols[2]:
        search = search_filter or st.text_input("Search", placeholder="Filter by name...", label_visibility="collapsed")

    df = get_models_summary(days=days, search=search, show_all=show_all)

    if df.empty:
        if show_all:
            st.info("No model runs found in this time range")
        else:
            st.success("All models healthy")
        return

    # Summary stats
    failed_count = len(df[df["LATEST_STATUS"].isin(["fail", "error"])])
    slow_count = len(df[df["IS_SLOW"] == True])

    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("Total Models", len(df))
    with stat_cols[1]:
        st.metric("Failed", failed_count)
    with stat_cols[2]:
        st.metric("Slow", slow_count)
    with stat_cols[3]:
        st.metric("Healthy", len(df) - failed_count - slow_count)

    st.divider()

    # Model list
    for _, row in df.iterrows():
        status_icon = ":red_circle:" if row["LATEST_STATUS"] in ("fail", "error") else ":green_circle:"
        slow_badge = " :orange_circle:" if row["IS_SLOW"] else ""
        schema = row["SCHEMA_NAME"] or "unknown"

        with st.expander(f"{status_icon}{slow_badge} {row['NAME']} — {schema}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Last Status", row["LATEST_STATUS"].upper())
            with col2:
                avg_time = row["AVG_EXECUTION_TIME"]
                st.metric("Avg Time", f"{avg_time:.1f}s" if avg_time else "N/A")
            with col3:
                st.metric("Run Count", int(row["RUN_COUNT"]))

            st.caption(f"Last run: {row['LAST_RUN']}")

            # Model details (SQL, description, etc.)
            details_df = get_model_details(row["UNIQUE_ID"])
            if not details_df.empty:
                details = details_df.iloc[0]

                if details.get("DESCRIPTION"):
                    st.markdown(f"**Description:** {details['DESCRIPTION']}")

                if details.get("OWNER"):
                    st.markdown(f"**Owner:** {details['OWNER']}")

                if details.get("TAGS"):
                    st.markdown(f"**Tags:** {details['TAGS']}")

                if details.get("ORIGINAL_PATH"):
                    st.markdown(f"**Path:** `{details['ORIGINAL_PATH']}`")

                if details.get("MATERIALIZATION"):
                    st.markdown(f"**Materialization:** {details['MATERIALIZATION']}")

            # Run history with error messages
            history_df = get_model_run_history(row["UNIQUE_ID"], days)
            if not history_df.empty:
                st.markdown("**Run History:**")
                st.altair_chart(run_status_timeline(history_df), use_container_width=True)

                # Show recent runs with details
                for _, h_row in history_df.head(5).iterrows():
                    status_color = "green" if h_row["STATUS"] == "success" else "red"
                    time_str = f"{h_row['EXECUTION_TIME']:.1f}s" if h_row["EXECUTION_TIME"] else "N/A"
                    st.markdown(
                        f":{status_color}_circle: **{h_row['STATUS']}** — "
                        f"{h_row['GENERATED_AT']} ({time_str})"
                    )

                    # Show error message if present
                    if h_row.get("MESSAGE") and h_row["STATUS"] in ("fail", "error"):
                        st.error(h_row["MESSAGE"])

            # Execution trend
            trend_df = get_model_execution_trend(row["UNIQUE_ID"], days)
            if not trend_df.empty and len(trend_df) > 1:
                st.markdown("**Execution Time Trend:**")
                st.altair_chart(execution_time_chart(trend_df), use_container_width=True)
