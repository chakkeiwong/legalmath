"""Run the isolated candidate with an explicit import root; no live dispatch."""
from pathlib import Path
import os
import sys

ROOT = Path('/home/chakwong/python/legalmath')
CANDIDATE = Path('/tmp/legalmath-baselines-corpus-hardened')
sys.path.insert(0, str(CANDIDATE / 'src'))
os.chdir(CANDIDATE)
import pytest
from legalmath.interpretation.assurance import corpus_review
assert Path(corpus_review.__file__).resolve().is_relative_to(CANDIDATE)
raise SystemExit(pytest.main([
    'tests/assurance/test_baseline_corpus_repairs.py',
    'tests/assurance/test_corpus_passage_attribution.py',
    'tests/assurance/test_context_exact_references.py',
    'tests/assurance/test_context_need_disposition.py',
    'tests/assurance/test_downstream_capacity.py',
    'tests/assurance/test_requirement_correction.py',
    'tests/assurance/test_source_review_repair.py',
    '-q', '--junitxml=' + str(ROOT /
        'artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/tests-attribution-qualified.xml')
]))
