-- How much history the pipeline has accumulated (shown in the app header).
select
    min(captured_at) as first_capture_at,
    max(captured_at) as last_capture_at,
    count(*)         as captures
from {{ source('raw', 'cbp_snapshot') }}
