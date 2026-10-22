"""Renamed terms, printed-purpose ambiguity and independent source checks."""
from copy import deepcopy
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import purpose_uses as module
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/purpose-use-discovery-351'


def request(text, regions=None):
    return {'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'language': 'de',
        'regions': regions or [{'id': 'r', 'start': 0, 'end': len(text), 'selected': True, 'language': 'de'}]}


def case(use='besonderen Betrag', adjective='besondere', noun='Betrag', bracket=False):
    label = '[(7)]' if bracket else '(7)'
    text = (f'(1) Allgemeiner Verweis: {use}.\n'
            f'{label} Der {use} ist zahlbar.\n'
            f'(10) {adjective.capitalize()} {noun}.\n'
            f'Für die Zwecke des Absatzes {label} dieses § 9 entspricht der {adjective} {noun} '
            'einer Schuldverschreibung dem Nennbetrag.')
    starts = [text.index(value) for value in ('(1)', label, '(10)')]
    index = [{'section': '9', 'path': [str(p)], 'start': a, 'end': b, 'printed_label': printed}
        for p, a, b, printed in zip((1, 7, 10), starts, starts[1:] + [len(text)], ('(1)', label, '(10)'))]
    return text, index


@pytest.mark.parametrize('stem,noun', [('besonder', 'Betrag'), ('rötlich', 'Entgelt'), ('sondermäßig', 'Bonus')])
@pytest.mark.parametrize('ending', ['e', 'en', 'er', 'es', 'em'])
def test_renamed_inflected_terms_connect_only_to_printed_purpose(stem, noun, ending):
    text, index = case(stem + ending + ' ' + noun, stem + 'e', noun)
    result = module.discover(request(text), index)
    rows = result['occurrences']
    assert len(rows) == 4
    assert [row['role'] for row in rows] == ['USE_CANDIDATE', 'USE_CANDIDATE', 'HEADING_CANDIDATE', 'DECLARATION_TERM']
    assert rows[0]['selected_declaration_starts'] == []
    assert rows[1]['selected_declaration_starts'] == [result['declarations'][0]['declaration_start']]
    assert rows[2]['selected_declaration_starts'] == []
    assert all(r['meaning'] is None and r['governing_scope'] is None for r in rows)


@pytest.mark.parametrize('use', ['BESONDEREN BETRAG', 'besonderen\nBetrag', 'besonderen\t Betrag', '(besonderen Betrag)'])
def test_case_whitespace_and_punctuation_preserve_exact_source(use):
    text, index = case(use)
    rows = module.discover(request(text), index)['occurrences']
    assert len(rows) == 4
    assert rows[1]['raw'] == use.strip('()')
    assert text[rows[1]['start']:rows[1]['end']] == rows[1]['raw']


@pytest.mark.parametrize('use', ['besonderen\n\nBetrag', 'besonderen\r\n \r\nBetrag', 'xbesonderen Betrag',
    'besonderen Betragsteil', 'un-besonderen Betrag', 'besonderen Betrag-Teil',
    'besonderen Betrag/Teil', 'besonderen Beträge', 'besonderenX Betrag',
    'besonderen Betrag\u0301', 'besonderen_Betrag'])
def test_compounds_substrings_and_paragraph_crossings_are_not_uses(use):
    text, index = case(use)
    rows = module.discover(request(text), index)['occurrences']
    assert [r['role'] for r in rows] == ['HEADING_CANDIDATE', 'DECLARATION_TERM']


def test_printed_optional_brackets_are_retained():
    text, index = case(bracket=True)
    declaration = module.discover(request(text), index)['declarations'][0]
    assert declaration['targets'][0]['printed_label'] == '[(7)]'
    assert declaration['printed_scope_address'] == {'section': '9', 'paragraph': '7'}


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'other-section'])
def test_missing_or_duplicate_destinations_do_not_choose_first(kind):
    text, index = case()
    if kind == 'missing': index.pop(1)
    elif kind == 'duplicate': index.append(deepcopy(index[1]))
    else: index[1]['section'] = '8'
    result = module.discover(request(text), index)
    assert result['declarations'][0]['address_status'] == (
        'AMBIGUOUS_PRINTED_ADDRESS' if kind == 'duplicate' else 'MISSING_PRINTED_ADDRESS')
    assert result['occurrences'][1]['status'] == 'UNRESOLVED_PRINTED_PURPOSE'
    assert result['occurrences'][1]['selected_declaration_starts'] == []
    assert result['occurrences'][-1]['role'] == 'DECLARATION_TERM'


@pytest.mark.parametrize('same_purpose', [False, True])
def test_same_name_declarations_are_preserved_and_ambiguous_uses_stay_ambiguous(same_purpose):
    text, index = case()
    second = '7' if same_purpose else '1'
    text += (f' Für die Zwecke des Absatzes ({second}) dieses § 9 entspricht der besondere Betrag '
             'einer Schuldverschreibung dem Marktwert.')
    index[-1]['end'] = len(text)
    result = module.discover(request(text), index)
    assert len(result['declarations']) == 2
    first, second = [r['declaration_start'] for r in result['declarations']]
    assert [r['value']['raw'] for r in result['declarations']] == ['dem Nennbetrag', 'dem Marktwert']
    assert result['occurrences'][1]['selected_declaration_starts'] == ([first, second] if same_purpose else [first])
    assert result['occurrences'][1]['status'] == ('AMBIGUOUS_PRINTED_PURPOSE' if same_purpose else 'UNIQUE_PRINTED_PURPOSE')
    assert [r['selected_declaration_starts'] for r in result['occurrences'] if r['role'] == 'DECLARATION_TERM'] == [[first], [second]]


def test_unsupported_adjective_form_remains_explicit():
    text, index = case(use='rosso Betrag', adjective='rosso')
    result = module.discover(request(text), index)
    assert result['declarations'] == [] and result['occurrences'] == []
    assert result['unsupported_declarations'][0]['reason'] == 'UNSUPPORTED_ADJECTIVE_NOUN_FORM'


@pytest.mark.parametrize('kind', ['unselected', 'other-language', 'split'])
def test_no_match_across_region_or_selection_boundaries(kind):
    text, index = case()
    cut = text.index('besonderen') + 5
    regions = [{'id': 'a', 'start': 0, 'end': len(text), 'selected': kind != 'unselected',
                'language': 'en' if kind == 'other-language' else 'de'}]
    if kind == 'split':
        regions[0]['end'] = cut
        regions.append({'id': 'b', 'start': cut, 'end': len(text), 'selected': True, 'language': 'de'})
    result = module.discover(request(text, regions), index)
    assert len(result['occurrences']) == (3 if kind == 'split' else 0)


@pytest.mark.parametrize('kind', ['hash', 'vocabulary', 'index-none', 'index-interval', 'index-label', 'index-path'])
def test_invalid_requests_and_index_are_refused(kind):
    text, index = case()
    value = request(text)
    if kind == 'hash': value['text_sha256'] = '0' * 64
    elif kind == 'vocabulary': value['forms'] = ['besonderen Betrag']
    elif kind == 'index-none': index = None
    elif kind == 'index-interval': index[0]['end'] = len(text) + 1
    elif kind == 'index-label': index[0]['printed_label'] = '(99)'
    else: index[0]['path'] = '1'
    with pytest.raises(ValueError): module.discover(value, index)


@lru_cache(maxsize=1)
def source_case():
    manifest = json.loads((AUTH / 'reviews/conditional-cli-311/products.json').read_text())
    products = {k: json.loads((ROOT / r['path']).read_text()) for k, r in manifest['products'].items()}
    old = json.loads(gzip.decompress((AUTH / 'attempts/basf-references/attempt-088/ordinary-answer.json.gz').read_bytes()))
    profile = json.loads((PREP / 'profile.json').read_text())
    actual = {**old, **module.evaluate(products, old, profile, ROOT, expected_profile_sha256=digest(profile))}
    actual['report_sha256'] = digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    return products, old, profile, actual


def test_independent_source_readings_before_expensive_consumers():
    from scripts.prospectus_purpose_uses_oracle import verify
    products, old, profile, actual = source_case()
    assert verify(actual, old, products, json.loads((PREP / 'expected.json').read_text()), profile)['status'] == 'PASS'


def test_reviewed_names_or_application_matrix_cannot_select_discovered_uses():
    products, old, _, _ = source_case()
    changed = deepcopy(old)
    changed['definition_sources']['records'] = []
    changed['definition_sources']['application_supplement'] = {'rules': [], 'applications': []}
    before, after = module.content(products, old), module.content(products, changed)
    before.pop('reviewed_binding_reconciliation')
    after.pop('reviewed_binding_reconciliation')
    assert before == after


@pytest.mark.parametrize('kind', ['scope-none', 'occurrence-none', 'declaration-none', 'target-none', 'reconciliation-none'])
def test_oracle_malformed_reports_require_explicit_refusal(kind):
    from scripts.prospectus_purpose_uses_oracle import verify
    products, old, profile, actual = source_case()
    bad = deepcopy(actual)
    report = bad[module.KEY]
    if kind == 'scope-none': report['declarations'][0]['restriction'] = None
    elif kind == 'occurrence-none': report['occurrences'][0] = None
    elif kind == 'declaration-none': report['declarations'][0] = None
    elif kind == 'target-none': report['declarations'][0]['targets'] = [None]
    else: report['reviewed_binding_reconciliation'] = None
    bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
    with pytest.raises(AssertionError): verify(bad, old, products, json.loads((PREP / 'expected.json').read_text()), profile)
