"""Numbered source coverage must survive a self-consistent profile edit."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import statutory_references as subject

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/h38-numbered-repair-300/baseline/statutory_references_spec.json'


def h38(spec):
    return next(row for row in spec['records'] if row['id'] == 'H38')


def test_numbered_measures_reproduce_complete_primary_source():
    spec = subject.specification()
    record = h38(spec)
    source = record['legal_sources'][0]
    raw = (ROOT / source['text_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source['text_sha256']
    text = raw.decode('utf-8')
    measures = subject.validate_numbered_measures(spec)
    assert [row['number'] for row in measures] == list(range(1, 9))
    for row in measures:
        assert text[row['start']:row['end']] == row['quote']
        assert row['quote'].startswith(str(row['number']) + '.\n')
    assert 'Fälligkeit, der Verringerung oder dem Ausschluss der Zinsen' in measures[0]['quote']
    assert 'Verzicht auf das Kündigungsrecht der Gläubiger oder dessen Beschränkung' in measures[7]['quote']
    assert measures[7]['meaning'] == 'Waiver or restriction of holders termination rights'


@pytest.mark.parametrize('mutation', ['omit8', 'duplicate1', 'wrong-number', 'quote', 'offset', 'meaning'])
def test_numbered_validator_refuses_corruption_without_hash_shortcut(mutation):
    bad = deepcopy(subject.specification())
    rows = h38(bad)['numbered_measures']
    if mutation == 'omit8':
        rows.pop()
    elif mutation == 'duplicate1':
        rows[-1] = deepcopy(rows[0])
    elif mutation == 'wrong-number':
        rows[-1]['number'] = 9
    elif mutation == 'quote':
        rows[-1]['quote'] = rows[-1]['quote'].replace('Kündigungsrecht', 'Stimmrecht')
    elif mutation == 'offset':
        rows[-1]['start'] += 1
    else:
        rows[-1]['meaning'] = 'Change of the currency of the notes'
    with pytest.raises(ValueError, match='H38'):
        subject.validate_numbered_measures(bad)


def test_repair_preserves_every_other_h38_field():
    baseline = json.loads(BASELINE.read_text())
    current = subject.specification()
    modified = h38(current)
    old = h38(baseline)
    del modified['numbered_measures']
    for key in ('reviewed_reading', 'unresolved_application'):
        assert '8. Waiver or restriction' in modified[key]
        modified[key] = old[key]
    # Other records have independent reviewed migrations and regressions.
    assert modified == old
