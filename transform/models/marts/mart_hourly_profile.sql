-- US-06: typical wait by crossing x lane x local hour of day, from fresh, distinct readings.
-- Rows below the minimum reading count are kept but flagged, so the app can say
-- "insufficient history (n = x)" instead of showing a misleading number.
select
    u.port_number,
    d.border,
    d.port_name,
    d.crossing_label,
    u.lane_type,
    u.local_hour,
    count(*)                                                        as n_readings,
    percentile_cont(0.5) within group (order by u.delay_minutes)    as median_delay_minutes,
    min(u.delay_minutes)                                            as min_delay_minutes,
    max(u.delay_minutes)                                            as max_delay_minutes,
    count(*) >= {{ var('min_readings_for_profile') }}               as is_sufficient,
    min(u.cbp_updated_at)                                           as first_reading_at,
    max(u.cbp_updated_at)                                           as last_reading_at
from {{ ref('int_lane_readings_unique') }} u
join {{ ref('dim_crossing') }} d using (port_number)
where not u.is_stale
group by 1, 2, 3, 4, 5, 6
