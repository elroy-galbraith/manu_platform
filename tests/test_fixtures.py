import csv
from pathlib import Path

FIXTURE = Path("transform/seeds/expected_scores.csv")


def test_fixture_shape():
    with FIXTURE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 72
    assert set(rows[0].keys()) == {
        "member_id", "score_certifications", "score_capacity_headroom",
        "readiness_score", "readiness_band",
    }
    assert all(r["readiness_band"] in
               {"Export Ready", "Near Ready", "Developing", "Early Stage"} for r in rows)
