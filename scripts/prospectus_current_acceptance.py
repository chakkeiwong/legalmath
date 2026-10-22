"""Strict retained native/installed acceptance with an exact registry-only delta."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus import native_current_acceptance as native, native_profile as product
from legalmath.prospectus import native_installed_acceptance as old_installed
from legalmath.prospectus.successor import process_ledger, service
from scripts import prospectus_installed_current as preparation
from scripts import prospectus_installed_live as live
from scripts import prospectus_installed_consumer as helper
from scripts.prospectus_native_campaign import bounded_stage

BASE = "docs/implementation/prospectus-execution-authority"
REGISTRY = "src/legalmath/prospectus/execution_acceptance.py"
SCRIPT = "scripts/prospectus_current_acceptance.py"
RUNNER = "scripts/prospectus_current_acceptance_runner.py"
TEST = "tests/prospectus/test_current_retained_acceptance.py"
NATIVE = "native-retained-current.v3"
INSTALLED = "native-installed-current.v2"
PATCH_ATTEMPT = BASE + "/attempts/native-confinement/attempt-008"
require = preparation.require
common = preparation.prep.historical


def registry_candidate(before):
    mapping = "              'native-installed-profile.v1': 'native-confinement'}"
    dispatch = "    if name == 'native-current-files.v2':\n"
    require(before.count(mapping) == before.count(dispatch) == 1, "Unexpected legacy registry structure")
    return before.replace(mapping, "              'native-installed-profile.v1': 'native-confinement',\n"
        "              'native-retained-current.v3': 'native-binding',\n"
        "              'native-installed-current.v2': 'native-confinement'}").replace(dispatch,
        "    if name in {'native-retained-current.v3', 'native-installed-current.v2'}:\n"
        "        from scripts.prospectus_current_acceptance import validate_submission\n"
        "        return validate_submission(root, attempt, task)\n" + dispatch)


def registration_only(before, after):
    return after == before or after == registry_candidate(before)


def retained(root, name, *, kind=None):
    authority = Authority(root)
    folder = preparation.prep.local(root, name)
    events = [e for e in authority.events() if e.get("attempt") == name and e["kind"] in {"ACCEPT", "RECORD", "REJECT"}]
    require(events and (kind is None or events[-1]["kind"] == kind) and authority.retained_evidence_valid(events[-1]), "Retained attempt evidence is missing, changed or has wrong disposition")
    return folder, events[-1]


def method_bridge(root, frozen, snapshots, current, *, hex_encoded):
    require(set(frozen) == set(current) == set(snapshots), "Current/frozen method inventory differs")
    changes = []
    for name, old_hash in frozen.items():
        data = bytes.fromhex(snapshots[name]) if hex_encoded else snapshots[name].encode()
        require(hashlib.sha256(data).hexdigest() == old_hash, "Retained method snapshot hash differs")
        if current[name] != old_hash:
            require(name == REGISTRY and registration_only(data.decode(), (root / name).read_text()), "Unreviewed current method change: " + name)
            changes.append(name)
    return changes


def bridge(root, folder, current, *, hex_encoded=True):
    return method_bridge(root, read(folder / "methods.json"), helper.read(folder / "method-snapshots.json.gz"), current, hex_encoded=hex_encoded)


def methods(root):
    value = dict(live.methods(root))
    value.update({p: file_hash(root / p) for p in (SCRIPT, RUNNER, TEST)})
    return value


def checked_current_tests(root, attempt):
    runs = sorted((attempt / "validation").glob("run-*/result.json"))
    require(1 <= len(runs) <= 2, "Current acceptance test starts differ")
    folder = runs[-1].parent; value = read(runs[-1])
    require(value["status"] == "PASS" and value["exit_code"] == 0 and value["wall_seconds"] <= 120
        and read(folder / "methods.json") == methods(root) and value["tests_sha256"] == file_hash(folder / "tests.xml"), "Current acceptance test methods or result differ")
    suites = list(ET.parse(folder / "tests.xml").getroot().iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Current acceptance tests failed/skipped")
    names = {n.get("name", "").split("[")[0] for n in ET.parse(folder / "tests.xml").getroot().iter("testcase")}
    require({"test_registry_only_delta_rejects_unrelated_edits", "test_bridge_refuses_product_change_or_forged_snapshot",
        "test_new_registry_dispatches_real_validator", "test_missing_retained_evidence_cannot_be_pass",
        "test_reconstructed_ocr_and_product_hash_regressions_remain_active", "test_retained_stage_hashes_refuse_rehashed_missing_outputs"} <= names,
        "Required acceptance refusal tests missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "sha256": value["tests_sha256"]}


def checked_stages(folder, stages):
    for name in stages:
        value = read(folder / "stages" / name / "result.json")
        require(value["status"] == "PASS" and 0 <= value["wall_seconds"] <= 120, "Failed or missing retained stage: " + name)


def native_evidence(root):
    folder, event = retained(root, BASE + "/attempts/native-binding/attempt-017", kind="ACCEPT")
    changes = bridge(root, folder, native.methods(root), hex_encoded=False)
    native.grant(read(folder / "admission.json")["task_spec"])
    tested = native.tests(folder, read(folder / "methods.json"))
    checked_stages(folder, native.STAGES)
    snapshots = {year: common.snapshot(folder / "snapshots" / year) for year in ("2009", "2010")}
    for year, old in (("2009", "008"), ("2010", "006")):
        historical = root / BASE / "attempts/native-binding" / ("attempt-" + old)
        common.verify_files(historical / "method-final", read(historical / "frozen-methods.json"))
        require(snapshots[year] == read(historical / "snapshot/manifest.json"), "Protected native snapshot changed")
    routes = [native.check_route(root, folder, route, consume=True) for route in native.ROUTES]
    controls = common.check_controls(folder); probe = common.check_probe(folder, snapshots["2009"])
    rows = native.ledger(folder, 11)["reservations"]
    require([r["argv"][0] == "/usr/bin/bwrap" for r in rows] == [True, True, False, False, True, True, True, True, True, True, True], "Native command sequence differs")
    require([read(folder / "stages" / ("route-" + route) / "result.json")["details"]["reservations"] for route in native.ROUTES]
        == [[i, i+2] for i in range(0, 10, 2)], "Native route reservation ranges differ")
    require(native.storage(folder)["encoded_unique_bytes"] < native.STORAGE_CAP, "Native evidence bound exceeded")
    return {"version": NATIVE, "retained_event": event["seq"], "retained_outputs_sha256": event["outputs_sha256"],
        "registry_only_changes": changes, "routes": routes, "historical_tests": tested,
        "prelaunch_refusals": controls, "probe_receipt_sha256": probe, "new_native_calls": 0,
        "prior_native_reservations": 11, "native_binding_lineage_lower_bound": 61,
        "independent_legal_acceptance": False, "portability_established": False, "whole_program_complete": False}


def prepared_current(root):
    folder, event = retained(root, BASE + "/attempts/native-confinement/attempt-004", kind="RECORD")
    changes = bridge(root, folder, preparation.methods(root))
    work = preparation.workspace(root, folder)
    package = work / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(folder / "source-package.json")
    require(helper.package_files(package) == expected, "Installed prepared package bytes changed")
    current = helper.package_files(root / "src/legalmath")
    require(set(current) == set(expected), "Current installed package inventory differs")
    for name, hashed in expected.items():
        if current[name] != hashed:
            require(name == "prospectus/execution_acceptance.py" and registration_only((package / name).read_text(), (root / "src/legalmath" / name).read_text()), "Installed product differs from current source: " + name)
    require(preparation.tree(work / "environment", dependencies=True) == read(folder / "dependencies.json"), "Prepared dependency bytes differ")
    wheel = read(folder / "built-wheel.json"); path = folder / wheel["file"]
    require(file_hash(path) == wheel["sha256"], "Prepared wheel changed")
    with zipfile.ZipFile(path) as archive:
        actual = {n.removeprefix("legalmath/"): hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist() if n.startswith("legalmath/") and not n.endswith("/")}
        require(actual == expected, "Prepared wheel content differs")
    require(read(folder / "installed-methods.json") == product.methods(), "Current installed product methods differ")
    profile, manifest = product.load_profile(folder / "profile", read(folder / "profile/capture-result.json")["profile_sha256"])
    require(manifest == read(folder / "expected-snapshot.json"), "Actual installed profile differs")
    checked_stages(folder, preparation.STAGES)
    product.checked_stage(folder / "profile", "capture"); product.checked_stage(folder / "profile-check", "check")
    require(read(folder / "native-ledger.json") == {"version": preparation.VERSION, "allowance": 0, "reservations": [], "historical_installed_starts": 4}, "Preparation had unexpected native reservations")
    outer = process_ledger.checked(folder / "outer-ledger.json")
    require(outer["limit"] == 10 and outer["historical_lower_bound"] == 18 and len(outer["reservations"]) == 10, "Preparation outer budget differs")
    command_evidence(folder, work, preparation.COMMANDS, outer["reservations"])
    controls = read(folder / "commands/controls/installed-result.json")
    expected_controls = {"wrong-pin", "blob-changed", "blob-missing", "method-changed", "runtime-changed", "manifest-changed", "changed-source", "duplicate-stage", "rehashed-answer", "extra-subprocess"}
    require(controls["native_processes"] == 0 and controls["blocked_native_attempts"] == 1
        and len(controls["details"]["cases"]) == len(expected_controls)
        and {r["case"] for r in controls["details"]["cases"]} == expected_controls
        and all(r["refused"] for r in controls["details"]["cases"]), "Actual preparation controls incomplete")
    for route in preparation.ROUTES:
        base = root / read(folder / "baseline.json")["attempt"] / "routes" / route
        actual = helper.read(folder / "replays" / route / "actual.json.gz")
        helper.compare_objects(actual, {n: helper.read(base / (n + ".json.gz")) for n in ("P1", "P2", "P3", "P4", "P5", "answer")})
    require(preparation.bounded_storage(folder, work)["evidence_unique_bytes"] < preparation.GRANT["evidence_bytes"], "Preparation bound exceeded")
    return folder, work, profile, manifest, {"event": event["seq"], "registry_only_changes": changes, "installed_package_files": len(expected), "wheel_sha256": wheel["sha256"], "profile_sha256": product.digest(profile), "installed_replays": 5, "profile_controls": 10}


def command_evidence(folder, work, names, reservations):
    require(len(reservations) == len(names) and {p.name for p in (folder / "commands").iterdir()} == set(names), "Actual command denominator differs")
    package = work / "environment/lib/python3.11/site-packages/legalmath"
    for name, row in zip(names, reservations):
        target = folder / "commands" / name
        command = read(target / "command.json"); result = read(target / "result.json")
        require(row["state"] == "STARTED" and row["argv"] == command["argv"] and result["returncode"] == 0
            and result["error"] is None and result["wall_seconds"] <= 110, "Actual installed command failed or differs")
        require(command["argv"][:3] == [str(work / "environment/bin/python"), "-I", "-B"]
            and command["environment"]["CUDA_VISIBLE_DEVICES"] == "-1" and command["environment"]["PIP_NO_INDEX"] == "1", "Installed command environment differs")
        if name in ("build", "install"): continue
        proof = read(target / "installed-proof.json")
        require(proof["isolated"] == 1 and proof["prefix"] == str(work / "environment")
            and proof["python"] == str(work / "environment/bin/python") and bool(proof["modules"]), "Installed import identity differs")
        require(all(not str(p).endswith("/src") for p in proof["sys_path"]), "Editable checkout import path")
        for value in proof["modules"].values():
            path = Path(value["path"])
            require(path.is_relative_to(package) and file_hash(path) == value["sha256"], "Loaded installed module differs")
        require(read(target / "installed-result.json")["status"] == "PASS", "Installed inner command failed")


def installed_source(root, folder, mode, prepared):
    prior, work, profile, manifest, _ = prepared
    base = root / read(prior / "baseline.json")["attempt"] / "routes" / ("2010-" + mode)
    job = folder / mode
    actual = helper.read(job / "P1.json.gz"); expected = helper.read(base / "P1.json.gz")
    request = read(prior / (mode + "-request.json"))
    require(request == expected["payload"]["request"], "Installed comparator request differs")
    execution = read(job / "execution.json")
    old_installed.installed_proof(execution, work / "environment", product.methods())
    live.product_bindings(actual, request, execution, profile, prior / "profile")
    required = old_installed.installed_requirements(product.preflight(request, profile, manifest), manifest, work / "environment")
    require(execution["required_files"] == required, "Actual installed preflight differs")
    rows = []
    for i in (0, 1):
        row, streams = common.receipt(job / "native" / str(i), manifest)
        expected_argv = read(base / "native" / str(i) / "receipt.json")["argv"]
        if i: expected_argv[1] = str(work / "environment/lib/python3.11/site-packages/legalmath/prospectus/successor/ocr_worker.py")
        require(row["argv"] == expected_argv and row["limits"]["max_stream_bytes"] == (20 if i else 64) * 1024 * 1024, "Installed native dispatch/cap differs")
        require(all(value == (base / "native" / str(i) / name).read_bytes() for name, value in zip(("stdin", "stdout", "stderr"), streams)), "Actual complete installed native stream differs")
        rows.append(row)
    require(execution["native_receipts"] == rows, "Installed source receipt inventory differs")
    graph, old = actual["payload"]["graph"], expected["payload"]["graph"]
    hashes = None
    if mode == "fresh":
        hashes = (live.checked_fresh_ocr(graph["documents"][0], (job / "native/1/stdout").read_bytes(), rows[1], manifest),
            live.checked_fresh_ocr(old["documents"][0], (base / "native/1/stdout").read_bytes(), read(base / "native/1/receipt.json"), read(base.parents[1] / "snapshots/2010/manifest.json")))
    live.compare_source_graph(graph, old, mode, rows, hashes)
    for stage in ("source", "construct", "finish", "verify"): product.checked_stage(job, stage)
    values, answer = common.products(job)
    common.compare_products(common.products(base), (values, answer))
    common.consumer(root, values, answer)
    require(read(job / "verification.json") == {"version": product.VERSION, "profile_sha256": product.digest(profile),
        "answer_sha256": answer["report_sha256"], "consumed_products": answer["consumed_products"], "native_calls": 2,
        "native_reuse_allowed": False, "independent_legal_acceptance": False}, "Actual installed verification differs")
    return {"mode": mode, "complete_native_streams_equal": True, "complete_source_and_semantics_equal": True,
        "answer_sha256": answer["report_sha256"], "receipts": [r["receipt_sha256"] for r in rows]}


def installed_evidence(root):
    folder, event = retained(root, BASE + "/attempts/native-confinement/attempt-007", kind="RECORD")
    changes = bridge(root, folder, live.methods(root))
    context = prepared_current(root); prior, work, _, _, prep_result = context
    checked_stages(folder, live.STAGES)
    original, failure = retained(root, BASE + "/attempts/native-confinement/attempt-005", kind="REJECT")
    sixth, _ = retained(root, BASE + "/attempts/native-confinement/attempt-006", kind="REJECT")
    require(read(original / "commands/source-fresh/installed-result.json")["status"] == "PASS"
        and read(original / "result.json")["status"] == read(sixth / "result.json")["status"] == "FAIL", "Failed attempts or successful original source lost")
    recovery = read(folder / "source-recovery.json")
    require(recovery["attempt"] == str(original.relative_to(root)) and recovery["outputs_sha256"] == failure["outputs_sha256"]
        and recovery["fresh_files"] == preparation.prep.files(original / "fresh"), "Recovered source map differs")
    common.verify_files(folder / "fresh", recovery["fresh_files"])
    expected_counts = [("001", 5, 0), ("002", 13, 4), ("004", 10, 0), ("005", 1, 2), ("006", 0, 0), ("007", 8, 2)]
    totals = {"outer": 0, "native": 0}; ledgers = {}
    for number, outer_n, native_n in expected_counts:
        attempt, _ = retained(root, BASE + "/attempts/native-confinement/attempt-" + number)
        outer = process_ledger.checked(attempt / ("command-ledger.json" if number in ("001", "002") else "outer-ledger.json"))
        if number == "004": native_rows = []
        else: native_rows = process_ledger.checked(attempt / "native-ledger.json")["reservations"]
        require(len(outer["reservations"]) == outer_n and len(native_rows) == native_n and
            all(r["state"] == "STARTED" for r in outer["reservations"] + native_rows), "Cumulative installed campaign accounting differs")
        totals["outer"] += outer_n; totals["native"] += native_n
        ledgers[number] = {"outer": outer, "native": native_rows}
    require(ledgers["007"]["outer"]["limit"] == 8 and ledgers["007"]["outer"]["historical_lower_bound"] == 29,
            "Final remaining outer allowance differs")
    native_ledger = process_ledger.checked(folder / "native-ledger.json")
    require(native_ledger["limit"] == 2 and native_ledger["historical_lower_bound"] == 6, "Final remaining native allowance differs")
    command_evidence(original, work, ("source-fresh",), ledgers["005"]["outer"]["reservations"])
    command_evidence(folder, work, live.COMMANDS, ledgers["007"]["outer"]["reservations"])
    controls = read(folder / "commands/controls/installed-result.json")
    require(controls["blocked_attempts"] == 1 and len(controls["details"]["cases"]) == 4
        and {r["case"] for r in controls["details"]["cases"]} == {"failed-predecessor", "rehashed-forged-answer", "missing-stream", "forbidden-subprocess"}
        and all(r["refused"] for r in controls["details"]["cases"]), "Actual installed lifecycle controls differ")
    cases = [installed_source(root, folder, mode, context) for mode in ("fresh", "retained")]
    for number, mode in (("005", "fresh"), ("007", "retained")):
        for index, reservation in enumerate(ledgers[number]["native"]):
            receipt = read(folder / mode / "native" / str(index) / "receipt.json")
            argv = reservation["argv"]
            require(argv[0] == "/usr/bin/bwrap" and "--" in argv and argv[argv.index("--")+1:] == receipt["argv"], "Installed native ledger dispatch differs")
    return {"version": INSTALLED, "retained_event": event["seq"], "retained_outputs_sha256": event["outputs_sha256"],
        "registry_only_changes": changes, "preparation": prep_result, "cases": cases, "lifecycle_controls": 4,
        "installed_lineage": totals, "new_native_calls": 0, "independent_legal_acceptance": False,
        "portability_established": False, "whole_program_complete": False}


def validate_submission(root, attempt, task):
    if "current_runtime_matrix" in task:
        from scripts.prospectus_runtime_matrix import validate_submission as validate_matrix
        return validate_matrix(root, attempt, task)
    if "product_delta_acceptance" in task:
        if task.get("id") == "native-confinement":
            from scripts.prospectus_installed_profile_refresh import validate_submission as validate_installed
            return validate_installed(root, attempt, task)
        from scripts.prospectus_native_product_delta import validate_submission as validate_delta
        return validate_delta(root, attempt, task)
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    require(task.get("native_call_allowance") == 0 and task.get("retained_acceptance_only") is True, "Explicit zero-call acceptance required")
    check = {NATIVE: ("native-binding", native_evidence), INSTALLED: ("native-confinement", installed_evidence)}
    require(task.get("validator") in check and check[task["validator"]][0] == task["id"], "Wrong retained acceptance task")
    expected = check[task["validator"]][1]
    with bounded_stage(), live.offline():
        tests = checked_current_tests(root, attempt)
        value = expected(root)
    require(read(attempt / "verification.json") == {**value, "current_tests": tests}, "Acceptance differs from actual retained/current evidence")
    result = read(attempt / "result.json")
    require(result.get("status") == "PASS" and result.get("task") == task["id"] and result.get("scope") == "FINITE_ENGINEERING_ONLY"
        and result.get("whole_program_complete") is False, "Unsupported acceptance result")
    return True
