"""Fixed offline S4 execution, kernel replay and evidence-based S5 refresh."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from scripts import run_legal_interpretation_master as master
from scripts import legal_interpretation_s3_execute as s3
from scripts import legal_interpretation_s4_data as data

ROOT = master.ROOT
BASE = ROOT / "artifacts/legal-interpretation-program/successor-s4"
PLAN = ROOT / "docs/plans/legal-interpretation-program/S4-conditional-runtime-and-proofs.md"
AUDIT = master.DOC / "s4-execution-audit.md"
BASELINE_SHA = "d36af67e9cfbe397ddfe36075d8cf4e409f1eb8b919337e1c4e2a8a8c44d0540"
S3_SHA = "722f5907e3edcf95cadadfae7bfd6ded0cfd881dd95a1ce61c69df2727601b92"
ALLOWED = {
    "src/legalmath/interpretation/semantics/integration.py",
    "tests/interpretation/semantics/test_master_resume.py",
}
TESTS = s3.TESTS
read, sha, ref, save, checked = master.read, master.sha, master.ref, master.save, master.checked
JDK = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"


def historical():
    path = checked({"path": str((BASE / "baseline.json").relative_to(ROOT)), "sha256": BASELINE_SHA})
    frozen = read(path)
    for row in frozen["files"]:
        checked(row)
    selected = frozen["s3_pointer"]
    result_path = checked(selected["result"])
    if sha(result_path) != S3_SHA:
        raise ValueError("Wrong S3 predecessor")
    for key in ("verification", "next_phase_plan"):
        checked(selected[key])
    for row in read(result_path)["outputs"]:
        checked(row)
    if frozen["s3_verification_before_edits"]["status"] != "PASS":
        raise ValueError("S3 not verified before changes")
    s3.historical()
    return {"status": "PASS", "s3": ref(result_path), "snapshot_files": len(frozen["files"]),
        "scope": "Exact historical bytes and pre-edit verification; not current-method execution"}


def preservation():
    baseline = read(BASE / "baseline.json")
    now = master.files()
    changed = sorted(p for p, h in baseline["source_and_tests"].items() if now.get(p) != h)
    if set(changed) - ALLOWED:
        raise ValueError("Unreviewed pre-existing file changes: " + repr(sorted(set(changed) - ALLOWED)))
    # Packaging was already dirty. Preserve every byte except the two new resource patterns.
    packaging = (ROOT / "pyproject.toml").read_text()
    addition = ', "interpretation/semantics/*.lean", "interpretation/semantics/*.java"'
    from legalmath.canonical import raw_digest
    if packaging.count(addition) != 1 or raw_digest(packaging.replace(addition, "").encode()) != (
            "8206b263d4208b311205c79c07394311273e7979c3af87bffdcdac25a1e0f0c2"):
        raise ValueError("Unreviewed packaging change")
    return {"baseline_files": len(baseline["source_and_tests"]), "changed": changed,
        "unchanged": len(baseline["source_and_tests"]) - len(changed),
        "added": sorted(set(now) - set(baseline["source_and_tests"])),
        "packaging": "Only new Lean/Java resource patterns; pre-existing dirty content preserved",
        "historical_originals": ref(BASE / "baseline.json")}


def method():
    from legalmath.interpretation.semantics import conditional_runtime as runtime
    drivers = [Path(__file__), ROOT / "scripts/run_legal_interpretation_master.py",
        ROOT / "scripts/legal_interpretation_s4_data.py", ROOT / "scripts/legal_interpretation_s4_prepare.py",
        ROOT / "scripts/legal_interpretation_successor_data.py", ROOT / "scripts/legal_interpretation_demo.py",
        ROOT / "pyproject.toml", master.MASTER, PLAN, AUDIT]
    drivers += sorted((ROOT / "scripts").glob("legal_interpretation_s2_*.py"))
    drivers += sorted((ROOT / "scripts").glob("legal_interpretation_s3_*.py"))
    return {"source_and_tests": master.files(),
        "drivers": {str(p.relative_to(ROOT)): sha(p) for p in drivers},
        "tools": {"java": runtime.targets(JDK), "lean": ref(runtime.LEAN) if runtime.LEAN.is_relative_to(ROOT)
                  else {"path": str(runtime.LEAN), "sha256": sha(runtime.LEAN)}}}


def derived():
    from legalmath.interpretation.semantics.conditional_ir import lower
    values = s3.derived()
    # Direct comparison to the verified predecessor keeps every source rule unchanged.
    old = read(BASE / "baseline.json")["s3_pointer"]["result"]
    folder = checked(old).parent
    for name, value in values.items():
        if value != read(folder / name):
            raise ValueError("S3 source/evidence computation changed: " + name)
    program, mapping = lower(values["development-computation.json"])
    return {**values, "reading-inventory.json": data.reading_inventory(),
        "development-program.json": program.model_dump(mode="json"),
        "development-lowering.json": mapping}


def summary(dossier, stages, receipts, inventory):
    stats = s3.summary(dossier, stages)
    report = dossier["semantic_stage"]["report"]
    conditional = report["conditional_runtime"]
    runtime = conditional["runtime"]
    stats.update({"semantic_profile": report["profile"],
        "standards_runtime_heads": len(runtime["java"]["decoded"]["heads"]),
        "standards_runtime_derived": len(runtime["java"]["derived"]),
        "standards_kernel_status": runtime["kernel"]["status"],
        "runtime_branch_records": sum(len(b["rule_results"]) for b in conditional["branches"]),
        "recursive_scenarios_kernel_checked": len(receipts),
        "unformalized_readings": sum(r["formalization"] == "UNFORMALIZED" for r in inventory["readings"])})
    if stats["standards_kernel_status"] != "KERNEL_CHECKED" or stats["runtime_branch_records"] != stats["branch_conditional_records"]:
        raise ValueError("Missing actual branch runtime proofs")
    return stats


def next_plan(stats):
    return f"""# S5: remaining interpretation work and a fresh prospective method

Refreshed from executed S4, master revision 3. The adjacent result binds exact
methods and evidence. S4 kernel-checked the actual Java result for
{stats['standards_runtime_heads']} declared conditional standards, attached it to
{stats['runtime_branch_records']} branch records, and checked
{stats['recursive_scenarios_kernel_checked']} explicitly synthetic recursive scenarios.
There are still {stats['unformalized_readings']} unformalized readings and 46
OPEN_QUALIFIED obligations. English fidelity and legal correctness remain
NOT_ESTABLISHED. These counts describe the preserved work, not legal accuracy.

## Review of the next phase

A fresh observation window alone cannot repair source-to-rule meaning. S4 proves
least derivability for the encoded fixed-evidence positive Horn theory. It does
not settle what responsibility, adequacy, requests or legal discharge mean, and
it does not infer recursive rules from prose. Do prerequisite source and lowering
work before freezing a method that will be advertised as observing unseen sources.

## Research intent and evidence contract

Question: which guarantees can the qualified investigation carry to genuinely
later official publications, while retaining unsupported inputs and alternatives?
Baseline: this immutable S4 method, its 35 individual readings, 14 source-bound
rules, six diagnostic hypotheses, 46 open obligations and qualified proof scope.

Primary engineering criteria: exact source identity; individually justified
source-to-rule relations or explicit qualification; actual v4 execution and
regenerated kernel/runtime receipts; a frozen whole-method window established
before admission of later publications. An observation must retain every
unfinished and unsupported task, not just successes. No observation count or
synthetic score proves English correctness or unrestricted generalization.

Promotion vetoes: missing applicability or factual/sufficiency premise, changed
method during observation, unknown publication timing, incomplete source
provenance, unsupported negative recursion/priorities or lost alternatives.
Continuation vetoes: corrupt evidence, false provenance, invalid checking,
unbounded execution or an external action beyond its authorization.
A failed interpretation candidate triggers a documented repair in development;
it does not by itself reject the research direction.

## Concrete phases

1. Preserve S4 before any method edits, including this plan and the exact method
   and tool hashes. Verify the selected receipt once before freezing historical
   dependencies; never rerun a changed method and call it historical execution.
2. Review reading-inventory.json individually against the retained originals.
   For paragraph 10, separate responsibility, conduct and adequacy. For paragraph
   14/footnote 5, preserve A/B/C objects, standards and request attachment.
   Select one still unsupported construct only after stating its semantics,
   intended source proposition and smallest discriminating counterexample.
   Produce a supported lowering or retain an explicit unresolved relation.
   Never invent formulas merely to reduce the unsupported count.
3. Keep missing legal inputs distinct: scheme conditions, governing-law title
   and settlement, adequate control/discharge evidence, opinion role and later
   case treatment. Inspect any admitted full reasons before extending a rule.
   Cheung reasons and the Gatecoin 2025 paragraph-8/95/annexure tension remain
   open. A failed search is not evidence that no relevant law exists.
   Existing S2 acquisition used 22 of 24 requests; no renewed retrieval budget
   or fresh model grant is created here.
4. Audit proof boundaries after any semantic extension. The present profile
   admits only fixed positive-only facts and positive derived heads. Negative
   recursion, dynamic contrary generation and recursive defeasible arguments
   require a different reviewed specification. Source lowering and codecs have
   independent finite checks, not universal compiler proofs.
5. Implement and test a fixed S5 handler before enabling dispatch. Freeze the
   reviewed whole method, source families, publication/knowledge cutoffs, end
   date, all development source hashes, unfinished-work policy and resource
   limits. Record the actual freeze time; do not backdate it. Current retained
   SFC excerpts, synthetic scenarios and old windows are development/history.
6. Admit only genuinely later official publications with documented publication
   dates and retained raw bytes. Execute through the configured actual route,
   retain exclusions/failures, and independently recheck the full dossier.
   If no eligible publication is available, report AWAITING_ELIGIBLE_SOURCE,
   preserve the empty window, and continue authorized prerequisite work.
   Do not fabricate observations or call an empty window a generalization result.
7. Treat any repair as a new development method and open a new window afterward.
   Write a decision table, source limitations, counterexamples and the next
   phase plan. Keep engineering, theorem validity and legal interpretation
   conclusions separate. No human answer labels or model votes are allowed.

## Defaults, bounds and review

Keep the 64-head/rule, 1024-fact and 32-antecedent positive profile and eight-node
preferred argument bound unless a specific counterexample justifies reviewed
change. Pinned CPU tools are the S4 baseline. Any live provider, retrieval,
installation or new external scope needs a concrete bounded plan; old campaign
allowances are not reusable. Two causal repairs precede a plan/audit revision.

Pre-mortem: a polished dossier can prove the wrong supplied legal rule. Preserve
premise identity and exact theorem scope. Existing-source replay can pass while
telling us nothing about future publications; actual freeze/admission dates and
development exclusions expose that error. Missing substantive evidence blocks
promotion, not qualified development.

Audit verdict: READY_FOR_PREREQUISITE_REVIEW. S5 has no implementation selected
by this receipt. Its detailed next work is determined by the preserved reading
inventory and explicit source gaps, not by a claim that interpretation is solved.
"""


def note(stats, tests):
    return f"""# S4 executed with qualifications

{tests['summary']}. The actual v4 investigation produced
{stats['actual_semantic_branches']} branches, {stats['runtime_branch_records']}
branch-bound conditional records, and a kernel-checked Java result for
{stats['standards_runtime_heads']} declared standards
({stats['standards_runtime_derived']} derived). All
{stats['recursive_scenarios_kernel_checked']} retained synthetic recursive
invocations also have regenerated Lean proofs.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept bounded conditional runtime | Actual decoded input equals requested theory; returned set proved sound and closed | No codec, cycle-support, closure or branch-identity failure in required checks | Toolchain and source-lowering correctness are not universally proved | Preserve S4 and audit S5 prerequisites | Legal correctness or general compiler correctness |
| Retain all original readings and obligations | 35 individually identified readings, 70 role records and 46 unchanged open obligations | Missing source, applicability and sufficiency premises block promotion | 32 readings have no formalization; three formulas remain qualified | Specific source-to-rule investigation | English interpretation repaired |
| Keep theorem scope explicit | Generic leastness theorem plus each actual invocation checked by pinned Lean | Arbitrary axioms and sorryAx rejected; propext/Quot.sound explicitly reported | Numeric proof encoder and supplied premises remain trust boundaries | Extend only through a reviewed semantic specification | General recursive defeasible reasoning |
| Prepare later observation only after review | Refreshed S5 states prerequisites and actual future-publication constraints | Current sources are development; no future evidence exists in this run | Stable method and eligible later publications | Freeze a fresh whole-method window after prerequisites | Future legal generalization |

Engineering, formal validity and source interpretation are distinct. Python's
synchronous evaluator, Java's agenda evaluator and finite closed-set enumeration
agree under the declared test domain. The generic Lean theorem says any sound
closed set equals inductive derivability; each retained runtime result has those
properties checked for its exact numeric input. This is stronger than sampled
agreement but does not prove either interpreter correct on every input.

The S3 scoped-computation report is retained unchanged, including its historical
Python-layer NOT_IMPLEMENTED lowering marker. The additional v4
conditional_runtime receipt records the new standards lowering and runtime proof.
The relation to legacy Boolean trigger formulas remains NOT_ESTABLISHED.

Four-state admission excludes unknown, negative-only and conflicting premises.
Non-derivation does not prove a negated legal consequence. Positive recursive
heads depend on fixed evidence; dynamic negatives and recursive defeasible
arguments remain unsupported. A seeded cycle can propagate its seed; an unseeded
cycle supplies no proof.

Red-team: the strongest alternative explanation for useful-looking results is a
shared source misinterpretation in an authored standard and its examples. The
theorem would still hold for that wrong legal premise. A source-grounded
counterexample would require revising the premise and invalidate dependent
receipts. The weakest evidence is English-to-rule fidelity and actual client
facts. Evidence truth, authority, duty sufficiency and discharge remain unresolved.
The new profile does not reject the research direction or close a legal gap by
counting successful tests.

S3 bytes were verified before edits and frozen in 606 files. Historical integrity
is checked separately from current execution. No live providers, network requests,
installations, GPU actions or human quality labels were used.
"""


def verify_attempt(path):
    from legalmath.interpretation.semantics import conditional_runtime as runtime
    from legalmath.interpretation.assurance.investigation_observations import method as actual_method, check_stages
    historical()
    result = read(path / "result.json")
    if result["phase"] != "S4" or result["method"] != method():
        raise ValueError("Current method differs from selected S4 method")
    for row in result["outputs"]:
        checked(row)
    if read(path / "tests.json")["exit_code"] != 0:
        raise ValueError("Required tests failed")
    values = derived()
    for name, value in values.items():
        if read(path / name) != value:
            raise ValueError("S4 recomputation differs: " + name)
    original = master.BASE / "attempt-1/obligations.json"
    if (path / "obligations.json").read_bytes() != original.read_bytes():
        raise ValueError("Original obligations changed")
    obligations = read(path / "obligations.json")
    if len(obligations) != 46 or any(r["status"] != "OPEN_QUALIFIED" for r in obligations):
        raise ValueError("Substantive closure unsupported")
    receipts = {}
    for name, program in data.recursive_programs().items():
        receipts[name] = runtime.verify(program, path / "recursive" / name, jdk=JDK)
    if read(path / "recursive-results.json") != receipts:
        raise ValueError("Recursive receipt mismatch")
    runner = data.runner_for(path / "product")
    dossier = read(checked(result["dossier"]))
    stages = check_stages(ROOT, dossier, actual_method(runner), runner)
    if stages != read(path / "whole-stage-verification.json"):
        raise ValueError("Whole-stage recomputation differs")
    if result["engineering"] != summary(dossier, stages, receipts, values["reading-inventory.json"]):
        raise ValueError("S4 summary differs")
    if (result["english_fidelity"], result["legal_correctness"], result["release_eligible"]) != (
            "NOT_ESTABLISHED", "NOT_ESTABLISHED", False):
        raise ValueError("Unsupported promotion")
    if read(path / "preservation.json") != preservation():
        raise ValueError("Preservation identity changed")
    return {"status": "PASS", "phase": "S4", "result": ref(path / "result.json"),
        "scope": "Historical integrity, source-lowering recomputation, fresh Java/Lean and whole-stage verification"}


def execute():
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / ".master.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute()


def _execute():
    from legalmath.interpretation.semantics import conditional_runtime as runtime
    from legalmath.interpretation.assurance.investigation_observations import method as actual_method, check_stages
    historical()
    preserved = preservation()
    current = master.selected()
    checked(current["master"])
    checked(current["next_phase_plan"])
    if current["completed_phase"] != "S3" or current["next_phase"] != "S4":
        raise ValueError("S4 requires selected S3 predecessor")
    if current["result"] != historical()["s3"]:
        raise ValueError("Selected predecessor differs")
    failures = [read(p) for p in BASE.glob("attempt-*/failure.json")]
    if sum(f["plan_sha256"] == sha(PLAN) and f["audit_sha256"] == sha(AUDIT) for f in failures) >= 2:
        raise ValueError("Two S4 failures: revise the cause audit before another attempt")
    number = max([int(p.name.split("-")[-1]) for p in BASE.glob("attempt-*")] + [0]) + 1
    attempt = BASE / f"attempt-{number}"
    attempt.mkdir()
    started = time.monotonic()
    frozen = method()
    try:
        (attempt / "plan.md").write_bytes(PLAN.read_bytes())
        (attempt / "master.md").write_bytes(master.MASTER.read_bytes())
        save(attempt / "manifest.json", {
            "command": "python3 -m scripts.run_legal_interpretation_master resume",
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty_baseline": ref(BASE / "baseline.json"), "environment": sys.executable,
            "python": sys.version, "cpu_gpu": "CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
            "seeds": "N/A: deterministic theories and source fixtures",
            "started_at": datetime.now(timezone.utc).isoformat(), "method": frozen,
            "source_versions": historical(), "plan": ref(PLAN), "provider_calls": 0, "network_requests": 0,
            "artifact_directory": str(attempt.relative_to(ROOT)),
            "result_file": str((attempt / "result.json").relative_to(ROOT))})
        command = [sys.executable, "-m", "pytest", *TESTS, "-q", "--tb=short"]
        print(json.dumps({"stage": "required-checks", "attempt": str(attempt.relative_to(ROOT))}), flush=True)
        with (attempt / "tests.log").open("x") as log:
            proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                timeout=1200, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"})
        lines = (attempt / "tests.log").read_text().splitlines()
        tests = {"command": command, "exit_code": proc.returncode,
            "summary": lines[-1] if lines else "No test output", "log": ref(attempt / "tests.log")}
        save(attempt / "tests.json", tests)
        if proc.returncode:
            print("\n".join(lines[-60:]), flush=True)
            raise ValueError("Required S4 tests failed")
        print(json.dumps({"stage": "required-checks", "status": "PASS", "summary": tests["summary"]}), flush=True)
        values = derived()
        for name, value in values.items():
            save(attempt / name, value)
        (attempt / "obligations.json").write_bytes((master.BASE / "attempt-1/obligations.json").read_bytes())
        receipts = {}
        for name, program in data.recursive_programs().items():
            print(json.dumps({"stage": "conditional-runtime", "scenario": name}), flush=True)
            receipts[name] = runtime.run(program, attempt / "recursive" / name, JDK)
        save(attempt / "recursive-results.json", receipts)
        print(json.dumps({"stage": "actual-investigation"}), flush=True)
        runner, dossier, provenance = data.execute_product(attempt / "product")
        stages = check_stages(ROOT, dossier, actual_method(runner), runner)
        if not stages["execution_complete"]:
            raise ValueError("Actual S4 investigation incomplete")
        save(attempt / "whole-stage-verification.json", stages)
        stats = summary(dossier, stages, receipts, values["reading-inventory.json"])
        save(attempt / "preservation.json", preserved)
        (attempt / "next-phase-plan.md").write_text(next_plan(stats))
        (attempt / "result-note.md").write_text(note(stats, tests))
        if frozen != method() or preserved != preservation():
            raise ValueError("Method changed during S4 execution")
        save(attempt / "result.json", {"status": "IMPLEMENTED_QUALIFIED", "phase": "S4",
            "program_revision": 3, "method": frozen, "predecessor": historical()["s3"],
            "engineering": stats, "dossier": read(attempt / "product/current.json"),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "english_fidelity": "NOT_ESTABLISHED", "legal_correctness": "NOT_ESTABLISHED",
            "release_eligible": False, "outputs": [ref(p) for p in sorted(attempt.rglob("*"))
                if p.is_file() and p.name != ".lock" and not p.name.endswith((".lock", "-wal", "-shm"))]})
        print(json.dumps({"stage": "independent-verification"}), flush=True)
        save(attempt / "verification.json", verify_attempt(attempt))
        pointer = {"program_revision": 3, "master": ref(master.MASTER), "completed_phase": "S4",
            "result": ref(attempt / "result.json"), "verification": ref(attempt / "verification.json"),
            "next_phase": "S5", "next_phase_plan": ref(attempt / "next-phase-plan.md"),
            "state": "S5_REQUIRES_PREREQUISITE_REVIEW_AND_FRESH_METHOD_WINDOW"}
        temporary = master.POINTER.with_suffix(".tmp")
        temporary.write_text(json.dumps(pointer, indent=2) + "\n")
        temporary.replace(master.POINTER)
        print(json.dumps({"status": "EXECUTED_AND_VERIFIED", "result": pointer["result"], **stats}), flush=True)
    except BaseException as error:
        save(attempt / "failure.json", {"status": "FAILED", "error": type(error).__name__,
            "details": str(error), "plan_sha256": sha(PLAN), "audit_sha256": sha(AUDIT),
            "elapsed_seconds": round(time.monotonic() - started, 3)})
        raise
