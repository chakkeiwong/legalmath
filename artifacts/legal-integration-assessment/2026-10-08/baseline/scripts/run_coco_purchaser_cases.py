#!/usr/bin/env python3
"""Execute the fixed two-prospectus study and preserve every phase attempt."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from legalmath.prospectus import purchaser_cases as cases
from legalmath.prospectus.common import JDK, LEAN, TOOLCHAIN, now, read, sha, write
from legalmath.canonical import digest
from legalmath.qualification import assurance
from legalmath.transaction import engine, intake

OUT = ROOT / "docs/implementation/coco-purchaser-cases"
PHASES = ("sources", "regression", "formal", "native", "integration")


def identity():
    paths = [Path(__file__), Path(cases.__file__), ROOT / "tests/prospectus/test_purchaser_cases.py",
             ROOT / "docs/plans/coco-purchaser-cases.md", cases.DOSSIER / "sources.json", cases.DOSSIER / "cases.json"]
    for source in read(cases.DOSSIER / "sources.json").values():
        paths += [ROOT / source["path"], ROOT / source["text_path"]]
    return {"files": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
            "shared_backend_methods": assurance.method_manifest(), "bank_method": engine.method_identity(),
            "tool_bytes": {str(p): sha(p.read_bytes()) for p in (LEAN, TOOLCHAIN["compiler"], JDK / "bin/java", JDK / "bin/javac")}}


def sources_phase(out, dossier, sources):
    result = cases.validate_dossier(dossier, sources)
    versions = {}
    for name, argv in (("java", [str(JDK / "bin/java"), "-version"]),
                       ("catala", [str(TOOLCHAIN["compiler"]), "--version"]), ("lean", [str(LEAN), "--version"])):
        p = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=True)
        versions[name] = {"command": argv, "version": (p.stdout + p.stderr).strip()}
    return {**result, "tools": versions}


def regression_phase(out, dossier, sources):
    argv = [sys.executable, "-m", "pytest", "-q", "tests/prospectus", "tests/compliance",
            "tests/translation/test_qualification_windows.py", "--junitxml=" + str(out / "tests.xml")]
    with (out / "pytest.log").open("w") as log:
        subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    suites = ET.parse(out / "tests.xml").getroot()
    totals = {k: sum(int(s.get(k, "0")) for s in suites.findall("testsuite")) for k in ("tests", "failures", "errors", "skipped")}
    if totals["errors"] or totals["failures"] or totals["skipped"]:
        raise ValueError("Regression evidence incomplete")
    return {"command": argv, **totals}


def formal_phase(out, dossier, sources):
    return cases.prove(out)


def native_phase(out, dossier, sources):
    inputs = cases.challenge_cases(dossier, sources)
    report = assurance.run(cases.model(), inputs, out / "assurance", JDK, toolchain=TOOLCHAIN)
    if report["proof"]["status"] != "KERNEL_CHECKED":
        raise ValueError("Missing kernel-checked formal preservation evidence")
    for target in report["targets"].values():
        if target["status"] != "CHECKED" or len(target["cases"]) != len(inputs):
            raise ValueError("Native backend unavailable or incomplete: " + str(target.get("detail")))
        for c, execution in zip(inputs, target["cases"]):
            reference = cases.evaluate(c)
            result = execution["result"]
            if reference["value"] is None:
                if result["status"] != "ABSTAIN":
                    raise ValueError("Incomplete/conflicting/stale input did not abstain")
            elif result["results"]["purchaser_route_pass"]["value"] != reference["value"]:
                raise ValueError("Native value differs from independent conditional route")
    counts = Counter(cases.evaluate(c)["status"] for c in inputs)
    return {"cases": len(inputs), "native_executions": len(inputs) * 2, "input_statuses": dict(counts),
            "qualification": report["summary"], "proof": report["proof"]["status"]}


def integration_phase(out, dossier, sources):
    request, store = intake.bootstrap(ROOT, out / "bank", at=now())
    rows = []
    for c, instrument in zip(cases.paired_cases(dossier, sources), dossier["instruments"]):
        r = deepcopy(request)
        registry = store.json(r["registry_sha256"])
        source = sources[instrument["source"]]
        registry[instrument["source"]] = intake.record(store.put((ROOT / source["path"]).read_bytes()),
            "law", source["url"], source["retrieved_at"], media_type="application/pdf")
        r["registry_sha256"] = store.put(registry)
        r["context"].update(instrument_id=instrument["id"], client_id="hypothetical-us-resident-individual")
        receipt = engine.investigate(r, store)
        engine.revalidate(receipt, r, store)
        combined = cases.attach_bank_investigation(cases.evaluate(c), receipt)
        layers = {x["layer"] for x in receipt["inventory"]}
        if len(layers) != 7 or combined["may_execute_transaction"] or receipt["may_execute_transaction"]:
            raise ValueError("Scope qualification or bank-layer inventory lost")
        path = out / (instrument["id"] + ".json")
        write(path, {"request": r, "case": c, "assessment": combined})
        rows.append({"instrument": instrument["id"], "isins": instrument["isins"],
            "purchaser_route": combined["offering_route"]["status"], "overall": combined["overall"],
            "bank_layers": len(layers), "bank_requirements": len(receipt["inventory"]),
            "bank_decision": receipt["decision"], "may_execute_transaction": False,
            "report": str(path.relative_to(ROOT))})
    return {"cases": rows, "actual_private_bank_approval": "NOT_ESTABLISHED", "human_quality_evidence": False}


def main():
    if len(sys.argv) != 1:
        raise SystemExit("This fixed study accepts no arbitrary commands or input paths")
    OUT.mkdir(parents=True, exist_ok=True)
    n = 1
    while (OUT / f"attempt-{n:03d}").exists():
        n += 1
    attempt = OUT / f"attempt-{n:03d}"; attempt.mkdir()
    started = time.monotonic(); bound = identity()
    dossier, sources = read(cases.DOSSIER / "cases.json"), read(cases.DOSSIER / "sources.json")
    write(attempt / "inputs.json", bound)
    manifest = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_worktree": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "command": [sys.executable, str(Path(__file__).resolve())], "python": sys.version,
        "platform": platform.platform(), "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1; no GPU imports",
        "random_seeds": "N/A: deterministic Boolean cases", "data_version": digest(sources),
        "plan": "docs/plans/coco-purchaser-cases.md", "result": str((attempt / "summary.json").relative_to(ROOT)),
        "started_at": now(), "input_hash": digest(bound)}
    write(attempt / "run-manifest.json", manifest)
    state = {"attempt": str(attempt.relative_to(ROOT)), "input_hash": digest(bound), "phases": {}, "status": "RUNNING"}
    try:
        for phase in PHASES:
            write(OUT / "next-phase.json", {"phase": phase, "action": "Execute or repair this phase; preserve failed attempts", "input_hash": digest(bound)})
            out = attempt / phase; out.mkdir()
            then = time.monotonic()
            result = globals()[phase + "_phase"](out, dossier, sources)
            write(out / "result.json", result)
            state["phases"][phase] = {"status": "PASS", "wall_ms": round(1000 * (time.monotonic() - then)), "result": result}
            write(OUT / "state.json", state)
            print(phase + ": PASS", flush=True)
        if identity() != bound:
            raise ValueError("Study inputs or methods changed during execution")
        state["status"] = "SCOPED_CASES_EXECUTED_WITH_LEGAL_QUALIFICATIONS"
        write(OUT / "next-phase.json", {"phase": "documentation", "action": "Document the qualified pair, compile and inspect the worked example; a scoped pass is not transaction approval."})
    except Exception as error:
        state.update(status="REPAIR_REQUIRED", failed_phase=phase, error=str(error), error_type=type(error).__name__)
        write(OUT / "next-phase.json", {"phase": phase, "action": "Repair the recorded failure and rerun; never replace an unknown legal/factual premise with true", "error": str(error)})
        raise
    finally:
        manifest.update(finished_at=now(), wall_ms=round(1000 * (time.monotonic() - started)))
        write(attempt / "run-manifest.json", manifest)
        write(attempt / "summary.json", state)
        write(OUT / "state.json", state)
        write(OUT / "summary.json", state)
    print(state["status"], flush=True)


if __name__ == "__main__":
    main()
