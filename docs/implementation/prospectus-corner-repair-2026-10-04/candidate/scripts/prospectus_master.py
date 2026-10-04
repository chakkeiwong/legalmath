#!/usr/bin/env python3
"""Fixed entry point for the prospectus campaign; no arbitrary commands accepted."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

if __name__ == "__main__":
    from legalmath.prospectus.campaign import main
    raise SystemExit(main())

