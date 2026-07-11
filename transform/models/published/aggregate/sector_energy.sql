select
    m.sector,
    count(distinct m.member_id) as member_count,
    round(avg(e.monthly_kwh))::int as avg_monthly_kwh,
    round(avg(e.generator_share_pct))::int as avg_generator_share_pct,
    round(avg(e.energy_pct_of_prod_cost)::numeric, 1) as avg_energy_pct_of_prod_cost,
    round(avg(e.monthly_energy_cost_jmd))::bigint as avg_monthly_energy_cost_jmd
from {{ ref('stg_member') }} m
inner join {{ ref('stg_energy_submission') }} e
    on e.member_id = m.member_id and e.quarter = '{{ var("current_quarter") }}'
group by m.sector
having count(distinct m.member_id) >= 5
