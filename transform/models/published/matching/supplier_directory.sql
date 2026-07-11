with tier3 as (
    select member_id
    from {{ ref('stg_visibility_setting') }}
    where field_group = 'matching' and tier = 3
),

products as (
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
    m.lead_time_days,
    p.products,
    c.certifications,
    cap.capacity,
    cap.unit as capacity_unit,
    sc.spare_capacity,
    r.readiness_score,
    r.readiness_band
from {{ ref('stg_member') }} m
inner join tier3 t on t.member_id = m.member_id
left join products p on p.member_id = m.member_id
left join certs c on c.member_id = m.member_id
left join {{ ref('stg_capacity_submission') }} cap
    on cap.member_id = m.member_id and cap.quarter = '{{ var("current_quarter") }}'
left join {{ ref('int_spare_capacity') }} sc
    on sc.member_id = m.member_id and sc.quarter = '{{ var("current_quarter") }}'
left join {{ ref('int_readiness_scores') }} r on r.member_id = m.member_id
