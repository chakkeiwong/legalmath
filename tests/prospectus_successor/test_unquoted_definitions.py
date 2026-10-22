"""Exact naming tokens, unfamiliar terms and conservative source boundaries."""
from copy import deepcopy
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import pytest

from legalmath.prospectus.successor import unquoted_definitions as module
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = BASE / 'reviews/unquoted-definitions-349'


def request(text, regions=None):
    return {'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'language': 'de',
        'regions': regions or [{'id': 'r', 'start': 0, 'end': len(text), 'selected': True, 'language': 'de'}]}


@pytest.mark.parametrize('text,label,value', [
    ('Die Bücher der ICSDs (unter denen die Bücher zu verstehen sind, die jede Stelle führt)', 'Bücher', 'die jede Stelle führt'),
    ('Bezugnahmen in diesen Anleihebedingungen auf Erlös der Schuldverschreibungen schließen, soweit anwendbar, die folgenden Beträge ein: den Bonus.', 'Erlös', 'den Bonus'),
    ('Bezugnahmen in diesen Anleihebedingungen auf Kosten auf die Schuldverschreibungen sollen, soweit anwendbar, weitere Kosten einschließen.', 'Kosten', 'weitere Kosten'),
    ('Für die Zwecke des Absatzes (7) dieses § 9 entspricht der besondere Betrag einer Schuldverschreibung dem Betrag.', 'besondere Betrag', 'dem Betrag'),
    ('Sondergesetz (SG)', 'SG', 'Sondergesetz'),
    ('Gesetz zur Beschränkung von Gebühren (Gebührengesetz)', 'Gebührengesetz', 'Gesetz zur Beschränkung von Gebühren'),
])
def test_unfamiliar_terms_are_discovered_without_vocabulary(text, label, value):
    rows = module.discover(request(text))['candidates']
    assert len(rows) == 1 and rows[0]['label'] == label and rows[0]['value']['raw'] == value
    assert rows[0]['term']['raw'] == label and rows[0]['governing_scope'] is None


def test_identical_terms_retain_different_printed_scope_and_value():
    text = ('Für die Zwecke des Absatzes (2) dieses § 5 entspricht der vorzeitige Betrag einer Schuldverschreibung dem Nennbetrag. '
            'Für die Zwecke des Absatzes [(5)] dieses § 5 entspricht der vorzeitige Betrag einer Schuldverschreibung dem Marktwert.')
    rows = module.discover(request(text))['candidates']
    assert len(rows) == 2 and rows[0]['label'] == rows[1]['label']
    assert [r['printed_scope_address']['paragraph'] for r in rows] == ['2', '5']
    assert [r['value']['raw'] for r in rows] == ['dem Nennbetrag', 'dem Marktwert']


def test_whitespace_maps_back_to_exact_original_term():
    text = 'Für die Zwecke des Absatzes (2) dieses § 5 entspricht der vorzeitige\nBetrag einer Schuldverschreibung dem Nennbetrag.'
    row = module.discover(request(text))['candidates'][0]
    assert row['label'] == 'vorzeitige Betrag' and row['term']['raw'] == 'vorzeitige\nBetrag'
    assert text[row['term']['start']:row['term']['end']] == row['term']['raw']


@pytest.mark.parametrize('text', [
    'Die Bücher der ICSDs (unter denen die Listen zu verstehen sind, die jede Stelle führt)',
    'Die Bücher der ICSDs (unter denen die Bücher zu\n\nverstehen sind, die jede Stelle führt)',
    'Sondergesetz ("SG")', 'Ein gewöhnliches Wort (Beispiel)',
    'Die tatsächliche Anzahl von Tagen in der jeweiligen Zinsperiode.',
    'Bezugnahmen auf Kapital in einem gewöhnlichen Satz.',
])
def test_near_misses_do_not_invent_declarations(text):
    assert module.discover(request(text))['candidates'] == []


@pytest.mark.parametrize('kind', ['unselected', 'other-language', 'split-selection'])
def test_selection_and_language_boundaries(kind):
    text = 'Sondergesetz (SG)'
    regions = [{'id': 'r', 'start': 0, 'end': len(text), 'selected': kind != 'unselected',
                'language': 'en' if kind == 'other-language' else 'de'}]
    if kind == 'split-selection':
        regions[0]['end'] = 8
        regions.append({'id': 'r2', 'start': 8, 'end': len(text), 'selected': True, 'language': 'de'})
    assert module.discover(request(text, regions))['candidates'] == []


@pytest.mark.parametrize('kind', ['hash', 'extra-vocabulary', 'region-gap', 'duplicate-region', 'language'])
def test_invalid_requests_refused(kind):
    value = request('Sondergesetz (SG)')
    if kind == 'hash': value['text_sha256'] = '0' * 64
    elif kind == 'extra-vocabulary': value['forms'] = ['SG']
    elif kind == 'region-gap': value['regions'][0]['start'] = 1
    elif kind == 'duplicate-region': value['regions'].append(deepcopy(value['regions'][0]))
    else: value['language'] = 'en'
    with pytest.raises(ValueError): module.discover(value)


@lru_cache(maxsize=1)
def source_case():
    manifest = json.loads((BASE / 'reviews/conditional-cli-311/products.json').read_text())
    products = {k: json.loads((ROOT / r['path']).read_text()) for k, r in manifest['products'].items()}
    old = json.loads(gzip.decompress((BASE / 'attempts/basf-references/attempt-087/ordinary-answer.json.gz').read_bytes()))
    return products, old


def test_original_source_exact_spans_before_full_consumers():
    from scripts.prospectus_unquoted_definitions_oracle import verify
    products, old = source_case()
    profile = json.loads((PREP / 'profile.json').read_text())
    actual = {**old, **module.evaluate(products, old, profile, ROOT, expected_profile_sha256=digest(profile))}
    actual['report_sha256'] = digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    assert verify(actual, old, products, json.loads((PREP / 'expected.json').read_text()))['status'] == 'PASS'


def test_existing_reviewed_vocabulary_is_not_an_input_to_discovery():
    products, old = source_case()
    changed = deepcopy(old)
    changed['definition_sources']['records'] = []
    assert module.content(products, changed) == module.content(products, old)
