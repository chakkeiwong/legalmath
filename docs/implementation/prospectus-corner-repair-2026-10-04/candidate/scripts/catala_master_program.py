#!/usr/bin/env python3
"""Execute eight reviewed phases of the optional Catala pilot, never promotion.

No network, installation, Git mutation, reference-result fallback or release
operation occurs here. Preparation is explicit; failed phases stop dependents.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legalmath.canonical import digest
from legalmath.catala.adapter import UnsupportedProfile, finish, native_integer, prepare, projection
from legalmath.catala.corpus import comparison_cases
from legalmath.catala.runtime import (Commands, evaluate_package, interpret, jar_file,
    java_packets, manifest, sha, verify_package, write_json)
from legalmath.conformance import evaluate_case
from legalmath.java.manifest import build_candidate, verify_candidate
from legalmath.sources.anchors import verify_span

BASELINE = "66d15b2aee8f0c00076ab1dd24334b5f80dac058"
PHASES = ["freeze", "toolchain", "fragment", "pilot", "conformance", "host",
          "reviewer", "decision"]
CODE_PATHS = ["scripts/catala_master_program.py", "scripts/prepare_catala_toolchain.py", "src/legalmath/catala",
              "tests/catala", "examples/catala", "docs/plans/catala-adapter.md",
              "docs/implementation/catala/toolchain-lock.json", "pyproject.toml"]


def reviewed_inputs():
    paths = []
    for name in CODE_PATHS:
        path = ROOT / name
        paths.extend(path.rglob("*") if path.is_dir() else [path])
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)
            if p.is_file() and "__pycache__" not in p.parts}


def verify_review(path):
    review = json.loads(Path(path).read_text())
    if review.get("verdict") != "PASS_FOR_BOUNDED_EXECUTION":
        raise ValueError("Program has no positive bounded-execution review")
    if review.get("reviewed_inputs") != reviewed_inputs():
        raise ValueError("Code/plan/toolchain changed after program review")
    return review


class Run:
    def __init__(self, args):
        self.args = args
        self.out = args.out.resolve()
        if self.out.exists():
            raise ValueError("Use a new output directory; prior evidence is immutable")
        self.review = verify_review(args.review)
        self.out.mkdir(parents=True)
        for name, expected in self.review["reviewed_inputs"].items():
            data = (ROOT / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Reviewed file changed while snapshotting: " + name)
            target = self.out / "reviewed-inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        shutil.copyfile(args.review, self.out / "program-review.json")
        self.commands = Commands(ROOT, self.out / "commands")
        self.profile = json.loads((ROOT / "examples/catala/profile.json").read_text())
        self.source = ROOT / "examples/catala/Pilots.catala_en"
        self.original, self.cases = comparison_cases(ROOT)
        self.records = []
        self.started = time.monotonic()
        self.run_manifest = {
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": self.commands.run(["git", "rev-parse", "HEAD"]).stdout.strip(),
            "baseline_commit": BASELINE,
            "command": [sys.executable, *sys.argv], "python": sys.version,
            "python_executable": sys.executable, "platform": platform.platform(),
            "cpu_gpu": "CPU only; no GPU framework loaded", "random_seeds": "N/A; deterministic corpus",
            "data_version": sha(ROOT / "docs/specs/v0.1/fixtures/decision-cases.json"),
            "plan": "docs/plans/catala-adapter.md", "review": str(args.review),
            "review_sha256": sha(args.review), "code_hashes": reviewed_inputs(),
            "result": str(self.out / "08-decision.json"), "phases": self.records,
            "evidence_contract": self.review["evidence_contract"],
        }
        write_json(self.out / "run-manifest.json", self.run_manifest)

    def freeze(self):
        paths = [*ROOT.glob("src/legalmath/ir/*.py"), *ROOT.glob("src/legalmath/schemas/*.json"),
                 *ROOT.glob("src/legalmath/java/*.py"), *ROOT.glob("src/legalmath/java/runtime/*.java"),
                 *[ROOT / n for n in ("src/legalmath/canonical.py", "src/legalmath/domain.py",
                    "src/legalmath/integer.py", "src/legalmath/conformance.py", "src/legalmath/errors.py",
                    "docs/specs/v0.1/fixtures/decision-cases.json", "tests/conformance/contract-matrix.json")]]
        hashes = {}
        for path in paths:
            name = str(path.relative_to(ROOT))
            # git show is text here: the comparator is entirely UTF-8 source/JSON.
            committed = self.commands.run(["git", "show", BASELINE + ":" + name]).stdout.encode()
            if hashlib.sha256(committed).hexdigest() != sha(path):
                raise ValueError("Reference changed from frozen baseline: " + name)
            hashes[name] = sha(path)
        baseline = []
        for case in self.original:
            result = evaluate_case(case)
            for key, value in case["expected"].items():
                good = (set(value) <= set(result["reason_codes"]) if key == "reason_codes_include"
                        else result.get(key) == value)
                if not good:
                    raise ValueError("Reference violates fixed expectation: " + case["id"])
            baseline.append({"id": case["id"], "result": result})
        self.expected = {c["id"]: evaluate_case(c) for c in self.cases}
        write_json(self.out / "baseline.json", {"hashes": hashes, "fixed_results": baseline,
                   "comparison_results": self.expected})
        write_json(self.out / "cases.json", self.cases)
        return {"fixed_cases": len(baseline), "comparison_cases": len(self.cases),
                "reference_files": len(hashes), "corpus_sha256": sha(self.out / "cases.json")}

    def toolchain(self):
        lock = json.loads((ROOT / "docs/implementation/catala/toolchain-lock.json").read_text())
        if sha(self.args.catala) != lock["compiler_sha256"]:
            raise ValueError("Catala compiler differs from reviewed lock")
        for name, expected in lock["source_files"].items():
            if sha(self.args.upstream / name) != expected:
                raise ValueError("Upstream file differs from lock: " + name)
        version = self.commands.run([self.args.catala, "--version"]).stdout.strip()
        if version != lock["compiler_version"] or "1.2.1" not in version:
            raise ValueError("Unexpected Catala version")
        jdk_version = self.commands.run([self.args.jdk / "bin/javac", "-version"]).stdout.strip()
        if not jdk_version.startswith("javac 17."):
            raise ValueError("Java 17 required")
        # Compile the actual pinned Java runtime under the existing Java target.
        self.classes = self.out / "classes"
        self.classes.mkdir()
        self.runtime_sources = sorted((self.args.upstream / "runtimes/java").rglob("*.java"))
        runtime_names = {str(p.relative_to(self.args.upstream)) for p in self.runtime_sources}
        locked_runtime = {name for name in lock["source_files"]
                          if name.startswith("runtimes/java/") and name.endswith(".java")}
        if runtime_names != locked_runtime:
            raise ValueError("Unreviewed or missing Java runtime source")
        self.commands.run([self.args.jdk / "bin/javac", "--release", "17", "-encoding", "UTF-8",
            "-d", self.classes, *self.runtime_sources])
        return {"catala_version": version, "compiler_sha256": sha(self.args.catala),
                "java_version": jdk_version, "upstream_commit": lock["upstream_commit"],
                "runtime_source_files": len(self.runtime_sources), "license": "Apache-2.0",
                "full_upstream_suite": "not run; actual pilot and runtime checked"}

    def fragment(self):
        source_map = json.loads((ROOT / "examples/catala/source-map.json").read_text())
        quote = verify_span(source_map["span"], (ROOT / source_map["raw_path"]).read_bytes(),
                            (ROOT / source_map["text_path"]).read_text())
        source_text = self.source.read_text()
        for anchor in source_map["definitions"]:
            if source_text.count(anchor["expression"]) != 1:
                raise ValueError("Catala source-map expression no longer resolves uniquely")
        write_json(self.out / "resolved-source-map.json", {
            "catala_sha256": sha(self.source), "source_map": source_map,
            "lines": {a["name"]: source_text[:source_text.index(a["expression"])].count("\n") + 1
                      for a in source_map["definitions"]}})
        self.packets = [prepare(c, self.profile) for c in self.cases]
        rejected = []
        for case in self.original:
            if case["rule_id"] not in ("spi.financial", "exception.test"):
                try:
                    prepare(case, self.profile)
                except UnsupportedProfile:
                    rejected.append(case["id"])
                else:
                    raise ValueError("Unsupported rule was silently accepted")
        write_json(self.out / "prepared-inputs.json", self.packets)
        return {"bundles": self.profile["bundles"], "unsupported_fixture_cases_rejected": rejected,
                "source_quote": quote, "synthetic_exception_fixture": True,
                "projection": "status,type,value,mode,diagnostics,reason_codes,missing_inputs,blocking_inputs",
                "outside_projection": "RuleIR trace and engine-specific identity; source map is separate",
                "execution_layers": dict(Counter(p["preflight"] or "catala" for p in self.packets))}

    def pilot(self):
        self.commands.run([self.args.catala, "typecheck", self.source, "--no-stdlib", "--check-invariants"])
        self.generated = self.out / "Pilots.java"
        self.commands.run([self.args.catala, "java", self.source, "--no-stdlib", "--check-invariants",
                           "--output", self.generated])
        self.commands.run([self.args.jdk / "bin/javac", "--release", "17", "-encoding", "UTF-8",
            "-parameters", "-cp", self.classes, "-d", self.classes, self.generated,
            ROOT / "src/legalmath/java/runtime/Json.java", ROOT / "src/legalmath/catala/CatalaPilotHost.java"])
        self.jar = self.out / "policy.jar"
        jar_file(self.classes, self.jar)
        # The two-true fixture exposes the equal-consequence behavior directly.
        packet = next(p for c, p in zip(self.cases, self.packets) if c["id"] == "exception.true.true")
        proc = self.commands.run([self.args.catala, "interpret", self.source, "--no-stdlib",
            "--scope=Exceptions", "--input=" + json.dumps(packet["inputs"]), "--output-format=json"])
        native = json.loads(proc.stdout, parse_float=Decimal)
        if native_integer(native["amount"]) != 10 or native_integer(native["decision"]) != 2:
            raise ValueError("Expected native coalescence and explicit ambiguity repair not observed")
        return {"generated_java_sha256": sha(self.generated), "jar_sha256": sha(self.jar),
                "native_two_true_amount": native_integer(native["amount"]), "explicit_ambiguity_code": native_integer(native["decision"]),
                "repair": "Ambiguity is explicitly calculated in Catala before accepting an amount"}

    def conformance(self):
        # Current Java must first agree with the unchanged reference on the same corpus.
        groups = {}
        for case in self.cases:
            c = deepcopy(case)
            c["expected"] = projection(self.expected[c["id"]])
            groups.setdefault(digest(c["bundle"]), []).append(c)
        java_reports = []
        for key, cases in groups.items():
            build = build_candidate(cases[0]["bundle"], self.out / "reference-java" / key[:16], self.args.jdk)
            java_reports.append(verify_candidate(build, cases, self.args.jdk))
        java = java_packets(self.packets, self.jar, self.args.jdk, self.commands)
        rows = []
        for case, packet, actual in zip(self.cases, self.packets, java):
            interpreter = interpret(packet, self.args.catala, self.source, self.commands)
            expected = projection(self.expected[case["id"]])
            row = {"id": case["id"], "reference": expected, "catala_interpreter": interpreter,
                   "catala_java": actual, "passed": expected == projection(interpreter) == projection(actual)}
            rows.append(row)
        write_json(self.out / "comparison.json", rows)
        mismatches = [row["id"] for row in rows if not row["passed"]]
        if mismatches:
            raise ValueError("Semantic mismatches: " + ", ".join(mismatches))
        # Show that the corpus notices broken candidate logic, not merely the wrapper.
        mutations = [
            ("strict_threshold", "portfolio_cents >= 4000000000", "portfolio_cents > 4000000000", "f01"),
            ("suppress_ambiguity", "second_known and second_applies then 2", "second_known and second_applies then 3", "exception.true.true"),
        ]
        mutation_results = []
        for name, before, after, ident in mutations:
            if self.source.read_text().count(before) != 1:
                raise ValueError("Mutation does not identify one intended expression")
            mutated = self.out / (name + ".catala_en")
            mutated.write_text(self.source.read_text().replace(before, after))
            packet = next(p for c, p in zip(self.cases, self.packets) if c["id"] == ident)
            actual = interpret(packet, self.args.catala, mutated, self.commands)
            detected = projection(actual) != projection(self.expected[ident])
            mutation_results.append({"mutation": name, "case": ident, "detected": detected, "actual": actual})
            if not detected:
                raise ValueError("Comparison failed to detect mutation: " + name)
        # An unknown amount's arbitrary payload must have no semantic influence.
        masked = deepcopy(next(p for c, p in zip(self.cases, self.packets) if c["id"] == "f07"))
        masked["inputs"]["portfolio_cents"] = "9" * 40
        masked_result = interpret(masked, self.args.catala, self.source, self.commands)
        masked_java = java_packets([masked], self.jar, self.args.jdk, self.commands)[0]
        if projection(masked_result) != projection(self.expected["f07"]) or projection(masked_java) != projection(masked_result):
            raise ValueError("Unknown payload affected a calculation")
        write_json(self.out / "mutations.json", mutation_results)
        return {"compared": len(rows), "mismatches": mismatches, "reference_java_builds": len(java_reports),
                "candidate_mutations_detected": len(mutation_results), "masked_payload_check": "PASS",
                "whole_ruleir_equivalence": False, "statistical_ranking": "N/A; exact deterministic checks"}

    def host(self):
        package = self.out / "host-package"
        package.mkdir()
        for source, name in [(self.jar, "policy.jar"), (self.source, "Pilots.catala_en"),
                (ROOT / "examples/catala/profile.json", "profile.json"),
                (ROOT / "examples/catala/source-map.json", "source-map.json"),
                (self.args.upstream / "LICENSE.txt", "LICENSE-Catala.txt")]:
            shutil.copyfile(source, package / name)
        for source, name in [(self.generated, "src/Pilots.java"),
                (ROOT / "src/legalmath/catala/CatalaPilotHost.java", "src/CatalaPilotHost.java"),
                (ROOT / "examples/catala/BankCaller.java", "src/BankCaller.java"),
                (ROOT / "src/legalmath/java/runtime/Json.java", "src/hk/legalmath/Json.java")]:
            target = package / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copytree(self.args.upstream / "runtimes/java", package / "runtime-source")
        mapping = json.loads((package / "source-map.json").read_text())
        shutil.copyfile(ROOT / mapping["raw_path"], package / "annex1.pdf")
        shutil.copyfile(ROOT / mapping["text_path"], package / "annex1.txt")
        write_json(package / "package.json", {"version": "catala-draft-host.v1", "java_target": 17,
            "bundle_hashes": sorted(self.profile["bundles"]), "release_eligible": False,
            "catala_source_sha256": sha(self.source), "compiler_sha256": sha(self.args.catala),
            "toolchain_lock_sha256": sha(ROOT / "docs/implementation/catala/toolchain-lock.json"),
            "input_boundary": "legalmath.catala.adapter.prepare validates raw facts and timestamps",
            "java_boundary": "CatalaPilotHost takes typed scope/inputs and returns native calculations",
            "output_boundary": "legalmath.catala.adapter.finish attaches status and provenance",
            "existing_release_schema_compatible": False, "existing_host_transaction_suite": "not integrated"})
        write_json(package / "manifest.json", manifest(package))
        trusted = sha(package / "manifest.json")
        case = self.cases[0]
        result = evaluate_package(package, trusted, case, self.args.jdk, self.commands)
        if projection(result) != projection(self.expected[case["id"]]):
            raise ValueError("Packaged draft host differs from conformance result")
        # Exercise the existing separate-Java-caller integration pattern too.
        caller = self.out / "java-caller"
        caller.mkdir()
        self.commands.run([self.args.jdk / "bin/javac", "--release", "17", "-Xlint:all", "-Werror",
            "-cp", package / "policy.jar", "-d", caller, ROOT / "examples/catala/BankCaller.java"])
        prepared = prepare(case, self.profile)
        write_json(caller / "request.json", {"scope": prepared["scope"], "inputs": prepared["inputs"]})
        called = self.commands.run([self.args.jdk / "bin/java", "-cp",
            str(caller) + os.pathsep + str(package / "policy.jar"), "BankCaller", caller / "request.json"])
        called_result = finish(prepared, json.loads(called.stdout), "catala-separate-java-caller")
        if projection(called_result) != projection(self.expected[case["id"]]):
            raise ValueError("Separate Java host call failed")
        with tempfile.TemporaryDirectory(prefix="catala-tamper-") as temporary:
            changed = Path(temporary) / "package"
            shutil.copytree(package, changed)
            with (changed / "policy.jar").open("ab") as stream:
                stream.write(b"tamper")
            try:
                verify_package(changed, trusted)
            except ValueError:
                pass
            else:
                raise ValueError("Altered jar accepted")
            write_json(changed / "manifest.json", manifest(changed))
            try:
                verify_package(changed, trusted)
            except ValueError:
                pass
            else:
                raise ValueError("Rewritten untrusted manifest accepted")
        # Direct Java boundary must reject unknown scopes and malformed typed inputs.
        for request in ({"scope": "Another", "inputs": {}}, {"scope": "Financial", "inputs": {}}):
            bad = self.commands.run([self.args.jdk / "bin/java", "-cp", self.jar, "CatalaPilotHost"],
                                    input=json.dumps(request) + "\n", check=False)
            if bad.returncode == 0:
                raise ValueError("Malformed Java request accepted")
        return {"package": str(package), "trusted_manifest_sha256": trusted,
                "packaged_call": "PASS", "separate_java_caller": "PASS", "tamper_checks": 2, "malformed_java_checks": 2,
                "existing_release_integration": "PENDING: full trace contract and host transaction suite"}

    def reviewer(self):
        # Execute the compiler's documentation path and provide a separate comparison packet.
        self.commands.run([self.args.catala, "html", self.source, "--wrap", "--output", self.out / "pilot.html"])
        mapping = json.loads((ROOT / "examples/catala/source-map.json").read_text())
        quote = verify_span(mapping["span"], (ROOT / mapping["raw_path"]).read_bytes(),
                            (ROOT / mapping["text_path"]).read_text())
        scenarios = [
            ("f01", "The portfolio is exactly HK$40 million; net assets are zero.",
             "The financial condition holds because equality satisfies the portfolio threshold."),
            ("f06", "The portfolio amount is unavailable; net assets are HK$90 million.",
             "The financial condition holds through the net-assets alternative. Portfolio evidence remains missing."),
            ("f07", "The portfolio amount is unavailable; net assets are HK$70 million.",
             "The decision remains unresolved: net assets do not suffice, but the portfolio could still qualify."),
            ("exception.true.true", "Both synthetic exceptions apply and both specify ten.",
             "The RuleIR convention requires a conflict. An explicit ambiguity check in Catala preserves that convention."),
            ("exception.true.none", "The first synthetic exception applies; whether the second applies is unknown.",
             "The result remains unresolved because the second exception could create a conflict."),
        ]
        examples = "".join("<article><h3>" + html.escape(question) + "</h3><p>" +
                           html.escape(answer) + "</p></article>" for _, question, answer in scenarios)
        packet = ("<!doctype html><meta charset='utf-8'><title>Reviewing the Catala pilot</title>"
                  "<style>body{max-width:850px;margin:3em auto;font:18px/1.6 Georgia}pre{white-space:pre-wrap;"
                  "font:14px/1.5 monospace;background:#f5f5f5;padding:1em}</style>"
                  "<h1>Does the program express the intended financial condition?</h1>"
                  "<p>Compare the archived circular, the two threshold alternatives, and the examples below. "
                  "These calculations cover only the financial subcondition. A true result does not establish "
                  "all SPI requirements or authorize a transaction.</p><h2>Annex 1, paragraph 3.1</h2><blockquote>"
                  + html.escape(quote) + "</blockquote><p><a href='pilot.html'>Read the Catala explanation and code</a></p>"
                  "<h2>Five cases that distinguish the decisions</h2>" + examples +
                  "<h2>Questions for a reviewer</h2><p>Explain the two thresholds, including units and whether "
                  "equality is sufficient. Explain why missing portfolio evidence can still yield true when "
                  "net assets suffice. Identify the missing legal judgments. In the synthetic exception example, "
                  "explain why two applicable exceptions require a conflict. Record errors and assistance needed "
                  "when answering these questions from the RuleIR and Catala versions.</p>"
                  "<p>Human review has not yet been performed. This packet establishes neither readability "
                  "nor a reduction in review effort.</p>")
        (self.out / "reviewer-packet.html").write_text(packet)
        return {"packet": "reviewer-packet.html", "compiler_document": "pilot.html",
                "source_anchor": "PASS", "human_review": "PENDING", "benefit_established": False,
                "future_protocol": "Same questions and cases, counterbalanced presentation order; record correctness, assistance and time. No ranking from one reader."}

    def decision(self):
        passed = {record["phase"] for record in self.records if record["status"] == "PASS"}
        engineering_pass = set(PHASES[:6]) <= passed
        result = {"decision": "NOT_PROMOTED", "optional_pilot_viable": engineering_pass,
            "primary_criterion": "PASS_FOR_DECLARED_PROJECTION" if engineering_pass else "INCOMPLETE_OR_FAILED",
            "veto_diagnostics": ["Human reviewer benefit untested", "Full RuleIR trace contract not implemented",
                "Existing release and transaction integration not completed", "Supported profiles remain narrow"],
            "main_uncertainty": "Does source-facing authoring help legal reviewers beyond this pilot?",
            "next_justified_action": "Review the pilot with intended users, then implement trace and host conformance before expanding profiles",
            "not_concluded": ["legal correctness", "whole-RuleIR equivalence", "compiler proof", "production readiness"],
            "research_direction_rejected": False,
            "post_run_red_team": {"alternative_explanation": "The finite manually authored fragment may conceal difficulties in general rules",
                "overturning_evidence": "Any accepted-input counterexample or source-map mismatch",
                "weakest_evidence": "Reviewer benefit and existing-host acceptance have not been measured"}}
        write_json(self.out / "decision.json", result)
        (self.out / "decision.md").write_text(
            "# Catala pilot decision\n\n" +
            ("The declared engineering comparison passed. " if engineering_pass else "The engineering comparison is incomplete or failed. ") +
            "The Catala implementation remains an optional draft pilot. It is not promoted to replace RuleIR.\n\n"
            "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            f"| Not promoted | {result['primary_criterion']} | Human review, trace and host work remain | Reviewer benefit | Review and complete integration | Legal correctness or production readiness |\n\n"
            "The native equal-consequence behavior differs from RuleIR. An explicit Catala ambiguity check repairs "
            "the declared exception fixture. This is a local repair, not a theorem about arbitrary programs. "
            "Shared validation and independently computed results are identified separately in the comparison records.\n")
        return result

    def execute(self):
        failed = False
        for i, name in enumerate(PHASES, 1):
            start = time.monotonic()
            record = {"phase": name, "number": i}
            if failed and name != "decision":
                record.update(status="NOT_RUN", reason="Earlier prerequisite failed")
            else:
                try:
                    record.update(status="PASS", evidence=getattr(self, name)())
                except Exception as error:
                    failed = True
                    record.update(status="FAIL", error=f"{type(error).__name__}: {error}")
            record["wall_seconds"] = time.monotonic() - start
            self.records.append(record)
            write_json(self.out / f"{i:02d}-{name}.json", record)
            self.run_manifest["wall_seconds"] = time.monotonic() - self.started
            self.run_manifest["execution_status"] = "FAILED" if failed else ("COMPLETED" if i == 8 else "RUNNING")
            write_json(self.out / "run-manifest.json", self.run_manifest)
            print(f"{i}/8 {name}: {record['status']}", flush=True)
        write_json(self.out / "manifest.json", manifest(self.out))
        return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--catala", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--jdk", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=ROOT / "docs/implementation/catala/program-review.json")
    args = parser.parse_args()
    for name in ("catala", "upstream", "jdk", "review"):
        setattr(args, name, getattr(args, name).resolve())
    return Run(args).execute()


if __name__ == "__main__":
    raise SystemExit(main())
