"""Current admitted installed native lifecycle with no unchanged retries."""
import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus import native_profile, native_installed_acceptance as old_check
from legalmath.prospectus.successor import process_ledger, sealed_runtime
from scripts import prospectus_installed_current as preparation
from scripts import prospectus_installed_consumer as helper
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess

VERSION = "installed-current-live-repair.v1"
SCRIPT = "scripts/prospectus_installed_live.py"
HELPER = "scripts/prospectus_installed_live_worker.py"
TEST = "tests/prospectus/test_installed_live.py"
COMMANDS = tuple(action + "-" + mode for mode in ("fresh", "retained") for action in ("source", "construct", "finish", "verify") if (action, mode) != ("source", "fresh")) + ("controls",)
STAGES = ("prepare", *COMMANDS, "finalize")
GRANT = {"version": VERSION, "maximum_outer_commands": 8, "maximum_native_reservations": 2,
    "historical_installed_outer_starts": 29, "historical_installed_native_starts": 6,
    "maximum_test_starts": 2, "repair_reservations": 0, "stage_timeout_seconds": 120,
    "evidence_bytes": 536870912, "workspace_bytes": 134217728,
    "network": False, "gpu": False, "installations": False}
require = preparation.require
common = preparation.prep.historical


@contextmanager
def offline():
    counter = {"attempts": 0}
    with no_subprocess(counter):
        yield
    require(counter["attempts"] == 0, "Unexpected caught offline subprocess attempt")


def admission(authority, name):
    folder = preparation.prep.local(authority.root, name)
    prefix = str((authority.base / "attempts/native-confinement").relative_to(authority.root))
    require(re.fullmatch(re.escape(prefix) + r"/attempt-[0-9]{3,}", name), "Current installed live attempt path required")
    ad = read(folder / "admission.json")
    program, tasks, _ = authority.spec(); task = tasks["native-confinement"]
    events = [e for e in authority.events() if e.get("task") == task["id"]]
    require(events and events[-1]["kind"] == "ADMIT" and events[-1]["attempt"] == name
        and events[-1]["admission_sha256"] == file_hash(folder / "admission.json"), "Current unclosed installed live admission required")
    require(ad["attempt"] == name and ad["task"] == task["id"] and ad["task_spec"] == task
        and ad["task_sha256"] == digest(task) and ad["program_sha256"] == digest(program)
        and ad["binding"] == authority.binding(task), "Installed live admission changed")
    require(task.get("installed_live") == GRANT and task.get("preparation_only") is False
        and task.get("native_call_allowance") == 2 and not task.get("validator"), "Explicit installed live grant required")
    require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed installed live attempt refused")
    preparation.prep.files(folder)
    return folder, ad, task


def methods(root):
    return {**preparation.methods(root), **{p: file_hash(root / p) for p in (SCRIPT, HELPER, TEST)}}


def check_methods(root, folder):
    value = methods(root)
    require(read(folder / "methods.json") == value, "Installed live methods changed")
    snapshot = helper.read(folder / "method-snapshots.json.gz")
    from hashlib import sha256
    require(set(value) == set(snapshot) and all(sha256(bytes.fromhex(snapshot[p])).hexdigest() == h for p, h in value.items()), "Installed live method snapshot changed")
    return value


def prepared(root, folder):
    row = read(folder / "preparation.json")
    target = preparation.prep.local(root, row["attempt"])
    require(file_hash(target / "outputs.json") == row["outputs_sha256"], "Preparation manifest changed")
    common.verify_files(target, read(target / "outputs.json"))
    preparation.checked_methods(root, target)
    work = preparation.workspace(root, target)
    require(helper.package_files(work / "environment/lib/python3.11/site-packages/legalmath") == read(target / "source-package.json"), "Prepared installed package changed")
    require(preparation.tree(work / "environment", dependencies=True) == read(target / "dependencies.json"), "Prepared dependency bytes changed")
    return target, work


def test_evidence(root, folder):
    runs = sorted((folder / "validation").glob("run-*/result.json"))
    require(1 <= len(runs) <= 2, "Installed live test allowance differs")
    target = runs[-1].parent; value = read(runs[-1])
    require(value["status"] == "PASS" and value["exit_code"] == 0 and value["wall_seconds"] <= 120
        and read(target / "methods.json") == methods(root) and value["tests_sha256"] == file_hash(target / "tests.xml"), "Current installed live tests failed or stale")
    suites = list(ET.parse(target / "tests.xml").getroot().iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Live tests failed or skipped")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "starts": len(runs), "sha256": value["tests_sha256"]}


def tests(authority, name):
    with authority.lock():
        folder, ad, task = admission(authority, name)
        require(not (folder / "started.json").exists(), "Tests must precede live method freeze")
        runs = sorted((folder / "validation").glob("run-*"))
        require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Live test allowance exhausted/interrupted")
        target = folder / "validation" / f"run-{len(runs)+1:03d}"; target.mkdir(parents=True)
        current = methods(authority.root)
        helper.save(target / "methods.json", current)
        helper.save(target / "method-snapshots.json.gz", {p: (authority.root / p).read_bytes().hex() for p in current})
        helper.save(target / "started.json", run_start(ad, task, name, "tests"))
        tick, code, error = time.monotonic(), 1, None
        try:
            with bounded_stage(), offline(), (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                import pytest
                code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, preparation.TEST, "tests/prospectus/test_native_profile.py", "--junitxml=" + str(target / "tests.xml")]))
                require(methods(authority.root) == current, "Live test methods changed")
        except BaseException as exc:
            code, error = 1, str(exc)
            (target / "error.log").write_text(traceback.format_exc())
        value = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "error": error,
            "wall_seconds": time.monotonic()-tick, "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        helper.save(target / "result.json", value)
        return code, value


def run_start(ad, task, name, stage):
    result = preparation.start(ad, task, name, stage)
    result["command"][3] = SCRIPT
    result["data_version"] = "Current installed004 profile and native017 2010 complete source comparators"
    return result


def prepare(authority, folder, task):
    tested = test_evidence(authority.root, folder)
    prior = authority.root / task["installed_preparation_attempt"]
    event = next(e for e in reversed(authority.events()) if e.get("attempt") == task["installed_preparation_attempt"] and e["kind"] == "RECORD")
    require(authority.retained_evidence_valid(event) and read(prior / "result.json")["status"] == "PASS", "Prepared partial evidence invalid")
    helper.save(folder / "preparation.json", {"attempt": task["installed_preparation_attempt"], "outputs_sha256": event["outputs_sha256"], "event": event["seq"]})
    prepared(authority.root, folder)
    current = methods(authority.root)
    helper.save(folder / "methods.json", current)
    helper.save(folder / "method-snapshots.json.gz", {p: (authority.root / p).read_bytes().hex() for p in current})
    work = Path(tempfile.mkdtemp(prefix="installed-live-", dir=authority.root / ".localresources/prospectus"))
    helper.save(folder / "workspace.json", {"directory": str(work)})
    process_ledger.create(folder / "outer-ledger.json", 8, 29, "Eight remaining installed commands; historical installed29 outer starts")
    process_ledger.create(folder / "native-ledger.json", 2, 6, "Two original remaining native calls; installed history6; native-binding history separate")
    origin = authority.root / task["source_recovery_attempt"]
    failed = next(e for e in reversed(authority.events()) if e.get("attempt") == task["source_recovery_attempt"] and e["kind"] == "REJECT")
    require(authority.retained_evidence_valid(failed) and read(origin / "commands/source-fresh/installed-result.json")["status"] == "PASS", "Recovery source evidence missing")
    require(len(process_ledger.checked(origin / "native-ledger.json")["reservations"]) == 2, "Recovery native count differs")
    shutil.copytree(origin / "fresh", folder / "fresh", copy_function=shutil.copyfile)
    files = preparation.prep.files(origin / "fresh")
    common.verify_files(folder / "fresh", files)
    helper.save(folder / "source-recovery.json", {"attempt": task["source_recovery_attempt"], "outputs_sha256": failed["outputs_sha256"],
        "fresh_files": files, "new_native_calls": 0, "failed_attempt_preserved": True})
    proof = source_evidence(authority.root, folder, "fresh")
    helper.save(folder / "recovered-source-verification.json", proof)
    return {"tests": tested, "native_reservations": 0, "workspace": str(work), "recovered_source": proof}


def product_bindings(actual, expected_request, execution, profile, profile_folder):
    """Product identities use the product serializer, never authority.digest."""
    product_digest = native_profile.digest
    require(actual["payload"]["request"] == expected_request, "Installed source request changed")
    native_profile.service.verify(actual, "P1", expected_request["bundle"], {"request": product_digest(expected_request)})
    require(execution["profile"] == str(profile_folder) and execution["profile_sha256"] == product_digest(profile)
        and execution["request_sha256"] == product_digest(expected_request) and execution["native_reuse_allowed"] is False,
        "Installed profile selection differs")


def checked_fresh_ocr(doc, stdout, receipt, manifest):
    """Reconstruct scan()'s full OCR object, including verified provenance."""
    data = json.loads(stdout)
    files = {row["path"]: row["sha256"] for row in manifest["files"]}
    interpreter, worker = receipt["argv"]
    data["runtime"].update(interpreter_sha256=files[interpreter], worker_sha256=files[worker],
        language_models=doc["hybrid_profile"]["models"], sealed_execution=receipt,
        dependency_assurance="SEALED_EXPLICIT_NATIVE_FILES; kernel/proc/dev trusted; reuse disabled")
    require(data["runtime"] == doc["runtime"] == doc["ocr_extraction"]["runtime"], "Complete reconstructed OCR runtime differs")
    hashed = native_profile.digest(data)
    require(doc["ocr_extraction"]["ocr_sha256"] == hashed, "Reconstructed complete OCR hash differs")
    return hashed


def compare_source_graph(actual, expected, mode, receipts, ocr_hashes=None):
    require(len(actual["documents"]) == len(expected["documents"]) == 1, "Source document denominator differs")
    candidate = deepcopy(actual)
    doc, old = candidate["documents"][0], expected["documents"][0]
    require(doc["native_extraction"]["sealed_execution"] == receipts[0], "Text receipt not delivered")
    doc["native_extraction"]["sealed_execution"] = old["native_extraction"]["sealed_execution"]
    target = doc["runtime"] if mode == "fresh" else doc["image_verification"]["verification_runtime"]
    old_target = old["runtime"] if mode == "fresh" else old["image_verification"]["verification_runtime"]
    require(target["sealed_execution"] == receipts[1], "OCR receipt not delivered")
    target["sealed_execution"] = old_target["sealed_execution"]
    if mode == "fresh":
        require(ocr_hashes is not None and doc["ocr_extraction"]["ocr_sha256"] == ocr_hashes[0]
            and old["ocr_extraction"]["ocr_sha256"] == ocr_hashes[1], "Verified reconstructed OCR hashes required")
        require(doc["ocr_extraction"]["runtime"]["sealed_execution"] == receipts[1], "Duplicate OCR receipt not delivered")
        doc["ocr_extraction"]["runtime"]["sealed_execution"] = old["ocr_extraction"]["runtime"]["sealed_execution"]
        doc["ocr_extraction"]["ocr_sha256"] = ocr_hashes[1]
    require(candidate == expected, "Complete installed source differs beyond checked receipts")


def source_evidence(root, folder, mode):
    prior, work = prepared(root, folder)
    base = root / read(prior / "baseline.json")["attempt"] / "routes" / ("2010-" + mode)
    job = folder / mode
    actual = helper.read(job / "P1.json.gz"); old = helper.read(base / "P1.json.gz")
    execution = read(job / "execution.json")
    require(actual["payload"]["request"] == old["payload"]["request"] == read(prior / (mode + "-request.json")), "Installed source request changed")
    profile, manifest = native_profile.load_profile(prior / "profile", read(prior / "profile/capture-result.json")["profile_sha256"])
    old_check.installed_proof(execution, work / "environment", native_profile.methods())
    product_bindings(actual, old["payload"]["request"], execution, profile, prior / "profile")
    required = old_check.installed_requirements(native_profile.preflight(actual["payload"]["request"], profile, manifest), manifest, work / "environment")
    require(execution["required_files"] == required, "Installed required files differ")
    rows = []
    for index in (0, 1):
        receipt, streams = common.receipt(job / "native" / str(index), manifest)
        for n, data in zip(("stdin", "stdout", "stderr"), streams):
            require(data == (base / "native" / str(index) / n).read_bytes(), "Complete installed native stream differs")
        expected_argv = read(base / "native" / str(index) / "receipt.json")["argv"]
        if index == 1:
            expected_argv[1] = str(work / "environment/lib/python3.11/site-packages/legalmath/prospectus/successor/ocr_worker.py")
        require(receipt["argv"] == expected_argv and receipt["limits"]["max_stream_bytes"] == (64 if index == 0 else 20) * 1024 * 1024, "Actual installed native dispatch/cap differs")
        rows.append(receipt)
    require(execution["native_receipts"] == rows, "Actual installed receipts differ")
    ocr_hashes = None
    if mode == "fresh":
        old_manifest = read(base.parents[1] / "snapshots/2010/manifest.json")
        old_receipt = read(base / "native/1/receipt.json")
        ocr_hashes = (checked_fresh_ocr(actual["payload"]["graph"]["documents"][0], (job / "native/1/stdout").read_bytes(), rows[1], manifest),
            checked_fresh_ocr(old["payload"]["graph"]["documents"][0], (base / "native/1/stdout").read_bytes(), old_receipt, old_manifest))
    compare_source_graph(actual["payload"]["graph"], old["payload"]["graph"], mode, rows, ocr_hashes)
    return {"mode": mode, "complete_source_equal_except_validated_receipts": True, "complete_native_streams_equal": True,
        "receipts": [r["receipt_sha256"] for r in rows]}


def compare(root, folder, mode):
    proof = source_evidence(root, folder, mode)
    prior, _ = prepared(root, folder)
    base = root / read(prior / "baseline.json")["attempt"] / "routes" / ("2010-" + mode)
    actual = common.products(folder / mode); baseline = common.products(base)
    common.compare_products(baseline, actual)
    common.consumer(root, *actual)
    expected = read(folder / mode / "verification.json")
    require(expected["answer_sha256"] == actual[1]["report_sha256"] and expected["native_calls"] == 2
        and expected["consumed_products"] == actual[1]["consumed_products"], "Installed verify did not consume its own products")
    return {**proof, "complete_semantics_equal": True, "current_consumer_recomputed": True, "answer_sha256": actual[1]["report_sha256"]}


def validate(root, folder):
    current = check_methods(root, folder); prior, work = prepared(root, folder)
    native = process_ledger.checked(folder / "native-ledger.json")
    outer = process_ledger.checked(folder / "outer-ledger.json")
    require(native["limit"] == 2 and native["historical_lower_bound"] == 6 and len(native["reservations"]) == 2
        and outer["limit"] == 8 and outer["historical_lower_bound"] == 29 and len(outer["reservations"]) == 8
        and all(r["state"] == "STARTED" for r in native["reservations"] + outer["reservations"]), "Actual installed process denominator differs")
    for stage, reservation in zip(COMMANDS, outer["reservations"]):
        require(read(folder / "commands" / stage / "command.json")["argv"] == reservation["argv"]
            and read(folder / "commands" / stage / "result.json")["returncode"] == 0, "Actual installed outer command differs")
        proof = read(folder / "commands" / stage / "installed-proof.json")
        require(proof["isolated"] == 1 and proof["prefix"] == str(work / "environment"), "Actual installed import proof differs")
        package = work / "environment/lib/python3.11/site-packages/legalmath"
        require(proof["modules"], "Missing installed loaded module proof")
        for row in proof["modules"].values():
            path = Path(row["path"])
            require(path.is_relative_to(package) and file_hash(path) == row["sha256"], "Actual installed module bytes differ")
        result = read(folder / "commands" / stage / "installed-result.json")
        require(result["status"] == "PASS", "Installed inner command failed")
        if stage.startswith("source-"):
            require(stage == "source-retained" and result["native_reservations"] == [0, 2], "Source reservation range differs")
    controls = read(folder / "commands/controls/installed-result.json")
    require(controls["blocked_attempts"] == 1 and {r["case"] for r in controls["details"]["cases"]}
        == {"failed-predecessor", "rehashed-forged-answer", "missing-stream", "forbidden-subprocess"}
        and all(r["refused"] for r in controls["details"]["cases"]), "Actual installed controls differ")
    cases = [compare(root, folder, mode) for mode in ("fresh", "retained")]
    recovery = read(folder / "source-recovery.json")
    origin = root / recovery["attempt"]
    require(file_hash(origin / "outputs.json") == recovery["outputs_sha256"], "Failed recovery source manifest changed")
    common.verify_files(origin, read(origin / "outputs.json"))
    common.verify_files(folder / "fresh", recovery["fresh_files"])
    old_native = process_ledger.checked(origin / "native-ledger.json")
    require(len(old_native["reservations"]) == 2 and all(r["state"] == "STARTED" for r in old_native["reservations"]), "Recovered source launches differ")
    for mode, reservations in (("fresh", old_native["reservations"]), ("retained", native["reservations"])):
        for offset in (0, 1):
            receipt = read(folder / mode / "native" / str(offset) / "receipt.json")
            argv = reservations[offset]["argv"]
            require(argv[0] == "/usr/bin/bwrap" and "--" in argv and argv[argv.index("--")+1:] == receipt["argv"], "Native ledger command differs from receipt")
    return {"version": VERSION, "methods_sha256": digest(current), "tests": test_evidence(root, folder), "cases": cases,
        "native_reservations": 2, "outer_starts": 8, "historical_installed_native_starts": 6,
        "historical_installed_outer_starts": 29, "recovered_source_native_reservations": 2,
        "whole_program_complete": False, "task_acceptance_established": False,
        "scope": "FINITE_CURRENT_INSTALLED_NATIVE_ENGINEERING", "independent_legal_acceptance": False, "portability_established": False}


def storage(folder):
    work = Path(read(folder / "workspace.json")["directory"])
    value = preparation.bounded_storage(folder, work)
    require(value["workspace_unique_bytes"] < GRANT["workspace_bytes"], "Installed live private workspace cap exceeded")
    return value


def seal(folder, task, result):
    helper.save(folder / "result.json", {**result, "task": task["id"], "scope": "FINITE_INSTALLED_LIVE_EVIDENCE",
        "whole_program_complete": False, "task_acceptance_established": False})
    (folder / "RESULT.md").write_text("# Current installed native lifecycle\n\nActual result: " + result["status"] +
        ". The stage files retain actual source, parent, answer, installed import, native stream and process evidence.\n\n"
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n|---|---|---|---|---|---|\n"
        f"| Retain actual live result | {result['status']} | See stage evidence | Same-host shared interpretation | Record and refresh, then review current acceptance or discriminating repair | No independent legal acceptance or whole-program completion |\n\n"
        "Post-run review: source preservation cannot establish independent legal correctness. A changed native stream, source field, import or answer would reject this candidate.\n")
    helper.save(folder / "outputs.json", preparation.prep.files(folder))


def run_stage(authority, name, stage):
    require(stage in STAGES, "Unknown installed live stage")
    with authority.lock():
        folder, ad, task = admission(authority, name)
        target = folder / "stages" / stage
        require(not target.exists(), "Installed live stage already started")
        for previous in STAGES[:STAGES.index(stage)]:
            marker = folder / "stages" / previous / "result.json"
            require(marker.exists() and read(marker)["status"] == "PASS", "Prior stage/canary required: " + previous)
        if stage != "prepare": check_methods(authority.root, folder)
        target.mkdir(parents=True)
        started = run_start(ad, task, name, stage)
        if stage == "prepare": helper.save(folder / "started.json", started)
        helper.save(target / "started.json", started)
        tick, error, details = time.monotonic(), None, None
        try:
            with bounded_stage():
                if stage == "prepare":
                    with offline(): details = prepare(authority, folder, task)
                elif stage == "finalize":
                    with offline(): details = validate(authority.root, folder)
                    helper.save(folder / "verification.json", details)
                else:
                    prior, work = prepared(authority.root, folder)
                    argv = [str(work / "environment/bin/python"), "-I", "-B", str(authority.root / HELPER), str(folder), str(authority.root), stage]
                    preparation.command(folder, Path(read(folder / "workspace.json")["directory"]), stage, argv)
                    with offline():
                        details = compare(authority.root, folder, stage.split("-")[1]) if stage.startswith("verify-") else source_evidence(authority.root, folder, stage.split("-")[1]) if stage.startswith("source-") else {"stage": stage, "returncode": 0}
                check_methods(authority.root, folder)
                admission(authority, name)
                storage(folder)
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            (target / "error.log").write_text(traceback.format_exc())
        code = 0 if error is None else 124 if error["type"] == "TimeoutError" else 1
        result = {"status": "PASS" if not error else "FAIL", "stage": stage, "error": error, "wall_seconds": time.monotonic()-tick,
            "exit_code": code, "details": details}
        helper.save(target / "result.json", result)
        if error or stage == "finalize": seal(folder, task, result)
        return code, {k: result[k] for k in ("status", "stage", "error", "wall_seconds")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True); parser.add_argument("--stage", required=True)
    args = parser.parse_args(); a = Authority(ROOT)
    code, result = tests(a, args.attempt) if args.stage == "tests" else run_stage(a, args.attempt, args.stage)
    print(json.dumps(result)); return code


if __name__ == "__main__": raise SystemExit(main())
