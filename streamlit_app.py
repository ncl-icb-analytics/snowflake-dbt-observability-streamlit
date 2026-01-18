"""dbt Observability Dashboard - Main entry point."""

import streamlit as st

from config import PAGE_CONFIG

st.set_page_config(**PAGE_CONFIG)

# Page imports
from page_modules import home, alerts, models, tests, growth, credits

# Navigation
PAGES = {
    "Home": home,
    "Alerts": alerts,
    "Models": models,
    "Tests": tests,
    "Growth": growth,
    "Performance": credits,
}


def main():
    # Sidebar navigation
    st.sidebar.title("dbt Observability")

    # Global search
    search_term = st.sidebar.text_input(
        "Search models/tests", placeholder="Enter name or tag..."
    )
    if search_term:
        st.session_state["global_search"] = search_term

    st.sidebar.divider()

    # Page selection
    page_name = st.sidebar.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

    # Render selected page
    page_module = PAGES[page_name]
    page_module.render(search_filter=st.session_state.get("global_search", ""))


if __name__ == "__main__":
    main()
