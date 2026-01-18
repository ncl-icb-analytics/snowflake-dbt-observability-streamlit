"""Tests page - Searchable list of tests with click-through to detail."""

import streamlit as st
from services.tests_service import get_tests_summary, get_models_without_tests, get_flaky_tests
from components.charts import pass_rate_bar_chart
from config import FLAKY_TEST_THRESHOLD


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def render(search_filter: str = ""):
    st.title("Tests")

    tab_all, tab_flaky, tab_coverage = st.tabs(["All Tests", "Flaky Tests", "Coverage Gaps"])

    with tab_all:
        _render_all_tests(search_filter)

    with tab_flaky:
        _render_flaky_tests()

    with tab_coverage:
        _render_coverage_gaps()


def _render_all_tests(search_filter: str):
    """Render all tests as clickable list."""
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="tests_days")
    with col2:
        search = search_filter or st.text_input("Search tests", placeholder="Filter by name...", key="tests_search")

    df = get_tests_summary(days=days, search=search)

    if df.empty:
        st.info("No test runs found")
        return

    st.write(f"**{len(df)} tests** (sorted by pass rate, lowest first)")

    for _, row in df.iterrows():
        pass_rate = row["PASS_RATE"] or 0
        if pass_rate >= 0.95:
            icon = ":green_circle:"
        elif pass_rate >= 0.8:
            icon = ":orange_circle:"
        else:
            icon = ":red_circle:"

        flaky_badge = " :warning:" if row["IS_FLAKY"] else ""
        name = _truncate(row["TEST_NAME"])
        model = row["TABLE_NAME"] or "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"{icon}{flaky_badge} **{name}**")
                st.caption(f"{model} | {row['TEST_TYPE']}")
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
        name = _truncate(row["TEST_NAME"])
        failure_rate = row["FAILURE_RATE"] * 100

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f":warning: **{name}**")
                st.caption(row["TABLE_NAME"] or "N/A")
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
