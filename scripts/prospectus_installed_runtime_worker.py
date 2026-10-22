"""Isolated frozen452-file profile, replay, controls and native lifecycle."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import gzip
import json
import os
from pathlib import Path
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True


class ExecutionGuard:
    """Bound Python process launches and refuse direct network/process bypasses."""
    def __init__(self, commands=(), manifest=None):
        self.commands = list(commands)
        self.manifest = manifest
        self.enabled = False
        self.starts = 0
        self.blocked = 0

    def expected(self, actual, inner):
        if self.manifest is None:
            return inner
        command = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
                   "--unshare-user", "--cap-drop", "ALL", "--clearenv", "--chdir", "/",
                   "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
        for name in sorted(self.manifest["directories"], key=lambda s: (s.count("/"), s)):
            command.extend(["--dir", name])
        descriptors = []
        for row in self.manifest["files"]:
            index = len(command) + 3
            fd = actual[index] if index < len(actual) else ""
            if not isinstance(fd, str) or not fd.isdecimal() or int(fd) < 3 or fd in descriptors:
                raise ValueError("Invalid sealed native descriptor")
            descriptors.append(fd)
            command.extend(["--perms", format(row["mode"], "o"), "--ro-bind-data", fd, row["path"]])
        for name, value in sorted(self.manifest["environment"].items()):
            command.extend(["--setenv", name, value])
        return [*command, "--remount-ro", "/", "--", *inner]

    def audit(self, event, args):
        if not self.enabled:
            return
        if event.startswith("socket.") or event in {"os.system", "os.fork", "os.forkpty", "os.exec", "os.posix_spawn", "os.spawn", "pty.spawn"}:
            self.blocked += 1
            raise RuntimeError("Network or direct process action forbidden: " + event)
        if event == "subprocess.Popen":
            try:
                argv = args[1]
                if (self.starts >= len(self.commands) or not isinstance(argv, (list, tuple)) or
                        list(argv) != self.expected(list(argv), self.commands[self.starts]) or args[0] != argv[0]):
                    raise ValueError("Unreviewed subprocess argv or exhausted allowance")
            except (ValueError, IndexError, TypeError):
                self.blocked += 1
                raise RuntimeError("Unreviewed subprocess argv or exhausted allowance") from None
            self.starts += 1

    def result(self):
        return {"starts": self.starts, "blocked": self.blocked}


@contextmanager
def execution_guard(commands=(), manifest=None):
    guard = ExecutionGuard(commands, manifest)
    sys.addaudithook(guard.audit)
    guard.enabled = True
    try:
        yield guard
    finally:
        guard.enabled = False


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report_controls(folder, product, helper):
    actual = helper.read(folder / "replays/2009-fresh/actual.json.gz")
    original = {p: actual[p] for p in ("P1", "P2", "P3", "P4", "P5")}
    from legalmath.prospectus.successor import service
    rows = []
    for case in ("missing-selection", "false-page", "unsupplied-selection"):
        bad = deepcopy(original)
        request = bad["P1"]["payload"]["request"]
        if case == "missing-selection":
            del bad["P2"]["payload"]["source_report_readings"]
        elif case == "false-page":
            reading = bad["P2"]["payload"]["source_report_readings"]["reports"][0]
            reading["pages"][0]["page"] += 1
            reading["sha256"] = product.digest({k: v for k, v in reading.items() if k != "sha256"})
        else:
            del request["source_report_readings"]
        bad["P1"] = service.seal("P1", request["bundle"], {"request": product.digest(request)}, bad["P1"]["payload"])
        for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")), ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
            bad[phase] = service.seal(phase, request["bundle"], {p: bad[p]["sha256"] for p in parents}, bad[phase]["payload"])
        expected = "Report readings lack supplied source evidence" if case == "unsupplied-selection" else "Report readings differ from supplied source evidence"
        try:
            service.consume(bad, Path(helper.read(folder / "capture-spec.json")["repository"]), mode="frozen", include_artifacts=True)
        except ValueError as exc:
            helper.require(str(exc) == expected, "Wrong installed report refusal")
            rows.append({"case": case, "reason": str(exc), "rejected": True,
                         "products": {p: v["sha256"] for p, v in bad.items()}})
        else:
            raise ValueError("Forged installed report selection accepted")
    return {"cases": rows}


def execute_stage(root, folder, stage, guard):
    config = json.loads((folder / "workspace.json").read_text())
    environment = Path(config["environment"])
    work = Path(config["directory"])
    helper = load("installed_helpers", work / "helpers/consumer.py")
    live = load("installed_lifecycle_helpers", work / "helpers/live.py")
    package = Path(config["package"]).resolve()
    helper.require(package == root / "docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-06/attempt-013/installed/legalmath", "Wrong current installed target")
    helper.require(not any(n == "legalmath" or n.startswith("legalmath.") for n in sys.modules), "Package imported before target selection")
    sys.path.insert(0, str(package.parent))
    expected = helper.read(folder / "source-package.json")
    helper.require(Path(sys.prefix) == environment, "Wrong installed profile interpreter")
    from legalmath.prospectus import native_profile as product
    from legalmath.prospectus.successor import process_ledger
    before_proof = helper.identity(package, root, expected)
    target = folder / "commands" / stage
    helper.save(target / "installed-proof-before.json", before_proof)
    # The copied original helper has no attempt-wide writer bound. Supply the
    # explicit bound for this campaign, including its owned control workspace.
    def save(path, value):
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        path = Path(path)
        encoded = gzip.compress(encoded, mtime=0) if path.suffix == ".gz" else encoded + b"\n"
        seen = {}
        for parent in (folder, work):
            for p in parent.rglob("*"):
                if p.is_file():
                    st = p.stat(); seen[st.st_dev, st.st_ino] = st.st_size
        helper.require(sum(seen.values()) + len(encoded) < 636 * 1024**2, "Installed profile evidence cap")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(encoded)
    helper.save = save
    counter = {"attempts": 0}
    before = len(process_ledger.checked(folder / "native-ledger.json")["reservations"])
    if stage.startswith("source-"):
        mode = stage.removeprefix("source-")
        helper.require(mode in ("fresh", "retained"), "Unknown installed source mode")
        with live.native_calls(folder / "native-ledger.json", 2):
            product.main(["source", "--request", str(folder / (mode + "-request.json")),
                "--profile", str(folder / "profile"), "--profile-sha256", helper.read(folder / "profile/capture-result.json")["profile_sha256"],
                "--output", str(folder / mode)])
        details = {"mode": mode, "action": "source"}
    else:
        with helper.no_native(counter):
            if stage == "capture":
                product.main(["capture", "--spec", str(folder / "capture-spec.json"), "--output", str(folder / "profile")])
                details = helper.read(folder / "profile/capture-result.json")
            elif stage == "check":
                pin = helper.read(folder / "profile/capture-result.json")["profile_sha256"]
                product.main(["check", "--profile", str(folder / "profile"), "--profile-sha256", pin, "--output", str(folder / "profile-check")])
                profile, manifest = product.load_profile(folder / "profile", pin)
                details = {m: product.preflight(helper.read(folder / (m + "-request.json")), profile, manifest) for m in ("fresh", "retained")}
                helper.save(folder / "preflight.json", details)
            elif stage.startswith("replay-"):
                details = helper.replay(root, folder, stage.removeprefix("replay-"))
            elif stage == "profile-controls":
                old = root / config["old_preparation"] / "profile"
                try:
                    product.load_profile(old, helper.read(old / "capture-result.json")["profile_sha256"])
                except ValueError as exc:
                    helper.require(str(exc) == "Installed product methods changed; recapture profile", "Wrong actual old-profile refusal")
                    old_refusal = {"case": "actual-old-profile", "refused": True, "error": str(exc)}
                else:
                    raise ValueError("Old product profile accepted by current installation")
                control_work = work / "profile-controls"
                control_work.mkdir()
                details = helper.controls(folder, control_work)
                details["cases"].append(old_refusal)
                details["adverse_controls"] += 1
            elif stage == "lifecycle-controls":
                control_work = work / "lifecycle-controls"
                control_work.mkdir()
                details = live.controls(folder, control_work, product, helper)
            elif stage == "report-controls":
                details = report_controls(folder, product, helper)
            else:
                action, mode = stage.split("-")
                helper.require(action in ("construct", "finish", "verify") and mode in ("fresh", "retained"), "Unknown installed lifecycle stage")
                product.main([action, "--output", str(folder / mode)])
                details = {"mode": mode, "action": action}
        helper.require(counter["attempts"] == (1 if stage in ("profile-controls", "lifecycle-controls") else 0),
                       "Unexpected installed native attempt")
    after = len(process_ledger.checked(folder / "native-ledger.json")["reservations"])
    helper.require(after - before == (2 if stage.startswith("source-") else 0), "Installed native denominator differs")
    helper.save(target / "installed-proof.json", helper.identity(package, root, expected))
    helper.save(target / "installed-result.json", {"status": "PASS", "details": details,
        "native_reservations": [before, after], "blocked_native_attempts": counter["attempts"],
        "process_guard": guard.result()})
    print(json.dumps({"status": "PASS", "stage": stage, "native_reservations": [before, after]}))


def main():
    root, folder = (Path(x).resolve() for x in sys.argv[1:3])
    stage = sys.argv[3]
    with execution_guard() as guard:
        if stage in ("source-fresh", "source-retained"):
            config = json.loads((folder / "workspace.json").read_text())
            mode = stage.removeprefix("source-")
            baseline = root / json.loads((folder / "baseline.json").read_text())["attempt"] / "routes" / ("2010-" + mode)
            guard.commands = [json.loads((baseline / "native" / str(i) / "receipt.json").read_text())["argv"] for i in (0, 1)]
            guard.commands[1][1] = str(Path(config["package"]) / "prospectus/successor/ocr_worker.py")
            guard.manifest = json.loads((folder / "expected-snapshot.json").read_text())
        execute_stage(root, folder, stage, guard)
        if guard.starts != len(guard.commands) or guard.blocked:
            raise RuntimeError("Installed process guard denominator differs")


if __name__ == "__main__":
    main()
