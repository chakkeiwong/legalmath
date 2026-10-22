"""Preserve the full original structure result and refusal behavior."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from legalmath.prospectus.successor import admissions
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/occurrence-scan-profile-272/pre-edit/src/legalmath/prospectus/successor/admissions.py'
module_spec = importlib.util.spec_from_file_location('legalmath.prospectus.successor.original_layout272', FROZEN)
original = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(original)


def case(version):
    graph = {'units': [{'id': name, 'raw': text, 'visible': True, 'document': 'doc',
        'source_sha256': 'a' * 64, 'page': 1} for name, text in (
            ('governor', 'If applicable'), ('body', 'Payment subject to notice'), ('other', 'Unrelated'))]}
    a, b = [anchor(u) for u in graph['units'][:2]]
    target = b if version == 1 else {'source': b, 'use': {'unit': 'selected', 'start': 0, 'end': len(b['quote'])}}
    packet = {'version': f'prospectus-layout.v{version}', 'graph_sha256': digest(graph), 'documents': [],
        'governing': [{'id': 'condition', 'kind': 'governs', 'from': a, 'to': [target],
            'questions': ['Q1', 'Q2'], 'reason': 'Synthetic explicit complete scope'}],
        'review': {'reviewer': 'equivalence-check', 'kind': 'DEVELOPMENT', 'reason': 'Exact old/new mechanical checks'}}
    return graph, packet


def outcome(function, graph, packet):
    try:
        return ('PASS', function(graph, packet))
    except (ValueError, KeyError, TypeError) as exc:
        return ('REFUSE', type(exc).__name__, str(exc))


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('mutation', ['valid', 'duplicate-source', 'duplicate-unrelated', 'missing',
    'hidden', 'edition', 'quote', 'bool', 'empty', 'negative', 'oversize', 'extra-field',
    'missing-field', 'non-dict', 'non-string-id', 'duplicate-edge', 'wrong-kind', 'question',
    'missing-reason', 'stale-graph'])
def test_complete_frozen_equivalence(version, mutation):
    graph, packet = case(version)
    source = packet['governing'][0]['from']
    if mutation == 'duplicate-source': graph['units'].append(deepcopy(graph['units'][0]))
    elif mutation == 'duplicate-unrelated': graph['units'].append(deepcopy(graph['units'][2]))
    elif mutation == 'missing': source['unit'] = 'absent'
    elif mutation == 'hidden': graph['units'][0]['visible'] = False
    elif mutation == 'edition': source['source_sha256'] = 'wrong'
    elif mutation == 'quote': source['quote'] = 'wrong'
    elif mutation == 'bool': source['start'] = False
    elif mutation == 'empty': source['end'] = 0
    elif mutation == 'negative': source['start'] = -1
    elif mutation == 'oversize': source['end'] = 999
    elif mutation == 'extra-field': source['unexpected'] = True
    elif mutation == 'missing-field': del source['document']
    elif mutation == 'non-dict': packet['governing'][0]['from'] = None
    elif mutation == 'non-string-id': source['unit'] = ['governor']
    elif mutation == 'duplicate-edge': packet['governing'].append(deepcopy(packet['governing'][0]))
    elif mutation == 'wrong-kind': packet['governing'][0]['kind'] = 'reference'
    elif mutation == 'question': packet['governing'][0]['questions'] = ['Q7']
    elif mutation == 'missing-reason': packet['governing'][0]['reason'] = ''
    packet['graph_sha256'] = 'stale' if mutation == 'stale-graph' else digest(graph)
    before = deepcopy((graph, packet))
    assert outcome(admissions.structure, graph, packet) == outcome(original.structure, graph, packet)
    assert (graph, packet) == before


@pytest.mark.parametrize('mutation', ['bool-start', 'empty-range', 'wrong-length', 'missing-use', 'wrong-quote'])
def test_selected_target_refusal_equivalence(mutation):
    graph, packet = case(2)
    target = packet['governing'][0]['to'][0]
    if mutation == 'bool-start': target['use']['start'] = False
    elif mutation == 'empty-range': target['use']['end'] = 0
    elif mutation == 'wrong-length': target['use']['end'] -= 1
    elif mutation == 'missing-use': del target['use']
    elif mutation == 'wrong-quote': target['source']['quote'] = 'wrong'
    want = outcome(original.structure, graph, packet)
    assert want[0] == 'REFUSE'
    assert outcome(admissions.structure, graph, packet) == want


def test_repeated_targets_bind_only_indexed_candidates(monkeypatch):
    graph, packet = case(2)
    graph['units'].extend({**graph['units'][2], 'id': f'extra-{i}'} for i in range(1000))
    packet['graph_sha256'] = digest(graph)
    packet['governing'][0]['to'] *= 80
    expected = original.structure(graph, packet)
    sizes = []
    real_bind = admissions.bind
    def watched(g, source):
        sizes.append(len(g['units']))
        return real_bind(g, source)
    monkeypatch.setattr(admissions, 'bind', watched)
    assert admissions.structure(graph, packet) == expected
    assert len(sizes) == 161 and set(sizes) == {1}
