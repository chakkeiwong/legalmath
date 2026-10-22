"""Bounded current-admission stages. This version permits offline work only."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write
from legalmath.prospectus import native_current_preparation as checks
from legalmath.prospectus.successor import service
from scripts.prospectus_verify_task import cooperative_cancellation, retained_evidence_only

STAGES = ("prepare", *("replay-" + r for r in checks.ROUTES), "finalize")


def save(folder, name, value):
    path = checks.local(folder, name)
    encoded = (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode()
    if name.endswith(".gz"):
        encoded = gzip.compress(encoded, mtime=0)
    total = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
    checks.require(total + len(encoded) < checks.MAX_BYTES - 256 * 1024, "Preparation storage cap exceeded")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded)


@contextmanager
def bounded_stage(seconds=120):
    old = signal.getsignal(signal.SIGALRM)
    def timeout(*_):
        raise TimeoutError("Current native preparation stage exceeded its time bound")
    signal.signal(signal.SIGALRM, timeout)
    previous = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        with cooperative_cancellation():
            yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous)
        signal.signal(signal.SIGALRM, old)


@contextmanager
def no_subprocess(counter):
    with retained_evidence_only():
        blocked = subprocess.Popen
        def observe(*args, **kwargs):
            counter["attempts"] += 1
            return blocked(*args, **kwargs)
        subprocess.Popen = observe
        try:
            yield
        finally:
            subprocess.Popen = blocked


def prepare(root, folder):
    current = checks.methods(root)
    checks.check_tests(folder, current)
    save(folder, "methods.json", current)
    save(folder, "method-snapshots.json.gz", {p: (root / p).read_text() for p in current})
    save(folder, "offline-ledger.json", {"version": checks.VERSION, "native_call_allowance": 0,
        "historical_lower_bound": 50, "reservations": [],
        "scope": "Offline preparation; historical floor is not a successful-call total"})
    proof = checks.history(root)
    save(folder, "historical-evidence.json", proof)
    return {"historical_routes": len(proof["routes"]), "frozen_methods": len(current)}


def replay(root, folder, route):
    old_folder = checks.local(root, checks.ROUTES[route])
    old, baseline = checks.historical.products(old_folder)
    p1 = old["P1"]
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2, old["P3"]["payload"].get("interpretation_input"))
    p4 = service.law_product(p1, p3, old["P4"]["payload"].get("cases"), old["P4"]["payload"].get("law_input"))
    p5 = service.financial_product(p1, p2, p3, old["P5"]["payload"].get("cases"), old["P5"]["payload"].get("scenario_input"))
    current = dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5)
    answer = service.consume(current, root, mode="frozen", include_artifacts=True)
    refs, equal = {}, {}
    for key, obj in {**current, "answer": answer}.items():
        equal[key] = obj == (baseline if key == "answer" else old[key])
        path = old_folder / (key + ".json.gz")
        if not equal[key]:
            relative = "routes/" + route + "/" + key + ".json.gz"
            save(folder, relative, obj)
            path = folder / relative
        refs[key] = {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
    save(folder, "routes/" + route + "/comparison.json", {
        "route": route, "objects": refs, "equality": equal,
        "actual_current_consumer": True, "current_native_execution_established": False})
    checks.require(all(equal.values()), "Complete current downstream mismatch: " + ",".join(k for k, v in equal.items() if not v))
    return {"route": route, "complete_equality": True, "native_calls": 0}


def seal(folder, task, result):
    write(folder / "result.json", {**result, "task": task["id"], "scope": "OFFLINE_PREPARATION_ONLY",
        "whole_program_complete": False, "task_acceptance_established": False}, exclusive=True)
    verdict = "Offline preparation passed; live native acceptance remains pending." if result["status"] == "PASS" else "Offline preparation failed; the actual exception and partial evidence are retained."
    with (folder / "RESULT.md").open("x") as stream:
        stream.write("# Current native preparation\n\n" + verdict + "\n\n"
            "The exact command, environment, current methods, tests and stage outcomes are retained. "
            "Historical receipts remain historical. No fresh extraction or independent legal acceptance is established.\n\n"
            "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            f"| {'Retain partial preparation' if result['status'] == 'PASS' else 'Reject candidate'} | {result['status']} | "
            f"{'No offline check failed' if result['status'] == 'PASS' else 'See error.log'} | Current native source path untested | "
            "Record actual event and refresh; review live driver/source validation | No task or whole-program completion |\n")
    write(folder / "outputs.json", checks.files(folder), exclusive=True)


def run_stage(authority, attempt_name, stage):
    checks.require(stage in STAGES, "Live or unknown stage is disabled in offline preparation")
    with authority.lock():
        folder, admitted, task = checks.current_admission(authority, attempt_name)
        stage_folder = folder / "stages" / stage
        checks.require(not stage_folder.exists(), "Stage already started; duplicate refused")
        for previous in (folder / "stages").glob("*/started.json"):
            checks.require((previous.parent / "result.json").exists(), "Interrupted stage requires reconciliation")
        if stage == "prepare":
            checks.require(not (folder / "started.json").exists(), "Preparation already started")
        else:
            checks.require(read(folder / "stages/prepare/result.json")["status"] == "PASS", "Preparation required")
            checks.check_methods(authority.root, folder)
            checks.check_zero_ledger(folder)
        tick = time.monotonic()
        start = {"stage": stage, "started_at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", checks.SCRIPT, "--attempt", attempt_name, "--stage", stage],
            "environment": sys.executable, "git_commit": admitted["git_commit"],
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
            "plan": task["dossier"], "program_revision": admitted["revision"],
            "admission_sha256": file_hash(folder / "admission.json"),
            "result_file": attempt_name + "/stages/" + stage + "/result.json"}
        if stage == "prepare":
            save(folder, "started.json", start)
        save(folder, "stages/" + stage + "/started.json", start)
        counter, error, details = {"attempts": 0}, None, None
        try:
            with bounded_stage(), no_subprocess(counter):
                if stage == "prepare":
                    details = prepare(authority.root, folder)
                elif stage == "finalize":
                    details = checks.evidence(authority.root, folder)
                    save(folder, "preparation.json", details)
                else:
                    details = replay(authority.root, folder, stage.removeprefix("replay-"))
                checks.current_admission(authority, attempt_name)
                checks.check_methods(authority.root, folder)
                checks.check_zero_ledger(folder)
                checks.require(counter["attempts"] == 0, "A subprocess was attempted during offline work")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            with (stage_folder / "error.log").open("x") as stream:
                stream.write(traceback.format_exc())
        code = 0 if error is None else 124 if error["type"] == "TimeoutError" else 130 if error["type"] == "KeyboardInterrupt" else 1
        result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
            "wall_seconds": time.monotonic() - tick, "subprocess_attempts": counter["attempts"], "exit_code": code,
            "details": details, "current_native_execution_established": False}
        write(stage_folder / "result.json", result, exclusive=True)
        if error is not None or stage == "finalize":
            seal(folder, task, result)
        return code, {k: result[k] for k in ("status", "stage", "wall_seconds", "error", "subprocess_attempts")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    code, result = run_stage(Authority(ROOT), args.attempt, args.stage)
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
