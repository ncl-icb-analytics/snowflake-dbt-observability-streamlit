"""Home page - Overview dashboard with KPIs."""

import streamlit as st
from services.metrics_service import get_dashboard_kpis, get_recent_runs, get_top_failures


def render(search_filter: str = ""):
    st.title("dbt Project Health")

    # KPIs
    kpis = get_dashboard_kpis()
    if not kpis.empty:
        row = kpis.iloc[0]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            failed_tests = int(row["FAILED_TESTS"] or 0)
            st.metric(
                "Failed Tests",
                failed_tests,
                delta=None,
                delta_color="inverse" if failed_tests > 0 else "normal",
            )
            if failed_tests > 0:
                st.caption(":red[Needs attention]")

        with col2:
            failed_models = int(row["FAILED_MODELS"] or 0)
            st.metric(
                "Failed Models",
                failed_models,
                delta=None,
                delta_color="inverse" if failed_models > 0 else "normal",
            )
            if failed_models > 0:
                st.caption(":red[Needs attention]")

        with col3:
            avg_time = row["AVG_EXECUTION_TIME"]
            st.metric(
                "Avg Model Runtime",
                f"{avg_time:.1f}s" if avg_time else "N/A",
            )

        with col4:
            last_run = row["LAST_RUN_TIME"]
            st.metric(
                "Last Run",
                last_run.strftime("%Y-%m-%d %H:%M") if last_run else "N/A",
            )

    st.divider()

    # Two columns: Needs Attention + Recent Runs
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Needs Attention")
        failures = get_top_failures()
        if failures.empty:
            st.success("No current failures")
        else:
            for _, row in failures.iterrows():
                icon = ":test_tube:" if row["TYPE"] == "test" else ":package:"
                st.markdown(
                    f"{icon} **{row['NAME']}** ({row['SCHEMA_NAME']})  \n"
                    f":gray[{row['FAILED_AT'].strftime('%Y-%m-%d %H:%M')}]"
                )

    with col_right:
        st.subheader("Recent Runs")
        runs = get_recent_runs()
        if runs.empty:
            st.info("No recent runs")
        else:
            for _, row in runs.iterrows():
                st.markdown(
                    f":clock1: **{row['GENERATED_AT'].strftime('%Y-%m-%d %H:%M')}**  \n"
                    f":gray[{row['COMMAND']} | {row['TARGET_NAME']}]"
                )
