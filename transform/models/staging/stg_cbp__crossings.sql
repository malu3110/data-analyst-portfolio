-- One row per snapshot x crossing: crossing attributes as CBP reported them.
select
    s.snapshot_id,
    s.captured_at,
    r ->> 'port_number'                                   as port_number,
    left(r ->> 'port_number', 4)                          as port_code,
    r ->> 'port_name'                                     as port_name,
    r ->> 'crossing_name'                                 as crossing_name,
    case r ->> 'border'
        when 'Mexican Border' then 'US-Mexico'
        when 'Canadian Border' then 'US-Canada'
        else r ->> 'border'
    end                                                   as border,
    r ->> 'port_status'                                   as port_status,
    nullif(r ->> 'hours', '')                             as hours,
    case when r -> 'commercial_vehicle_lanes' ->> 'maximum_lanes' ~ '^\d+$'
         then (r -> 'commercial_vehicle_lanes' ->> 'maximum_lanes')::int end
                                                          as commercial_max_lanes,
    nullif(r ->> 'construction_notice', '')               as construction_notice
from {{ source('raw', 'cbp_snapshot') }} s
cross join lateral jsonb_array_elements(s.payload) as r
