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
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND resource_type = 'model'
    ),
    last_run AS (
        SELECT MAX(generated_at) as last_run_time
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results
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
    """Get most recent dbt invocations with run stats."""
    query = f"""
    WITH run_stats AS (
        SELECT
            invocation_id,
            COUNT(*) as total_models,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN status IN ('fail', 'error') THEN 1 ELSE 0 END) as fail_count,
            SUM(execution_time) as total_time
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results
        WHERE resource_type = 'model'
        GROUP BY invocation_id
    )
    SELECT
        i.invocation_id,
        i.created_at,
        i.run_started_at,
        i.run_completed_at,
        i.command,
        i.target_name,
        i.selected,
        COALESCE(s.total_models, 0) as models_run,
        COALESCE(s.success_count, 0) as success_count,
        COALESCE(s.fail_count, 0) as fail_count,
        COALESCE(s.total_time, 0) as total_time,
        TIMESTAMPDIFF('second', TRY_TO_TIMESTAMP(i.run_started_at), TRY_TO_TIMESTAMP(i.run_completed_at)) as duration_seconds
    FROM {ELEMENTARY_SCHEMA}.dbt_invocations i
    LEFT JOIN run_stats s ON i.invocation_id = s.invocation_id
    ORDER BY i.created_at DESC
    LIMIT {limit}
    """
    return run_query(query)


def get_top_failures(limit: int = 5):
    """Get top current failures for 'needs attention' section with cleaner names."""
    query = f"""
    WITH test_failures AS (
        SELECT
            r.test_unique_id as unique_id,
            COALESCE(t.short_name, r.test_name) as name,
            'test' as type,
            r.detected_at as failed_at,
            r.schema_name,
            COALESCE(t.test_namespace, r.test_type) as test_namespace,
            r.table_name as model_name,
            ROW_NUMBER() OVER (PARTITION BY r.test_unique_id ORDER BY r.detected_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.elementary_test_results r
        LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_tests t ON r.test_unique_id = t.unique_id
        WHERE r.detected_at >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND r.status IN ('fail', 'error')
    ),
    model_failures AS (
        SELECT
            r.unique_id,
            r.name,
            'model' as type,
            r.generated_at as failed_at,
            m.schema_name,
            NULL as test_namespace,
            NULL as model_name,
            ROW_NUMBER() OVER (PARTITION BY r.unique_id ORDER BY r.generated_at DESC) as rn
        FROM {ELEMENTARY_SCHEMA}.dbt_run_results r
        LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_models m ON r.unique_id = m.unique_id
        WHERE r.generated_at >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND r.status IN ('fail', 'error')
        AND r.resource_type = 'model'
    )
    SELECT unique_id, name, type, failed_at, schema_name, test_namespace, model_name
    FROM (
        SELECT * FROM test_failures WHERE rn = 1
        UNION ALL
        SELECT * FROM model_failures WHERE rn = 1
    )
    ORDER BY failed_at DESC
    LIMIT {limit}
    """
    return run_query(query)


def get_project_totals():
    """Get total counts of models and tests in the project (not just recent runs)."""
    query = f"""
    SELECT
        (SELECT COUNT(*) FROM {ELEMENTARY_SCHEMA}.dbt_models) as total_models,
        (SELECT COUNT(DISTINCT test_unique_id) FROM {ELEMENTARY_SCHEMA}.elementary_test_results) as total_tests
    """
    return run_query(query)


def get_total_execution_time(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get total execution time for recent runs."""
    query = f"""
    SELECT SUM(execution_time) as total_time
    FROM {ELEMENTARY_SCHEMA}.dbt_run_results
    WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND resource_type = 'model'
    """
    return run_query(query)
