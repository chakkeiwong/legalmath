"""Exercise the actual consumer after valid resealing, without BASF rules."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import re

import pytest

from legalmath.prospectus.successor import service, source_graph, contract_assembly
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from legalmath.prospectus.successor.reference_closure import close
from scripts.prospectus_closure_fixtures import cross_document_fixture, REVIEW


def test_cycle_witnesses_are_invariant_to_root_and_edge_order():
    edges = [
        {'from': 'a', 'to': 'b', 'kind': 'reference', 'resolved': True, 'id': 'ab'},
        {'from': 'b', 'to': 'a', 'kind': 'conditions', 'resolved': True},
        {'from': 'a', 'to': None, 'kind': 'reference', 'resolved': False, 'id': 'missing'},
        {'from': 'b', 'to': 'b', 'kind': 'priority', 'resolved': True},
    ]
    expected = {'roots': ['a', 'b'], 'reachable': ['a', 'b'], 'unresolved': [
        'Unresolved reference: missing', 'Unsupported priority: b',
        'Unsupported reference cycle: a', 'Unsupported reference cycle: b']}
    for roots in permutations(['a', 'b']):
        for outgoing in permutations(edges):
            assert close(['a', 'b'], outgoing, roots) == expected


@pytest.fixture
def consumer_case(tmp_path):
    req = cross_document_fixture(tmp_path)
    req['bundle']['dependencies'].append({'id': 'declared-source-gap',
        'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED'})
    req['bundle']['dependencies'].append({'id': 'declared-resolved',
        'questions': ['Q1', 'Q2'], 'status': 'RESOLVED'})
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    # The synthetic dependencies change graph/assembly identity, not its text.
    req['annotation_admission']['assembly_sha256'] = digest(assembly)
    a = anchor(graph['units'][0])
    req['reference_admission'] = {'version': 'reviewed-references.v3',
        'assembly_sha256': digest(assembly), 'review': REVIEW, 'references': [{
            'id': 'self-scope', 'form': 'relative', 'source': a, 'from_use': a['unit'],
            'language': 'en', 'targets': [{'source': a, 'use': a['unit'], 'language': 'en'}],
            'authority': a, 'questions': ['Q1', 'Q2'], 'discovery_ids': [],
            'reason': 'Synthetic complete self-scope; conservative cycle remains unknown'}]}
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3,
        'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    return products, tmp_path


def reseal(products, semantic):
    products = dict(products)
    bundle = products['P1']['payload']['request']['bundle']
    p3 = products['P3']
    products['P3'] = service.seal('P3', bundle, p3['inputs'], semantic)
    for stage in ('P4', 'P5'):
        old = products[stage]
        products[stage] = service.seal(stage, bundle,
            {**old['inputs'], 'P3': products['P3']['sha256']}, old['payload'])
    return products


def test_positive_consumer_keeps_cycles_and_question_uncertainty(consumer_case):
    products, root = consumer_case
    answer = service.consume(products, root, mode='frozen')
    for q in ('Q1', 'Q2'):
        assert answer['questions'][q]['status'] == 'UNKNOWN'
        assert 'reference-closure:' + q in answer['questions'][q]['unresolved']
        closure = next(d for d in products['P3']['payload']['dependencies']
                       if d['id'] == 'reference-closure:' + q)
        assert any(s.startswith('Unsupported reference cycle:') for s in closure['unresolved'])


@pytest.mark.parametrize('case', ['roots', 'reachable', 'cycle', 'drop', 'duplicate', 'invent',
    'declared-drop', 'declared-status', 'question-hide', 'question-invent', 'subquestion-hide',
    'question-status', 'subquestion-status', 'question-value', 'q3-status', 'q3-value'])
def test_actual_consumer_rejects_forged_closure_and_concealed_uncertainty(consumer_case, case):
    products, root = consumer_case
    semantic = deepcopy(products['P3']['payload'])
    closure = next(d for d in semantic['dependencies'] if d['id'] == 'reference-closure:Q1')
    expected = 'Consumed reference closure differs'
    if case in ('roots', 'reachable'):
        closure[case].pop()
    elif case == 'cycle':
        closure['unresolved'].pop()
    elif case == 'drop':
        semantic['dependencies'].remove(closure)
    elif case == 'duplicate':
        semantic['dependencies'].append(deepcopy(closure))
    elif case == 'invent':
        semantic['dependencies'].append({**deepcopy(closure), 'id': 'reference-closure:invented'})
    elif case.startswith('declared-'):
        dep = next(d for d in semantic['dependencies'] if d['id'] == 'declared-source-gap')
        if case.endswith('drop'):
            semantic['dependencies'].remove(dep)
        else:
            dep['status'] = 'RESOLVED'
        expected = 'Consumed dependencies differ'
    elif case.startswith('q3-'):
        if case.endswith('status'):
            semantic['questions']['Q3']['status'] = 'COMPLETE'
        else:
            semantic['questions']['Q3']['value']['Q1']['complete'] = True
        expected = 'Consumed semantic completeness differs'
    else:
        q = semantic['questions']['Q2']
        if case.startswith('subquestion-'):
            q = q['subquestions']['possible_common']
        expected = 'Consumed question hides or invents'
        if case.endswith('hide'):
            q['unresolved'].remove('declared-source-gap')
        elif case.endswith('invent'):
            # A resolved source link cannot be invented as an unresolved one.
            q['unresolved'].append('declared-resolved')
        else:
            expected = 'Consumed question resolves source dependency uncertainty'
            if case.endswith('status'):
                q['status'] = 'YES'
            else:
                q['value'] = True
    # Exercise the intended dependency invariant even when an earlier question
    # replay already refuses this corruption. Retain the exact error contract.
    graph = products['P1']['payload']['graph']
    selected = products['P2']['payload']
    request = {**products['P1']['payload']['request'], **(semantic.get('interpretation_input') or {})}
    with pytest.raises(ValueError, match=expected):
        service._verify_consumed_dependencies(graph, selected, request, semantic)

    # The earlier refusal predates the reference-consumption repair. Check it
    # against frozen103 rather than weakening the consumer assertion to any error.
    from scripts.prospectus_reference_consumption_compare import load_before
    prep = Path(__file__).resolve().parents[2] / (
        'docs/implementation/prospectus-execution-authority/reviews/reference-consumption-repair-372')
    before = load_before(prep, 'service')
    def question_error(function):
        try:
            function(graph, selected, request, semantic)
        except ValueError as error:
            return str(error)
        return None
    first = question_error(before._verify_consumed_questions)
    assert question_error(service._verify_consumed_questions) == first
    with pytest.raises(ValueError, match=re.escape(first or expected)):
        service.consume(reseal(products, semantic), root, mode='frozen')
