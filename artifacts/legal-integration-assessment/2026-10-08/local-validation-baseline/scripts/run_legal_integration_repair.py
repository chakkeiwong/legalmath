#!/usr/bin/env python3
"""Closed command interface for the reviewed integration repair program."""
import os
import sys
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if len(sys.argv) > 1 and sys.argv[1].startswith('assess-'):
    from scripts.legal_integration_assessment import main
else:
    from scripts.legal_integration_repair import main

if __name__ == '__main__':
    main()
