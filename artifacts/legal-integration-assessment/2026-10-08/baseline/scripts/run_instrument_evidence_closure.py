#!/usr/bin/env python3
"""Content-bound phases with immutable attempts, causal repair and plan refresh."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from legalmath.canonical import digest
from legalmath.prospectus.common import JDK, LEAN, TOOLCHAIN, now, read, sha, write
from legalmath.prospectus import instrument_sources, instrument_cases, instrument_investigation, instrument_evidence, preferred_ss, evidence_checks
from legalmath.qualification import assurance
from legalmath.prospectus.models import make_model
from legalmath.transaction import prospective
from run_eligibility_gap_closure import tests, check_native
from run_instrument_gap_closure import execution_counts, verify_outputs
from run_instrument_transport_study import prepare as prepare_transport

OUT=ROOT/"docs/implementation/instrument-evidence-closure"
PHASES=("E0","E1","E2","E3","E4")
# These independently edited files are neither imported nor executed by this
# program, its selected tests, native backends or source-only transport study.
UNRELATED = {"src/legalmath/interpretation/assurance/executable_references_v2.py",
             "tests/assurance/test_executable_references_v2.py"}


def identity(phase):
    paths=[Path(__file__),ROOT/"scripts/run_instrument_transport_study.py",
        ROOT/"scripts/run_eligibility_gap_closure.py",ROOT/"scripts/run_instrument_gap_closure.py",
        ROOT/"docs/plans/instrument-evidence-closure.md",ROOT/"docs/implementation/catala/toolchain-lock.json"]
    for prefix,suffixes in (("src",{".py",".java",".lean",".json"}),("tests",{".py"}),
        ("docs/prospectus",{".pdf",".json",".txt",".html",".xml"}),
        ("docs/compliance/sources",None),("docs/compliance/feeds",None)):
        paths.extend(p for p in (ROOT/prefix).rglob("*") if p.is_file() and (suffixes is None or p.suffix in suffixes))
    if phase=="E4":
        for prefix in ("chapters","frontmatter","appendices"):
            paths.extend((ROOT/"docs/monograph"/prefix).glob("*.tex"))
        paths.extend(ROOT/p for p in ("docs/monograph/monograph.tex","docs/monograph/technical-companion.tex",
            "docs/monograph/references.bib","docs/monograph/review/revision/citation-reading.json",
            "docs/monograph/review/reader-facing/citation-occurrence-review.json","docs/papers/monograph-citation-archive.json",
            "scripts/build_reader_facing_monograph.py","scripts/check_reader_facing_monograph.py",
            "scripts/export_monograph_process_guide.py"))
    return {"files":{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(set(paths)) if str(p.relative_to(ROOT)) not in UNRELATED},
        "reviewed_unrelated_exclusions":sorted(UNRELATED),
        "tools":{str(p):sha(p.read_bytes()) for p in (LEAN,TOOLCHAIN["compiler"],JDK/"bin/java",JDK/"bin/javac")}}


def E0(out):
    acquired=read(ROOT/"docs/prospectus/supplemental/manifest.json")
    for row in acquired["sources"]:
        if sha((ROOT/row["path"]).read_bytes())!=row["sha256"]:raise ValueError("Changed acquired source")
        if "text_path" in row and sha((ROOT/row["text_path"]).read_bytes())!=row["text_sha256"]:
            raise ValueError("Changed source extraction")
    write(out/"public-acquisition.json",acquired)
    write(out/"ubs-dossier.json",instrument_sources.dossier(ROOT))
    write(out/"preferred-dossier.json",preferred_ss.dossier(ROOT))
    request,store=instrument_cases.request(ROOT,out/"bank")
    missing=instrument_evidence.requirements(request["joined_request"]["bank_request"],store)
    write(out/"evidence-requests.json",missing)
    return {"acquired_records":len(acquired["sources"]),"missing_facts":len(missing["missing_facts"]),
        "bank_obligations":len(missing["obligations"]),"tests":tests(out,["tests/prospectus/test_instrument_evidence.py"]),
        "calendar":"Retained 2027 SIC clearing schedule; not a complete UBS contractual bank/FX calendar",
        "legal_force":"NOT_ESTABLISHED","human_quality_evidence":False}


def E1(out):
    result=tests(out,["tests/prospectus/test_instrument_branches.py","tests/prospectus/test_instrument_terms.py"])
    coverage={"rounding":"Exact rational down/half-up scenarios; source selection remains qualified",
        "contractual_determinations":"Scoped issue/event/history/evidence checks, adviser/issuer fallback and stated exceptions",
        "successor":"Separate fully covered market calendars, five preceding dealing days each, ECP date, dated FX/VWAP",
        "alternative_notice":"Scoped notice and rule bytes; stated exchange permission remains a factual premise",
        "holder_delivery":"Taxes, actual custody receipt and voting-register receipt evaluated separately",
        "printed_formula":"Preserved; no amendment inferred","intraday_order":"Unresolved where only dates are supplied",
        "full_contract":"NOT_FULLY_FORMALIZED"}
    write(out/"branch-coverage.json",coverage)
    return {"tests":result,"coverage":coverage,"human_quality_evidence":False}


def E2(out):
    result=tests(out,["tests/prospectus/test_preferred_ss.py","tests/prospectus/test_instrument_investigation.py","tests/prospectus/test_instrument_extensions.py","tests/prospectus/test_joined_eligibility.py"])
    request,store=instrument_cases.request(ROOT,out/"bank")
    reports={}
    ubs=instrument_investigation.investigate(request,store,ROOT)
    write(out/"ubs-real-document.json",ubs)
    joined=deepcopy(request["joined_request"])
    joined["bank_request"]["context"].update(instrument_id=preferred_ss.KEY,instrument_kind="preferred_share")
    joined["prospectus_source_ids"]=[preferred_ss.KEY];joined["issuer_basis_source_ids"]=[]
    ss=preferred_ss.investigate(joined,store,ROOT)
    write(out/"preferred-real-document.json",ss)
    for name,report in (("ubs",ubs),("preferred",ss)):
        if len(report["inventory"])!=14 or report["may_execute_transaction"]:raise ValueError("Inventory or clearance regression")
        reports[name]={"scope":report["calculations"]["scope"],"decision":report["decision"],
            "bank_obligations":len(report["inventory"]),"receipt_hash":report["receipt_hash"]}
    extended_request,extended_store=instrument_cases.extended_request(ROOT,out/"extended")
    extended=instrument_investigation.investigate(extended_request,extended_store,ROOT)
    instrument_investigation.revalidate(extended,extended_request,extended_store,ROOT)
    if (extended["instrument_event"]["holder_delivery"]["delivered"] is not True
            or extended["may_execute_transaction"] or len(extended["inventory"])!=14):
        raise ValueError("Extended evidence did not assemble consistently")
    write(out/"ubs-extended-hypothetical.json",{"request":extended_request,"receipt":extended})
    dividend=preferred_ss.regular_dividend(start="2026-05-17",end="2026-08-17",declared_fraction="1",funds_available=True,
        depositary_shares=100,allocation_basis="round_holder_allocation",withholding="0")
    write(out/"hypothetical-dividend.json",{"premise_kind":"HYPOTHETICAL","calculation":dividend})
    return {"tests":result,"real_document_reports":reports,"extended_hypothetical_receipt":extended["receipt_hash"],"human_quality_evidence":False}


def E3(out):
    proof=evidence_checks.prove(out/"proof",LEAN)
    native={};counts={}
    for name,spec in evidence_checks.specifications().items():
        inputs=evidence_checks.cases(name)
        report=assurance.run(make_model("ss_"+name,spec),inputs,out/"native"/name,JDK,toolchain=TOOLCHAIN)
        native[name]=check_native(report,inputs);counts[name]=execution_counts(report)
        for target in report["targets"].values():
            if any(c["result"]["status"]!="ABSTAIN" for c in target["cases"][-2:]):raise ValueError("Missing/conflicting input did not abstain")
        print("E3 checked native/formal "+name,flush=True)
    transport=prepare_transport(out/"transport-study")
    request,store=instrument_cases.request(ROOT,out/"future")
    bank=request["joined_request"]["bank_request"]
    frozen=prospective.freeze(at=now(),known_source_hashes=[r["blob"] for r in store.json(bank["registry_sha256"]).values()])
    write(out/"future-freeze.json",{"freeze":frozen,"observations":[],"development_cases_are_future_observations":False})
    return {"proof":proof,"native":native,"counts":counts,
        "native_executions":sum(v["native_executions"] for v in counts.values()),
        "pre_execution_abstentions":sum(v["pre_execution_abstentions"] for v in counts.values()),
        "transport":{"prepared_calls":transport["calls_required"],"live_calls":0,"status":"AWAITING_FRESH_ALLOWANCE"},
        "future_observations":0,"human_quality_evidence":False}


def E4(out):
    regression=tests(out,["tests/prospectus","tests/compliance","tests/translation/test_qualification_proof.py",
        "tests/translation/test_qualification_windows.py","tests/translation/test_gregorian_proof.py"],timeout=300)
    command=["python3","scripts/build_reader_facing_monograph.py"]
    with (out/"documents.log").open("w") as log:
        subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    documents={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/"docs/monograph/monograph.pdf",
        ROOT/"docs/monograph/technical-companion.pdf",ROOT/"docs/monograph/process-guide.pdf")}
    return {"regression":regression,"documents":documents,"document_command":command,
        "decision":"BOUNDED_ENGINEERING_CHECKS_PASSED","legal_entailment":"NOT_ESTABLISHED",
        "future_legal_accuracy":"NOT_ESTABLISHED","human_quality_evidence":False}


def execute(phase,*,output=OUT,repair_note=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    bound=identity(phase); input_hash=digest(bound);predecessors={}
    for name in PHASES[:PHASES.index(phase)]:
        manifests=sorted((output/name).glob("attempt-*/manifest.json"))
        if not manifests:raise ValueError("Missing predecessor "+name)
        previous=read(manifests[-1])
        if previous["status"]!="PASS" or previous["input_hash"]!=digest(identity(name)):
            raise ValueError("Failed or changed predecessor "+name)
        verify_outputs(manifests[-1],previous);predecessors[name]=sha(manifests[-1].read_bytes())
    directory=output/phase;directory.mkdir(exist_ok=True)
    prior=sorted(directory.glob("attempt-*/manifest.json"))
    if prior:
        last=read(prior[-1])
        if last["status"]=="PASS" and last["input_hash"]==input_hash and last["predecessors"]==predecessors:
            verify_outputs(prior[-1],last);return {"phase":phase,"status":"PASS","reused":True}
        if last["status"]!="PASS" and (not isinstance(repair_note,str) or not repair_note.strip()):
            raise ValueError("Causal repair note required before retry")
        if len(prior)>=4:raise ValueError("Four-attempt limit reached; revise plan")
    attempt=directory/f"attempt-{len(prior)+1:03d}";attempt.mkdir()
    write(attempt/"inputs.json",bound)
    started=time.monotonic()
    manifest={"phase":phase,"status":"RESERVED","input_hash":input_hash,"predecessors":predecessors,
        "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "command":sys.argv,"environment":sys.executable,"python":sys.version,"platform":platform.platform(),
        "cpu_gpu":"CPU only; CUDA_VISIBLE_DEVICES=-1","seeds":"N/A: deterministic","started_at":now(),
        "plan":"docs/plans/instrument-evidence-closure.md","repair_note":repair_note,"live_calls":0}
    write(attempt/"manifest.json",manifest)
    write(output/"next-phase-plan.json",{"phase":phase,"status":"RESERVED","attempt":str(attempt)})
    try:
        result=globals()[phase](attempt);write(attempt/"result.json",result)
        if identity(phase)!=bound:raise ValueError("Inputs changed during phase")
        manifest["status"]="PASS"
    except Exception as exc:
        (attempt/"failure.log").write_text(traceback.format_exc());manifest.update(status="FAILED",error=str(exc));raise
    finally:
        manifest.update(finished_at=now(),wall_seconds=round(time.monotonic()-started,3))
        manifest["output_hashes"]={str(p.relative_to(attempt)):sha(p.read_bytes()) for p in attempt.rglob("*") if p.is_file() and p!=attempt/"manifest.json"}
        write(attempt/"manifest.json",manifest)
        index=PHASES.index(phase);passed=manifest["status"]=="PASS"
        write(output/"next-phase-plan.json",{"last_phase":phase,"status":manifest["status"],"input_hash":input_hash,
            "next_phase":PHASES[index+1] if passed and index+1<len(PHASES) else None,"repair_required":not passed,
            "error":manifest.get("error"),"next_action":"Proceed to bound successor or rendered delivery review" if passed else "Diagnose failure, preserve it, execute causal repair and retry",
            "remaining":["Authentic complete event/action/calendar and private evidence","Complete current applicable-law inventory",
                "Contractual ambiguities and missing agreements","Fresh live allowance for prepared transport study","Actual later observations and unproved English meaning"],
            "human_quality_evidence":False,"live_calls_authorized":0})
    return {"phase":phase,"status":"PASS","reused":False,"manifest":str(attempt/"manifest.json")}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--phase",choices=(*PHASES,"all"),default="all");parser.add_argument("--repair-note");args=parser.parse_args()
    for phase in PHASES if args.phase=="all" else (args.phase,):print(json.dumps(execute(phase,repair_note=args.repair_note)),flush=True)
