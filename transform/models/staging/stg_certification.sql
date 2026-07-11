select member_id, cert_type, verification_status
from {{ source('raw', 'certification') }}
