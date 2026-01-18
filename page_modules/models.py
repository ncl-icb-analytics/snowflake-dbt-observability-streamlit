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

    # Filters row
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="models_days")

    with col2:
        show_all = st.checkbox("Show all models", value=False, help="By default only shows models with issues")

    # Search from global or local
    search = search_filter or st.text_input("Search models", placeholder="Filter by name...")

    # Get models data
    df = get_models_summary(days=days, search=search, show_all=show_all)

    if df.empty:
        if show_all:
            st.info("No model runs found in this time range")
        else:
            st.success("No model issues found")
        return

    st.write(f"**{len(df)} models**")

    # Table with expandable rows
    for _, row in df.iterrows():
        status_icon = ":red_circle:" if row["LATEST_STATUS"] in ("fail", "error") else ":green_circle:"
        slow_badge = " :orange_circle: SLOW" if row["IS_SLOW"] else ""

        with st.expander(f"{status_icon} {row['NAME']}{slow_badge} — {row['SCHEMA_NAME']}"):
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

                # Compiled SQL
                if details.get("COMPILED_CODE"):
                    with st.expander("View Compiled SQL"):
                        st.code(details["COMPILED_CODE"], language="sql")

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
