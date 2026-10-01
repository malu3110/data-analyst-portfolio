-- US-01/02/03: current commercial waits, one row per crossing, from the latest snapshot.
with latest_snapshot as (
    select max(snapshot_id) as snapshot_id from {{ source('raw', 'cbp_snapshot') }}
),

r as (
    select lr.*
    from {{ ref('stg_cbp__commercial_lane_readings') }} lr
    join latest_snapshot ls using (snapshot_id)
)

select
    d.port_number,
    d.border,
    d.port_name,
    d.crossing_name,
    d.crossing_label,
    d.commercial_max_lanes,
    d.utc_offset_hours,
    max(r.captured_at)                                                         as captured_at,
    max(r.reading_status)      filter (where r.lane_type = 'standard')        as standard_status,
    max(r.delay_minutes)       filter (where r.lane_type = 'standard')        as standard_delay_minutes,
    max(r.lanes_open)          filter (where r.lane_type = 'standard')        as standard_lanes_open,
    max(r.cbp_updated_at)      filter (where r.lane_type = 'standard')        as standard_updated_at,
    max(r.update_time_raw)     filter (where r.lane_type = 'standard')        as standard_update_time_text,
    max(r.reading_age_minutes) filter (where r.lane_type = 'standard')        as standard_reading_age_minutes,
    bool_or(r.is_stale)        filter (where r.lane_type = 'standard')        as standard_is_stale,
    max(r.reading_status)      filter (where r.lane_type = 'fast')            as fast_status,
    max(r.delay_minutes)       filter (where r.lane_type = 'fast')            as fast_delay_minutes,
    max(r.lanes_open)          filter (where r.lane_type = 'fast')            as fast_lanes_open,
    max(r.cbp_updated_at)      filter (where r.lane_type = 'fast')            as fast_updated_at,
    max(r.update_time_raw)     filter (where r.lane_type = 'fast')            as fast_update_time_text,
    max(r.reading_age_minutes) filter (where r.lane_type = 'fast')            as fast_reading_age_minutes,
    bool_or(r.is_stale)        filter (where r.lane_type = 'fast')            as fast_is_stale
from r
join {{ ref('dim_crossing') }} d using (port_number)
group by 1, 2, 3, 4, 5, 6, 7
