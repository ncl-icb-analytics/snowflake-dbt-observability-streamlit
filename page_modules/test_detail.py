"""Test detail page - Full view of a single test."""

import streamlit as st
from services.tests_service import get_test_details, get_test_run_history
from services.models_service import get_model_by_name
from config import DEFAULT_LOOKBACK_DAYS


def render(test_unique_id: str):
    """Render full test detail page."""
    # Back button
    if st.button("← Back to Tests"):
        st.session_state["selected_test"] = None
        st.rerun()

    # Get test details
    details_df = get_test_details(test_unique_id)
    if details_df.empty:
        st.error(f"Test not found: {test_unique_id}")
        return

    details = details_df.iloc[0]

    # Header - use short_name if available
    short_name = details.get("SHORT_NAME") or details["TEST_NAME"]
    st.title(short_name)
    test_ns = details.get("TEST_NAMESPACE") or details.get("TEST_TYPE") or ""
    if test_ns:
        st.caption(f"{test_ns}")
    st.caption(f"`{test_unique_id}`")

    # Description if available
    if details.get("DESCRIPTION"):
        st.info(details["DESCRIPTION"])

    st.divider()

    # Metadata section
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.markdown("**Test Type**")
        st.write(test_ns or "N/A")
    with meta_cols[1]:
        st.markdown("**Model**")
        model_name = details.get("TABLE_NAME") or "N/A"
        st.write(model_name)
    with meta_cols[2]:
        st.markdown("**Schema**")
        st.write(details.get("SCHEMA_NAME") or "N/A")
    with meta_cols[3]:
        st.markdown("**Column**")
        col_name = details.get("TEST_COLUMN_NAME") or details.get("COLUMN_NAME") or "N/A"
        st.write(col_name)

    # Additional metadata row
    if details.get("SEVERITY") or details.get("TAGS") or details.get("ORIGINAL_PATH"):
        meta_cols2 = st.columns(3)
        with meta_cols2[0]:
            if details.get("SEVERITY"):
                st.markdown("**Severity**")
                st.write(details["SEVERITY"])
        with meta_cols2[1]:
            if details.get("TAGS"):
                st.markdown("**Tags**")
                st.write(details["TAGS"])
        with meta_cols2[2]:
            if details.get("ORIGINAL_PATH"):
                st.markdown("**Path**")
                st.caption(details["ORIGINAL_PATH"])

    if details.get("TEST_PARAMS"):
        with st.expander("Test Parameters"):
            st.json(details["TEST_PARAMS"])

    st.divider()

    # Run history
    days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days", key="test_detail_days")

    history_df = get_test_run_history(test_unique_id, days)

    if history_df.empty:
        st.info("No runs in this time range")
        return

    # Stats row
    total_runs = len(history_df)
    pass_runs = len(history_df[history_df["STATUS"] == "pass"])
    pass_rate = (pass_runs / total_runs * 100) if total_runs > 0 else 0
    latest = history_df.iloc[0]

    stat_cols = st.columns(4)
    with stat_cols[0]:
        status = latest["STATUS"].upper()
        st.metric("Last Status", status)
    with stat_cols[1]:
        st.metric("Pass Rate", f"{pass_rate:.0f}%")
    with stat_cols[2]:
        st.metric("Total Runs", total_runs)
    with stat_cols[3]:
        st.metric("Passed", pass_runs)

    st.caption(f"Last run: {latest['DETECTED_AT']}")

    # Run history timeline
    st.subheader("Run History")

    for _, row in history_df.iterrows():
        status_icon = "🟢" if row["STATUS"] == "pass" else "🔴"

        with st.container(border=True):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(f"{status_icon} **{row['STATUS'].upper()}**")
            with cols[1]:
                st.caption(str(row["DETECTED_AT"])[:16])

            if row.get("TEST_RESULTS_DESCRIPTION") and row["STATUS"] in ("fail", "error"):
                st.error(row["TEST_RESULTS_DESCRIPTION"])

    # Show test SQL from most recent run
    if latest.get("TEST_RESULTS_QUERY"):
        st.subheader("Test SQL")
        st.code(latest["TEST_RESULTS_QUERY"], language="sql")

    # Link to model
    if details.get("TABLE_NAME"):
        st.divider()
        st.subheader("Related Model")
        model_name = details["TABLE_NAME"]
        model_df = get_model_by_name(model_name)
        if not model_df.empty:
            model = model_df.iloc[0]
            with st.container(border=True):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{model['NAME']}**")
                    st.caption(model.get("SCHEMA_NAME") or "")
                with cols[1]:
                    if st.button("View Model", key="view_related_model"):
                        st.session_state["selected_model"] = model["UNIQUE_ID"]
                        st.session_state["selected_test"] = None
                        st.rerun()
        else:
            st.info(f"Model: **{model_name}**")
