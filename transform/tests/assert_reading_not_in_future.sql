-- A CBP update can't be later than when we captured it (allowing 15 min clock skew).
-- Guards the date-inference logic for "At h:mm am TZ" update times.
select *
from {{ ref('stg_cbp__commercial_lane_readings') }}
where cbp_updated_at > captured_at + interval '15 minutes'
