"""Test the isolated controller and source together; no live provider is used."""
import os
from pathlib import Path
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path[:0] = [str(CANDIDATE/'src'), str(CANDIDATE), str(ROOT)]
import scripts
scripts.__path__ = [str(CANDIDATE/'scripts'), *list(scripts.__path__)]
from scripts import legal_review_deployment, legal_mission_control
from legalmath.interpretation.assurance.phased import context_disposition
for module in (legal_review_deployment, legal_mission_control, context_disposition):
    assert Path(module.__file__).is_relative_to(CANDIDATE), module.__file__
import pytest

raise SystemExit(pytest.main([
    'tests/tooling/test_review_context_isolation.py',
    'tests/tooling/test_review_deployment.py',
    'tests/assurance/test_corrected_context_disposition.py',
    'tests/assurance/test_context_need_disposition.py',
    'tests/assurance/test_context_pointer_warrant_targets.py',
    'tests/assurance/test_source_review_repair.py',
    '-q', '--junitxml=artifacts/legal-mission-control/2026-10-23/p14-corrected-context/deployment-tests.xml',
]))
