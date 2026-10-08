"""Fixed offline successor operations; no provider dispatch or shell passthrough."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and Path(sys.prefix) != ROOT / ".venv":
    os.execv(str(ROOT / ".venv/bin/python"), [str(ROOT / ".venv/bin/python"), "-m",
        "scripts.run_legal_interpretation_successor", *sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.canonical import digest
RUN = ROOT / "artifacts/legal-interpretation-program/successor-s1"
P0 = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
PLAN = ROOT / "docs/plans/legal-interpretation-program/S1-reconciliation-and-sourced-arguments.md"
POINTER = ROOT / "docs/implementation/legal-interpretation-program/successor-current.json"
COMPLETION = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/completion-2.json"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def ref(p): return {"path":str(p.relative_to(ROOT)), "sha256":sha(p)}
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as f: json.dump(v,f,indent=2,ensure_ascii=False);f.write("\n")
def files():
    roots = ("src/legalmath","tests")
    return {str(p.relative_to(ROOT)):sha(p) for name in roots for p in sorted((ROOT/name).rglob("*"))
        if p.is_file() and p.suffix in (".py",".json",".java",".lean")}
def inputs():
    return [ref(p) for p in (COMPLETION,P0/"packet.json",P0/"overlay.json",P0/"obligation-map.json")]
def baseline():
    if sha(COMPLETION)!="00787202085da9ee4942a34bf87252a9be5192fe1333075b843edede74bb788d":
        raise ValueError("Wrong completed baseline")
    p=RUN/"baseline.json"
    if p.exists():
        value=read(p)
        if value["inputs"]!=inputs(): raise ValueError("Baseline source changed")
    else:
        value={"at":datetime.now(timezone.utc).isoformat(),"inputs":inputs(),"files":files(),
            "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "git_status":subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True),
            "plan":ref(PLAN)}
        save(p,value)
    print(json.dumps({"baseline":ref(p),"files":len(value["files"])}))
    return value

def dependencies():
    return {str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),
        ROOT/"scripts/legal_interpretation_successor_data.py",ROOT/"scripts/legal_interpretation_demo.py",
        ROOT/"docs/implementation/legal-interpretation-program/s1-final-audit.md",PLAN)}

def preserve(base):
    current=files()
    changed={p for p,h in base["files"].items() if current.get(p)!=h}
    allowed={
        "src/legalmath/interpretation/semantics/lower.py",
        "src/legalmath/interpretation/semantics/integration.py",
        "src/legalmath/interpretation/assurance/complete_investigation.py",
        "src/legalmath/interpretation/assurance/investigation_observations.py",
        "tests/interpretation/semantics/test_integration.py"}
    if not changed<=allowed:
        raise ValueError("Unrelated pre-existing code changed: "+repr(sorted(changed-allowed)))
    if base["inputs"]!=inputs():
        raise ValueError("Original evidence changed")
    return {"status":"PASS","pre_existing_files":len(base["files"]),
        "changed_pre_existing_files":sorted(changed),
        "new_files":sorted(set(current)-set(base["files"])),
        "original_inputs_byte_identical":True}

def next_plan(stats):
    return """# S2 refreshed from S1 execution

S1 has individually reconciled {readings} readings, retained {roles} role records
and bound {claims} source-related claims. It ran {branches} retained semantic
branches and {java_cases} actual Java cases; {unsupported} branches explicitly
remain unsupported for lowering. The actual CompleteInvestigation fixture carried
typed objections through execution, stage binding and verification. Conditional
argument membership is separate from conditional formula evaluation.

All 46 original substantive obligations remain OPEN_QUALIFIED. No substantive
legal repair, English-fidelity proof or suitable precedent was established.

## Next discriminating phase: authority and standards

Question: can a bounded official-source packet supply premises that distinguish
allocation, effective conduct and achieved adequacy, or clarify paragraph 14 /
footnote 5 trigger, object and standard attachment?

Comparator: the source packet and individual claims in this S1 attempt. Retained
readings and formulas stay separate; no frequency or model vote is a comparator.

1. Inspect the retained UT Code, its introduction, the tokenised-securities
   circular and Appendix in their relevant full context. Inventory the precise
   missing applicability, authority, temporal, actor and sufficiency premises for
   each of the 46 obligations. Source acquisition is not proof of applicability.
2. Search a bounded set of official Hong Kong court publications and regulator
   legal sources for the exact responsibility and contextual-interpretation
   questions. Retain query, official URL, publication/edition date, acquisition
   date, bytes and unsuccessful searches. A generic interpretation case is
   method background unless a checked transfer argument connects its holding.
3. For each potentially relevant judgment, retain full reasons, paragraph
   anchors, material facts, issue, opinion role, holding, hierarchy and treatment.
   Citation syntax and an unverified model summary are not acceptance criteria.
4. Express any transfer as a proposed rule with scoped premises and objections.
   Adequate supervision, retained responsibility, proper records and title need
   sufficient rules and correctly joined evidence; recorded supervision alone
   does not establish adequacy. No legal priority follows from code execution.
5. Execute only newly supported finite theories. Keep unknown premises and
   objections. Do not turn prose critical questions into signed attacks without
   a source-bound contrary and target. The existing preferred cap stays eight.
6. Verify source-amendment, contrary-attachment and missing-premise challenges.
   Write an immutable attempt and refresh the next phase from actual findings.

Primary engineering criterion: every new rule and contrary binds a source,
edition, scope, inference and unresolved premises; missing authority stays
explicit. Promotion needs an independently checked stated proposition.
Provenance failure, silently dropped readings or false complete status stop
execution. Failure to find a relevant case is a research result and repair trigger,
not evidence that an arbitrary case settles the law.

Separate later phases remain: independently checked larger/recursive theories;
a new semantics theorem profile with serialization/runtime correspondence; and a
separately frozen study on genuinely later official publications. Existing
windows and receipts are historical after method changes. Future-source evidence
cannot be manufactured from the current packet or this deterministic fixture.

Plan refresh required before S2 execution: record exact official repositories,
search budget, candidate sources and stop conditions after local context review.
No provider call grant, installation or prospective legal result is presumed.
""".format(**stats)

def execute():
    from legalmath.interpretation.semantics import integration
    from legalmath.interpretation.semantics.sourced import context
    from legalmath.interpretation.assurance.complete_investigation import verify as verify_product
    from legalmath.interpretation.assurance import investigation_observations as obs
    from scripts.legal_interpretation_successor_data import make_reconciliation,policy,execute_product
    base=baseline()
    preserve(base)
    RUN.mkdir(parents=True,exist_ok=True)
    number=max([int(p.name.split("-")[-1]) for p in RUN.glob("attempt-*")]+[0])+1
    attempt=RUN/("attempt-"+str(number));attempt.mkdir()
    started=time.monotonic()
    method={"files":files(),"drivers":dependencies()}
    save(attempt/"manifest.json",{"command":"python3 -m scripts.run_legal_interpretation_successor run",
        "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "environment":sys.executable,"python":sys.version,"cpu_gpu":"CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
        "seeds":"N/A: deterministic fixtures","provider_calls":0,"plan":ref(PLAN),"inputs":inputs(),
        "method":method,"started_at":datetime.now(timezone.utc).isoformat(),
        "artifact_directory":str(attempt.relative_to(ROOT)),"result_file":str((attempt/"result.json").relative_to(ROOT))})
    try:
        test_paths=["tests/interpretation/semantics","tests/interpretation/test_contracts.py",
            "tests/assurance/test_closure_references.py","tests/assurance/test_source_derivative.py",
            "tests/assurance/test_investigation_observations.py","tests/assurance/test_continuation_qualification.py",
            "tests/assurance/test_integrated_workflow.py","tests/translation/test_frontend.py",
            "tests/translation/test_qualification_execution.py"]
        command=[sys.executable,"-m","pytest",*test_paths,"-q"]
        with (attempt/"tests.log").open("w") as log:
            tested=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        save(attempt/"tests.json",{"command":command,"exit_code":tested.returncode,"log":ref(attempt/"tests.log")})
        if tested.returncode:
            print((attempt/"tests.log").read_text()[-6000:],flush=True)
            raise ValueError("Required tests failed")
        print(json.dumps({"stage":"tests","status":"PASS","log":ref(attempt/"tests.log")}),flush=True)
        packet,candidates,questions,rec=make_reconciliation(ROOT)
        save(attempt/"reconciliation.json",rec)
        options={"profile":integration.PROFILE,"settings":[policy().model_dump(mode="json")],"case_limit":2}
        ctx=context(reconciliation=rec);jdk=ROOT/".localresources/java-toolchain/jdk-17.0.20.1+1"
        at="2026-10-06T00:00:00.000000Z"
        report=integration.run(packet,candidates,questions,options,attempt/"retained",jdk,at,context=ctx)
        integration.verify(attempt/"retained",packet,candidates,questions,options,at,jdk=jdk,context=ctx)
        print(json.dumps({"stage":"retained","branches":len(report["branch_reports"]),"verified":True}),flush=True)
        root,product,dossier=execute_product(attempt/"product")
        verify_product(root,dossier)
        checked=obs.check_stages(root,dossier,obs.method(product),product)
        save(attempt/"product-verification.json",checked)
        obligations=[{**row,"status":"OPEN_QUALIFIED",
            "disposition":"Source-bound reconciliation and conditional computation; substantive meaning and facts remain unresolved."}
            for row in read(P0/"obligation-map.json")]
        if len(obligations)!=46: raise ValueError("Obligation denominator changed")
        save(attempt/"obligations.json",obligations)
        stats={"readings":rec["reading_count"],"roles":rec["role_count"],
            "claims":sum(len(e["claims"]) for e in rec["entries"].values()),
            "branches":len(report["branch_reports"]),
            "java_cases":sum(len(r["target"]["executions"]) for r in report["branch_reports"]),
            "unsupported":sum(r["target"]["java"]=="UNSUPPORTED" for r in report["branch_reports"]),
            "product_branches":len(dossier["semantic_stage"]["report"]["branch_reports"]),
            "product_java_cases":sum(len(r["target"]["executions"]) for r in dossier["semantic_stage"]["report"]["branch_reports"]),
            "open_obligations":len(obligations)}
        (attempt/"next-phase-plan.md").write_text(next_plan(stats))
        save(attempt/"preservation.json",preserve(base))
        if method!={"files":files(),"drivers":dependencies()}:raise ValueError("Method changed during execution")
        result={"status":"IMPLEMENTED_QUALIFIED","engineering":stats,"method":method,"inputs":inputs(),
            "elapsed_seconds":round(time.monotonic()-started,3),"legal_correctness":"NOT_ESTABLISHED",
            "english_fidelity":"NOT_ESTABLISHED","release_eligible":False,"provider_calls":0,
            "outputs":[ref(p) for p in sorted(attempt.rglob("*")) if p.is_file() and
                not p.name.endswith((".lock","-wal","-shm")) and p.name!=".lock"]}
        save(attempt/"result.json",result)
        POINTER.parent.mkdir(parents=True,exist_ok=True)
        POINTER.write_text(json.dumps({"phase":"S1","result":ref(attempt/"result.json"),
            "next_phase_plan":ref(attempt/"next-phase-plan.md")},indent=2)+"\n")
        print(json.dumps({"result":ref(attempt/"result.json"),**stats}),flush=True)
    except BaseException as error:
        save(attempt/"failure.json",{"status":"FAILED","error":type(error).__name__,"details":str(error),
            "elapsed_seconds":round(time.monotonic()-started,3)})
        raise

def verified():
    from legalmath.interpretation.semantics import integration
    from legalmath.interpretation.assurance.complete_investigation import verify as verify_product
    pointer=read(POINTER);path=ROOT/pointer["result"]["path"]
    if sha(path)!=pointer["result"]["sha256"]:raise ValueError("Current receipt changed")
    result=read(path)
    if result["method"]!={"files":files(),"drivers":dependencies()} or result["inputs"]!=inputs():
        raise ValueError("Stale successor receipt")
    for item in result["outputs"]:
        p=(ROOT/item["path"]).resolve()
        if not p.is_relative_to(ROOT) or sha(p)!=item["sha256"]:raise ValueError("Changed output: "+item["path"])
    attempt=path.parent;retained=attempt/"retained";data=read(retained/"inputs.json")
    integration.verify(retained,*[data[k] for k in ("packet","candidates","questions","options","at")],
        context=data["context"],jdk=ROOT/".localresources/java-toolchain/jdk-17.0.20.1+1")
    dossier=read(ROOT/read(attempt/"product/current.json")["path"])
    verify_product(ROOT,dossier)
    preserve(read(RUN/"baseline.json"))
    print(json.dumps({"status":"VERIFIED","result":pointer["result"],**result["engineering"]}),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=("baseline","test","run","verify"))
    args=parser.parse_args()
    if args.action=="baseline":baseline()
    elif args.action=="test":
        command=[sys.executable,"-m","pytest","tests/interpretation/semantics/test_reconciliation.py","-q"]
        raise SystemExit(subprocess.run(command,cwd=ROOT,timeout=300).returncode)
    elif args.action=="run":execute()
    else:verified()
if __name__=="__main__":main()
