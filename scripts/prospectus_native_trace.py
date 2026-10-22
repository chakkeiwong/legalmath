"""Consume a hash-bound retained native trace as an offline diagnostic."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from legalmath.prospectus.successor.native_trace import account


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = account(Path(args.trace).read_bytes(), args.sha256)
    with Path(args.output).open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"line_count": report["line_count"], "counts": report["counts"],
                      "complete_native_closure": False, "native_reuse_allowed": False}))


if __name__ == "__main__":
    main()
