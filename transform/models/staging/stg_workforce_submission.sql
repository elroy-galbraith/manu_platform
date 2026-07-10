select member_id, quarter, employment, vacancies, skills_gaps
from {{ source('raw', 'workforce_submission') }}
