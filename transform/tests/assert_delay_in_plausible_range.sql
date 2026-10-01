-- Delays outside 0..24h indicate a parsing problem, not a real queue.
select *
from {{ ref('stg_cbp__commercial_lane_readings') }}
where delay_minutes < 0 or delay_minutes > 1440
