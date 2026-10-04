"""Execute or resume the audited bank-compliance implementation checks."""
import argparse
from pathlib import Path

from legalmath.transaction.program import run

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/implementation/bank-compliance-closure")
    args = parser.parse_args()
    result = run(ROOT, args.out)
    print(result["status"])


if __name__ == "__main__":
    main()
