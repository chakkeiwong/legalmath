"""Reviewed governing scope composes with already bound source/construction."""
from copy import deepcopy

import pytest

from test_closure_consumers import pdf_fixture
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest


def test_governing_scope_preserves_parents_and_missing_target_changes_answer(tmp_path):
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    original = deepcopy((p1, p2))
    p3 = service.interpretation_product(p1, p2, {'governing_admission': admission})
    assert (p1, p2) == original
    assert digest(p1['payload']['graph']) == admission['graph_sha256']
    assert p3['payload']['questions']['Q1']['status'] == 'NO'
    assert p3['payload']['governing_admission_sha256'] == digest(admission)
    p4, p5 = service.law_product(p1, p3), service.financial_product(p1, p2, p3)
    report = service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), tmp_path)
    assert report['mode'] == 'ASSISTED'
    assert report['questions']['Q1']['status'] == 'NO'
    req['governing_admission'] = admission
    req['assembly']['operations'][1]['role'] = 'EXCLUDED'
    missing = service.assess(req, tmp_path)
    assert missing['questions']['Q1']['status'] == 'UNKNOWN'
    assert 'governing:margin:Q1' in missing['questions']['Q1']['unresolved']
    assert missing['mode'] == 'ASSISTED'


@pytest.mark.parametrize('mutation', ['graph', 'source', 'target', 'duplicate'])
def test_governing_interpretation_rejects_invalid_binding(tmp_path, mutation):
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    if mutation == 'graph':
        admission['graph_sha256'] = '0' * 64
    elif mutation == 'source':
        admission['governing'][0]['from']['quote'] = 'invented'
    elif mutation == 'target':
        admission['governing'][0]['to'][0]['source_sha256'] = '0' * 64
    else:
        admission['governing'].append(deepcopy(admission['governing'][0]))
    req['governing_admission'] = admission
    with pytest.raises(ValueError):
        service.assess(req, tmp_path)


def test_existing_layout_and_later_governing_cannot_repeat_identity(tmp_path):
    req = pdf_fixture(tmp_path)
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    admission = deepcopy(req['layout_admission'])
    admission['graph_sha256'] = digest(p1['payload']['graph'])
    with pytest.raises(ValueError, match='Duplicate governing relationship'):
        service.interpretation_product(p1, p2, {'governing_admission': admission})


@pytest.mark.parametrize('variant', ['complete', 'excluded', 'ambiguous', 'question'])
def test_repeated_complete_scope_matches_uncached_occurrence_resolution(tmp_path, monkeypatch, variant):
    from legalmath.prospectus.successor import admissions
    from legalmath.prospectus.successor.occurrences import uses
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    graph = deepcopy(p1['payload']['graph'])
    assembly = deepcopy(p2['payload']['assembly'])
    edge = deepcopy(admission['governing'][0])
    edge['questions'] = ['Q1', 'Q2']
    selected_id = uses(graph, assembly, edge['to'][0], question='Q1')[0]['unit']
    selected = next(u for u in assembly['units'] if u['unit'] == selected_id)
    if variant == 'excluded':
        selected['role'] = 'EXCLUDED'
    elif variant == 'ambiguous':
        duplicate = deepcopy(selected)
        duplicate['unit'] += ':duplicate'
        assembly['units'].append(duplicate)
    elif variant == 'question':
        selected['questions'] = ['Q1']
    graph['layout'] = {'governing': [{**deepcopy(edge), 'id': f'line-{i}'} for i in range(12)]}
    expected = []
    for item in graph['layout']['governing']:
        for question in item['questions']:
            mappings = [uses(graph, assembly, source, question=question) for source in item['to']]
            expected.append({'id': 'governing:' + item['id'] + ':' + question,
                'questions': [question], 'status': 'RESOLVED' if all(len(m) == 1 for m in mappings) else 'UNRESOLVED',
                'authority': item['from'], 'target_uses': mappings,
                'reason': 'Every source-reviewed governed occurrence must survive in the selected question'})
    calls = []
    def counted(*args, **kwargs):
        calls.append((digest(args[2]), kwargs['question']))
        return uses(*args, **kwargs)
    monkeypatch.setattr(admissions, 'uses', counted)
    actual = admissions.governing_dependencies(graph, assembly)
    assert actual == expected
    assert len(calls) == len(set(calls)) == 2 * len({digest(s) for s in edge['to']})
    # Repeated dependency rows must not share mutable mapping output.
    actual[0]['target_uses'][0].append({'changed': True})
    assert actual[2] == expected[2]
    # A changed assembly is re-evaluated in a separate call.
    assembly['units'] = [u for u in assembly['units'] if u['unit'] != selected_id + ':duplicate']
    selected['role'] = 'EXCLUDED'
    again = admissions.governing_dependencies(graph, assembly)
    assert len(calls) == 2 * len(set(calls))
    assert all(row['status'] == 'UNRESOLVED' for row in again)


def test_repeated_scope_does_not_hide_changed_source_anchor(tmp_path):
    from legalmath.prospectus.successor import admissions
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    edges = [deepcopy(admission['governing'][0]) for _ in range(2)]
    edges[1]['id'] = 'changed-anchor'
    edges[1]['to'][0]['quote'] = 'invented'
    graph = {**p1['payload']['graph'], 'layout': {'governing': edges}}
    with pytest.raises(ValueError):
        admissions.governing_dependencies(graph, p2['payload']['assembly'])


@pytest.mark.parametrize('mutation', ['none', 'excluded', 'unknown', 'missing', 'interval', 'question'])
def test_explicit_governing_use_cannot_resolve_through_another_equal_source(tmp_path, mutation):
    from legalmath.prospectus.successor import admissions
    from legalmath.prospectus.successor.occurrences import uses
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    graph = p1['payload']['graph']
    assembly = deepcopy(p2['payload']['assembly'])
    raw = admission['governing'][0]['to'][0]
    original = uses(graph, assembly, raw, question='Q1')[0]
    unit = next(u for u in assembly['units'] if u['unit'] == original['unit'])
    twin = deepcopy(unit)
    twin['unit'] += ':intended-copy'
    assembly['units'].append(twin)
    use = {k: original[k] for k in ('unit', 'start', 'end')}
    use['unit'] = twin['unit']
    if mutation == 'excluded':
        twin['role'] = 'EXCLUDED'
    elif mutation == 'unknown':
        twin['role'] = 'UNKNOWN'
    elif mutation == 'missing':
        assembly['units'].remove(twin)
    elif mutation == 'interval':
        use['start'] += 1
        use['end'] += 1
    elif mutation == 'question':
        twin['questions'] = ['Q2']
    edge = {**admission['governing'][0], 'to': [{'source': raw, 'use': use}], 'questions': ['Q1']}
    admission.update(version='prospectus-layout.v2', governing=[edge])
    layout = admissions.structure(graph, admission)
    result = admissions.governing_dependencies({**graph, 'layout': layout}, assembly)
    assert len(result) == 1
    assert result[0]['status'] == ('RESOLVED' if mutation == 'none' else 'UNRESOLVED')
    if mutation == 'none':
        assert result[0]['target_uses'][0][0]['unit'] == twin['unit']
    else:
        assert result[0]['target_uses'] == [[]]
    # The equal source in the unrelated original paragraph still exists.
    assert any(m['unit'] == original['unit'] for m in uses(graph, assembly, raw, question='Q1'))


@pytest.mark.parametrize('mutation', ['missing-use', 'empty-unit', 'reversed', 'length', 'source'])
def test_explicit_governing_target_rejects_malformed_binding(tmp_path, mutation):
    from legalmath.prospectus.successor import admissions
    from legalmath.prospectus.successor.occurrences import uses
    req = pdf_fixture(tmp_path)
    admission = req.pop('layout_admission')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    raw = admission['governing'][0]['to'][0]
    found = uses(p1['payload']['graph'], p2['payload']['assembly'], raw, question='Q1')[0]
    target = {'source': deepcopy(raw), 'use': {k: found[k] for k in ('unit', 'start', 'end')}}
    if mutation == 'missing-use':
        target.pop('use')
    elif mutation == 'empty-unit':
        target['use']['unit'] = ''
    elif mutation == 'reversed':
        target['use']['start'] = target['use']['end']
    elif mutation == 'length':
        target['use']['end'] += 1
    elif mutation == 'source':
        target['source']['quote'] = 'invented'
    admission.update(version='prospectus-layout.v2')
    admission['governing'][0]['to'] = [target]
    with pytest.raises(ValueError):
        admissions.structure(p1['payload']['graph'], admission)
