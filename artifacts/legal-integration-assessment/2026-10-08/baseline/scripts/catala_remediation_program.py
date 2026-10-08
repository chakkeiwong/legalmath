#!/usr/bin/env python3
"""Reviewed, fail-stop execution and retained evidence for Catala backend repair."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.catala.backend import _pinned
from legalmath.catala.generator import ENGINE
from legalmath.java.manifest import build_candidate, verify_candidate
from tests.catala.backend_support import JDK, TOOLCHAIN, corpus_groups, interaction_cases
from tests.conformance.event_support import event_cases

PLAN = "docs/plans/catala-gap-remediation.md"
REVIEW = "docs/implementation/catala/gap-remediation-review.json"
BASELINE = "9160ce72a17a255242299cc8ab33046f2501f42b"
PHASES = ("synchronize", "toolchain", "conformance", "interactions", "integration_regressions", "reproducibility", "reviewer_material", "decision")
TESTS = ["tests/catala", "tests/unit", "tests/conformance", "tests/integration/test_java_host.py",
         "tests/integration/test_host_transactions.py", "tests/integration/test_java_build.py", "tests/integration/test_release.py",
         "tests/assurance/test_declared_evaluation.py", "tests/assurance/test_declared_master.py",
         "tests/assurance/test_public_issue.py", "tests/assurance/test_public_issue_master.py",
         "tests/assurance/test_checkpoints.py", "tests/assurance/test_output_semantics.py"]


def inputs():
    paths = [*ROOT.glob("src/legalmath/**/*.py"), *ROOT.glob("src/legalmath/**/*.java"),
             *ROOT.glob("src/legalmath/schemas/*.json"), *ROOT.glob("tests/**/*.py"),
             *ROOT.glob("docs/specs/v0.1/fixtures/*.json"), *ROOT.glob("examples/java-dry-run/spec/*.json")]
    paths += [ROOT / x for x in [PLAN, "docs/implementation/catala/gap-remediation-review.md",
              "docs/implementation/catala/toolchain-lock.json", "scripts/catala_remediation_program.py", "pyproject.toml"]]
    return {p.relative_to(ROOT).as_posix(): raw_digest(p.read_bytes()) for p in sorted(set(paths))}


def verify_review(path):
    review = loads(Path(path).read_bytes())
    if review["verdict"] != "PASS_FOR_IMPLEMENTATION" or review["inputs"] != inputs():
        raise ValueError("Inputs changed after review; inspect and renew the reviewed fingerprint")
    return review


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, timeout=20).strip()


class Run:
    def __init__(self, out, review):
        self.out = Path(out).resolve()
        if self.out.exists():
            raise ValueError("Use a new output directory; old evidence is immutable")
        self.review = verify_review(review)
        self.out.mkdir(parents=True)
        self.started = time.monotonic()
        self.records = []
        self.builds = []
        self.summary = {"git_commit": git("rev-parse", "HEAD"), "baseline": BASELINE,
            "command": [sys.executable, *sys.argv], "environment": {"python": sys.version, "executable": sys.executable,
            "jdk": str(JDK.resolve()), "catala": str(TOOLCHAIN["compiler"].resolve()), "PYTHONPATH": os.environ.get("PYTHONPATH", "")},
            "hardware": "CPU only; no GPU framework imported or device initialized", "seeds": "N/A: deterministic engineering assertions",
            "data_version": "Reviewed fixture bytes in inputs.json", "plan": PLAN, "result": "decision.json",
            "started_at": datetime.now(timezone.utc).isoformat(), "phases": self.records, "output": str(self.out)}
        save(self.out / "inputs.json", self.review["inputs"])
        save(self.out / "review.json", self.review)
        (self.out / "plan.md").write_bytes((ROOT / PLAN).read_bytes())
        # Freeze the exact implementation and test inputs used by this run.
        for filename in self.review["inputs"]:
            p = self.out / "reviewed-sources" / filename
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((ROOT / filename).read_bytes())

    def synchronize(self):
        subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=ROOT, check=True, timeout=20)
        current_main = git("rev-parse", "main")
        if current_main != BASELINE:
            raise ValueError("Committed main changed; re-audit synchronization before continuing")
        return {"main": current_main, "merged": True, "main_dirty_work": "Preserved separately; see main-sync.json"}

    def toolchain(self):
        _, locked, runtime, _ = _pinned(**TOOLCHAIN)
        return {"compiler": locked["compiler_version"], "compiler_sha256": locked["compiler_sha256"],
                "upstream_commit": locked["upstream_commit"], "runtime_files_verified": len(runtime)}

    def group(self, cases, name, events=None):
        out = self.out / "comparisons" / name
        out.mkdir(parents=True)
        # Avoid repeating the same large bundle in every case in the retained input.
        save(out / "corpus.json", {"bundle": cases[0]["bundle"], "cases": [{k: v for k, v in c.items() if k != "bundle"} for c in cases]})
        built = build_candidate(cases[0]["bundle"], out, JDK, backend="catala", catala_toolchain=TOOLCHAIN)
        report = verify_candidate(built, cases, JDK, events)
        results = loads((out / "verification-results.json").read_bytes())
        layers = Counter("catala-and-shared-host" if r["java"]["trace"] else "shared-host-preflight" for r in results)
        self.builds.append((built, cases))
        return {"cases": len(cases), "bundle_hash": report["bundle_hash"], "jar_sha256": report["jar_sha256"],
                "report": str((out / "verification-report.json").relative_to(self.out)), "execution_layers": dict(layers)}

    def conformance(self):
        return {"groups": [self.group(cs, str(i), event_cases() if i == 0 else None) for i, cs in enumerate(corpus_groups())],
                "comparison": "Full results, including traces; engine_version and result_hash intentionally distinct and independently checked"}

    def interactions(self):
        return self.group(interaction_cases(), "interactions")

    def integration_regressions(self):
        # These two expensive corpus tests have just run above with retained outputs.
        command = [sys.executable, "-m", "pytest", "-q", *TESTS, "-k",
                   "not test_complete_results_for_each_compiled_bundle and not test_operator_status_interactions_and_exact_types",
                   "--junitxml=" + str(self.out / "tests.xml")]
        with (self.out / "tests.log").open("wb") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
        if result.returncode:
            raise ValueError("Regression tests failed; inspect tests.log")
        import xml.etree.ElementTree as ET
        suite = ET.parse(self.out / "tests.xml").getroot().find("testsuite")
        return {"command": command, "tests": int(suite.attrib["tests"]), "failures": int(suite.attrib["failures"]),
                "errors": int(suite.attrib["errors"]), "skipped": int(suite.attrib["skipped"]), "log": "tests.log"}

    def reproducibility(self):
        original, cases = self.builds[0]
        repeated = build_candidate(cases[0]["bundle"], self.out / "repeat", JDK, backend="catala", catala_toolchain=TOOLCHAIN)
        if repeated["manifest"] != original["manifest"]:
            raise ValueError("Different build paths changed output identity")
        return {"identical_manifests_and_jar": True, "jar_sha256": original["manifest"]["jar_sha256"]}

    def reviewer_material(self):
        path = self.out / "reviewer-guide.md"
        path.write_text("# Reviewing the generated backend\n\n"
            "The authored rules are in each comparison's corpus.json. source-map.json maps\n"
            "every RuleIR node to its rule, source spans, execution layer, and generated\n"
            "Catala scope/line numbers. Lowered.catala_en contains the generated calculations.\n"
            "verification-results.json places complete Python and Catala/Java results beside\n"
            "one another, including skipped branches and evidence IDs. The JAR retains those\n"
            "generated sources and the pinned runtime sources under META-INF/legalmath.\n\n"
            "A lawyer should assess the canonical rule and retained source interpretation.\n"
            "An engineer can follow node IDs into generated code and the executed trace.\n"
            "No human reviewer has yet compared accuracy, time, or comprehension using this\n"
            "backend. A counterbalanced study with the same source, rules and questions is\n"
            "required before claiming that either presentation is easier to review.\n")
        return {"source_navigation": "AVAILABLE", "guide": path.name, "human_study": "PENDING", "readability_claim": False}

    def decision(self):
        passed = all(r["status"] == "PASS" for r in self.records)
        value = {"engineering_contract": "PASS" if passed else "FAIL", "optional_backend_viable": passed,
                 "default_changed": False, "production_approved": False, "human_reviewer_benefit": "NOT_CHECKED",
                 "engine": ENGINE, "shared_components": ["snapshot validation", "fact/time/conflict boundary", "traversal", "provenance", "hashing", "events", "transaction and release lifecycle"],
                 "next_action": "Institution-specific review and human comparison before adoption" if passed else "Repair the failed implementation/harness phase and rerun in a new directory",
                 "not_concluded": ["legal correctness", "compiler proof", "independent whole-engine validation", "performance ranking"]}
        save(self.out / "decision.json", value)
        return value

    def execute(self):
        failed = False
        for name in PHASES:
            start = time.monotonic()
            record = {"phase": name, "status": "NOT_RUN"}
            if not failed or name == "decision":
                print("Starting " + name, flush=True)
                try:
                    record.update(status="PASS", result=getattr(self, name)())
                except Exception as error:
                    record.update(status="FAIL", error=type(error).__name__ + ": " + str(error))
                    failed = True
                record["wall_ms"] = int((time.monotonic() - start) * 1000)
            self.records.append(record)
            save(self.out / "run-manifest.json", self.summary)
            print(name + ": " + record["status"], flush=True)
        if inputs() != self.review["inputs"]:
            failed = True
            self.summary["integrity_failure"] = "Reviewed inputs changed during execution"
            save(self.out / "decision.json", {"engineering_contract": "FAIL", "optional_backend_viable": False, "reason": self.summary["integrity_failure"]})
        self.summary.update(status="FAIL" if failed else "PASS", wall_ms=int((time.monotonic() - self.started) * 1000))
        save(self.out / "run-manifest.json", self.summary)
        save(self.out / "artifact-hashes.json", {p.relative_to(self.out).as_posix(): raw_digest(p.read_bytes()) for p in sorted(self.out.rglob("*")) if p.is_file() and p.name != "artifact-hashes.json"})
        return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--review", default=str(ROOT / REVIEW))
    args = parser.parse_args()
    return Run(args.out, args.review).execute()


if __name__ == "__main__":
    sys.exit(main())
