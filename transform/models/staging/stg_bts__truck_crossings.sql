-- BTS monthly inbound truck crossings by port, typed.
select
    port_code,
    port_name,
    state,
    case border
        when 'US-Mexico Border' then 'US-Mexico'
        when 'US-Canada Border' then 'US-Canada'
        else border
    end                                  as border,
    left(month, 10)::date                as month,
    nullif(value, '')::numeric::bigint   as trucks
from {{ source('raw', 'bts_truck_crossing') }}
where measure = 'Trucks'
