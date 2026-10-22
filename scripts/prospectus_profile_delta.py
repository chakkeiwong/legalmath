"""Finite current compatibility after the two reviewed annual-profile additions."""
import ast
import base64
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_native_product_delta as old

prior = old.prior
require = old.require
BASE = old.BASE
REVIEW = BASE + "/reviews/profile-delta-195"
PREVIOUS = BASE + "/attempts/native-binding/attempt-020"
CURRENT = BASE + "/attempts/source-bes-dep-09/attempt-014"
NATIVE = old.NATIVE
SCRIPT = "scripts/prospectus_profile_delta.py"
RUNNER = "scripts/prospectus_profile_delta_runner.py"
TEST = "tests/prospectus/test_profile_delta.py"
PLAN = "docs/plans/prospectus-current-profile-compatibility-2026-10-17.md"
PROPOSAL = BASE + "/proposals/profile-delta-195.json"
REVIEW_FILE = BASE + "/proposals/profile-delta-195-review.json"
ROUTE_FILE = BASE + "/closure-routes-2026-10-17-profile-delta-195.json"
CELLS = old.CELLS
PROFILE_KEYS = ("bes-annual2010-statements-notes.v1", "bes-annual2010-statements-capital-notes.v2")
ROUTES = old.ROUTES
STAGES = old.STAGES
TEST_MODULES = (TEST, old.TEST, prior.TEST,
    "tests/prospectus_successor/test_statement_cells.py",
    "tests/prospectus_successor/test_annual_statement_cells.py",
    "tests/prospectus_successor/test_annual_capital_statement_cells.py")
SELECTOR = {"version": "current-annual-profile-delta.v1", "review": REVIEW,
    "previous_native": PREVIOUS, "source_execution": NATIVE, "normal_build": CURRENT,
    "stages": list(STAGES), "routes": list(ROUTES), "new_native_calls": 0,
    "new_subprocess_calls": 0, "stage_seconds": 115, "execution_seconds": 720,
    "validation_seconds": 195, "evidence_bytes": 32 * 1024**2}


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected compatibility dispatch baseline")
    return before.replace(marker, marker +
        '    if "annual_profile_compatibility" in task:\n'
        '        from scripts.prospectus_profile_delta import validate_submission as validate_profile\n'
        '        return validate_profile(root, attempt, task)\n')


def canonical(value):
    return json.loads(json.dumps(value))


def annual_shape(before, after, profiles, explanation_ast):
    """Protect every old entry/function; only the exact reviewed extension differs."""
    require(set(profiles) == set(PROFILE_KEYS), "Wrong annual profile denominator")
    trees = [ast.parse(s) for s in (before, after)]
    old_explanation = None
    for index, tree in enumerate(trees):
        require(isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str), "Statement docstring missing")
        tree.body.pop(0)
        declarations = [n for n in tree.body if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == "PROFILES" for t in n.targets)]
        require(len(declarations) == 1 and isinstance(declarations[0].value, ast.Dict), "Profile declaration differs")
        declaration = declarations[0].value
        for key in PROFILE_KEYS:
            indices = [i for i, k in enumerate(declaration.keys) if isinstance(k, ast.Constant) and k.value == key]
            require(len(indices) == index, "Unexpected annual profile addition")
            if index:
                i, = indices
                require(canonical(ast.literal_eval(declaration.values[i])) == profiles[key], "Annual profile content differs")
                declaration.keys.pop(i); declaration.values.pop(i)
        positions = [i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == "explain"]
        require(len(positions) == 1, "One statement explanation required")
        position, = positions
        if index == 0:
            old_explanation = tree.body[position]
        else:
            require(ast.dump(tree.body[position], include_attributes=False) == explanation_ast,
                "Unreviewed statement explanation")
            tree.body[position] = old_explanation
    require(ast.dump(trees[0], include_attributes=False) == ast.dump(trees[1], include_attributes=False),
        "Old profile or other statement implementation changed")


def literal_profiles(source):
    tree = ast.parse(source)
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    class Inline(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in constants:
                value = constants[node.id]
                if isinstance(value, (str, int, float, bool, type(None))):
                    return ast.copy_location(ast.Constant(value), node)
            return node
    tree = Inline().visit(tree)
    ast.fix_missing_locations(tree)
    declarations = [n for n in tree.body if isinstance(n, ast.Assign) and
        any(isinstance(t, ast.Name) and t.id == "PROFILES" for t in n.targets)]
    require(len(declarations) == 1, "One literal profile declaration required")
    return ast.literal_eval(declarations[0].value)


def annual_source_evidence(root, profiles):
    from legalmath.prospectus.successor.statement_cells import profile_digest
    cases = {
        PROFILE_KEYS[0]: ("tests/prospectus_successor/fixtures/bes_annual2010_statement_cells.json.gz",
            "docs/implementation/prospectus-execution-authority/reviews/2010-annual-product-187/profile.json"),
        PROFILE_KEYS[1]: ("tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v2.json.gz", None),
    }
    result = {}
    for name, (fixture_name, profile_name) in cases.items():
        with gzip.open(root / fixture_name, "rt") as stream:
            fixture = json.load(stream)
        graph, reading, profile = fixture["graph"], fixture["reading"], profiles[name]
        if profile_name:
            require(canonical(read(root / profile_name)) == profile, "Annual source review profile differs")
        selected = sorted((u for u in graph["units"] if u["document"] == profile["document"]
            and u["page"] in profile["pages"]), key=lambda u: (u["page"], u["order"], u["id"]))
        require(profile_digest(reading) == profile["reading"] and len(selected) == profile["occurrences"]
            and bool(selected) and all(u["visible"] and u["source_sha256"] == profile["source"] for u in selected)
            and profile_digest(selected) == profile["pages_digest"], "Annual reading/source geometry differs")
        result[name] = {"fixture": fixture_name, "fixture_sha256": file_hash(root / fixture_name),
            "profile_sha256": file_hash(root / profile_name) if profile_name else None,
            "reading_sha256": profile_digest(reading), "page_occurrences": len(selected),
            "pages_sha256": profile_digest(selected), "source_sha256": profile["source"]}
    installed = literal_profiles((root / CURRENT / "installed/legalmath/prospectus/successor/statement_cells.py").read_text())
    require(all(canonical(installed[name]) == canonical(profiles[name]) for name in PROFILE_KEYS),
        "Fresh normal-build installation has different annual profiles")
    return result


def method_bridge(frozen, snapshots, current, changes, additions):
    require(set(frozen) == set(snapshots) and set(current) == set(frozen) | set(additions)
        and not set(frozen) & set(additions), "Compatibility method inventory differs")
    require(all(hashlib.sha256(bytes.fromhex(snapshots[p])).hexdigest() == h for p, h in frozen.items()),
        "Forged historical method snapshot")
    changed = {p for p, h in frozen.items() if current[p] != h}
    require(changed == set(changes), "Unexpected changed compatibility methods")
    require(all(changes[p] == {"before": frozen[p], "after": current[p]} for p in changed)
        and all(current[p] == h for p, h in additions.items()), "Unreviewed exact compatibility method bytes")
    return sorted(changed)


def package_delta(before, after, additions, cell_change):
    key = CELLS.removeprefix("src/legalmath/")
    require(set(after) == set(before) | set(additions) and not set(before) & set(additions), "Current package inventory differs")
    require({p for p in before if before[p] != after[p]} == {key}
        and cell_change == {"before": before[key], "after": after[key]}
        and all(after[p] == h for p, h in additions.items()), "Unreviewed current package delta")


def methods(root):
    return {**old.methods(root), **{p: file_hash(root / p) for p in (SCRIPT, RUNNER, TEST, *TEST_MODULES)}}


def storage(root, attempt):
    """Charge new attempt, review, transport and revision copies without a workspace."""
    roots = [attempt, root / REVIEW, *(root / p for p in (PROPOSAL, REVIEW_FILE, ROUTE_FILE,
        BASE + "/revisions/0195.json", SCRIPT, RUNNER, TEST, PLAN))]
    found = {}
    for parent in roots:
        paths = parent.rglob("*") if parent.is_dir() else [parent]
        for path in paths:
            require(not path.is_symlink(), "Compatibility evidence symlink refused")
            if path.is_file():
                st = path.stat(); found[st.st_dev, st.st_ino] = st.st_size
    return sum(found.values())


def wheel_contents(path, expected):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and archive.testzip() is None and
            all(not Path(p).is_absolute() and ".." not in Path(p).parts for p in names), "Invalid normal wheel archive")
        records = [p for p in names if p.endswith(".dist-info/RECORD")]
        require(len(records) == 1, "One wheel RECORD required")
        record, = records
        rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
        require(all(len(r) == 3 for r in rows) and len(rows) == len(names)
            and {r[0] for r in rows} == set(names), "Wheel RECORD denominator differs")
        for name, encoded, length in rows:
            data = archive.read(name)
            if name == record:
                require(encoded == length == "", "RECORD self-entry differs")
            else:
                actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
                require(encoded == "sha256=" + actual and length == str(len(data)), "Wheel RECORD content differs")
        package = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
            for p in names if p.startswith("legalmath/")}
        require(package == expected, "Normal wheel package differs")
    return file_hash(path)


def method_evidence(root):
    spec = read(root / REVIEW / "approved-delta.json")
    folder = root / PREVIOUS
    frozen = read(folder / "methods.json")
    snapshots = prior.helper.read(folder / "method-snapshots.json.gz")
    current = methods(root)
    changes = method_bridge(frozen, snapshots, current, spec["changes"], spec["added_methods"])
    require(set(changes) == {CELLS, old.SCRIPT}, "Wrong reviewed current delta")
    before = {p: bytes.fromhex(snapshots[p]).decode() for p in changes}
    require((root / old.SCRIPT).read_text() == dispatch_candidate(before[old.SCRIPT]), "Unreviewed native task dispatch")
    annual_shape(before[CELLS], (root / CELLS).read_text(), spec["annual_profiles"], spec["explanation_ast"])
    source_profiles = annual_source_evidence(root, spec["annual_profiles"])
    old_package = read(root / old.INSTALLED / "source-package.json")
    package = read(root / CURRENT / "final-package.json")
    package_delta(old_package, package, spec["added_package_modules"], spec["changes"][CELLS])
    require(prior.helper.package_files(root / "src/legalmath") == package ==
        prior.helper.package_files(root / CURRENT / "installed/legalmath"), "Current source or installed package changed")
    wheel = read(root / CURRENT / "built-wheel.json")
    require(wheel["normal_build"] is True and wheel["all_non_RECORD_entry_bytes_equal"] is True and
        wheel["RECORD_semantics_equal"] is True and wheel["package_files"] == len(package), "Normal-build evidence differs")
    require(wheel_contents(root / CURRENT / wheel["path"], package) == wheel["sha256"], "Normal wheel identity changed")
    for action in ("candidate-products", "candidate-answer", "input-a", "phase-c"):
        receipt = read(root / CURRENT / "installed-checks" / (action + ".json"))
        require(receipt["status"] == "PASS" and receipt["action"] == action and receipt["isolated"] == 1
            and receipt["native_calls"] == 0 and receipt["package_files"] == len(package)
            and receipt["package"] == str(root / CURRENT / "installed/legalmath")
            and bool(receipt["modules_relative_to_package"]), "Normal installed comparison is incomplete")
        require(all(p in package for p in receipt["modules_relative_to_package"].values()), "Installed module inventory differs")
    return {"changed_methods": changes, "added_package_modules": spec["added_package_modules"],
        "native_methods_sha256": digest(current), "current_package_sha256": digest(package),
        "package_files": len(package), "normal_wheel_sha256": wheel["sha256"],
        "annual_profiles": list(PROFILE_KEYS), "annual_source_evidence": source_profiles,
        "old_profiles_and_admission_unchanged": True, "task_specific_dispatch_frozen": True}


def historical_evidence(root):
    a = Authority(root); history = read(root / REVIEW / "history.json"); events = a.events()
    require(all(e in events and a.retained_evidence_valid(e) for e in history["validated_events"]),
        "Retained native or normal-build evidence changed")
    require(any(e["attempt"] == PREVIOUS and e["kind"] == "ACCEPT" for e in history["validated_events"])
        and any(e["attempt"] == NATIVE and e["kind"] == "ACCEPT" for e in history["validated_events"])
        and any(e["attempt"] == CURRENT and e["kind"] == "RECORD" for e in history["validated_events"]),
        "Required actual native/current-build history missing")
    folder = root / NATIVE
    prior.native.grant(read(folder / "admission.json")["task_spec"])
    tested = prior.native.tests(folder, read(folder / "methods.json"))
    prior.checked_stages(folder, prior.native.STAGES)
    snapshots = {year: prior.common.snapshot(folder / "snapshots" / year) for year in ("2009", "2010")}
    for year, number in (("2009", "008"), ("2010", "006")):
        baseline = root / BASE / "attempts/native-binding" / ("attempt-" + number)
        prior.common.verify_files(baseline / "method-final", read(baseline / "frozen-methods.json"))
        require(snapshots[year] == read(baseline / "snapshot/manifest.json"), "Protected native runtime changed")
    controls = prior.common.check_controls(folder)
    probe = prior.common.check_probe(folder, snapshots["2009"])
    rows = prior.native.ledger(folder, 11)["reservations"]
    require([r["argv"][0] == "/usr/bin/bwrap" for r in rows] ==
        [True, True, False, False, True, True, True, True, True, True, True], "Original native reservation sequence differs")
    require([read(folder / "stages" / ("route-" + route) / "result.json")["details"]["reservations"] for route in ROUTES]
        == [[i, i + 2] for i in range(0, 10, 2)], "Original five-route reservation denominator differs")
    old.checked_stages(root / PREVIOUS)
    return {"method_evidence": method_evidence(root), "historical_tests": tested,
        "prelaunch_controls": controls, "probe_receipt_sha256": probe, "prior_reservations": 11,
        "native_lineage_lower_bound": 61, "prior_native_admissions": 20, "new_native_calls": 0,
        "scope": "Original actual native executions; current complete downstream compatibility"}


route = old.route
adverse = old.adverse
checked_stages = old.checked_stages


def selector(task):
    require(task.get("id") == "native-binding" and task.get("validator") == prior.NATIVE
        and task.get("product_delta_acceptance") == old.SELECTOR
        and task.get("annual_profile_compatibility") == SELECTOR and task.get("native_call_allowance") == 0
        and task.get("retained_acceptance_only") is True, "Unreviewed annual-profile native selector")


def check_tests(folder):
    result = read(folder / "tests/result.json")
    require(result["exit_code"] == 0 and result["status"] == "PASS" and
        result["junit_sha256"] == file_hash(folder / "tests/results.xml"), "Current profile-delta tests missing")
    tree = ET.parse(folder / "tests/results.xml").getroot(); suites = list(tree.iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")),
        "Current profile-delta tests failed/skipped")
    names = {n.get("name", "").split("[")[0] for n in tree.iter("testcase")}
    require({"test_annual_shape_protects_old_profiles_and_functions", "test_method_bridge_refuses_repinning_and_inventory_changes",
        "test_package_delta_refuses_unreviewed_modules", "test_native_dispatch_preserves_fallback_and_enforces_selector",
        "test_selector_refuses_other_scope_or_allowance", "test_all_five_routes_are_required",
        "test_complete_nested_reading_preserves_source_and_authority_limits",
        "test_combined_profile_exposes_old_readings_and_capital_notes"} <= names, "Required profile compatibility checks missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "junit_sha256": result["junit_sha256"]}


def validate_submission(root, attempt, task):
    selector(task); root, attempt = Path(root).resolve(), Path(attempt).resolve()
    with prior.bounded_stage(SELECTOR["validation_seconds"]), prior.live.offline():
        result = read(attempt / "result.json")
        require(result.get("status") == "PASS" and result.get("task") == "native-binding"
            and result.get("scope") == "FINITE_CURRENT_NATIVE_COMPATIBILITY"
            and result.get("whole_program_complete") is False and result.get("new_native_calls") == 0,
            "Wrong current native compatibility result")
        require(read(attempt / "methods.json") == methods(root), "Current compatibility methods changed")
        checked_stages(attempt); check_tests(attempt)
        require(read(attempt / "historical-evidence.json") == historical_evidence(root), "Native history or current delta differs")
        for name in ROUTES:
            require(read(attempt / "routes" / (name + ".json")) == route(root, name, rebuild=False),
                "Current complete route differs: " + name)
        require(read(attempt / "adverse.json") == adverse(root), "Current native provenance refusals differ")
        require(storage(root, attempt) < SELECTOR["evidence_bytes"],
            "Current native evidence cap exceeded")
    return True
