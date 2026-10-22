"""Actual isolated installed CLI lifecycle, with per-stage native accounting."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True


@contextmanager
def native_calls(ledger, limit):
    from legalmath.prospectus.successor import process_ledger
    before = len(process_ledger.checked(ledger)["reservations"])
    attempts = 0
    # Count in the shared ledger, including failed spawns, only after the local
    # per-stage cap permits this particular operation.
    with process_ledger.observe(ledger):
        observed = subprocess.Popen
        def limited(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts > limit:
                raise ValueError("Installed native stage allowance exhausted before launch")
            return observed(*args, **kwargs)
        subprocess.Popen = limited
        try:
            yield
        finally:
            subprocess.Popen = observed
    after = process_ledger.checked(ledger)["reservations"][before:]
    if attempts != limit or len(after) != limit or any(r["state"] != "STARTED" for r in after):
        raise ValueError("Missing, failed or extra installed native call")


def load_helper(path):
    spec = importlib.util.spec_from_file_location("installed_preparation_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controls(folder, workspace, product, helper):
    target = workspace / "controls"; target.mkdir()
    cases = []
    def refuses(name, action, expected):
        try: action()
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            helper.require(expected in str(exc), "Wrong control refusal: " + str(exc))
            cases.append({"case": name, "refused": True, "error": type(exc).__name__ + ": " + str(exc)})
        else: raise ValueError("Installed control accepted: " + name)
    failed = target / "failed"
    helper.save(failed / "stages/source/result.json", {"status": "FAIL", "files": {"P1.json.gz": "0" * 64}})
    refuses("failed-predecessor", lambda: product.construct(failed), "Predecessor stage did not pass")
    forged = target / "forged"
    shutil.copytree(folder / "fresh", forged, copy_function=shutil.copyfile)
    answer = product.read(forged / "answer.json.gz")
    answer["questions"]["Q1"]["status"] = "FORGED"
    answer["report_sha256"] = product.digest({k: v for k, v in answer.items() if k != "report_sha256"})
    (forged / "answer.json.gz").unlink(); product.write(forged / "answer.json.gz", answer)
    finish = product.read(forged / "stages/finish/result.json")
    finish["files"]["answer.json.gz"] = product.file_hash(forged / "answer.json.gz")
    (forged / "stages/finish/result.json").unlink(); product.write(forged / "stages/finish/result.json", finish)
    refuses("rehashed-forged-answer", lambda: product.verify(forged), "Delivered answer differs from actual consumer")
    missing = target / "missing"
    shutil.copytree(folder / "retained", missing, copy_function=shutil.copyfile)
    (missing / "native/1/stdout").unlink()
    refuses("missing-stream", lambda: product.verify(missing), "No such file")
    refuses("forbidden-subprocess", lambda: subprocess.Popen(["forbidden-native"]), "Native subprocess forbidden")
    return {"cases": cases, "controls": len(cases)}


def main():
    folder, root = (Path(x).resolve() for x in sys.argv[1:3])
    stage = sys.argv[3]
    read = lambda p: json.loads(p.read_text())
    source = read(folder / "preparation.json")
    preparation = root / source["attempt"]
    prep_workspace = Path(read(preparation / "workspace.json")["directory"])
    helper_path = prep_workspace / "installed_consumer.py"
    helper = load_helper(helper_path)
    helper.require(helper.sha(helper_path) == read(preparation / "methods.json")["scripts/prospectus_installed_consumer.py"], "Prepared helper changed")
    helper.require(helper.sha(Path(__file__)) == read(folder / "methods.json")["scripts/prospectus_installed_live_worker.py"], "Live helper changed")
    package = prep_workspace / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(preparation / "source-package.json")
    from legalmath.prospectus import native_profile as product
    from legalmath.prospectus.successor import process_ledger
    helper.require(Path(sys.prefix) == prep_workspace / "environment", "Wrong installed live interpreter")
    helper.identity(package, root, expected)
    before = len(process_ledger.checked(folder / "native-ledger.json")["reservations"])
    counter = {"attempts": 0}
    if stage == "controls":
        with helper.no_native(counter):
            details = controls(folder, Path(read(folder / "workspace.json")["directory"]), product, helper)
        helper.require(counter["attempts"] == 1, "Expected only intentional native refusal")
    else:
        action, mode = stage.split("-")
        helper.require(mode in ("fresh", "retained") and action in ("source", "construct", "finish", "verify"), "Unknown installed live stage")
        args = [action, "--output", str(folder / mode)]
        if action == "source":
            args.extend(["--request", str(preparation / (mode + "-request.json")), "--profile", str(preparation / "profile"),
                         "--profile-sha256", read(preparation / "profile/capture-result.json")["profile_sha256"]])
            with native_calls(folder / "native-ledger.json", 2): product.main(args)
        else:
            with helper.no_native(counter): product.main(args)
            helper.require(counter["attempts"] == 0, "Unexpected downstream native attempt")
        details = {"action": action, "mode": mode}
    after = len(process_ledger.checked(folder / "native-ledger.json")["reservations"])
    helper.require(after - before == (2 if stage.startswith("source-") else 0), "Installed native stage accounting differs")
    target = folder / "commands" / stage
    helper.save(target / "installed-proof.json", helper.identity(package, root, expected))
    helper.save(target / "installed-result.json", {"status": "PASS", "details": details,
        "native_reservations": [before, after], "blocked_attempts": counter["attempts"]})
    print(json.dumps({"status": "PASS", "stage": stage, "native_reservations": [before, after]}))


if __name__ == "__main__": main()
