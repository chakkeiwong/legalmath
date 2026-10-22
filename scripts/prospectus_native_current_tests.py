"""Retain bounded in-process live-driver tests; never launch native workers."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, file_hash, read, write
from legalmath.prospectus import native_current_acceptance as check
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess

TESTS = (*check.rehearsal.TESTS, check.TEST)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    authority = Authority(ROOT)
    with authority.lock():
        folder, admitted, task = (check.admission(authority, args.attempt) if args.live
                                 else check.prep.current_admission(authority, args.attempt))
        check.require(not (folder / "started.json").exists(), "Test methods must precede source freeze")
        if args.live:
            target = folder / "validation"
        else:
            runs = sorted((folder / "validation").glob("run-*"))
            check.require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Preparation test allowance exhausted/interrupted")
            target = folder / "validation" / f"run-{len(runs)+1:03d}"
        target.mkdir(parents=True, exist_ok=False)
        methods = check.methods(ROOT)
        write(target / "methods.json", methods, exclusive=True)
        with (target / "method-snapshots.json.gz").open("xb") as stream:
            stream.write(gzip.compress(json.dumps({p: (ROOT / p).read_text() for p in methods}).encode(), mtime=0))
        write(target / "started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", check.TEST_RUNNER, "--attempt", args.attempt, *(["--live"] if args.live else [])],
            "environment": sys.executable, "git_commit": admitted["git_commit"], "plan": task["dossier"],
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic"}, exclusive=True)
        tick, code, error = time.monotonic(), 1, None
        try:
            with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                with bounded_stage(), no_subprocess({"attempts": 0}):
                    import pytest
                    code = int(pytest.main(["-q", "-p", "no:cacheprovider", *TESTS, "--junitxml=" + str(target / "tests.xml")]))
                    check.require(check.methods(ROOT) == methods, "Candidate methods changed during tests")
        except BaseException as exc:
            code = 124 if isinstance(exc, TimeoutError) else 130 if isinstance(exc, KeyboardInterrupt) else 1
            error = {"type": type(exc).__name__, "message": str(exc)}
            with (target / "error.log").open("x") as stream: stream.write(traceback.format_exc())
        result = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "error": error,
            "wall_seconds": time.monotonic()-tick,
            "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        write(target / "result.json", result, exclusive=True)
        print(json.dumps(result))
        return code


if __name__ == "__main__":
    raise SystemExit(main())
