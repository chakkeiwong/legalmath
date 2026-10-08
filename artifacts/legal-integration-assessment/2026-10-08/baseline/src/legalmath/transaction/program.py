"""Phased execution with retained failures, dependency checks and refreshed plans."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

from ..canonical import canonical, digest
from ..prospectus.common import JDK, TOOLCHAIN, LEAN
from ..qualification import assurance, proof
from .catalog import models, inventory, PROFILE, specifications
from .checks import prove_equations, cases
from .engine import investigate, method_identity, revalidate
from .evidence import sha
from .feeds import FEEDS
from .intake import bootstrap, hypothetical
from .prospective import freeze
from .sanctions import parse

PHASES = ("sources", "regression", "formal", "native", "integration")


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical(value))
    tmp.replace(path)


def input_identity(root):
    paths = [root / "docs/plans/bank-compliance-closure.md", Path(__file__),
             root / "scripts/run_bank_compliance_program.py", root / "docs/compliance/feeds/manifest.json",
             root / "docs/compliance/sources/manifest.json", root / "docs/prospectus/manifest.json",
             *sorted((root / "tests/compliance").glob("*.py"))]
    paths.extend(root / "docs/compliance/feeds" / row[2] for row in FEEDS)
    for row in json.loads((root / "docs/compliance/sources/manifest.json").read_text())["sources"]:
        for field, hash_field in (("path", "sha256"), ("text_path", "text_sha256")):
            path = root / row[field]
            if sha(path.read_bytes()) != row[hash_field]:
                raise ValueError("Archived source differs from its retained manifest: " + row["key"])
            paths.append(path)
    selected = ("sfc-spi-annex-1", "sfc-complex-products", "ubs-sgd-at1-2024-final-published",
                "jpm-series-pp-2026", "bofa-series-ss-2022-issuer")
    documents = json.loads((root / "docs/prospectus/manifest.json").read_text())["documents"]
    for key in selected:
        path = root / "docs/prospectus" / documents[key]["file"]
        if sha(path.read_bytes()) != documents[key]["sha256"]:
            raise ValueError("Prospectus source identity changed: " + key)
        paths.extend([path, root / "docs/prospectus/text" / (key + ".json")])
    tools = [JDK / "bin/java", JDK / "bin/javac", LEAN, TOOLCHAIN["compiler"], TOOLCHAIN["lock"]]
    return {"method_hash": method_identity(), "files": {str(p.relative_to(root)): sha(p.read_bytes()) for p in paths},
            "tool_files": {str(p): sha(p.read_bytes()) for p in tools}}


def output_hashes(directory):
    return {str(p.relative_to(directory)): sha(p.read_bytes()) for p in sorted(directory.rglob("*"))
            if p.is_file() and p.name != "receipt.json"}


def execute(phase, out, root, completed):
    if phase == "sources":
        versions = {}
        for name, command in (("java", [str(JDK / "bin/java"), "-version"]),
                              ("catala", [str(TOOLCHAIN["compiler"]), "--version"]),
                              ("lean", [str(LEAN), "--version"])):
            proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if proc.returncode:
                raise ValueError("Toolchain preflight failed: " + name)
            versions[name] = {"command": command, "version": (proc.stdout + proc.stderr).strip()}
        feeds = []
        manifest = json.loads((root / "docs/compliance/feeds/manifest.json").read_text())
        for row in manifest["sources"]:
            data = (root / row["path"]).read_bytes()
            if sha(data) != row["sha256"]:
                raise ValueError("Feed source changed")
            parsed = parse(data, list_kind=row["list_kind"])
            if parsed["record_count"] != row["records"] or parsed["published_date"] != row["published_date"]:
                raise ValueError("Feed metadata changed")
            feeds.append({k: v for k, v in parsed.items() if k != "entries"})
        return {"tools": versions, "feeds": feeds, "rule_models": len(models()),
                "obligations": len(inventory(PROFILE)), "source_meaning": "NOT_ESTABLISHED"}
    if phase == "regression":
        command = [sys.executable, "-m", "pytest", "-q", "tests/compliance", "tests/prospectus",
                   "tests/translation/test_qualification_windows.py", "--junitxml=" + str(out / "tests.xml")]
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300)
        (out / "tests.log").write_text(proc.stdout + proc.stderr)
        if proc.returncode:
            raise ValueError("Regression failed; inspect retained tests.log and repair")
        counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
        for suite in ET.parse(out / "tests.xml").getroot().iter("testsuite"):
            for key in counts:
                counts[key] += int(suite.get(key, 0))
        if any(counts[k] for k in ("failures", "errors", "skipped")):
            raise ValueError("Every required check must execute successfully")
        return {"command": command, **counts}
    if phase == "formal":
        equations = prove_equations(out / "solver")
        certificates = {}
        for name, model in models().items():
            certificates[name] = proof.produce(model, out / name)
        return {"equations": equations, "certificates": certificates,
                "legal_entailment": "NOT_ESTABLISHED"}
    if phase == "native":
        results = {}
        for name, model in models().items():
            print("Native checks: " + name, flush=True)
            report = assurance.run(model, cases(name), out / name, JDK, toolchain=TOOLCHAIN)
            if (report["proof"]["status"] != "KERNEL_CHECKED" or
                    any(r["status"] != "CHECKED" for r in report["targets"].values()) or
                    report["summary"]["independent_formal_matches"] != 2 * len(cases(name))):
                raise ValueError("Required native execution/proof failed: " + name)
            results[name] = report["summary"]
        return {"models": results, "native_executions": sum(x["executed_target_cases"] for x in results.values()),
                "backend_ranking": "NOT_ESTABLISHED", "legal_entailment": "NOT_ESTABLISHED"}
    if phase == "integration":
        at = now()
        request, store = bootstrap(root, out / "public-example", at=at)
        receipt = investigate(request, store)
        if receipt["may_execute_transaction"] or len(receipt["inventory"]) != len(inventory(PROFILE)):
            raise ValueError("Incomplete public inputs were incorrectly cleared")
        write(out / "public-example/assessment.json", receipt)
        revalidate(receipt, request, store)
        from .native import execute as native_execute
        native_dir = out.parent / completed["native"]["directory"]
        native_results = {}
        generated = hypothetical(request, store)
        generated_receipt = investigate(generated, store)
        write(out / "hypothetical-request.json", generated)
        write(out / "hypothetical-assessment.json", generated_receipt)
        for label, req, assessed in (("public", request, receipt), ("hypothetical", generated, generated_receipt)):
            native_results[label] = {}
            for target in ("ruleir", "catala"):
                native = native_execute(assessed, req, store, native_dir, target, JDK)
                write(out / (label + "-" + target + ".json"), native)
                statuses = {k: r["status"] for k, r in native["models"].items()}
                if label == "public" and any(x not in {"ABSTAIN", "UNSUPPORTED_ACTION_OR_CAPACITY"} for x in statuses.values()):
                    raise ValueError("Incomplete public facts escaped native abstention")
                if label == "hypothetical" and any(x != "VALUE" for x in statuses.values()):
                    raise ValueError("Complete generated premises failed native integration")
                native_results[label][target] = statuses
        registry = store.json(request["registry_sha256"])
        frozen = freeze(at=at, known_source_hashes=[r["blob"] for r in registry.values()])
        write(out / "prospective-freeze.json", frozen)
        return {"decision": receipt["decision"], "formal_outcome": receipt["formal_assessment"]["outcome"],
                "inventory_entries": len(receipt["inventory"]), "unresolved": receipt["formal_assessment"]["unresolved"],
                "sanctions_snapshots": receipt["sanctions_screenings"], "source_records": len(registry),
                "receipt_hash": receipt["receipt_hash"], "prospective_freeze_hash": frozen["freeze_hash"],
                "native_integration": native_results,
                "future_observations": 0, "complete_legal_compliance": "NOT_ESTABLISHED"}
    raise ValueError("Unknown phase")


def run(root, directory):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    directory.mkdir(parents=True, exist_ok=True)
    initial = input_identity(root)
    identity = digest(initial)
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"attempts": []}
    completed = {}
    for phase in PHASES:
        prior = [r for r in state["attempts"] if r["phase"] == phase and r["input_hash"] == identity and r["status"] == "PASS"]
        reusable = None
        for item in reversed(prior):
            path = directory / item["directory"]
            if item["outputs"] == output_hashes(path):
                reusable = item
                break
        if reusable is not None:
            completed[phase] = reusable
            print("Verified retained phase: " + phase, flush=True)
            continue
        index = 1 + sum(r["phase"] == phase for r in state["attempts"])
        name = phase + "-attempt-" + str(index).zfill(3)
        out = directory / name
        out.mkdir(exist_ok=False)
        started, at = time.monotonic(), now()
        receipt = {"phase": phase, "directory": name, "input_hash": identity, "started_at": at,
                   "status": "RUNNING", "command": [sys.executable, "scripts/run_bank_compliance_program.py"],
                   "environment": sys.executable, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1; no GPU framework",
                   "seeds": "N/A: exact specifications and deterministic generated cases",
                   "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                   "uncommitted_method": initial, "plan": "docs/plans/bank-compliance-closure.md"}
        state["attempts"].append(receipt)
        write(state_path, state)
        try:
            receipt["result"] = execute(phase, out, root, completed)
            if input_identity(root) != initial:
                raise ValueError("Method, plan or source changed during execution; recheck dependent phases")
            receipt["status"] = "PASS"
        except Exception as exc:
            receipt.update(status="REPAIR_REQUIRED", error=type(exc).__name__, detail=str(exc))
            (out / "failure.log").write_text(traceback.format_exc())
        receipt["wall_ms"] = int((time.monotonic() - started) * 1000)
        receipt["outputs"] = output_hashes(out)
        write(out / "receipt.json", receipt)
        write(state_path, state)
        if receipt["status"] == "PASS":
            completed[phase] = receipt
        refresh = {"after": phase, "completed": list(completed),
                   "next": [p for p in PHASES if p not in completed], "input_hash": identity,
                   "repair": None if receipt["status"] == "PASS" else receipt.get("detail"),
                   "action": "Continue independent engineering; unavailable private inputs and unproved meaning remain qualified",
                   "external_gaps": ["Actual bank policies/account/ownership data", "Complete current legal inventory",
                                     "Natural-language entailment", "Actual unseen future observations"]}
        write(directory / "next-phase.json", refresh)
        write(out / "next-phase.json", refresh)
        # The refresh record is part of the preserved output identity too.
        receipt["outputs"] = output_hashes(out)
        write(out / "receipt.json", receipt); write(state_path, state)
        print(phase + ": " + receipt["status"], flush=True)
        if receipt["status"] != "PASS":
            raise RuntimeError("Repair required; failure and next-phase instructions retained in " + str(out))
    summary = {"status": "ENGINEERING_PHASES_EXECUTED_WITH_LEGAL_QUALIFICATIONS", "input_hash": identity,
        "phases": {p: {"directory": r["directory"], "result": r["result"], "wall_ms": r["wall_ms"]} for p, r in completed.items()},
        "complete_legal_compliance": "NOT_ESTABLISHED", "human_quality_evidence": False,
        "remaining": ["Source semantics and complete applicable-law discovery are unproved",
                      "Internal policies and real account facts are not supplied",
                      "Unimplemented rule families remain explicit inventory obligations",
                      "Future-source observation series has zero real prospective observations"]}
    write(directory / "summary.json", summary)
    return summary
