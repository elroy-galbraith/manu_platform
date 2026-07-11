-- Fails (returns rows) if any member is missing from pub_private.member_profile.
select m.member_id
from {{ ref('stg_member') }} m
left join {{ ref('member_profile') }} p on p.member_id = m.member_id
where p.member_id is null
