"""Reject wrong complete-scope claims against immutable original BASF evidence."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import basf_printed_scope as core
from legalmath.prospectus.execution_acceptance import check_task


@pytest.fixture(scope='module')
def specimen():
    from scripts.prospectus_margin_preparation import products
    p = products()
    return (p['P1']['payload']['graph'], p['P2']['payload']['assembly'],
            p['P3']['payload']['interpretation_input']['governing_admission'])


def test_original_full_scope_and_unknown_bodies_are_separate(specimen):
    graph, assembly, admission = specimen
    result = core.check(graph, assembly, admission)
    assert result['status'] == 'COMPLETE_REVIEWED_SCOPE'
    assert len(result['groups']) == 54 and not result['missing_families']
    assert any(u['role'] == 'UNKNOWN' for u in assembly['units'])
    assert len(core.specification()['occurrences']) == 522
    assert len({o['source']['unit'] for o in core.specification()['occurrences']}) == 522


@pytest.mark.parametrize('family', list(core.PREFIXES))
def test_absent_whole_family_creates_unresolved_dependency(specimen, family):
    graph, assembly, original = specimen
    admission = {**original, 'governing': [e for e in original['governing'] if core.family(e['id']) != family]}
    result = core.check(graph, assembly, admission)
    assert result['status'] == 'PARTIAL'
    assert result['missing_families'] == [family]
    dependencies = core.missing_dependencies(result)
    assert dependencies[0]['id'] == 'margin-scope:' + family
    assert dependencies[0]['status'] == 'UNRESOLVED'


def test_all_families_missing_is_unreviewed(specimen):
    graph, assembly, _ = specimen
    result = core.check(graph, assembly, None)
    assert result['status'] == 'UNREVIEWED'
    assert len(core.missing_dependencies(result)) == 3


@pytest.mark.parametrize('mutation', [
    'governor-omitted', 'body-truncated', 'body-extended', 'duplicate-edge',
    'source-offset', 'selected-offset', 'numeric-boolean-offset', 'question-omitted',
    'inapplicable-governor', 'unrelated-family-name', 'governors-reversed'])
def test_malformed_full_family_refuses(specimen, mutation):
    graph, assembly, original = specimen
    admission = deepcopy(original)
    edges = admission['governing']
    index = next(i for i, e in enumerate(edges) if core.family(e['id']) == 'remaining')
    edge = edges[index]
    if mutation == 'governor-omitted': edges.pop(index)
    elif mutation == 'body-truncated': edge['to'].pop()
    elif mutation == 'body-extended': edge['to'].append(deepcopy(edges[0]['to'][0]))
    elif mutation == 'duplicate-edge': edges.append(deepcopy(edge))
    elif mutation == 'source-offset': edge['from']['start'] += 1
    elif mutation == 'selected-offset': edge['to'][0]['use']['start'] += 1
    elif mutation == 'numeric-boolean-offset': edge['to'][0]['use']['start'] = False
    elif mutation == 'question-omitted': edge['questions'] = ['Q1']
    elif mutation == 'inapplicable-governor': edge['id'] = 'basf-remaining-margin:permanent-global:p108:l15'
    elif mutation == 'unrelated-family-name': edge['id'] = 'other-family:' + edge['id']
    elif mutation == 'governors-reversed': edge['from'], edges[index + 1]['from'] = edges[index + 1]['from'], edge['from']
    with pytest.raises(ValueError, match='BASF'):
        core.check(graph, assembly, admission)


@pytest.mark.parametrize('kind', ['raw', 'role', 'selection'])
def test_source_or_construction_change_refuses(specimen, kind):
    graph, assembly, admission = specimen
    identity = 'basf-base-september-2022-exchange:p112:l18'
    if kind == 'raw':
        graph = {**graph, 'units': [{**u, 'raw': u['raw'] + '!'} if u['id'] == identity else u for u in graph['units']]}
        # Alter an included character rather than an unbound suffix.
        next(u for u in graph['units'] if u['id'] == identity)['raw'] = 'WRONG'
    else:
        change = {'role': 'EXCLUDED'} if kind == 'role' else {'text': 'WRONG'}
        assembly = {**assembly, 'units': [{**u, **change} if u['unit'] == identity else u for u in assembly['units']]}
    with pytest.raises(ValueError, match='BASF|occurrence'):
        core.check(graph, assembly, admission)


def test_unrelated_source_does_not_inherit_basf_choices():
    assert core.check({'units': []}, {'units': []}, None) is None


def test_duplicate_selected_identity_is_not_silently_collapsed(specimen):
    graph, assembly, admission = specimen
    unit = next(u for u in assembly['units'] if u['unit'] == 'basf-base-september-2022-exchange:p112:l18')
    assembly = {**assembly, 'units': [*assembly['units'], dict(unit)]}
    with pytest.raises(ValueError, match='Duplicate BASF'):
        core.check(graph, assembly, admission)


@pytest.mark.parametrize('change', ['task', 'handler', 'stream', 'name'])
def test_assisted_validator_is_narrowly_registered(change):
    task = {'id': 'basf-margins', 'validator': 'basf-printed-scope.v1', 'handler': 'agent', 'stream': 'assisted'}
    check_task(task)
    task[{'task': 'id', 'handler': 'handler', 'stream': 'stream', 'name': 'validator'}[change]] = {
        'task': 'independent-readings', 'handler': 'external', 'stream': 'engineering', 'name': 'anything.v1'}[change]
    with pytest.raises(ValueError, match='named task'):
        check_task(task)
