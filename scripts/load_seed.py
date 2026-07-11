"""Load generator seed CSVs into the raw schema (truncate-and-reload, one transaction)."""
import csv
import os

import psycopg

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed-data")
QUARTER = "2026-Q2"
TABLES = ["workforce_submission", "visibility_setting", "readiness_assessment",
          "energy_submission", "certification", "capacity_submission",
          "product", "buyer_request", "member"]


def admin_dsn() -> str:
    return (
        f"host={os.environ.get('JMEA_DB_HOST', 'localhost')} "
        f"port={os.environ.get('JMEA_DB_PORT', '5433')} "
        f"dbname={os.environ.get('JMEA_DB_NAME', 'jmea')} "
        f"user={os.environ.get('JMEA_DB_ADMIN_USER', 'jmea_admin')} "
        f"password={os.environ.get('JMEA_DB_ADMIN_PASSWORD', 'jmea_dev_admin')}"
    )


def read_csv(name: str) -> list[dict]:
    with open(os.path.join(SEED_DIR, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    members = read_csv("members.csv")
    buyers = read_csv("buyer_requests.csv")
    with psycopg.connect(admin_dsn()) as conn, conn.cursor() as cur:
        cur.execute("truncate table " + ", ".join(f"raw.{t}" for t in TABLES) + " cascade")
        for m in members:
            cur.execute(
                """insert into raw.member (member_id, company, sector, parish, lat, lon,
                       employees, size_band, lead_time_days, export_status, export_markets)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (m["member_id"], m["company"], m["sector"], m["parish"], m["lat"], m["lon"],
                 m["employees"], m["size_band"], m["lead_time_days"], m["export_status"],
                 m["export_markets"] or None),
            )
            for prod in m["products"].split("; "):
                cur.execute(
                    "insert into raw.product (member_id, product_name) values (%s, %s)",
                    (m["member_id"], prod),
                )
            cur.execute(
                """insert into raw.capacity_submission
                       (member_id, quarter, capacity, unit, utilization_pct)
                   values (%s, %s, %s, %s, %s)""",
                (m["member_id"], QUARTER, m["capacity"], m["capacity_unit"],
                 m["utilization_pct"]),
            )
            if m["certifications"] != "None":
                for cert in m["certifications"].split("; "):
                    cur.execute(
                        """insert into raw.certification
                               (member_id, cert_type, verification_status)
                           values (%s, %s, 'unverified')""",
                        (m["member_id"], cert),
                    )
            cur.execute(
                """insert into raw.energy_submission
                       (member_id, quarter, monthly_kwh, generator_share_pct,
                        monthly_energy_cost_jmd, energy_pct_of_prod_cost, renewable_adoption)
                   values (%s, %s, %s, %s, %s, %s, %s)""",
                (m["member_id"], QUARTER, m["monthly_kwh"], m["generator_share_pct"],
                 m["monthly_energy_cost_jmd"], m["energy_pct_of_prod_cost"],
                 m["renewable_adoption"]),
            )
            cur.execute(
                """insert into raw.readiness_assessment
                       (member_id, quarter, score_packaging, score_logistics,
                        score_quality_systems, score_export_history)
                   values (%s, %s, %s, %s, %s, %s)""",
                (m["member_id"], QUARTER, m["score_packaging"], m["score_logistics"],
                 m["score_quality_systems"], m["score_export_history"]),
            )
            tier = 3 if m["matching_opt_in"] == "True" else 1
            cur.execute(
                """insert into raw.visibility_setting (member_id, field_group, tier)
                   values (%s, 'matching', %s)""",
                (m["member_id"], tier),
            )
        for b in buyers:
            cur.execute(
                """insert into raw.buyer_request
                       (request_id, buyer, buyer_type, location, products_needed,
                        sector, required_cert, monthly_volume, volume_unit, max_lead_time_days)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (b["request_id"], b["buyer"], b["buyer_type"], b["location"],
                 b["products_needed"], b["sector"], b["required_cert"] or None,
                 b["monthly_volume"], b["volume_unit"], b["max_lead_time_days"]),
            )
    print(f"loaded members={len(members)} buyers={len(buyers)}")


if __name__ == "__main__":
    main()
