-- One row per CBP crossing, with its latest attributes and BTS truck volume context.
with latest as (
    select distinct on (port_number) *
    from {{ ref('stg_cbp__crossings') }}
    order by port_number, snapshot_id desc
),

bts_window as (
    select max(month) as latest_month from {{ ref('stg_bts__truck_crossings') }}
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
    l.port_name || ' – ' || l.crossing_name as crossing_label,
    l.border,
    l.hours,
    l.commercial_max_lanes,
    l.commercial_max_lanes is not null as has_commercial_lanes,
    v.trucks_last_12_months as port_trucks_last_12_months,
    (select latest_month from bts_window) as bts_latest_month,
    l.captured_at as last_seen_at
from latest l
left join port_volume v on v.port_code = l.port_code
