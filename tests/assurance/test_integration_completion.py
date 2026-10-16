"""Adversarial authorization, occurrence/aggregate and installed tool controls."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.source_context import ContextProvider
from legalmath.interpretation.assurance.provider_authority import verify_live_provider
from legalmath.interpretation.search.providers import CodexProvider, Completion
from legalmath.interpretation.search.models import Settings
from .test_source_context import preparation
from .test_integration import source
from .test_successor_grants import grant
from .test_dossier_answer import prepared
from .test_successor_workflow import investigation
from scripts.legal_integration_tools import ProductToolBackend

ROOT=Path(__file__).resolve().parents[2]

def counted_provider(tmp_path):
    allowance, _=grant(tmp_path)
    class Counted(CodexProvider):
        def __init__(self):self.allowance=allowance;self.routing={'fixture':True};self.calls=0
        def complete(self,request,schema,settings):
            slot=self.allowance.reserve(digest(request));self.calls+=1
            return Completion({'receipt':True},{'allowance_slot':slot,'synthetic':True})
    return Counted()

def test_valid_qualified_provider_preserves_one_reservation(tmp_path):
    provider=counted_provider(tmp_path)
    context,packet=preparation(tmp_path,tmp_path/'source',[source()])
    wrapped=ContextProvider(provider,context,tmp_path)
    assert verify_live_provider(wrapped)['used']==0
    wrapped.complete({'source_packet':packet},{},Settings())
    assert provider.calls==provider.allowance.verify()['used']==1

@pytest.mark.parametrize('fault',['fake','route','context','allowance','evidence','underlying',
                                'wrapper_live','provider_live'])
def test_invalid_qualified_authority_never_dispatches(tmp_path,fault):
    provider=counted_provider(tmp_path)
    context,_=preparation(tmp_path,tmp_path/'source',[source()])
    wrapped=ContextProvider(provider,context,tmp_path)
    if fault=='fake':
        class Fake:live=True;allowance=provider.allowance
        wrapped.provider=Fake()
    if fault=='route':provider.routing={'changed':True}
    if fault=='context':wrapped.source_context['qualification']['limitations'].append('changed')
    if fault=='allowance':wrapped.allowance=None
    if fault=='evidence':(tmp_path/'source/packet.json').write_text('changed')
    if fault=='underlying':wrapped.provider=counted_provider(tmp_path)
    if fault=='wrapper_live':wrapped.live=False
    if fault=='provider_live':provider.live=False
    with pytest.raises(LegalMathError):wrapped.complete({}, {}, Settings())
    assert provider.calls==0 and provider.allowance.verify()['used']==0

def test_shared_text_occurrences_keep_independent_context_and_stable_ids(prepared):
    from legalmath.interpretation.assurance import dossier_answer as w
    original=deepcopy(prepared[4])
    original['extra']={'batches':[{'role':'first','rows':[{'detail':'same'}]},
                                  {'role':'second','rows':[{'detail':'same'}]}]}
    idx=w.registry(original)
    records=[r for r in idx['records'].values() if w.record_value(idx,r)=={'detail':'same'}]
    assert len(records)==2 and records[0]['content_id']==records[1]['content_id']
    req=w.review_request(idx,[records[0]['record_id']])
    assert len([r for r in req['records'] if req['content_table'][r['content_id']]=={'detail':'same'}])==1
    reversed_input={k:original[k] for k in reversed(original)}
    other=w.registry(reversed_input)
    assert {r['occurrence_id'] for r in idx['records'].values()}=={r['occurrence_id'] for r in other['records'].values()}
    assert w.restore(idx)==original

def test_aggregate_capacity_refuses_large_output_reservation(prepared):
    from legalmath.interpretation.assurance import dossier_answer as w
    p=w.partition(prepared[4],maximum_records_per_group=2)
    budget=w.capacity_budget(prepared[4],p)
    assert sum(budget['review_output_limits']) <= 200000
    assert all(1000 < n <= 4000 for n in budget['review_output_limits'])
    with pytest.raises(LegalMathError) as exc:w.capacity_budget(prepared[4],p,extra_dependency_bytes=190000)
    assert exc.value.code=='E_RESOURCE_LIMIT'

def test_occurrence_account_range_cannot_hide_missing_duplicate_or_foreign_homes(prepared):
    from legalmath.interpretation.assurance import dossier_answer as w
    from scripts.legal_mission_context_boundary import receipt
    p=w.partition(prepared[4]);req=w.review_request(p['registry'],p['batches'][0])
    value=receipt(req);ids=req['assigned_records']
    value['accounts'][0]['record_ids']=w.compact_account_ids(ids)
    w.validate_review(value,req)
    assert w.expand_account_ids(value['accounts'][0]['record_ids'])==ids
    for faulty in [value['accounts']*2,
                   [{'record_ids':[ids[0]+'..e99999'],'disposition':'UNRESOLVED','explanation':'false'}],
                   [{'record_ids':[ids[0]],'disposition':'UNRESOLVED','explanation':'missing'}]]:
        bad=deepcopy(value);bad['accounts']=faulty
        with pytest.raises(LegalMathError):w.validate_review(bad,req)

def test_backend_selection_is_bound_and_disabled_checks_do_not_run(tmp_path):
    a=ProductToolBackend(['bm25']);b=ProductToolBackend(['legalruleml'])
    assert a.identity()!=b.identity()
    assert b.retrieval({}, {}, tmp_path)['reason']=='DISABLED_BY_PROFILE'
    assert a.criticism({}, {}, tmp_path)['reason']=='DISABLED_BY_PROFILE'
    with pytest.raises(LegalMathError):ProductToolBackend(['invented'])
    with pytest.raises(LegalMathError):ProductToolBackend(['bm25','bm25'])

def test_logical_english_installed_parser_and_truth_preserve_unknown(prepared):
    from scripts.legal_mission_logical_english import check,conditional_values
    original=prepared[4];packet=original['source_packet']
    reading=deepcopy(next(iter(original['candidates'].values())))
    names=['request','records','technical']
    reading['formalization']={'result_type':'bool','scope':'true',
        'result':'(and request (or records (not technical)))',
        'facts':[{'name':n,'type':'bool','meaning':n,'unit':'Boolean',
                  'source_unit_ids':[packet['units'][0]['unit_id']],'requires_judgment':True} for n in names]}
    with TemporaryDirectory(dir=ROOT/'artifacts',prefix='le-integration-test-') as td:
        result=check(packet,{'conditional':reading},Path(td))
        assert result['status']=='PASS', result
        row=result['readings'][0]
        assert row['unknown_inputs']['result']=='UNKNOWN'
        import json
        table=json.loads((ROOT/row['conditional_values']['path']).read_text())
        assert conditional_values(table,{'request':False})['result'] is False
        assert conditional_values(table,{'request':True,'records':True})['result'] is True
        assert conditional_values(table,{'request':True,'records':False})['result']=='UNKNOWN'
        assert row['exact_parsed_rules'] and row['consequences_equal']
