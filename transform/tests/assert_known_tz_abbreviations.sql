-- Every parsed update time must map to a known zone; otherwise extend the seed.
select update_time_raw
from {{ ref('stg_cbp__commercial_lane_readings') }}
where update_time_raw is not null and tz_abbrev is null
