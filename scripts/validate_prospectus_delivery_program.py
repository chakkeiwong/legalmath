"""Check a proposed delivery program; never dispatch its future handlers.

Run from the worktree: python3 -m scripts.validate_prospectus_delivery_program
Only readiness.json and validation-manifest.json in the new program directory
are written. No imports from production, network, model or GPU operations occur.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-delivery-program-2026-10-06"
PROGRAM = OUT / "program.json"
INVESTIGATION = ROOT / "docs/implementation/prospectus-root-cause-2026-10-06"
DOCS = [
    ROOT / "docs/plans/prospectus-delivery-program-2026-10-06.md",
    ROOT / "docs/plans/prospectus-root-cause-investigation-2026-10-06.md",
    INVESTIGATION / "ROOT-CAUSE-REPORT.md",
    INVESTIGATION / "LITERATURE-REVIEW.md",
    OUT / "PROGRAM-EVIDENCE.md",
    OUT / "SKEPTICAL-REVIEW.md",
    OUT / "RESET-MEMO.md",
]
SCRIPTS = [
    ROOT / "scripts/audit_prospectus_root_causes.py",
    ROOT / "scripts/prepare_prospectus_root_cause_literature.py",
    Path(__file__).resolve(),
]
INSPECTED = [
    "src/legalmath/cli.py",
    "src/legalmath/prospectus/master_phases.py",
    "src/legalmath/prospectus/closure_mechanisms.py",
    "src/legalmath/prospectus/eligibility.py",
    "src/legalmath/prospectus/reader_scope.py",
    "scripts/run_bond_loss_absorption_classification.py",
    "scripts/prospectus_corner_repair_worker.py",
    "scripts/prospectus_basf_admission.py",
    "scripts/prospectus_refresh_admission.py",
    "scripts/prospectus_refresh_semantics.py",
    ".localresources/projects/catala-conditions.ml",
    ".localresources/projects/catala-translation.fst",
    ".localresources/projects/catala-formalization.md",
    ".localresources/legal-interpretation-reuse-2026-10-05/aspic-correction.html",
    ".localresources/legal-interpretation-reuse-2026-10-05/sources/SgfdDttt__sara-ie/sara/data/dataset/ground_case.py",
    ".localresources/legal-interpretation-reuse-2026-10-05/sources/SgfdDttt__sara-ie/sara/models/ie.py",
    ".localresources/legal-interpretation-reuse-2026-10-05/sources/DaphneOdekerken__PyArg/src/py_arg/aspic_classes/argumentation_theory.py",
    ".localresources/legal-interpretation-reuse-2026-10-05/sources/DaphneOdekerken__PyArg/src/py_arg/algorithms/semantics/get_grounded_extension.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    if len(sys.argv) != 1:
        raise SystemExit("No arguments: this checks only the fixed proposed specification.")
    started = time.monotonic()
    program = read(PROGRAM)
    failures, bindings, checks = [], {}, []

    def require(condition, label):
        checks.append({"check": label, "pass": bool(condition)})
        if not condition:
            failures.append(label)

    def bind(path, expected=None):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        require(path.is_file(), "file exists: " + str(path))
        if not path.is_file():
            return
        actual = sha(path)
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        bindings[key] = actual
        if expected is not None:
            require(actual == expected, "hash matches: " + key)

    require(program["schema"] == "prospectus-delivery-program.v1", "schema")
    require(program["status"] == "PROPOSED_NOT_EXECUTED", "proposal is not execution")
    phases = program["phases"]
    ids = [p["id"] for p in phases]
    require(len(set(ids)) == len(ids), "unique phase ids")
    require(set(ids) == {f"P{i}" for i in range(9)}, "P0-P8 all present")
    expected_roots = {f"R{i:02d}" for i in range(1, 13)}
    require(set(program["root_causes"]) == expected_roots, "R01-R12 declared")
    covered = {r for p in phases for r in p["maps_to"]}
    require(covered == expected_roots, "all root causes mapped")
    graph = {p["id"]: set(p["depends_on"]) for p in phases}
    remaining, ordered = set(ids), []
    while remaining:
        ready = sorted(p for p in remaining if graph[p] <= set(ordered))
        if not ready:
            require(False, "acyclic DAG with known dependencies")
            break
        ordered.extend(ready)
        remaining.difference_update(ready)
    require(not remaining, "topological order found")
    missing = []
    for phase in phases:
        prefix = phase["id"] + ": "
        require(phase["implementation_status"] == "NOT_IMPLEMENTED", prefix + "honest implementation status")
        require(phase["execution_status"] == "NOT_EXECUTED", prefix + "honest execution status")
        require(phase["evidence_status"] == "PENDING", prefix + "independent evidence not fabricated")
        require(phase["release_status"] == "NOT_ACCEPTED", prefix + "release not fabricated")
        for field in ("owner", "deliverables", "acceptance", "promotion_veto",
                      "continuation_veto", "repair_trigger", "refresh", "budget"):
            require(bool(phase.get(field)), prefix + field)
        path = ROOT / phase["handler"]["path"]
        require(not path.exists(), prefix + "planned handler really absent")
        missing.append(phase["handler"]["path"])
        require(phase["command"]["status"] == "PLANNED_UNAVAILABLE", prefix + "command marked unavailable")
        require(phase["command"]["argv"] == [
            "python3", "-m", "scripts.prospectus_delivery", "phase", "--phase", phase["id"]
        ], prefix + "fixed future command form")
    controller = program["controller"]
    require(controller["status"] == "NOT_IMPLEMENTED", "controller status")
    require(not (ROOT / controller["path"]).exists(), "future dispatcher really absent")
    missing.append(controller["path"])
    budget = program["resources"]["http"]
    require(budget["limit"] - budget["used"] == budget["remaining"] == 24, "HTTP allowance unchanged")
    require(program["evaluation"]["reviewers"] == [], "reviewers unassigned")
    require(program["evaluation"]["curator"] is None, "curator unassigned")
    require(program["evaluation"]["threshold_owner"] is None, "risk threshold owner unassigned")

    for path, expected in program["evidence_bindings"].items():
        bind(path, expected)
    probe = read(INVESTIGATION / "probes/manifest.json")
    require(probe["git_commit"] == program["baseline"]["git_commit"], "probe/program baseline equality")
    require(len(probe["summary"]) == 7, "seven diagnostic probes")
    for group in ("reader_bindings", "artifacts"):
        for path, expected in probe[group].items():
            bind(path, expected)
    bind(SCRIPTS[0], probe["method_sha256"])
    literature = read(INVESTIGATION / "literature/manifest.json")
    require(len(literature["records"]) == 7, "seven retained papers")
    for paper in literature["records"]:
        for kind in ("pdf", "text"):
            bind(paper[kind], paper[kind + "_sha256"])
    for path, expected in literature["parser_files"].items():
        bind(path, expected)
    for relative in INSPECTED:
        bind(relative)
    generated = {OUT / "readiness.json", OUT / "validation-manifest.json"}
    for document in DOCS:
        bind(document)
        if not document.is_file():
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"[A-Za-z]+://", target):
                continue
            path = (document.parent / target).resolve()
            require(path.exists() or path in generated,
                    "local document link: " + str(document.relative_to(ROOT)) + " -> " + target)
    for script in SCRIPTS:
        bind(script)
        try:
            ast.parse(script.read_text(), filename=str(script))
        except SyntaxError:
            require(False, "Python syntax: " + script.name)
        else:
            require(True, "Python syntax: " + script.name)
    bind(PROGRAM)
    current_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", program["baseline"]["git_commit"], current_commit],
        cwd=ROOT, capture_output=True, text=True)
    require(ancestry.returncode == 0, "current commit descends from inspected baseline")
    result = {
        "specification_status": "PASS" if not failures else "FAIL",
        "product_execution_performed": False,
        "execution_readiness": "HANDLERS_NOT_IMPLEMENTED",
        "independent_acceptance": "PENDING_EXTERNAL_RESOURCES",
        "topological_order": ordered,
        "root_causes_mapped": sorted(covered),
        "missing_handlers": missing,
        "checks_passed": sum(c["pass"] for c in checks),
        "checks_total": len(checks),
        "failures": failures,
        "checked_bindings": len(bindings),
        "checks": checks,
    }
    output = OUT / "readiness.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "git_commit": current_commit,
        "inspected_baseline": program["baseline"]["git_commit"],
        "command": [sys.executable, "-m", "scripts.validate_prospectus_delivery_program"],
        "python": sys.version,
        "compute": "CPU only; no framework/GPU initialization",
        "random_seeds": "N/A deterministic specification check",
        "data_version": "program and nested baseline/source hashes below",
        "wall_seconds": time.monotonic() - started,
        "plan": program["governing_plan"],
        "result": str(output.relative_to(ROOT)),
        "result_sha256": sha(output),
        "input_bindings": bindings,
        "new_network_requests": 0,
        "new_model_calls": 0,
        "new_installations": 0,
        "meaning": "Structural specification validation only; no product handler executed",
    }
    (OUT / "validation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("checks", "missing_handlers")}, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
