"""Tests page - Test results and flaky test detection."""

import streamlit as st
from services.tests_service import get_tests_summary, get_test_run_history, get_models_without_tests, get_flaky_tests
from components.charts import pass_rate_bar_chart
from config import DEFAULT_LOOKBACK_DAYS, FLAKY_TEST_THRESHOLD


def render(search_filter: str = ""):
    st.title("Tests")

    # Tabs
    tab_all, tab_flaky, tab_coverage = st.tabs(["All Tests", "Flaky Tests", "Coverage Gaps"])

    with tab_all:
        _render_all_tests(search_filter)

    with tab_flaky:
        _render_flaky_tests()

    with tab_coverage:
        _render_coverage_gaps()


def _render_all_tests(search_filter: str):
    """Render all tests sorted by pass rate (lowest first)."""
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="tests_days")

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

        flaky_badge = " :warning: FLAKY" if row["IS_FLAKY"] else ""
        status_badge = f" ({row['LATEST_STATUS'].upper()})" if row["LATEST_STATUS"] in ("fail", "error") else ""

        with st.expander(f"{icon} {row['TEST_NAME']}{flaky_badge}{status_badge}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Pass Rate", f"{pass_rate * 100:.0f}%")
            with col2:
                st.metric("Total Runs", int(row["TOTAL_RUNS"]))
            with col3:
                st.metric("Passed", int(row["PASS_COUNT"]))

            st.caption(f"Model: {row['TABLE_NAME'] or 'N/A'} | Schema: {row['SCHEMA_NAME']}")
            st.caption(f"Type: {row['TEST_TYPE']} | Last run: {row['LAST_RUN']}")

            # Run history with error details
            history_df = get_test_run_history(row["TEST_UNIQUE_ID"], days)
            if not history_df.empty:
                st.markdown("**Run History:**")
                for _, h_row in history_df.head(5).iterrows():
                    status_color = "green" if h_row["STATUS"] == "pass" else "red"
                    st.markdown(f":{status_color}_circle: **{h_row['STATUS']}** — {h_row['DETECTED_AT']}")

                    # Show error description if test failed
                    if h_row.get("TEST_RESULTS_DESCRIPTION") and h_row["STATUS"] in ("fail", "error"):
                        st.error(h_row["TEST_RESULTS_DESCRIPTION"])

                # Show test SQL (from most recent run)
                latest = history_df.iloc[0]
                if latest.get("TEST_RESULTS_QUERY"):
                    with st.expander("View Test SQL"):
                        st.code(latest["TEST_RESULTS_QUERY"], language="sql")


def _render_flaky_tests():
    """Render flaky tests (high failure rate)."""
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

    # Table
    st.dataframe(
        df[["TEST_NAME", "TABLE_NAME", "FAILURE_RATE", "TOTAL_RUNS", "FAIL_COUNT"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "TEST_NAME": "Test",
            "TABLE_NAME": "Model",
            "FAILURE_RATE": st.column_config.ProgressColumn("Failure Rate", min_value=0, max_value=1, format="%.0f%%"),
            "TOTAL_RUNS": "Runs",
            "FAIL_COUNT": "Failures",
        },
    )


def _render_coverage_gaps():
    """Render models without tests."""
    st.subheader("Models Without Tests")

    df = get_models_without_tests()

    if df.empty:
        st.success("All models have tests")
        return

    st.warning(f"**{len(df)} models** have no associated tests")

    st.dataframe(
        df[["NAME", "SCHEMA_NAME", "DATABASE_NAME"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "NAME": "Model",
            "SCHEMA_NAME": "Schema",
            "DATABASE_NAME": "Database",
        },
    )
