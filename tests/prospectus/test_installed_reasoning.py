"""Harness integrity controls for exact installed full-answer verification."""
from copy import deepcopy
from pathlib import Path
import pytest

from scripts.prospectus_installed_reasoning_evidence import (
    EXPLANATIONS, load, products, same, verify_record,
)

ROOT = Path(__file__).resolve().parents[2]


def test_complete_comparison_rejects_unrelated_answer_loss():
    path = next((ROOT / EXPLANATIONS / 'calendar').glob('*.json.gz'))
    baseline = load(path)
    bad = deepcopy(baseline)
    bad['answers']['frozen']['questions'].pop('Q1')
    with pytest.raises(ValueError, match='Complete installed evidence differs'):
        same(bad, baseline, 'unrelated question')


def test_independent_record_check_rejects_replaced_authority_quote():
    paths = sorted((ROOT / EXPLANATIONS / 'calendar').glob('*.json.gz'))
    ps, _ = products(ROOT, 'calendar')
    original = load(paths[0])
    verify_record(ps, original, 'calendar')
    bad = deepcopy(original)
    bad['P4']['payload']['question']['value'][0]['explanation']['authority_source']['quote'] = 'forged'
    with pytest.raises(ValueError, match='Wrong explanation authority'):
        verify_record(ps, bad, 'calendar')
