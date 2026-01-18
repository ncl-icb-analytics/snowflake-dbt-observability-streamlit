"""Models page - Searchable list of models with click-through to detail."""

import streamlit as st
from services.models_service import get_models_summary, get_models_count
from config import DEFAULT_LOOKBACK_DAYS


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def render(search_filter: str = ""):
    st.title("Models")

    # Get total model count
    total_count_df = get_models_count()
    total_models = int(total_count_df.iloc[0]["TOTAL"]) if not total_count_df.empty else 0

    # Filters row
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="models_days")
    with col2:
        show_all = st.checkbox("Show all", value=False, help=f"Show all {total_models} models")
    with col3:
        search = search_filter or st.text_input("Filter by name", placeholder="Search models...", key="models_search")

    df = get_models_summary(days=days, search=search, show_all=show_all)

    if df.empty:
        if show_all:
            st.info("No models found")
        else:
            st.success(f"All models healthy ({total_models} total)")
        return

    # Summary stats
    failed_count = len(df[df["LATEST_STATUS"].isin(["fail", "error"])])
    slow_count = len(df[df["IS_SLOW"] == True])
    no_runs_count = len(df[df["LATEST_STATUS"] == "no_runs"]) if show_all else 0

    stat_cols = st.columns(5 if show_all else 4)
    with stat_cols[0]:
        st.metric("Showing", len(df))
    with stat_cols[1]:
        st.metric("Failed", failed_count)
    with stat_cols[2]:
        st.metric("Slow", slow_count)
    if show_all:
        with stat_cols[3]:
            st.metric("No Recent Runs", no_runs_count)
        with stat_cols[4]:
            st.metric("Total in Project", total_models)
    else:
        with stat_cols[3]:
            st.metric("Total in Project", total_models)

    st.divider()

    # Model list - clickable rows
    for _, row in df.iterrows():
        status = row["LATEST_STATUS"]
        if status in ("fail", "error"):
            status_icon = ":red_circle:"
        elif status == "no_runs":
            status_icon = ":white_circle:"
        else:
            status_icon = ":green_circle:"
        slow_badge = " :orange_circle:" if row["IS_SLOW"] else ""
        schema = row["SCHEMA_NAME"] or "unknown"
        name = _truncate(row["NAME"])
        avg_time = row["AVG_EXECUTION_TIME"]
        time_str = f"{avg_time:.1f}s" if avg_time else "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon}{slow_badge} **{name}**")
                st.caption(schema)
            with cols[1]:
                st.caption("Status")
                st.write(status.upper().replace("_", " "))
            with cols[2]:
                st.caption("Avg Time")
                st.write(time_str)
            with cols[3]:
                if st.button("View", key=f"model_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()
