"""Isolated installed consumer/profile checks; no native process is permitted."""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    path = Path(path)
    with (gzip.open(path, "rt") if path.suffix == ".gz" else path.open()) as stream:
        return json.load(stream)


def save(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(gzip.compress(data, mtime=0) if path.suffix == ".gz" else data + b"\n")


def package_files(package):
    result = {}
    for path in sorted(package.rglob("*")):
        require(not path.is_symlink(), "Package symlink refused")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[str(path.relative_to(package))] = sha(path)
    return result


def compare_objects(actual, expected):
    require(set(actual) == set(expected) == {"P1", "P2", "P3", "P4", "P5", "answer"},
            "Complete product denominator differs")
    for name in expected:
        require(actual[name] == expected[name], "Complete installed object differs: " + name)


@contextmanager
def no_native(counter):
    previous = subprocess.Popen
    def refuse(*args, **kwargs):
        counter["attempts"] += 1
        raise RuntimeError("Native subprocess forbidden in installed preparation")
    subprocess.Popen = refuse
    try:
        yield
    finally:
        subprocess.Popen = previous


def identity(package, root, expected):
    require(sys.flags.isolated == 1, "Isolated interpreter required")
    require(package_files(package) == expected, "Installed package bytes differ")
    require(all(not Path(p).resolve().is_relative_to(root / "src") for p in sys.path if p),
            "Checkout import path refused")
    loaded = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package), "Package import escaped installation: " + name)
            rel = str(path.relative_to(package))
            require(expected.get(rel) == sha(path), "Loaded module bytes differ: " + name)
            loaded[name] = {"path": str(path), "sha256": expected[rel]}
    return {"python": sys.executable, "prefix": sys.prefix, "isolated": sys.flags.isolated,
            "sys_path": sys.path, "modules": loaded, "package_files": len(expected)}


def replay(root, folder, route):
    from legalmath.prospectus.successor import service
    base = root / read(folder / "baseline.json")["attempt"] / "routes" / route
    expected = {n: read(base / (n + ".json.gz")) for n in ("P1", "P2", "P3", "P4", "P5", "answer")}
    p1 = expected["P1"]
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2, expected["P3"]["payload"].get("interpretation_input"))
    p4 = service.law_product(p1, p3, expected["P4"]["payload"].get("cases"), expected["P4"]["payload"].get("law_input"))
    p5 = service.financial_product(p1, p2, p3, expected["P5"]["payload"].get("cases"), expected["P5"]["payload"].get("scenario_input"))
    values = dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5)
    answer = service.consume(values, root, mode="frozen", include_artifacts=True)
    actual = {**values, "answer": answer}
    compare_objects(actual, expected)
    target = folder / "replays" / route
    save(target / "actual.json.gz", actual)
    result = {"route": route, "complete_objects_equal": True, "answer_sha256": answer["report_sha256"],
        "actual_current_consumer": True, "fresh_native_execution_established": False}
    save(target / "comparison.json", result)
    return result


def controls(folder, workspace):
    from legalmath.prospectus import native_profile as product
    current = folder / "profile"
    pin = read(current / "capture-result.json")["profile_sha256"]
    rows = []
    def refuses(name, function, expected):
        try:
            function()
        except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
            require(expected in str(exc), "Wrong refusal for " + name + ": " + str(exc))
            rows.append({"case": name, "error": type(exc).__name__ + ": " + str(exc), "refused": True})
        else:
            raise ValueError("Installed adverse input accepted: " + name)
    refuses("wrong-pin", lambda: product.load_profile(current, "0" * 64), "Pinned profile")
    private = workspace / "controls"
    private.mkdir()
    for label in ("blob-changed", "blob-missing", "method-changed", "runtime-changed", "manifest-changed"):
        trial = private / label
        shutil.copytree(current, trial, copy_function=os.link)
        value, manifest = read(trial / "profile.json"), read(trial / "snapshot/manifest.json")
        expected_pin = pin
        if label.startswith("blob-"):
            blob = trial / "snapshot/blobs" / manifest["files"][0]["sha256"]
            blob.unlink()
            if label == "blob-changed": blob.write_bytes(b"changed private input")
            error = "Snapshot blob" if label == "blob-changed" else "No such file"
        elif label == "manifest-changed":
            manifest["directories"].append("/different")
            (trial / "snapshot/manifest.json").unlink()
            save(trial / "snapshot/manifest.json", manifest)
            error = "Snapshot manifest identity"
        else:
            if label == "method-changed": value["methods"]["prospectus/native_profile.py"] = "0" * 64
            else: value["trusted_runtime"]["kernel_release"] = "changed"
            (trial / "profile.json").unlink()
            save(trial / "profile.json", value)
            expected_pin = product.digest(value)
            error = "Installed product methods" if label == "method-changed" else "Trusted runtime"
        refuses(label, lambda p=trial, h=expected_pin: product.load_profile(p, h), error)
    profile, manifest = product.load_profile(current, pin)
    request = read(folder / "fresh-request.json")
    request["bundle"]["documents"][0]["sha256"] = "0" * 64
    refuses("changed-source", lambda: product.preflight(request, profile, manifest), "Source bytes changed")
    refuses("duplicate-stage", lambda: product.stage(current, "capture", lambda: None, new=True), "File exists")
    expected = read(folder / "replays/2010-fresh/actual.json.gz")
    wrong = deepcopy(expected)
    wrong["answer"]["questions"]["Q1"]["status"] = "FORGED"
    wrong["answer"]["report_sha256"] = product.digest({k: v for k, v in wrong["answer"].items() if k != "report_sha256"})
    refuses("rehashed-answer", lambda: compare_objects(wrong, expected), "Complete installed object differs: answer")
    refuses("extra-subprocess", lambda: subprocess.Popen(["forbidden-native"]), "Native subprocess forbidden")
    return {"cases": rows, "adverse_controls": len(rows)}


def main():
    folder, root = (Path(n).resolve() for n in sys.argv[1:3])
    stage = sys.argv[3]
    workspace = Path(read(folder / "workspace.json")["directory"])
    package = Path(sys.prefix) / "lib/python3.11/site-packages/legalmath"
    require(Path(sys.prefix) == workspace / "environment", "Wrong installed interpreter")
    require(sha(Path(__file__)) == read(folder / "methods.json")["scripts/prospectus_installed_consumer.py"], "Installed helper changed")
    expected = read(folder / "source-package.json")
    from legalmath.prospectus import native_profile as product
    identity(package, root, expected)
    counter = {"attempts": 0}
    with no_native(counter):
        if stage == "capture":
            product.main(["capture", "--spec", str(folder / "capture-spec.json"), "--output", str(folder / "profile")])
            details = read(folder / "profile/capture-result.json")
        elif stage == "check":
            pin = read(folder / "profile/capture-result.json")["profile_sha256"]
            product.main(["check", "--profile", str(folder / "profile"), "--profile-sha256", pin, "--output", str(folder / "profile-check")])
            profile, manifest = product.load_profile(folder / "profile", pin)
            details = {mode: product.preflight(read(folder / (mode + "-request.json")), profile, manifest) for mode in ("fresh", "retained")}
            save(folder / "preflight.json", details)
        elif stage.startswith("replay-"):
            details = replay(root, folder, stage.removeprefix("replay-"))
        elif stage == "controls":
            details = controls(folder, workspace)
        else:
            raise ValueError("Unknown installed preparation stage")
    require(counter["attempts"] == (1 if stage == "controls" else 0), "Unexpected native process attempt")
    target = folder / "commands" / stage
    save(target / "installed-proof.json", identity(package, root, expected))
    save(target / "installed-result.json", {"status": "PASS", "details": details,
        "native_processes": 0, "blocked_native_attempts": counter["attempts"],
        "fresh_native_execution_established": False})
    print(json.dumps({"status": "PASS", "stage": stage, "native_processes": 0}))


if __name__ == "__main__":
    main()
