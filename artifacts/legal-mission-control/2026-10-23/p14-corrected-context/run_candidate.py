"""Local-only corrected-context regression run; no provider dispatch."""
import os
from pathlib import Path
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path[:0] = [str(CANDIDATE/'src'), str(ROOT)]
from legalmath.interpretation.assurance.phased import context_disposition
assert Path(context_disposition.__file__).is_relative_to(CANDIDATE)
import pytest

raise SystemExit(pytest.main([
    'tests/assurance/test_corrected_context_disposition.py',
    'tests/assurance/test_context_need_disposition.py',
    '-q',
    '--junitxml=artifacts/legal-mission-control/2026-10-23/p14-corrected-context/candidate-complete-fixture.xml',
]))
