"""Current offline native preparation, separate from historical/live acceptance."""
from pathlib import Path, PurePosixPath
import gzip
import json
import re
import xml.etree.ElementTree as ET

from .execution_authority import CODE, digest, file_hash, read
from . import native_binding_acceptance as historical
from .successor import process_ledger, service

VERSION = "native-current-preparation.v1"
BASE = "docs/implementation/prospectus-execution-authority"
INVENTORY = BASE + "/reviews/native-verification-recovery-123/receipt-inventory.json"
ROUTES = {"2009-" + m: BASE + "/attempts/native-binding/attempt-008/" + m
          for m in ("fresh", "default", "retained")}
ROUTES.update({"2010-" + m: BASE + "/attempts/native-binding/attempt-006/" + m
               for m in ("fresh", "retained")})
SCRIPT = "scripts/prospectus_native_campaign.py"
TESTS = ("tests/prospectus/test_native_current_preparation.py", "tests/prospectus/test_verify_task.py")
MAX_BYTES = 32 * 1024 * 1024
REQUIRED_TESTS = {
    "test_current_admission_and_historical_destinations", "test_symlinks_refuse_before_writes",
    "test_duplicate_and_sealed_preserve_bytes", "test_failure_finalizes_complete_manifest",
    "test_cooperative_cancel_finalizes", "test_changed_methods_refuse_before_stage",
    "test_missing_matrix_arm_refuses", "test_changed_receipt_refuses",
    "test_unaccounted_reservation_refuses", "test_preparation_cannot_accept_task",
    "test_live_stage_refuses_without_writes", "test_subprocess_attempt_is_retained",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(root, name):
    """Require a canonical relative path with no symlink component."""
    root = Path(root).resolve()
    require(isinstance(name, str) and bool(name), "Evidence path must be text")
    parts = PurePosixPath(name).parts
    require(not name.startswith("/") and ".." not in parts and str(PurePosixPath(name)) == name,
            "Evidence path must be canonical and relative")
    path = root
    for part in parts:
        path /= part
        require(not path.is_symlink(), "Symlink evidence path refused: " + name)
    require(path.resolve().is_relative_to(root), "Evidence path escapes root")
    return path


def files(folder):
    answer = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Symlink output refused")
        if path.is_file():
            answer[str(path.relative_to(folder))] = file_hash(path)
    return answer


def method_names(root):
    names = {str(p.relative_to(root)) for p in (root / "src/legalmath/prospectus").rglob("*.py")}
    names.update(CODE)
    names.update((SCRIPT, "scripts/prospectus_native_preparation_tests.py", "scripts/prospectus_verify_task.py", *TESTS))
    return sorted(names)


def methods(root):
    return {p: file_hash(local(root, p)) for p in method_names(root)}


def check_methods(root, folder):
    expected = read(folder / "methods.json")
    require(expected == methods(root), "Current method set changed after freeze")
    with gzip.open(folder / "method-snapshots.json.gz", "rt") as stream:
        snapshots = json.load(stream)
    require(set(snapshots) == set(expected), "Method snapshot inventory incomplete")
    from hashlib import sha256
    require(all(sha256(snapshots[p].encode()).hexdigest() == h for p, h in expected.items()),
            "Current method snapshot changed")
    return expected


def current_admission(authority, name):
    folder = local(authority.root, name)
    prefix = str((authority.base / "attempts/native-binding").relative_to(authority.root))
    require(re.fullmatch(re.escape(prefix) + r"/attempt-[0-9]{3,}", name) is not None,
            "Current native-binding attempt path required")
    admitted = read(local(authority.root, name + "/admission.json"))
    program, tasks, _ = authority.spec()
    require(admitted.get("task") == "native-binding", "Wrong admitted task")
    task = tasks["native-binding"]
    events = [e for e in authority.events() if e.get("task") == "native-binding"]
    require(bool(events) and events[-1]["kind"] == "ADMIT" and events[-1]["attempt"] == name,
            "Current unclosed admission required")
    require(file_hash(folder / "admission.json") == events[-1]["admission_sha256"],
            "Admission changed after freeze")
    require(admitted.get("attempt") == name and admitted["program_sha256"] == digest(program)
            and admitted["task_sha256"] == digest(task) and admitted["task_spec"] == task
            and admitted["binding"] == authority.binding(task), "Admitted method/input or program changed")
    require(task.get("preparation_only") is True and task.get("native_call_allowance") == 0
            and task.get("validator") is None and bool(task.get("completion_validation_pending")),
            "Explicit offline partial preparation required")
    require(not any((folder / p).exists() for p in ("result.json", "outputs.json")),
            "Sealed attempt refused")
    files(folder)  # Refuse symlink outputs before any stage can write through them.
    return folder, admitted, task


def check_zero_ledger(folder):
    ledger = read(folder / "offline-ledger.json")
    require(ledger == {"version": VERSION, "native_call_allowance": 0,
        "historical_lower_bound": 50, "reservations": [],
        "scope": "Offline preparation; historical floor is not a successful-call total"},
        "Unexpected reservation or changed offline allowance")
    return ledger


def check_tests(folder, current):
    runs = sorted((folder / "validation").glob("run-*/result.json"))
    require(1 <= len(runs) <= 2, "Expected one or two bounded test starts")
    result = read(runs[-1])
    tested = read(runs[-1].parent / "methods.json")
    require(result["status"] == "PASS" and result["exit_code"] == 0
            and 0 <= result["wall_seconds"] <= 120 and tested == current,
            "Current tests failed, timed out or tested different methods")
    xml = runs[-1].parent / "tests.xml"
    require(file_hash(xml) == result["tests_sha256"], "Test report changed")
    suites = list(ET.parse(xml).getroot().iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("failures", "errors", "skipped")),
            "Failed/skipped focused checks")
    names = {n.get("name", "").split("[")[0] for n in ET.parse(xml).getroot().iter("testcase")}
    require(REQUIRED_TESTS <= names, "Required current refusal checks missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites),
            "path": str(xml.relative_to(folder)), "sha256": file_hash(xml), "starts": len(runs)}


def historical_receipt(folder, manifest):
    row = read(folder / "receipt.json")
    streams = [(folder / n).read_bytes() for n in ("stdin", "stdout", "stderr")]
    historical.runtime.verify_receipt(row, manifest, row["argv"], *streams, require_current=False)
    require(row["returncode"] == 0 and row["file_namespace"] ==
            "sealed explicit files; private proc/dev/tmp; no host directory mounts", "Historical call failed")
    return row


def history(root):
    """Verify retained bytes against retained identities, never against new code."""
    inventory = read(local(root, INVENTORY))
    require({r["route"] for r in inventory["routes"]} == set(ROUTES)
            and len(inventory["routes"]) == len(ROUTES), "Historical route inventory differs")
    historical.verify_files(root, inventory["input_files"])
    lineage = []
    for row in inventory["ledger_lineage"]:
        actual = process_ledger.checked(local(root, row["path"]))
        require(actual == {k: v for k, v in row.items() if k not in {"attempt", "path"}},
                "Historical ledger differs")
        lineage.append((row["attempt"], actual["historical_lower_bound"], len(actual["reservations"])))
    require(lineage == [(4, 18, 9), (5, 27, 2), (6, 30, 9), (7, 39, 0), (8, 39, 11)]
            and inventory["historical_lower_bound"] == 50, "Historical cumulative floor differs")
    snapshots = {}
    for attempt in ("attempt-006", "attempt-008"):
        old = local(root, BASE + "/attempts/native-binding/" + attempt)
        historical.verify_files(old / "method-final", read(old / "frozen-methods.json"))
        snapshots[str(old.relative_to(root)) + "/snapshot/manifest.json"] = historical.snapshot(old / "snapshot")
    routes = []
    for route in inventory["routes"]:
        folder = local(root, ROUTES[route["route"]])
        manifest = snapshots[route["manifest"]]
        for call in route["calls"]:
            native = local(root, call["folder"])
            if route["route"] == "2009-default":
                record = read(native / "command.json")
                require(read(native / "result.json")["returncode"] == 0, "Historical default call failed")
            else:
                record = historical_receipt(native, manifest)
            require(record == call["record"], "Historical receipt/command changed")
            for name, binding in call["streams"].items():
                path = native / name
                require(file_hash(path) == binding["sha256"] and path.stat().st_size == binding["bytes"],
                        "Historical native stream changed")
        paths = [folder / (p + ".json.gz") for p in ("P1", "P2", "P3", "P4", "P5", "answer")]
        routes.append({"route": route["route"], "consumed_P1": str(paths[0].relative_to(root)),
            "source_kind": "RETAINED_REBOUND_P1", "products": {str(p.relative_to(root)): file_hash(p) for p in paths}})
    return {"version": VERSION, "routes": routes, "historical_lower_bound": 50,
            "inventory_sha256": file_hash(root / INVENTORY), "native_calls": 0,
            "current_native_execution_established": False}


def load_object(root, row):
    require(set(row) == {"path", "sha256"}, "Object reference fields differ")
    path = local(root, row["path"])
    require(file_hash(path) == row["sha256"], "Referenced object changed")
    return historical.unpack(path)


def validate_route(root, folder, route):
    result = read(folder / "stages" / ("replay-" + route) / "result.json")
    require(result["status"] == "PASS" and result["subprocess_attempts"] == 0
            and 0 <= result["wall_seconds"] <= 120, "Current route failed or timed out")
    comparison = read(folder / "routes" / route / "comparison.json")
    require(set(comparison["objects"]) == {"P1", "P2", "P3", "P4", "P5", "answer"},
            "Incomplete current route products")
    old = local(root, ROUTES[route])
    objects = {k: load_object(root, row) for k, row in comparison["objects"].items()}
    for key, obj in objects.items():
        require(obj == historical.unpack(old / (key + ".json.gz")), "Full retained comparison differs: " + key)
    require(comparison["current_native_execution_established"] is False
            and comparison["actual_current_consumer"] is True, "Route scope is not retained-source replay")
    values, answer = historical.products(old)
    require(objects == {**values, "answer": answer}, "Route parent/product identities differ")
    return {"route": route, "answer_sha256": answer["report_sha256"],
            "products": {k: v["sha256"] for k, v in values.items()}, "complete_equality": True}


def evidence(root, folder):
    """Check current retained evidence without repeating consumers or native calls."""
    current = check_methods(root, folder)
    check_zero_ledger(folder)
    tests = check_tests(folder, current)
    require(history(root) == read(folder / "historical-evidence.json"), "Historical preparation evidence differs")
    for route in ROUTES:
        require((folder / "routes" / route / "comparison.json").is_file(), "Missing current matrix arm: " + route)
    rows = [validate_route(root, folder, route) for route in ROUTES]
    require(sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) < MAX_BYTES,
            "Preparation storage cap exceeded")
    return {"version": VERSION, "status": "PASS", "scope": "OFFLINE_PREPARATION_ONLY",
        "routes": rows, "tests": tests, "methods_sha256": digest(current), "native_calls": 0,
        "historical_lower_bound": 50, "current_native_execution_established": False,
        "task_acceptance_established": False, "whole_program_complete": False,
        "pending": ["Current live source driver and validator", "Reviewed cumulative live grant",
                    "Fresh five-route matrix and boundary/prelaunch controls", "Independent legal/source acceptance"]}
