-- US-05: monthly inbound truck crossings by port (BTS), for volume context.
select
    port_code,
    port_name,
    state,
    border,
    month,
    trucks,
    month = max(month) over () as is_latest_month
from {{ ref('stg_bts__truck_crossings') }}
