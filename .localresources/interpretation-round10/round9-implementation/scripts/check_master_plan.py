"""Check the review packet and task graph; does not execute the planned product."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reviews/master-plan-evidence"
OUTPUT = EVIDENCE / "plan-check.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    plan = (ROOT / "docs/implementation/master-plan.md").read_text()
    graph = json.loads((ROOT / "docs/implementation/master-plan.tasks.json").read_text())
    tasks = {t["id"]: t for t in graph["tasks"]}
    if len(tasks) != len(graph["tasks"]):
        errors.append("duplicate task IDs")
    if set(tasks) != {f"T{i:02d}" for i in range(25)}:
        errors.append("task inventory differs from T00-T24")
    active, visited, order = set(), set(), []

    def visit(ident):
        if ident not in tasks:
            errors.append(f"unknown dependency {ident}")
            return
        if ident in active:
            errors.append(f"dependency cycle at {ident}")
            return
        if ident in visited:
            return
        active.add(ident)
        for dep in tasks[ident]["depends_on"]:
            visit(dep)
        active.remove(ident)
        visited.add(ident)
        order.append(ident)

    for ident in tasks:
        visit(ident)
    case_ids = set(re.findall(r"^\| (A\d\d) \|", plan, re.M))
    if case_ids != {f"A{i:02d}" for i in range(1, 17)}:
        errors.append("acceptance inventory differs from A01-A16")
    for ident, task in tasks.items():
        match = re.search(r"^### " + ident + r" — ([^\n]+)\n(.*?)(?=^### T\d\d|^## 7\.|\Z)", plan, re.M | re.S)
        if not match:
            errors.append(f"missing task section {ident}")
            continue
        if match.group(1) != task["title"]:
            errors.append(f"title mismatch {ident}")
        if "\n" in task["title"] or len(task["title"]) > 120:
            errors.append(f"invalid task title {ident}")
        deps = re.search(r"Depends ([^;]+);", match.group(2))
        prose_deps = set(re.findall(r"T\d\d", deps.group(1))) if deps else set()
        if prose_deps != set(task["depends_on"]):
            errors.append(f"prose/graph dependency mismatch {ident}")
        if not task["acceptance_criteria"] or not task["planned_outputs"] or not task["acceptance_command"]:
            errors.append(f"missing output/acceptance contract {ident}")
        if set(task["acceptance_cases"]) - case_ids:
            errors.append(f"unknown acceptance case {ident}")
        if task["implementation_status"] != "NOT_STARTED" or task["evidence_paths"]:
            errors.append(f"unexpected implementation claim in initial review packet: {ident}")
        if task["command_status"] != "PLANNED_NOT_RUN":
            errors.append(f"future command represented as executed: {ident}")

    ancestors = set()

    def closure(ident):
        for dep in tasks.get(ident, {}).get("depends_on", []):
            if dep not in ancestors:
                ancestors.add(dep)
                closure(dep)

    closure("T22")
    required = {i for i, t in tasks.items() if t["required_for_engineering_mvp"]}
    if required != ancestors | {"T22"}:
        errors.append("MVP dependency closure omits a required task or includes optional work")
    if ancestors & {"T23", "T24"}:
        errors.append("optional research/pilot blocks engineering MVP")
    if graph["independent_claude_review"] != "NOT_RUN; handoff prepared":
        errors.append("unexpected Claude review claim")

    markdown = [ROOT / "README.md", *sorted((ROOT / "docs/implementation").glob("*.md")),
                *sorted((ROOT / "docs/specs/v0.1").glob("*.md")),
                ROOT / "docs/reviews/master-plan-review.md", ROOT / "docs/reviews/claude-review-handoff.md",
                EVIDENCE / "README.md", *sorted((ROOT / "docs/plans/templates").glob("*.md")),
                ROOT / "docs/plans/master-plan-audit-plan.md", ROOT / "docs/plans/master-plan-reset-memo.md"]
    link_count = 0
    for p in markdown:
        if not p.exists():
            errors.append(f"missing packet document {p.relative_to(ROOT)}")
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)\n]+)\)", p.read_text()):
            target = target.strip().strip("<>")
            if target.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z+.-]*:", target):
                continue
            resolved = (p.parent / unquote(target.split("#")[0])).resolve()
            link_count += 1
            if resolved != OUTPUT and not resolved.exists():
                errors.append(f"broken link {p.relative_to(ROOT)} -> {target}")

    baseline = json.loads((EVIDENCE / "baseline-files.json").read_text())["files"]
    protected = {name: digest for name, digest in baseline.items()
                 if name.startswith(("examples/", "scripts/")) or name.endswith((".pdf", ".schema.json"))
                 or "/fixtures/" in name or name.endswith("storage.sql")}
    for name, digest in protected.items():
        if not (ROOT / name).exists() or sha(ROOT / name) != digest:
            errors.append(f"protected source/demo/PDF changed: {name}")
    inputs = json.loads((EVIDENCE / "review-inputs.json").read_text())
    for name, digest in inputs["files"].items():
        if not (ROOT / name).exists() or sha(ROOT / name) != digest:
            errors.append(f"stale review input: {name}")
    replay = json.loads((EVIDENCE / "java-replay-comparison.json").read_text())
    if not all(r["matches"] and r["original"] == r["replay"] for r in replay["files"].values()):
        errors.append("isolated Java replay differs from original")
    spec = json.loads((EVIDENCE / "spec-check.json").read_text())
    if spec["runtime_decisions_executed"] != 0 or spec["event_and_release_outcomes_executed"]:
        errors.append("fixture check claims unavailable full runtime execution")
    record = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "initial master-plan review packet, not product correctness",
        "status": "PASS" if not errors else "FAIL", "errors": errors,
        "task_count": len(tasks), "core_tasks": len(required), "topological_order": order,
        "acceptance_case_families": len(case_ids), "local_links_checked": link_count,
        "protected_files_unchanged": len(protected), "review_input_files_checked": len(inputs["files"]),
        "isolated_java_hashes_match": len(replay["files"]),
        "claude_review": "NOT_RUN; handoff prepared",
        "application_implemented_by_this_task": False,
    }
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
