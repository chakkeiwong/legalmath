#!/usr/bin/env python3
"""Closed entry point for the reviewed retained-coverage continuation."""
import os
import sys
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if len(sys.argv) == 2 and sys.argv[1] in (
        'resume-check', 'resume-test', 'resume-execute', 'resume-status', 'resume-verify'):
    from scripts.legal_coverage_resume import main
else:
    from scripts.legal_integration_coverage import main

if __name__ == '__main__':
    main()
