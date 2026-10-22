"""Frozen016 equivalence for call-scoped validation and real dependency callers."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from legalmath.prospectus.successor import admissions, occurrences, reviewed_references, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, _DependencyLookup

FROZEN = Path(__file__).resolve().parents[2] / (
    'docs/implementation/prospectus-execution-authority/attempts/basf-meanings/'
    'attempt-016/methods/src/legalmath/prospectus/successor')


def frozen(name):
    spec = importlib.util.spec_from_file_location(
        'legalmath.prospectus.successor.frozen016_' + name, FROZEN / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old_occurrences, old_service = frozen('occurrences'), frozen('service')
REVIEW = {'reviewer': 'development-equivalence', 'kind': 'DEVELOPMENT',
          'reason': 'Synthetic exact comparison; not independent legal review'}


def case():
    raw = [{'id': 'raw-' + str(i), 'document': 'doc', 'source_sha256': 'a' * 64,
            'raw': text, 'visible': True, 'page': 1, 'language': 'en'}
           for i, text in enumerate(('Condition 2 applies.', 'Payment definition.', 'Separate caption.'))]
    units = [{'unit': 'use-' + str(i), 'role': 'OPERATIVE', 'text': row['raw'],
              'source': anchor(row), 'questions': ['Q1', 'Q2'], 'character_map': [
                  {'operation': 'Text', 'source': anchor(row), 'start': 0, 'end': len(row['raw'])}]}
             for i, row in enumerate(raw)]
    graph = {'units': raw, 'references': [], 'unresolved': []}
    assembly = {'units': units}
    return graph, assembly


def outcome(function, *args, **kwargs):
    try:
        return 'PASS', function(*args, **kwargs)
    except (ValueError, KeyError, TypeError) as error:
        return 'REFUSE', type(error).__name__, str(error)


USE_CASES = [
    ('valid', 1), ('partial-source', 1), ('legacy', 1), ('legacy-changed', 0),
    ('split', 1), ('split-gap', 0), ('split-overlap', 0), ('output-gap', 0),
    ('output-offset', 1), ('unit-offset-map', 1), ('ast-global-offset', 1), ('ast-multiple-global', None),
    ('duplicate-selected-identity', 2), ('repeated-source', 2), ('duplicate-raw', None),
    ('duplicate-unrelated-raw', None), ('bad-unrelated-map', None),
    ('bad-unrelated-role', 1), ('bad-unrelated-question', 1), ('bad-excluded-map', 1),
    ('bad-unknown-map-outside-scope', 1), ('missing-map-source', None),
    ('hidden-map-source', None), ('empty-unrelated-piece', 1), ('ignored-operation', 1),
    ('wrong-document', None), ('wrong-edition', None), ('wrong-quote', None),
    ('missing-source', None), ('hidden-source', None), ('bool-interval', None),
    ('empty-interval', None), ('negative-interval', None), ('oversize-interval', None),
    ('bool-output', None), ('substituted-map-quote', None),
]


@pytest.mark.parametrize('variant,count', USE_CASES)
def test_complete_uses_equivalence(variant, count):
    graph, assembly = case()
    first, other, _ = assembly['units']
    raw = graph['units'][0]
    source, options = anchor(raw), {'roles': ('OPERATIVE', 'UNKNOWN')}
    length = len(raw['raw'])
    if variant == 'partial-source':
        source = anchor(raw, 2, 12)
    elif variant.startswith('legacy'):
        first['unit'] = raw['id']
        del first['character_map']
        if variant == 'legacy-changed': first['text'] += '!'
    elif variant.startswith('split') or variant in ('output-gap', 'output-offset'):
        intervals = [(0, 5), (5, length)]
        if variant == 'split-gap': intervals = [(0, 5), (6, length)]
        if variant == 'split-overlap': intervals = [(0, 6), (5, length)]
        first['character_map'] = [
            {'operation': 'Field', 'source': anchor(raw, a, b), 'start': a, 'end': b}
            for a, b in intervals]
        if variant == 'output-gap':
            first['text'] = raw['raw'][:5] + ' ' + raw['raw'][5:]
            first['character_map'][1]['start'] += 1
            first['character_map'][1]['end'] += 1
        if variant == 'output-offset':
            first['text'] = 'Prefix ' + raw['raw']
            for piece in first['character_map']:
                piece['start'] += 7
                piece['end'] += 7
    elif variant == 'unit-offset-map':
        first['character_map'] = [{'operation': 'Field', 'unit': raw['id'],
            'source_start': 0, 'source_end': length, 'start': 0, 'end': length}]
    elif variant.startswith('ast-'):
        first['unit'] = 'ast:source-copy'
        if variant == 'ast-multiple-global':
            first['character_map'] = [
                {'operation': 'Text', 'source': anchor(raw, a, b), 'start': a + 41, 'end': b + 41}
                for a, b in [(0, 5), (5, length)]]
        else:
            first['character_map'][0].update(start=41, end=41 + length)
    elif variant in ('duplicate-selected-identity', 'repeated-source'):
        copy = deepcopy(first)
        if variant == 'repeated-source': copy['unit'] = 'another-copy'
        assembly['units'].insert(0, copy)
    elif variant.startswith('duplicate-'):
        graph['units'].append(deepcopy(graph['units'][1 if 'unrelated' in variant else 0]))
    elif variant.startswith('bad-'):
        other['character_map'][0]['end'] -= 1
        if variant == 'bad-unrelated-role': other['role'] = 'HEADER'
        if variant == 'bad-excluded-map': other['role'] = 'EXCLUDED'
        if variant == 'bad-unrelated-question':
            other['questions'], options['question'] = ['Q2'], 'Q1'
        if variant == 'bad-unknown-map-outside-scope':
            other['role'], options['roles'] = 'UNKNOWN', ('OPERATIVE',)
    elif variant == 'missing-map-source': other['character_map'][0]['source']['unit'] = 'absent'
    elif variant == 'hidden-map-source': graph['units'][1]['visible'] = False
    elif variant == 'empty-unrelated-piece':
        other['character_map'][0]['source'].update(start=0, end=0, quote='', source_sha256='wrong')
    elif variant == 'ignored-operation': other['character_map'][0].update(operation='Replacement', end=-1)
    elif variant == 'wrong-document': source['document'] = 'other'
    elif variant == 'wrong-edition': source['source_sha256'] = 'b' * 64
    elif variant == 'wrong-quote': source['quote'] = 'wrong'
    elif variant == 'missing-source': source['unit'] = 'absent'
    elif variant == 'hidden-source': raw['visible'] = False
    elif variant == 'bool-interval': source['start'] = False
    elif variant == 'empty-interval': source.update(end=0, quote='')
    elif variant == 'negative-interval': source['start'] = -1
    elif variant == 'oversize-interval': source['end'] = length + 1
    elif variant == 'bool-output': first['character_map'][0]['start'] = False
    elif variant == 'substituted-map-quote': first['character_map'][0]['source']['quote'] = 'wrong'
    snapshot = deepcopy((graph, assembly, source))
    expected = outcome(old_occurrences.uses, graph, assembly, source, **options)
    actual = outcome(_DependencyLookup(graph, assembly).uses, graph, assembly, source, **options)
    assert actual == expected
    if count is None:
        assert actual[0] == 'REFUSE'
    else:
        assert actual[0] == 'PASS' and len(actual[1]) == count
    assert (graph, assembly, source) == snapshot


@pytest.mark.parametrize('roles,question', [
    (('OPERATIVE',), None), (('OPERATIVE', 'UNKNOWN'), None),
    (('OPERATIVE',), 'Q1'), (('OPERATIVE',), 'Q2'), (('UNKNOWN',), 'Q2'), ((), 'Q1')])
def test_role_question_and_assembly_order(roles, question):
    graph, assembly = case()
    first = assembly['units'][0]
    assembly['units'] = [
        {**deepcopy(first), 'unit': 'unknown-copy', 'role': 'UNKNOWN', 'questions': ['Q2']},
        {**deepcopy(first), 'unit': 'q1-copy', 'questions': ['Q1']},
        {**deepcopy(first), 'unit': 'q2-copy', 'questions': ['Q2']}, first]
    source = anchor(graph['units'][0])
    expected = old_occurrences.uses(graph, assembly, source, roles=roles, question=question)
    assert _DependencyLookup(graph, assembly).uses(graph, assembly, source, roles=roles, question=question) == expected


@pytest.mark.parametrize('variant,refused', [
    ('raw-name', False), ('selected-name', False), ('explicit', False),
    ('ambiguous-raw', True), ('explicit-copy', False), ('duplicate-identity', True),
    ('bad-unrelated-map', True), ('unknown-target', False), ('excluded-target', True),
    ('wrong-use', True), ('missing-target', True), ('split-selected-name', True)])
def test_exact_target_equivalence(variant, refused):
    graph, assembly = case()
    first = assembly['units'][0]
    source = anchor(graph['units'][0])
    value = {'source': source, 'use': first['unit']}
    if variant == 'raw-name': value = source['unit']
    if variant in ('selected-name', 'split-selected-name'): value = first['unit']
    if variant in ('ambiguous-raw', 'explicit-copy', 'duplicate-identity'):
        copy = deepcopy(first)
        if variant != 'duplicate-identity': copy['unit'] = 'another-copy'
        assembly['units'].append(copy)
        if variant == 'ambiguous-raw': value = source['unit']
    if variant == 'bad-unrelated-map': assembly['units'][1]['character_map'][0]['end'] -= 1
    if variant == 'unknown-target': first['role'] = 'UNKNOWN'
    if variant == 'excluded-target': first['role'] = 'EXCLUDED'
    if variant == 'wrong-use': value['use'] = 'absent'
    if variant == 'missing-target': value = 'absent'
    if variant == 'split-selected-name':
        first['character_map'] = [
            {'operation': 'Text', 'source': anchor(graph['units'][0], a, b), 'start': a, 'end': b}
            for a, b in [(0, 5), (5, len(first['text']))]]
    expected = outcome(old_occurrences.target, graph, assembly, value)
    actual = outcome(occurrences.target, graph, assembly, value, _lookup=_DependencyLookup(graph, assembly))
    assert actual == expected and (actual[0] == 'REFUSE') == refused


def dependency_case():
    graph, assembly = case()
    source = anchor(graph['units'][0], 0, 11)
    graph['references'] = [{'id': 'reference-1', **source, 'text': source['quote']}]
    request = {'bundle': {'dependencies': []}}
    return request, graph, assembly


def reviewed_packet(graph, assembly):
    a, b = [anchor(u) for u in graph['units'][:2]]
    return {'version': 'reviewed-references.v2', 'assembly_sha256': digest(assembly), 'review': REVIEW,
        'references': [{'id': 'reviewed-1', 'form': 'named', 'source': a, 'from_use': 'use-0',
            'language': 'en', 'targets': [{'source': b, 'use': 'use-1', 'language': 'en'}],
            'authority': deepcopy(a), 'questions': ['Q1'], 'reason': 'Exact synthetic target',
            'discovery_ids': ['reference-1']}]}


@pytest.mark.parametrize('variant,refused', [
    ('unresolved', False), ('discovered-target', False), ('reviewed', False),
    ('reviewed-both-questions', False), ('governing', False), ('governing-admission', False),
    ('governing-and-reviewed', False), ('bad-unrelated-map', True), ('bad-header-map', False),
    ('ambiguous-target', True), ('wrong-target-edition', True), ('wrong-language', True),
    ('wrong-target-question', True), ('bad-authority', True), ('stale-review', True),
    ('duplicate-raw', True), ('duplicate-selected-target', True), ('unavailable-reference', False),
    ('explicit-unavailable-reference', True), ('invalid-split', False)])
def test_frozen_complete_dependency_equivalence(variant, refused):
    request, graph, assembly = dependency_case()
    a, b = [anchor(u) for u in graph['units'][:2]]
    if variant not in ('unresolved', 'unavailable-reference', 'explicit-unavailable-reference', 'invalid-split'):
        request['reference_dispositions'] = {'reference-1': {
            'source_sha256': a['source_sha256'], 'reason': 'Synthetic exact target', 'targets': [b['unit']]}}
    if variant in ('reviewed', 'reviewed-both-questions', 'governing-and-reviewed',
                   'wrong-language', 'wrong-target-question', 'bad-authority', 'stale-review'):
        request['reference_admission'] = reviewed_packet(graph, assembly)
        row = request['reference_admission']['references'][0]
        if variant == 'reviewed-both-questions': row['questions'] = ['Q1', 'Q2']
        if variant == 'wrong-language': row['language'] = 'de'
        if variant == 'wrong-target-question': assembly['units'][1]['questions'] = ['Q2']
        if variant == 'bad-authority': row['authority']['quote'] = 'wrong'
        if variant == 'stale-review': request['reference_admission']['assembly_sha256'] = '0' * 64
    if variant in ('governing', 'governing-admission', 'governing-and-reviewed'):
        edge = {'id': 'scope-1', 'kind': 'governs', 'from': b, 'to': [a, a],
                'questions': ['Q1', 'Q2'], 'reason': 'Synthetic governing relationship'}
        if variant == 'governing-admission':
            edge['to'] = [{'source': a, 'use': {'unit': 'use-0', 'start': 0, 'end': len(a['quote'])}}]
            request['governing_admission'] = {'version': 'prospectus-layout.v2',
                'graph_sha256': digest(graph), 'documents': [], 'governing': [edge], 'review': REVIEW}
        else:
            graph['layout'] = {'version': 'admitted-layout.v1', 'governing': [edge]}
    if variant in ('bad-unrelated-map', 'bad-header-map'):
        assembly['units'][2]['character_map'][0]['end'] -= 1
        if variant == 'bad-header-map': assembly['units'][2]['role'] = 'HEADER'
    if variant in ('ambiguous-target', 'duplicate-selected-target'):
        copy = deepcopy(assembly['units'][1])
        if variant == 'ambiguous-target': copy['unit'] = 'another-target'
        assembly['units'].append(copy)
    if variant == 'wrong-target-edition':
        request['reference_dispositions']['reference-1']['targets'] = [
            {'source': {**b, 'source_sha256': 'wrong'}, 'use': 'use-1'}]
    if variant == 'duplicate-raw': graph['units'].append(deepcopy(graph['units'][2]))
    if variant in ('unavailable-reference', 'explicit-unavailable-reference'):
        graph['units'][0]['visible'] = False
        assembly['units'].pop(0)
        if variant == 'explicit-unavailable-reference':
            request['reference_dispositions'] = {'reference-1': {'reason': 'Must still refuse'}}
    if variant == 'invalid-split':
        first = assembly['units'][0]
        first['character_map'] = [
            {'operation': 'Text', 'source': anchor(graph['units'][0], x, y), 'start': x, 'end': y}
            for x, y in [(0, 4), (5, len(first['text']))]]
    # Keep test-specific packet hashes current except the deliberate stale case.
    if 'reference_admission' in request and variant != 'stale-review':
        request['reference_admission']['assembly_sha256'] = digest(assembly)
    snapshot = deepcopy((request, graph, assembly))
    expected = outcome(old_service.dependencies, request, graph, assembly)
    actual = outcome(service.dependencies, request, graph, assembly)
    assert actual == expected and (actual[0] == 'REFUSE') == refused
    assert (request, graph, assembly) == snapshot


def test_validation_is_shared_without_dropping_scope(monkeypatch):
    graph, assembly = case()
    assembly['units'][1]['role'] = 'UNKNOWN'
    assembly['units'][2]['role'] = 'HEADER'
    assembly['units'][2]['character_map'][0]['end'] -= 1
    queries = [(anchor(graph['units'][0]), ('OPERATIVE',), 'Q1'),
               (anchor(graph['units'][1]), ('OPERATIVE', 'UNKNOWN'), None),
               (anchor(graph['units'][0], 2, 12), ('OPERATIVE',), 'Q2')]
    expected = [old_occurrences.uses(graph, assembly, s, roles=r, question=q) for s, r, q in queries]
    called, original = [], occurrences.segments
    def counted(g, u, **kwargs):
        called.append(u['unit'])
        return original(g, u, **kwargs)
    monkeypatch.setattr(occurrences, 'segments', counted)
    lookup = _DependencyLookup(graph, assembly)
    assert [lookup.uses(graph, assembly, s, roles=r, question=q) for s, r, q in queries] == expected
    assert called == ['use-0', 'use-1']
    with pytest.raises(ValueError, match='differs from source'):
        lookup.uses(graph, assembly, queries[0][0], roles=('HEADER',))


@pytest.mark.parametrize('change', ['source-row', 'selected-map', 'selected-role'])
def test_no_cache_survives_separate_dependency_calls(change):
    request, graph, assembly = dependency_case()
    assert service.dependencies(request, graph, assembly) == old_service.dependencies(request, graph, assembly)
    if change == 'source-row': graph['units'][1]['raw'] = 'Changed source text.'
    if change == 'selected-map': assembly['units'][1]['character_map'][0]['end'] -= 1
    if change == 'selected-role': assembly['units'][0]['role'] = 'HEADER'
    actual = outcome(service.dependencies, request, graph, assembly)
    assert actual == outcome(old_service.dependencies, request, graph, assembly)
    assert actual[0] == ('PASS' if change == 'selected-role' else 'REFUSE')


@pytest.mark.parametrize('change', ['source-list', 'assembly-object', 'assembly-list'])
def test_existing_lookup_rejects_substituted_context(change):
    graph, assembly = case()
    lookup, source = _DependencyLookup(graph, assembly), anchor(graph['units'][0])
    lookup.uses(graph, assembly, source)
    if change == 'source-list': graph = {**graph, 'units': deepcopy(graph['units'])}
    if change == 'assembly-object': assembly = {**assembly}
    if change == 'assembly-list': assembly['units'] = deepcopy(assembly['units'])
    with pytest.raises(ValueError, match='another source/assembly context'):
        lookup.uses(graph, assembly, source)
    with pytest.raises(ValueError, match='another source/assembly context'):
        occurrences.target(graph, assembly, source['unit'], _lookup=lookup)


def test_layout_copy_and_optional_caller_defaults():
    request, graph, assembly = dependency_case()
    graph['layout'] = {'version': 'admitted-layout.v1', 'governing': [{
        'id': 'governed', 'from': anchor(graph['units'][1]), 'to': [anchor(graph['units'][0])],
        'questions': ['Q1', 'Q2']}]}
    lookup = _DependencyLookup(graph, assembly)
    copy = {**graph, 'layout': deepcopy(graph['layout'])}
    assert admissions.governing_dependencies(copy, assembly, _lookup=lookup) == admissions.governing_dependencies(graph, assembly)
    packet = reviewed_packet(graph, assembly)
    assert reviewed_references.admit(graph, assembly, packet, _lookup=lookup) == reviewed_references.admit(graph, assembly, packet)
