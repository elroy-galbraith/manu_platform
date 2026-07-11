-- Fails (returns rows) if any published aggregate cell covers fewer than 5 firms.
select 'sector_summary' as source_view, sector, member_count
from {{ ref('sector_summary') }}
where member_count < 5

union all

select 'sector_energy' as source_view, sector, member_count
from {{ ref('sector_energy') }}
where member_count < 5
