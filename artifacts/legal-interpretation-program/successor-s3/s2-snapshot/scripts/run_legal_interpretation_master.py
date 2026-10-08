"""Fixed master status/resume/verify for legal interpretation revision 3.

This runner executes the implemented S2 phase offline. Acquisition is a separate
bounded public-source action. No arbitrary command, model provider or GPU path is
available. Historical evidence is checked without rerunning historical methods.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__" and Path(sys.prefix)!=ROOT/".venv":
    os.execv(str(ROOT/".venv/bin/python"),[str(ROOT/".venv/bin/python"),"-m","scripts.run_legal_interpretation_master",*sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from scripts.legal_interpretation_s2_prepare import files, inputs
from scripts.legal_interpretation_s2_data import (
    packet, inventory, source_findings, obligation_ledger, development_cases)
from scripts.legal_interpretation_s2_cases import build as case_records
from legalmath.interpretation.semantics.records import Scope, Interval
from legalmath.interpretation.semantics.standards import Assessment, evaluate
DOC=ROOT/"docs/implementation/legal-interpretation-program"
BASE=ROOT/"artifacts/legal-interpretation-program/successor-s2"
POINTER=DOC/"program-current.json"
MASTER=ROOT/"docs/plans/legal-interpretation-master-program.md"
PLAN=ROOT/"docs/plans/legal-interpretation-program/S2-authority-and-standards.md"
COMPLETION=ROOT/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/completion-2.json"
S1=ROOT/"artifacts/legal-interpretation-program/successor-s1/attempt-2/result.json"
TESTS=["tests/interpretation/semantics","tests/interpretation/test_contracts.py",
 "tests/assurance/test_closure_references.py","tests/assurance/test_source_derivative.py",
 "tests/assurance/test_investigation_observations.py","tests/assurance/test_continuation_qualification.py",
 "tests/assurance/test_integrated_workflow.py","tests/translation/test_frontend.py",
 "tests/translation/test_qualification_execution.py"]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {"path":str(p.relative_to(ROOT)),"sha256":sha(p)}
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write("\n")
def checked(row):
    p=ROOT/row["path"]
    if not p.resolve().is_relative_to(ROOT) or not p.is_file() or sha(p)!=row["sha256"]:
        raise ValueError("Changed/missing reference: "+row["path"])
    return p
def history():
    expected=((COMPLETION,"00787202085da9ee4942a34bf87252a9be5192fe1333075b843edede74bb788d"),
              (S1,"75b6cfd2f361b7e28ebdac0cd742876831a2b5d5314ba82dc5328432b8993cdd"))
    for p,h in expected:
        if sha(p)!=h:raise ValueError("Wrong completed baseline")
    archive=read(DOC/"revision-2-archive.json")
    for row in archive["files"]:checked({"path":row["retained_path"],"sha256":row["sha256"]})
    count=0
    previous=read(COMPLETION)
    for selected in list(previous["phases"].values())+[{"result":previous["validation"]},{"result":ref(S1)}]:
        result=read(checked(selected["result"]))
        for row in result.get("outputs",[]):
            checked(row);count+=1
        if "test_receipt" in result:checked(result["test_receipt"])
    base=read(BASE/"baseline.json")
    archived_plan=DOC/"revisions/s2-plan-1.md"
    if sha(archived_plan)!=base["plan"]["sha256"]:raise ValueError("Historical S2 plan changed")
    if base["inputs"]!=inputs():raise ValueError("S2 baseline inputs changed")
    return {"status":"PASS","revision_2_archived_files":len(archive["files"]),
        "historical_output_files":count,"baseline":ref(BASE/"baseline.json"),
        "historical_method_scope":"Integrity of retained evidence; later code is a different method"}
def preserve():
    base=read(BASE/"baseline.json");now=files()
    changed=sorted(p for p,h in base["files"].items() if now.get(p)!=h)
    if changed:raise ValueError("Pre-existing source/test files changed during additive S2: "+repr(changed))
    return {"pre_existing_files_byte_identical":len(base["files"]),
        "new_source_test_files":sorted(set(now)-set(base["files"]))}
def method():
    drivers=[Path(__file__),ROOT/"scripts/legal_interpretation_refresh_master.py",MASTER,PLAN,
        DOC/"revision-3-audit.md",DOC/"s2-source-findings.md",DOC/"s2-execution-audit.md"]
    drivers += sorted((ROOT/"scripts").glob("legal_interpretation_s2_*.py"))
    return {"source_and_tests":files(),"drivers":{str(p.relative_to(ROOT)):sha(p) for p in drivers}}
def acquisitions():
    folder=BASE/"acquisition";requests=sorted(folder.glob("*/request-*.json"))
    if len(requests)>24:raise ValueError("HTTP acquisition ceiling exceeded")
    records=[]
    for p in sorted(folder.glob("*/spec.json")):
        result=p.parent/"result.json"
        r=read(result) if result.exists() else {"status":"INCOMPLETE"}
        disposition="NOT_ADMITTED_AS_AUTHORITY"
        if p.parent.name in ("gatecoin-2023-official","gatecoin-2025-official"):
            disposition="EXACT_OFFICIAL_PASSAGES_REVIEWED; target transfer and treatment remain qualified"
        elif p.parent.name in ("gatecoin-2023","gatecoin-2025"):
            disposition="FULL_MIRROR_REASONS_INSPECTED; official originals separately retained"
        note=None
        if r.get("content_type","").startswith("application/json") and (p.parent/"response.bin").exists():
            data=read(p.parent/"response.bin")
            if isinstance(data,dict) and "results" in data:
                note={"reported_count":data.get("count"),"returned_count":len(data["results"]),
                    "recommendation":data.get("recommendation"),"admission":"Unreviewed retrieval leads"}
                if "Exception" in str(data.get("recommendation","")):disposition="SEARCH_ERROR; no absence inference"
        records.append({"spec":ref(p),"result":ref(result) if result.exists() else None,
            "status":r["status"],"disposition":disposition,"search_note":note})
    return {"http_attempts":len(requests),"ceiling":24,"records":records,
        "files":[ref(p) for p in sorted(folder.rglob("*")) if p.is_file()],
        "completeness":"NOT_ESTABLISHED"}
def neutral_assessment():
    return Assessment(scope=Scope(actor=None,product=None,component=None,activity=None,
        interval=Interval(start=None,end=None)),provider=None,jurisdiction="HK",known_by=None)
def build_outputs():
    source=packet();cat,rules=inventory(source)
    payload={"source-catalogue.json":cat,"standards.json":[r.model_dump(mode="json") for r in rules],
        "source-findings.json":source_findings(source,cat),
        "obligations.json":obligation_ledger(source,cat,rules),
        "case-records.json":case_records(),
        "retained-evaluation.json":evaluate(rules,source,cat,neutral_assessment(),()),
        "development-cases.json":development_cases(source,cat,rules)}
    return json.loads(json.dumps(payload))
def next_plan(stats,attempt):
    return f"""# S3: scoped evidence and actual investigation integration

Refreshed from S2 {attempt.name}, master revision 3, 6 October 2026.
S2 produced {stats['conditional_rules']} source-bound rules, {stats['development_cases']}
deterministic conditional cases and {stats['case_records']} original-court case records.
All {stats['open_obligations']} original obligations remain OPEN_QUALIFIED. Current
source-to-rule meaning, actual arrangement facts and sufficient discharge standards
remain unresolved. The S2 receipt in this directory is the baseline, alongside the
unchanged S1 inventory of 35 readings, 70 roles and 32 unformalized readings.

## Question and evidence contract

Can observations with exact role, identity, valid interval and knowledge date feed
the proposed conditional standards through CompleteInvestigation without converting
recorded events into legal adequacy or settling a disputed attachment?

Comparator: verified S2 standards and missing-premise ledger, and S1's version-2
investigation context. Primary engineering criterion: the actual route preserves
all source, premise, branch and assessment identities; exclusion, conflict and
missing standards survive serialization, execution and independent stage checks.
Source-to-rule sufficiency and substantive legal closure still require a stated,
independently checked proposition; otherwise retain qualification.

Promotion vetoes: incomplete temporal coverage, unknown interpretation/applicability,
unsupported authority transfer, missing factual classification or lost objections.
Continuation vetoes: corrupted baseline, false provenance, dropped obligations,
invalid checker or unbounded execution. Missing facts and failed source candidates
trigger qualified development, not abandonment of the direction.

## Concrete phases within S3

1. Freeze the exact S2 receipt and current package; audit actual observation and
   investigation interfaces. Specify a new versioned context before changing
   strict version-2 schemas. Preserve historical bytes and unsupported branches.
2. Implement an explicit observation-to-premise adapter. A recorded supervision,
   remediation or reconciliation event must not imply adequate supervision,
   retrospective cure or proper records. Require a separate sufficient-rule
   premise and evidence covering the complete assessment interval.
3. Keep the 14/footnote-5 A/B/C alternatives, their distinct objects/standards and
   paragraph-15/16 request identities through actual investigation. One request
   cannot substitute for another. Negative antecedents are not negated conclusions.
4. Use the case findings to design discriminating inputs: an automated ledger event
   without customer access; changed terms without known acceptance; a trust duty
   between A and B without a proven duty between C and B; and conflicting identity
   or time coverage. These are source-informed development challenges, not legal
   answer labels. Preserve the Gatecoin 2025 paragraph-8/95/annexure tension until
   a source-grounded reconciliation is separately supported.
5. Emit and verify an actual dossier containing standards input, admitted and
   excluded evidence, branch-bound conditional consequences and retained unknowns.
   Independent recomputation must detect a changed source, scope, premise kind,
   evidence identity, condition attachment and post-cutoff event.
6. Run focused checks plus affected investigation/qualification regressions. Write
   an immutable attempt, decision table and red-team note, then refresh S4 from
   actual unsupported constructs and runtime correspondence gaps.

## Defaults, budget and review

Finite sufficient implications and full-interval coverage are the S2 contract,
not general legal semantics. A declaration is not an observation and a quotation
does not establish applicability. Existing original sources are the default;
no provider calls, installation, GPU, private evidence acquisition or new network
budget is implied. Keep S2's 64-rule/1024-evidence profile and existing eight-node
preferred reference bound unless measured, reviewed changes justify a new profile.
Use two causal repair attempts per distinct engineering cause before plan revision.

Skeptical review: PASS_FOR_BOUNDED_IMPLEMENTATION after the new context and adapter
are specified. A synthetic success cannot establish performance on actual client
facts, English correctness, generalization or production readiness. The master
runner does not yet execute S3: implement and review the fixed handler, then add
its exact phase dispatch. Re-running S2 is not S3 execution.

## Further ordering

S4 follows actual integration: broader/recursive theories, supported lowering for
remaining readings, and a new declared-semantics theorem profile with serialization
and runtime correspondence. S5 follows method stabilization and requires genuinely
later official publications in a freshly frozen observation window. Earlier
windows remain historical after these method changes.

Additional source investigation remains a specific parallel research need:
Cheung's full reasons are not yet admitted; one responsibility search lead is
unreviewed; the tokenisation query returned an application error. Case-treatment
coverage, product-specific conditions and governing-law title/settlement rules
remain incomplete. None of these search outcomes establishes absence of law.
"""
def result_note(stats):
    return f"""# S2 executed with qualifications

S2 implements {stats['conditional_rules']} source-bound sufficient implications and
executes {stats['development_cases']} deterministic development cases. Exact original
court passages from two Gatecoin decisions are represented in the existing
opinion-aware model. All 46 original obligations retain their original identities,
role responses, sources and individual missing-premise lists.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept bounded engineering result | Source/scope checks, behavioral tests and deterministic replay pass | No corrupt baseline or dropped obligations | Authored rule inventory is not a proved English translation | Integrate scoped evidence and standards through actual investigation in S3 | Legal discharge, actual compliance or release readiness |
| Retain all substantive obligations open | No independent legal closure supplied | Applicability, sufficiency and facts veto promotion | Dated scheme conditions, authority, ownership and incident standards | Preserve explicit missing premises and acquire specific evidence when available | No relevant law exists |
| Admit limited case context | Official raw documents and exact quoted passages retained | Target transfer and treatment completeness unresolved | Gatecoin insolvency facts differ from the target SFC product | Preserve terms/consent/relationship distinctions and textual tensions | General paragraph 10 or footnote 5 rule |

Engineering correctness, source interpretation and formal validity remain separate:
tests exercise deterministic software behavior; source identity checks locate exact
passages; no new kernel theorem or proof of source-to-rule meaning was produced.
The retained arrangement has no supplied scope or factual premises, so it produces
no unqualified consequence. Synthetic supplied-premise cases demonstrate useful
conditional execution without relabelling those premises true.

Red-team: the strongest alternative explanation for passing cases is a shared
mistake in the authored inventory and its examples. Source quotes and replay would
not detect every such mistake. Separate modalities, request objects and negative
antecedents were challenged; source amendment, identity/date changes, quotation
role, missing interpretation and conflicting support must remain detectable.
The weakest evidence is source-to-rule sufficiency and actual factual coverage.
A counterexample to an encoded implication triggers a new immutable repair attempt;
a missing standard triggers the planned S3 qualification, not a claim of closure.

All {stats['readings_preserved']} readings and {stats['role_records_preserved']} role
records remain byte-bound to S1/P0. No old formulas or historical receipts were
rewritten. Package additions invalidate reuse of historical methods as current
evidence; the master checks their retained integrity separately.
"""
def verify_attempt(path):
    result=read(path/"result.json")
    if result["method"]!=method():raise ValueError("Current method differs from the selected S2 method")
    if result["inputs"]!=inputs():raise ValueError("Baseline input identities changed")
    for row in result["outputs"]:checked(row)
    if read(path/"acquisitions.json")!=acquisitions():raise ValueError("Acquisition packet changed")
    if read(path/"tests.json")["exit_code"]!=0:raise ValueError("Tests did not pass")
    rebuilt=build_outputs()
    for name,value in rebuilt.items():
        if read(path/name)!=value:raise ValueError("Recomputation differs: "+name)
    rows=rebuilt["obligations.json"]
    if len(rows)!=46 or any(r["status"]!="OPEN_QUALIFIED" for r in rows):
        raise ValueError("Invalid obligation dispositions")
    if (result["legal_correctness"],result["english_fidelity"],result["release_eligible"])!=(
            "NOT_ESTABLISHED","NOT_ESTABLISHED",False):raise ValueError("Unsupported promotion")
    history();preserve()
    return {"status":"PASS","phase":"S2","result":ref(path/"result.json"),
        "verification":"Source identity, preserved originals and deterministic recomputation; not a proof of English meaning"}
def selected():
    return read(POINTER) if POINTER.exists() else None
def status():
    h=history();current=selected()
    if current:checked(current["master"]);checked(current["result"]);checked(current["next_phase_plan"])
    return {"program_revision":3,"master":ref(MASTER),"historical":h["status"],
        "completed":["P0","P1","P2","P3","P4","P5","P6","P7","P8","S1"]+(["S2"] if current else []),
        "phase":current["next_phase"] if current else "S2","state":current["state"] if current else "READY_FOR_BOUNDED_S2",
        "open_obligations":46,"english_fidelity":"NOT_ESTABLISHED","release_eligible":False}
def execute():
    history();preserve()
    start=time.monotonic();number=max([int(p.name.split("-")[-1]) for p in BASE.glob("attempt-*")]+[0])+1
    attempt=BASE/f"attempt-{number}";attempt.mkdir()
    frozen=method();acquired=acquisitions()
    try:
        (attempt/"plan.md").write_bytes(PLAN.read_bytes())
        (attempt/"master.md").write_bytes(MASTER.read_bytes())
        save(attempt/"manifest.json",{"command":"python3 -m scripts.run_legal_interpretation_master resume",
            "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "environment":sys.executable,"python":sys.version,
            "cpu_gpu":"CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
            "seeds":"N/A: deterministic development cases","provider_calls":0,
            "started_at":datetime.now(timezone.utc).isoformat(),"method":frozen,"plan":ref(PLAN),
            "data_versions":inputs(),"artifact_directory":str(attempt.relative_to(ROOT)),
            "result_file":str((attempt/"result.json").relative_to(ROOT))})
        save(attempt/"acquisitions.json",acquired)
        command=[sys.executable,"-m","pytest",*TESTS,"-q"]
        with (attempt/"tests.log").open("x") as log:
            tests=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        save(attempt/"tests.json",{"command":command,"exit_code":tests.returncode,"log":ref(attempt/"tests.log")})
        if tests.returncode:
            print((attempt/"tests.log").read_text()[-6000:],flush=True)
            raise ValueError("Required checks failed")
        print(json.dumps({"stage":"checks","status":"PASS","summary":(attempt/"tests.log").read_text().splitlines()[-1]}),flush=True)
        generated=build_outputs()
        for name,value in generated.items():save(attempt/name,value)
        stats={"conditional_rules":len(generated["standards.json"]),"development_cases":len(generated["development-cases.json"]),
            "case_records":len(generated["case-records.json"]["cases"]),"source_findings":len(generated["source-findings.json"]),
            "open_obligations":len(generated["obligations.json"]),"substantive_closures":0,
            "readings_preserved":35,"role_records_preserved":70,"http_attempts":acquired["http_attempts"]}
        (attempt/"next-phase-plan.md").write_text(next_plan(stats,attempt))
        (attempt/"result-note.md").write_text(result_note(stats))
        save(attempt/"preservation.json",preserve())
        if frozen!=method() or acquired!=acquisitions():raise ValueError("Method or evidence changed during execution")
        save(attempt/"result.json",{"status":"IMPLEMENTED_QUALIFIED","phase":"S2","program_revision":3,
            "engineering":stats,"inputs":inputs(),"method":frozen,
            "elapsed_seconds":round(time.monotonic()-start,3),"legal_correctness":"NOT_ESTABLISHED",
            "english_fidelity":"NOT_ESTABLISHED","release_eligible":False,"provider_calls":0,
            "outputs":[ref(p) for p in sorted(attempt.rglob("*")) if p.is_file()]})
        verification=verify_attempt(attempt)
        save(attempt/"verification.json",verification)
        pointer={"program_revision":3,"master":ref(MASTER),"completed_phase":"S2","result":ref(attempt/"result.json"),
            "verification":ref(attempt/"verification.json"),"next_phase":"S3",
            "next_phase_plan":ref(attempt/"next-phase-plan.md"),"state":"S3_REVIEWED_PLAN_REQUIRES_IMPLEMENTATION"}
        tmp=POINTER.with_suffix(".tmp");tmp.write_text(json.dumps(pointer,indent=2)+"\n");tmp.replace(POINTER)
        print(json.dumps({"status":"EXECUTED_AND_VERIFIED","result":ref(attempt/"result.json"),**stats}),flush=True)
    except BaseException as error:
        save(attempt/"failure.json",{"status":"FAILED","error":type(error).__name__,"details":str(error),
            "elapsed_seconds":round(time.monotonic()-start,3)})
        raise
def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument("action",choices=("status","resume","verify"))
    args=parser.parse_args();current=selected()
    if args.action=="status":print(json.dumps(status(),indent=2))
    elif current:
        path=checked(current["result"]).parent
        verified=verify_attempt(path);checked(current["verification"])
        print(json.dumps({**verified,"next_phase":current["next_phase"],"next_phase_plan":current["next_phase_plan"],
            "note":"S2 is complete; S3 requires its reviewed handler and versioned integration before execution."},indent=2))
    elif args.action=="verify":raise ValueError("No selected S2 result; use status or resume")
    else:execute()
if __name__=="__main__":main()
