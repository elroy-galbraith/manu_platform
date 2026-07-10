select
    member_id,
    quarter,
    monthly_kwh,
    generator_share_pct,
    monthly_energy_cost_jmd,
    energy_pct_of_prod_cost,
    renewable_adoption
from {{ source('raw', 'energy_submission') }}
