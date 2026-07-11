select member_id, product_name
from {{ source('raw', 'product') }}
