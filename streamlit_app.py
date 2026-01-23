"""dbt Observability Dashboard - Main entry point."""

import streamlit as st

from config import PAGE_CONFIG

st.set_page_config(**PAGE_CONFIG)

from page_modules import home, alerts, models, tests, runs, growth, credits, model_detail, test_detail

PAGES = {
    "Home": home,
    "Alerts": alerts,
    "Models": models,
    "Tests": tests,
    "Runs": runs,
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
    if "selected_invocation" not in st.session_state:
        st.session_state["selected_invocation"] = None
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"

    # Check if we should navigate to a specific page (from back buttons)
    if st.session_state.get("nav_page"):
        st.session_state["current_page"] = st.session_state["nav_page"]
        st.session_state["nav_page"] = None

    # Check if viewing detail page
    if st.session_state.get("selected_model"):
        model_detail.render(st.session_state["selected_model"])
        return

    if st.session_state.get("selected_test"):
        test_detail.render(st.session_state["selected_test"])
        return

    if st.session_state.get("selected_invocation"):
        runs.render()
        return

    # Sidebar navigation
    st.sidebar.title("dbt Observability")

    page_list = list(PAGES.keys())
    current_index = page_list.index(st.session_state["current_page"]) if st.session_state["current_page"] in page_list else 0

    page_name = st.sidebar.radio("Navigation", page_list, index=current_index, label_visibility="collapsed")

    # Update current page when user clicks sidebar
    if page_name != st.session_state["current_page"]:
        st.session_state["current_page"] = page_name

    page_module = PAGES[page_name]
    page_module.render()


if __name__ == "__main__":
    main()
