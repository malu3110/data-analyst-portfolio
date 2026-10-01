-- One row per CBP crossing, with its latest attributes and BTS truck volume context.
with latest as (
    select distinct on (port_number) *
    from {{ ref('stg_cbp__crossings') }}
    order by port_number, snapshot_id desc
),

bts_window as (
    select max(month) as latest_month from {{ ref('stg_bts__truck_crossings') }}
),

latest_zone as (
    -- the crossing's time zone, from the most recent update time CBP stamped on it
    select distinct on (port_number) port_number, tz_abbrev, utc_offset_hours
    from {{ ref('stg_cbp__commercial_lane_readings') }} r
    join {{ ref('tz_abbreviations') }} using (tz_abbrev)
    order by port_number, snapshot_id desc
),

port_volume as (
    select
        t.port_code,
        sum(t.trucks) as trucks_last_12_months
    from {{ ref('stg_bts__truck_crossings') }} t
    cross join bts_window w
    where t.month > w.latest_month - interval '12 months'
    group by t.port_code
)

select
    l.port_number,
    l.port_code,
    l.port_name,
    l.crossing_name,
    case when coalesce(l.crossing_name, '') = '' then l.port_name
         else l.port_name || ' – ' || l.crossing_name end as crossing_label,
    l.border,
    l.hours,
    l.commercial_max_lanes,
    l.commercial_max_lanes is not null as has_commercial_lanes,
    z.tz_abbrev,
    z.utc_offset_hours,
    v.trucks_last_12_months as port_trucks_last_12_months,
    (select latest_month from bts_window) as bts_latest_month,
    l.captured_at as last_seen_at
from latest l
left join port_volume v on v.port_code = l.port_code
left join latest_zone z on z.port_number = l.port_number
