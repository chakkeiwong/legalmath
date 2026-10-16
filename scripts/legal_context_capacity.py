"""Execute the reviewed local context integration; never dispatch model calls."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance.bounded_context import (
    Limits, citation_dependencies, tree_synthesis, require)
from legalmath.interpretation.search.providers import Completion
from scripts.legal_product_completion import prepare_bounded_context, run_bounded_context

BASE = ROOT/"artifacts/legal-mission-control/2026-10-12/context-integration"
PACKAGE = BASE
INPUT = ROOT/"artifacts/legal-mission-control/2026-10-12/remaining-work/regulatory-qualified-envelope.json"
TOKENIZER = ROOT/".localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken"


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
    tmp.replace(path)


def update_task(task_id,status,reason,evidence=None):
    state = json.loads((PACKAGE/"state.json").read_text())
    task = state["tasks"][task_id]
    dependencies = [state["tasks"][key]["status"] for key in task["depends_on"]]
    if status == "SUCCEEDED":
        require(all(value == "SUCCEEDED" for value in dependencies) or
            (task["dependency_mode"] == "completion" and
             all(value in ("SUCCEEDED","FAILED","BLOCKED") for value in dependencies)),
            "Cannot complete task before its declared prerequisites")
    task.update(status=status,reason=reason,
                evidence=[str((BASE/path).relative_to(PACKAGE)) for path in (evidence or [])])
    task["attempts"] = max(1,task["attempts"])
    state["ready"] = []
    for key,row in state["tasks"].items():
        if row["status"] != "PENDING":
            continue
        prereqs = [state["tasks"][d]["status"] for d in row["depends_on"]]
        if all(x == "SUCCEEDED" for x in prereqs) or (
            row["dependency_mode"] == "completion" and all(x in ("SUCCEEDED","FAILED","BLOCKED") for x in prereqs)):
            state["ready"].append(key)
    save(PACKAGE/"state.json",state)


def controls():
    command = [sys.executable,"-m","pytest","tests/assurance/test_bounded_context.py",
               "tests/tooling/test_context_capacity_program.py",
               "--junitxml="+str(BASE/"controls.xml")]
    result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
    (BASE/"controls.log").write_text(result.stdout+result.stderr)
    save(BASE/"controls.json",{"command":command,"returncode":result.returncode,
         "utc":datetime.now(timezone.utc).isoformat(),"live_calls":0})
    update_task("V1","SUCCEEDED" if result.returncode == 0 else "FAILED",
                "Focused integrity, capacity, dependency and independent-failure controls.",
                ["controls.json","controls.xml","controls.log"])


def rehearse(route,envelope,packets,blocked,bridges,bridge_blocks,retrieval_packets):
    _, execution = run_bounded_context(envelope,TOKENIZER,ScriptedUnresolvedProvider(),BASE/"product")
    retrieval_execution = route.execute(retrieval_packets,ScriptedUnresolvedProvider(),BASE/"retrieval-product")
    expected_source = {i for i,r in route.records.items() if r["kind"]=="source"}
    for reader in ("reader-1","reader-2"):
        delivered = {r["id"] for p in packets if p["request"]["reader"]==reader for r in p["request"]["records"]}
        require(delivered == expected_source,"Incomplete reading delivery")
    delivered = {r["id"] for p in packets for r in p["request"]["records"]}
    require(delivered == set(route.records) and not blocked,"Missing exact input delivery")
    require(not bridge_blocks,"Explicit dependency capacity failure")
    require(all(x["status"]=="VALIDATED_PROPOSAL" for x in execution["outcomes"]+
        retrieval_execution["outcomes"]),"Scripted response/dispatch failure")
    require(route.reconstruct() == envelope,"Exact original-input reconstruction failed")
    # Real hierarchy with synthetic summaries; it cannot close legal obligations.
    hierarchy = tree_synthesis([r["text"] for r in route.records.values() if r["kind"]=="source"],
        "Identify conditions, exceptions and unresolved legal connections",route.encode,
        lambda prompt:"UNRESOLVED. Scripted hierarchy control; original sources require legal review.",
        input_tokens=1800,output_tokens=160,maximum_calls=64)
    save(BASE/"hierarchy.json",hierarchy)
    return {"hierarchy_calls":len(hierarchy["calls"]),"hierarchy_levels":hierarchy["level_tokens"],
        "scripted_calls":len(execution["outcomes"])+len(retrieval_execution["outcomes"])+len(hierarchy["calls"]),
        "exact_reconstruction":True,"complete_delivery":True}


class ScriptedUnresolvedProvider:
    live = False
    def complete(self,request,schema,settings):
        return Completion({"records":[{"id":r["id"],"status":"UNRESOLVED","findings":[],
            "open_dependencies":["Scripted integration control; no legal interpretation performed."]}
            for r in request["records"]]}, {"provider":"scripted-unresolved-control","live":False})


def verify(*,correction=False):
    global BASE
    from scripts import legal_mission_control as control
    mission = control.read(ROOT/control.BASE/"mission.json")
    tools = control.read(ROOT/control.BASE/"tools.json")
    admitted = control.admit(mission,tools)
    require(admitted["context_integration"]["execution_allowed"],"Local package settled or expired","E_AUTHORITY")
    if correction:
        require((PACKAGE/"verification-result.json").exists(),"Correction requires retained first attempt")
        require(not (PACKAGE/"correction-started.json").exists(),"Single correction already consumed")
        save(PACKAGE/"correction-started.json",{"utc":datetime.now(timezone.utc).isoformat(),
            "reason":"Whole-unit expansion overflow and unmapped multi-paragraph footnote endpoints",
            "review":"docs/implementation/legal-mission-control/context-integration-review-2026-10-12.md"})
        state = json.loads((PACKAGE/"state.json").read_text())
        save(PACKAGE/"first-attempt-state.json",state)
        for key in ("C2","V1","V2","Q1"):
            state["tasks"][key].update(status="PENDING",attempts=2)
        save(PACKAGE/"state.json",state)
        BASE = PACKAGE/"correction"
    require(not (BASE/"verification-started.json").exists(),"Verification already attempted; inspect retained result")
    save(BASE/"verification-started.json",{"utc":datetime.now(timezone.utc).isoformat(),"pid":os.getpid()})
    started = time.monotonic()
    envelope = json.loads(INPUT.read_text())
    route = prepare_bounded_context(envelope,TOKENIZER)
    counts = Counter(r["kind"] for r in route.records.values())
    require(counts["obligation"] == 46 and counts["reading"] == 35,"Original acceptance population changed")
    versions = {name:importlib.metadata.version(name) for name in ("llama-index-core","rank-bm25","tiktoken","pydantic")}
    save(BASE/"environment.json",{"python":sys.executable,"versions":versions,"gpu":"intentionally hidden",
        "tokenizer_file_sha256":hashlib.sha256(TOKENIZER.read_bytes()).hexdigest(),
        "tokenizer_service_equivalence":"NOT_QUALIFIED"})
    update_task("E1","SUCCEEDED","Pinned real library environment installed and imported.",["environment.json"])
    save(BASE/"store.json",{"input_hash":route.input_hash,"store_hash":route.store_hash,
         "records":route.records,"index_hash":route.index_hash,"by_unit":route.by_unit,
         "source_order":route.source_order,"source_population_status":"PARTIAL_RETAINED_REGULATORY_CORPUS"})
    update_task("C1","SUCCEEDED","Exact original 55 source units,46 obligations and35 readings retained; partial corpus explicit.",["store.json"])
    packets,blocked = route.reading_plan()
    dependencies,unresolved = citation_dependencies(envelope)
    bridges,bridge_blocks = route.dependency_packets(dependencies)
    save(BASE/"reading-plan.json",{"packets":packets,"blocked":blocked,"dependencies":dependencies,
        "bridge_packets":bridges,"bridge_blocks":bridge_blocks,"unresolved_locations":unresolved})
    comparisons = []
    retrieval_packets = []
    for q in envelope["original_questions"]:
        arms = {}
        for expanded in (False,True):
            hits = route.retrieve(q["text"],expand=expanded)
            try:
                p=route.make_packet("QUESTION_SOURCE_REVIEW",hits["record_ids"],
                    question_ids=[q["question_id"]])
                retrieval_packets.append(p)
                arms[str(expanded)]={"hits":hits,"packet":p}
            except Exception as exc:
                arms[str(expanded)]={"hits":hits,"blocked":str(getattr(exc,"details",str(exc)))}
        comparisons.append({"question_id":q["question_id"],"arms":arms})
    save(BASE/"retrieval-comparison.json",comparisons)
    update_task("C2","SUCCEEDED","Actual product prepares library split/retrieve/expand and explicit bridges.",["reading-plan.json","retrieval-comparison.json"])
    try:
        controls()
    except Exception as exc:
        save(BASE/"controls-failure.json",{"type":type(exc).__name__,"details":str(exc)})
        update_task("V1","FAILED","Controls failed; original-input branch remains independent.",["controls-failure.json"])
    try:
        rehearsal = rehearse(route,envelope,packets,blocked,bridges,bridge_blocks,retrieval_packets)
        save(BASE/"rehearsal.json",rehearsal)
        require(len(retrieval_packets) == 2*len(envelope["original_questions"]),
                "A prepared retrieval comparison arm exceeded capacity")
        require(not unresolved,"Some explicit dependency endpoints remain unresolved")
        update_task("V2","SUCCEEDED","Original input executed and reconstructed using real libraries and scripted responses.",["rehearsal.json"])
    except Exception as exc:
        rehearsal = {"failed":True,"type":type(exc).__name__,"details":str(getattr(exc,"details",str(exc)))}
        save(BASE/"rehearsal-failure.json",rehearsal)
        update_task("V2","FAILED","Original-input failure retained; qualification preparation continues.",["rehearsal-failure.json"])
    all_packets = packets + bridges + retrieval_packets
    # Concrete two-arm packet for each original question; preparation only.
    save(BASE/"qualification-packets.json",{"profile":"bounded-context-qualification-prepared.v1",
        "packets":retrieval_packets,"additional_reading_packets":len(packets),
        "explicit_bridge_packets":len(bridges),"live_dispatch":"NOT_AUTHORIZED",
        "full_acquisition_required":True})
    prospective = {"qualification_calls":len(retrieval_packets),"review_calls":len(retrieval_packets),
        "one_response_repair_per_call":2*len(retrieval_packets),
        "maximum_new_calls":4*len(retrieval_packets),"per_call_seconds":300,
        "sequential_maximum_seconds":4*len(retrieval_packets)*300,
        "per_call_input_tokens":route.limits.input_tokens,"per_call_output_tokens":route.limits.output_tokens,
        "maximum_output_tokens":4*len(retrieval_packets)*route.limits.output_tokens,
        "tokenizer_and_provider_overhead":"REQUIRES_SERVICE_QUALIFICATION",
        "money_cost":"Unquoted service pricing; no paid dispatch admitted",
        "historical_calls":41,"historical_grant_expired":True,
        "acceptance":"Evidence presence, exact quotations, remote dependencies, supported rivals; no legal truth certification",
        "limitations":["Partial retained corpus; not full two-reader acquisition","Reviewer packets require actual answers",
                      "Live adapter and finite fresh authorization remain required"]}
    save(BASE/"qualification-budget.json",prospective)
    update_task("Q1","SUCCEEDED",f"Prepared {len(retrieval_packets)} original-question source-reading requests; final-answer schemas and live dispatch remain unqualified.",["qualification-packets.json","qualification-budget.json"])
    # The literal comparator is retained independently of any codec API changes.
    from legalmath.interpretation.assurance import answer_transport
    from legalmath.interpretation.assurance.decomposition import compact_request
    shared_bytes = answer_transport.wire_size(envelope)
    require(shared_bytes == 252110,"Historical comparator changed")
    result = {"profile":"context-capacity-local-result.v1","input_hash":route.input_hash,
        "counts":dict(counts),"source_units":len(route.units),"questions":len(envelope["original_questions"]),
        "reading_packets":len(packets),"bridge_packets":len(bridges),"retrieval_packets":len(retrieval_packets),
        "blocked_reading_packets":blocked,"blocked_bridges":bridge_blocks,
        "unresolved_quote_locations":unresolved,"maximum_prepared_bytes":max(p["measurement"]["bytes"] for p in all_packets),
        "maximum_prepared_tokens":max(p["measurement"]["tokens"] for p in all_packets),
        "baseline_literal_bytes":len(canonical(envelope)),
        "baseline_logical_compact_bytes":len(canonical(compact_request(envelope,profile="v2"))),
        "baseline_shared_bytes":shared_bytes,
        "blocked_retrieval_arms":sum("blocked" in arm for row in comparisons for arm in row["arms"].values()),
        **rehearsal,
        "live_calls":0,"legal_acceptance":False,"complete_corpus":False,"tool_effect_evaluated":False,
        "wall_seconds":round(time.monotonic()-started,3)}
    save(BASE/"verification-result.json",result)
    print(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["verify","correct","status"])
    args=parser.parse_args()
    if args.action=="status":
        print((BASE/"state.json").read_text())
    else:
        try:
            verify(correction=args.action=="correct")
        except Exception as exc:
            save(BASE/"verification-failure.json",{"type":type(exc).__name__,
                "details":str(getattr(exc,"details",str(exc))),"utc":datetime.now(timezone.utc).isoformat()})
            raise

if __name__=="__main__":
    main()

