select
    member_id,
    quarter,
    capacity,
    unit,
    utilization_pct,
    round((capacity * (100 - utilization_pct))::float8 / 100)::int as spare_capacity
from {{ ref('stg_capacity_submission') }}
