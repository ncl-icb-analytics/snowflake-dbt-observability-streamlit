"""Reusable chart components using Altair."""

import altair as alt
import pandas as pd


def status_color(status: str) -> str:
    """Get color for status."""
    colors = {
        "pass": "#28a745",
        "success": "#28a745",
        "fail": "#dc3545",
        "error": "#dc3545",
        "warn": "#ffc107",
        "skip": "#6c757d",
    }
    return colors.get(status.lower(), "#6c757d")


def execution_time_chart(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Line chart for execution time trends."""
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.value("No data"))

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("RUN_DATE:T", title="Date"),
            y=alt.Y("AVG_TIME:Q", title="Avg Execution Time (s)"),
            tooltip=["RUN_DATE:T", "AVG_TIME:Q", "RUN_COUNT:Q"],
        )
        .properties(height=height)
    )
    return chart


def pass_rate_bar_chart(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Bar chart showing pass rates."""
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.value("No data"))

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("TEST_NAME:N", title="Test", sort="-y"),
            y=alt.Y("PASS_RATE:Q", title="Pass Rate", scale=alt.Scale(domain=[0, 1])),
            color=alt.condition(
                alt.datum.PASS_RATE < 0.8,
                alt.value("#dc3545"),
                alt.value("#28a745"),
            ),
            tooltip=["TEST_NAME:N", "PASS_RATE:Q", "TOTAL_RUNS:Q"],
        )
        .properties(height=height)
    )
    return chart


def run_status_timeline(df: pd.DataFrame, height: int = 100) -> alt.Chart:
    """Mini timeline showing recent run statuses (sparkline-style)."""
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.value("No data"))

    chart = (
        alt.Chart(df.head(10))
        .mark_circle(size=60)
        .encode(
            x=alt.X("GENERATED_AT:T", title=None, axis=alt.Axis(labels=False)),
            color=alt.Color(
                "STATUS:N",
                scale=alt.Scale(
                    domain=["pass", "success", "fail", "error"],
                    range=["#28a745", "#28a745", "#dc3545", "#dc3545"],
                ),
                legend=None,
            ),
            tooltip=["STATUS:N", "GENERATED_AT:T", "EXECUTION_TIME:Q"],
        )
        .properties(height=height)
    )
    return chart


def row_count_trend_chart(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Line chart for table row count trends (ROW_COUNT_LOG table)."""
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.value("No data"))

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("RUN_STARTED_AT:T", title="Date"),
            y=alt.Y("ROW_COUNT:Q", title="Row Count", scale=alt.Scale(zero=False)),
            tooltip=["RUN_STARTED_AT:T", "ROW_COUNT:Q"],
        )
        .properties(height=height)
    )
    return chart


def row_count_change_chart(df: pd.DataFrame, height: int = 250) -> alt.Chart:
    """Bar chart showing daily row count changes (net change per day)."""
    if df.empty or len(df) < 2:
        return alt.Chart().mark_text().encode(text=alt.value("Not enough data"))

    # Prepare data: get first and last row count per day
    df = df.sort_values("RUN_STARTED_AT").copy()
    df["DATE"] = pd.to_datetime(df["RUN_STARTED_AT"]).dt.date

    # For each day, get the net change (last count - first count of previous day)
    daily = df.groupby("DATE").agg(
        FIRST_COUNT=("ROW_COUNT", "first"),
        LAST_COUNT=("ROW_COUNT", "last"),
    ).reset_index()
    daily["DATE"] = pd.to_datetime(daily["DATE"])

    # Calculate change from previous day's last count
    daily["PREV_COUNT"] = daily["LAST_COUNT"].shift(1)
    daily["CHANGE"] = daily["LAST_COUNT"] - daily["PREV_COUNT"]
    daily["CHANGE_PCT"] = ((daily["CHANGE"] / daily["PREV_COUNT"]) * 100).round(1)
    daily = daily.dropna(subset=["CHANGE"])

    if daily.empty:
        return alt.Chart().mark_text().encode(text=alt.value("Not enough data"))

    # Bar chart with conditional coloring
    bars = alt.Chart(daily).mark_bar().encode(
        x=alt.X("DATE:T", title="Date"),
        y=alt.Y("CHANGE:Q", title="Row Change"),
        color=alt.condition(
            alt.datum.CHANGE >= 0,
            alt.value("#28a745"),
            alt.value("#dc3545"),
        ),
        tooltip=[
            alt.Tooltip("DATE:T", title="Date"),
            alt.Tooltip("CHANGE:Q", title="Change", format=","),
            alt.Tooltip("CHANGE_PCT:Q", title="Change %", format="+.1f"),
            alt.Tooltip("LAST_COUNT:Q", title="Total Rows", format=","),
        ],
    )

    # Zero line
    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[4, 4], color="#666"
    ).encode(y="y:Q")

    return (bars + zero_line).properties(height=height)


def top_models_bar_chart(df: pd.DataFrame, height: int = 400) -> alt.Chart:
    """Horizontal bar chart for slowest models."""
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.value("No data"))

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            y=alt.Y("NAME:N", title="Model", sort="-x"),
            x=alt.X("TOTAL_TIME:Q", title="Total Execution Time (s)"),
            color=alt.value("#4a90d9"),
            tooltip=["NAME:N", "TOTAL_TIME:Q", "AVG_TIME:Q", "RUN_COUNT:Q"],
        )
        .properties(height=height)
    )
    return chart
