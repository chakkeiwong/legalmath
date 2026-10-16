"""Actual rejected response and adversarial exact-evidence boundaries."""
from copy import deepcopy
from pathlib import Path
import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import evidence_tables as codec, source_references as spans
from legalmath.interpretation.assurance.decomposition import merge_pieces, apply_cross, compact_request
from legalmath.interpretation.assurance.semantics import Inventory, validate_inventory
from legalmath.interpretation.assurance.journal import JournalProvider
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .support import packet, inventory

ROOT=Path(__file__).resolve().parents[2]
RETAINED=ROOT/'artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol-inventory-window/baseline/product/revisions/fe77546e483dd7ea2225605147e9a2555e6ae173327a5f78e0ca000cb21ebb9b/core/actions/action-0001/transport/call-003/source-references'


def test_exact_shared_evidence_and_trusted_expected_hashes():
    p=packet();quote={'unit_id':p['units'][0]['unit_id'],'quote':p['units'][0]['text']}
    req={'task':'SOURCE_FIDELITY','source_packet':p,'rows':[{'evidence':[quote], 'text':'unchanged '*100} for _ in range(30)]}
    wire=codec.encode(req)
    args={'expected_request_hash':digest(req),'expected_packet_hash':digest(p)}
    assert codec.decode(wire,**args)==req
    assert len(canonical(wire))<len(canonical(req))
    for key in ('request_hash','packet_hash'):
        changed=deepcopy(wire);changed[key]='0'*64
        with pytest.raises(LegalMathError):codec.decode(changed,**args)
    changed=deepcopy(wire);changed['source_packet']['units'][0]['text']+='changed'
    changed['packet_hash']=digest(changed['source_packet'])
    with pytest.raises(LegalMathError):codec.decode(changed,**args)
    with pytest.raises(LegalMathError):codec.decode(wire,maximum=1000,**args)


def test_marker_like_source_data_round_trips_without_becoming_an_instruction():
    req={'task':'TEST','source_packet':packet(),'extra':{'$text':0,'$row':[1,2],'$quote':'data'}}
    wire=codec.encode(req)
    assert codec.decode(wire,expected_request_hash=digest(req),expected_packet_hash=digest(packet()))==req
    bad=deepcopy(wire);bad['texts'].append('unattached data')
    with pytest.raises(LegalMathError):codec.decode(bad,expected_request_hash=digest(req),expected_packet_hash=digest(packet()))


def test_retained_full_unit_response_has_separate_raw_and_expanded_caps(tmp_path):
    read=lambda name:loads((RETAINED/name).read_bytes())
    raw=read('raw-response.json')['value'];refs=read('references.json');request=read('original-request.json')
    schema=read('original-schema.json');wire_schema=read('wire-schema.json')
    assert len(canonical(raw))==25681
    with pytest.raises(LegalMathError) as exc:
        spans.resolve_response(raw,schema,wire_schema,refs,request['source_packet'],refs['request_hash'],maximum=200000)
    assert exc.value.code=='E_RESOURCE_LIMIT'
    resolved=spans.resolve_response(raw,schema,wire_schema,refs,request['source_packet'],refs['request_hash'],maximum=codec.MAXIMUM)
    assert len(canonical(resolved))==475806
    validate_inventory(resolved,request['source_packet'])
    provider=FunctionProvider(lambda _:resolved)
    settings=Settings(max_input_bytes=200000,max_output_bytes=200000,
        max_logical_input_bytes=codec.MAXIMUM,max_expanded_output_bytes=codec.MAXIMUM)
    answer=JournalProvider(provider,tmp_path/'journal').complete(request,schema,settings)
    assert answer.value==resolved
    assert (tmp_path/'journal/call-000/response.json').exists()


def test_prepared_schema_and_source_references_reach_actual_transport(tmp_path):
    p=packet();inv=inventory()
    schema=Inventory.model_json_schema()
    def respond(wire):
        decoded=codec.decode(wire,expected_request_hash=wire['request_hash'],expected_packet_hash=digest(compact_request({'source_packet':p},profile='v2')['source_packet']))
        refs=decoded['source_references']
        whole=next(s['span_id'] for s in refs['spans'] if s['unit_id']==p['units'][0]['unit_id'] and s['start_codepoint']==0)
        value=deepcopy(inv);value['claims'][0]['evidence']=[{'span_ids':[whole]}]
        return value
    provider=FunctionProvider(respond)
    wrapped=CompactProvider(provider,tmp_path/'transport',reference_protocol=spans.PROTOCOL,input_profile=codec.PROFILE)
    req={'task':'SOURCE_INVENTORY','source_packet':p,'large_repeated_claims':[inv]*30}
    settings=Settings(max_input_bytes=200000,max_output_bytes=200000,max_logical_input_bytes=codec.MAXIMUM,max_expanded_output_bytes=codec.MAXIMUM)
    answer=JournalProvider(wrapped,tmp_path/'journal').complete(req,schema,settings)
    assert validate_inventory(answer.value,p)==inv
    assert provider.requests[0]['evidence_profile']==codec.PROFILE


def two_pieces():
    p=packet();unit=deepcopy(p['units'][0]);unit['unit_id']='second';unit['text']='Other actor; a secondary record can differ.'
    p['units'].append(unit);parts=[]
    for u in p['units']:
        piece={**deepcopy(p),'units':[deepcopy(u)]};inv=inventory()
        inv['claims'][0]['evidence']=[{'unit_id':u['unit_id'],'quote':u['text']}]
        inv['claims'][0]['statement']=u['text']
        inv['units'][0]['unit_id']=u['unit_id'];inv['uncertainties']=['Unresolved authority']*30
        parts.append((piece,inv))
    return p,parts


def test_aggregate_preserves_response_denominators_and_separate_cross_issues():
    p,parts=two_pieces();merged=merge_pieces(p,parts)
    assert len(merged['uncertainties'])==60 and len(merged['pieces'])==2
    with pytest.raises(LegalMathError):validate_inventory(merged,p)
    issue={'checked_unit_ids':[u['unit_id'] for u in p['units']],
        'issues':[{'issue_id':'cross','affected_claim_ids':[merged['claims'][0]['claim_id']],
            'evidence':merged['claims'][1]['evidence'],'explanation':'Different actor qualifies the inference.'}],
        'unresolved_questions':['Which record has legal effect?']}
    checked=apply_cross(merged,issue,p)
    assert checked['uncertainties']==merged['uncertainties']
    assert checked['cross_reviews']==[issue]
    with pytest.raises(LegalMathError):merge_pieces(p,parts[:1])
    with pytest.raises(LegalMathError):merge_pieces(p,parts+parts[:1])


def test_changed_piece_and_nonunique_quotes_are_rejected():
    p,parts=two_pieces();parts[0][0]['units'][0]['text']+='changed'
    with pytest.raises(LegalMathError):merge_pieces(p,parts)
    p=packet();p['units'][0]['text']='repeat repeat'
    with pytest.raises(LegalMathError):codec.encode({'source_packet':p,'evidence':{'unit_id':p['units'][0]['unit_id'],'quote':'repeat'}})
