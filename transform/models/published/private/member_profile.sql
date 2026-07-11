with products as (
    select member_id, string_agg(product_name, '; ' order by product_name) as products
    from {{ ref('stg_product') }}
    group by member_id
),

certs as (
    select member_id, string_agg(cert_type, '; ' order by cert_type) as certifications
    from {{ ref('stg_certification') }}
    group by member_id
)

select
    m.member_id,
    m.company,
    m.sector,
    m.parish,
    m.lat,
    m.lon,
    m.employees,
    m.size_band,
    m.lead_time_days,
    m.export_status,
    m.export_markets,
    p.products,
    c.certifications,
    cap.capacity,
    cap.unit as capacity_unit,
    cap.utilization_pct,
    sc.spare_capacity,
    e.monthly_kwh,
    e.generator_share_pct,
    e.monthly_energy_cost_jmd,
    e.energy_pct_of_prod_cost,
    e.renewable_adoption,
    r.score_certifications,
    r.score_capacity_headroom,
    r.score_packaging,
    r.score_logistics,
    r.score_quality_systems,
    r.score_export_history,
    r.readiness_score,
    r.readiness_band
from {{ ref('stg_member') }} m
left join products p on p.member_id = m.member_id
left join certs c on c.member_id = m.member_id
inner join {{ ref('stg_capacity_submission') }} cap
    on cap.member_id = m.member_id and cap.quarter = '{{ var("current_quarter") }}'
inner join {{ ref('int_spare_capacity') }} sc
    on sc.member_id = m.member_id and sc.quarter = '{{ var("current_quarter") }}'
inner join {{ ref('stg_energy_submission') }} e
    on e.member_id = m.member_id and e.quarter = '{{ var("current_quarter") }}'
inner join {{ ref('int_readiness_scores') }} r on r.member_id = m.member_id
