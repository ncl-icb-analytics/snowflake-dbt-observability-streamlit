"""Tests page - Searchable list of tests with click-through to detail."""

import streamlit as st
from services.tests_service import get_tests_summary, get_tests_count, get_models_without_tests, get_flaky_tests
from components.charts import pass_rate_bar_chart
from config import FLAKY_TEST_THRESHOLD, TESTS_PAGE_SIZE


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def render(search_filter: str = ""):
    st.title("Tests")

    tab_all, tab_flaky, tab_coverage = st.tabs(["All Tests", "Flaky Tests", "Coverage Gaps"])

    with tab_all:
        _render_all_tests()

    with tab_flaky:
        _render_flaky_tests()

    with tab_coverage:
        _render_coverage_gaps()


def _render_all_tests():
    """Render all tests as clickable list with pagination."""
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search tests", placeholder="Filter by name or model...", key="tests_search")
    with col2:
        days = st.selectbox("Range", [7, 14, 30], index=0, format_func=lambda x: f"{x}d", key="tests_days")

    # Get total count for pagination
    total_count_df = get_tests_count(days=days, search=search)
    total_tests = int(total_count_df.iloc[0]["TOTAL"]) if not total_count_df.empty else 0

    # Pagination controls
    page_size = TESTS_PAGE_SIZE
    total_pages = max(1, (total_tests + page_size - 1) // page_size)

    if "tests_page" not in st.session_state:
        st.session_state["tests_page"] = 0

    # Reset page if search changes
    current_page = st.session_state["tests_page"]
    if current_page >= total_pages:
        current_page = 0
        st.session_state["tests_page"] = 0

    offset = current_page * page_size
    df = get_tests_summary(days=days, search=search, limit=page_size, offset=offset)

    if df.empty:
        st.info("No test runs found")
        return

    # Header with count and pagination
    header_cols = st.columns([3, 2])
    with header_cols[0]:
        st.write(f"**{total_tests} tests** (sorted by pass rate, lowest first)")
    with header_cols[1]:
        if total_pages > 1:
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button("← Prev", disabled=current_page == 0, key="tests_prev"):
                    st.session_state["tests_page"] = current_page - 1
                    st.rerun()
            with nav_cols[1]:
                st.caption(f"Page {current_page + 1} of {total_pages}")
            with nav_cols[2]:
                if st.button("Next →", disabled=current_page >= total_pages - 1, key="tests_next"):
                    st.session_state["tests_page"] = current_page + 1
                    st.rerun()

    for _, row in df.iterrows():
        pass_rate = row["PASS_RATE"] or 0
        latest_status = (row.get("LATEST_STATUS") or "").lower()

        # Icon based on latest status, not pass rate
        if latest_status == "pass":
            icon = "🟢"
        elif latest_status == "warn":
            icon = "🟡"
        elif latest_status in ("fail", "error"):
            icon = "🔴"
        else:
            icon = "⚪"

        flaky_badge = " ⚠️" if row["IS_FLAKY"] else ""
        short_name = row.get("SHORT_NAME") or row["TEST_NAME"]
        test_name = _truncate(short_name)
        model = row["TABLE_NAME"] or "N/A"
        test_ns = row.get("TEST_NAMESPACE") or row["TEST_TYPE"] or ""

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                # Show model name as primary, test name as secondary
                st.markdown(f"{icon}{flaky_badge} **{model}**")
                st.caption(f"{test_name} | {test_ns}" if test_ns else test_name)
            with cols[1]:
                st.caption("Pass Rate")
                st.write(f"{pass_rate * 100:.0f}%")
            with cols[2]:
                st.caption("Runs")
                st.write(int(row["TOTAL_RUNS"]))
            with cols[3]:
                if st.button("View", key=f"test_{row['TEST_UNIQUE_ID']}"):
                    st.session_state["selected_test"] = row["TEST_UNIQUE_ID"]
                    st.session_state["selected_model"] = None
                    st.rerun()


def _render_flaky_tests():
    """Render flaky tests with click navigation."""
    st.subheader("Flaky Tests")
    st.caption(f"Tests with >= {FLAKY_TEST_THRESHOLD * 100:.0f}% failure rate over at least 3 runs")

    col1, _ = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="flaky_days")

    df = get_flaky_tests(days)

    if df.empty:
        st.success("No flaky tests detected")
        return

    st.write(f"**{len(df)} flaky tests**")

    # Chart
    if len(df) <= 20:
        chart_df = df.copy()
        chart_df["PASS_RATE"] = 1 - chart_df["FAILURE_RATE"]
        st.altair_chart(pass_rate_bar_chart(chart_df), use_container_width=True)

    # Clickable list
    for _, row in df.iterrows():
        short_name = row.get("SHORT_NAME") or row["TEST_NAME"]
        name = _truncate(short_name)
        failure_rate = row["FAILURE_RATE"] * 100
        test_ns = row.get("TEST_NAMESPACE") or ""
        model = row["TABLE_NAME"] or "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"⚠️ **{name}**")
                st.caption(f"{test_ns} | {model}" if test_ns else model)
            with cols[1]:
                st.caption("Failure Rate")
                st.write(f"{failure_rate:.0f}%")
            with cols[2]:
                st.caption("Failures")
                st.write(int(row["FAIL_COUNT"]))
            with cols[3]:
                if st.button("View", key=f"flaky_{row['TEST_UNIQUE_ID']}"):
                    st.session_state["selected_test"] = row["TEST_UNIQUE_ID"]
                    st.session_state["selected_model"] = None
                    st.rerun()


def _render_coverage_gaps():
    """Render models without tests."""
    st.subheader("Models Without Tests")

    df = get_models_without_tests()

    if df.empty:
        st.success("All models have tests")
        return

    st.warning(f"**{len(df)} models** have no associated tests")

    for _, row in df.iterrows():
        name = _truncate(row["NAME"])
        schema = row["SCHEMA_NAME"] or "unknown"

        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"**{name}**")
                st.caption(f"{schema} | {row['DATABASE_NAME'] or 'N/A'}")
            with cols[1]:
                if st.button("View", key=f"gap_{row['UNIQUE_ID']}"):
                    st.session_state["selected_model"] = row["UNIQUE_ID"]
                    st.session_state["selected_test"] = None
                    st.rerun()
