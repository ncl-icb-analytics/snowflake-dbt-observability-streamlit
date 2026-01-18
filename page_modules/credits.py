"""Performance/Credits page - Identify expensive models."""

import streamlit as st
from database import run_query
from components.charts import top_models_bar_chart, execution_time_chart
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def render(search_filter: str = ""):
    st.title("Performance")

    # Filters in a compact row
    filter_cols = st.columns([1, 2, 3])
    with filter_cols[0]:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="perf_days")
    with filter_cols[1]:
        search = search_filter or st.text_input("Search", placeholder="Filter by name...", key="perf_search")

    # Summary metrics
    summary = _get_performance_summary(days)
    if not summary.empty:
        row = summary.iloc[0]
        total_time = row["TOTAL_EXECUTION_TIME"] or 0
        total_runs = int(row["TOTAL_RUNS"] or 0)
        avg_time = row["AVG_EXECUTION_TIME"] or 0

        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Total Time", f"{total_time / 60:.1f} min")
        with metric_cols[1]:
            st.metric("Total Runs", total_runs)
        with metric_cols[2]:
            st.metric("Avg Time", f"{avg_time:.1f}s")
        with metric_cols[3]:
            if total_runs > 0:
                st.metric("Time/Run", f"{total_time / total_runs:.1f}s")

    st.divider()

    df = _get_slowest_models(days, search)

    if df.empty:
        st.info("No model runs found")
        return

    # Two-column layout: chart on left, top models on right
    chart_col, list_col = st.columns([3, 2])

    with chart_col:
        st.subheader("Execution Time by Model")
        st.altair_chart(top_models_bar_chart(df.head(15)), use_container_width=True)

    with list_col:
        st.subheader("Top 5 Slowest")
        for _, row in df.head(5).iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['NAME']}**")
                cols = st.columns(2)
                with cols[0]:
                    st.caption(f"Total: {row['TOTAL_TIME']:.1f}s")
                with cols[1]:
                    st.caption(f"Avg: {row['AVG_TIME']:.1f}s")

    st.divider()

    # Expandable details for all models
    st.subheader("All Models")
    for _, row in df.iterrows():
        with st.expander(f"{row['NAME']} — {row['TOTAL_TIME']:.1f}s total"):
            cols = st.columns(4)
            with cols[0]:
                st.metric("Total", f"{row['TOTAL_TIME']:.1f}s")
            with cols[1]:
                st.metric("Avg", f"{row['AVG_TIME']:.1f}s")
            with cols[2]:
                st.metric("Max", f"{row['MAX_TIME']:.1f}s")
            with cols[3]:
                st.metric("Runs", int(row["RUN_COUNT"]))

            st.caption(f"Schema: {row['SCHEMA_NAME'] or 'N/A'}")

            trend_df = _get_model_time_trend(row["UNIQUE_ID"], days)
            if not trend_df.empty and len(trend_df) > 1:
                st.altair_chart(execution_time_chart(trend_df), use_container_width=True)


def _get_performance_summary(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get overall performance summary."""
    query = f"""
    SELECT
        SUM(execution_time) as total_execution_time,
        COUNT(*) as total_runs,
        AVG(execution_time) as avg_execution_time
    FROM {ELEMENTARY_SCHEMA}.dbt_run_results
    WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND status = 'success'
    AND resource_type = 'model'
    """
    return run_query(query)


def _get_slowest_models(days: int = DEFAULT_LOOKBACK_DAYS, search: str = "", limit: int = 50):
    """Get models ranked by total execution time."""
    search_filter = f"AND LOWER(r.unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    SELECT
        r.unique_id,
        r.name,
        m.schema_name,
        SUM(r.execution_time) as total_time,
        AVG(r.execution_time) as avg_time,
        MAX(r.execution_time) as max_time,
        COUNT(*) as run_count
    FROM {ELEMENTARY_SCHEMA}.dbt_run_results r
    LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_models m ON r.unique_id = m.unique_id
    WHERE r.generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND r.status = 'success'
    AND r.resource_type = 'model'
    {search_filter}
    GROUP BY r.unique_id, r.name, m.schema_name
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
    FROM {ELEMENTARY_SCHEMA}.dbt_run_results
    WHERE unique_id = '{unique_id}'
    AND generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND status = 'success'
    GROUP BY DATE_TRUNC('day', generated_at)
    ORDER BY run_date
    """
    return run_query(query)
