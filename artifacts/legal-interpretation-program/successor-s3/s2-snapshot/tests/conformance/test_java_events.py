from copy import deepcopy
import subprocess
from legalmath.canonical import canonical, loads, digest
from legalmath.java.manifest import build_candidate
from legalmath.events.replay import replay, consent_fact
from tests.conformance.event_support import event_cases


def test_full_event_results_and_composition(case, root, tmp_path):
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    build = build_candidate(case["bundle"], tmp_path, jdk)
    requests = [c["request"] for c in event_cases()]
    future = deepcopy(requests[1]); future["completeness"]["complete_through"] = "2026-09-05T00:00:00.000000Z";requests.append(future)
    wrong = deepcopy(requests[0]);wrong["events"][0]["subject"] = "wrong";requests.append(wrong)
    order = deepcopy(requests[0]);order["header"]["ordering_authority"] = None;order["events"][1]["occurred_at"] = order["events"][0]["occurred_at"];requests.append(order)
    raw = subprocess.check_output([str(jdk / "bin/java"), "-cp", build["jar"], "hk.legalmath.Runner"], input=b"\n".join(canonical({"event_request": r}) for r in requests) + b"\n")
    results = [loads(line) for line in raw.splitlines()]
    for request, java in zip(requests, results):
        python = replay(request)
        assert {k:v for k,v in java.items() if k not in ("engine_version", "result_hash")} == {k:v for k,v in python.items() if k not in ("engine_version", "result_hash")}
        assert java["result_hash"] == digest({"request": request, "result": {k:v for k,v in java.items() if k != "result_hash"}})
        assert java["engine_version"] != python["engine_version"]
    assert consent_fact(results[0], requests[0]["header"]["inception"], None)["value"] is False
    assert consent_fact(results[1], requests[1]["header"]["inception"], None)["value"] is True
