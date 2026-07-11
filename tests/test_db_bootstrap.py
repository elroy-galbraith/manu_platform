from conftest import connect

EXPECTED_SCHEMAS = {
    "raw", "staging", "intermediate", "fixtures",
    "pub_private", "pub_aggregate", "pub_matching",
}
EXPECTED_ROLES = {"app_portal", "transform", "svc_analytics", "svc_matching"}
EXPECTED_RAW_TABLES = {
    "member", "product", "capacity_submission", "certification",
    "energy_submission", "readiness_assessment", "buyer_request",
    "visibility_setting", "workforce_submission",
}


def test_schemas_exist():
    with connect("jmea_admin") as conn:
        rows = conn.execute("select nspname from pg_namespace").fetchall()
    assert EXPECTED_SCHEMAS <= {r[0] for r in rows}


def test_roles_exist():
    with connect("jmea_admin") as conn:
        rows = conn.execute("select rolname from pg_roles").fetchall()
    assert EXPECTED_ROLES <= {r[0] for r in rows}


def test_raw_tables_exist():
    with connect("jmea_admin") as conn:
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema = 'raw'"
        ).fetchall()
    assert {r[0] for r in rows} == EXPECTED_RAW_TABLES


def test_lightdash_app_db_exists():
    with connect("jmea_admin") as conn:
        dbs = {r[0] for r in conn.execute("select datname from pg_database").fetchall()}
        roles = {r[0] for r in conn.execute("select rolname from pg_roles").fetchall()}
    assert "lightdash" in dbs
    assert "lightdash" in roles
