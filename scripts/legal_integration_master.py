#!/usr/bin/env python3
"""Fixed, resumable master for the complete integration contract.

Local commands never create a live grant. Native tools and model calls are
separate branches. Historical programs, attempts and grants remain untouched.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import Execution, ref, verify, read, save, require, digest

DOC = Path("docs/implementation/legal-mission-control")
BASE = Path("artifacts/legal-mission-control/2026-10-13/master")
PLAN = Path("docs/plans/legal-integration-master-2026-10-13.md")
SUBSTANTIVE_PLAN = Path("docs/plans/legal-integration-substantive-continuation-2026-10-14.md")
PROGRAM = DOC / "integration-master.json"
STATE = BASE / "execution-state.json"
CONTRACT = Path("docs/plans/legal-mission-integration-completion-contract-2026-10-12.md")
RULES = DOC / "integration-master.rules"
TOOLS = ("bm25", "legalruleml", "pyarg", "carneades", "clingo", "logical-english")
QUESTIONS = ("p10", "p14", "evidence", "gatecoin")
PRIOR = Path("artifacts/legal-mission-control/2026-10-12/remaining-work")
TOKENIZER = Path(".localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken")
LOCAL_ACTIONS = ("check", "status", "prepare", "verify", "run", "approval-packet")


def current_qualification_view(root, program, view):
    """Show later verified diagnostics without altering attempt status/history."""
    if program.get('execution_refresh'):
        return view
    reference = program.get('remaining_work_revision', {}).get('final_verification')
    if not reference:
        return view
    verify(root, reference)
    latest = read(root / reference['path'])
    require(latest['source'] == program['remaining_work_revision']['source_revision'],
            'Final qualification describes a different current source')
    for qid, outcome in latest['questions'].items():
        tid = 'qualify-' + qid
        if tid not in view['tasks'] or view['tasks'][tid]['status'] != 'BLOCKED':
            continue
        require(outcome['_node_status'] == 'BLOCKED', 'Local diagnostic cannot promote live qualification')
        verify(root, outcome['capacity'])
        row = view['tasks'][tid]
        row.setdefault('recorded_attempt_reason', row['reason'])
        row['reason'] = outcome['_conclusion']
        row['current_verification'] = outcome['capacity']
        view['blocked'][tid] = outcome['_conclusion']
    view['current_verification'] = reference
    return view


def summary(root=ROOT):
    program = read(root / PROGRAM)
    execution = MasterExecution(root, PROGRAM, STATE)
    view = current_qualification_view(root, program, execution.summary())
    return {"program": str(PROGRAM), "plan": str(PLAN), "execution": view["execution"],
            "ready": view["ready"], "running": view["running"], "blocked": view["blocked"],
            "tasks": view["tasks"], "mission_complete": False,
            "historical_calls": 41, "historical_detours": 18,
            "new_live_grant_present": (root / BASE / "live-grant.json").exists(),
            "local_deadline": program["deadline_utc"]}


class MasterExecution(Execution):
    def sync_mission(self):
        from scripts import legal_mission_control as control
        mission_path = self.root / DOC / "mission.json"
        with mission_path.with_suffix(".execution.lock").open("a") as lock:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
            mission = read(mission_path)
            require(mission["integration_master"]["program"] == ref(self.root, self.program_path),
                    "Master program is not registered")
            with self.locked() as state:
                completed = [(tid, a) for tid, row in state["tasks"].items()
                             for a in row["attempts"] if "result" in a]
            recorded = {(r.get("master_node"), r.get("master_attempt")) for r in mission["history"]}
            for tid, attempt in sorted(completed, key=lambda pair: pair[1]["finished_at_utc"]):
                if (tid, attempt["number"]) in recorded: continue
                result = read(self.root / attempt["result"]["path"])
                mission["history"].append({"id": f"master-{tid}-{attempt['number']}",
                    "task_id": "product-contribution", "kind": "product_evaluation", "outcome": "no_advance",
                    "master_node": tid, "master_attempt": attempt["number"],
                    "decision": result["conclusion"], "next_task": "product-contribution",
                    "next_task_reason": "Continue ready master nodes; retain question/tool-specific blockers and complete source work independently.",
                    "recorded_at_utc": attempt["finished_at_utc"],
                    "result_evidence": [ref(self.root, self.program_path), attempt["result"]]})
            view = self.summary()
            mission["next_task_reason"] = ("Integration master active. Ready: " + ", ".join(view["ready"]) +
                ". Read the master frontier for dependent blockers; no local result establishes legal closure.")
            control.validate(mission, read(self.root / DOC / "tools.json"), self.root)
            save(mission_path, mission)
        result = subprocess.run([".venv/bin/python", "scripts/legal_mission_control.py", "refresh"],
                                cwd=self.root, capture_output=True, text=True, timeout=300)
        (self.root / BASE / "mission-refresh.json").write_text(result.stdout)
        require(result.returncode == 0, "Mission refresh failed: " + result.stderr[-500:])
        save(self.root / BASE / "next-ready.json", self.summary())
        with self.locked() as state:
            state.pop("mission_sync_error", None)
            save(self.state_path, state)


def task(tid, deps=(), *, after=(), agent=False, questions=QUESTIONS, deliverable=None):
    return {"id": tid, "executor": "agent" if agent else "command", "kind": "product_evaluation",
        "question_ids": list(questions), "priority": 10, "requires": list(deps), "after": list(after),
        "maximum_attempts": 2, "write_resources": [tid], "inputs": [],
        "acceptance": deliverable or tid, "deliverable": str(BASE / tid / "result.json"),
        **({} if agent else {"command": [".venv/bin/python", "scripts/legal_integration_master.py", "worker", tid],
                            "timeout_seconds": 3600})}


def prepare():
    if (ROOT / PROGRAM).exists():
        from scripts.legal_integration_repair_execution import WORK as REPAIR_WORK
        if (ROOT / REPAIR_WORK / 'pending-round.json').exists():
            from scripts.legal_integration_repair_execution import register
            return register()
        from scripts.legal_integration_complete_account_capacity import WORK as COMPLETE_CAPACITY_WORK
        if (ROOT / COMPLETE_CAPACITY_WORK / 'review.md').exists():
            require((ROOT / COMPLETE_CAPACITY_WORK / 'local-review.json').exists(),
                'Capacity amendment needs retained local validation before registration')
            from scripts.legal_integration_complete_account_capacity import register
            return register()
        from scripts.legal_integration_account_reconstruction import WORK as RECONSTRUCTION_WORK
        if (ROOT / RECONSTRUCTION_WORK / 'review.md').exists():
            require((ROOT / RECONSTRUCTION_WORK / 'local-review.json').exists(),
                'Reconstruction amendment needs retained local validation before registration')
            from scripts.legal_integration_account_reconstruction import register
            return register()
        from scripts.legal_integration_account_instruction_repair import WORK as INSTRUCTION_WORK
        if (ROOT / INSTRUCTION_WORK / 'review.md').exists():
            require((ROOT / INSTRUCTION_WORK / 'local-review.json').exists(),
                    'Instruction amendment needs retained local validation before registration')
            from scripts.legal_integration_account_instruction_repair import register
            return register()
        from scripts.legal_integration_qualification_continuation import WORK as QUALIFICATION_WORK
        if (ROOT / QUALIFICATION_WORK / 'local-review.json').exists():
            from scripts.legal_integration_qualification_continuation import register
            return register()
        from scripts.legal_integration_lossless_repair import WORK as LOSSLESS_WORK
        if (ROOT / LOSSLESS_WORK / 'local-review.json').exists():
            from scripts.legal_integration_lossless_repair import register
            return register()
        from scripts.legal_integration_schema_repair import WORK as SCHEMA_WORK
        if (ROOT / SCHEMA_WORK / 'local-review.json').exists():
            from scripts.legal_integration_schema_repair import register
            return register()
        from scripts.legal_integration_account_repair import WORK as ACCOUNT_WORK
        if (ROOT / ACCOUNT_WORK / 'local-review.json').exists():
            from scripts.legal_integration_account_repair import register
            return register()
        from scripts.legal_integration_route_repair import WORK as ROUTE_WORK
        if (ROOT/ROUTE_WORK/'local-review.json').exists():
            from scripts.legal_integration_route_repair import register
            return register()
        from scripts.legal_integration_phased_repair import WORK as PHASE_WORK
        if (ROOT/PHASE_WORK/'local-review.json').exists():
            from scripts.legal_integration_phased_repair import register
            return register()
        if (ROOT / 'docs/plans/legal-integration-master-execution-refresh-2026-10-14.md').exists():
            from scripts.legal_integration_execution_refresh import register
            return register()
        if (ROOT / SUBSTANTIVE_PLAN).exists() and read(ROOT / PROGRAM).get('remaining_work_revision'):
            from scripts.legal_integration_substantive_continuation import register
            return register()
        if (ROOT / DOC / 'remaining-work-review-2026-10-13.md').exists():
            from scripts.legal_integration_remaining import register
            return register()
        if (ROOT / DOC / 'acceptance-revision-review-2026-10-13.md').exists():
            from scripts.legal_integration_acceptance_revision import register
            return register()
        return summary()
    from scripts import legal_mission_control as control
    mission = read(ROOT / DOC / "mission.json")
    state = control.validate(mission, read(ROOT / DOC / "tools.json"))
    require(state["detours_since_advance"] == 18, "Unexpected historical detour count")
    directory = ROOT / BASE
    directory.mkdir(parents=True, exist_ok=True)
    protected = [PLAN, CONTRACT, DOC / "mission.json", DOC / "tools.json",
        Path("scripts/legal_product_completion.py"), Path("src/legalmath/interpretation/assurance/complete_investigation.py"),
        Path("src/legalmath/interpretation/assurance/dossier_answer.py")]
    for path in protected:
        target = directory / "before" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    save(directory / "baseline.json", {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_status": subprocess.check_output(["git", "status", "--porcelain", "-uno"], cwd=ROOT, text=True),
        "historical_calls": 41, "historical_detours": 18,
        "protected": [ref(ROOT, directory / "before" / p) for p in protected],
        "contract": ref(ROOT, CONTRACT), "plan": ref(ROOT, PLAN)})
    nodes = [task("scope", deliverable="Original contract and exact populations retained; no historical reset"),
             task("sources", ["scope"], deliverable="Combined retained corpus, qualifications and exact original source identities"),
             task("runtime", ["scope"], deliverable="Persistent budget/restart/failure controls pass"),
             task("product", ["scope"], deliverable="Actual bounded product path and semantic-loss negative controls pass"),
             task("corpus-qualification", ["sources"], agent=True,
                  deliverable="Rendered/source fidelity and dated research qualification for each source profile")]
    for q in QUESTIONS:
        nodes.append(task("legal-" + q, ["scope"], questions=[q],
                          deliverable="Source-backed conditional acceptance cases and precise remaining research/facts"))
    for tool in TOOLS:
        nodes.append(task("native-" + tool, ["scope"], deliverable="Real supported and negative native controls; retain supported scope"))
    for q in QUESTIONS:
        nodes.append(task("qualify-" + q, ["sources", "runtime", "product", "legal-" + q], questions=[q],
                          deliverable="Original-input capacity, schema and per-question source-backed qualification requests"))
    nodes.append(task("campaign", after=["qualify-" + q for q in QUESTIONS] + ["native-" + t for t in TOOLS],
                      deliverable="Counted campaign, fixed rules, exact commands and explicit unqualified arms"))
    nodes.append(task("live-approval", ["campaign"], agent=True,
                      deliverable="User approval of the concrete model/call/time proposal, separately from host rules"))
    for q in QUESTIONS:
        nodes.append(task("acquire-" + q, ["qualify-" + q, "live-approval"], agent=True, questions=[q],
                          deliverable="Actual two-reader acquisition, bridges and actual-population re-budget"))
        nodes.append(task("baseline-" + q, ["acquire-" + q], agent=True, questions=[q],
                          deliverable="Complete baseline product answer with valid fresh source review"))
        for tool in TOOLS:
            nodes.append(task(f"tool-{q}-{tool}", ["acquire-" + q, "native-" + tool], agent=True, questions=[q],
                              deliverable="Actual product candidate, native feedback, downstream account and fresh review"))
            nodes.append(task(f"compare-{q}-{tool}", ["baseline-" + q], after=[f"tool-{q}-{tool}"], agent=True, questions=[q],
                              deliverable="Valid matched effect or explicit invalid-comparison reason; no forced positive result"))
    nodes.append(task("release-review", after=[n["id"] for n in nodes], agent=True,
                      deliverable="Separate engineering, individual tool and original-question acceptance, residual owners and evidence"))
    now = datetime.now(timezone.utc)
    program = {"profile": "legal-mission-execution.v1", "workers": 2,
        "deadline_utc": (now + timedelta(days=7)).isoformat(),
        "local_deadline_only": True, "prior_detours": 18, "historical_charged_calls": 41,
        "global_call_ceiling": 0, "artifact_directory": str(BASE),
        "protected_evidence": [ref(ROOT, PLAN), ref(ROOT, CONTRACT), ref(ROOT, directory / "baseline.json")],
        "tasks": nodes}
    save(ROOT / PROGRAM, program)
    rules = "# Fixed integration-master actions; live spending still requires its separate grant.\n"
    for action in (*LOCAL_ACTIONS, "live"):
        rules += 'prefix_rule(pattern=[".venv-context/bin/python", "scripts/legal_integration_master.py", "' + action + '"], decision="allow")\n'
    (ROOT / RULES).write_text(rules)
    mission["integration_master"] = {"profile": "legal-integration-master-registration.v1",
        "program": ref(ROOT, PROGRAM), "plan": ref(ROOT, PLAN), "contract": ref(ROOT, CONTRACT),
        "baseline": ref(ROOT, directory / "baseline.json"), "prior_detours": 18,
        "additional_consolidated_revision": 1, "historical_calls": 41,
        "local_authorization": "User requested create, review and execute the complete integration master on 2026-10-13",
        "live_authorization": "SEPARATE_CONCRETE_APPROVAL_REQUIRED"}
    mission["history"].append({"id": "integration-master-register-2026-10-13", "task_id": "product-contribution",
        "kind": "product_evaluation", "outcome": "no_advance", "decision": "Registered the complete integration master with independent dependencies and unchanged closure criteria.",
        "next_task": "product-contribution", "next_task_reason": "Execute ready master branches; retain all historical evidence and resources.",
        "recorded_at_utc": now.isoformat(), "result_evidence": [ref(ROOT, PROGRAM), ref(ROOT, directory / "baseline.json")]})
    mission["next_task_reason"] = mission["history"][-1]["next_task_reason"]
    control.validate(mission, read(ROOT / DOC / "tools.json"))
    save(ROOT / DOC / "mission.json", mission)
    return summary()


def sources():
    from legalmath.canonical import digest as canonical_digest
    from legalmath.interpretation.assurance.answer_acceptance import reading_quote_locations, validate_manifest
    from legalmath.interpretation.assurance.legal_locators import build_index, retained_html
    envelope = read(ROOT / PRIOR / "regulatory-qualified-envelope.json")
    gatecoin = read(ROOT / PRIOR / "gatecoin-source-packet.json")
    qualification = read(ROOT / PRIOR / "gatecoin-source-qualification.json")
    packet = envelope["source_packet"]
    packet["units"] += gatecoin["units"]
    packet["dependencies"] += gatecoin["dependencies"]
    packet["selected_slice"] = "\n\n".join(q["text"] for q in envelope["original_questions"])
    packet["source_key"] = "bounded.combined.original-corpus"
    require(len(packet["units"]) == len({u["unit_id"] for u in packet["units"]}), "Duplicate combined source ID")
    envelope["source_qualification"]["limitations"] += qualification["limitations"]
    envelope["source_qualification"]["details"]["gatecoin"] = qualification["details"]
    envelope["source_qualification"]["evidence"] += qualification["evidence"]
    envelope["source_qualification"]["source_packet_hash"] = canonical_digest(packet)
    for evidence in envelope["source_qualification"]["evidence"]: verify(ROOT, evidence)
    envelope["legal_indexes"] = [build_index(packet, retained_html(d["source"], ROOT),
        source_ref=d["source"], unit_ids=d["unit_ids"], root=ROOT,
        numbering_profile=d.get("numbering_profile", "ordered-lists"))
        for d in envelope["answer_acceptance"]["source_documents"]]
    envelope["answer_acceptance"]["current_quote_locations"] = reading_quote_locations(envelope["answer_acceptance"], packet)
    envelope["binding"] = {"profile": "bounded-combined-corpus.v1", "predecessors": [
        ref(ROOT, PRIOR / "regulatory-qualified-envelope.json"), ref(ROOT, PRIOR / "gatecoin-source-packet.json")],
        "source_packet_hash": canonical_digest(packet)}
    envelope["binding_hash"] = canonical_digest(envelope["binding"])
    validate_manifest(envelope["answer_acceptance"], envelope["original_questions"], ROOT)
    save(ROOT / BASE / "combined-envelope.json", envelope)
    return {"units": len(packet["units"]), "questions": len(envelope["original_questions"]),
            "obligations": len(envelope["answer_acceptance"]["acceptance_obligations"]),
            "readings": len(envelope["answer_acceptance"]["original_readings"]),
            "corpus_status": "COMBINED_RETAINED_DERIVATIVES; RENDERING_EDITION_CURRENT_LAW_UNQUALIFIED"}


def run_tests(names, directory):
    command = [str(ROOT / ".venv-context/bin/python"), "-m", "pytest", "-q", *names]
    started = time.monotonic()
    process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=600)
    (directory / "tests.log").write_text(process.stdout + process.stderr)
    result = {"command": command, "exit_code": process.returncode, "wall_seconds": time.monotonic() - started}
    save(directory / "test-result.json", result)
    require(process.returncode == 0, "Focused tests failed; inspect retained tests.log")
    return result


def native(tool, directory):
    from scripts.legal_independent_tools import IndependentProductToolBackend
    from legalmath.interpretation.assurance.arguments import evaluate_criticism
    original = Path("artifacts/legal-mission-control/2026-10-09/continuation/product-contribution/reviewed/prepared.json")
    prepared = read(ROOT / original)
    backend = IndependentProductToolBackend([tool])
    packet, candidates = prepared["packet"], prepared["candidates"]
    if tool == "bm25":
        output = {qid: backend.retrieval(packet, {"question": question}, directory / qid)
                  for qid, question in prepared["questions"].items()}
    elif tool in ("legalruleml", "logical-english"):
        output = backend.candidates(packet, candidates, directory / "formal")
    else:
        output = {}
        for name in ("questioned", "assumed", "false-supported", "undercut"):
            proposal = prepared["proposals"][name]
            evaluation = evaluate_criticism(proposal, packet, list(candidates))
            output[name] = backend.criticism(packet, {"proposal": proposal, "evaluation": evaluation}, directory / name)
    save(directory / "native.json", {"tool": tool, "output": output, "identity": backend.identity(),
         "source": ref(ROOT, original), "scope": "Retained supplied conditional controls, not product-discovered warrants"})
    def failed(value):
        if isinstance(value, dict):
            return value.get("status") == "FAILED" or any(failed(v) for v in value.values())
        if isinstance(value, list): return any(failed(v) for v in value)
        return False
    require(not failed(output), "Native adapter failed a retained control")
    return {"tool": tool, "native_controls": "PASS", "full_evaluation": False}


def qualify(question, directory):
    from legalmath.interpretation.assurance.bounded_context import ContextRoute, tokenizer, citation_dependencies
    envelope = read(ROOT / BASE / "combined-envelope.json")
    route = ContextRoute(envelope, tokenizer(ROOT / TOKENIZER))
    packets, blocked = route.reading_plan()
    dependencies, unresolved = citation_dependencies(envelope)
    bridges, failed = route.dependency_packets(dependencies)
    q = next(q for q in envelope["original_questions"] if q["question_id"] == question)
    hits = route.retrieve(q["text"])
    requests = [route.make_packet("READ_SOURCE", hits["record_ids"][i:i+4],
                                 question_ids=[question], reader="canary")
                for i in range(0, len(hits["record_ids"]), 4)]
    save(directory / "canary.json", {"packets": requests,
        "selected_source_ids": hits["record_ids"], "all_selected_sources_retained": True})
    result = {"question": question, "input_hash": route.input_hash, "units": len(route.units),
        "chunks": sum(r["kind"] == "source" for r in route.records.values()),
        "reading_requests": len(packets), "bridge_requests": len(bridges),
        "blocked": blocked + failed + unresolved, "local_canary_measurements": [r['measurement'] for r in requests],
        "live_qualified": False, "service_tokenizer": "UNKNOWN; LOCAL_CL100K_ESTIMATE_ONLY"}
    save(directory / "qualification.json", result)
    require(not result["blocked"], "Some combined-corpus source dependencies remain unresolved")
    return result


def approval_packet(directory):
    if read(ROOT / PROGRAM).get('execution_refresh'):
        path = BASE / 'current-binding.json'
        require((ROOT/path).exists(), 'Current binding package has not completed')
        value = read(ROOT/path)
        return {'dispatch_ready':True,'scope':'Current semantic preflight; own-question acquisition remains gated',
                'maximum_calls':value['maximum_calls'],'proposal':ref(ROOT,path),
                'command':'.venv-context/bin/python scripts/legal_integration_master.py live'}
    if read(ROOT / PROGRAM).get('substantive_continuation_revision'):
        from scripts.legal_integration_post_review import approval_packet as current_packet
        return current_packet()
    from scripts.legal_integration_campaign import prepare as prepare_campaign
    return prepare_campaign()


def worker(tid):
    execution = MasterExecution(ROOT, PROGRAM, STATE)
    with execution.locked() as state:
        saved = state["tasks"][tid]
        require(saved["status"] == "RUNNING", "Worker needs scheduler reservation")
        attempt = len(saved["attempts"])
    directory = ROOT / BASE / tid / f"attempt-{attempt}"
    directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    status = "SUCCEEDED"
    try:
        reopening = execution.program.get('reviewed_reopening')
        if execution.program.get('repair_execution') and tid in ('current-binding', 'continuation-review'):
            from scripts import legal_integration_repair_execution as repair
            value = {'current-binding': repair.prepare, 'continuation-review': repair.verification}[tid](directory)
        elif execution.program.get('complete_account_capacity_repair') and tid in ('current-binding', 'campaign', 'continuation-review'):
            from scripts import legal_integration_complete_account_capacity as capacity
            value = {'current-binding': capacity.prepare, 'campaign': capacity.campaign,
                'continuation-review': capacity.verification}[tid](directory)
        elif execution.program.get('account_reconstruction_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_account_reconstruction import prepare as reconstruction_prepare, verification
            value = reconstruction_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('account_instruction_repair') and tid in ('current-binding', 'campaign', 'continuation-review'):
            from scripts import legal_integration_account_instruction_repair as instructions
            handlers = {'current-binding': instructions.prepare, 'campaign': instructions.campaign,
                'continuation-review': instructions.verification}
            value = handlers[tid](directory)
        elif execution.program.get('qualification_continuation') and tid in ('current-binding', 'corpus-qualification', 'campaign', 'continuation-review'):
            from scripts import legal_integration_qualification_continuation as continuation
            handlers = {'current-binding': continuation.prepare, 'corpus-qualification': continuation.corpus,
                'campaign': continuation.campaign, 'continuation-review': continuation.verification}
            value = handlers[tid](directory)
        elif execution.program.get('lossless_account_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_lossless_repair import prepare as lossless_prepare, verification
            value = lossless_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('response_schema_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_schema_repair import prepare as schema_prepare, verification
            value = schema_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('account_capacity_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_account_repair import prepare as account_prepare, verification
            value = account_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('route_context_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_route_repair import prepare as route_prepare, verification
            value = route_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('phased_acquisition_repair') and tid in ('current-binding', 'continuation-review'):
            from scripts.legal_integration_phased_live import prepare as phased_prepare
            from scripts.legal_integration_phased_repair import verification
            value = phased_prepare(directory) if tid == 'current-binding' else verification(directory)
        elif execution.program.get('execution_refresh'):
            from scripts.legal_integration_execution_refresh import worker as refresh_worker
            value = refresh_worker(tid, directory)
        elif execution.program.get('substantive_continuation_revision'):
            from scripts.legal_integration_substantive_continuation import worker as substantive_worker
            value = substantive_worker(tid, directory)
        elif execution.program.get('remaining_work_revision'):
            from scripts.legal_integration_remaining import worker as remaining_worker
            value = remaining_worker(tid, directory)
        elif execution.program.get('acceptance_revision'):
            from scripts.legal_integration_acceptance_revision import worker as acceptance_worker
            value = acceptance_worker(tid, directory)
        elif reopening and (tid == 'sources' or tid.startswith('qualify-')):
            from scripts.legal_integration_reopening import local_node
            value = local_node(tid, directory)
        elif reopening and tid == 'campaign':
            from scripts.legal_integration_reopening_live import prepare_binding
            value = prepare_binding()
        elif tid == "scope":
            from scripts.legal_mission_control import ANCHORS
            for path, sha in ANCHORS.values(): verify(ROOT, {"path": path, "sha256": sha})
            value = {"contract": ref(ROOT, CONTRACT), "originals": list(ANCHORS), "selected_tools": list(TOOLS),
                     "claims": "Engineering qualification, tool contribution and legal handling remain separate"}
        elif tid == "sources": value = sources()
        elif tid == "runtime":
            value = run_tests(["tests/assurance/test_bounded_product.py", "tests/tooling/test_integration_master.py",
                              "tests/tooling/test_integration_campaign.py", "tests/assurance/test_master_reopening.py"], directory)
        elif tid == "product":
            value = run_tests(["tests/assurance/test_bounded_product.py", "-k",
                              "not (resume or dispatch or campaign)"], directory)
        elif tid.startswith("legal-"):
            q = tid[6:]
            names = {"p10": "p10-standard", "p14": "p14-attachment", "evidence": "p10-effective-mitigation", "gatecoin": "gatecoin-transfer"}
            notes = [DOC / "results" / (names[q] + ".md"), PRIOR / "conditional-source-bank.json",
                     PRIOR / "individual-statement-review.json"]
            value = {"question": q, "provisional_reference": [ref(ROOT, p) for p in notes],
                "legal_disposition": "OPEN", "client_facts": "UNKNOWN",
                "acceptance": "Conditional conclusions, source warrants, strongest rivals, exact missing premises; no bare unknown",
                "research_remaining": "Complete corpus qualification and dated applicability/later-treatment review"}
        elif tid.startswith("native-"): value = native(tid[7:], directory)
        elif tid.startswith("qualify-"): value = qualify(tid[8:], directory)
        elif tid == "campaign": value = approval_packet(directory)
        else: raise ValueError("No fixed worker for task")
        status = value.pop('_node_status', 'SUCCEEDED')
        conclusion = value.pop('_conclusion', tid + " local deliverable retained; no legal or complete-tool acceptance inferred.")
        save(directory / "evidence.json", value)
    except Exception as exc:
        status = "FAILED"
        value = {"error": getattr(exc, "code", type(exc).__name__), "details": str(getattr(exc, "details", None) or exc)}
        save(directory / "failure.json", value)
        conclusion = tid + " failed: " + value["details"][:500]
    evidence = [ref(ROOT, directory / p) for p in ("evidence.json", "failure.json") if (directory / p).exists()]
    result = {"task_id": tid, "status": status, "conclusion": conclusion,
        "next_action": "Continue independent ready master nodes; review failures against their acceptance criteria.",
        "evidence": evidence, "command": ".venv-context/bin/python scripts/legal_integration_master.py worker " + tid,
        "environment": sys.executable, "devices": "CPU only; CUDA_VISIBLE_DEVICES=-1", "seeds": "N/A: deterministic local work",
        "wall_seconds": time.monotonic() - started, "plan": str(PLAN), "legal_acceptance": False}
    save(directory / "result.json", result)
    return result


def install_rules():
    # This is the single protected-path mutation, invoked only with escalation.
    target = Path.home() / ".codex/rules/legalmath-integration-master.rules"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(target.read_bytes() == (ROOT / RULES).read_bytes(), "Different existing master rules; review before replacement")
    else:
        target.write_bytes((ROOT / RULES).read_bytes())
    return {"installed": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=[*LOCAL_ACTIONS, "worker", "install-rules", "live", "approve-and-run"])
    parser.add_argument("task", nargs="?")
    args = parser.parse_args()
    require((args.action == "worker") == bool(args.task), "Only worker accepts a registered task")
    if args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('repair_execution'):
        from scripts.legal_integration_repair_execution import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('complete_account_capacity_repair'):
        from scripts.legal_integration_complete_account_capacity import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('account_reconstruction_repair'):
        from scripts.legal_integration_account_reconstruction import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('account_instruction_repair'):
        from scripts.legal_integration_account_instruction_repair import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('qualification_continuation'):
        from scripts.legal_integration_qualification_continuation import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('lossless_account_repair'):
        from scripts.legal_integration_lossless_repair import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('response_schema_repair'):
        from scripts.legal_integration_schema_repair import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('execution_refresh'):
        from scripts.legal_integration_execution_refresh import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('substantive_continuation_revision'):
        from scripts.legal_integration_substantive_verify import check
        result = check()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('remaining_work_revision'):
        from scripts.legal_integration_remaining import verify_repairs
        result = verify_repairs()
    elif args.action == "prepare": result = prepare()
    elif args.action == "worker": result = worker(args.task)
    elif args.action in ("check", "status"): result = summary()
    elif args.action == "install-rules": result = install_rules()
    elif args.action == "approval-packet": result = approval_packet(ROOT / BASE)
    elif args.action == "verify":
        result = run_tests(["tests/assurance/test_bounded_product.py", "tests/tooling/test_integration_master.py",
            "tests/tooling/test_integration_campaign.py",
            "tests/assurance/test_dossier_answer.py", "tests/assurance/test_integration_repair_product.py",
            "tests/assurance/test_completion_contract.py", "tests/assurance/test_integration_completion.py"], ROOT / BASE)
    elif args.action in ("live", "approve-and-run"):
        from scripts.legal_integration_campaign import live, approve
        if args.action == "approve-and-run": approve()
        result = live()
    else:
        result = MasterExecution(ROOT, PROGRAM, STATE).run()
        if read(ROOT / PROGRAM).get('repair_execution'):
            from scripts.legal_integration_repair_execution import verification
            verification()
        elif read(ROOT / PROGRAM).get('complete_account_capacity_repair'):
            from scripts.legal_integration_complete_account_capacity import verification
            verification()
        elif read(ROOT / PROGRAM).get('account_reconstruction_repair'):
            from scripts.legal_integration_account_reconstruction import verification
            verification()
        elif read(ROOT / PROGRAM).get('account_instruction_repair'):
            from scripts.legal_integration_account_instruction_repair import verification
            verification()
        elif read(ROOT / PROGRAM).get('qualification_continuation'):
            from scripts.legal_integration_qualification_continuation import verification
            verification()
        elif read(ROOT / PROGRAM).get('lossless_account_repair'):
            from scripts.legal_integration_lossless_repair import verification
            verification()
        elif read(ROOT / PROGRAM).get('response_schema_repair'):
            from scripts.legal_integration_schema_repair import verification
            verification()
        elif read(ROOT / PROGRAM).get('execution_refresh'):
            from scripts.legal_integration_execution_refresh import verification
            verification()
        elif read(ROOT / PROGRAM).get('substantive_continuation_revision') and not result['ready'] and not result['running']:
            from scripts.legal_integration_post_review import settle
            settle()
        elif read(ROOT / PROGRAM).get('remaining_work_revision') and not result['ready'] and not result['running']:
            from scripts.legal_integration_remaining import settle
            settle()
        elif read(ROOT / PROGRAM).get('acceptance_revision') and not result['ready'] and not result['running']:
            from scripts.legal_integration_acceptance_revision import settle
            settle()
    if args.action in ('check', 'status', 'prepare', 'run', 'live', 'approve-and-run') and 'tasks' in result:
        result = current_qualification_view(ROOT, read(ROOT / PROGRAM), result)
        from collections import Counter
        result = {key: result[key] for key in ('execution', 'ready', 'running', 'blocked') if key in result} | {
            'task_counts': dict(Counter(row['status'] for row in result['tasks'].values())),
            'full_state': str(STATE), 'mission_complete': False}
    elif args.action == 'approval-packet':
        result = {key: result[key] for key in ('dispatch_ready', 'maximum_calls', 'window_seconds', 'routing',
                                               'command', 'resume_command', 'installation_target', 'scope',
                                               'remaining_calls', 'all_branch_maximum', 'blockers', 'proposal') if key in result}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    expected = ROOT / ".venv-context/bin/python"
    if Path(sys.prefix).resolve() != (ROOT / ".venv-context").resolve():
        os.execv(str(expected), [str(expected), str(Path(__file__).resolve()), *sys.argv[1:]])
    main()
