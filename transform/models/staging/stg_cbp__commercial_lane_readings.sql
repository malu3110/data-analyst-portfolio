-- One row per snapshot x crossing x commercial lane type (standard / FAST).
--
-- CBP gives each lane's update time as text like "At 2:00 pm CDT": a local
-- time-of-day and zone abbreviation, but no date. The date is inferred from our
-- capture time: take the capture moment in that zone; if the stated time-of-day
-- would be in the future, the reading is from the previous day.
with crossings as (
    select s.snapshot_id, s.captured_at, r
    from {{ source('raw', 'cbp_snapshot') }} s
    cross join lateral jsonb_array_elements(s.payload) as r
    where r -> 'commercial_vehicle_lanes' ->> 'maximum_lanes' ~ '^\d+$'
),

lanes as (
    select
        c.snapshot_id,
        c.captured_at,
        c.r ->> 'port_number' as port_number,
        l.lane_type,
        l.lane
    from crossings c
    cross join lateral (values
        ('standard', c.r -> 'commercial_vehicle_lanes' -> 'standard_lanes'),
        ('fast',     c.r -> 'commercial_vehicle_lanes' -> 'FAST_lanes')
    ) as l (lane_type, lane)
    where l.lane is not null
),

parsed as (
    select
        snapshot_id,
        captured_at,
        port_number,
        lane_type,
        lane ->> 'operational_status' as operational_status,
        case when lane ->> 'delay_minutes' ~ '^\d+$' then (lane ->> 'delay_minutes')::int end as delay_minutes,
        case when lane ->> 'lanes_open' ~ '^\d+$' then (lane ->> 'lanes_open')::int end as lanes_open,
        nullif(lane ->> 'update_time', '') as update_time_raw,
        regexp_match(lane ->> 'update_time', '^At (\d{1,2}):(\d{2}) (am|pm) ([A-Za-z]{3,4})$', 'i') as m
    from lanes
),

zoned as (
    select
        p.*,
        tz.tz_abbrev,
        tz.utc_offset_hours,
        (p.m[1]::int % 12) + case when lower(p.m[3]) = 'pm' then 12 else 0 end as update_hour,
        p.m[2]::int as update_minute,
        (p.captured_at at time zone 'UTC') + make_interval(hours => tz.utc_offset_hours) as captured_local
    from parsed p
    left join {{ ref('tz_abbreviations') }} tz on tz.tz_abbrev = upper(p.m[4])
),

dated as (
    select
        z.*,
        case
            when candidate_local > captured_local + interval '15 minutes'
                then candidate_local - interval '1 day'
            else candidate_local
        end as updated_local
    from (
        select *, date_trunc('day', captured_local) + make_interval(hours => update_hour, mins => update_minute) as candidate_local
        from zoned
    ) z
),

final as (
    select
        md5(snapshot_id::text || '|' || port_number || '|' || lane_type) as reading_id,
        snapshot_id,
        captured_at,
        port_number,
        lane_type,
        operational_status,
        delay_minutes,
        lanes_open,
        update_time_raw,
        tz_abbrev,
        (updated_local - make_interval(hours => utc_offset_hours)) at time zone 'UTC' as cbp_updated_at,
        updated_local                                     as cbp_updated_local,
        extract(hour from updated_local)::int             as local_hour,
        extract(isodow from updated_local)::int           as local_isodow
    from dated
)

select
    *,
    round(extract(epoch from (captured_at - cbp_updated_at)) / 60)::int as reading_age_minutes,
    coalesce(extract(epoch from (captured_at - cbp_updated_at)) / 60 > {{ var('stale_after_minutes') }}, false) as is_stale,
    case
        when lower(operational_status) = 'lanes closed'   then 'closed'
        when lower(operational_status) = 'update pending' then 'pending'
        when lower(operational_status) = 'n/a'            then 'not_applicable'
        when delay_minutes is not null and cbp_updated_at is not null then 'reported'
        else 'unparsed'
    end as reading_status
from final
