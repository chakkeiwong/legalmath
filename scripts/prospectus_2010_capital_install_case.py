"""Isolated comparisons against sealed012; writes only its new small receipt."""
import importlib.util
import json
import os
from pathlib import Path
import sys


def main():
    root, previous, target, action = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    sys.dont_write_bytecode = True
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if sys.flags.isolated != 1 or any(n == "legalmath" or n.startswith("legalmath.") for n in sys.modules):
        raise ValueError("Isolated interpreter with no early package import required")
    package = (target / "installed/legalmath").resolve()
    sys.path.insert(0, str(package.parent))
    receipt = target / "installed-checks" / (action + ".json")

    def guard(event, args):
        if event.startswith("socket.") or event in {
            "subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.spawn"}:
            raise RuntimeError("Isolated comparison forbids network/process actions: " + event)
        if event == "open":
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing and (not isinstance(args[0], (str, bytes, os.PathLike)) or Path(args[0]).resolve() != receipt.resolve()):
                raise RuntimeError("Comparison may write only its new receipt")
        if event in {"os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink", "os.truncate"}:
            if event != "os.mkdir" or Path(args[0]).resolve() != receipt.parent.resolve():
                raise RuntimeError("Unexpected comparison filesystem mutation: " + event)

    sys.addaudithook(guard)
    spec = importlib.util.spec_from_file_location("frozen_capital191_cases", root / "scripts/prospectus_2010_capital_resume_cases.py")
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    cases.configure(root, previous)
    cases.require(action in {"candidate-products", "candidate-answer", *cases.INPUT_GROUPS, *cases.PHASE_GROUPS},
                  "Unreviewed installed comparison")
    expected = cases.read(previous / "final-package.json")
    cases.require(cases.legacy.package_files(package) == expected, "Installed package differs")
    result = cases.dispatch(action, installed=True)
    cases.require(result == cases.read(previous / "checks" / (action + ".json")), "Installed comparison differs: " + action)
    modules = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            cases.require(path.is_relative_to(package), "Checkout import: " + name)
            relative = str(path.relative_to(package))
            cases.require(cases.sha(path) == expected[relative], "Loaded module differs: " + name)
            modules[name] = relative
    cases.require(cases.legacy.package_files(package) == expected, "Installed package drift")
    value = {"status": "PASS", "action": action, "details": result, "python": sys.executable,
             "isolated": sys.flags.isolated, "package": str(package), "modules_relative_to_package": modules,
             "sys_path": sys.path, "package_files": len(expected), "native_calls": 0,
             "comparison_folder": str(previous), "comparison_folder_writes": 0}
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() + b"\n"
    cases.require(len(data) < 16384, "Installed receipt exceeds forecast")
    receipt.parent.mkdir(exist_ok=True)
    with receipt.open("xb") as stream:
        stream.write(data)
    print(json.dumps({"status": "PASS", "action": action, "package_files": len(expected)}))


if __name__ == "__main__":
    main()
