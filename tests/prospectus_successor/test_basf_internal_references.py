from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest
from legalmath.prospectus.successor import basf_internal_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reviewed_references import admit

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
KEY = 'basf-base-september-2022-exchange'


@pytest.fixture(scope='module')
def original():
    p = json.loads(gzip.decompress((AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz').read_bytes()))
    packet = json.loads((AUTH / 'reviews/internal-closure-279/packet.json').read_text())
    spec = core.specification()
    ids = {r['source']['unit'] for r in spec['references']} | {r['unit'] for r in spec['contexts']}
    for rows in spec['selection'].values():
        for r in rows:
            ids.add(r['use'])
            ids |= {m['source']['unit'] for m in r['segments']}
    for name in ('call', 'payment', 'legacy', 'governance', 'default', 'substitution', 'financial'):
        other = json.loads((ROOT / ('src/legalmath/prospectus/successor/basf_' + name + '_references_spec.json')).read_text())
        ids |= {r['source']['unit'] for r in other['references']}
        ids |= {r['unit'] for r in other.get('contexts', []) + other.get('split_contexts', [])}
    graph = p['P1']['payload']['graph']
    # Keep each original edition represented when reducing the unit inventory.
    ids |= {next(u['id'] for u in graph['units'] if u['document'] == s['id'])
            for s in spec['sources']}
    raw_ids = ids | {m['source']['unit'] for u in p['P2']['payload']['assembly']['units']
                     if u['unit'] in ids for m in (u.get('character_map') or [])}
    graph = {**graph, 'units': [u for u in graph['units'] if u['id'] in raw_ids],
             'references': [r for r in graph['references'] if r['unit'] in ids]}
    assembly = p['P2']['payload']['assembly']
    assembly = {**assembly, 'units': [u for u in assembly['units'] if u['unit'] in ids]}
    packet['assembly_sha256'] = digest(assembly)
    return graph, assembly, packet


def test_complete_internal_scopes_keep_exceptions_cross_page_endings_and_unknowns(original):
    graph, assembly, packet = original
    deps, edges = admit(graph, assembly, packet)
    assert [len(d['targets']) for d in deps] == [23, 43, 43, 32, 66, 32, 46, 41, 2, 30]
    assert len(edges) == 358
    assert [d['status'] for d in deps] == [
        'RESOLVED', 'UNRESOLVED', 'UNRESOLVED', *(['RESOLVED'] * 7)]
    assert deps[1]['unknown_target_uses'] == [KEY + ':p125:l1', KEY + ':p125:l2']
    assert any(t['source']['unit'] == KEY + ':p119:l81' for t in deps[4]['targets'])
    assert any(t['source']['unit'] == KEY + ':p120:l8' for t in deps[4]['targets'])
    tax = ' '.join(t['source']['quote'] for t in deps[1]['targets'])
    assert all(x in tax for x in ('(a)', '(b)', '(c)', '(d)', '(e)', 'Solidaritätszuschlag'))
    report = core.check(graph, assembly, packet)
    assert report['conservative_cycle_policy'] and not report['automatic_discovery']
    assert report['actual_tax_and_event_application'] == 'UNKNOWN'


@pytest.mark.parametrize('index', range(10))
def test_every_internal_target_requires_full_scope(original, index):
    graph, assembly, packet = deepcopy(original)
    packet['references'][index]['targets'] = packet['references'][index]['targets'][-1:]
    with pytest.raises(ValueError, match='exact complete selected target'):
        admit(graph, assembly, packet)


@pytest.mark.parametrize('case', ['finance-tax', 'finance-substitution', 'promote-tax-heading',
    'selected-text', 'character-map', 'question', 'edition', 'source-context', 'definition-continuation',
    'language', 'discovery', 'rename', 'duplicate', 'reason', 'drop-exception', 'drop-proof-ending'])
def test_issuer_source_language_discovery_and_provenance_controls(original, case):
    graph, assembly, packet = deepcopy(original)
    units = {u['unit']: u for u in assembly['units']}
    row = packet['references'][0]
    if case == 'finance-tax':
        units[KEY + ':p119:l1']['role'] = 'OPERATIVE'
    elif case == 'finance-substitution':
        units[KEY + ':p128:l69']['role'] = 'OPERATIVE'
    elif case == 'promote-tax-heading':
        units[KEY + ':p125:l1']['role'] = 'OPERATIVE'
    elif case == 'selected-text':
        units[KEY + ':p125:l50']['text'] = 'no exception'
    elif case == 'character-map':
        units[KEY + ':p120:l8']['character_map'][0]['source']['end'] -= 1
    elif case == 'question':
        row['questions'] = ['Q1']
    elif case == 'edition':
        row['source']['source_sha256'] = '0' * 64
    elif case in ('source-context', 'definition-continuation'):
        suffix = ':p123:l36' if case == 'source-context' else ':p128:l59'
        next(u for u in graph['units'] if u['id'].endswith(suffix))['raw'] = 'altered original'
    elif case == 'language':
        row['targets'][0]['language'] = 'en'
    elif case == 'discovery':
        row['discovery_ids'] = packet['references'][1]['discovery_ids']
    elif case == 'rename':
        row['id'] = 'hidden'
    elif case == 'duplicate':
        packet['references'].append(deepcopy(row))
    elif case == 'reason':
        row['reason'] = ' '
    elif case == 'drop-exception':
        packet['references'][1]['targets'] = packet['references'][1]['targets'][:-4]
    else:
        packet['references'][-1]['targets'].pop()
    packet['assembly_sha256'] = digest(assembly)
    with pytest.raises(ValueError):
        admit(graph, assembly, packet)


def test_all_omitted_links_remain_uncertain_in_every_answer(original):
    graph, assembly, packet = original
    packet = {**packet, 'references': []}
    deps = core.missing_dependencies(core.check(graph, assembly, packet))
    missing = [d['id'] for d in deps]
    assert len(missing) == 10
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': missing.copy(),
        'subquestions': {'a': {'unresolved': missing.copy()}}} for q in ('Q1', 'Q2')}}
    core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
    semantic['questions']['Q2']['subquestions']['a']['unresolved'].pop()
    with pytest.raises(ValueError, match='hides or invents'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
