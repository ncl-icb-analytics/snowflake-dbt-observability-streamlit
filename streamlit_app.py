"""dbt Observability Dashboard - Main entry point."""

import streamlit as st

from config import PAGE_CONFIG

st.set_page_config(**PAGE_CONFIG)

from page_modules import home, alerts, models, tests, growth, credits, model_detail, test_detail

PAGES = {
    "Home": home,
    "Alerts": alerts,
    "Models": models,
    "Tests": tests,
    "Growth": growth,
    "Performance": credits,
}


def navigate_to_model(unique_id: str):
    """Navigate to model detail page."""
    st.session_state["selected_model"] = unique_id
    st.session_state["selected_test"] = None


def navigate_to_test(test_unique_id: str):
    """Navigate to test detail page."""
    st.session_state["selected_test"] = test_unique_id
    st.session_state["selected_model"] = None


def navigate_back():
    """Return to list view."""
    st.session_state["selected_model"] = None
    st.session_state["selected_test"] = None


def main():
    # Initialize session state
    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = None
    if "selected_test" not in st.session_state:
        st.session_state["selected_test"] = None

    # Check if viewing detail page
    if st.session_state.get("selected_model"):
        model_detail.render(st.session_state["selected_model"])
        return

    if st.session_state.get("selected_test"):
        test_detail.render(st.session_state["selected_test"])
        return

    # Sidebar navigation
    st.sidebar.title("dbt Observability")

    search_term = st.sidebar.text_input(
        "Search models/tests", placeholder="Enter name or tag..."
    )
    if search_term:
        st.session_state["global_search"] = search_term

    st.sidebar.divider()

    page_name = st.sidebar.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

    page_module = PAGES[page_name]
    page_module.render(search_filter=st.session_state.get("global_search", ""))


if __name__ == "__main__":
    main()
