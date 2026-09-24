from copy import deepcopy
from fastapi.testclient import TestClient
from legalmath.api.app import create_app
from legalmath.sources.intake import import_spi
from tests.helpers import IDENTITIES


def headers(key="one", who="author"):
    return {"Authorization": "Bearer " + IDENTITIES[who]["token"], "Idempotency-Key": key}


def test_api_evaluation_identity_and_restart(root, tmp_path, case):
    directory = tmp_path / "service"
    app = create_app(directory, IDENTITIES, run_jobs=False)
    import_spi(app.state.db, root)
    with TestClient(app) as c:
        r = c.post("/v1/bundles", json=case["bundle"], headers=headers())
        assert r.status_code == 201, r.text
        bh = r.json()["bundle_hash"]
        request = {k: case[k] for k in ("snapshot", "rule_id", "valid_at", "known_at")}
        request["bundle_hash"] = bh
        r = c.post("/v1/evaluations", json=request, headers=headers("eval"))
        assert r.status_code == 200 and r.json()["status"] == "TRUE", r.text
        original = r.json()
        assert c.get("/v1/evaluations/" + original["result_hash"], headers=headers()).json()["result"] == original
        bad = deepcopy(request);bad["snapshot"]["facts"]["portfolio"]["type"] = "integer"
        invalid = c.post("/v1/evaluations", json=bad, headers=headers("semantic-error"))
        assert invalid.status_code == 200 and invalid.json()["status"] == "ERROR"
        assert c.post("/v1/evaluations", json={**request, "mode": "production"}, headers=headers("prod")).status_code == 409
        assert c.post("/v1/bundles", content='{"duplicate":1,"duplicate":2}', headers={**headers("bad-json"), "Content-Type": "application/json"}).status_code == 422
        assert c.post("/v1/bundles/" + bh + "/review", json={"decision": "approve_meaning", "expected_revision": 1, "role": "meaning"}, headers=headers("spoof")).status_code == 422
    with TestClient(create_app(directory, IDENTITIES, run_jobs=False)) as c:
        assert c.post("/v1/evaluations", json=request, headers=headers("eval")).json() == original
        changed = {**request, "mode": "replay"}
        assert c.post("/v1/evaluations", json=changed, headers=headers("eval")).status_code == 409


def test_stream_api_and_request_boundaries(root, tmp_path):
    from tests.conformance.event_support import event_cases
    req = event_cases()[0]["request"]
    with TestClient(create_app(tmp_path, IDENTITIES, run_jobs=False)) as c:
        s = c.post("/v1/event-streams", json=req["header"], headers=headers("stream"))
        assert s.status_code == 201, s.text
        stream = req["header"]["stream_id"]
        for i, event in enumerate(req["events"]):
            r = c.post(f"/v1/event-streams/{stream}/events", json={"event": event, "expected_revision": i + 1}, headers=headers("event" + str(i)))
            assert r.status_code == 201, r.text
        r = c.post(f"/v1/event-streams/{stream}/replay", json={k: req[k] for k in ("valid_at", "known_at", "completeness")}, headers=headers("replay"))
        assert r.json()["state"] == "WITHDRAWN", r.text
        assert c.get("/v1/jobs/missing", headers=headers()).status_code == 404
        assert c.post("/v1/event-streams", json=req["header"], headers={"Authorization": "Bearer invalid", "Idempotency-Key": "x"}).status_code == 403


def test_uploaded_text_cannot_claim_official_authority(tmp_path):
    import base64
    app = create_app(tmp_path, IDENTITIES, run_jobs=False)
    with TestClient(app) as c:
        request = {"source_id": "uploaded", "official_url": "https://apps.sfc.hk/forged", "retrieved_at": "2026-09-01T00:00:00.000000Z", "media_type": "text/plain", "content_base64": base64.b64encode(b"invented text").decode()}
        result = c.post("/v1/sources/import", json=request, headers=headers()).json()
        with app.state.db.connect() as con:
            assert app.state.db.get(con, result["source_hash"])["authority"] == "UPLOADED_UNVERIFIED"
        assert c.post("/v1/drafts", json={"source_inventory": {}, "responses": []}, headers=headers("draft")).status_code == 422


def test_api_console_and_embedded_domain_contracts(tmp_path):
    with TestClient(create_app(tmp_path, IDENTITIES, run_jobs=False)) as c:
        assert 'src="/static/api.js"' in c.get("/docs").text
        assert c.get("/static/api.js").status_code == 200
        spec = c.get("/openapi.json").json()
        schemas = spec["components"]["schemas"]
        assert schemas["Evaluation"]["properties"]["snapshot"]["$ref"].endswith("/fact-snapshot")
        assert spec["paths"]["/v1/bundles"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/rule-bundle")
        def inspect(value):
            if isinstance(value, list):
                for child in value: inspect(child)
            elif isinstance(value, dict):
                if "$ref" in value:
                    assert value["$ref"].startswith("#/components/schemas/")
                    assert value["$ref"].split("/")[-1] in schemas
                for child in value.values(): inspect(child)
        inspect(spec)
