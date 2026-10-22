"""Frozen source judgments, inherited scopes, and adversarial destination tests."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import gzip
import json
import pytest

from legalmath.prospectus.successor import reference_addresses as module
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = BASE / 'reviews/reference-addresses-345'


@lru_cache(maxsize=1)
def source_case():
    manifest = json.loads((BASE / 'reviews/conditional-cli-311/products.json').read_text())
    products = {k: json.loads((ROOT / r['path']).read_text()) for k, r in manifest['products'].items()}
    old = json.loads(gzip.decompress((BASE / 'attempts/basf-references/attempt-083/ordinary-answer.json.gz').read_bytes()))
    return products, old


@pytest.mark.parametrize('paths,connectors,parent,wanted', [
    ([['1', 'b'], ['1', 'c']], ['und/oder'], ['2'], [['1', 'b'], ['1', 'c']]),
    ([['1', 'a'], ['1', 'd'], ['g']], ['und', 'bis'], ['2'],
     [['1', 'a'], ['1', 'd'], ['1', 'e'], ['1', 'f'], ['1', 'g']]),
    ([['a', 'ii'], ['iii']], ['und'], ['7', 'b', 'i'], [['7', 'a', 'ii'], ['7', 'a', 'iii']]),
    ([['a'], ['b'], ['c'], ['d']], [',', ',', 'und'], ['1', 'e'],
     [['1', 'a'], ['1', 'b'], ['1', 'c'], ['1', 'd']]),
    ([['b']], [], ['4', 'a'], [['4', 'b']]),
    ([['b']], [], ['5', 'a'], [['5', 'b']]),
    ([['2'], ['4']], ['bis'], ['8'], [['2'], ['3'], ['4']]),
    ([['a']], [], [], [['a']]),
    ([['1'], ['2']], ['oder'], [], [['1'], ['2']]),
])
def test_declared_address_grammar(paths, connectors, parent, wanted):
    assert module.expanded_paths(paths, connectors, parent) == wanted


@pytest.mark.parametrize('paths,connectors,parent', [
    ([['1', 'd'], ['2', 'g']], ['bis'], []),
    ([['1', 'g'], ['d']], ['bis'], []),
    ([['1'], ['100']], ['bis'], []),
    ([['ii']], [], []),
    ([['2', 'ii']], [], []),
    ([['01']], [], []),
    ([['1000']], [], []),
    ([['z']], [], []),
    ([['1'], ['2']], ['unless'], []),
    ([['1'], ['2']], [], []),
])
def test_invalid_grammar_refused(paths, connectors, parent):
    with pytest.raises(ValueError):
        module.expanded_paths(paths, connectors, parent)


def test_original_source_targets_before_expensive_consumers():
    from scripts.prospectus_reference_addresses_oracle import verify
    products, old = source_case()
    profile = json.loads((PREP / 'profile.json').read_text())
    actual = {**old, **module.evaluate(products, old, profile, ROOT, expected_profile_sha256=digest(profile))}
    actual['report_sha256'] = digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    assert verify(actual, old, products, json.loads((PREP / 'expected.json').read_text()))['status'] == 'PASS'


@lru_cache(maxsize=1)
def index_case():
    products, old = source_case()
    text, _, _, nodes, issues = module.source_model(products, old)
    groups = module.compound_groups(text, old['reference_scope_context']['contexts'],
                                   old['paragraph_reference_discovery']['discovery']['candidates'])
    assert issues == []
    return nodes, groups


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'other-document', 'other-context', 'wrong-parent'])
def test_equal_labels_cannot_select_unbound_target(kind):
    original, groups = index_case()
    nodes = deepcopy(original)
    target = next(n for n in nodes if n['section'] == '5' and n['path'] == ['4', 'b'])
    if kind == 'missing':
        nodes.remove(target)
    elif kind == 'duplicate':
        nodes.append(deepcopy(target))
    elif kind == 'other-document':
        target['document'] = 'different-document'
    elif kind == 'other-context':
        target['context'] = 'different-option'
    else:
        target['path'] = ['99', 'b']
    group = next(g for g in groups if g['contexts'][0]['paragraph_start'] == 17340)
    result = module.resolve(group, nodes)
    assert result['status'] == 'UNRESOLVED' and result['targets'] == []


def test_no_dependency_on_old_reviewed_destinations_or_auxiliary_associations():
    products, old = source_case()
    changed = deepcopy(products)
    changed['P3']['payload']['interpretation_input']['reference_admission']['references'] = []
    altered = deepcopy(old)
    for piece in altered['definition_sources']['source_pieces']:
        piece['assembly_uses'] = []
    assert module.content(changed, altered) == module.content(products, old)


def test_statute_never_uses_equal_contract_section():
    nodes, groups = index_case()
    group = next(g for g in groups if g['contexts'][0]['statute'] == 'SchVG')
    result = module.resolve(group, nodes)
    assert result['status'] == 'EXTERNAL_STATUTE' and result['targets'] == []


def test_unknown_default_remains_unknown():
    nodes, groups = index_case()
    group = next(g for g in groups if g['contexts'][0]['paragraph_start'] == 31593)
    result = module.resolve(group, nodes)
    unknown = next(n for n in result['targets'] if n['path'] == ['1', 'f'])
    assert unknown['heading_role'] == 'UNKNOWN' and unknown['unknown_source_units']
    assert unknown['legal_meaning_established'] is False


@pytest.mark.parametrize('kind', ['raw-hash', 'character-map', 'document'])
def test_current_source_tampering_refused(kind):
    products, old = source_case()
    bad = deepcopy(products)
    unit = next(u for u in bad['P2']['payload']['assembly']['units'] if u['unit'].endswith(':p120:l51'))
    if kind == 'raw-hash':
        unit['original_sha256'] = '0' * 64
    elif kind == 'character-map':
        unit['character_map'][0]['source']['start'] += 1
    else:
        unit['source']['document'] = 'different-document'
    with pytest.raises(ValueError):
        module.source_model(bad, old)
