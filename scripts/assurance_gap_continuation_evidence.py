"""Verify supplemental receipts and execute retained formal proposals offline."""
from collections import Counter
from copy import deepcopy
from itertools import product
from pathlib import Path
import argparse
import json
import sys
import time
import os

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from legalmath.canonical import canonical,digest,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import supplemental_repair as repair
from legalmath.interpretation.assurance import conditional_elimination as logic
from legalmath.interpretation.assurance.diversity import save
from run_assurance_gap_continuation import BASE,ROLES,validator,read_result

AT="2026-09-30T00:00:00.000000Z"


def read(path):return json.loads(Path(path).read_text())


def receipt(path,repo):
    return {"path":str(Path(path).relative_to(repo)),"sha256":raw_digest(Path(path).read_bytes())}


def verified_rows(repo):
    out=repo/BASE
    allowance=repair.SupplementalAllowance(out/"authorization.json")
    allowance.verify()
    # Capture result paths before the append-only ledger: every listed result
    # was persisted after its reservation, even while live calls continue.
    result_paths=sorted((out/"tasks").glob("*/attempt-*/result.json"))
    ledger=read(out/"allowance.json")["calls"] if (out/"allowance.json").exists() else []
    by_slot={row["slot"]:row for row in ledger}
    rows=[]
    used=set()
    for path in result_paths:
        row=read_result(repo,path)
        directory=path.parent
        request=read(directory/"request.json")
        wire=read(directory/"wire.json")
        if digest(request)!=row["request_hash"] or digest(wire)!=row["wire_hash"]:
            raise LegalMathError("E_INTEGRITY",details="Saved request changed")
        repair.decode(wire,digest(request))
        reservations=[r for r in ledger if r["task"]==row["task"] and r["request_hash"]==digest(wire)]
        if not reservations:
            if row["status"]=="VALIDATED":
                raise LegalMathError("E_INTEGRITY",details="Validated result without a reservation")
            row["spending_class"]="NO_PROVIDER_DISPATCH"
        elif len(reservations)!=1:
            raise LegalMathError("E_INTEGRITY",details="Ambiguous reservation")
        else:
            reservation=reservations[0]
            if reservation["slot"] in used:
                raise LegalMathError("E_INTEGRITY",details="Reservation counted twice")
            used.add(reservation["slot"])
            provider=out/"provider-evidence"/(str(reservation["slot"]).zfill(4)+"-"+digest(wire)[:16])
            manifest=read(provider/"manifest.json")
            if manifest["request_hash"]!=digest(wire) or manifest["allowance_slot"]!=reservation["slot"]:
                raise LegalMathError("E_INTEGRITY",details="Provider manifest detached")
            for name,entry in manifest["files"].items():
                if raw_digest((provider/name).read_bytes())!=entry["retained_sha256"]:
                    raise LegalMathError("E_INTEGRITY",details="Retained provider bytes changed")
            if read(provider/"request.json")!=wire or read(provider/"schema.json")!=read(directory/"schema.json"):
                raise LegalMathError("E_INTEGRITY",details="Model saw another request or schema")
            if row["status"]=="VALIDATED":
                actual=read(provider/"result.json")
                checked=validator(repo,row["phase"],request,row["selected"])(actual)
                if checked!=row["value"]:
                    raise LegalMathError("E_INTEGRITY",details="Accepted response changed")
                if row["provenance"]["allowance_slot"]!=reservation["slot"]:
                    raise LegalMathError("E_INTEGRITY",details="Provenance has wrong allowance slot")
            row["spending_class"]="RESERVED"
            row["allowance_slot"]=reservation["slot"]
        row["receipt"]=receipt(path,repo)
        rows.append(row)
    return rows,[r for r in ledger if r["slot"] not in used]


def summarize(repo,final=False):
    out=repo/BASE
    rows,pending=verified_rows(repo)
    if final and pending:
        raise LegalMathError("E_INTEGRITY",details="Reserved actions still lack a final record")
    context=read(out/"context.json")
    baseline=read(out/"predecessors/panel.json")
    latest=deepcopy(baseline["latest"])
    assessments={role:{} for role in ROLES}
    alternatives=[]
    formal=[]
    authority=[]
    active_authority={}
    authority_frontier={}
    for row in rows:
        if row["phase"]=="authority":
            authority_frontier[row["task"]]={"task":row["task"],"role":row["role"],
                "selected":row["selected"],"status":row["status"],"error":row.get("error"),
                "receipt":row["receipt"]}
            active_authority.pop(row["task"],None)
        if row["status"]!="VALIDATED":continue
        if row["phase"] in ("coverage","integration"):
            for a in row["value"]["answers"]:
                latest[row["role"]][a["obligation_id"]]=a
            alternatives.extend({"origin":row["receipt"],"reading":r} for r in row["value"]["alternative_readings"])
        elif row["phase"]=="assessment":
            for a in row["value"]["assessments"]:
                assessments[row["role"]][a["reading_id"]]=a
                value=repair.formal_evidence(context["packet"],context["candidates"][a["reading_id"]],
                    context["questions"][a["reading_id"]],a)
                formal.append({"role":row["role"],"reading_id":a["reading_id"],
                    "assessment_receipt":row["receipt"],**value})
            alternatives.extend({"origin":row["receipt"],"reading":r} for r in row["value"]["newly_proposed_readings"])
        else:
            item={"role":row["role"],"findings":row["value"]["findings"],"receipt":row["receipt"],
                  "task":row["task"],"request_hash":row["request_hash"]}
            authority.append(item)
            active_authority[row["task"]]=item
    obligations=context["contract"]["obligations"]
    missing=[{"obligation_id":o["obligation_id"],"role":role} for o in obligations for role in ROLES if o["obligation_id"] not in latest[role]]
    unresolved=[o["obligation_id"] for o in obligations if any(
        o["obligation_id"] not in latest[role] or latest[role][o["obligation_id"]]["status"]!="PROPOSED_SUPPORTED"
        or latest[role][o["obligation_id"]]["followup_question"] for role in ROLES)]
    missing_assessments=[{"reading_id":cid,"role":role} for cid in context["candidates"] for role in ROLES if cid not in assessments[role]]
    disagreements=[]
    for cid in context["candidates"]:
        pair=[assessments[role].get(cid) for role in ROLES]
        if all(pair):
            differences=[d for d in contract_dimensions() if pair[0]["dimensions"][list(x["dimension"] for x in pair[0]["dimensions"]).index(d)]["status"]
                !=pair[1]["dimensions"][list(x["dimension"] for x in pair[1]["dimensions"]).index(d)]["status"]]
            if differences or pair[0]["disposition"]!=pair[1]["disposition"]:
                disagreements.append({"reading_id":cid,"dimensions":differences,
                    "dispositions":[p["disposition"] for p in pair]})
    summary={"profile":repair.PROFILE,"status":"VERIFIED_FINAL" if final else "VERIFIED_PROGRESS",
        "allowance":repair.SupplementalAllowance(out/"authorization.json").verify(),
        "baseline_counts":{"original_candidates":14,"original_obligations":126,"alternative_records":21,"missing_role_assignments":60},
        "actions":{"validated":sum(r["status"]=="VALIDATED" for r in rows),
                   "failed":sum(r["status"]!="VALIDATED" for r in rows),"pending":len(pending)},
        "offline_recoveries":[{"original_result":r["receipt"],"recovery":r["offline_recovery"],
                                "original_error":r["error"]} for r in rows if r.get("offline_recovery")],
        "failure_history":[{"result":r["receipt"],"phase":r["phase"],"error":r.get("error"),
                            "active_status":r["status"]} for r in rows
                           if r["status"]!="VALIDATED" or r.get("original_status")=="FAILED"],
        "phases":{phase:dict(Counter(r["status"] for r in rows if r["phase"]==phase)) for phase in ("coverage","assessment","authority","integration")},
        "missing_original_role_assignments":missing,"unresolved_original_obligations":unresolved,
        "reading_records":len(context["candidates"]),"missing_reading_assessments":missing_assessments,
        "reading_disagreements":disagreements,
        "formal_status_counts":dict(Counter(r["certificate"]["status"] for r in formal)),
        "new_alternative_records":alternatives,"authority_reviews":list(active_authority.values()),
        "authority_review_history":authority,"authority_review_frontier":list(authority_frontier.values()),
        "original_failed_actions_preserved":baseline["failed_actions"],
        "original_issue_histories":read(out/"inventory.json")["original_issue_histories"],
        "all_original_readings_retained":True,"all_old_alternative_records_retained":True,
        "legal_correctness":"NOT_ESTABLISHED","fresh_whole_method_execution":False,
        "record_receipts":[r["receipt"] for r in rows]}
    save(out/"formal-evidence.json",formal)
    save(out/"assessment-evidence.json",assessments)
    save(out/"latest-challenge-evidence.json",latest)
    save(out/("final-result.json" if final else "progress-result.json"),summary)
    return {"status":summary["status"],"used":summary["allowance"]["used"],
        "validated":summary["actions"]["validated"],"failed":summary["actions"]["failed"],
        "pending":len(pending),"missing_perspectives":len(missing),"unresolved_obligations":len(unresolved),
        "missing_reading_assessments":len(missing_assessments),"formal_status_counts":summary["formal_status_counts"]}


def contract_dimensions():
    return ("actor","scope","quantifier","negation","exception","time","definition","authority","output")


def cases_for(model,formal,obligations,certificate):
    names=[f["name"] for f in formal["facts"]]
    values=[dict(zip(names,values)) for values in product((False,True),repeat=len(names))]
    chosen=[values[0],values[-1]]
    scope=logic.parse_boolean(formal["scope"],names)
    for p in obligations:
        tree=logic.parse_boolean(p["when"],names)
        found=next((v for v in values if logic.evaluate(tree,v)),None)
        if found is not None:chosen.append(found)
    outside=next((v for v in values if not logic.evaluate(scope,v)),None)
    if outside is not None:chosen.append(outside)
    chosen.extend(w["assignment"] for w in certificate["witnesses"])
    unique={digest(v):v for v in chosen}
    if len(unique)>12:
        raise LegalMathError("E_RESOURCE_LIMIT",details="Runtime probe bound; declare another evidence contract before expansion")
    cases=[]
    for i,value in enumerate(unique.values()):
        evidence={("/"+f["name"]):["synthetic."+str(i)+"."+f["name"]] for f in model["facts"]}
        snapshot={"subject_id":"synthetic.supplemental."+str(i),"evidence":evidence,"facts":{
            f["name"]:{"status":"known","type":f["type"],"value":value[f["name"]],
                "evidence_ids":evidence["/"+f["name"]],"complete":True,
                "valid_from":AT,"valid_until":None,"recorded_at":AT} for f in model["facts"]}}
        cases.append({"id":"boolean-probe."+str(i),"snapshot":snapshot,"valid_at":AT,"known_at":AT})
    return cases


def qualify(repo,limit=None):
    from legalmath.translation.model import from_reading
    from legalmath.interpretation.assurance import qualification_adapter as adapter
    out=repo/BASE
    summarize(repo)
    context=read(out/"context.json")
    evidence=read(out/"formal-evidence.json")
    jdk=repo/".localresources/java-toolchain/jdk-17.0.20.1+1"
    tools={"compiler":repo/".localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala",
        "upstream":repo/".localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa",
        "lock":repo/"docs/implementation/catala/toolchain-lock.json"}
    rows=[]
    executed=0
    for e in evidence:
        if e["derived_reading"]["formalization"] is None:continue
        key=digest({"reading":e["derived_reading"],"question":e["question"]})
        base=out/"machine-qualification"/key
        prior=([base/"result.json"] if (base/"result.json").exists() else [])+sorted(base.glob("attempt-*/result.json"))
        if prior and read(prior[-1])["status"]=="CHECKED":
            rows.append(read(prior[-1]));continue
        if len(prior)>=3:
            rows.append(read(prior[-1]));continue
        directory=base if not prior else base/("attempt-"+str(len(prior)+1).zfill(2))
        result=directory/"result.json"
        directory.mkdir(parents=True,exist_ok=False)
        row={"reading_id":e["reading_id"],"role":e["role"],"key":key,
             "source_assessment":e["assessment_receipt"],"status":"RUNNING",
             "claim":"Conditional Boolean structure and executed compiler behavior under synthetic facts; no legal fact labels."}
        began=time.monotonic()
        try:
            model=from_reading(e["derived_reading"],context["packet"],AT)
            cases=cases_for(model,e["derived_reading"]["formalization"],e["obligations"],e["certificate"])
            save(directory/"probe-contract.json",{"selection":"All-false, all-true, first witness of each nonvacuous premise, first out-of-scope valuation, and conditional counterexamples; deduplicated.",
                "full_boolean_valuation_count":e["certificate"]["valuations_checked"],"runtime_cases":len(cases),
                "scope":"Finite diagnostic runtime cases; full Boolean premise enumeration is separate.",
                "promotion_criterion":"Source-to-model lowering and independent native/Java/Catala execution checks agree on these cases.",
                "veto":"Unsupported lowering, compilation failure or execution disagreement",
                "not_concluded":"Legal correctness, source entailment or whole-compiler equivalence on untested cases."})
            value=adapter.run(context["packet"],e["derived_reading"],e["question"],cases,directory/"qualified",
                jdk,AT,toolchain=tools)
            adapter.verify(directory/"qualified",context["packet"],e["derived_reading"],e["question"],jdk,compiler=tools["compiler"])
            row.update(status="CHECKED",summary=value["summary"],runtime_cases=len(cases),
                       report=receipt(directory/"qualified/qualification.json",repo))
        except LegalMathError as exc:
            row.update(status="QUALIFIED_FAILURE",error=exc.code,details=str(exc.details)[:3000])
        except Exception as exc:
            row.update(status="ENGINEERING_FAILURE",error=type(exc).__name__,details=str(exc)[:3000])
            raise
        finally:
            row["elapsed_seconds"]=str(round(time.monotonic()-began,3))
            save(result,row)
        rows.append(row);executed+=1
        print(json.dumps({"reading":e["reading_id"],"role":e["role"],"status":row["status"],"new_qualifications":executed}),flush=True)
        if limit is not None and executed>=limit:break
    save(out/"machine-qualification-summary.json",rows)
    return {"new_qualifications":executed,"total":len(rows),"statuses":dict(Counter(r["status"] for r in rows))}


def expression_checks(repo, limit=None):
    from legalmath.interpretation.search.formal import Comparisons
    out=repo/BASE
    summarize(repo)
    context=read(out/"context.json")
    evidence=read(out/"formal-evidence.json")
    rows=[]; executed=0
    for e in evidence:
        if e["derived_reading"]["formalization"] is None:continue
        key=digest({"reading":e["derived_reading"],"question":e["question"]})
        directory=out/"expression-diagnostics"/key
        result=directory/"result.json"
        if result.exists():rows.append(read(result));continue
        directory.mkdir(parents=True,exist_ok=False)
        row={"reading_id":e["reading_id"],"role":e["role"],"key":key,
             "source_assessment":e["assessment_receipt"],"legal_correctness":"NOT_ESTABLISHED",
             "production_translation_allowed":False,
             "scope":"Existing conditional search-expression compiler, under unchanged unresolved source premises. Native/Java differential probes only; production translation remains blocked."}
        began=time.monotonic()
        try:
            comparison=Comparisons(directory/"java",repo/".localresources/java-toolchain/jdk-17.0.20.1+1",AT)
            value=comparison.verify(e["derived_reading"],context["packet"])
            row.update(status="CONDITIONAL_EXPRESSION_CHECKED",verification=value)
        except LegalMathError as exc:
            row.update(status="QUALIFIED_FAILURE",error=exc.code,details=str(exc.details)[:3000])
        except Exception as exc:
            row.update(status="ENGINEERING_FAILURE",error=type(exc).__name__,details=str(exc)[:3000])
            raise
        finally:
            row["elapsed_seconds"]=str(round(time.monotonic()-began,3));save(result,row)
        rows.append(row);executed+=1
        print(json.dumps({"reading":e["reading_id"],"role":e["role"],"status":row["status"],"cases":row.get("verification",{}).get("cases",0)}),flush=True)
        if limit is not None and executed>=limit:break
    save(out/"expression-diagnostics-summary.json",rows)
    return {"new_checks":executed,"total":len(rows),"statuses":dict(Counter(r["status"] for r in rows))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["summarize","final","qualify","expressions"])
    parser.add_argument("--repo",type=Path,default=ROOT)
    parser.add_argument("--limit",type=int)
    a=parser.parse_args()
    repo=a.repo.resolve()
    result=expression_checks(repo,a.limit) if a.action=="expressions" else qualify(repo,a.limit) if a.action=="qualify" else summarize(repo,a.action=="final")
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":main()
