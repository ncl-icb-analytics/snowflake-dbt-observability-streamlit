"""Alert queries - test and model failures with smart filtering."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def get_current_test_failures(days: int = DEFAULT_LOOKBACK_DAYS, search: str = ""):
    """
    Get test failures where the most recent run is a failure.
    Joins with dbt_tests for cleaner display names.
    """
    search_filter = f"AND LOWER(r.test_unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH ranked AS (
        SELECT
            r.test_unique_id,
            r.test_name,
            r.test_type,
            r.status,
            r.detected_at,
            r.database_name,
            r.schema_name,
            r.table_name,
            r.column_name,
            r.test_results_description,
            r.test_results_query,
            ROW_NUMBER() OVER (
                PARTITION BY r.test_unique_id
                ORDER BY r.detected_at DESC
            ) as rn
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results r
        WHERE r.detected_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    )
    SELECT
        r.test_unique_id,
        r.test_name,
        COALESCE(t.short_name, r.test_name) as short_name,
        COALESCE(t.test_namespace, r.test_type) as test_namespace,
        t.test_column_name,
        t.parent_model_unique_id,
        r.test_type,
        r.status,
        r.detected_at,
        r.database_name,
        r.schema_name,
        r.table_name,
        r.column_name,
        r.test_results_description,
        r.test_results_query
    FROM ranked r
    LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_tests t ON r.test_unique_id = t.unique_id
    WHERE r.rn = 1 AND r.status IN ('fail', 'error')
    ORDER BY r.detected_at DESC
    """
    return run_query(query)


def get_current_model_failures(days: int = DEFAULT_LOOKBACK_DAYS, search: str = ""):
    """
    Get model failures where the most recent run failed.
    """
    search_filter = f"AND LOWER(r.unique_id) LIKE LOWER('%{search}%')" if search else ""

    query = f"""
    WITH ranked AS (
        SELECT
            r.unique_id,
            r.name,
            r.status,
            r.execution_time,
            r.generated_at,
            m.database_name,
            m.schema_name,
            r.compile_started_at,
            r.compile_completed_at,
            r.execute_started_at,
            r.execute_completed_at,
            r.message,
            ROW_NUMBER() OVER (
                PARTITION BY r.unique_id
                ORDER BY r.generated_at DESC
            ) as rn
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results r
        LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_models m ON r.unique_id = m.unique_id
        WHERE r.generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND r.resource_type = 'model'
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
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND resource_type = 'model'
    )
    SELECT
        (SELECT COUNT(*) FROM test_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_tests,
        (SELECT COUNT(*) FROM model_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_models
    """
    return run_query(query)
