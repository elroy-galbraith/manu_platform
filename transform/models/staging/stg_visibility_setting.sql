select member_id, field_group, tier, changed_at
from {{ source('raw', 'visibility_setting') }}
