import json
import os
import re
import urllib.request
from pathlib import Path

import pytest

BASE = os.environ.get("LIGHTDASH_URL", "http://localhost:8080")
PAT = os.environ.get("LIGHTDASH_PAT", "")
PROJECT = os.environ.get("LIGHTDASH_PROJECT", "")

EXPECTED_DASHBOARDS = {
    "Capacity Overview",
    "Tourism & Buyer Matching",
    "Export Readiness",
    "Energy Burden",
}

PROFILES_PATH = Path(__file__).resolve().parent.parent / "transform" / "profiles.yml"

needs_bootstrap = pytest.mark.skipif(
    not (PAT and PROJECT),
    reason="LIGHTDASH_PAT/LIGHTDASH_PROJECT not set - run the README bootstrap and export them",
)


def _get(path):
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"ApiKey {PAT}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _lightdash_target_user():
    """Return the `user:` value of the `lightdash:` output target in transform/profiles.yml.

    profiles.yml has a small, fixed two-target structure (`dev` and
    `lightdash`), so a targeted line scan is enough here - no need to pull in
    a YAML parser for one field. Find the `lightdash:` block, then return the
    first `user:` value nested under it.
    """
    in_lightdash = False
    for line in PROFILES_PATH.read_text().splitlines():
        if re.match(r"^\s{4}lightdash:\s*$", line):
            in_lightdash = True
            continue
        if in_lightdash:
            if re.match(r"^\s{4}\S", line):  # dedent back to a sibling target
                break
            m = re.match(r"^\s+user:\s*(\S+)\s*$", line)
            if m:
                return m.group(1)
    raise AssertionError("could not find `user:` under the `lightdash:` target in profiles.yml")


def test_lightdash_health():
    with urllib.request.urlopen(f"{BASE}/api/v1/health", timeout=10) as r:
        assert r.status == 200


@needs_bootstrap
def test_four_dashboards_exist():
    body = _get(f"/api/v1/projects/{PROJECT}/dashboards")
    names = {d["name"] for d in body["results"]}
    assert EXPECTED_DASHBOARDS <= names


@needs_bootstrap
def test_warehouse_connection_is_svc_analytics():
    # Lightdash's API redacts the warehouse connection user (the project
    # response only exposes {type, host, port, dbname, schema, sslmode} under
    # warehouseConnection - no `user` key), so we can't assert on
    # body["results"]["warehouseConnection"]["user"] directly.
    #
    # Instead, prove it with two checks: (1) a live check that the deployed
    # project's semantic layer was built from the `lightdash` dbt target, and
    # (2) a static config check that the `lightdash` target's `user` is
    # `svc_analytics`. These two checks establish the *configured* target is
    # svc_analytics (dbt target name + profiles.yml) - the Lightdash API
    # redacts warehouseConnection.user, so the true live-connection identity
    # can't be directly asserted here without a live SQL query (out of scope
    # / would be racy).
    body = _get(f"/api/v1/projects/{PROJECT}")
    assert body["results"]["dbtConnection"]["target"] == "lightdash"
    assert _lightdash_target_user() == "svc_analytics"
