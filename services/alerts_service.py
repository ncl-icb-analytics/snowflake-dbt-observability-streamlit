"""Alert queries - test and model failures with smart filtering."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def get_current_test_failures(days: int = DEFAULT_LOOKBACK_DAYS, search: str = ""):
    """
    Get test failures where the most recent run is a failure.
    Hides failures that have been subsequently fixed.
    """
    search_filter = f"AND LOWER(test_unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH ranked AS (
        SELECT
            test_unique_id,
            elementary_unique_id,
            test_name,
            test_type,
            status,
            detected_at,
            database_name,
            schema_name,
            table_name,
            column_name,
            test_results_description,
            test_results_query,
            ROW_NUMBER() OVER (
                PARTITION BY test_unique_id
                ORDER BY detected_at DESC
            ) as rn
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
        WHERE detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    )
    SELECT
        test_unique_id,
        elementary_unique_id,
        test_name,
        test_type,
        status,
        detected_at,
        database_name,
        schema_name,
        table_name,
        column_name,
        test_results_description,
        test_results_query
    FROM ranked
    WHERE rn = 1 AND status IN ('fail', 'error')
    ORDER BY detected_at DESC
    """
    return run_query(query)


def get_current_model_failures(days: int = DEFAULT_LOOKBACK_DAYS, search: str = ""):
    """
    Get model failures where the most recent run failed.
    """
    search_filter = f"AND LOWER(unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH ranked AS (
        SELECT
            unique_id,
            name,
            status,
            execution_time,
            generated_at,
            database_name,
            schema_name,
            compile_started_at,
            compile_completed_at,
            execute_started_at,
            execute_completed_at,
            ROW_NUMBER() OVER (
                PARTITION BY unique_id
                ORDER BY generated_at DESC
            ) as rn
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    )
    SELECT *
    FROM ranked
    WHERE rn = 1 AND status IN ('fail', 'error')
    ORDER BY generated_at DESC
    """
    return run_query(query)


def get_alert_counts(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get summary counts of current failures."""
    query = f"""
    WITH test_ranked AS (
        SELECT
            test_unique_id,
            status,
            ROW_NUMBER() OVER (PARTITION BY test_unique_id ORDER BY detected_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
        WHERE detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ),
    model_ranked AS (
        SELECT
            unique_id,
            status,
            ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY generated_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    )
    SELECT
        (SELECT COUNT(*) FROM test_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_tests,
        (SELECT COUNT(*) FROM model_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_models
    """
    return run_query(query)
