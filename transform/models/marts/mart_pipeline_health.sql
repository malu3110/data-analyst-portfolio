-- Success metrics §6.2 and US-04/US-10: is the scheduled capture keeping up,
-- and how much of what CBP publishes is usable?
with runs as (
    select
        date_trunc('day', started_at at time zone 'UTC')::date as run_date,
        count(*) filter (where status = 'success')  as runs_succeeded,
        count(*) filter (where status = 'failed')   as runs_failed,
        count(distinct date_trunc('hour', started_at)) filter (where status = 'success') as hours_with_success
    from {{ source('raw', 'pipeline_run') }}
    where job = 'ingest_cbp'
    group by 1
),

readings as (
    select
        date_trunc('day', captured_at at time zone 'UTC')::date as run_date,
        count(*) filter (where reading_status <> 'not_applicable') as lane_readings,
        count(*) filter (where reading_status = 'reported' and not is_stale) as usable_readings
    from {{ ref('stg_cbp__commercial_lane_readings') }}
    group by 1
)

select
    r.run_date,
    case when r.run_date = (now() at time zone 'UTC')::date
         then extract(hour from now() at time zone 'UTC')::int + 1
         else 24 end                                           as expected_hourly_runs,
    r.runs_succeeded,
    r.runs_failed,
    r.hours_with_success,
    coalesce(q.lane_readings, 0)                               as lane_readings,
    coalesce(q.usable_readings, 0)                             as usable_readings,
    round(100.0 * q.usable_readings / nullif(q.lane_readings, 0), 1) as pct_usable
from runs r
left join readings q using (run_date)
