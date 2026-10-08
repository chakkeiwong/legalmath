"""Fixed local phase dispatcher. Use: python3 -m scripts.prospectus_delivery run."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    application_python = ROOT / ".venv/bin/python"
    if Path(sys.executable).absolute() != application_python.absolute():
        os.execv(str(application_python), [str(application_python), "-m", "scripts.prospectus_delivery", *sys.argv[1:]])
    # Checkout runner only. P6 separately verifies the installed CLI.
    sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor import controller
    from legalmath.prospectus.successor.controller import execute, refresh
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", choices=["repair", "adoption"], default="repair")
    commands = parser.add_subparsers(dest="command", required=True)
    phase = commands.add_parser("phase")
    phase.add_argument("--phase", choices=[f"P{i}" for i in range(9)] + [f"A{i}" for i in range(7)], required=True)
    commands.add_parser("run")
    commands.add_parser("status")
    check = commands.add_parser("check")
    check.add_argument("tests", nargs="*", default=["tests/prospectus_successor", "tests/prospectus/test_closure_mechanisms.py"])
    check.add_argument("--junitxml", help="Preserve the regression result for the execution record")
    repair = commands.add_parser("repair")
    repair.add_argument("--record", required=True)
    args = parser.parse_args()
    if args.command == "check":
        # The package-wide suite includes both controller programs. A CLI
        # selection must not alter the initial module state of those tests.
        import pytest
        outputs = ["--junitxml=" + args.junitxml] if args.junitxml else []
        raise SystemExit(pytest.main(["-q", *args.tests, *outputs]))
    controller.configure(args.program)
    if args.command == "phase" and args.phase not in controller.DAG:
        parser.error("Phase does not belong to selected program")
    if args.command == "repair":
        from legalmath.prospectus.successor.controller import admit_record
        from legalmath.prospectus.successor.contracts import read
        result = admit_record(ROOT, read(args.record))
    elif args.command == "status":
        result = refresh(ROOT)
    elif args.command == "phase":
        result = execute(ROOT, args.phase)
    else:
        result = [execute(ROOT, phase) for phase in controller.DAG]
    import json
    print(json.dumps(result, indent=2))
    rows = result if isinstance(result, list) else [result]
    if any(r.get("execution") in {"FAILED", "DEPENDENCY_NOT_CURRENT", "REPAIR_REQUIRED"} for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
