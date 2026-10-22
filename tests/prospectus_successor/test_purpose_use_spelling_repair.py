"""Printed German sharp-s spellings must not disappear or merge with ss."""
import hashlib

import pytest

from legalmath.prospectus.successor import purpose_uses as module


def source(use, adjective, noun):
    text = (f'(1) Der {use} ist zahlbar.\n'
        f'Für die Zwecke des Absatzes (1) dieses § 9 entspricht der {adjective} {noun} '
        'einer Schuldverschreibung dem Nennbetrag.')
    request = {'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'language': 'de', 'regions': [{'id': 'r', 'start': 0, 'end': len(text),
            'selected': True, 'language': 'de'}]}
    index = [{'section': '9', 'path': ['1'], 'start': 0, 'end': len(text), 'printed_label': '(1)'}]
    return request, index


@pytest.mark.parametrize('stem,noun', [('sondermäßig', 'Bonus'), ('groß', 'Maß'),
    ('mäßig', 'Fuß'), ('besonder', 'Straße')])
@pytest.mark.parametrize('ending', ['e', 'en', 'er', 'es', 'em'])
@pytest.mark.parametrize('case', ['printed', 'capital-sharp-s', 'title'])
def test_sharp_s_in_adjective_or_noun_preserves_source_and_purpose(stem, noun, ending, case):
    use = stem + ending + ' ' + noun
    if case == 'capital-sharp-s':
        use = ''.join('ẞ' if char == 'ß' else char.upper() for char in use)
    elif case == 'title':
        use = use[0].upper() + use[1:]
    request, index = source(use, stem + 'e', noun)
    rows = module.discover(request, index)['occurrences']
    assert len(rows) == 2
    assert rows[0]['raw'] == use
    assert (rows[0]['start'], rows[0]['end']) == (8, 8 + len(use))
    assert rows[0]['role'] == 'USE_CANDIDATE'
    assert rows[0]['status'] == 'UNIQUE_PRINTED_PURPOSE'
    assert rows[0]['selected_declaration_starts'] == rows[1]['selected_declaration_starts']
    assert rows[1]['role'] == 'DECLARATION_TERM'
    assert rows[1]['raw'] == stem + 'e ' + noun
    assert all(row['meaning'] is None and row['governing_scope'] is None for row in rows)


@pytest.mark.parametrize('use,adjective,noun', [
    ('sondermässigen Bonus', 'sondermäßige', 'Bonus'),
    ('besonderen Masse', 'besondere', 'Maße'),
    ('besonderen Maße', 'besondere', 'Masse'),
    ('besonderen Strasse', 'besondere', 'Straße')])
def test_full_fold_substitutions_do_not_select_printed_terms(use, adjective, noun):
    request, index = source(use, adjective, noun)
    result = module.discover(request, index)
    assert len(result['declarations']) == 1
    assert [r['role'] for r in result['occurrences']] == ['DECLARATION_TERM']


def test_coexisting_sharp_s_and_ss_declarations_do_not_merge():
    text = ('(1) Der besonderen Maße und der besonderen Masse.\n'
        'Für die Zwecke des Absatzes (1) dieses § 9 entspricht der besondere Maße '
        'einer Schuldverschreibung dem Nennbetrag. '
        'Für die Zwecke des Absatzes (1) dieses § 9 entspricht der besondere Masse '
        'einer Schuldverschreibung dem Marktwert.')
    request = {'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'language': 'de', 'regions': [{'id': 'r', 'start': 0, 'end': len(text),
            'selected': True, 'language': 'de'}]}
    index = [{'section': '9', 'path': ['1'], 'start': 0, 'end': len(text), 'printed_label': '(1)'}]
    result = module.discover(request, index)
    declarations, rows = result['declarations'], result['occurrences']
    assert len(declarations) == 2 and len(rows) == 4
    assert [row['raw'] for row in rows] == [
        'besonderen Maße', 'besonderen Masse', 'besondere Maße', 'besondere Masse']
    a, b = [row['declaration_start'] for row in declarations]
    assert [row['compatible_declaration_starts'] for row in rows] == [[a], [b], [a], [b]]
    assert [row['selected_declaration_starts'] for row in rows] == [[a], [b], [a], [b]]
    assert [row['status'] for row in rows[:2]] == ['UNIQUE_PRINTED_PURPOSE'] * 2
