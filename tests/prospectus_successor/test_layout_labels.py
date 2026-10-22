from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor import layout_labels as module
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_layout_label_oracle import verify

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/layout-labels-324'
CASES = json.loads((PREP / 'cases.json').read_text())['cases']


def request(row):
    return {**{k: deepcopy(row[k]) for k in
        ('raw_units', 'source_sha256', 'language', 'quotation_convention', 'layout')},
        'raw_units_sha256': digest(row['raw_units'])}


@pytest.mark.parametrize('row', CASES, ids=lambda r: r['id'])
def test_frozen_source_and_constructed_cases(row):
    if row['expected_status'] == 'REFUSE':
        with pytest.raises(ValueError):
            module.review(request(row))
    else:
        assert verify(row, module.review(request(row)))['status'] == 'PASS'


def test_source_change_requires_a_new_binding():
    value = request(CASES[0])
    value['raw_units'][0]['raw'] += 'changed'
    with pytest.raises(ValueError, match='identity changed'):
        module.review(value)


def test_original_mixed_margin_body_line_is_not_discarded():
    result = module.review(request(CASES[0]))
    original = next(r for r in result['regions'][0]['name_provenance']
                    if r['label'].startswith('Ordem'))
    assert [s['unit'] for s in original['source_pieces']] == [
        'bes-2010-en:p190:l24', 'bes-2010-en:p190:l26']
    assert original['source_pieces'][1]['start'] == 4
    assert original['source_pieces'][1]['quote'] == 'Revisores Oficiais de Contas'
    assert any(s['unit'] == 'bes-2010-en:p190:l26' and s['quote'] == '190 '
               for s in result['source_accounting']['excluded'])
    assert len(original['formatting_spans']) == 1


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), True])
def test_nonfinite_or_missing_geometry_cannot_hide_source_words(value):
    data = request(CASES[1])
    data['raw_units'][1]['words'][0]['bbox'][0] = value
    with pytest.raises(ValueError):
        # Nonfinite values cannot acquire a canonical JSON identity; the
        # remaining invalid values reach the explicit geometry checks.
        data['raw_units_sha256'] = digest(data['raw_units'])
        module.review(data)
