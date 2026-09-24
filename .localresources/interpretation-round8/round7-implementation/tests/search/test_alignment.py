from copy import deepcopy
from itertools import product
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.alignment import (
    discover, review_packet, validate_correspondence, rename_bundle, translate_snapshot)
from legalmath.interpretation.search.formal import Comparisons, bundle, project, RULE
from legalmath.interpretation.search.models import commitment
from legalmath.interpretation.search.questions import questions, behavioral_groups
from legalmath.ir.evaluate import evaluate
from tests.search.support import generation, packet
from tests.search.test_formal import linkage_pair, AT


def proposal(left, right, mapping, source=None):
    return {'source_packet_hash': digest(source or packet()),
            'left_commitment': commitment(left), 'right_commitment': commitment(right),
            'links': [{'left': a, 'right': b,
                       'assumption': 'For this hypothetical comparison only, these entries have identical tagged values.'}
                      for a, b in mapping.items()],
            'rationale': 'Investigate the consequence of a proposed fact correspondence; no semantic approval.',
            'output_meaning_assumption': 'Assume both Boolean outputs mean that the selected restriction is triggered.',
            'citations': [{'unit_id': 'p1', 'quote': 'at least six months'}]}


def alias_readings():
    left, right = linkage_pair()
    mapping = {'scope_fact': 'covered', 'gift': 'gift_alias', 'discount': 'discount_alias',
               'direct': 'contextual', 'contextual': 'direct'}
    for fact in right['formalization']['facts']:
        fact['name'] = mapping[fact['name']]
    right['formalization']['facts'].reverse()
    right['formalization']['scope'] = 'covered'
    right['formalization']['result'] = '(and gift_alias (not discount_alias) (or contextual direct))'
    return left, right, mapping


def checker(root, tmp_path, domain=None):
    return Comparisons(tmp_path, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, domain)


def test_exact_aliases_replay_original_java_and_distinguishing_questions(root, tmp_path):
    a, b, mapping = alias_readings()
    original = deepcopy((a, b))
    c = checker(root, tmp_path)
    result = c.compare(a, b, packet())
    assert result['status'] == 'DIFFERENT'
    assert result['fact_correspondence']['mapping'] == mapping
    assert result['right_bundle_hash'] == digest(bundle(b, packet(), AT))
    snapshots = result['original_snapshots']
    assert snapshots['right'] == translate_snapshot(snapshots['left'], mapping)
    assert [project(r['java']) for r in result['replays']] == [
        project(evaluate(bundle(r, packet(), AT), snapshots[k], RULE, AT, AT))
        for r, k in [(a, 'left'), (b, 'right')]]
    assert len({r['build_manifest']['bundle_hash'] for r in result['replays']}) == 2
    assert (a, b) == original
    nodes = [{'node_id': i, 'reading': r, 'encoding_error': None} for i, r in [('a', a), ('b', b)]]
    qs = questions(nodes, [{'pair': ['a','b'], 'left_node_id': 'a', 'right_node_id': 'b', 'result': result}], packet(), AT)
    assert qs[0]['separated_candidate_pairs'] == 1
    assert set(qs[0]['predictions']) == {'a', 'b'} and not qs[0]['excluded_incompatible_fact_bindings']


def test_simultaneous_aliases_preserve_all_boolean_states_including_missing_facts():
    a, b, mapping = alias_readings()
    original = bundle(b, packet(), AT); normalized = rename_bundle(original, bundle(a, packet(), AT), mapping)
    for values in product((None, False, True), repeat=len(mapping)):
        facts = {name: {'type': 'bool', 'status': 'known', 'value': v, 'evidence_ids': ['fixture'],
                         'valid_from': AT, 'valid_until': None, 'recorded_at': AT}
                 for name, v in zip(mapping, values) if v is not None}
        snap = {'subject_id': 'fixture', 'facts': facts}
        assert project(evaluate(normalized, snap, RULE, AT, AT)) == project(
            evaluate(original, translate_snapshot(snap, mapping), RULE, AT, AT))
    conflict = {'subject_id': 'fixture', 'facts': {'gift': {'type': 'bool', 'status': 'conflict', 'evidence_ids': ['a','b']}}}
    assert translate_snapshot(conflict, mapping)['facts']['gift_alias'] == conflict['facts']['gift']


@pytest.mark.parametrize('field,value', [
    ('meaning', 'Thirty-day periods rather than completed calendar months'),
    ('meaning', 'All distributors, including actors outside the original class'),
    ('unit', 'days'), ('requires_judgment', True), ('source_unit_ids', ['p2'])])
def test_semantic_changes_are_never_automatic_aliases(root, tmp_path, field, value):
    a = generation()['readings'][0]; b = deepcopy(a)
    b['formalization']['facts'][0][field] = value
    assert discover(a, b)['mapping'] is None
    result = checker(root, tmp_path).compare(a, b, packet())
    assert result['status'] == 'INCOMPARABLE_FACT_BINDINGS'
    assert field in result['fact_correspondence']['same_name_changes']['months']


def test_exact_reordered_declarations_are_equivalent_but_ambiguous_aliases_are_not(root, tmp_path):
    a, _ = linkage_pair(); b = deepcopy(a); b['formalization']['facts'].reverse()
    assert checker(root, tmp_path).compare(a, b, packet())['status'] == 'EQUIVALENT_WITHIN_DOMAIN'
    a['formalization']['facts'][1]['meaning'] = a['formalization']['facts'][0]['meaning']
    b = deepcopy(a)
    b['formalization']['facts'][0]['name'] = 'renamed_scope'
    b['formalization']['facts'][1]['name'] = 'renamed_gift'
    found = discover(a, b)
    assert found['mapping'] is None and found['ambiguous_matches']


def test_conditional_comparison_cannot_establish_unconditional_groups(root, tmp_path):
    a = generation()['readings'][0]; b = deepcopy(a)
    b['formalization']['facts'][0]['meaning'] = 'Completed months under a different cutoff convention'
    p = proposal(a, b, {'months': 'months'})
    result = checker(root, tmp_path, {'months': {'min': '0', 'max': '12', 'allow_unknown': True}}).compare_conditional(a, b, packet(), p)
    assert result['status'] == 'CONDITIONAL_ANALYSIS'
    assert result['encoded_comparison']['status'] == 'EQUIVALENT_WITHIN_DOMAIN'
    assert result['correspondence']['changed_declarations'][0]['fields']['meaning']
    assert result['review_required'] and not result['release_eligible']
    assert behavioral_groups([{'node_id':'a'}, {'node_id':'b'}], [{'pair':['a','b'], 'result':result}])['groups'] == [['a'],['b']]
    packet_out = review_packet(a,b,packet())
    assert packet_out['left'] == a and packet_out['right'] == b
    assert packet_out['semantic_mapping_approved'] is False


@pytest.mark.parametrize('defect', ['missing', 'many-to-one', 'extra-exception', 'unit', 'type', 'assumption',
                                    'source', 'candidate', 'quote', 'output-meaning', 'authority'])
def test_invalid_or_stale_correspondence_is_rejected(defect):
    a, b, mapping = alias_readings()
    p = proposal(a, b, mapping)
    if defect == 'missing': p['links'].pop()
    if defect == 'many-to-one': p['links'][1]['right'] = p['links'][0]['right']
    if defect == 'extra-exception':
        b['formalization']['facts'].append({**deepcopy(b['formalization']['facts'][0]), 'name':'hidden_exception'})
        p['right_commitment'] = commitment(b)
    if defect in ('unit', 'type'):
        a = generation()['readings'][0]; b = deepcopy(a)
        b['formalization']['facts'][0][defect] = 'days' if defect == 'unit' else 'money_hkd'
        p = proposal(a,b,{'months':'months'})
    if defect == 'assumption':
        b['formalization']['facts'][-1]['meaning'] = 'Changed scope'; p['right_commitment'] = commitment(b)
        for link in p['links']: link['assumption'] = None
    if defect == 'source': p['source_packet_hash'] = '0'*64
    if defect == 'candidate': p['right_commitment'] = '0'*64
    if defect == 'quote': p['citations'][0]['quote'] = 'not in retained source'
    if defect == 'output-meaning': p['output_meaning_assumption'] = ' '
    if defect == 'authority': p['approved'] = True
    with pytest.raises(LegalMathError): validate_correspondence(p,a,b,packet())
