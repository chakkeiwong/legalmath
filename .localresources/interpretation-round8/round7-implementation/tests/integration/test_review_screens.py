from fastapi.testclient import TestClient
from legalmath.api.app import create_app
from legalmath.sources.intake import import_spi
from legalmath.web.views import hkd
from tests.helpers import IDENTITIES
from tests.integration.test_api import headers


def test_four_views_escape_text_and_show_cents(root, tmp_path, case):
    app = create_app(tmp_path, IDENTITIES)
    import_spi(app.state.db, root)
    case["bundle"]["interpretations"][0]["statement"] = '<script>alert("injection")</script>'
    with TestClient(app) as c:
        bh = c.post("/v1/bundles", json=case["bundle"], headers=headers()).json()["bundle_hash"]
        text = c.get("/review/" + bh).text
        assert "&lt;script&gt;" in text and "<script>alert" not in text
        assert "HK$40,000,000.00" in text and "Original passages" in text
        assert "/original#page=" in text and "Scope and condition flow" in text
        request = {"bundle_hash": bh, **{k: case[k] for k in ("snapshot", "rule_id", "valid_at", "known_at")}}
        result = c.post("/v1/evaluations", json=request, headers=headers("eval")).json()
        page = c.get("/decisions/" + result["result_hash"])
        assert page.status_code == 200 and "Exact retained request and result" in page.text
        assert c.get(f"/amendments/{bh}/{bh}").status_code == 200
        assert c.get("/").status_code == 200
        assert c.get("/sources/%2e%2e/original").status_code in (404, 422)
    assert hkd("-101") == "−HK$1.01"
