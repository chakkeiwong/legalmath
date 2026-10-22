"""Strict compatibility of retained native evidence with two reviewed product edits."""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from legalmath.prospectus.execution_authority import Authority, file_hash, read
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from scripts import prospectus_current_acceptance as prior
from scripts.prospectus_report_integrity import read as unpack

BASE = "docs/implementation/prospectus-execution-authority"
REVIEW = BASE + "/reviews/native-product-152"
NATIVE = BASE + "/attempts/native-binding/attempt-017"
INSTALLED = BASE + "/attempts/source-bes-dep-09/attempt-005"
VERSION = "native-product-delta.v1"
SCRIPT = "scripts/prospectus_native_product_delta.py"
RUNNER = "scripts/prospectus_native_product_delta_runner.py"
TEST = "tests/prospectus/test_native_product_delta.py"
SERVICE = "src/legalmath/prospectus/successor/service.py"
CELLS = "src/legalmath/prospectus/successor/statement_cells.py"
ROUTES = tuple(prior.native.ROUTES)
STAGES = ("tests", "historical-evidence", *("replay-" + r for r in ROUTES), "adverse", "seal")
ATTACKS = ("missing-selection", "false-page", "unsupplied-selection")
SELECTOR = {"version": VERSION, "review": REVIEW, "stages": list(STAGES),
            "new_native_calls": 0, "new_subprocess_calls": 0, "stage_seconds": 115,
            "execution_seconds": 720, "validation_seconds": 195, "evidence_bytes": 32 * 1024**2}
require = prior.require


def methods(root):
    return {**prior.methods(root), **{p: file_hash(root / p) for p in (SCRIPT, RUNNER, TEST)}}


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected old acceptance dispatch")
    return before.replace(marker, marker +
        '    if "product_delta_acceptance" in task:\n'
        '        if task.get("id") == "native-confinement":\n'
        '            from scripts.prospectus_installed_profile_refresh import validate_submission as validate_installed\n'
        '            return validate_installed(root, attempt, task)\n'
        '        from scripts.prospectus_native_product_delta import validate_submission as validate_delta\n'
        '        return validate_delta(root, attempt, task)\n')


def exact_delta(before, after, approved):
    """Names alone do not authorize edits: both complete byte hashes are pinned."""
    require(set(before) == set(after), "Method inventory differs")
    changes = {p for p in before if before[p] != after[p]}
    require(changes == set(approved), "Unexpected changed method inventory")
    for path in changes:
        require(hashlib.sha256(before[path]).hexdigest() == approved[path]["before"] and
                hashlib.sha256(after[path]).hexdigest() == approved[path]["after"],
                "Unreviewed exact method bytes: " + path)
    return sorted(changes)


def service_shape(before, after):
    trees = [ast.parse(x) for x in (before, after)]
    changed = {"_bound_report_readings", "interpretation_product", "consume"}
    for tree in trees:
        tree.body = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name not in changed]
    require(ast.dump(trees[0], include_attributes=False) == ast.dump(trees[1], include_attributes=False),
            "Unreviewed service globals or other functions")


def cells_shape(before, after, expected_profile):
    trees = [ast.parse(x) for x in (before, after)]
    key = "bes-fy2010-statement-cells.v1"
    for index, tree in enumerate(trees):
        require(isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and
                isinstance(tree.body[0].value.value, str), "Cell module docstring missing")
        tree.body.pop(0)
        declarations = [n for n in tree.body if isinstance(n, ast.Assign) and
                        any(isinstance(t, ast.Name) and t.id == "PROFILES" for t in n.targets)]
        require(len(declarations) == 1 and isinstance(declarations[0].value, ast.Dict), "Profile declaration differs")
        profiles = declarations[0].value
        indices = [i for i, k in enumerate(profiles.keys) if isinstance(k, ast.Constant) and k.value == key]
        require(len(indices) == index, "FY profile addition differs")
        if index:
            i = indices[0]
            value = ast.literal_eval(profiles.values[i])
            value["pages"] = list(value["pages"])
            require(value == expected_profile, "Reviewed FY profile content differs")
            profiles.keys.pop(i)
            profiles.values.pop(i)
    require(ast.dump(trees[0], include_attributes=False) == ast.dump(trees[1], include_attributes=False),
            "Other profile or cell implementation changed")


def method_evidence(root):
    review = root / REVIEW
    spec = read(review / "approved-delta.json")
    folder = root / NATIVE
    frozen = read(folder / "methods.json")
    snapshots = unpack(folder / "method-snapshots.json.gz")
    current = prior.native.methods(root)
    require(set(frozen) == set(current) == set(snapshots), "Native method inventory differs")
    before = {n: snapshots[n].encode() for n in frozen}
    after = {n: (root / n).read_bytes() for n in current}
    require(all(hashlib.sha256(before[n]).hexdigest() == h for n, h in frozen.items()), "Forged historical method snapshot")
    changes = exact_delta(before, after, spec["changes"])
    require(changes == sorted((prior.REGISTRY, SERVICE, CELLS)), "Wrong approved product delta")
    require(prior.registration_only(before[prior.REGISTRY].decode(), after[prior.REGISTRY].decode()), "Registry delta differs")
    service_shape(before[SERVICE], after[SERVICE])
    cells_shape(before[CELLS], after[CELLS], spec["fy_profile"])
    baseline = (review / "acceptance-before.py").read_text()
    require(file_hash(review / "acceptance-before.py") == spec["dispatch_before_sha256"] and
            (root / prior.SCRIPT).read_text() == dispatch_candidate(baseline), "Unreviewed acceptance dispatch delta")
    installed = root / INSTALLED
    package = read(installed / "source-package.json")
    require(package == prior.helper.package_files(root / "src/legalmath"), "Current package differs from evaluated installed report repair")
    for name in (SERVICE, CELLS):
        require(file_hash(root / name) == package[name.removeprefix("src/legalmath/")], "Product method differs from installed result")
    return {"changes": {p: spec["changes"][p] for p in changes},
            "native_methods_sha256": digest(current), "dispatch_sha256": file_hash(root / prior.SCRIPT),
            "current_package_sha256": digest(package), "native_methods_otherwise_equal": True}


def historical_evidence(root):
    method = method_evidence(root)
    a = Authority(root)
    history = read(root / REVIEW / "history.json")
    events = a.events()
    require(history["events"] and all(e in events and a.retained_evidence_valid(e) for e in history["events"]),
            "Historical evidence changed")
    require(any(e["attempt"] == NATIVE and e["kind"] == "ACCEPT" for e in history["events"]) and
            any(e["attempt"] == INSTALLED and e["kind"] == "RECORD" for e in history["events"]),
            "Required actual native/installed evidence missing")
    folder = root / NATIVE
    prior.native.grant(read(folder / "admission.json")["task_spec"])
    tests = prior.native.tests(folder, read(folder / "methods.json"))
    prior.checked_stages(folder, prior.native.STAGES)
    snapshots = {year: prior.common.snapshot(folder / "snapshots" / year) for year in ("2009", "2010")}
    for year, number in (("2009", "008"), ("2010", "006")):
        old = root / BASE / "attempts/native-binding" / ("attempt-" + number)
        prior.common.verify_files(old / "method-final", read(old / "frozen-methods.json"))
        require(snapshots[year] == read(old / "snapshot/manifest.json"), "Protected native runtime changed")
    controls = prior.common.check_controls(folder)
    probe = prior.common.check_probe(folder, snapshots["2009"])
    rows = prior.native.ledger(folder, 11)["reservations"]
    require([r["argv"][0] == "/usr/bin/bwrap" for r in rows] ==
            [True, True, False, False, True, True, True, True, True, True, True], "Native reservation sequence differs")
    require([read(folder / "stages" / ("route-" + route) / "result.json")["details"]["reservations"] for route in ROUTES]
            == [[i, i + 2] for i in range(0, 10, 2)], "Original route reservation ranges differ")
    require(prior.native.storage(folder)["encoded_unique_bytes"] < prior.native.STORAGE_CAP, "Original native storage cap differs")
    return {"method_evidence": method, "historical_tests": tests, "prelaunch_controls": controls,
            "probe_receipt_sha256": probe, "prior_reservations": 11, "native_lineage_lower_bound": 61,
            "new_native_calls": 0, "scope": "Retained native execution; current downstream compatibility"}


def route(root, name, *, rebuild):
    require(name in ROUTES, "Unknown native route")
    folder = root / NATIVE
    evidence = prior.native.check_route(root, folder, name, consume=False)
    values, expected = prior.common.products(folder / "routes" / name)
    actual = values
    if rebuild:
        p1 = values["P1"]
        p2 = service.construction_product(p1, root)
        p3 = service.interpretation_product(p1, p2, values["P3"]["payload"].get("interpretation_input"))
        actual = {"P1": p1, "P2": p2, "P3": p3,
            "P4": service.law_product(p1, p3, values["P4"]["payload"].get("cases"), values["P4"]["payload"].get("law_input")),
            "P5": service.financial_product(p1, p2, p3, values["P5"]["payload"].get("cases"), values["P5"]["payload"].get("scenario_input"))}
    answer = service.consume(actual, root, mode="frozen", include_artifacts=True)
    require(actual == values and answer == expected, "Complete current native route products/answer differ: " + name)
    base = folder / "routes" / name
    return {"route": name, "evidence": evidence, "products": {p: v["sha256"] for p, v in actual.items()},
            "complete_answer_sha256": digest(answer), "complete_objects_equal": True,
            "references": {p: {"path": str((base / (p + ".json.gz")).relative_to(root)),
                               "file_sha256": file_hash(base / (p + ".json.gz"))} for p in (*values, "answer")}}


def changed(values, case):
    require(case in ATTACKS, "Unknown native source attack")
    bad = deepcopy(values)
    request = bad["P1"]["payload"]["request"]
    if case == "missing-selection":
        del bad["P2"]["payload"]["source_report_readings"]
    elif case == "false-page":
        reading = bad["P2"]["payload"]["source_report_readings"]["reports"][0]
        reading["pages"][0]["page"] += 1
        reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
    else:
        del request["source_report_readings"]
    bad["P1"] = service.seal("P1", request["bundle"], {"request": digest(request)}, bad["P1"]["payload"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")), ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        bad[phase] = service.seal(phase, request["bundle"], {p: bad[p]["sha256"] for p in parents}, bad[phase]["payload"])
    return bad


def adverse(root):
    values, _ = prior.common.products(root / NATIVE / "routes/2009-fresh")
    results = {}
    for case in ATTACKS:
        bad = changed(values, case)
        expected = "Report readings lack supplied source evidence" if case == "unsupplied-selection" else "Report readings differ from supplied source evidence"
        try:
            service.consume(bad, root, mode="frozen", include_artifacts=True)
        except ValueError as exc:
            require(str(exc) == expected, "Wrong native source refusal: " + str(exc))
            results[case] = {"rejected": True, "reason": str(exc), "products": {p: v["sha256"] for p, v in bad.items()}}
        else:
            raise ValueError("Altered native-source reading accepted")
    return results


def selector(task):
    require(task.get("product_delta_acceptance") == SELECTOR and task.get("id") == "native-binding" and
            task.get("validator") == prior.NATIVE and task.get("retained_acceptance_only") is True and
            task.get("native_call_allowance") == 0, "Unreviewed product-delta selector")


def check_tests(folder):
    result = read(folder / "tests/result.json")
    require(result["exit_code"] == 0 and result["status"] == "PASS" and
            result["junit_sha256"] == file_hash(folder / "tests/results.xml"), "Current delta tests missing or changed")
    root = ET.parse(folder / "tests/results.xml").getroot()
    suites = list(root.iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Delta tests failed/skipped")
    names = {x.get("name", "").split("[")[0] for x in root.iter("testcase")}
    require({"test_exact_delta_rejects_unreviewed_bytes", "test_fy_delta_rejects_extra_profile_or_changed_old_entry",
             "test_service_shape_rejects_globals_and_other_functions", "test_dispatch_preserves_old_validator_and_refuses_unknown_selector",
             "test_missing_route_cannot_validate", "test_bridge_refuses_product_change_or_forged_snapshot"} <= names,
            "Required acceptance refusal tests missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "junit_sha256": result["junit_sha256"]}


def checked_stages(folder):
    require({p.name for p in (folder / "stages").iterdir()} == set(STAGES),
            "Missing or additional native compatibility stage")
    records = [read(folder / "stages" / s / "result.json") for s in STAGES]
    require(all(r["stage"] == s and r["status"] == "PASS" and 0 <= r["wall_seconds"] < 115
                for s, r in zip(STAGES, records)) and
            sum(r["wall_seconds"] for r in records) < 720, "Missing/failed native compatibility stage")
    return records


def validate_submission(root, attempt, task):
    if "annual_profile_compatibility" in task:
        from scripts.prospectus_profile_delta import validate_submission as validate_profile
        return validate_profile(root, attempt, task)
    selector(task)
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    with prior.bounded_stage(SELECTOR["validation_seconds"]), prior.live.offline():
        result = read(attempt / "result.json")
        require(result.get("status") == "PASS" and result.get("task") == "native-binding" and
                result.get("scope") == "FINITE_CURRENT_NATIVE_COMPATIBILITY" and
                result.get("whole_program_complete") is False and result.get("new_native_calls") == 0,
                "Wrong native compatibility result")
        require(read(attempt / "methods.json") == methods(root), "Native compatibility methods changed")
        checked_stages(attempt)
        check_tests(attempt)
        require(read(attempt / "historical-evidence.json") == historical_evidence(root), "Historical native compatibility evidence differs")
        for name in ROUTES:
            require(read(attempt / "routes" / (name + ".json")) == route(root, name, rebuild=False), "Current native answer/reference differs")
        require(read(attempt / "adverse.json") == adverse(root), "Current native adverse evidence differs")
        require(sum(p.stat().st_size for p in attempt.rglob("*") if p.is_file()) < 32 * 1024**2, "Native compatibility evidence cap exceeded")
    return True
