select
    m.sector,
    count(distinct m.member_id) as member_count,
    max(cap.unit) as capacity_unit,
    round(avg(cap.utilization_pct))::int as avg_utilization_pct,
    sum(sc.spare_capacity) as total_spare_capacity,
    round(avg(r.readiness_score))::int as avg_readiness_score,
    count(*) filter (where r.readiness_band in ('Export Ready', 'Near Ready'))
        as members_near_or_export_ready
from {{ ref('stg_member') }} m
inner join {{ ref('stg_capacity_submission') }} cap
    on cap.member_id = m.member_id and cap.quarter = '{{ var("current_quarter") }}'
inner join {{ ref('int_spare_capacity') }} sc
    on sc.member_id = m.member_id and sc.quarter = '{{ var("current_quarter") }}'
inner join {{ ref('int_readiness_scores') }} r on r.member_id = m.member_id
group by m.sector
having count(distinct m.member_id) >= 5
