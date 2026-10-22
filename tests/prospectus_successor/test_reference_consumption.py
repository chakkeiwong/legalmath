"""Frozen-method equivalence, refusal preservation and fresh-call validation."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from legalmath.prospectus.successor import reviewed_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_reference_consumption_compare import FAMILIES, load_before, old_families

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/reference-consumption-repair-372'


def semantic_for(graph, assembly, packet):
    old = load_before(PREP, 'reviewed_references')
    dependencies = old.admit(graph, assembly, packet)[0] if packet is not None else []
    for name in FAMILIES:
        module = load_before(PREP, 'basf_' + name + '_references')
        dependencies += module.missing_dependencies(module.check(graph, assembly, packet))
    questions = {}
    for q in ('Q1', 'Q2'):
        unresolved = [d['id'] for d in dependencies if d['status'] == 'UNRESOLVED' and q in d['questions']]
        refs = [key for key in unresolved if key.startswith('reviewed-reference:')]
        if refs and packet['version'] in ('reviewed-references.v3', 'reviewed-references.v4'):
            dependencies.append({'id': 'reference-closure:' + q, 'questions': [q], 'status': 'UNRESOLVED',
                'unresolved': ['Unresolved reference: ' + key for key in refs]})
            unresolved.append('reference-closure:' + q)
        questions[q] = {'unresolved': unresolved.copy(), 'subquestions': {'payment': {'unresolved': unresolved.copy()}}}
    return {'dependencies': dependencies, 'questions': questions}


def synthetic():
    raw = [{'id': str(i), 'document': 'synthetic', 'source_sha256': 'a' * 64, 'raw': text,
            'visible': True, 'page': 1, 'language': 'en'}
           for i, text in enumerate(('See payment.', 'Pay principal.', 'Separate operative clause.'))]
    graph = {'units': raw, 'references': []}
    assembly = {'units': [{'unit': u['id'], 'role': 'OPERATIVE', 'text': u['raw'], 'source': anchor(u),
        'questions': ['Q1', 'Q2'], 'character_map': [
            {'operation': 'Text', 'source': anchor(u), 'start': 0, 'end': len(u['raw'])}]} for u in raw]}
    packet = {'version': 'reviewed-references.v3', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'test', 'kind': 'DEVELOPMENT', 'reason': 'Synthetic validation only'},
        'references': [{'id': 'link', 'form': 'named', 'source': anchor(raw[0]), 'from_use': '0',
            'language': 'en', 'targets': [{'source': anchor(raw[1]), 'use': '1', 'language': 'en'}],
            'authority': anchor(raw[0]), 'questions': ['Q1', 'Q2'], 'reason': 'Exact synthetic target',
            'discovery_ids': []}]}
    return graph, assembly, {'reference_admission': packet}, semantic_for(graph, assembly, packet)


def outcome(function, *args):
    try: return ('PASS', function(*args))
    except (ValueError, KeyError, TypeError) as error: return ('REFUSE', type(error).__name__)


def compare(case, refused=False):
    original = deepcopy(case)
    expected = outcome(lambda *args: old_families(PREP, *args), *case)
    actual = outcome(core.verify_consumed_families, *case)
    assert actual == expected
    assert (actual[0] == 'REFUSE') == refused
    assert case == original
    return actual


@pytest.mark.parametrize('kind', ('valid', 'unknown', 'empty', 'absent'))
def test_generic_reports_and_uncertainty_match_frozen(kind):
    graph, assembly, request, semantic = synthetic()
    packet = request['reference_admission']
    if kind == 'unknown': assembly['units'][1]['role'] = 'UNKNOWN'
    if kind == 'empty': packet['references'] = []
    packet['assembly_sha256'] = digest(assembly)
    if kind == 'absent': request = {}; packet = None
    semantic = semantic_for(graph, assembly, packet)
    compare((graph, assembly, request, semantic))


@pytest.mark.parametrize('kind', ('bad-unrelated-map', 'wrong-source', 'wrong-edition', 'duplicate-row',
    'duplicate-raw', 'wrong-assembly', 'drop-dependency', 'alter-dependency', 'invent-dependency',
    'hide-unknown', 'hide-subquestion', 'hide-closure', 'wrong-target'))
def test_malformed_inputs_and_forged_dependencies_match_frozen(kind):
    graph, assembly, request, semantic = synthetic(); packet = request['reference_admission']
    if kind.startswith('hide'):
        assembly['units'][1]['role'] = 'UNKNOWN'; packet['assembly_sha256'] = digest(assembly)
        semantic = semantic_for(graph, assembly, packet)
    if kind == 'bad-unrelated-map':
        assembly['units'][2]['character_map'][0]['end'] -= 1; packet['assembly_sha256'] = digest(assembly)
    elif kind == 'wrong-source': packet['references'][0]['source']['quote'] = 'Changed'
    elif kind == 'wrong-edition': graph['units'][1]['source_sha256'] = 'b' * 64
    elif kind == 'duplicate-row': packet['references'].append(deepcopy(packet['references'][0]))
    elif kind == 'duplicate-raw': graph['units'].append(deepcopy(graph['units'][2]))
    elif kind == 'wrong-assembly': assembly['units'][1]['text'] += ' Changed'
    elif kind == 'drop-dependency': semantic['dependencies'].pop(0)
    elif kind == 'alter-dependency': semantic['dependencies'][0]['targets'].pop()
    elif kind == 'invent-dependency': semantic['dependencies'].append(deepcopy(semantic['dependencies'][0]))
    elif kind == 'hide-unknown': semantic['questions']['Q1']['unresolved'].remove('reviewed-reference:link')
    elif kind == 'hide-subquestion': semantic['questions']['Q2']['subquestions']['payment']['unresolved'] = []
    elif kind == 'hide-closure': semantic['dependencies'] = [d for d in semantic['dependencies'] if d['id'] != 'reference-closure:Q1']
    else: packet['references'][0]['targets'][0]['use'] = '2'
    compare((graph, assembly, request, semantic), refused=True)


@pytest.mark.parametrize('kind', ('source', 'selection', 'packet', 'semantic'))
def test_later_calls_do_not_reuse_mutated_inputs(kind):
    case = synthetic(); compare(case)
    graph, assembly, request, semantic = case
    if kind == 'source': graph['units'][1]['raw'] = 'Changed'
    elif kind == 'selection': assembly['units'][2]['character_map'][0]['end'] -= 1
    elif kind == 'packet': request['reference_admission']['references'][0]['authority']['quote'] = 'Changed'
    else: semantic['dependencies'].pop()
    compare(case, refused=True)


@pytest.fixture(scope='module')
def basf():
    donor = AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz'
    products = json.loads(gzip.decompress(donor.read_bytes()))
    graph, assembly = products['P1']['payload']['graph'], products['P2']['payload']['assembly']
    specifications = [load_before(PREP, 'basf_' + n + '_references').specification() for n in FAMILIES]
    rows = [deepcopy(row) for spec in specifications for row in spec['references']]
    ids = {row['source']['unit'] for row in rows} | {t['source']['unit'] for row in rows for t in row['targets']}
    def retain_identities(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('unit', 'use', 'from_use') and isinstance(child, str): ids.add(child)
                retain_identities(child)
        elif isinstance(value, list):
            for child in value: retain_identities(child)
    for spec in specifications:
        retain_identities(spec)
        ids.update(next(u['id'] for u in graph['units'] if u['document'] == source['id'])
                   for source in spec['sources'])
    ids.add(next(u['id'] for u in graph['units'] if u['document'] == 'basf-2032-final'))
    selected_ids = {row['from_use'] for row in rows} | {t['use'] for row in rows for t in row['targets']} | ids
    selected = [u for u in assembly['units'] if u['unit'] in selected_ids]
    ids.update(m['source']['unit'] for u in selected for m in (u.get('character_map') or []))
    graph = {**graph, 'units': [u for u in graph['units'] if u['id'] in ids],
             'references': [r for r in graph['references'] if r['unit'] in ids]}
    assembly = {**assembly, 'units': selected}
    packet = {'version': 'reviewed-references.v3', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'test', 'kind': 'DEVELOPMENT', 'reason': 'Retained family source comparison'},
        'references': rows}
    return graph, assembly, packet


@pytest.mark.parametrize('kind', ('complete', 'one-family-omitted', 'all-omitted'))
def test_all_family_reports_match_frozen(basf, kind):
    graph, assembly, packet = deepcopy(basf)
    if kind == 'one-family-omitted':
        ids = {r['id'] for r in load_before(PREP, 'basf_default_references').specification()['references']}
        packet['references'] = [r for r in packet['references'] if r['id'] not in ids]
    elif kind == 'all-omitted': packet['references'] = []
    semantic = semantic_for(graph, assembly, packet)
    compare((graph, assembly, {'reference_admission': packet}, semantic))


def test_one_full_admission_preserves_all_family_source_checks(basf):
    graph, assembly, packet = deepcopy(basf)
    semantic = semantic_for(graph, assembly, packet); request = {'reference_admission': packet}
    expected = old_families(PREP, graph, assembly, request, semantic)
    from contextlib import ExitStack
    import importlib
    with ExitStack() as stack:
        admission = stack.enter_context(patch.object(core, 'admit', wraps=core.admit))
        checks = []
        for name in FAMILIES:
            module = importlib.import_module('legalmath.prospectus.successor.basf_' + name + '_references')
            checks.append(stack.enter_context(patch.object(module, 'check', wraps=module.check)))
        actual = core.verify_consumed_families(graph, assembly, request, semantic)
        assert actual == expected and admission.call_count == 1
        assert all(check.call_count == 2 for check in checks)


@pytest.mark.parametrize('family', FAMILIES)
def test_each_family_still_refuses_altered_dependencies(basf, family):
    graph, assembly, packet = deepcopy(basf)
    semantic = semantic_for(graph, assembly, packet)
    row = load_before(PREP, 'basf_' + family + '_references').specification()['references'][0]
    dependency = next(d for d in semantic['dependencies'] if d['id'] == 'reviewed-reference:' + row['id'])
    dependency['targets'] = []
    compare((graph, assembly, {'reference_admission': packet}, semantic), refused=True)


def test_public_review_verifier_keeps_return_contract():
    assert core.verify_consumed(*synthetic()) is None
