"""Current finite native campaign; requires an explicit admitted live grant."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", LEGALMATH_OCR_PYTHON="/home/chakwong/miniconda3/envs/tfgpu/bin/python")
from legalmath.prospectus.execution_authority import Authority, file_hash, read, write
from legalmath.prospectus import native_current_acceptance as check
from legalmath.prospectus import native_source_rehearsal as source
from legalmath.prospectus.successor import process_ledger, sealed_runtime as runtime, sealed_source, service
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess


def save(folder, name, value):
    path = check.prep.local(folder, name)
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode()
    if name.endswith(".gz"): data = gzip.compress(data, mtime=0)
    check.require(check.storage(folder)["encoded_unique_bytes"] + len(data) < check.STORAGE_CAP - 2 * 1024 * 1024,
                  "Live storage bound exceeded")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


@contextmanager
def native_calls(folder, allowance, *, ledger=check.ledger):
    """Atomically count supervised starts, including failures, and cap this stage."""
    before = len(ledger(folder)["reservations"])
    with process_ledger.observe(folder / "process-ledger.json"):
        counted = subprocess.Popen
        def limited(*args, **kwargs):
            check.require(len(ledger(folder)["reservations"]) - before < allowance,
                          "Native stage call allowance exhausted before launch")
            return counted(*args, **kwargs)
        subprocess.Popen = limited
        try:
            yield
        finally:
            subprocess.Popen = counted


@contextmanager
def capture_default(folder):
    original = subprocess.run
    calls = []
    def captured(argv, *args, **kwargs):
        target = folder / str(len(calls))
        target.mkdir(parents=True, exist_ok=False)
        calls.append(argv)
        kwargs["timeout"] = min(kwargs.get("timeout", 60), 60)
        environment = kwargs.get("env", os.environ)
        write(target / "command.json", {"argv": argv, "timeout": kwargs["timeout"],
            "environment": {k: environment.get(k) for k in ("CUDA_VISIBLE_DEVICES", "OMP_THREAD_LIMIT", "LANG")}}, exclusive=True)
        encode = lambda data: data.encode() if isinstance(data, str) else data or b""
        (target / "stdin").write_bytes(encode(kwargs.get("input", b"")))
        try:
            result = original(argv, *args, **kwargs)
        except BaseException as error:
            for name, data in (("stdout", getattr(error, "output", b"")), ("stderr", getattr(error, "stderr", b""))):
                (target / name).write_bytes(encode(data))
            write(target / "result.json", {"returncode": getattr(error, "returncode", None),
                "error": {"type": type(error).__name__, "message": str(error)}}, exclusive=True)
            raise
        for name in ("stdout", "stderr"): (target / name).write_bytes(encode(getattr(result, name)))
        write(target / "result.json", {"returncode": result.returncode}, exclusive=True)
        return result
    subprocess.run = captured
    try:
        yield calls
    finally:
        subprocess.run = original


def prepare(root, folder, *, historical_floor=check.HISTORICAL_FLOOR):
    methods = check.methods(root)
    tested = check.tests(folder, methods)
    save(folder, "methods.json", methods)
    save(folder, "method-snapshots.json.gz", {p: (root / p).read_text() for p in methods})
    process_ledger.create(folder / "process-ledger.json", check.CALL_LIMIT, historical_floor,
        "Ten actual source calls plus one trusted boundary; no retry allowance; descendants excluded")
    save(folder, "historical-evidence.json", check.prep.history(root))
    owned = {}
    for year, attempt in (("2009", "attempt-008"), ("2010", "attempt-006")):
        old = check.prep.local(root, check.prep.BASE + "/attempts/native-binding/" + attempt + "/snapshot")
        manifest = check.prep.historical.snapshot(old)
        target = folder / "snapshots" / year
        (target / "blobs").mkdir(parents=True)
        for row in manifest["files"]:
            path = target / "blobs" / row["sha256"]
            if path.exists(): continue
            if row["sha256"] in owned:
                os.link(owned[row["sha256"]], path)  # Both paths belong to this new attempt.
            else:
                shutil.copyfile(old / "blobs" / row["sha256"], path)
                owned[row["sha256"]] = path
        save(folder, "snapshots/" + year + "/manifest.json", manifest)
        rows = {r["path"]: r for r in manifest["files"]}
        # Native worker/runtime/model bytes are checked without importing GPU frameworks.
        for route in (r for r in check.ROUTES if r.startswith(year)):
            req, _, _ = source.source_request(root, route)
            doc = req["bundle"]["documents"][0]
            names = [str((root / doc["path"]).resolve()), "/usr/bin/pdftotext",
                os.environ["LEGALMATH_OCR_PYTHON"], str(root / "src/legalmath/prospectus/successor/ocr_worker.py"),
                str(root / "src/legalmath/prospectus/successor/native_inputs.py"),
                str(root / doc["hybrid_profile"]["tessdata"] / "por.traineddata")]
            check.require(all(n in rows and file_hash(Path(n)) == rows[n]["sha256"] for n in names),
                          "Current native source/runtime input differs from protected snapshot")
    return {"tests": tested, "snapshot_unique_blobs": len(owned), "native_reservations": 0,
            "storage": check.storage(folder)}


def controls(root, folder, *, ledger=check.ledger):
    snapshot = folder / "snapshots/2009"
    manifest = read(snapshot / "manifest.json")
    indexed = {r["path"]: r for r in manifest["files"]}
    request, _, _ = source.source_request(root, "2009-fresh")
    doc = request["bundle"]["documents"][0]
    targets = {"source": str(root / doc["path"]), "model": str(root / doc["hybrid_profile"]["tessdata"] / "por.traineddata"),
        "worker": str(root / "src/legalmath/prospectus/successor/ocr_worker.py"), "executable": "/usr/bin/pdftotext"}
    results = []
    for name, path in targets.items():
        for mutation in ("wrong-hash", "missing"):
            candidate = sealed_source.SourceRuntime(snapshot, runtime.digest(manifest))
            changed = deepcopy(manifest)
            if mutation == "missing": changed["files"] = [r for r in changed["files"] if r["path"] != path]
            else: next(r for r in changed["files"] if r["path"] == path)["sha256"] = "0" * 64
            candidate.manifest, candidate.manifest_sha256 = changed, runtime.digest(changed)
            before = len(ledger(folder)["reservations"])
            try:
                candidate.execute(["/usr/bin/pdftotext"], b"", {"/usr/bin/pdftotext": indexed["/usr/bin/pdftotext"]["sha256"], path: indexed[path]["sha256"]})
            except ValueError as error:
                results.append({"input": name, "mutation": mutation, "reason": str(error), "refused": True,
                    "processes_before": before, "processes_after": len(ledger(folder)["reservations"])})
            else: raise ValueError("Required actual prelaunch refusal missing")
    save(folder, "actual-input-refusals.json", results)
    return {"prelaunch_refusals": check.prep.historical.check_controls(folder)}


def route(root, folder, name, *, ledger=check.ledger):
    request, old, old_raw = source.source_request(root, name)
    target = folder / "routes" / name
    target.mkdir(parents=True, exist_ok=False)
    before = len(ledger(folder)["reservations"])
    with native_calls(folder, 2, ledger=ledger):
        if name == "2009-default":
            with capture_default(target / "native") as calls:
                raw = service.source_product(request, root)
            check.require(len(calls) == 2, "Default source call denominator changed")
        else:
            snapshot = folder / "snapshots" / name[:4]
            candidate = sealed_source.SourceRuntime(snapshot, runtime.digest(read(snapshot / "manifest.json")),
                evidence_directory=target / "native", native_text_max_stream=64 * 1024 * 1024)
            raw = sealed_source.source_product(request, root, candidate)
            save(folder, "routes/" + name + "/receipts.json", candidate.receipts)
            check.require(len(candidate.receipts) == 2, "Selected source call denominator changed")
    p1 = check.prep.historical.rebind(raw, old["payload"]["request"]) if old_raw is not None else raw
    save(folder, "routes/" + name + "/raw-P1.json.gz", raw)
    save(folder, "routes/" + name + "/P1.json.gz", p1)
    check.check_source(root, folder, name)
    old_values, _ = check.prep.historical.products(check.prep.local(root, check.prep.ROUTES[name]))
    # Native budget is closed during all downstream construction/consumption.
    with no_subprocess({"attempts": 0}):
        values, answer = source.downstream(root, p1, old_values)
    for key in ("P2", "P3", "P4", "P5"):
        save(folder, "routes/" + name + "/" + key + ".json.gz", values[key])
    save(folder, "routes/" + name + "/answer.json.gz", answer)
    comparison = check.check_route(root, folder, name)
    save(folder, "routes/" + name + "/comparison.json", comparison)
    after = len(ledger(folder, before + 2)["reservations"])
    return {"route": name, "reservations": [before, after], "complete_equality": True}


def probe(root, folder, *, ledger=check.ledger):
    snapshot = folder / "snapshots/2009"
    manifest = read(snapshot / "manifest.json")
    host = folder / "host-only-sentinel"
    host.write_bytes(b"host-only\n")
    request, _, _ = source.source_request(root, "2009-fresh")
    pdf = str(root / request["bundle"]["documents"][0]["path"])
    program = ("import os,json\nfrom pathlib import Path\n"
        "r={'environment':dict(os.environ),'sentinel':Path(" + repr(check.SENTINEL) + ").read_text()}\n"
        "try: Path(" + repr(str(host)) + ").read_bytes();r['host_errno']=0\n"
        "except OSError as e:r['host_errno']=e.errno\n"
        "try: fd=os.open(" + repr(pdf) + ",os.O_WRONLY);os.close(fd);r['write_errno']=0\n"
        "except OSError as e:r['write_errno']=e.errno\nprint(json.dumps(r,sort_keys=True))\n")
    from legalmath.prospectus.successor.contracts import digest
    blob = snapshot / "blobs" / digest(b"before-capture\n")
    control = {"host_existed": host.is_file(), "host_path": str(host), "sentinel_path": check.SENTINEL,
        "host_extra_environment": "PROSPECTUS_HOST_ONLY", "before_sha256": file_hash(blob), "program": program}
    def mutate():
        blob.write_bytes(b"after-capture!\n")
        control["after_capture_sha256"] = file_hash(blob)
    target = folder / "probe"
    target.mkdir()
    previous = os.environ.get("PROSPECTUS_HOST_ONLY")
    os.environ["PROSPECTUS_HOST_ONLY"] = "must-not-leak"
    try:
        with native_calls(folder, 1, ledger=ledger):
            result = runtime.run(snapshot, manifest, [os.environ["LEGALMATH_OCR_PYTHON"], "-c", program], after_capture=mutate)
        for name in ("stdout", "stderr"): (target / name).write_bytes(result[name])
        (target / "stdin").write_bytes(b"")
        save(folder, "probe/receipt.json", result["receipt"])
    finally:
        blob.write_bytes(b"before-capture\n")
        control["restored_sha256"] = file_hash(blob)
        save(folder, "probe/control.json", control)
        if previous is None: os.environ.pop("PROSPECTUS_HOST_ONLY", None)
        else: os.environ["PROSPECTUS_HOST_ONLY"] = previous
    return {"receipt_sha256": check.prep.historical.check_probe(folder, manifest), "reservations": [10, 11]}


def seal(folder, result):
    write(folder / "result.json", {**result, "task": "native-binding", "scope": "FINITE_ENGINEERING_ONLY",
        "whole_program_complete": False}, exclusive=True)
    with (folder / "RESULT.md").open("x") as stream:
        stream.write("# Current native campaign\n\n" + ("The complete current finite native checks passed. Authority acceptance remains pending."
            if result["status"] == "PASS" else "The campaign failed. Actual error, partial evidence and consumed reservations are retained.") +
            "\n\nThe historical source/receipt comparators and current methods remain separate. "
            "No independent legal acceptance, universal dependency closure or portability is established.\n\n"
            "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            f"| {'Submit finite evidence' if result['status'] == 'PASS' else 'Reject candidate'} | {result['status']} | "
            f"{'Required checks passed' if result['status'] == 'PASS' else 'See stage error log'} | Shared source interpretation; one host | "
            "Authority record and refresh | No whole-program completion |\n")
    write(folder / "outputs.json", check.prep.files(folder), exclusive=True)


def run_stage(authority, name, stage):
    check.require(stage in check.STAGES, "Unknown current native stage")
    with authority.lock():
        folder, admitted, task = check.admission(authority, name)
        target = folder / "stages" / stage
        check.require(not target.exists(), "Current native stage already started")
        for marker in (folder / "stages").glob("*/started.json"):
            check.require((marker.parent / "result.json").exists(), "Interrupted native stage needs reconciliation")
        if stage == "prepare":
            check.require(not (folder / "started.json").exists(), "Live preparation already started")
        else:
            check.check_methods(authority.root, folder)
            check.require(read(folder / "stages/prepare/result.json")["status"] == "PASS", "Live preparation required")
            if stage not in ("controls", "route-2009-fresh"):
                canary = folder / "stages/route-2009-fresh/result.json"
                check.require(canary.exists() and read(canary)["status"] == "PASS", "Successful current canary required")
            if stage.startswith("route-"):
                check.require(read(folder / "stages/controls/result.json")["status"] == "PASS", "Prelaunch refusals required")
                index = check.ROUTES.index(stage.removeprefix("route-"))
                check.ledger(folder, index * 2)
            if stage == "probe": check.ledger(folder, 10)
        tick, error, details = time.monotonic(), None, None
        start = {"stage": stage, "command": ["timeout", "120", ".venv/bin/python", check.SCRIPT,
            "--attempt", name, "--stage", stage], "started_at": datetime.now(timezone.utc).isoformat(),
            "git_commit": admitted["git_commit"], "environment": sys.executable,
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
            "plan": task["dossier"], "grant": check.grant(task), "result_file": name + "/stages/" + stage + "/result.json"}
        if stage == "prepare": save(folder, "started.json", start)
        save(folder, "stages/" + stage + "/started.json", start)
        try:
            with bounded_stage():
                if stage.startswith("route-"):
                    details = route(authority.root, folder, stage.removeprefix("route-"))
                elif stage == "probe": details = probe(authority.root, folder)
                else:
                    with no_subprocess({"attempts": 0}):
                        if stage == "prepare": details = prepare(authority.root, folder)
                        elif stage == "controls": details = controls(authority.root, folder)
                        else:
                            details = check.evidence(authority.root, folder, task)
                            save(folder, "verification.json", details)
                check.admission(authority, name)
                check.check_methods(authority.root, folder)
                check.require(check.storage(folder)["encoded_unique_bytes"] < check.STORAGE_CAP - 1024 * 1024,
                              "Live finalization storage reserve exhausted")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            with (target / "error.log").open("x") as stream: stream.write(traceback.format_exc())
        code = 0 if error is None else 124 if error["type"] == "TimeoutError" else 130 if error["type"] == "KeyboardInterrupt" else 1
        result = {"status": "PASS" if error is None else "FAIL", "stage": stage, "error": error,
            "wall_seconds": time.monotonic() - tick, "exit_code": code, "details": details}
        write(target / "result.json", result, exclusive=True)
        if error is not None or stage == "finalize": seal(folder, result)
        return code, {k: result[k] for k in ("status", "stage", "error", "wall_seconds", "exit_code")}


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
