import subprocess
import sys

from conftest import connect

TABLES = ["member", "product", "capacity_submission", "certification",
          "energy_submission", "readiness_assessment", "buyer_request",
          "visibility_setting", "workforce_submission"]


def row_counts():
    with connect("jmea_admin") as conn:
        return {t: conn.execute(f"select count(*) from raw.{t}").fetchone()[0]
                for t in TABLES}


def run_loader():
    subprocess.run([sys.executable, "scripts/load_seed.py"], check=True)


def test_loader_loads_expected_counts():
    run_loader()
    counts = row_counts()
    assert counts["member"] == 72
    assert counts["buyer_request"] == 15
    assert counts["capacity_submission"] == 72
    assert counts["energy_submission"] == 72
    assert counts["readiness_assessment"] == 72
    assert counts["visibility_setting"] == 72
    assert counts["workforce_submission"] == 0
    assert counts["product"] >= 72          # 1-3 products per member
    assert counts["certification"] > 0      # ~75% of members hold >=1 cert


def test_visibility_tiers_are_1_or_3():
    run_loader()
    with connect("jmea_admin") as conn:
        tiers = {r[0] for r in conn.execute(
            "select distinct tier from raw.visibility_setting").fetchall()}
    assert tiers <= {1, 3} and 3 in tiers


def test_loader_is_idempotent():
    run_loader()
    first = row_counts()
    run_loader()
    assert row_counts() == first
