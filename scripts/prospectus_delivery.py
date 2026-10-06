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
    from legalmath.prospectus.successor.controller import execute, refresh
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    phase = commands.add_parser("phase")
    phase.add_argument("--phase", choices=[f"P{i}" for i in range(9)], required=True)
    commands.add_parser("run")
    commands.add_parser("status")
    args = parser.parse_args()
    if args.command == "status":
        result = refresh(ROOT)
    elif args.command == "phase":
        result = execute(ROOT, args.phase)
    else:
        result = [execute(ROOT, f"P{i}") for i in range(9)]
    import json
    print(json.dumps(result, indent=2))
    rows = result if isinstance(result, list) else [result]
    if any(r.get("execution") in {"FAILED", "DEPENDENCY_NOT_CURRENT", "REPAIR_REQUIRED"} for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
