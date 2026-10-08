"""Fixed offline S3 execution, historical integrity, replay and S4 refresh."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from scripts import run_legal_interpretation_master as master

ROOT = master.ROOT
BASE = ROOT / "artifacts/legal-interpretation-program/successor-s3"
PLAN = ROOT / "docs/plans/legal-interpretation-program/S3-scoped-evidence-and-investigation.md"
AUDIT = master.DOC / "s3-execution-audit.md"
BASELINE_SHA = "bc21fdd64ca53ad7addf109b8a25f2af35c43805283183dfc93a76f09ec8e696"
S2_SHA = "b4c73d1e47ec07634554263355bdd8a84bb73364b3320a91a06ef46a51988f6c"
ALLOWED = {
    "src/legalmath/interpretation/semantics/integration.py",
    "src/legalmath/interpretation/assurance/complete_investigation.py",
    "src/legalmath/interpretation/assurance/investigation_observations.py",
    "tests/interpretation/semantics/test_master_resume.py",
}
TESTS = master.TESTS + ["tests/assurance/test_successor_workflow.py",
    "tests/assurance/test_integration.py", "tests/assurance/test_challenge_integration.py"]
read, sha, ref, save, checked = master.read, master.sha, master.ref, master.save, master.checked


def historical():
    baseline = checked({"path": str((BASE / "baseline.json").relative_to(ROOT)), "sha256": BASELINE_SHA})
    frozen = read(baseline)
    for row in frozen["files"]:
        checked(row)
    current = frozen["s2_pointer"]
    path = checked(current["result"])
    if sha(path) != S2_SHA:
        raise ValueError("Wrong S2 predecessor")
    for key in ("verification", "next_phase_plan"):
        checked(current[key])
    for row in read(path)["outputs"]:
        checked(row)
    if frozen["s2_verification_before_edits"]["status"] != "PASS":
        raise ValueError("S2 was not verified before changes")
    master.history()
    return {"status": "PASS", "s2": ref(path), "snapshot_files": len(frozen["files"]),
        "scope": "Exact historical bytes and recorded pre-edit verification; not current-method execution"}


def preservation():
    baseline = read(BASE / "baseline.json")
    now = master.files()
    changed = sorted(p for p, h in baseline["source_and_tests"].items() if now.get(p) != h)
    if set(changed) - ALLOWED:
        raise ValueError("Unreviewed pre-existing file changes: " + repr(sorted(set(changed) - ALLOWED)))
    return {"baseline_files": len(baseline["source_and_tests"]), "changed": changed,
        "unchanged": len(baseline["source_and_tests"]) - len(changed),
        "added": sorted(set(now) - set(baseline["source_and_tests"])),
        "historical_originals": ref(BASE / "baseline.json")}


def method():
    drivers = [Path(__file__), ROOT / "scripts/run_legal_interpretation_master.py",
        ROOT / "scripts/legal_interpretation_s3_data.py", ROOT / "scripts/legal_interpretation_s3_prepare.py",
        master.MASTER, PLAN, AUDIT]
    drivers += sorted((ROOT / "scripts").glob("legal_interpretation_s2_*.py"))
    drivers += [ROOT / "scripts/legal_interpretation_demo.py"]
    return {"source_and_tests": master.files(),
        "drivers": {str(p.relative_to(ROOT)): sha(p) for p in drivers}}


def derived():
    from scripts.legal_interpretation_s3_data import retained_inputs, product_inputs
    from legalmath.interpretation.semantics.scoped_standards import compute
    source, supplied = retained_inputs()
    _, projected, product, provenance = product_inputs()
    return {"development-inputs.json": {"packet": source, "standards_input": supplied},
        "development-computation.json": compute(supplied, source, {}, {}, []),
        "product-inputs.json": {"packet": projected, "standards_input": product},
        "projection-provenance.json": provenance}


def summary(dossier, checked_stages):
    report = dossier["semantic_stage"]["report"]
    scoped = report["standards"]
    rules = scoped["evaluation"]["results"]
    return {"source_bound_rules_preserved": 14, "diagnostic_hypotheses": 6,
        "actual_semantic_branches": len(scoped["branches"]),
        "branch_conditional_records": sum(len(b["results"]) for b in scoped["branches"]),
        "admitted_observations": sum(e["admitted"] for e in scoped["observation_admission"]),
        "excluded_observations": sum(not e["admitted"] for e in scoped["observation_admission"]),
        "conditional_rules": sum(r["status"] == "CONDITIONALLY_DERIVED" for r in rules),
        "not_derived_rules": sum(r["status"] == "NOT_DERIVED" for r in rules),
        "java_cases": sum(len(r["target"]["executions"]) for r in report["branch_reports"]),
        "whole_stage_checked": checked_stages["execution_complete"],
        "open_obligations": 46, "readings_preserved": 35, "role_records_preserved": 70,
        "substantive_closures": 0, "live_provider_calls": 0}


def next_plan(stats):
    return f"""# S4: declared semantics, broader theories and runtime correspondence

Refreshed from executed S3 under master revision 3, 6 October 2026.
The adjacent result.json binds the exact method and evidence. S3 executed
{stats['actual_semantic_branches']} actual semantic branches, preserving A/B/C
attachments and {stats['branch_conditional_records']} branch-bound conditional
records, with {stats['java_cases']} Java cases. The fourteen S2 source-bound rules
remain unchanged in meaning; six extra implications are labelled diagnostic
hypotheses. All 46 substantive obligations remain OPEN_QUALIFIED.

## Research intent and evidence contract

Question: can a precisely declared broader rule/argument language have a checked
semantics and faithful serialization/runtime implementation without claiming that
its legal premises are true? Compare the verified S3 finite sufficient-implication
evaluator, v3 transport and existing acyclic source-argument implementation.

Primary criteria: a kernel-checked proposition for the declared semantics,
validated codecs and independent runtime correspondence over its supported domain;
every retained unsupported reading remains identified. Synthetic agreement is a
diagnostic, not a proof of source-to-rule meaning or universal implementation
correctness. Lost alternatives, unsupported negation/priorities, missing premises,
branch/formula conflation and invalid runtime correspondence veto promotion.
Corrupted evidence, inconsistent semantic specification, an invalid checker and
unbounded execution veto continuation. Expected unsupported constructs trigger
the next bounded repair.

## Concrete phases

1. Freeze S3 bytes before any method edit. Inventory unsupported constructs from
   the 35 retained readings, existing argument profiles, and S3 standards receipts.
   Preserve the 32 S1 readings without formalization. A trigger-only formula is
   not an encoding of an entire duty, object, standard, or discharge judgment.
2. Specify the smallest useful extension and its mathematical semantics. Decide
   explicitly whether recursive derivation uses a monotone least fixed point,
   finite argument unfolding or a separately bounded qualified profile. Do not
   mix these semantics silently. State domains, termination and conflict rules.
3. State and implement a theorem profile for four-state support and sufficient
   implications. Prove the chosen property (for example derivation requires all
   declared antecedents), with negative antecedents never proving the opposite.
   Relate the specification to encoded inputs; retain assumptions and trust boundary.
4. Implement only the reviewed supported lowering. S3 conditional standards are
   currently computed in Python, separately from legacy Boolean Java outputs;
   standards lowering is NOT_IMPLEMENTED and their relationship is NOT_ESTABLISHED.
   Add serialization/decoder rejection and evaluator/backend correspondence checks
   before making a new runtime claim. Preserve unsupported cases explicitly.
5. Expand actual-route development only for newly supported constructs. Retain
   A/B/C object/standard differences, source/premise identities, rejected evidence
   and all obligations. Test cycles, no-support, conflict, incomplete graph,
   malformed inputs and resource bounds without legal answer labels.
6. Execute required affected regressions, independent kernel/runtime checking,
   immutable attempts and a red-team decision note. Refresh S5 only from the
   resulting method and actual residual gaps.

## Defaults and pre-mortem

The existing eight-node preferred reference bound, 64 standards and 1024 total
evidence rows are baselines; a larger or recursive domain needs a measured and
reviewed bound. A theorem about a finite Python-like list does not automatically
cover serialized JSON, Java, source extraction or arbitrary recursive theories.
An English-looking rule with a successful proof can still be the wrong reading.

Audit status: READY_FOR_SPECIFICATION_REVIEW. Before implementation, inspect the
current Lean theorem profiles and actual unsupported inventory, select a concrete
theorem/extension, write its derivation and runtime relation, and audit inherited
defaults. No new mathematical proposition or general recursive algorithm is
pre-approved by this title. Missing legal evidence is a promotion veto only;
continue the authorized engineering after the specific design passes audit.

Use two causal repairs per cause before plan revision. Use installed CPU tools;
no live model/provider, network retrieval, installation or GPU budget is implied.
S5 requires a newly frozen method and genuinely later official publications.
Old observations remain historical after any S4 method change.

Remaining source questions include scheme-specific conditions, governing-law
title and settlement, legal sufficiency of control evidence, full case-treatment
coverage, Cheung reasons and the Gatecoin 2025 paragraph-8/95/annexure tension.
Their absence neither establishes absence of law nor stops qualified S4 work.
"""


def note(stats, tests):
    return f"""# S3 executed with qualifications

The versioned v3 context transports scoped events, declared premises and proposed
standard attachments through CompleteInvestigation and its independent stage
checker. {tests['summary']} The actual retained-text fixture produced
{stats['actual_semantic_branches']} semantic branches and {stats['java_cases']}
legacy-trigger Java cases. This validates deterministic engineering only.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept bounded v3 integration | Actual dossier, source projection, scope exclusions, branch identities and whole-stage replay checked | No lost obligations or corrupt baseline | Authored attachment and legal sufficiency remain unproved | S4 semantics and correspondence design | English fidelity or actual legal compliance |
| Preserve all 46 substantive obligations open | No new substantive closure evidence | Missing facts, authority and standards veto promotion | Scheme conditions, applicable law and sufficient discharge criteria | Continue qualified development | No applicable law exists |
| Retain standards as a distinct conditional computation | Observed events cannot supply missing authority or inference premises | Conflicting and incomplete evidence retained | Standards have no backend lowering or kernel correspondence theorem yet | Implement a stated S4 theorem and supported lowering | Java trigger outputs validate standards |

The fourteen S2 rules retain their consequences, modalities and requirements.
Six additional implications are explicit diagnostic hypotheses motivated by the
source findings. They do not add six legal rules. Synthetic premises make selected
conditional calculations possible; their truth is not established. Evidence text
hashes bind supplied bytes only. The source fixture is a local assembly of exact
retained SFC quotations, not a new official publication or HTTP retrieval.

Red-team: the strongest alternative explanation for passing checks is a shared
misinterpretation in an authored rule and its examples. The narrow recorded-event
vocabulary prevents automatic adequacy claims but cannot authenticate supplied
premises or prove that an event description is true. Whole-interval coverage is a
declared admission rule, not a general legal theorem; combining partial coverage
is unsupported. A changed encoded attachment is detected by identity, while the
original attachment's legal meaning remains unresolved. A counterexample to the
declared transformation requires repair; it would not by itself reject the wider
research direction. Missing source-to-rule proof is the weakest evidence.

Separate ledgers: engineering transport/replay passes; standards' kernel theorem
and backend lowering remain pending; substantive source interpretation remains
NOT_ESTABLISHED. No human or model agreement is used as legal quality evidence.
Historical S2 files are preserved and verified as historical bytes, rather than
rerun under changed dependencies. No provider calls, network retrieval or GPU use.
"""


def verify_attempt(path):
    from scripts.legal_interpretation_s3_data import runner_for, ROOT as data_root
    from legalmath.interpretation.assurance.investigation_observations import method as actual_method, check_stages
    historical()
    result = read(path / "result.json")
    if result["phase"] != "S3" or result["method"] != method():
        raise ValueError("Current method differs from selected S3 method")
    for row in result["outputs"]:
        checked(row)
    if read(path / "tests.json")["exit_code"] != 0:
        raise ValueError("Required tests failed")
    for name, value in derived().items():
        if read(path / name) != value:
            raise ValueError("S3 recomputation differs: " + name)
    original = master.BASE / "attempt-1/obligations.json"
    if (path / "obligations.json").read_bytes() != original.read_bytes():
        raise ValueError("Original obligations changed")
    ledger = read(path / "obligations.json")
    if len(ledger) != 46 or any(r["status"] != "OPEN_QUALIFIED" for r in ledger):
        raise ValueError("Substantive closure unsupported")
    runner = runner_for(path / "product")
    dossier = read(checked(result["dossier"]))
    stages = check_stages(data_root, dossier, actual_method(runner), runner)
    if stages != read(path / "whole-stage-verification.json"):
        raise ValueError("Actual stage recomputation differs")
    if result["engineering"] != summary(dossier, stages):
        raise ValueError("S3 summary differs")
    if (result["english_fidelity"], result["legal_correctness"], result["release_eligible"]) != (
            "NOT_ESTABLISHED", "NOT_ESTABLISHED", False):
        raise ValueError("Unsupported promotion")
    if preservation() != read(path / "preservation.json"):
        raise ValueError("Preservation identity changed")
    return {"status": "PASS", "phase": "S3", "result": ref(path / "result.json"),
        "scope": "Historical integrity, deterministic recomputation and actual whole-stage runtime verification"}


def execute():
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / ".master.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute()


def _execute():
    from scripts.legal_interpretation_s3_data import execute_product
    from legalmath.interpretation.assurance.investigation_observations import method as actual_method, check_stages
    historical()
    preserved = preservation()
    current = master.selected()
    checked(current["master"])
    checked(current["next_phase_plan"])
    if current["completed_phase"] != "S2" or current["next_phase"] != "S3":
        raise ValueError("S3 requires the selected S2 predecessor")
    failures = [read(p) for p in BASE.glob("attempt-*/failure.json")]
    if sum(f["plan_sha256"] == sha(PLAN) and f["audit_sha256"] == sha(AUDIT) for f in failures) >= 2:
        raise ValueError("Two S3 failures: revise the cause audit before another attempt")
    number = max([int(p.name.split("-")[-1]) for p in BASE.glob("attempt-*")] + [0]) + 1
    attempt = BASE / f"attempt-{number}"
    attempt.mkdir()
    start = time.monotonic()
    frozen = method()
    try:
        (attempt / "plan.md").write_bytes(PLAN.read_bytes())
        (attempt / "master.md").write_bytes(master.MASTER.read_bytes())
        save(attempt / "manifest.json", {"command": "python3 -m scripts.run_legal_interpretation_master resume",
            "git_commit": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "dirty_baseline": ref(BASE / "baseline.json"), "environment": sys.executable, "python": sys.version,
            "cpu_gpu": "CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
            "seeds": "N/A: deterministic development", "started_at": datetime.now(timezone.utc).isoformat(),
            "source_versions": historical(), "method": frozen, "plan": ref(PLAN),
            "provider_calls": 0, "network_requests": 0,
            "result_file": str((attempt / "result.json").relative_to(ROOT))})
        command = [sys.executable, "-m", "pytest", *TESTS, "-q", "--tb=short"]
        print(json.dumps({"stage":"required-checks","attempt":str(attempt.relative_to(ROOT))}),flush=True)
        with (attempt / "tests.log").open("x") as log:
            test_run = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1200,
                env={**os.environ, "CUDA_VISIBLE_DEVICES":"-1"})
        lines = (attempt / "tests.log").read_text().splitlines()
        test_result = {"command":command,"exit_code":test_run.returncode,
            "summary":lines[-1] if lines else "No test output", "log":ref(attempt / "tests.log")}
        save(attempt / "tests.json",test_result)
        if test_run.returncode:
            print("\n".join(lines[-50:]),flush=True)
            raise ValueError("Required S3 tests failed")
        print(json.dumps({"stage":"required-checks","status":"PASS","summary":test_result["summary"]}),flush=True)
        for name,value in derived().items():
            save(attempt / name,value)
        (attempt / "obligations.json").write_bytes((master.BASE / "attempt-1/obligations.json").read_bytes())
        print(json.dumps({"stage":"actual-investigation"}),flush=True)
        runner,dossier,provenance = execute_product(attempt / "product")
        stages = check_stages(ROOT,dossier,actual_method(runner),runner)
        if not stages["execution_complete"]:
            raise ValueError("Actual S3 investigation incomplete")
        save(attempt / "whole-stage-verification.json",stages)
        stats=summary(dossier,stages)
        save(attempt / "preservation.json",preserved)
        (attempt / "next-phase-plan.md").write_text(next_plan(stats))
        (attempt / "result-note.md").write_text(note(stats,test_result))
        if frozen!=method() or preservation()!=preserved:
            raise ValueError("Method changed during S3 execution")
        dossier_ref=read(attempt / "product/current.json")
        save(attempt / "result.json",{"status":"IMPLEMENTED_QUALIFIED","phase":"S3","program_revision":3,
            "method":frozen,"predecessor":ref(master.BASE / "attempt-1/result.json"),"engineering":stats,
            "dossier":dossier_ref,"elapsed_seconds":round(time.monotonic()-start,3),
            "english_fidelity":"NOT_ESTABLISHED","legal_correctness":"NOT_ESTABLISHED","release_eligible":False,
            "outputs":[ref(p) for p in sorted(attempt.rglob("*")) if p.is_file() and
                p.name!=".lock" and not p.name.endswith((".lock","-wal","-shm"))]})
        verification=verify_attempt(attempt)
        save(attempt / "verification.json",verification)
        pointer={"program_revision":3,"master":ref(master.MASTER),"completed_phase":"S3",
            "result":ref(attempt / "result.json"),"verification":ref(attempt / "verification.json"),
            "next_phase":"S4","next_phase_plan":ref(attempt / "next-phase-plan.md"),
            "state":"S4_REQUIRES_SPECIFICATION_REVIEW_AND_IMPLEMENTATION"}
        temporary=master.POINTER.with_suffix(".tmp")
        temporary.write_text(json.dumps(pointer,indent=2)+"\n")
        temporary.replace(master.POINTER)
        print(json.dumps({"status":"EXECUTED_AND_VERIFIED","result":pointer["result"],**stats}),flush=True)
    except BaseException as error:
        save(attempt / "failure.json",{"status":"FAILED","error":type(error).__name__,"details":str(error),
            "plan_sha256":sha(PLAN),"audit_sha256":sha(AUDIT),"elapsed_seconds":round(time.monotonic()-start,3)})
        raise
