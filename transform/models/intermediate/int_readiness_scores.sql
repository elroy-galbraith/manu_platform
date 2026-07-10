with certs as (
    select
        member_id,
        count(*) as n_certs,
        max(case when cert_type in ('HACCP', 'FSSC 22000') then 1 else 0 end)
            as has_food_safety_cert
    from {{ ref('stg_certification') }}
    group by member_id
),

capacity as (
    select member_id, utilization_pct
    from {{ ref('stg_capacity_submission') }}
    where quarter = '{{ var("current_quarter") }}'
),

assessment as (
    select member_id, score_packaging, score_logistics,
           score_quality_systems, score_export_history
    from {{ ref('stg_readiness_assessment') }}
    where quarter = '{{ var("current_quarter") }}'
),

scored as (
    select
        m.member_id,
        least(100,
              20 + coalesce(c.n_certs, 0) * 20
                 + coalesce(c.has_food_safety_cert, 0) * 10) as score_certifications,
        least(100,
              round(((100 - cap.utilization_pct) * 1.8 + 20)::numeric)::int)
            as score_capacity_headroom,
        a.score_packaging,
        a.score_logistics,
        a.score_quality_systems,
        a.score_export_history
    from {{ ref('stg_member') }} m
    inner join capacity cap on cap.member_id = m.member_id
    inner join assessment a on a.member_id = m.member_id
    left join certs c on c.member_id = m.member_id
),

composite as (
    select
        *,
        round(
            0.25::float8 * score_certifications
            + 0.15::float8 * score_packaging
            + 0.15::float8 * score_logistics
            + 0.15::float8 * score_quality_systems
            + 0.20::float8 * score_export_history
            + 0.10::float8 * score_capacity_headroom
        )::int as readiness_score
    from scored
)

select
    *,
    case
        when readiness_score >= 75 then 'Export Ready'
        when readiness_score >= 55 then 'Near Ready'
        when readiness_score >= 35 then 'Developing'
        else 'Early Stage'
    end as readiness_band
from composite
