"""Snowflake connection utilities for Snowflake-native Streamlit."""

import streamlit as st
from snowflake.snowpark.context import get_active_session

from config import CACHE_TTL


@st.cache_resource
def get_session():
    """Get Snowflake session (cached for app lifetime)."""
    return get_active_session()


@st.cache_data(ttl=CACHE_TTL)
def run_query(query: str):
    """Execute query and return results as pandas DataFrame."""
    session = get_session()
    return session.sql(query).to_pandas()


def run_query_uncached(query: str):
    """Execute query without caching (for mutations or time-sensitive data)."""
    session = get_session()
    return session.sql(query).to_pandas()
