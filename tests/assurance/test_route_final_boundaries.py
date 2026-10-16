"""Downstream expansion and retrieved-source regressions from route review."""
from copy import deepcopy
import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import evidence_tables as codec
from tests.search.support import FunctionProvider
from .support import packet, inventory
from .test_fidelity_capacity import engine, matrix
from .test_integration import responder, settings
from .test_staged_source_review import reviewed
from .test_evidence_route import two_pieces
from legalmath.interpretation.assurance import staged_source_review as stage
from legalmath.interpretation.assurance.decomposition import merge_pieces


def passage_request():
    p = packet()
    p['units'][0]['text'] = 'An ownership entry 🧾 can be copied incorrectly. ' * 400
    unit = p['units'][0]
    passages = [{'rank':i+1,'unit_id':unit['unit_id'],'start':i,'end':i+4000,
        'text':unit['text'][i:i+4000],'source':None,'role':None} for i in range(20)]
    return {'task':'SCOPED_SOURCE_FIDELITY','source_packet':p,'passages':passages,
        'ordinary_marker_data':{'$source_text':[0,1,2]}}


def test_overlapping_retrieved_passages_preserve_text_offsets_rank_and_metadata():
    request = passage_request()
    wire = codec.encode(request)
    decoded = codec.decode(wire,expected_request_hash=digest(request),
        expected_packet_hash=digest(request['source_packet']))
    assert decoded == request
    assert len(canonical(wire)) < len(canonical(request))/2
    assert b'"$source_text"' in canonical(wire)


@pytest.mark.parametrize('fault',['offset','foreign_unit','replacement_text'])
def test_retrieval_coordinates_cannot_silently_replace_tool_evidence(fault):
    request = passage_request()
    if fault == 'offset':request['passages'][0]['start'] += 1
    if fault == 'foreign_unit':request['passages'][0]['unit_id'] = 'foreign'
    if fault == 'replacement_text':request['passages'][0]['text'] = 'Unsupported conclusion'
    with pytest.raises(LegalMathError):codec.encode(request)


def test_fidelity_conservative_reservation_uses_expanded_response_cap(root,tmp_path):
    claims,candidates = matrix(n_candidates=1)
    provider = FunctionProvider(responder())
    search = settings().search.model_copy(update={'max_output_bytes':1000,'max_expanded_output_bytes':3000000})
    run = engine(root,tmp_path,provider,search=search)
    result,findings = run._fidelity(packet(),claims,candidates)
    assert result is None and not provider.requests
    assert findings[0]['diagnostic']['constraint'] == 'bytes'
    plan = loads((run.directory/'fidelity-rounds/round-000/plan.json').read_bytes())
    assert plan['byte_upper_bound'] >= 3000000


def test_incremental_policy_checks_actual_expanded_parts_under_same_aggregate_bound(root,tmp_path):
    claims,candidates = matrix(n_candidates=1)
    provider = FunctionProvider(responder())
    search = settings().search.model_copy(update={'max_output_bytes':1000,'max_expanded_output_bytes':3000000})
    run = engine(root,tmp_path,provider,search=search,incremental_fidelity_admission=True)
    result,_ = run._fidelity(packet(),claims,candidates)
    assert result is not None and len(provider.requests) == 1
    plan = loads((run.directory/'fidelity-rounds/round-000/plan.json').read_bytes())
    assert plan['validated_batches'][0]['admitted']
    assert len(canonical(result)) < plan['limits']['bytes']


def test_staged_review_applies_to_both_unpartitioned_inventories(root,tmp_path):
    def respond(request):
        if request['task'] == 'SOURCE_INVENTORY':return inventory()
        if request['task'] == 'REVIEW_SOURCE_CLAIMS':return reviewed(request)
        if request['task'] == 'REVIEW_SOURCE_OMISSIONS':
            return {'checked_unit_ids':[u['unit_id'] for u in request['source_packet']['units']],
                'issues':[],'unresolved_questions':['Governing ownership standard remains open.']}
        raise AssertionError(request['task'])
    provider = FunctionProvider(respond)
    run = engine(root,tmp_path,provider,staged_source_review=True,inventory_piece_characters=0)
    inventories = run._source_inventories(packet())
    assert set(inventories) == {'atomic-reader','qualification-reader'}
    assert all(inv['staged_reviews'][0]['claims'][0]['qualifications'] for inv in inventories.values())
    assert all(inv['cross_reviews'] for inv in inventories.values())
    assert [r['task'] for r in provider.requests].count('REVIEW_SOURCE_CLAIMS') == 2


def test_interaction_node_coverage_cannot_replace_directed_edge_accounting():
    p,parts = two_pieces()
    inventory = merge_pieces(p,parts)
    a,b = [c['claim_id'] for c in inventory['claims']]
    request = stage.interaction_request(p,'atomic-reader',inventory,[[a,b],[b,a]])
    value = {'request_binding':request['request_binding'],
        'checked_unit_ids':[u['unit_id'] for u in p['units']], 'checked_claim_ids':[a,b],
        'checked_edges':[{'claim_id':a,'related_claim_id':b}], 'issues':[], 'unresolved_questions':[]}
    with pytest.raises(LegalMathError):stage.validate_interaction(value,request,inventory)
    value['checked_edges'].append({'claim_id':b,'related_claim_id':a})
    assert stage.validate_interaction(value,request,inventory) == value


def test_nonlocal_nomination_cannot_silently_be_a_self_relation():
    p,parts = two_pieces()
    inv = merge_pieces(p,parts)
    request = stage.review_request(p,'atomic-reader',inv,[inv['claims'][0]['claim_id']])
    value = reviewed(request)
    value['claims'][0]['nonlocal_claim_ids'] = [value['claims'][0]['claim_id']]
    with pytest.raises(LegalMathError):stage.validate_review(value,request,inv)
