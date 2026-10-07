"""Actual external-engine checks with independently stated computational targets."""
from dataclasses import asdict
import json
from pathlib import Path
from scripts.legal_tool_program import ROOT,OUT,RES,read,save,ref,command,check_ref

def previous(phase):
    state=read(OUT/"state.json")
    return read(check_ref(state["completed"][phase]))["result"]

def external(kind,request,work,name):
    save(work/(name+"-input.json"),request)
    command([RES/"venv/bin/python",ROOT/"scripts/legal_tool_worker.py",kind,
             work/(name+"-input.json"),work/(name+"-output.json")],work,name,timeout=90)
    return read(work/(name+"-output.json"))

def graph_cases():
    from legalmath.interpretation.semantics.arguments import Argument,Attack,Theory,evaluate
    cases=[]
    # Enumerate every directed graph up to three arguments, including self-attacks.
    for n in range(4):
        ids=[str(i) for i in range(n)]
        possible=[(a,b) for a in ids for b in ids]
        for bits in range(1<<len(possible)):
            edges=[e for i,e in enumerate(possible) if bits&(1<<i)]
            cases.append({"id":"finite-"+str(n)+"-"+str(bits),"ids":ids,"attacks":edges})
    raw=read(ROOT/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/P3/attempt-4/graph.json")
    cases.append({"id":"retained-p14-p10-graph","ids":[a["id"] for a in raw["arguments"]],
                  "attacks":[[a["source"],a["target"]] for a in raw["attacks"]]})
    for case in cases:
        theory=Theory(tuple(Argument(i,i) for i in case["ids"]),
                      tuple(Attack(a,b,"rebuttal",b) for a,b in case["attacks"]))
        case["baseline"]={s:[list(e) for e in evaluate(theory,s,max_arguments=12).extensions]
                          for s in ("grounded","preferred")}
    return cases

def run(work):
    from scripts.legal_tool_inputs import QUESTIONS
    baseline=previous("T0")
    corpus=read(check_ref(baseline["corpus"]))
    sources=previous("T1")["sources"]
    results={}
    try:
        cases=graph_cases()
        result=external("pyarg",{"cases":cases},work,"pyarg")
        byid={c["id"]:c for c in cases}
        differences=[{"id":r["id"],"external":r,"baseline":byid[r["id"]]["baseline"]}
                     for r in result["cases"] if any(r[s]!=byid[r["id"]]["baseline"][s]
                                                   for s in ("grounded","preferred"))]
        if differences:raise ValueError("External/local semantics differ: "+str(differences[:2]))
        result.update(status="PASS",matched_cases=len(cases),differences=differences,
            adoption_scope="Independent grounded/preferred checking for a supplied bounded graph",
            legal_premises_established=False)
        results["pyarg"]=result
    except (ImportError,RuntimeError,ValueError,KeyError) as exc:
        results["pyarg"]={"status":"TRIAL_FAILED","error":str(exc),"decision":"REPAIR_OR_DEFER"}
    try:
        texts=["[2023] HKCFI 914","[2025] HKCFI 493","[2020] UKSC 12",
               "Brown v. Board of Education, 347 U.S. 483 (1954).","Id. at 487."]
        result=external("citations",{"texts":texts},work,"eyecite")
        result["hong_kong_matched"]=sum(bool(c["citations"]) for c in result["cases"][:2])
        result["us_positive_control"]=bool(result["cases"][3]["citations"])
        result["decision"]="DEFER_HK_CITATION_ROUTE" if result["hong_kong_matched"]<2 else "ADAPT_PENDING_RESOLUTION"
        results["eyecite"]=result
    except (ImportError,RuntimeError,ValueError) as exc:
        results["eyecite"]={"status":"TRIAL_FAILED","error":str(exc)}
    try:
        result=external("retrieve",{"corpus":corpus,"questions":QUESTIONS},work,"retrieval")
        units={u["id"]:u for u in corpus["units"]}
        for r in result["results"]:
            for p in r["passages"]:
                if p["text"]!=units[p["unit_id"]]["text"]:raise ValueError("Retrieval changed source")
        result["source_identity"]="CHECKED"
        result["relevance"]="NOT_ESTABLISHED_BY_RANK"
        results["retrieval"]=result
    except (ImportError,RuntimeError,ValueError) as exc:
        results["retrieval"]={"status":"TRIAL_FAILED","error":str(exc)}
    from scripts.legal_tool_native import carneades,logical_english,legalruleml
    for name,trial in (("carneades",lambda:carneades(work,graph_cases())),
                       ("logical-english",lambda:logical_english(work)),
                       ("legalruleml",lambda:legalruleml(work))):
        try:
            results[name]=trial()
        except Exception as exc:
            results[name]={"status":"TRIAL_FAILED","error":str(exc),"decision":"REPAIR_OR_DEFER"}
    results["sara-ie"]={"status":"DEFER","reason":"Retained root licence unverified; tax ontology and trained extraction protocol not qualified for these sources",
        "reference":"docs/research/legal-interpretation-reuse-2026-10-05.md"}
    results["hypo-cato-agatha"]={"status":"CONCEPTS_ONLY","reason":"No verified installable original engine; use explicit sourced factors and distinctions",
        "case_records":"scripts/legal_interpretation_s2_cases.py"}
    results["clerc"]={"status":"DEFER_ORIGINAL_ENGINE","source":sources.get("clerc"),
        "reason":"Whole-repository/corpus reuse permission and target corpus deployment not established; rank-bm25 is separately identified"}
    save(work/"components.json",results)
    return {"status":"COMPONENT_EVIDENCE_RECORDED","components":ref(work/"components.json"),
            "tools":{k:{a:b for a,b in v.items() if a in ("status","decision","matched_cases","hong_kong_matched","adoption_scope","reason")}
                     for k,v in results.items()}}

