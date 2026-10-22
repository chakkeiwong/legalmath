"""Adverse scope changes against retained original FY2010 page occurrences."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import contract_assembly, reviewed_references
from legalmath.prospectus.successor.bes_fy2010_scope import INTRO, RELEASE, check
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_fy2010_scope_program import source_units, controls

UNITS = [u for u in source_units()['units'] if
         (u['source_sha256'] == INTRO and u['page'] in (1, 2)) or
         (u['source_sha256'] == RELEASE and u['page'] in (1, 41, 42))]


def fixture():
    graph = {'units': deepcopy(UNITS), 'references': [], 'context': 'synthetic-test'}
    asm = contract_assembly.assemble(graph, {'operations': [
        {'unit': u['id'], 'source_text_sha256': u['text_sha256'], 'role': 'OPERATIVE',
         'reason': 'Retained source scope'} for u in graph['units']]})
    raw = {u['id']: u for u in graph['units']}
    row = {'id': 'finite-fy2010', 'form': 'external', 'source': anchor(raw['bes-supplement-2:p1:l35']),
           'from_use': 'bes-supplement-2:p1:l35', 'language': 'en',
           'targets': [{'source': anchor(u), 'use': u['id'], 'language': 'en'} for u in graph['units']
                       if u['source_sha256'] == RELEASE and u['page'] in (41, 42)],
           'authority': anchor(raw['bes-supplement-2:p1:l22']), 'questions': ['Q1', 'Q2'],
           'reason': 'All selected statement units, with context and original obligations separate', 'discovery_ids': []}
    return graph, asm, {'version': 'reviewed-references.v2', 'assembly_sha256': digest(asm),
                       'review': {'kind': 'DEVELOPMENT', 'reviewer': 'test fixture', 'reason': 'Finite source control'},
                       'references': [row]}


@pytest.mark.parametrize('version', ['v1', 'v2', 'v3'])
def test_complete_source_scope_and_qualification(version):
    graph, asm, p = fixture()
    p['version'] = 'reviewed-references.' + version
    if version == 'v1': del p['references'][0]['discovery_ids']
    deps, edges = reviewed_references.admit(graph, asm, p)
    assert len(edges) == 300 and deps[0]['status'] == 'RESOLVED'
    result = deps[0]['statement_scope_check']
    assert result['pages'] == [41, 42] and result['target_units'] == 300
    assert result['context_pages_do_not_expand_incorporation']
    assert result['source_authenticity'] == 'NOT_ESTABLISHED'
    assert result['incorporation_status'] == 'UNRESOLVED'
    assert not result['independent_legal_acceptance']
    assert 'for information purposes only.' in result['restriction'][-1]['quote']
    assert 'Unaudited financial information under IFRS as implemented by the European Union' in result['release_identity_and_qualification'][2]['quote']


def test_all_declared_adverse_scope_controls_refuse():
    graph, asm, p = fixture()
    result = controls(graph, asm, p)
    assert len(result) == 15 and all(r['rejected'] for r in result)


@pytest.mark.parametrize('identity', [
    *['bes-supplement-2:p1:l' + str(i) for i in (22, 23, 24, 25, 33, 34, 35, 36, 37, 38)],
    *['bes-supplement-2:p2:l' + str(i) for i in (0, 1, 2, 3, 8, 9, 10)]])
def test_each_known_reference_and_restriction_line_is_guarded(identity):
    graph, asm, p = fixture()
    row = p['references'][0]
    row['source'] = anchor(next(u for u in graph['units'] if u['id'] == identity))
    row['from_use'] = identity
    row['targets'].pop()
    with pytest.raises(ValueError, match='all300'):
        reviewed_references.admit(graph, asm, p)


@pytest.mark.parametrize('change', ['duplicate_raw', 'duplicate_selected', 'duplicate_order',
                                   'wrong_edition', 'changed_intro', 'changed_cover', 'wrong_language'])
def test_source_identity_and_context_damage_refuses(change):
    graph, asm, p = fixture()
    row = p['references'][0]
    raw = {u['id']: u for u in graph['units']}
    if change == 'duplicate_raw': graph['units'].append(deepcopy(raw[row['targets'][0]['use']]))
    elif change == 'duplicate_selected': asm['units'].append(deepcopy(asm['units'][0]))
    elif change == 'duplicate_order': raw[row['targets'][1]['use']]['order'] = 0
    elif change == 'wrong_edition':
        for u in graph['units']:
            if u['source_sha256'] == RELEASE: u['source_sha256'] = '0' * 64
    elif change in ('changed_intro', 'changed_cover'):
        u = raw['bes-supplement-2:p1:l37' if change == 'changed_intro' else 'bes-release-fy10:p1:l2']
        u['raw'] += ' changed'
        u['text_sha256'] = digest(u['raw'].encode())
    else: row['targets'][0]['language'] = 'pt'
    p['assembly_sha256'] = digest(asm)
    with pytest.raises(ValueError):
        reviewed_references.admit(graph, asm, p)


def test_unrelated_reference_remains_outside_finite_profile():
    graph, asm, p = fixture()
    row = p['references'][0]
    row['source'] = anchor(next(u for u in graph['units'] if u['id'] == 'bes-supplement-2:p2:l15'))
    assert check(graph, asm, row) is None


def test_complete_target_permutation_is_allowed():
    graph, asm, p = fixture()
    p['references'][0]['targets'].reverse()
    assert reviewed_references.admit(graph, asm, p)[0][0]['statement_scope_check']['target_units'] == 300
