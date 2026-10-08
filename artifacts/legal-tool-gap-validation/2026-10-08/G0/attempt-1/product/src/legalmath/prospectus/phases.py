"""Phase implementations; each result retains its unresolved source premises."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from . import archive, evidence, models, checks, legal_review
from .common import ARCHIVE, JDK, PLAN, PROGRAM, PYTHON, ROOT, TOOLCHAIN, digest, now, read, relative, sha, write


def complete_sources(directory):
    rows = archive.catalog()
    acquisition = archive.acquire([r for r in rows if r["group"] == "repair"], directory)
    manifest = read(ARCHIVE / "manifest.json")
    packages = {}
    for row in rows:
        if row["role"] in ("issue", "terms", "preliminary", "base-programme", "duplicate-edition"):
            packages.setdefault(row["instrument"], []).append({"id": row["id"], "role": row["role"],
                "preserved": row["id"] in manifest["documents"]})
    write(Path(directory) / "packages.json", packages)
    repairs = [{"action": "Acquire separately identified issue document", "document": r["id"],
                "outcome": r["status"], "download_executed": not r["cached"]} for r in acquisition]
    return {"status": "QUALIFIED", "acquisition": acquisition, "packages": packages,
            "repairs": repairs, "resolved": [r["id"] for r in acquisition if r["status"] == "PRESERVED"],
            "open_issues": ["Incorporated-document and amendment closure remains unproved",
                            "Later base prospectuses are not automatically applicable to earlier issues"] +
                           ["Unpreserved source: " + r["id"] for r in rows if r["id"] not in manifest["documents"]]}


def execute(phase, directory, current):
    if phase == "P1":
        return complete_sources(directory)
    if phase == "P2":
        from .campaign import RepairableError
        repairs = archive.derivative_repairs()
        if repairs:
            raise RepairableError("Extracted text requires regeneration: " + json.dumps(repairs))
        result = evidence.investigate(archive.catalog(), directory / "evidence")
        result["legal_source_dossier"] = legal_review.verify_dossier(ROOT)
        result["specifications"] = models.build_specifications(directory / "specification")
        return {"status": "QUALIFIED", **result,
                "resolved": ["Source-bound quotations and conditional model inputs constructed"],
                "open_issues": ["English entailment, applicability and complete legal coverage remain unproved",
                                "Client and trade facts absent; actual SPI eligibility is undetermined"]}
    if phase == "P3":
        result = checks.prove(previous(current, "P2") / "specification", directory)
        return {"status": "CHECKED", **result,
                "open_issues": ["Universal formal guarantees do not establish source interpretation"]}
    if phase == "P4":
        return execute_backends(directory, current)
    if phase == "P5":
        return challenges(directory)
    if phase == "P6":
        return finish(directory, current)
    raise ValueError(phase)


def previous(current, phase):
    return ROOT / current["phases"][phase]["directory"]


def execute_backends(directory, current):
    from ..qualification import assurance
    specdir = previous(current, "P2") / "specification"
    reports = read(previous(current, "P2") / "evidence/instruments.json")
    doc_cases, qualifications = models.candidate_cases(reports)
    write(directory / "candidate-qualifications.json", qualifications)
    summaries = {}
    count = 0
    for name in models.definitions():
        model = read(specdir / (name + ".model.json"))
        cases = read(specdir / (name + ".cases.json"))
        if name == "complex":
            cases += doc_cases
        count += len(cases)
        if count > read(PROGRAM / "allowlist.json")["max_backend_cases"]:
            raise ValueError("Backend case budget exhausted")
        print(json.dumps({"model": name, "backend_cases": len(cases), "stage": "EXECUTE"}), flush=True)
        report = assurance.run(model, cases, directory / name, JDK, toolchain=TOOLCHAIN)
        summaries[name] = report["summary"]
        if (any(t["status"] != "CHECKED" for t in report["targets"].values()) or
                report["summary"]["independent_formal_matches"] != 2 * len(cases) or
                report["proof"]["status"] != "KERNEL_CHECKED"):
            write(directory / "incomplete-backends.json", summaries)
            raise ValueError("Backend/proof mismatch or unavailable required target: " + name)
    return {"status": "CHECKED", "models": summaries, "input_cases": count, "executed_target_cases": 2 * count,
            "real_document_candidate_cases": len(doc_cases), "candidate_cases_are_actual_legal_decisions": False,
            "open_issues": ["Equal formal executions establish no Catala/RuleIR superiority and no legal accuracy ranking"]}


def challenges(directory):
    argv = [str(PYTHON), "-m", "pytest", "tests/prospectus", "tests/translation/test_qualification_windows.py",
            "-q", "--junitxml=" + str(directory / "tests.xml")]
    started = time.monotonic()
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=300)
    (directory / "pytest.log").write_text(proc.stdout + proc.stderr)
    if proc.returncode:
        raise ValueError("Challenge regression failed; inspect retained pytest.log")
    xml = ET.parse(directory / "tests.xml")
    suites = list(xml.getroot().iter("testsuite"))
    result = {"status": "CHECKED", "command": argv, "wall_seconds": time.monotonic() - started,
              "tests": sum(int(s.get("tests", 0)) for s in suites),
              "failures": sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites),
              "repair_scope": "Deterministic fault injection used real derivative repair and supervisor retry in isolated archives",
              "future_evidence": "Existing prospective ledger rejects development sources, changed methods and human labels",
              "open_issues": ["Generated combinations and isolated fault injection are engineering evidence; future legal accuracy is not established"]}
    return result


def recheck_backends(current):
    from ..qualification import assurance
    results = {}
    for name in models.definitions():
        directory = previous(current, "P4") / name
        report = assurance.verify(directory, read(directory / "model.json"), JDK, compiler=TOOLCHAIN["compiler"])
        results[name] = {"qualification_hash": report["report_hash"], "independent_formal_matches": report["summary"]["independent_formal_matches"]}
    return results


def verify_campaign(current):
    from .campaign import PHASES, completed
    for phase in PHASES:
        if not completed(current, phase):
            raise ValueError("Incomplete, stale or corrupted phase: " + phase)
    result = archive.verify()
    result.update(status="CHECKED", phases=list(PHASES),
                  legal_source_dossier=legal_review.verify_dossier(ROOT),
                  backend_replay=read(previous(current, "P6") / "backend-replay.json"),
                  qualification="Retained replay evidence remains current; terminal verification rechecks identities, outputs and archive extraction")
    return result


def finish(directory, current):
    from .campaign import material_inputs
    from ..qualification import prospective
    integrity = archive.verify()
    legal_integrity = legal_review.verify_dossier(ROOT)
    replay = recheck_backends(current)
    write(directory / "backend-replay.json", replay)
    manifest = read(ARCHIVE / "manifest.json")
    methods = material_inputs("P6")
    write(directory / "method-and-inputs.json", methods)
    from .future import method_identity
    frozen_method = method_identity()
    write(directory / "prospective-method.json", frozen_method)
    freeze = prospective.freeze(directory / "prospective", digest(frozen_method),
        ["new_issuer", "new_contract_template", "later_rule_edition"],
        ends_at=(datetime.now(timezone.utc) + timedelta(days=180)).isoformat(),
        development_sources=[d["sha256"] for d in manifest["documents"].values()] +
            [d["sha256"] for d in legal_review.dossier_inputs(ROOT)[1]["sources"]])
    p2 = read(previous(current, "P2") / "result.json")
    p3 = read(previous(current, "P3") / "result.json")
    p4 = read(previous(current, "P4") / "result.json")
    p5 = read(previous(current, "P5") / "result.json")
    missing = [r["id"] for r in archive.catalog() if r["id"] not in manifest["documents"]]
    next_program = {
        "status": "READY_FOR_NEW_EVIDENCE", "frozen_protocol": relative(directory / "prospective/freeze.json"),
        "human_quality_authority": "FORBIDDEN", "observations": 0,
        "phases": [
            {"id": "N1", "question": "Can a complete issue package be identified?",
             "actions": ["Recover each unavailable supplied edition when a public source becomes accessible",
                         "Enumerate referenced base documents, indentures, amendments and effective dates per specific security",
                         "Refresh Swiss legislation and merits dockets; establish current SFC/HKMA scope, legal form and service-specific exceptions"],
             "pass": "Every referenced dependency is preserved or the affected decision remains explicitly qualified",
             "repair": "Add a separately identified source or retain an unresolved dependency; rerun master P0-P2"},
            {"id": "N2", "question": "Do candidate clauses entail the declared contractual and SFC premises?",
             "actions": ["Extend source-language semantics for referents, negation, definitions and explicit overrides",
                         "Require a checked derivation per supported construction; unknown constructions retain alternative readings"],
             "pass": "Every promoted source-to-formal proposition has a checked derivation within a declared fragment",
             "repair": "Counterexample becomes development evidence; revise fragment and run P2-P5; never replace qualification with an AI vote"},
            {"id": "N3", "question": "Does an unchanged method handle later publications and unfamiliar templates?",
             "actions": ["Use the implemented future action to bind the full frozen method, source hash and question to candidate qualifications",
                         "Register all qualifying new publications before candidate analysis; retain failures and abstentions",
                         "Use frozen-method observations only; any repair starts development and requires a later window"],
             "pass": "Machine proofs or explicit qualifications for every registered observation; legal generalization remains unproved without a source semantics theorem",
             "repair": "Execute repair, rerun the master program and freeze a new untouched window"},
        ],
        "refresh": "After each result update unresolved premises, execute available repairs, recheck affected phases and rewrite the next phase plan",
        "scope_limit": "Prospective observations check preservation, quotation binding and candidate possible worlds, with explicit legal qualifications. No future observation exists yet. Publication metadata and inventory completeness remain premises.",
    }
    write(directory / "next-program.json", next_program)
    write(PROGRAM / "next-program.json", next_program)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    run_manifest = {"git_commit": head, "uncommitted_implementation": True,
        "source_and_method_identity": relative(directory / "method-and-inputs.json"),
        "command": [str(PYTHON), str(ROOT / "scripts/prospectus_master.py"), "run"],
        "environment": read(PROGRAM / "preflight.json"), "cpu": True, "gpu": "Intentionally hidden with CUDA_VISIBLE_DEVICES=-1",
        "data_version": {k: v["sha256"] for k, v in manifest["documents"].items()},
        "seeds": "N/A: deterministic enumeration and exact arithmetic", "started_at": current["started_at"], "reported_at": now(),
        "completed_phase_wall_seconds_before_reporting": current["wall_seconds"], "wall_time_record": "artifacts/prospectus-master/state.json",
        "plan": relative(PLAN), "result": relative(directory / "result.json"), "output_artifacts": {p: v["directory"] for p, v in current["phases"].items()}}
    write(directory / "run-manifest.json", run_manifest)
    result = {"status": "QUALIFIED", "archive": integrity, "missing_sources": missing,
        "legal_source_dossier": legal_integrity,
        "quotations": p2["quotations_checked"], "instrument_reports": p2["instrument_reports"],
        "conditional_complex_candidates": p2["conditional_complex_candidates"],
        "lean_theorems": p3["lean"]["theorems_reported"], "smt_obligations": len(p3["solver"]["obligations"]),
        "detected_mutants": len(p3["solver"]["mutants"]), "generated": p3["generated"],
        "backend_cases": p4["input_cases"], "backend_executions": p4["executed_target_cases"], "regression_tests": p5["tests"],
        "future_observations": 0, "freeze_hash": freeze["window_hash"], "human_quality_evidence": False,
        "legal_correctness": "NOT_ESTABLISHED", "unknown_future_legal_generalization": "NOT_ESTABLISHED",
        "open_issues": ["Missing originals/editions: " + ", ".join(missing),
            "Complete document packages and current applicable-law closure remain unproved",
            "Swiss/Hong Kong legal dossier is preserved and scoped guards tested; automatic legal interpretation, full schedules and current merits-appeal outcomes remain unresolved",
            "Candidate extraction has no general natural-language entailment proof",
            "No client/trade facts; all actual SPI eligibility decisions remain undetermined",
            "No future publications have yet been observed under the frozen full-method protocol"],
        "decision": "Retain the implementation as a conditional, checked engineering path; do not promote to autonomous legal certification"}
    write(directory / "summary.json", result)
    write(PROGRAM / "summary.json", result)
    write_report(directory, result, current)
    return result


def write_report(directory, result, current):
    rows = read(previous(current, "P2") / "evidence/instruments.json")
    lines = ["# Prospectus campaign results", "", "The seven-phase program executed preservation, document repairs, conditional interpretation, formal checks, native RuleIR/Catala execution, adversarial tests and replay verification.", "",
        f"Preserved {result['archive']['preserved']} of {result['archive']['requested']} catalogued URLs/editions, including supporting legal sources and separately identified mirrors. Failed originals remain listed; a mirror or a later edition does not replace an unavailable original.", "",
        f"The separate Swiss/Hong Kong legal dossier contains {result['legal_source_dossier']['sources']} source records, bound into phase and future-method identities. Its conditional guards distinguish authority, event timing, judicial proceedings, product scope and selling restrictions. Source identity and these guards do not certify legal currentness or English entailment.", "",
        f"Checked {result['lean_theorems']} reported Lean propositions, {result['smt_obligations']} SMT equivalence obligations over the actual shared programs, {result['generated']['partial_spi_states']} partial SPI evidence states and {result['generated']['contract_event_combinations']} exact contractual event combinations. All {result['backend_executions']} target executions from {result['backend_cases']} identical input cases matched independent formal evaluation. The {result['regression_tests']} regression tests passed. Three deliberately wrong encodings produced solver counterexamples.", "",
        "These results establish scoped mathematical and engineering properties. The actual computed quantities are consequences of explicit formal premises and hypothetical completions of candidate document interpretations. Complete English interpretation, discovery of all applicable law and unknown future legal situations are not established. No human quality labels or decisions are used.", "",
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Conclusion not supported |",
        "| --- | --- | --- | --- | --- | --- |",
        "| Retain conditional implementation | Formal obligations, exact challenges and native executions passed | No unrepaired semantic mismatch in tested scope | Source entailment and completeness | Complete source dependencies and formal source-language fragment | Autonomous legal correctness |",
        "| Preserve RuleIR and Catala routes | Equal shared formal cases matched independent evaluation | Neither route failed supported controls | Untested richer mechanisms and performance | Extend identical supported-domain challenges | One backend is legally better |",
        "| Keep real SPI outcomes undetermined | Missing client/trade premises retained | No unconditional permission generated | Consent, category choice, assessments, exposure | Supply factual evidence without expected labels | Actual transaction eligibility |",
        "| Freeze future protocol | Development identities frozen; observation adapter tested; zero future observations | Existing documents cannot count as prospective evidence | New source/template/time performance | Collect untouched evidence using the future action | Future generalization |", "",
        "| Document | Conditional classification | SPI outcome |", "| --- | --- | --- |"]
    lines += [f"| {r['document']} | {r['classification']} | {r['spi_eligibility']['decision']} |" for r in rows]
    lines += ["", "Remaining source and interpretation limits:", ""] + ["* " + issue for issue in result["open_issues"]]
    lines += ["", "The strongest alternative explanation for success is that all engines correctly execute an incomplete legal specification. The source qualifications deliberately preserve that possibility. A contradictory contractual clause, missing amendment or solver/runtime disagreement would overturn the affected conditional result and trigger repair. The weakest evidence is general source-language interpretation: regular-expression retrieval is a candidate generator, not an entailment checker.", "",
              "The operative next plan is `next-program.json`. Every phase retains its result, review, repairs and refreshed next-phase plan. Existing source packages are development evidence. Source hashes prove byte consistency, not issuer authenticity or legal authority.", ""]
    report = "\n".join(lines)
    (directory / "report.md").write_text(report)
    (PROGRAM / "report.md").write_text(report)
    (PROGRAM / "RESET-MEMO.md").write_text("# Prospectus master reset memo\n\n" + result["decision"] + "\n\nLatest evidence: `" + relative(directory) + "`. Resume with the exact approved `scripts/prospectus_master.py` entry point documented in the plan. `run` invalidates changed inputs and reuses current completed phases; `verify` checks all retained phase outputs and originals. Existing unrelated assurance/monograph work was preserved.\n\n" + "\n".join("* " + x for x in result["open_issues"]) + "\n")
