"""Model run queries."""

from database import run_query
from config import ELEMENTARY_SCHEMA, DEFAULT_LOOKBACK_DAYS, DEFAULT_PAGE_SIZE


def get_models_summary(
    days: int = DEFAULT_LOOKBACK_DAYS,
    search: str = "",
    show_all: bool = False,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
):
    """
    Get model summary with latest status and avg execution time.
    By default shows only models with issues (failed or slow).
    """
    search_filter = f"AND LOWER(unique_id) LIKE LOWER('%{search}%')" if search else ""
    issues_filter = "" if show_all else "AND (latest_status IN ('fail', 'error') OR is_slow = TRUE)"

    query = f"""
    WITH model_stats AS (
        SELECT
            unique_id,
            name,
            schema_name,
            database_name,
            status,
            execution_time,
            generated_at,
            ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY generated_at DESC) as rn,
            AVG(execution_time) OVER (PARTITION BY unique_id) as avg_execution_time,
            COUNT(*) OVER (PARTITION BY unique_id) as run_count
        FROM {ELEMENTARY_SCHEMA}.model_run_results
        WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        {search_filter}
    ),
    percentiles AS (
        SELECT PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY avg_execution_time) as p90
        FROM (SELECT DISTINCT unique_id, AVG(execution_time) as avg_execution_time
              FROM {ELEMENTARY_SCHEMA}.model_run_results
              WHERE generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
              GROUP BY unique_id)
    )
    SELECT
        ms.unique_id,
        ms.name,
        ms.schema_name,
        ms.database_name,
        ms.status as latest_status,
        ms.generated_at as last_run,
        ms.avg_execution_time,
        ms.run_count,
        CASE WHEN ms.avg_execution_time > p.p90 THEN TRUE ELSE FALSE END as is_slow
    FROM model_stats ms
    CROSS JOIN percentiles p
    WHERE ms.rn = 1
    {issues_filter}
    ORDER BY
        CASE WHEN ms.status IN ('fail', 'error') THEN 0 ELSE 1 END,
        ms.avg_execution_time DESC NULLS LAST
    LIMIT {limit} OFFSET {offset}
    """
    return run_query(query)


def get_model_run_history(unique_id: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get run history for a specific model including error messages."""
    query = f"""
    SELECT
        unique_id,
        name,
        status,
        execution_time,
        generated_at,
        compile_started_at,
        compile_completed_at,
        execute_started_at,
        execute_completed_at,
        message
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE unique_id = '{unique_id}'
    AND generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY generated_at DESC
    """
    return run_query(query)


def get_model_details(unique_id: str):
    """Get model metadata including compiled SQL."""
    query = f"""
    SELECT
        unique_id,
        name,
        schema_name,
        database_name,
        alias,
        description,
        owner,
        tags,
        package_name,
        original_path,
        path,
        compiled_code
    FROM {ELEMENTARY_SCHEMA}.dbt_models
    WHERE unique_id = '{unique_id}'
    """
    return run_query(query)


def get_model_execution_trend(unique_id: str, days: int = DEFAULT_LOOKBACK_DAYS):
    """Get execution time trend for charting."""
    query = f"""
    SELECT
        DATE_TRUNC('day', generated_at) as run_date,
        AVG(execution_time) as avg_time,
        MAX(execution_time) as max_time,
        MIN(execution_time) as min_time,
        COUNT(*) as run_count
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE unique_id = '{unique_id}'
    AND generated_at >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', generated_at)
    ORDER BY run_date
    """
    return run_query(query)


def get_schema_list():
    """Get list of schemas for filtering."""
    query = f"""
    SELECT DISTINCT schema_name
    FROM {ELEMENTARY_SCHEMA}.model_run_results
    WHERE schema_name IS NOT NULL
    ORDER BY schema_name
    """
    return run_query(query)
