"""Performance/Credits page - Identify expensive models."""

import streamlit as st
from database import run_query
from components.charts import top_models_bar_chart, execution_time_chart
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def render(search_filter: str = ""):
    st.title("Performance")
    st.caption("Identify expensive models for optimization")

    # Filters
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="perf_days")

    search = search_filter or st.text_input("Search models", placeholder="Filter by name...", key="perf_search")

    # Summary metrics
    summary = _get_performance_summary(days)
    if not summary.empty:
        row = summary.iloc[0]
        col1, col2, col3 = st.columns(3)
        with col1:
            total_time = row["TOTAL_EXECUTION_TIME"] or 0
            st.metric("Total Execution Time", f"{total_time / 60:.1f} min")
        with col2:
            st.metric("Total Runs", int(row["TOTAL_RUNS"] or 0))
        with col3:
            avg_time = row["AVG_EXECUTION_TIME"] or 0
            st.metric("Avg Model Time", f"{avg_time:.1f}s")

    st.divider()

    # Top slowest models
    st.subheader("Slowest Models (by total execution time)")

    df = _get_slowest_models(days, search)

    if df.empty:
        st.info("No model runs found")
        return

    # Bar chart
    st.altair_chart(top_models_bar_chart(df.head(20)), use_container_width=True)

    # Detailed table
    st.subheader("Details")

    for _, row in df.iterrows():
        with st.expander(f"{row['NAME']} — {row['TOTAL_TIME']:.1f}s total"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Time", f"{row['TOTAL_TIME']:.1f}s")
            with col2:
                st.metric("Avg Time", f"{row['AVG_TIME']:.1f}s")
            with col3:
                st.metric("Run Count", int(row["RUN_COUNT"]))

            st.caption(f"Schema: {row['SCHEMA_NAME']}")

            # Execution time trend
            trend_df = _get_model_time_trend(row["UNIQUE_ID"], days)
            if not trend_df.empty and len(trend_df) > 1:
                st.markdown("**Execution Time Trend:**")
                st.altair_chart(execution_time_chart(trend_df), use_container_width=True)


def _get_performance_summary(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get overall performance summary."""
    query = f"""
    SELECT
        SUM(execution_time) as total_execution_time,
        COUNT(*) as total_runs,
        AVG(execution_time) as avg_execution_time
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND status = 'success'
    """
    return run_query(query)


def _get_slowest_models(days: int = DEFAULT_LOOKBACK_DAYS, search: str = "", limit: int = 50):
    """Get models ranked by total execution time."""
    search_filter = f"AND LOWER(unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    SELECT
        unique_id,
        name,
        schema_name,
        SUM(execution_time) as total_time,
        AVG(execution_time) as avg_time,
        MAX(execution_time) as max_time,
        COUNT(*) as run_count
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND status = 'success'
    {search_filter}
    GROUP BY unique_id, name, schema_name
    ORDER BY total_time DESC
    LIMIT {limit}
    """
    return run_query(query)


def _get_model_time_trend(unique_id: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get execution time trend for a specific model."""
    query = f"""
    SELECT
        DATE_TRUNC('day', generated_at) as run_date,
        AVG(execution_time) as avg_time,
        COUNT(*) as run_count
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE unique_id = '{unique_id}'
    AND generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND status = 'success'
    GROUP BY DATE_TRUNC('day', generated_at)
    ORDER BY run_date
    """
    return run_query(query)
