-- US-08: how much the FAST lane saves vs the standard lane, from readings CBP
-- published at the same moment for the same crossing.
with pairs as (
    select
        s.port_number,
        s.cbp_updated_at,
        s.delay_minutes as standard_minutes,
        f.delay_minutes as fast_minutes
    from {{ ref('int_lane_readings_unique') }} s
    join {{ ref('int_lane_readings_unique') }} f
      on f.port_number = s.port_number
     and f.cbp_updated_at = s.cbp_updated_at
     and f.lane_type = 'fast'
    where s.lane_type = 'standard'
      and not s.is_stale and not f.is_stale
)

select
    p.port_number,
    d.border,
    d.port_name,
    d.crossing_label,
    count(*)                                                                         as n_pairs,
    percentile_cont(0.5) within group (order by p.standard_minutes)                  as median_standard_minutes,
    percentile_cont(0.5) within group (order by p.fast_minutes)                      as median_fast_minutes,
    percentile_cont(0.5) within group (order by p.standard_minutes - p.fast_minutes) as median_minutes_saved,
    count(*) >= {{ var('min_readings_for_profile') }}                                as is_sufficient
from pairs p
join {{ ref('dim_crossing') }} d using (port_number)
group by 1, 2, 3, 4
