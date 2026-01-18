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

    # View mode tabs
    tab_list, tab_browse = st.tabs(["List View", "Browse by Path"])

    with tab_list:
        _render_list_view(search_filter, total_models)

    with tab_browse:
        _render_path_browser(total_models)


def _render_list_view(search_filter: str, total_models: int):
    """Render the standard list view."""
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
            status_icon = "🔴"
        elif status == "no_runs":
            status_icon = "⚪"
        else:
            status_icon = "🟢"
        slow_badge = " 🟠" if row["IS_SLOW"] else ""
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

    # Folder selector
    col1, col2 = st.columns([2, 2])
    with col1:
        selected_folder = st.selectbox(
            "Select folder",
            folder_options,
            key="model_folder_select"
        )
    with col2:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="models_browse_days")

    # Build search pattern from folder
    if selected_folder == "All":
        search = ""
    else:
        search = selected_folder.replace("/", "\\")  # Match Windows paths

    df = get_models_summary(days=days, search=search, show_all=True, limit=200)

    if df.empty:
        st.info("No models in this folder")
        return

    st.write(f"**{len(df)} models** in `{selected_folder}`")

    # Model list
    for _, row in df.iterrows():
        status = row["LATEST_STATUS"]
        if status in ("fail", "error"):
            status_icon = "🔴"
        elif status == "no_runs":
            status_icon = "⚪"
        else:
            status_icon = "🟢"
        slow_badge = " 🟠" if row["IS_SLOW"] else ""
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
