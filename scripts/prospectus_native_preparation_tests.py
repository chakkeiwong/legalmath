"""At most two retained in-process test starts for current offline preparation."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
from legalmath.prospectus.execution_authority import Authority, read, write, file_hash
from legalmath.prospectus import native_current_preparation as checks
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    authority = Authority(ROOT)
    with authority.lock():
        folder, admitted, task = checks.current_admission(authority, args.attempt)
        checks.require(not (folder / "started.json").exists(), "Tests must precede method freeze")
        runs = sorted((folder / "validation").glob("run-*"))
        checks.require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Test allowance exhausted or interrupted")
        target = folder / "validation" / f"run-{len(runs)+1:03d}"
        target.mkdir(parents=True)
        methods = checks.methods(ROOT)
        write(target / "methods.json", methods, exclusive=True)
        save(folder, str(target.relative_to(folder)) + "/method-snapshots.json.gz", {p: (ROOT / p).read_text() for p in methods})
        write(target / "started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_native_preparation_tests.py", "--attempt", args.attempt],
            "git_commit": admitted["git_commit"], "environment": sys.executable,
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
            "plan": task["dossier"], "result_file": str((target / "result.json").relative_to(ROOT))}, exclusive=True)
        tick, error, code = time.monotonic(), None, 1
        try:
            with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                with bounded_stage(), no_subprocess({"attempts": 0}):
                    import pytest
                    code = int(pytest.main(["-q", "-p", "no:cacheprovider", *checks.TESTS,
                        "--junitxml=" + str(target / "tests.xml")]))
                    checks.require(checks.methods(ROOT) == methods, "Methods changed during tests")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            code = 124 if isinstance(exc, TimeoutError) else 130 if isinstance(exc, KeyboardInterrupt) else 1
            with (target / "error.log").open("x") as stream: stream.write(traceback.format_exc())
        result = {"status": "PASS" if code == 0 and error is None else "FAIL", "exit_code": code,
            "wall_seconds": time.monotonic()-tick, "error": error,
            "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        write(target / "result.json", result, exclusive=True)
        import json
        print(json.dumps(result))
        return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
