#!/usr/bin/env python3
"""Fixed operations for the reviewed legal-gap validation program."""
import os
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.legal_gap_program import main

if __name__ == "__main__":
    main()
