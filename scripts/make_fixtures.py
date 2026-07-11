"""Extract the generator's computed scores into a dbt seed used as the rubric oracle."""
import csv
import os

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed-data")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "transform", "seeds", "expected_scores.csv")
COLS = ["member_id", "score_certifications", "score_capacity_headroom",
        "readiness_score", "readiness_band"]


def main():
    with open(os.path.join(SEED_DIR, "members.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows([{c: r[c] for c in COLS} for r in rows])
    print(f"wrote {len(rows)} fixture rows to {OUT}")


if __name__ == "__main__":
    main()
