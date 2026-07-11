import urllib.request


BASE = "http://localhost:8080"


def test_lightdash_health():
    with urllib.request.urlopen(f"{BASE}/api/v1/health", timeout=10) as r:
        assert r.status == 200
