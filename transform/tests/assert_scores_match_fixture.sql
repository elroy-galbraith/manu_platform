-- Fails (returns rows) when dbt-computed scores disagree with the generator oracle.
with diffs as (
    select
        coalesce(f.member_id, i.member_id) as member_id,
        f.score_certifications     as expected_cert,
        i.score_certifications     as actual_cert,
        f.score_capacity_headroom  as expected_capa,
        i.score_capacity_headroom  as actual_capa,
        f.readiness_score          as expected_score,
        i.readiness_score          as actual_score,
        f.readiness_band           as expected_band,
        i.readiness_band           as actual_band
    from {{ ref('expected_scores') }} f
    full outer join {{ ref('int_readiness_scores') }} i using (member_id)
)
select *
from diffs
where expected_cert is distinct from actual_cert
   or expected_capa is distinct from actual_capa
   or expected_score is distinct from actual_score
   or expected_band is distinct from actual_band
