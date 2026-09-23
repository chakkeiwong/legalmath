"""Audit current completion evidence without rewriting the original planning packet."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/runs/acceptance/execution-check.json"
errors = []


def read(name):
    return json.loads((ROOT / name).read_text())


def sha(name):
    path = ROOT / name
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def require(condition, message):
    if not condition: errors.append(message)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


graph = read("docs/implementation/master-plan.tasks.json")
tasks = {t["id"]: t for t in graph["tasks"]}
require(len(tasks) == len(graph["tasks"]) == 25, "Task inventory is not T00-T24")
require(set(tasks) == {f"T{i:02}" for i in range(25)}, "Unexpected task identity")
require(graph["application_status"] == "ENGINEERING_MVP_COMPLETE; LOCAL_SYNTHETIC", "Incorrect application authority/status")
visited, active = set(), set()


def visit(ident):
    if ident in active:
        errors.append("Cyclic task dependency: " + ident)
        return
    if ident not in tasks:
        errors.append("Unknown task dependency: " + ident)
        return
    if ident in visited: return
    active.add(ident)
    for parent in tasks[ident]["depends_on"]: visit(parent)
    active.remove(ident)
    visited.add(ident)


for ident in tasks: visit(ident)
tests = ET.parse(ROOT / "artifacts/runs/acceptance/tests.xml").getroot()
cases = tests.findall(".//testcase")
require(bool(cases), "No executed tests")
require(not any(c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped")), "Suite has failures/errors/skips")
require(set(read("tests/conformance/contract-matrix.json")["cases"]) == {f"A{i:02}" for i in range(1, 17)}, "Acceptance families changed")
for t in tasks.values():
    if t["required_for_engineering_mvp"]:
        require(t["implementation_status"] == "COMPLETE", "Unfinished core task " + t["id"])
        require(t["command_status"].startswith("PASSED"), "No passing command for " + t["id"])
        require(all(tasks[p]["implementation_status"] == "COMPLETE" for p in t["depends_on"]), "Incomplete dependency for " + t["id"])
        names = {p[:-3].replace("/", ".") for p in t["executed_test_files"]}
        actual = sum(c.attrib["classname"] in names for c in cases)
        require(actual == t["passing_test_count"] and actual > 0, "Test evidence mismatch for " + t["id"])
        for name in t["planned_outputs"] + t["executed_test_files"] + t["evidence_paths"]:
            require((ROOT / name).exists(), "Missing output/evidence: " + name)
require(tasks["T23"]["implementation_status"] == "NOT_RUN_OPTIONAL", "Adapter claim requires separate evidence")
require(tasks["T24"]["implementation_status"] == "PENDING_HUMAN_PILOT", "Human pilot claim requires separate evidence")

manifest = read("artifacts/runs/acceptance/run-manifest.json")
final = read("artifacts/runs/acceptance/final-artifacts.json")
require(manifest["status"] == "CORE_ACCEPTANCE_PASSED", "Core run failed")
require({c["name"] for c in manifest["commands"]} == {"tests", "contracts", "spec-runtime", "walkthrough"}, "Missing acceptance command")
for c in manifest["commands"]: require(c["exit_code"] == 0, "Failed command: " + c["name"])
for name, expected in manifest["input_sha256"].items():
    if name == "scripts/browser_walkthrough.py":
        repair = final["browser_harness_repair"]
        require(expected == repair["before_sha256"] and sha(name) == repair["after_sha256"] and repair["passed_after_repair"], "Unexplained browser harness change")
    else:
        require(sha(name) == expected, "Implementation changed after acceptance: " + name)
for name, expected in final["artifact_sha256"].items():
    require(sha(name) == expected, "Evidence changed or missing: " + name)
for c in final["additional_checks"]: require(c["exit_code"] == 0, "Failed additional check")

walk = read("artifacts/runs/mvp-accepted/walkthrough.json")
require(walk["status"] == "OFFLINE_WALKTHROUGH_PASSED" and walk["original_replay_equal"], "Walkthrough/restore failed")
require(walk["authority"] == "LOCAL_SYNTHETIC" and not walk["production_bank_connection"], "False bank authority")
require(walk["bank_legal_approval"] == walk["human_usability"] == "PENDING", "Unsubstantiated human approval")
for directory, expected_jar in [("java-release", walk["java"]["jar_sha256"]), ("amended-java-release", walk["amendment_jar_sha256"])]:
    prefix = "artifacts/runs/mvp-accepted/" + directory + "/"
    build, report, release = (read(prefix + name) for name in ("build-manifest.json", "verification-report.json", "release-manifest.json"))
    require(sha(prefix + "policy.jar") == expected_jar == build["jar_sha256"] == report["jar_sha256"], "Wrong delivered Java binary")
    require(canonical_hash(build) == report["build_manifest_hash"] == release["build_manifest_hash"], "Wrong build identity")
    require(canonical_hash(report) == release["verification_report_hash"] and report["passed"], "Wrong verification identity")
    require(all(c["passed"] for c in report["checks"]), "Failed release verification")
    require({c["name"] for c in report["checks"]} == {"full-semantic-conformance", "attributed-event-conformance"}, "Missing decision/event release evidence")
require(walk["amendment_jar_sha256"] != walk["java"]["jar_sha256"], "Amendment reused old binary")
require(sha("artifacts/runs/mvp-accepted/history.zip") == walk["history_archive"]["archive_hash"], "Wrong history archive")

browser = read("artifacts/runs/browser-review/report.json")
require(len(browser["checks"]) == 5 and all(c["http_status"] == 200 for c in browser["checks"]) and browser["keyboard_expansion"], "Browser checks incomplete")
require(any(c.get("authenticated_get") for c in browser["checks"]), "API console was not exercised")
require((ROOT / "artifacts/runs/fresh-install/pip-check.txt").read_text().strip() == "No broken requirements found.", "Fresh installation dependencies failed")
spec = json.loads((ROOT / "artifacts/runs/acceptance/spec-runtime.log").read_text())
require(spec["runtime_decisions_executed"] == 35 and not spec["legal_interpretations_approved"], "Runtime/authority evidence mismatch")

baseline = read("docs/reviews/master-plan-evidence/baseline-files.json")["files"]
protected = {k:v for k,v in baseline.items() if k.startswith(("examples/", "scripts/")) or k.endswith((".pdf", ".schema.json", "storage.sql")) or "/fixtures/" in k}
for name, expected in protected.items(): require(sha(name) == expected, "Protected baseline changed: " + name)
inputs = read("docs/reviews/master-plan-evidence/review-inputs.json")["files"]
for name, expected in inputs.items():
    require(sha("docs/reviews/master-plan-evidence/initial-review-snapshot/" + name) == expected, "Initial review snapshot changed: " + name)

documents = ["README.md", "README.application.md", "docs/implementation/START-HERE.md", "docs/implementation/master-plan.md", "docs/implementation/execution-report.md", "docs/specs/v0.1/implementation-closure.md"]
links = 0
for name in documents:
    path = ROOT / name
    for target in re.findall(r"\[[^\]]*\]\(([^)\n]+)\)", path.read_text()):
        target = target.strip().strip("<>")
        if target.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z+.-]*:", target): continue
        links += 1
        require((path.parent / unquote(target.split("#")[0])).exists(), "Broken link: " + name + " -> " + target)

result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS" if not errors else "FAIL", "errors": errors,
    "core_tasks": sum(t["required_for_engineering_mvp"] for t in tasks.values()), "passing_tests": len(cases), "source_files_checked": len(manifest["input_sha256"]),
    "final_evidence_files_checked": len(final["artifact_sha256"]), "protected_baseline_files_checked": len(protected), "initial_review_files_checked": len(inputs), "local_links_checked": links,
    "authority": "LOCAL_SYNTHETIC", "optional_adapters": "NOT_RUN", "human_model_pilot": "PENDING"}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if errors: raise SystemExit(1)
