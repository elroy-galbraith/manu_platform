select member_id, quarter, capacity, unit, utilization_pct
from {{ source('raw', 'capacity_submission') }}
