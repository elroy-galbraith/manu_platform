select
    member_id,
    quarter,
    score_packaging,
    score_logistics,
    score_quality_systems,
    score_export_history
from {{ source('raw', 'readiness_assessment') }}
