#!/usr/bin/env python3
"""Execute the reviewed UBS increment with retained failures and refreshed plans."""
import argparse
from copy import deepcopy
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ["CUDA_VISIBLE_DEVICES"]="-1"

from legalmath.canonical import digest
from legalmath.prospectus.common import JDK, TOOLCHAIN, now, read, sha, write
from legalmath.prospectus import instrument_sources, instrument_cases, instrument_checks, instrument_investigation
from legalmath.prospectus.models import make_model
from legalmath.qualification import assurance
from legalmath.transaction.evidence import Store
from run_eligibility_gap_closure import identity as baseline_identity, tests, check_native

OUT=ROOT/"docs/implementation/instrument-gap-closure"
PHASES=("I0","I1","I2","I3","I4")
PRICE_SELECTION="aggregate or settlement or rights or price or successor or offer"


def identity():
    bound=baseline_identity()
    paths=[Path(__file__),ROOT/"docs/plans/instrument-gap-closure.md",
           ROOT/"docs/monograph/monograph.tex",ROOT/"docs/monograph/technical-companion.tex",
           ROOT/"docs/monograph/references.bib",ROOT/"scripts/build_reader_facing_monograph.py",
           ROOT/"scripts/export_monograph_process_guide.py",ROOT/"scripts/check_reader_facing_monograph.py",
           ROOT/"docs/monograph/review/revision/citation-reading.json",
           ROOT/"docs/monograph/review/reader-facing/citation-occurrence-review.json"]
    for directory in ("chapters","frontmatter","appendices"):
        paths.extend((ROOT/"docs/monograph"/directory).glob("*.tex"))
    bound["files"].update({str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths})
    return bound


def I0(out):
    packet=instrument_sources.dossier(ROOT)
    write(out/"dossier.json",packet)
    # Retain rendered evidence of the formula, not only its text extraction.
    command=["python3","-c",
        "import fitz,sys; p=fitz.open(sys.argv[1]); p[29].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(sys.argv[2])",
        str(ROOT/"docs/prospectus/originals"/(instrument_sources.KEY+".pdf")),str(out/"printed-distribution-formula.png")]
    subprocess.run(command,check=True,timeout=30)
    return {"source":packet["source"],"annex":packet["annex"],"dossier_hash":packet["dossier_hash"],
        "bound_anchors":len(packet["anchors"]),"dependencies":packet["dependencies"],"anomalies":packet["anomalies"],
        "decision":"SOURCE_BOUND_WITH_EXPLICIT_QUALIFICATIONS","live_calls":0}


def I1(out):
    calendar,scenario=instrument_cases.fixtures(Store(out/"store"))
    write(out/"declared-scenario.json",scenario)
    return {"tests":tests(out,["tests/prospectus/test_instrument_terms.py","-k","not ("+PRICE_SELECTION+")"]),
        "calendar_evidence":calendar.identity,"premise_kind":"HYPOTHETICAL",
        "actual_event":"NOT_ESTABLISHED"}


def I2(out):
    result=tests(out,["tests/prospectus/test_instrument_terms.py","-k",PRICE_SELECTION])
    coverage={
        "7a_7b":"Ratio, notice, restoration, higher-trigger postponement; intraday/order uncertainty qualified",
        "7c_7e":"Viability premises, calendar notice, event-anchored business deadline, alternative actual notice",
        "7d":"Retained immutable publication; changed components rejected",
        "8a_8b_8c_8g":"Conditional share entitlement, holder aggregation, fractions, creation and depository receipt",
        "8d_A_B_D":"Declared split/bonus/rights arithmetic; exact-cent deterministic price-history subset",
        "8d_C":"Printed (A-B)/B calculated literally; operational price QUALIFIED",
        "8d_E_and_ii":"Par floor and exact carry-forward; rounding, overlapping/discretionary adjustments QUALIFIED",
        "8e":"Successor price arithmetic and seven-day/effective conditions; supplied common dealing calendar only",
        "8h":"Net SGD offer allocation and deadlines; actual FX, subscription, offer validity and delivery not established",
        "8i_8j_8k_8l_8m_8n":"Taxes, registration, share rights, repurchase and binding determinations remain separate dependencies",
        "13_14_15":"Amendment/substitution invalidates profile; first SIX publication/delisting delivery supported; alternative SIX methods QUALIFIED",
        "whole_contract":"NOT_FULLY_FORMALIZED"}
    write(out/"branch-coverage.json",coverage)
    return {"tests":result,"coverage":coverage,"market_value":"NOT_COMPUTED"}


def I3(out):
    equations=instrument_checks.prove(out/"equations")
    native={}; counts={}
    for name,spec in instrument_checks.specifications().items():
        inputs=instrument_checks.inputs(name,spec)
        report=assurance.run(make_model("ubs_"+name,spec),inputs,out/"native"/name,JDK,toolchain=TOOLCHAIN)
        native[name]=check_native(report,inputs)
        counts[name]=execution_counts(report)
        for target in report["targets"].values():
            if any(c["result"]["status"] != "ABSTAIN" for c in target["cases"][-2:]):
                raise ValueError("Native missing/conflict premises did not abstain")
        print("I3 native/formal checked: "+name,flush=True)
    request,store=instrument_cases.request(ROOT,out/"bank")
    reports={}
    for name,scenario in {"real_document":None,**instrument_cases.scenarios(store)}.items():
        current=deepcopy(request)
        if scenario is not None: current["scenario_sha256"]=store.put(scenario)
        report=instrument_investigation.investigate(current,store,ROOT)
        instrument_investigation.revalidate(report,current,store,ROOT)
        if len(report["inventory"]) != 14 or report["may_execute_transaction"]:
            raise ValueError("Missing bank obligations or invented clearance")
        write(out/(name+".json"),{"request":current,"receipt":report})
        reports[name]={"receipt_hash":report["receipt_hash"],"decision":report["decision"],
            "source_dependent_premises":report["source_dependent_product_premises"],
            "product_scope":report["calculations"]["scope"],"restriction":report["calculations"]["restriction"],
            "event_status":report["instrument_event"]["status"],"scenario_kind":report["scenario_kind"],
            "bank_obligations":len(report["inventory"]),"may_execute_transaction":False}
    return {"independent_equations":equations,"native":native,
        "target_cases":sum(v["target_cases"] for v in counts.values()),
        "native_executions":sum(v["native_executions"] for v in counts.values()),
        "pre_execution_abstentions":sum(v["pre_execution_abstentions"] for v in counts.values()),
        "execution_counts":counts,"investigations":reports}


def execution_counts(report):
    rows=[case for target in report["targets"].values() for case in target["cases"]]
    skipped=sum(row["result"]["status"] == "ABSTAIN" for row in rows)
    return {"target_cases":len(rows),"native_executions":len(rows)-skipped,"pre_execution_abstentions":skipped}


def I4(out):
    regression=tests(out,["tests/prospectus","tests/compliance","tests/translation/test_qualification_proof.py",
        "tests/translation/test_qualification_windows.py","tests/translation/test_gregorian_proof.py"],timeout=300)
    command=["python3","scripts/build_reader_facing_monograph.py"]
    with (out/"documents.log").open("w") as log:
        subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    documents={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
        [ROOT/"docs/monograph/monograph.pdf",ROOT/"docs/monograph/technical-companion.pdf",ROOT/"docs/monograph/process-guide.pdf"]}
    bound=identity()
    write(out/"future-freeze.json",{"at":now(),"method_and_inputs":bound,"hash":digest(bound),
        "future_observations":[],"development_cases_are_future_observations":False,
        "prospective_legal_accuracy":"NOT_ESTABLISHED","human_quality_evidence":False})
    return {"regression":regression,"documents":documents,"document_command":command,
        "decision":"BOUNDED_IMPLEMENTATION_CHECKED","rendered_review":"RECORDED_SEPARATELY",
        "future_observations":0,"legal_entailment":"NOT_ESTABLISHED"}


def execute(phase,*,output=OUT,repair_note=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    bound=identity(); input_hash=digest(bound)
    predecessors={}
    for name in PHASES[:PHASES.index(phase)]:
        manifests=sorted((output/name).glob("attempt-*/manifest.json"))
        if not manifests: raise ValueError("Missing predecessor "+name)
        previous=read(manifests[-1])
        if previous["status"] != "PASS" or previous["input_hash"] != input_hash:
            raise ValueError("Failed or changed predecessor "+name)
        verify_outputs(manifests[-1],previous)
        predecessors[name]=sha(manifests[-1].read_bytes())
    directory=output/phase; directory.mkdir(exist_ok=True)
    prior=sorted(directory.glob("attempt-*/manifest.json"))
    if prior:
        last=read(prior[-1])
        if last["status"] == "PASS" and last["input_hash"] == input_hash and last["predecessors"] == predecessors:
            verify_outputs(prior[-1],last)
            return {"phase":phase,"status":"PASS","reused":True}
        if last["status"] != "PASS" and not repair_note:
            raise ValueError("Causal repair note required before retry")
        if len(prior) >= 4: raise ValueError("Four-attempt limit reached; revise the recorded plan")
    attempt=directory/f"attempt-{len(prior)+1:03d}"; attempt.mkdir()
    write(attempt/"inputs.json",bound)
    started=time.monotonic()
    manifest={"phase":phase,"status":"RESERVED","input_hash":input_hash,"predecessors":predecessors,
        "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "command":sys.argv,"python":sys.version,"platform":platform.platform(),"started_at":now(),
        "cpu_gpu":"CPU only; CUDA_VISIBLE_DEVICES=-1","seeds":"N/A: deterministic",
        "plan":"docs/plans/instrument-gap-closure.md","repair_note":repair_note,"live_calls":0}
    write(attempt/"manifest.json",manifest)
    write(output/"next-phase-plan.json",{"phase":phase,"status":"RESERVED","attempt":str(attempt)})
    try:
        result=globals()[phase](attempt)
        write(attempt/"result.json",result)
        if identity() != bound: raise ValueError("Inputs or method changed during phase")
        manifest["status"]="PASS"
    except Exception as exc:
        (attempt/"failure.log").write_text(traceback.format_exc())
        manifest.update(status="FAILED",error=str(exc))
        raise
    finally:
        manifest.update(finished_at=now(),wall_seconds=round(time.monotonic()-started,3))
        manifest["output_hashes"]={str(p.relative_to(attempt)):sha(p.read_bytes()) for p in attempt.rglob("*")
            if p.is_file() and p != attempt/"manifest.json"}
        write(attempt/"manifest.json",manifest)
        index=PHASES.index(phase)
        write(output/"next-phase-plan.json",{"last_phase":phase,"status":manifest["status"],"input_hash":input_hash,
            "next_phase":PHASES[index+1] if manifest["status"]=="PASS" and index+1<len(PHASES) else None,
            "repair_required":manifest["status"]!="PASS","error":manifest.get("error"),
            "next_action":"Proceed to bound successor or rendered delivery review" if manifest["status"]=="PASS" else "Diagnose preserved failure, execute causal repair, then retry with repair note",
            "remaining":["Incorporated agreements and actual notices/calendars/market histories","Source formula/rounding clarification",
                "Current legal applicability and private bank evidence","Additional instrument families","Unknown future legal meaning"],
            "human_quality_evidence":False,"live_calls_authorized":0})
    return {"phase":phase,"status":"PASS","reused":False,"manifest":str(attempt/"manifest.json")}


def verify_outputs(path,manifest):
    for relative,expected in manifest["output_hashes"].items():
        if sha((path.parent/relative).read_bytes()) != expected:
            raise ValueError("Changed phase output: "+relative)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase",choices=(*PHASES,"all"),default="all")
    parser.add_argument("--repair-note")
    args=parser.parse_args()
    for phase in PHASES if args.phase=="all" else (args.phase,):
        print(json.dumps(execute(phase,repair_note=args.repair_note)),flush=True)


if __name__=="__main__": main()
