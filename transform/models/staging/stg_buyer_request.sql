select
    request_id,
    buyer,
    buyer_type,
    location,
    products_needed,
    sector,
    required_cert,
    monthly_volume,
    volume_unit,
    max_lead_time_days
from {{ source('raw', 'buyer_request') }}
