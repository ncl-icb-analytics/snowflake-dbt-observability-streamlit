"""Test result queries."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS, DEFAULT_PAGE_SIZE, FLAKY_TEST_THRESHOLD


def get_tests_summary(
    days: int = DEFAULT_LOOKBACK_DAYS,
    search: str = "",
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
):
    """
    Get test summary with pass rate and flaky detection.
    Sorted by failure rate (flakiest first).
    """
    search_filter = f"AND LOWER(test_unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH test_stats AS (
        SELECT
            test_unique_id,
            test_name,
            test_type,
            table_name,
            schema_name,
            status,
            detected_at,
            ROW_NUMBER() OVER (PARTITION BY test_unique_id ORDER BY detected_at DESC) as rn,
            COUNT(*) OVER (PARTITION BY test_unique_id) as total_runs,
            SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) OVER (PARTITION BY test_unique_id) as pass_count
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
        WHERE detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    )
    SELECT
        test_unique_id,
        test_name,
        test_type,
        table_name,
        schema_name,
        status as latest_status,
        detected_at as last_run,
        total_runs,
        pass_count,
        ROUND(pass_count::FLOAT / NULLIF(total_runs, 0), 3) as pass_rate,
        CASE
            WHEN (1 - pass_count::FLOAT / NULLIF(total_runs, 0)) >= {FLAKY_TEST_THRESHOLD}
            AND total_runs >= 3
            THEN TRUE ELSE FALSE
        END as is_flaky
    FROM test_stats
    WHERE rn = 1
    ORDER BY pass_rate ASC NULLS LAST, total_runs DESC
    LIMIT {limit} OFFSET {offset}
    """
    return run_query(query)


def get_test_run_history(test_unique_id: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get run history for a specific test."""
    query = f"""
    SELECT
        test_unique_id,
        test_name,
        status,
        detected_at,
        test_results_description,
        test_results_query
    FROM {ELEMENTARY_SCHEMA}.elementary_test_results
    WHERE test_unique_id = '{test_unique_id}'
    AND detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY detected_at DESC
    """
    return run_query(query)


def get_models_without_tests():
    """Get models that have no associated tests."""
    query = f"""
    WITH tested_models AS (
        SELECT DISTINCT table_name
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
    )
    SELECT
        m.unique_id,
        m.name,
        m.schema_name,
        m.database_name
    FROM {ELEMENTARY_SCHEMA}.dbt_models m
    LEFT JOIN tested_models t ON LOWER(m.name) = LOWER(t.table_name)
    WHERE t.table_name IS NULL
    ORDER BY m.schema_name, m.name
    """
    return run_query(query)


def get_flaky_tests(days: int = DEFAULT_LOOKBACK_DAYS, limit: int = 20):
    """Get tests with high failure rates (flaky tests)."""
    query = f"""
    WITH test_stats AS (
        SELECT
            test_unique_id,
            test_name,
            table_name,
            schema_name,
            COUNT(*) as total_runs,
            SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN status IN ('fail', 'error') THEN 1 ELSE 0 END) as fail_count
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
        WHERE detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY test_unique_id, test_name, table_name, schema_name
        HAVING total_runs >= 3
    )
    SELECT
        test_unique_id,
        test_name,
        table_name,
        schema_name,
        total_runs,
        pass_count,
        fail_count,
        ROUND(fail_count::FLOAT / total_runs, 3) as failure_rate
    FROM test_stats
    WHERE fail_count::FLOAT / total_runs >= {FLAKY_TEST_THRESHOLD}
    ORDER BY failure_rate DESC, total_runs DESC
    LIMIT {limit}
    """
    return run_query(query)
