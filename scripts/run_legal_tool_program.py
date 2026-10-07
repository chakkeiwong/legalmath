#!/usr/bin/env python3
"""Use the exact fixed command documented in the legal tool comparison plan."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.legal_tool_program import main
if __name__ == "__main__":
    main()
