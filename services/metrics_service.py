"""Metrics queries for dashboard KPIs."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def get_dashboard_kpis(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get main dashboard KPIs in a single query."""
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
            execution_time,
            ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY generated_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ),
    last_run AS (
        SELECT MAX(generated_at) as last_run_time
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    )
    SELECT
        (SELECT COUNT(*) FROM test_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_tests,
        (SELECT COUNT(*) FROM test_ranked WHERE rn = 1) as total_tests_run,
        (SELECT COUNT(*) FROM model_ranked WHERE rn = 1 AND status IN ('fail', 'error')) as failed_models,
        (SELECT COUNT(*) FROM model_ranked WHERE rn = 1) as total_models_run,
        (SELECT AVG(execution_time) FROM model_ranked WHERE rn = 1) as avg_execution_time,
        (SELECT last_run_time FROM last_run) as last_run_time
    """
    return run_query(query)


def get_recent_runs(limit: int = 10):
    """Get most recent dbt invocations."""
    query = f"""
    SELECT
        invocation_id,
        generated_at,
        command,
        dbt_version,
        full_refresh,
        target_name,
        selected
    FROM {ELEMENTARY_SCHEMA}.dbt_invocations
    ORDER BY generated_at DESC
    LIMIT {limit}
    """
    return run_query(query)


def get_top_failures(limit: int = 5):
    """Get top current failures for 'needs attention' section."""
    query = f"""
    WITH test_failures AS (
        SELECT
            test_name as name,
            'test' as type,
            detected_at as failed_at,
            schema_name,
            ROW_NUMBER() OVER (PARTITION BY test_unique_id ORDER BY detected_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results
        WHERE detected_at >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND status IN ('fail', 'error')
    ),
    model_failures AS (
        SELECT
            name,
            'model' as type,
            generated_at as failed_at,
            schema_name,
            ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY generated_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND status IN ('fail', 'error')
    )
    SELECT name, type, failed_at, schema_name
    FROM (
        SELECT * FROM test_failures WHERE rn = 1
        UNION ALL
        SELECT * FROM model_failures WHERE rn = 1
    )
    ORDER BY failed_at DESC
    LIMIT {limit}
    """
    return run_query(query)
