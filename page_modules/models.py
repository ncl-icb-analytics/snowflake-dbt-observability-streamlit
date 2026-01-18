"""Models page - Searchable list of models with click-through to detail."""

import streamlit as st
from services.models_service import get_models_summary, get_models_count, get_model_paths
from config import DEFAULT_LOOKBACK_DAYS


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def _build_folder_tree(paths):
    """Build folder tree from paths."""
    tree = {}
    for path in paths:
        if not path:
            continue
        parts = path.replace("\\", "/").split("/")
        current = tree
        for part in parts[:-1]:  # Exclude filename
            if part not in current:
                current[part] = {}
            current = current[part]
    return tree


def _get_folder_options(tree, prefix=""):
    """Get flat list of folder paths from tree."""
    options = []
    for name, subtree in sorted(tree.items()):
        path = f"{prefix}/{name}" if prefix else name
        options.append(path)
        options.extend(_get_folder_options(subtree, path))
    return options


def render(search_filter: str = ""):
    st.title("Models")

    # Get total model count
    total_count_df = get_models_count()
    total_models = int(total_count_df.iloc[0]["TOTAL"]) if not total_count_df.empty else 0

    # View mode tabs - Browse by Path is default
    tab_browse, tab_slow = st.tabs(["Browse by Path", "🐢 Slow Models"])

    with tab_browse:
        _render_path_browser(total_models)

    with tab_slow:
        _render_slow_models(search_filter, total_models)


def _render_slow_models(search_filter: str, total_models: int):
    """Render slow models view - models in top 10% by execution time."""
    # Filters row
    col1, col2 = st.columns([1, 4])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="models_days")
    with col2:
        search = search_filter or st.text_input("Filter by name", placeholder="Search models...", key="models_search")

    # Get all models, then filter to slow ones
    df = get_models_summary(days=days, search=search, show_all=True, limit=2000)

    if df.empty:
        st.info("No models found")
        return

    # Filter to slow models only
    slow_df = df[df["IS_SLOW"] == True].copy()

    if slow_df.empty:
        st.success("No slow models (top 10% by execution time)")
        return

    st.caption("Slow = top 10% by avg execution time, minimum 60s")
    st.write(f"**{len(slow_df)} slow models** out of {total_models} total")

    st.divider()

    # Sort by execution time descending
    slow_df = slow_df.sort_values("AVG_EXECUTION_TIME", ascending=False)

    # Model list - clickable rows
    for _, row in slow_df.iterrows():
        status = row["LATEST_STATUS"]
        if status in ("fail", "error"):
            status_icon = "🔴"
        elif status == "no_runs":
            status_icon = "⚪"
        else:
            status_icon = "🟢"
        schema = row["SCHEMA_NAME"] or "unknown"
        name = _truncate(row["NAME"])
        avg_time = row["AVG_EXECUTION_TIME"]
        time_str = f"{avg_time:.1f}s" if avg_time else "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon} 🐢 **{name}**")
                st.caption(schema)
            with cols[1]:
                st.caption("Status")
                st.write(status.upper().replace("_", " "))
            with cols[2]:
                st.caption("Avg Time")
                st.write(time_str)
            with cols[3]:
                if st.button("View", key=f"slow_model_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()


def _render_path_browser(total_models: int):
    """Render path-based folder browser."""
    # Get all paths
    paths_df = get_model_paths()
    if paths_df.empty:
        st.info("No model paths found")
        return

    paths = paths_df["MODEL_PATH"].tolist()
    tree = _build_folder_tree(paths)
    folder_options = ["All"] + _get_folder_options(tree)

    # Search and filters row
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search_text = st.text_input("Search models", placeholder="Filter by name or path...", key="models_browse_search")
    with col2:
        selected_folder = st.selectbox(
            "Folder",
            folder_options,
            key="model_folder_select"
        )
    with col3:
        days = st.selectbox("Range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="models_browse_days")

    # Combine search: text search takes priority, folder filters additionally
    if search_text:
        search = search_text
    elif selected_folder != "All":
        search = selected_folder
    else:
        search = ""

    df = get_models_summary(days=days, search=search, show_all=True, limit=500)

    if df.empty:
        if search:
            st.info(f"No models found matching '{search}'")
        else:
            st.info("No models found")
        return

    st.write(f"**{len(df)} models**")

    # Model list
    for _, row in df.iterrows():
        status = row["LATEST_STATUS"]
        if status in ("fail", "error"):
            status_icon = "🔴"
        elif status == "no_runs":
            status_icon = "⚪"
        else:
            status_icon = "🟢"
        slow_badge = " 🐢" if row["IS_SLOW"] else ""
        name = row["NAME"]
        avg_time = row["AVG_EXECUTION_TIME"]
        time_str = f"{avg_time:.1f}s" if avg_time else ""

        with st.container(border=True):
            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.markdown(f"{status_icon}{slow_badge} **{name}**")
            with cols[1]:
                if time_str:
                    st.caption(time_str)
            with cols[2]:
                if st.button("View", key=f"browse_model_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()
