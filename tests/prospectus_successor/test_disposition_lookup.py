"""Exact outputs/refusals against the frozen pre-optimization validator."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from legalmath.prospectus.successor.admissions import dispositions
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

FROZEN = Path(__file__).resolve().parents[2] / (
    'docs/implementation/prospectus-execution-authority/attempts/basf-meanings/'
    'attempt-015/methods/src/legalmath/prospectus/successor/admissions.py')
spec = importlib.util.spec_from_file_location(
    'legalmath.prospectus.successor.frozen015_admissions', FROZEN)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def case():
    raw = [{'id': 'raw-' + k, 'document': 'doc', 'source_sha256': 'a' * 64,
            'raw': text, 'visible': True, 'page': 1}
           for k, text in [('a', 'Initially appointed'), ('b', 'Separate caption')]]
    units = [{'unit': 'use-' + str(i), 'role': 'UNKNOWN', 'text': row['raw'],
              'questions': ['Q1', 'Q2'], 'character_map': [
                  {'operation': 'Text', 'source': anchor(row), 'start': 0, 'end': len(row['raw'])}]}
             for i, row in enumerate(raw)]
    assembly = {'version': 'assembled-contract.v2', 'units': units,
                'continuous_text': '\n'.join(u['text'] for u in units),
                'unresolved': [u['unit'] for u in units], 'status': 'PARTIAL'}
    admission = {'version': 'reviewed-dispositions.v1', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'development-equivalence', 'kind': 'DEVELOPMENT',
                   'reason': 'Synthetic comparison with frozen015'},
        'units': [{'unit': units[0]['unit'], 'text_sha256': digest(units[0]['text'].encode()),
                   'role': 'OPERATIVE', 'reason': 'Complete supplied source', 'sources': [anchor(raw[0])]}]}
    return {'units': raw}, assembly, admission


@pytest.mark.parametrize('variant,rejected', [
    ('valid', False), ('repeated-raw-use', False), ('split-map', False),
    ('two-reviewed-roles', False), ('missing-coverage', True), ('wrong-quote', True),
    ('malformed-other-map', True), ('malformed-other-role', False),
    ('duplicate-target', True), ('duplicate-raw', True), ('excluded', True),
])
def test_complete_disposition_equivalence(variant, rejected):
    graph, assembly, admission = case()
    first, other = assembly['units']
    if variant == 'repeated-raw-use':
        assembly['units'].append({**deepcopy(first), 'unit': 'another-use'})
    elif variant == 'split-map':
        raw = graph['units'][0]
        first['character_map'] = [
            {'operation': 'Text', 'source': anchor(raw, a, b), 'start': a, 'end': b}
            for a, b in [(0, 9), (9, len(raw['raw']))]]
    elif variant == 'two-reviewed-roles':
        admission['units'].append({'unit': other['unit'], 'text_sha256': digest(other['text'].encode()),
            'role': 'HEADER', 'reason': 'Retain original lookup role', 'sources': [anchor(graph['units'][1])]})
    elif variant == 'missing-coverage':
        admission['units'][0]['sources'] = [anchor(graph['units'][0], 0, 9)]
    elif variant == 'wrong-quote':
        admission['units'][0]['sources'][0]['quote'] = 'Wrong quote'
    elif variant.startswith('malformed-other'):
        other['character_map'][0]['end'] -= 1
        if variant == 'malformed-other-role':
            other['role'] = 'HEADER'
    elif variant == 'duplicate-target':
        assembly['units'].append(deepcopy(first))
    elif variant == 'duplicate-raw':
        graph['units'].append(deepcopy(graph['units'][0]))
    elif variant == 'excluded':
        first['role'] = 'EXCLUDED'
    assembly['continuous_text'] = '\n'.join(u['text'] for u in assembly['units']
        if u['role'] in {'OPERATIVE', 'UNKNOWN'})
    admission['assembly_sha256'] = digest(assembly)
    snapshot = deepcopy((graph, assembly, admission))
    if rejected:
        for function in (old.dispositions, dispositions):
            with pytest.raises(ValueError):
                function(graph, assembly, admission)
    else:
        assert dispositions(graph, assembly, admission) == old.dispositions(graph, assembly, admission)
    assert (graph, assembly, admission) == snapshot
