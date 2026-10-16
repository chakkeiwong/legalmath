#!/usr/bin/env python3
"""Record the completed offline integration attempt and return to product work."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT / "docs/implementation/legal-mission-control/mission.json"
TOOLS = ROOT / "docs/implementation/legal-mission-control/tools.json"
OUT = ROOT / "artifacts/legal-mission-control/2026-10-10/tool-integration"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def controlled(scope: str, *evidence: dict[str, str]) -> dict:
    return {"level": "controlled", "evidence": list(evidence), "scope": scope}


def source_manifest() -> dict:
    paths = [
        "scripts/legal_integration_tools.py",
        "scripts/legal_mission_logical_english.py",
        "scripts/legal_mission_tool_integration.py",
        "scripts/legal_mission_integration_controls.py",
        "scripts/legal_mission_live_preflight.py",
        "src/legalmath/interpretation/assurance/provider_authority.py",
        "src/legalmath/interpretation/assurance/source_context.py",
        "src/legalmath/interpretation/assurance/scoped_investigation.py",
        "src/legalmath/interpretation/assurance/complete_investigation.py",
        "src/legalmath/interpretation/assurance/dossier_answer.py",
        "tests/assurance/test_integration_completion.py",
        "docs/plans/legal-mission-tool-integration-execution.md",
        "docs/implementation/legal-mission-control/tool-integration-final-local-review.md",
        "docs/implementation/legal-mission-control/tool-integration-source-controls-review.md",
        "docs/implementation/legal-mission-control/tool-integration-resource-review.md",
    ]
    return {
        "profile": "legal-mission-tool-integration-final-source-manifest.v1",
        "command": ".venv/bin/python scripts/legal_mission_finalize_integration.py",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1 set before package imports",
        "live_calls": 0,
        "source_files": [ref(ROOT / path) for path in paths],
        "result_files": [
            ref(OUT / "qualify-correction-3/result.json"),
            ref(OUT / "capacity-correction-3/result.json"),
            ref(OUT / "source-controls/result.json"),
            ref(OUT / "live-preflight/result.json"),
        ],
        "unrelated_allowance_sha256": sha(ROOT / "artifacts/assurance-new-grant/2026-09-29/live-allowance.json"),
    }


def update_tools() -> None:
    tools = read(TOOLS)
    result_doc = ref(ROOT / "docs/implementation/legal-mission-control/results/tool-integration.md")
    source_result = ref(OUT / "source-controls/result.json")
    qualify_result = ref(OUT / "qualify-correction-3/result.json")
    preflight_result = ref(OUT / "live-preflight/result.json")
    final_source = ref(OUT / "final-source-manifest.json")
    integration_evidence = [result_doc, qualify_result, source_result, preflight_result, final_source]
    for tool in tools:
        if tool["id"] not in {"bm25", "legalruleml", "pyarg", "carneades", "clingo", "logical-english"}:
            continue
        tool["evidence"] = tool.get("evidence", []) + [r for r in integration_evidence if r not in tool.get("evidence", [])]
        tool["fully_integrated"] = False
        tool["evaluation"] = None
        if tool["id"] == "logical-english":
            tool["current_use"] = "A restricted source-bound Boolean adapter ran against the prepared full packet; six formalized paragraph-14 activation proposals passed and six unformalized paragraph-10 proposals stayed unsupported."
            tool["remaining_gap"] = "The source-to-controlled-language warrant and downstream complete-answer contribution remain unassessed; general English interpretation is unsupported."
            tool["next_test_or_reopen"] = "Use the adapter in the matched original-question answer comparison and retain unsupported fulfillment readings; assess source warrant before any promotion."
            tool["stages"]["target_adapter"] = controlled("Restricted pinned parser/AST adapter; exact source remapping and Boolean consequence checks only.", result_doc, source_result, final_source)
            tool["stages"]["product_invocation"] = controlled("Current ProductToolBackend ToolSession invocation on twelve retained paragraph-14/paragraph-10 proposals.", qualify_result, source_result)
            tool["stages"]["question_preservation"] = controlled("Exact P14 question and source/candidate hashes delivered in the source-linked control.", source_result, final_source)
            tool["stages"]["downstream_delivery"] = controlled("Tool result reached the local product delivery sink; no final-answer consideration was measured.", qualify_result, source_result)
            tool["stages"]["negative_and_unsupported"] = controlled("Unknown request, malformed quote/source, non-Boolean, nine-fact and unformalized cases remain explicit.", source_result, result_doc)
        else:
            tool["current_use"] = tool["current_use"] + " Final local qualification ran this tool independently and in the all-six product configuration; result delivery and unsupported controls passed."
            tool["remaining_gap"] = tool["remaining_gap"] + " A matched complete legal answer and source-grounded downstream contribution remain unassessed."
            tool["next_test_or_reopen"] = "Run the matched original-question baseline/candidate comparison, then inspect whether this tool changes a warranted inference while preserving contrary readings."
            tool["stages"]["target_adapter"] = controlled("Explicit selectable current ProductToolBackend profile bound into method/cache identity.", result_doc, qualify_result, final_source)
            tool["stages"]["product_invocation"] = controlled("Current CompleteInvestigation path executed the selected tool independently and in the all-six profile.", qualify_result, result_doc)
            tool["stages"]["question_preservation"] = controlled("Exact source/candidate/question bindings were preserved through the current product qualification.", qualify_result, source_result)
            tool["stages"]["downstream_delivery"] = controlled("Tool feedback reached the dossier/consumer delivery path; scripted answer is legally empty.", qualify_result, result_doc)
            tool["stages"]["negative_and_unsupported"] = controlled("Disabled profiles, oversized graphs, false warrants, undercuts and unsupported readings remain explicit.", result_doc, source_result)
    write(TOOLS, tools)


def update_mission() -> None:
    mission = read(MISSION)
    task = next(t for t in mission["tasks"] if t["id"] == "tool-integration-completion")
    result_doc = ROOT / "docs/implementation/legal-mission-control/results/tool-integration.md"
    result_refs = [
        ref(result_doc),
        ref(OUT / "qualify-correction-3/result.json"),
        ref(OUT / "capacity-correction-3/result.json"),
        ref(OUT / "source-controls/result.json"),
        ref(OUT / "live-preflight/result.json"),
        ref(OUT / "final-source-manifest.json"),
    ]
    task["status"] = "blocked"
    task["blocker_kind"] = "target_answer_and_live_resource"
    task["blocker_scope"] = "Local adapter and byte-capacity controls pass, but genuine full-target answer fidelity, matched tool contribution, a fresh live grant and enforceable service billing ceiling remain unavailable."
    task["blocker_evidence"] = [ref(result_doc), ref(OUT / "live-preflight/result.json")]
    task["actual_result"] = ref(result_doc)
    row = {
        "id": "tool-integration-return-2026-10-10",
        "task_id": "tool-integration-completion",
        "kind": "engineering",
        "outcome": "no_advance",
        "result_evidence": result_refs,
        "decision": "Local integration controls pass, but the synthetic answer is legally empty and the live pilot is not ready; retain all failures and return to the original substantive product-contribution task.",
        "next_task": "product-contribution",
        "next_task_reason": "The current route now preserves qualified source identity, occurrence context, selectable six-tool execution, explicit unsupported cases and a concrete 375-call pilot specification. Complete-target answer fidelity and tool contribution still require a fresh resource decision; no additional repair or live call is authorized.",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_resource_accounting": {
            "new_live_calls": 0,
            "approved_consolidated_attempts": 1,
            "attempts_remaining": 0,
            "cumulative_detours": 4,
            "approved_attempt_minutes": 120,
            "historical_ledgers_rewritten": False,
            "live_pilot_ready": False,
            "proposed_global_call_ceiling": 375,
        },
    }
    if any(h["id"] == row["id"] for h in mission["history"]):
        raise SystemExit("integration return already recorded")
    mission["history"].append(row)
    mission["current_task"] = "product-contribution"
    mission["next_task_reason"] = row["next_task_reason"]
    write(MISSION, mission)


def main() -> None:
    if any(row['id'] == 'tool-integration-return-2026-10-10'
           for row in read(MISSION)['history']):
        raise SystemExit('Integration return already recorded; no files changed.')
    manifest = source_manifest()
    write(OUT / "final-source-manifest.json", manifest)
    update_tools()
    update_mission()
    print(json.dumps({"status": "RECORDED", "mission": ref(MISSION), "tools": ref(TOOLS),
                      "final_source_manifest": ref(OUT / "final-source-manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
