#!/usr/bin/env python3
"""Fixed, bounded entry point for the prospectus evidence continuation."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["PYTHONPATH"] = str(ROOT / "src")
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "continue":
        from legalmath.prospectus.evidence_continuation import main
        raise SystemExit(main(sys.argv[2:]))
    from legalmath.prospectus.master_control import main
    raise SystemExit(main())
