select
    member_id,
    company,
    sector,
    parish,
    lat,
    lon,
    employees,
    size_band,
    lead_time_days,
    export_status,
    export_markets
from {{ source('raw', 'member') }}
