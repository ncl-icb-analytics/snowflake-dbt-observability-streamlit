"""Growth page - Table row count trends and anomaly detection."""

import streamlit as st
from database import run_query
from components.charts import growth_trend_chart
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def render(search_filter: str = ""):
    st.title("Table Growth")
    st.caption("Track row counts and identify anomalies")

    # Check if data_monitoring_metrics table exists and has data
    metrics_df = _get_growth_summary(search_filter)

    if metrics_df.empty:
        st.info(
            "No growth data available. This feature requires Elementary's "
            "`data_monitoring_metrics` table to be populated.\n\n"
            "Configure volume monitoring in your Elementary setup to enable this feature."
        )
        return

    # Filters
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="growth_days")

    search = search_filter or st.text_input("Search tables", placeholder="Filter by name...", key="growth_search")

    # Refresh data with filters
    df = _get_growth_summary(search, days)

    if df.empty:
        st.info("No tables match your filter")
        return

    st.write(f"**{len(df)} tables** (sorted by growth rate)")

    for _, row in df.iterrows():
        change_pct = row.get("CHANGE_PCT", 0) or 0

        if change_pct > 50:
            icon = ":chart_with_upwards_trend:"
            badge = " :red[HIGH GROWTH]"
        elif change_pct < -20:
            icon = ":chart_with_downwards_trend:"
            badge = " :orange[SHRINKING]"
        else:
            icon = ":bar_chart:"
            badge = ""

        with st.expander(f"{icon} {row['TABLE_NAME']}{badge}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Current Rows", f"{row['LATEST_ROW_COUNT']:,}" if row["LATEST_ROW_COUNT"] else "N/A")
            with col2:
                st.metric("7d Change", f"{change_pct:+.1f}%" if change_pct else "N/A")
            with col3:
                st.metric("Schema", row["SCHEMA_NAME"])

            # Trend chart
            trend_df = _get_table_trend(row["FULL_TABLE_NAME"], days)
            if not trend_df.empty and len(trend_df) > 1:
                st.altair_chart(growth_trend_chart(trend_df), use_container_width=True)


def _get_growth_summary(search: str = "", days: int = DEFAULT_LOOKBACK_DAYS):
    """Get table growth summary with change percentages."""
    search_filter = f"AND LOWER(full_table_name) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH latest_metrics AS (
        SELECT
            full_table_name,
            table_name,
            schema_name,
            metric_value as row_count,
            bucket_end as metric_date,
            ROW_NUMBER() OVER (PARTITION BY full_table_name ORDER BY bucket_end DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.data_monitoring_metrics
        WHERE metric_name = 'row_count'
        AND bucket_end >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    ),
    week_ago AS (
        SELECT
            full_table_name,
            metric_value as row_count_7d_ago
        FROM {ELEMENTARY_SCHEMA}.data_monitoring_metrics
        WHERE metric_name = 'row_count'
        AND bucket_end >= DATEADD(day, -{days + 7}, CURRENT_TIMESTAMP())
        AND bucket_end < DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        QUALIFY ROW_NUMBER() OVER (PARTITION BY full_table_name ORDER BY bucket_end DESC) = 1
    )
    SELECT
        l.full_table_name,
        l.table_name,
        l.schema_name,
        l.row_count as latest_row_count,
        w.row_count_7d_ago,
        CASE
            WHEN w.row_count_7d_ago > 0
            THEN ((l.row_count - w.row_count_7d_ago) / w.row_count_7d_ago) * 100
            ELSE NULL
        END as change_pct
    FROM latest_metrics l
    LEFT JOIN week_ago w ON l.full_table_name = w.full_table_name
    WHERE l.rn = 1
    ORDER BY ABS(COALESCE(change_pct, 0)) DESC
    """
    try:
        return run_query(query)
    except Exception:
        # Table might not exist
        return run_query("SELECT 1 WHERE FALSE")


def _get_table_trend(full_table_name: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get row count trend for a specific table."""
    query = f"""
    SELECT
        DATE_TRUNC('day', bucket_end) as metric_date,
        MAX(metric_value) as row_count
    FROM {ELEMENTARY_SCHEMA}.data_monitoring_metrics
    WHERE full_table_name = '{full_table_name}'
    AND metric_name = 'row_count'
    AND bucket_end >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', bucket_end)
    ORDER BY metric_date
    """
    try:
        return run_query(query)
    except Exception:
        return run_query("SELECT 1 WHERE FALSE")
