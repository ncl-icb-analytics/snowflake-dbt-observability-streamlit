"""Run/invocation queries for the Runs page."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS


def get_invocations(days: int = DEFAULT_LOOKBACK_DAYS, limit: int = 50, offset: int = 0):
    """Get dbt invocations with summary stats."""
    query = f"""
    WITH run_stats AS (
        SELECT
            invocation_id,
            COUNT(*) as total_models,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN status IN ('fail', 'error') THEN 1 ELSE 0 END) as fail_count,
            SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count
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
        i.dbt_user,
        i.selected,
        TRY_PARSE_JSON(i.target_adapter_specific_fields):warehouse::VARCHAR as warehouse,
        COALESCE(s.total_models, 0) as models_run,
        COALESCE(s.success_count, 0) as success_count,
        COALESCE(s.fail_count, 0) as fail_count,
        COALESCE(s.skipped_count, 0) as skipped_count,
        TIMESTAMPDIFF('second', TRY_TO_TIMESTAMP(i.run_started_at), TRY_TO_TIMESTAMP(i.run_completed_at)) as duration_seconds
    FROM {ELEMENTARY_SCHEMA}.dbt_invocations i
    LEFT JOIN run_stats s ON i.invocation_id = s.invocation_id
    WHERE i.created_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY i.created_at DESC
    LIMIT {limit} OFFSET {offset}
    """
    return run_query(query)


def get_invocations_count(days: int = DEFAULT_LOOKBACK_DAYS):
    """Get total count of invocations in time period."""
    query = f"""
    SELECT COUNT(*) as total
    FROM {ELEMENTARY_SCHEMA}.dbt_invocations
    WHERE created_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    """
    return run_query(query)


def get_invocation_details(invocation_id: str):
    """Get full details for a specific invocation."""
    query = f"""
    SELECT
        i.invocation_id,
        i.created_at,
        i.run_started_at,
        i.run_completed_at,
        i.command,
        i.dbt_command,
        i.target_name,
        i.dbt_user,
        i.selected,
        i.dbt_version,
        i.job_url,
        TRY_PARSE_JSON(i.target_adapter_specific_fields):warehouse::VARCHAR as warehouse,
        TIMESTAMPDIFF('second', TRY_TO_TIMESTAMP(i.run_started_at), TRY_TO_TIMESTAMP(i.run_completed_at)) as duration_seconds
    FROM {ELEMENTARY_SCHEMA}.dbt_invocations i
    WHERE i.invocation_id = '{invocation_id}'
    """
    return run_query(query)


def get_invocation_models(invocation_id: str):
    """Get all model runs for a specific invocation with timing for waterfall chart."""
    query = f"""
    SELECT
        r.unique_id,
        r.name,
        r.status,
        r.execution_time,
        r.compile_started_at,
        r.compile_completed_at,
        r.execute_started_at,
        r.execute_completed_at,
        r.generated_at,
        r.message,
        m.schema_name,
        COALESCE(m.original_path, m.path) as model_path
    FROM {ELEMENTARY_SCHEMA}.dbt_run_results r
    LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_models m ON r.unique_id = m.unique_id
    WHERE r.invocation_id = '{invocation_id}'
    AND r.resource_type = 'model'
    ORDER BY r.execute_started_at ASC NULLS LAST, r.generated_at ASC
    """
    return run_query(query)


def get_invocation_tests(invocation_id: str):
    """Get all test runs for a specific invocation."""
    query = f"""
    SELECT
        r.test_unique_id,
        COALESCE(t.short_name, r.test_name) as test_name,
        COALESCE(t.test_namespace, r.test_type) as test_namespace,
        r.table_name as model_name,
        r.status,
        r.detected_at,
        r.test_results_description
    FROM {ELEMENTARY_SCHEMA}.elementary_test_results r
    LEFT JOIN {ELEMENTARY_SCHEMA}.dbt_tests t ON r.test_unique_id = t.unique_id
    WHERE r.invocation_id = '{invocation_id}'
    ORDER BY
        CASE WHEN r.status IN ('fail', 'error') THEN 0
             WHEN r.status = 'warn' THEN 1
             ELSE 2 END,
        r.detected_at ASC
    """
    return run_query(query)
