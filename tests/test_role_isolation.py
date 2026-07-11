import psycopg.errors
import pytest

from conftest import connect

DENIED = [
    ("svc_analytics", "raw.member"),
    ("svc_analytics", "raw.energy_submission"),
    ("svc_matching", "raw.member"),
    ("svc_matching", "pub_private.member_profile"),
    ("svc_matching", "pub_aggregate.sector_summary"),
    ("app_portal", "raw.member"),  # write-only: INSERT/UPDATE granted, SELECT not
    ("app_portal", "pub_private.member_profile"),
    ("app_portal", "pub_aggregate.sector_summary"),
]

ALLOWED = [
    ("svc_analytics", "pub_private.member_profile"),
    ("svc_analytics", "pub_aggregate.sector_summary"),
    ("svc_analytics", "pub_aggregate.sector_energy"),
    ("svc_analytics", "pub_matching.supplier_directory"),
    ("svc_matching", "pub_matching.supplier_directory"),
    ("svc_analytics", "pub_aggregate.reference_stats"),
    ("svc_matching", "pub_matching.buyer_request"),
]


@pytest.mark.parametrize("role,relation", DENIED)
def test_denied(role, relation):
    with connect(role) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f"select * from {relation} limit 1")


@pytest.mark.parametrize("role,relation", ALLOWED)
def test_allowed(role, relation):
    with connect(role) as conn:
        assert conn.execute(f"select count(*) from {relation}").fetchone() is not None


def test_portal_can_write_raw():
    # Self-contained: insert the parent member in the same (rolled-back)
    # transaction so the test doesn't depend on the seed loader having run.
    with connect("app_portal") as conn:
        conn.execute(
            """insert into raw.member (member_id, company, sector)
               values ('TEST-PORTAL', 'Portal Write Test Ltd', 'Packaging')"""
        )
        conn.execute(
            """insert into raw.workforce_submission
                   (member_id, quarter, employment, vacancies, skills_gaps)
               values ('TEST-PORTAL', '2026-Q3', 10, 2, 'industrial welding')"""
        )
        conn.rollback()  # leave no trace
