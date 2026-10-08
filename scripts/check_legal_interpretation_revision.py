"""Verify the two documentation revisions without running product code or providers."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("docs/implementation/legal-interpretation-program")
MANIFEST = BASE / "revision-2-manifest.json"
RESULT = BASE / "revision-2-validation.json"
ARCHIVE = BASE / "revisions/revision-1"
CHANGED = (
    "docs/plans/legal-interpretation-master-program.md",
    "docs/plans/legal-interpretation-program/README.md",
    "docs/plans/legal-interpretation-program/P0-baseline-and-operative-repair.md",
    "docs/plans/legal-interpretation-program/P1-typed-meaning-and-evidence.md",
    "docs/plans/legal-interpretation-program/P2-clause-scope-and-pilot-readings.md",
    "docs/plans/legal-interpretation-program/P3-arguments-and-explicit-priorities.md",
    "docs/plans/legal-interpretation-program/P5-evidence-applicability-and-consequences.md",
    "docs/plans/legal-interpretation-program/P6-lowering-explanations-and-product-integration.md",
    "docs/plans/legal-interpretation-program/P7-independent-checks-and-formal-claims.md",
    "docs/plans/legal-interpretation-program/P8-coverage-and-prospective-observation.md",
    str(BASE / "phase-manifest.json"),
    str(BASE / "README.md"),
)
CURRENT = CHANGED + (
    "docs/plans/legal-interpretation-program/P4-precedent-and-factor-transfer.md",
    str(BASE / "revision-2-audit.md"),
    str(BASE / "claude-review-response.md"),
    str(BASE / "claude-review.md"),
    "scripts/check_legal_interpretation_revision.py",
)
ORIGINAL_MANIFEST_SHA = "f61bb9c37c3706d8cfa90c0d25af61f0b7b58fe15fcfcc21f6966fabb7835924"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def path(name):
    target = (ROOT / name).resolve()
    require(target.is_relative_to(ROOT), "Outside checkout: " + str(name))
    require(not {".git", ".codex", ".agents", ".venv"}.intersection(
        target.relative_to(ROOT).parts), "Protected path: " + str(name))
    return target


def sha(name):
    return hashlib.sha256(path(name).read_bytes()).hexdigest()


def record(name):
    return {"path": str(name), "sha256": sha(name), "bytes": path(name).stat().st_size}


def main():
    require(len(sys.argv) == 1, "This fixed checker accepts no arguments")
    handoff = BASE / "handoff.sha256"
    original_manifest = BASE / "handoff-manifest.json"
    require(sha(original_manifest) == ORIGINAL_MANIFEST_SHA,
            "Original handoff manifest changed")
    rows = [line.split("  ", 1) for line in path(handoff).read_text().splitlines()]
    require(len(rows) == 693 and len({r[1] for r in rows}) == 693,
            "Original handoff count/uniqueness mismatch")
    expected = {name: digest for digest, name in rows}
    overrides = []
    changed_live = []
    for digest, name in rows:
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "Malformed digest")
        retained = str(ARCHIVE / name) if name in CHANGED else name
        require(sha(retained) == digest, "Historical mismatch: " + name)
        if retained != name:
            overrides.append({"path": name, "retained_path": retained, "sha256": digest})
        if sha(name) != digest:
            changed_live.append(name)
    require(len(overrides) == 11, "Unexpected historical override scope")

    snapshots = []
    for name in CHANGED:
        saved = str(ARCHIVE / name)
        snapshots.append({"path": name, "retained_path": saved, "sha256": sha(saved)})
        if name in expected:
            require(sha(saved) == expected[name], "Snapshot mismatch: " + name)
    current = [record(name) for name in CURRENT]
    binding = {
        "schema_version": 1, "program_revision": 2,
        "scope": "Documentation amendment; not Claude approval or phase completion",
        "original_handoff": str(handoff), "original_handoff_sha256": sha(handoff),
        "original_manifest": str(original_manifest),
        "original_manifest_sha256": sha(original_manifest),
        "original_entry_count": len(rows),
        "historical_overrides": overrides, "pre_amendment_snapshots": snapshots,
        "files": current,
        "excludes": [str(MANIFEST), str(RESULT)],
        "exclusion_reason": "No recursive hashes; validation records this manifest's hash",
    }
    phase = json.loads(path(BASE / "phase-manifest.json").read_text())
    phases = phase["phases"]
    ids = [p["id"] for p in phases]
    require(ids == ["P" + str(i) for i in range(9)], "Phase inventory changed")
    require(phase["program_revision"] == 2 and phase["product_phases_executed"] == []
            and phase["runtime_entry_point"] is None and phase["provider_calls_used"] == 0,
            "Unexpected execution state")
    require(phase["claude_review"] == "RECEIVED_FOR_REVISION_1"
            and phase["revision_2_independent_review"] == "NOT_DISPATCHED",
            "Review scope changed")
    parsed = ast.parse(path("scripts/legal_interpretation_ops.py").read_text())
    fixed_tests = next(ast.literal_eval(node.value) for node in parsed.body
                       if isinstance(node, ast.Assign) and any(
                           isinstance(t, ast.Name) and t.id == "PHASE_TESTS"
                           for t in node.targets))
    dependency_map = {p["id"]: p["depends_on"] for p in phases}
    visited, active = set(), set()

    def visit(phase_id):
        require(phase_id in dependency_map, "Missing dependency: " + phase_id)
        require(phase_id not in active, "Cyclic phase dependencies")
        if phase_id in visited:
            return
        active.add(phase_id)
        for dependency in dependency_map[phase_id]:
            visit(dependency)
        active.remove(phase_id)
        visited.add(phase_id)

    for p in phases:
        visit(p["id"])
        require(p["status"] == "PLANNED_NOT_EXECUTED" and p["required_result"] is None,
                "Unexpected completion: " + p["id"])
        require("Status: PLANNED_NOT_EXECUTED" in path(p["plan"]).read_text(),
                "Plan status mismatch")
        declared = ["tests/interpretation/semantics/" + t for t in fixed_tests[p["id"]]]
        require(p["future_tests"] == declared, "Fixed test mapping mismatch")
    response = path(BASE / "claude-review-response.md").read_text()
    for i in range(1, 13):
        require("| F" + str(i).zfill(2) + " —" in response, "Missing finding disposition")

    links = 0
    for name in CURRENT:
        if not name.endswith(".md") or name.endswith("/claude-review.md"):
            continue
        for dest in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", path(name).read_text()):
            dest = dest.strip("<>")
            split = urlsplit(dest)
            if split.scheme or not split.path:
                continue
            target = (path(name).parent / unquote(split.path)).resolve()
            if target == path(MANIFEST) and not target.exists():
                # The initial snapshot is proposed on stdout, then bound explicitly.
                continue
            require(target.is_relative_to(ROOT) and target.exists(),
                    "Broken local link in " + name + ": " + dest)
            links += 1
    diff = subprocess.run(["git", "diff", "--check", "--", *CURRENT],
                          cwd=ROOT, text=True, capture_output=True, timeout=30)
    require(diff.returncode == 0, "Diff whitespace check failed: " + diff.stdout + diff.stderr)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                          capture_output=True, check=True, timeout=10).stdout.strip()
    checks = {"historical_entries": len(rows), "archived_overrides": len(overrides),
              "current_files": len(current), "phase_dag": "ACYCLIC",
              "planned_phases": len(phases), "phase_test_mapping": "MATCHES_FIXED_RUNNER",
              "finding_dispositions": 12, "local_links": links, "diff_check": "PASS",
              "expected_changed_handoff_paths": changed_live}
    if not path(MANIFEST).exists():
        return {"status": "READY_TO_BIND", "checks": checks, "proposed_manifest": binding}
    require(json.loads(path(MANIFEST).read_text()) == binding,
            "Revision identity mismatch; do not refresh hashes silently")
    return {"status": "PASS", "checked_at": datetime.now(timezone.utc).isoformat(),
            "command": "python3 -m scripts.check_legal_interpretation_revision",
            "git_commit": head, "manifest_sha256": sha(MANIFEST), "checks": checks,
            "product_phases_executed": [], "provider_dispatch_requested": False,
            "scope": "Documentation identity, links, phase graph and command mapping only",
            "not_established": ["implementation acceptance", "English fidelity",
                                "legal correctness", "revision-2 Claude approval"]}


if __name__ == "__main__":
    try:
        result = main()
    except (ValueError, OSError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "FAIL", "reason": str(error)}, indent=2))
        raise SystemExit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))
