#!/usr/bin/env python3
"""Audited supplemental assurance execution; all model calls share one 100-call ledger."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CODE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(CODE/"src"), str(CODE/"scripts")]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Settings, commitment
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.assurance import supplemental_repair as repair
from legalmath.interpretation.assurance import challenge_contract as contract
from legalmath.interpretation.assurance.diversity import save

BASE = Path("artifacts/assurance-gap-continuation/2026-10-01")
OLD = Path("artifacts/assurance-gap-closure/2026-09-30")
ROLES = ("structure-reader", "exception-challenger")
PLAN = "docs/plans/assurance-gap-continuation-100-calls.md"


def read(path):
    # Operational receipts contain measured fractional seconds. Model proposals
    # still enter through the provider canonical parser and their strict schema.
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise LegalMathError("E_INTEGRITY", details="Duplicate receipt field")
            value[key] = item
        return value
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(LegalMathError("E_SCHEMA")))


def receipt(path, repo):
    p = Path(path)
    return {"path": str(p.relative_to(repo)), "sha256": raw_digest(p.read_bytes())}


def verified(ref, repo):
    p = repo/ref["path"]
    if raw_digest(p.read_bytes()) != ref["sha256"]:
        raise LegalMathError("E_INTEGRITY", details="Baseline receipt changed: "+ref["path"])
    return read(p)


def prepare(repo):
    out = repo/BASE
    if (out/"authorization.json").exists():
        return status(repo)
    prior = read(repo/OLD/"G7r/attempt-01/recovery-result.json")
    panel = verified(prior["recovered_panel"], repo)
    original = verified(prior["historical_predecessor"], repo)
    packet = verified(original["packet"], repo)
    candidates = verified(original["candidates"], repo)
    questions = {r["candidate_id"]: r["question"] for r in original["questions"]["assignments"]}
    baseline_candidates = deepcopy(candidates)
    baseline_questions = deepcopy(questions)
    alternative_records = []
    for i, row in enumerate(panel["alternative_readings"]):
        r = row["reading"]
        cid = "alternative."+str(i).zfill(3)+"."+commitment(r)[:16]
        candidates[cid] = deepcopy(r)
        q = {"control_id": "control."+cid,
             "question": "Under paragraph 10 and footnote 1 of the 20 April 2026 edition of 26EC22, what follows under this proposed reading: "+r["statement"],
             "unit_of_assessment": "One identified provider, product, tokenisation arrangement and explicitly identified assessment period.",
             "actor": "The independently identified Product Provider.",
             "temporal_basis": "20 April 2026 source edition; the actual assessment period and ongoing applicability must be independently established.",
             "result_kind": "REQUIREMENT_SATISFIED",
             "true_means": "The proposed reading predicate holds under its explicitly declared facts and assumptions; source entailment is not established.",
             "false_means": "That proposed predicate fails under the same declared facts and assumptions; this does not itself establish legal breach.",
             "source_evidence": r["citations"]}
        questions[cid] = q
        alternative_records.append({"record_index": i, "candidate_id": cid,
            "substantive_hash": commitment(r), "original_record": row})
    rebuilt = contract.build(packet, baseline_candidates, baseline_questions)
    if rebuilt != panel["contract"]:
        raise LegalMathError("E_INTEGRITY", details="Baseline obligation denominator changed")
    for h in panel["history"]:
        if h["status"] == "VALIDATED":
            contract.validate_response(h["value"], rebuilt, packet, h["selected"])
    out.mkdir(parents=True, exist_ok=False)
    checkpoints = out/"predecessors"
    checkpoints.mkdir()
    refs = []
    files = {"recovery-result.json": repo/OLD/"G7r/attempt-01/recovery-result.json",
             "panel.json": repo/prior["recovered_panel"]["path"],
             "dossier.json": repo/prior["historical_predecessor"]["path"],
             "delivery.json": repo/OLD/"delivery.json",
             "old-grant.json": repo/"artifacts/assurance-new-grant/2026-09-29/grant.json",
             "old-arm.json": repo/"artifacts/assurance-new-grant/2026-09-29/gap-closure-allowance.json"}
    grant = read(files["old-grant.json"])
    files["old-ledger.json"] = files["old-grant.json"].parent/grant["ledger"]
    files["plan.md"] = repo/PLAN
    for name, p in files.items():
        target = checkpoints/name
        shutil.copyfile(p, target)
        refs.append({"path": str(target.relative_to(out)), "sha256": raw_digest(target.read_bytes())})
    inventory = {"profile": repair.PROFILE, "source_packet_hash": digest(packet),
        "source_edition": "2026-04-20", "source_date_evidence": [
            u for u in packet["units"] if u["text"] in ("20 Apr 2026", "Revised on 20 April 2026")],
        "baseline": {name: receipt(p, repo) for name, p in files.items()},
        "original_candidates": list(baseline_candidates), "all_reading_records": list(candidates),
        "original_obligations": rebuilt["obligations"],
        "missing_perspectives": panel["missing_perspectives"],
        "unresolved_obligation_ids": panel["unresolved_obligation_ids"],
        "response_differences": panel["response_differences"],
        "failed_actions": panel["failed_actions"],
        "alternative_records": alternative_records,
        "original_issue_histories": panel["issue_histories"],
        "duplicate_substantive_groups": {},
        "new_calls": 0, "legal_correctness": "NOT_ESTABLISHED"}
    groups = {}
    for row in alternative_records:
        groups.setdefault(row["substantive_hash"], []).append(row["candidate_id"])
    inventory["duplicate_substantive_groups"] = {k:v for k,v in groups.items() if len(v)>1}
    save(out/"inventory.json", inventory)
    save(out/"context.json", {"packet": packet, "candidates": candidates, "questions": questions,
        "original_candidates": baseline_candidates, "original_questions": baseline_questions,
        "contract": rebuilt})
    for name in ("inventory.json", "context.json"):
        refs.append({"path": name, "sha256": raw_digest((out/name).read_bytes())})
    allowed = []
    for role in ROLES:
        for o in rebuilt["obligations"]:
            allowed.extend(phase+"."+role+"."+o["obligation_id"] for phase in ("coverage", "integration"))
        allowed.extend("assessment."+role+"."+commitment(r) for r in candidates.values())
        allowed.extend("authority."+role+"."+str(i) for i in range(6))
    now = datetime.now(timezone.utc)
    auth = {"profile": repair.PROFILE, "authorization_id": "user.2026-10-01.assurance100",
        "authorization": "propose a plan to handle these problems. you have 100 calls more. Review the plan thoroughly and execute",
        "maximum": 100, "ledger": "allowance.json", "starts_at": now.isoformat(),
        "ends_at": (now+timedelta(hours=24)).isoformat(),
        "maximum_new_attempts_per_issue": 2, "phase_limits": repair.PHASE_LIMITS,
        "repair_reserve": 16, "allowed_issues": sorted(set(allowed)),
        "predecessors": refs, "previous_spending": {"shared": 78, "old_repair_arm": 45},
        "history_policy": "Original start times, failures and counts retained in inventory. New explicit 24-hour supplemental window; two additional attempts per substantive task/role. No old quota reset."}
    save(out/"authorization.json", auth)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    save(out/"run-manifest.json", {"git_commit": commit, "plan": receipt(repo/PLAN, repo),
        "environment": str(repo/".venv/bin/python"), "cpu_only": True,
        "gpu_policy": "CUDA_VISIBLE_DEVICES=-1", "data": receipt(out/"context.json", repo),
        "randomness": "Remote generation uncontrolled; local checks deterministic.",
        "started_at": now.isoformat(), "authorization": receipt(out/"authorization.json", repo),
        "study_class": "RETAINED_DEVELOPMENT_CONTINUATION", "future_observation": False})
    return status(repo)


def tasks_for(repo, phase):
    out = repo/BASE
    context = read(out/"context.json")
    inventory = read(out/"inventory.json")
    packet = context["packet"]
    if phase in ("coverage", "integration"):
        for role in ROLES:
            if phase == "coverage":
                selected = [r["obligation_id"] for r in inventory["missing_perspectives"] if role in r["roles"]]
            else:
                selected = integration_selected(repo)
            groups = [selected[i:i+12] for i in range(0,len(selected),12)] if phase == "coverage" else integration_groups(repo, selected)
            for group in groups:
                request = contract.request(context["contract"], packet, context["original_candidates"],
                    context["original_questions"], group, role)
                request["instructions"] += (
                    " The source edition is 20 April 2026. Copy all supplied hashes exactly. "
                    "This completes retained research; no response establishes legal truth. "
                    "Keep rationale concise. Do not repeat an existing reading as a new alternative. "
                    "For missing external standards retain a precise unresolved question."
                )
                if phase == "integration":
                    request["new_evidence"] = integration_evidence(repo, group)
                    request["instructions"] += " Reconsider the selected obligations using the actual new evidence, including formal witnesses and disputed premises; explain remaining uncertainty."
                schema = contract.ChallengeResponse.model_json_schema()
                schema["properties"]["binding_hash"]["enum"] = [context["contract"]["binding_hash"]]
                schema["properties"]["answers"].update(minItems=len(group), maxItems=len(group))
                schema["$defs"]["ChallengeAnswer"]["properties"]["obligation_id"]["enum"] = group
                issues = [phase+"."+role+"."+oid for oid in group]
                yield role, group, issues, request, schema
    elif phase == "assessment":
        ids = list(context["candidates"])
        for offset in range(0, len(ids), 2):
            group = ids[offset:offset+2]
            for role in ROLES:
                identity = {"phase": phase, "role": role, "packet": digest(packet),
                            "selected": {k: commitment(context["candidates"][k]) for k in group},
                            "inventory": digest(context["candidates"]), "questions": digest(context["questions"])}
                request = {"task": "SOURCE_BOUND_READING_ASSESSMENT",
                    "binding_hash": digest(identity), "source_packet": packet,
                    "candidates": context["candidates"], "questions": context["questions"],
                    "selected_readings": identity["selected"], "role": role,
                    "instructions": (
                        "Assess every selected reading against all nine dimensions: actor, scope, quantifier, "
                        "negation, exception, time, definition, authority, output. Read the complete source and "
                        "all retained reading context. The source is the 20 April 2026 edition. "
                        "Structure-reader reconstructs the strongest precise reading; exception-challenger "
                        "seeks omitted conditions, changed meaning, unsupported inferences and alternative explanations. "
                        "The two first assessments are blind to each other. These are source-bound proposals, not legal grades. "
                        "For each selected reading propose a useful conditional Boolean formalization when its logical "
                        "structure permits it, preserving unresolved legal/factual classifications. Do not encode the "
                        "conclusion itself as one unexplained compliance Boolean. If no faithful finite abstraction "
                        "is supportable, formalization must be null, premises empty and unresolved_questions explicit. "
                        "Use one to eight Boolean facts, operators and/or/not/if/= and literal true/false. "
                        "Facts need exact meanings, scope/period/units and existing source-unit anchors. "
                        "Preserve the original statement, assumptions and uncertainties; record added assumptions. "
                        "A formalization needs at least two independently justified source-anchored test obligations, "
                        "including expected true and false, whose when guards include the scope and are satisfiable. "
                        "Do not invent predicates or tautologies merely to obtain a pass. A conditional counterexample "
                        "may reject a proposed program without deciding the source meaning. "
                        "Return exactly one assessment per selected ID and all nine dimensions. Copy supplied hashes; "
                        "literal exact quotations only. Keep each explanation short. Related readings remain proposals "
                        "of relationship, never automatic merging. Propose a new reading only if substantively absent "
                        "from every retained reading; otherwise reference the existing ID."
                    )}
                schema = repair.AssessmentResponse.model_json_schema()
                schema["properties"]["binding_hash"]["enum"] = [request["binding_hash"]]
                schema["properties"]["assessments"].update(minItems=len(group), maxItems=len(group))
                schema["$defs"]["Assessment"]["properties"]["reading_id"]["enum"] = group
                issues = ["assessment."+role+"."+commitment(context["candidates"][cid]) for cid in group]
                yield role, group, sorted(set(issues)), request, schema
    else:
        from assurance_gap_authorities import authority_tasks
        yield from authority_tasks(repo, context)


def integration_selected(repo):
    out = repo/BASE
    baseline = read(out/"predecessors/panel.json")
    latest = deepcopy(baseline["latest"])
    for p in sorted((out/"tasks").glob("coverage.*/attempt-*/result.json")):
        row=read(p)
        if row["status"]=="VALIDATED":
            for answer in row["value"]["answers"]:
                latest[row["role"]][answer["obligation_id"]]=answer
    return [o["obligation_id"] for o in baseline["contract"]["obligations"] if any(
        o["obligation_id"] not in latest[role] or latest[role][o["obligation_id"]]["status"]!="PROPOSED_SUPPORTED"
        or latest[role][o["obligation_id"]]["followup_question"] for role in ROLES)]


def integration_groups(repo, selected):
    context=read(repo/BASE/"context.json")
    groups=[]; current=[]
    # Keep a reading's dimensions adjacent: this reduces repeated full
    # assessments per request without omitting any source, reading or question.
    owners={o["obligation_id"]:tuple(sorted(o["candidate_ids"])) for o in context["contract"]["obligations"]}
    ordered=sorted(selected,key=lambda oid:(owners[oid],oid))
    for oid in ordered:
        trial=[*current,oid]
        request=contract.request(context["contract"],context["packet"],context["original_candidates"],
            context["original_questions"],trial,"exception-challenger")
        request["new_evidence"]=integration_evidence(repo,trial)
        # Reserve bytes for the actual instructions appended by tasks_for.
        fits=len(canonical(repair.encode(request)))<=198000
        if current and (len(trial)>8 or not fits):
            groups.append(current);current=[oid]
        else:current=trial
    if current:groups.append(current)
    if len(groups)*2>repair.PHASE_LIMITS["integration"]:
        raise LegalMathError("E_RESOURCE_LIMIT",details="Integration partition exceeds reviewed call allocation")
    return groups


def integration_evidence(repo, group):
    out = repo/BASE
    context = read(out/"context.json")
    cids = {cid for o in context["contract"]["obligations"] if o["obligation_id"] in group for cid in o["candidate_ids"]}
    rows = []
    for p in sorted((out/"tasks").glob("assessment.*/attempt-*/result.json")):
        row = read(p)
        if row["status"] != "VALIDATED":
            continue
        for a in row["value"]["assessments"]:
            if a["reading_id"] in cids:
                formal = repair.formal_evidence(context["packet"], context["candidates"][a["reading_id"]],
                    context["questions"][a["reading_id"]], a)
                rows.append({"role": row["role"], "assessment": a, "formal_certificate": formal["certificate"]})
    authority = read(out/"integration-authority-evidence.json") if (out/"integration-authority-evidence.json").exists() else read(out/"authority-summary.json") if (out/"authority-summary.json").exists() else None
    return {"reading_assessments": rows, "authority_evidence": authority,
            "qualification": "Source entailment and actual legal/factual classifications remain unproved."}


def integration_citation_packet(repo, request, packet):
    evidence=request.get("new_evidence",{}).get("authority_evidence")
    if not evidence:return packet
    ref=evidence["complete_reviewed_context"]
    path=(repo/ref["path"]).resolve()
    if not path.is_relative_to(repo.resolve()) or raw_digest(path.read_bytes())!=ref["sha256"]:
        raise LegalMathError("E_INTEGRITY",details="Attached authority context changed")
    authority=read(path)
    units={u["unit_id"]:u for u in authority["units"]}
    if len(units)!=len(authority["units"]):
        raise LegalMathError("E_REFERENCE",details="Duplicate authority source identities")
    declared=evidence["quoted_source_unit_metadata"]
    original_ids={u["unit_id"] for u in packet["units"]}
    if original_ids.intersection(declared) or not set(declared)<=set(units):
        raise LegalMathError("E_REFERENCE",details="Authority source identity collision")
    for uid,metadata in declared.items():
        source=(repo/metadata["source_locator"]).resolve()
        if (not source.is_relative_to(repo.resolve()) or metadata["source_locator"]!=units[uid]["locator"]
                or raw_digest(source.read_bytes())!=metadata["source_sha256"]):
            raise LegalMathError("E_INTEGRITY",details="Attached authority source bytes changed")
    extended=deepcopy(packet)
    extended["units"].extend(deepcopy(units[uid]) for uid in declared)
    return extended


def read_result(repo, path):
    row=read(path)
    recovery=path.with_name("offline-recovery.json")
    if not recovery.exists():return row
    data=read(recovery)
    if (row["phase"]!="integration" or row["status"]!="FAILED" or row.get("error")!="E_REFERENCE"
            or data["original_result_hash"]!=raw_digest(path.read_bytes())
            or data["request_hash"]!=row["request_hash"]):
        raise LegalMathError("E_INTEGRITY",details="Detached offline validation recovery")
    request=read(path.with_name("request.json"))
    checked=validator(repo,"integration",request,row["selected"])(row["rejected_value"])
    if digest(checked)!=data["checked_value_hash"]:
        raise LegalMathError("E_INTEGRITY",details="Recovered response changed")
    return {**row,"status":"VALIDATED","value":checked,
            "original_status":"FAILED","offline_recovery":receipt(recovery,repo),
            "provenance":{"allowance_slot":data["allowance_slot"]}}


def validator(repo, phase, request, selected):
    context = read(repo/BASE/"context.json")
    if phase in ("coverage", "integration"):
        packet=integration_citation_packet(repo,request,context["packet"]) if phase=="integration" else context["packet"]
        return lambda v: contract.validate_response(v, context["contract"], packet, selected)
    if phase == "assessment":
        return lambda v: repair.validate_assessment(v, request["binding_hash"], context["packet"], context["candidates"], selected)
    from assurance_gap_authorities import validate_authority
    return lambda v: validate_authority(repo, v, request)


def dispatch(repo, phase, role, selected, issues, request, schema, *, retry=False):
    out = repo/BASE
    task = phase+"."+role+"."+digest(sorted(issues))[:24]
    taskdir = out/"tasks"/task
    existing = sorted(taskdir.glob("attempt-*/result.json")) if taskdir.exists() else []
    for p in existing:
        previous = read_result(repo,p)
        if previous["status"] == "VALIDATED":
            validator(repo, phase, read(p.parent/"request.json"), previous["selected"])(previous["value"])
            # Count a source-selection repair as the same substantive task.
            old_request=read(p.parent/"request.json")
            changed_source=(phase=="authority" and
                digest(old_request["source_packet"])!=digest(request["source_packet"]))
            if not changed_source or not retry:
                return previous
    if existing and not retry:
        return read(existing[-1])
    if len(existing) >= 2:
        return read(existing[-1])
    if taskdir.exists() and list(taskdir.glob("attempt-*")) and len(existing) != len(list(taskdir.glob("attempt-*"))):
        raise LegalMathError("E_INTEGRITY", details="Interrupted task needs explicit recovery before dispatch")
    wire = repair.encode(request)
    if len(canonical(wire)) > 200000:
        raise LegalMathError("E_RESOURCE_LIMIT", details={"task": task, "encoded_bytes":len(canonical(wire)), "maximum":200000})
    attempt = taskdir/("attempt-"+str(len(existing)+1).zfill(2))
    if retry and existing:
        error = read(existing[-1])
        request = deepcopy(request)
        request["previous_rejected_output"] = {
            "error": error.get("error"), "details": error.get("details"),
            "response": error.get("rejected_value")}
        if phase=="authority" and error["status"]=="VALIDATED":
            request["previous_rejected_output"]={
                "error":"SOURCE_CONTEXT_REPAIRED",
                "details":"The operative Part IV and substantive Chapter 6 selections were repaired. Reassess the corrected source packet; preserve edition limits and still-open questions.",
                "response":error["value"],"previous_request_hash":error["request_hash"]}
        request["instructions"] += " This is the single counted correction attempt. Repair the precise rejected output error; recheck every identity, exact quote and formal premise."
        wire = repair.encode(request)
        if len(canonical(wire)) > 200000:
            raise LegalMathError("E_RESOURCE_LIMIT", details="Correction context exceeds input cap; no model dispatch")
    attempt.mkdir(parents=True, exist_ok=False)
    save(attempt/"request.json", request)
    save(attempt/"wire.json", wire)
    save(attempt/"schema.json", schema)
    save(attempt/"preflight.json", {"original_hash":digest(request), "wire_hash":digest(wire),
        "bytes":len(canonical(wire)), "exact_reconstruction":repair.decode(wire,digest(request))==request})
    allowance = repair.SupplementalAllowance(out/"authorization.json", task=task, phase=phase,
        issues=issues, repair=bool(existing))
    began = time.monotonic()
    record = {"task": task, "phase": phase, "role": role, "selected": selected,
        "request_hash":digest(request), "wire_hash":digest(wire), "status":"RUNNING",
        "started_at":datetime.now(timezone.utc).isoformat(), "before_calls":allowance.verify()["used"]}
    save(attempt/"started.json", record)
    value = None
    try:
        response = CodexProvider(allowance=allowance).complete(wire, schema,
            Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000))
        value = response.value
        checked = validator(repo, phase, request, selected)(value)
        record.update(status="VALIDATED", value=checked, provenance={
            k:v for k,v in response.provenance.items() if k!="events_jsonl"})
    except LegalMathError as exc:
        record.update(status="FAILED", error=exc.code, details=str(exc.details)[:4000], rejected_value=value)
        if exc.code in ("E_INTEGRITY","E_AUTHORITY"):
            save(attempt/"result.json", record)
            raise
    except BaseException as exc:
        record.update(status="INTERRUPTED", error=type(exc).__name__, details=str(exc)[:1000])
        raise
    finally:
        record["after_calls"] = allowance.verify()["used"]
        record["elapsed_seconds"] = str(round(time.monotonic()-began, 3))
        record["ended_at"] = datetime.now(timezone.utc).isoformat()
        save(attempt/"result.json", record)
    print(json.dumps({"task":task,"status":record["status"],"used":record["after_calls"]}), flush=True)
    return record


def preflight(repo, phases):
    out = repo/BASE
    rows = []
    for phase in phases:
        for role, selected, issues, request, schema in tasks_for(repo, phase):
            wire = repair.encode(request)
            rows.append({"phase":phase,"role":role,"selected":selected,
                "original_hash":digest(request),"wire_hash":digest(wire),"bytes":len(canonical(wire)),
                "fits":len(canonical(wire))<=200000,
                "exact":repair.decode(wire,digest(request))==request})
    path=out/("preflight-"+"-".join(phases)+".json")
    index=2
    while path.exists():
        path=out/("preflight-"+"-".join(phases)+"-"+str(index).zfill(2)+".json");index+=1
    save(path, rows)
    return {"requests":len(rows),"maximum_bytes":max((r["bytes"] for r in rows),default=0),
            "oversized":sum(not r["fits"] for r in rows),"new_model_calls":0}


def run(repo, phase, *, retry=False, limit=None, workers=1):
    from concurrent.futures import ThreadPoolExecutor
    if workers not in (1, 2):
        raise LegalMathError("E_RESOURCE_LIMIT", details="One or two bounded provider workers only")
    out = repo/BASE
    with (out/".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        rows = []
        failures = 0
        executed = 0
        scheduled = list(tasks_for(repo, phase))
        positions = {role: 0 for role in ROLES}
        ranked = []
        for item in scheduled:
            ranked.append((positions[item[0]], ROLES.index(item[0]), item))
            positions[item[0]] += 1
        scheduled = [item for _, _, item in sorted(ranked, key=lambda r:r[:2])]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for offset in range(0, len(scheduled), workers):
                batch = scheduled[offset:offset+workers]
                if limit is not None:
                    batch = batch[:max(0,limit-executed)]
                if not batch:
                    break
                before = repair.SupplementalAllowance(out/"authorization.json").verify()["used"]
                futures = [pool.submit(dispatch,repo,phase,*item,retry=retry) for item in batch]
                for future in futures:
                    result = future.result()
                    rows.append({"task":result["task"],"status":result["status"]})
                    failures = failures+1 if result.get("error")=="E_DEPENDENCY" else 0
                current = repair.SupplementalAllowance(out/"authorization.json").verify()
                executed += current["used"]-before
                save(out/(phase+"-progress.json"), {"rows":rows,"provider_failure_streak":failures,
                    "workers":workers,"allowance":current})
                if failures>=2 or (limit is not None and executed>=limit):
                    break
        return status(repo)


def status(repo):
    out = repo/BASE
    statuses = Counter()
    phases = {}
    for task in (out/"tasks").glob("*") if (out/"tasks").exists() else []:
        results = sorted(task.glob("attempt-*/result.json"))
        if results:
            r = read_result(repo,results[-1])
            statuses[r["status"]] += 1
            phases.setdefault(r["phase"], Counter())[r["status"]] += 1
    a = repair.SupplementalAllowance(out/"authorization.json").verify()
    return {"used":a["used"],"maximum":100,"tasks":dict(statuses),
        "phases":{k:dict(v) for k,v in phases.items()},"repair_calls":a["repair_calls"]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","preflight","run","status"])
    parser.add_argument("--repo",type=Path,default=CODE)
    parser.add_argument("--phase",choices=["coverage","assessment","authority","integration"])
    parser.add_argument("--retry",action="store_true")
    parser.add_argument("--limit",type=int)
    parser.add_argument("--workers",type=int,choices=[1,2],default=1)
    args=parser.parse_args()
    repo=args.repo.resolve()
    if args.action=="prepare": result=prepare(repo)
    elif args.action=="status": result=status(repo)
    elif args.action=="preflight": result=preflight(repo,[args.phase] if args.phase else ["coverage","assessment"])
    else:
        if not args.phase: parser.error("run requires --phase")
        result=run(repo,args.phase,retry=args.retry,limit=args.limit,workers=args.workers)
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
