"""Finite current native evidence, with separate historical and current methods."""
from pathlib import Path
import gzip
import json
import re
import xml.etree.ElementTree as ET

from .execution_authority import digest, file_hash, read
from . import native_current_preparation as prep
from . import native_source_rehearsal as rehearsal
from .successor import process_ledger, sealed_runtime as runtime, service

VERSION = "native-current-files.v2"
SCRIPT = "scripts/prospectus_native_current.py"
TEST = "tests/prospectus/test_native_current_campaign.py"
TEST_RUNNER = "scripts/prospectus_native_current_tests.py"
ROUTES = tuple(prep.ROUTES)
CALL_LIMIT = 11
STORAGE_CAP = 512 * 1024 * 1024
HISTORICAL_FLOOR = 50
STAGES = ("prepare", "controls", *("route-" + r for r in ROUTES), "probe", "finalize")
SENTINEL = "/prospectus-probe-sentinel"
require = prep.require


def methods(root):
    names = set(rehearsal.methods(root)) | {SCRIPT, TEST, TEST_RUNNER}
    return {p: file_hash(prep.local(root, p)) for p in sorted(names)}


def check_methods(root, folder):
    current = methods(root)
    require(current == read(folder / "methods.json"), "Current live methods changed after freeze")
    from hashlib import sha256
    with gzip.open(folder / "method-snapshots.json.gz", "rt") as stream:
        stored = json.load(stream)
    require(set(stored) == set(current) and all(sha256(stored[p].encode()).hexdigest() == h
        for p, h in current.items()), "Current live snapshot differs")
    return current


def grant(task):
    expected = {"version": VERSION, "routes": list(ROUTES), "maximum_reservations": CALL_LIMIT,
        "historical_lower_bound": HISTORICAL_FLOOR, "repair_reservations": 0,
        "storage_unique_bytes": STORAGE_CAP, "stage_timeout_seconds": 120,
        "canary": "2009-fresh", "source_calls_per_route": 2, "boundary_calls": 1,
        "network": False, "gpu": False, "installations": False}
    require(task.get("native_campaign") == expected and task.get("preparation_only") is False
        and task.get("native_call_allowance") == CALL_LIMIT and task.get("validator") == VERSION,
        "Missing or altered explicit current live grant")
    return expected


def admission(authority, name):
    folder = prep.local(authority.root, name)
    prefix = str((authority.base / "attempts/native-binding").relative_to(authority.root))
    require(re.fullmatch(re.escape(prefix) + r"/attempt-[0-9]{3,}", name) is not None,
            "Current native attempt path required")
    admitted = read(folder / "admission.json")
    program, tasks, _ = authority.spec()
    task = tasks["native-binding"]
    events = [e for e in authority.events() if e.get("task") == "native-binding"]
    require(events and events[-1]["kind"] == "ADMIT" and events[-1]["attempt"] == name
        and file_hash(folder / "admission.json") == events[-1]["admission_sha256"], "Current unclosed admission required")
    require(admitted.get("attempt") == name and admitted.get("task") == task["id"]
        and admitted["program_sha256"] == digest(program) and admitted["task_sha256"] == digest(task)
        and admitted["task_spec"] == task and admitted["binding"] == authority.binding(task),
        "Current native admission bindings changed")
    grant(task)
    require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed live attempt refused")
    prep.files(folder)
    return folder, admitted, task


def storage(folder):
    unique, logical = {}, 0
    for path in folder.rglob("*"):
        require(not path.is_symlink(), "Symlink live evidence refused")
        if path.is_file():
            info = path.stat()
            logical += info.st_size
            unique[(info.st_dev, info.st_ino)] = info.st_size
    return {"encoded_unique_bytes": sum(unique.values()), "logical_bytes": logical,
            "cap_unique_bytes": STORAGE_CAP}


def ledger(folder, expected=None):
    result = process_ledger.checked(folder / "process-ledger.json")
    require(result["limit"] == CALL_LIMIT and result["historical_lower_bound"] == HISTORICAL_FLOOR,
            "Live reservation limit or historical floor changed")
    if expected is not None:
        require(len(result["reservations"]) == expected and
            all(r["state"] == "STARTED" for r in result["reservations"]), "Unexpected or failed native reservation")
    return result


def tests(folder, current):
    target = folder / "validation"
    result = read(target / "result.json")
    require(result["status"] == "PASS" and result["exit_code"] == 0 and result["wall_seconds"] <= 120
        and read(target / "methods.json") == current
        and result["tests_sha256"] == file_hash(target / "tests.xml"), "Live tests missing, stale or failed")
    tree = ET.parse(target / "tests.xml")
    suites = list(tree.getroot().iter("testsuite"))
    names = {r.get("name", "").split("[")[0] for r in tree.getroot().iter("testcase")}
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("failures", "errors", "skipped")),
            "Live focused tests failed or skipped")
    require({"test_live_grant_refuses_missing_or_altered_limits", "test_live_admission_refuses_before_writes",
        "test_live_failure_is_sealed_and_recordable", "test_live_stage_requires_canary_and_refuses_duplicate",
        "test_live_ledger_rejects_unaccounted_reservation", "test_current_validator_rejects_missing_matrix",
        "test_live_default_captures_actual_failure", "test_full_source_comparator_does_not_hide_changes",
        "test_current_acceptance_refuses_forged_evidence"} <= names, "Live refusal tests incomplete")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "tests_sha256": file_hash(target / "tests.xml")}


def check_source(root, folder, route):
    actual = folder / "routes" / route
    baseline = prep.local(root, prep.ROUTES[route])
    request, old_p1, old_raw = rehearsal.source_request(root, route)
    raw = prep.historical.unpack(actual / "raw-P1.json.gz")
    service.verify(raw, "P1", request["bundle"], {"request": service.digest(request)})
    require(raw["payload"]["request"] == request, "Actual original source request changed")
    # Exact historical manifests are preserved in new owned snapshots. No
    # receipt normalization is needed; any runtime drift must be investigated.
    exact_source(raw, old_raw if old_raw is not None else old_p1)
    rebound = prep.historical.rebind(raw, old_p1["payload"]["request"]) if old_raw is not None else raw
    p1 = prep.historical.unpack(actual / "P1.json.gz")
    require(p1 == rebound == old_p1, "Complete consumed source or correction rebind differs")
    for index in (0, 1):
        new, old = actual / "native" / str(index), baseline / "native" / str(index)
        for name in ("stdin", "stdout", "stderr"):
            require(file_hash(new / name) == file_hash(old / name), "Complete native stream differs")
        if route != "2009-default":
            manifest = read(folder / "snapshots" / route[:4] / "manifest.json")
            receipt, _ = prep.historical.receipt(new, manifest)
            require(receipt == read(old / "receipt.json"), "Current receipt differs from protected runtime")
        else:
            require(read(new / "command.json") == read(old / "command.json")
                and read(new / "result.json")["returncode"] == 0, "Actual default reference dispatch differs")
    return p1


def exact_source(actual, expected):
    require(actual == expected, "Complete raw source differs")


def check_route(root, folder, route, *, consume=False):
    actual = folder / "routes" / route
    values, answer = prep.historical.products(actual)
    old_values, old_answer = prep.historical.products(prep.local(root, prep.ROUTES[route]))
    require(values == old_values and answer == old_answer, "Complete live products/answer differ")
    require(check_source(root, folder, route) == values["P1"], "Current source binding differs")
    if consume:
        require(service.consume(values, root, mode="frozen", include_artifacts=True) == answer,
                "Current answer was not consumed from its own products")
    return {"route": route, "products": {p: v["sha256"] for p, v in values.items()},
        "answer_sha256": answer["report_sha256"], "complete_equality": True}


def evidence(root, folder, task):
    root, folder = Path(root).resolve(), Path(folder).resolve()
    grant(task)
    current = check_methods(root, folder)
    tested = tests(folder, current)
    for name in STAGES[:-1]:
        path = folder / "stages" / name / "result.json"
        require(path.is_file(), "Missing current native stage: " + name)
        result = read(path)
        require(result["status"] == "PASS" and 0 <= result["wall_seconds"] <= 120,
                "Current native stage failed or timed out: " + name)
    snapshots = {year: prep.historical.snapshot(folder / "snapshots" / year) for year in ("2009", "2010")}
    for year, attempt in (("2009", "attempt-008"), ("2010", "attempt-006")):
        old = prep.local(root, prep.BASE + "/attempts/native-binding/" + attempt)
        prep.historical.verify_files(old / "method-final", read(old / "frozen-methods.json"))
        require(snapshots[year] == read(old / "snapshot/manifest.json"), "Historical source runtime changed")
    routes = [check_route(root, folder, route, consume=True) for route in ROUTES]
    controls = prep.historical.check_controls(folder)
    probe = prep.historical.check_probe(folder, snapshots["2009"])
    rows = ledger(folder, CALL_LIMIT)["reservations"]
    require([r["argv"][0] == "/usr/bin/bwrap" for r in rows] ==
        [True, True, False, False, True, True, True, True, True, True, True], "Actual native call sequence differs")
    ranges = [read(folder / "stages" / ("route-" + route) / "result.json")["details"]["reservations"] for route in ROUTES]
    require(ranges == [[i, i+2] for i in range(0, 10, 2)], "Route reservations omitted or reassigned")
    require(storage(folder)["encoded_unique_bytes"] < STORAGE_CAP, "Native evidence storage limit exceeded")
    return {"version": VERSION, "scope": "FINITE_CURRENT_NATIVE_ENGINEERING_ONLY", "routes": routes,
        "tests": tested, "prelaunch_refusals": controls, "probe_receipt_sha256": probe,
        "native_reservations": CALL_LIMIT, "historical_lower_bound": HISTORICAL_FLOOR,
        "cumulative_lower_bound": HISTORICAL_FLOOR + CALL_LIMIT,
        "methods_sha256": digest(current), "independent_legal_acceptance": False,
        "portability_established": False, "universal_dependency_closure": False, "whole_program_complete": False}


def validate_submission(root, folder, task):
    expected = evidence(root, folder, task)
    require(read(folder / "verification.json") == expected, "Current native verification differs from actual evidence")
    result = read(folder / "result.json")
    require(result.get("status") == "PASS" and result.get("task") == "native-binding"
        and result.get("scope") == "FINITE_ENGINEERING_ONLY" and result.get("whole_program_complete") is False,
        "Current native submission scope differs")
    return True
