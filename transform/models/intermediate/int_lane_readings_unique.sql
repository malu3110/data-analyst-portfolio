-- Each distinct CBP reading exactly once (US-04). The hourly job can capture the
-- same CBP update more than once (CBP hasn't refreshed yet, or a re-run), so
-- keep the earliest capture per crossing x lane x CBP update time.
select distinct on (port_number, lane_type, cbp_updated_at)
    port_number || '|' || lane_type || '|' || to_char(cbp_updated_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI') as reading_key,
    port_number,
    lane_type,
    cbp_updated_at,
    cbp_updated_local,
    local_hour,
    local_isodow,
    delay_minutes,
    lanes_open,
    captured_at,
    reading_age_minutes,
    is_stale
from {{ ref('stg_cbp__commercial_lane_readings') }}
where reading_status = 'reported'
order by port_number, lane_type, cbp_updated_at, captured_at
