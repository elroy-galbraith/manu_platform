select
    stat_key,
    label,
    value,
    unit,
    year_or_asof,
    source,
    provenance
from {{ ref('seed_reference_stats') }}
