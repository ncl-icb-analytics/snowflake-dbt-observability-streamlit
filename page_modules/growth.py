"""Growth page - Model row count trends showing highest changes."""

import streamlit as st
from database import run_query
from components.charts import row_count_trend_chart
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


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
    return f"{count:,}"


def render(search_filter: str = ""):
    st.title("Model Growth")
    st.caption("Track row counts for table models (sorted by change %)")

    # Filters row
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search models", placeholder="Filter by name...", key="growth_search")
    with col2:
        days = st.selectbox("Range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="growth_days")

    df = _get_growth_summary(search, days)

    if df.empty:
        st.info("No row count data available. Row counts are logged for table models only.")
        return

    st.write(f"**{len(df)} models** with row count data")

    for _, row in df.iterrows():
        change_pct = row.get("CHANGE_PCT")
        latest_count = row.get("LATEST_ROW_COUNT")
        model_name = row["MODEL_NAME"]

        # Determine icon and badge based on change
        if change_pct is None:
            icon = "📊"
            badge = ""
        elif change_pct > 50:
            icon = "📈"
            badge = " :red[HIGH GROWTH]"
        elif change_pct < -20:
            icon = "📉"
            badge = " :orange[SHRINKING]"
        elif change_pct > 10:
            icon = "📈"
            badge = ""
        elif change_pct < -10:
            icon = "📉"
            badge = ""
        else:
            icon = "📊"
            badge = ""

        with st.expander(f"{icon} {model_name}{badge}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Current Rows", _format_row_count(latest_count))
            with col2:
                if change_pct is not None:
                    st.metric("Change", f"{change_pct:+.1f}%")
                else:
                    st.metric("Change", "N/A")
            with col3:
                st.metric("Schema", row.get("SCHEMA_NAME") or "N/A")

            # Trend chart
            trend_df = _get_model_trend(model_name, days)
            if not trend_df.empty and len(trend_df) > 1:
                st.altair_chart(row_count_trend_chart(trend_df), use_container_width=True)

            # Link to model detail
            if st.button("View Model", key=f"growth_{model_name}"):
                # Get model unique_id
                model_df = _get_model_unique_id(model_name)
                if not model_df.empty:
                    st.session_state["selected_model"] = model_df.iloc[0]["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()


def _get_growth_summary(search: str = "", days: int = DEFAULT_LOOKBACK_DAYS):
    """Get model growth summary with change percentages from ROW_COUNT_LOG."""
    search_filter = f"AND LOWER(model_name) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH latest AS (
        SELECT
            model_name,
            database_name,
            schema_name,
            row_count,
            run_started_at,
            ROW_NUMBER() OVER (PARTITION BY model_name ORDER BY run_started_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.ROW_COUNT_LOG
        WHERE run_started_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    ),
    earliest AS (
        SELECT
            model_name,
            row_count as earliest_row_count
        FROM {ELEMENTARY_SCHEMA}.ROW_COUNT_LOG
        WHERE run_started_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY model_name ORDER BY run_started_at ASC) = 1
    )
    SELECT
        l.model_name,
        l.database_name,
        l.schema_name,
        l.row_count as latest_row_count,
        e.earliest_row_count,
        CASE
            WHEN e.earliest_row_count > 0
            THEN ((l.row_count - e.earliest_row_count) / e.earliest_row_count) * 100
            ELSE NULL
        END as change_pct
    FROM latest l
    LEFT JOIN earliest e ON l.model_name = e.model_name
    WHERE l.rn = 1
    ORDER BY ABS(COALESCE(change_pct, 0)) DESC
    LIMIT 100
    """
    try:
        return run_query(query)
    except Exception:
        return run_query("SELECT 1 WHERE FALSE")


def _get_model_trend(model_name: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get row count trend for a specific model."""
    query = f"""
    SELECT
        run_started_at,
        row_count
    FROM {ELEMENTARY_SCHEMA}.ROW_COUNT_LOG
    WHERE LOWER(model_name) = LOWER('{model_name}')
    AND run_started_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY run_started_at
    """
    try:
        return run_query(query)
    except Exception:
        return run_query("SELECT 1 WHERE FALSE")


def _get_model_unique_id(model_name: str):
    """Get model unique_id by name."""
    query = f"""
    SELECT unique_id
    FROM {ELEMENTARY_SCHEMA}.dbt_models
    WHERE LOWER(name) = LOWER('{model_name}')
    LIMIT 1
    """
    try:
        return run_query(query)
    except Exception:
        return run_query("SELECT 1 WHERE FALSE")
