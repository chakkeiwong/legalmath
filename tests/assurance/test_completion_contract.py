"""Reproduced gaps through repaired production boundaries; no live model claims."""
from copy import deepcopy
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import tempfile

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import dossier_answer as whole, answer_evidence
from legalmath.interpretation.assurance import investigation_answer as answer
from legalmath.interpretation.assurance.legal_locators import build_index, validate_citation
from legalmath.interpretation.assurance.failure_policy import SettledProviderFailure
from legalmath.interpretation.assurance.route_admission import workload, admission, RouteBudgetProvider
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_mission_context_boundary import receipt
from scripts.legal_independent_tools import IndependentProductToolBackend
from scripts.legal_product_completion import run_product
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_successor_workflow import investigation, complete_responder
from .test_dossier_answer import prepared
from .test_integration import source, settings
from tests.tooling.test_legal_answer_evidence import source_index, read
from scripts.legal_mission_answer import receipt_proposal
from legalmath.interpretation.assurance import answer_acceptance

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def circular_answer(prepared):
    root, directory, _, _, original = prepared
    request = deepcopy(original)
    packet, index = source_index()
    request['source_packet'] = packet
    manifest = {'profile':'product-answer-acceptance.v1', 'original_questions':request['original_questions'],
        'acceptance_obligations':[{'id':'staff-citation','question_ids':['gift']}],
        'cases':[{'case_id':'staff-control','question_ids':['gift'],'facts':{'competence_claimed':True}}],
        'source_documents':[{'source':index['source'],'unit_ids':list(index['units'])}]}
    save(directory/'circular-acceptance.json', manifest)
    request = answer_acceptance.bind(request, root, evidence_file(directory/'circular-acceptance.json', root))
    value = receipt_proposal(request)
    unit = next(u for u in packet['units'] if 'at least one competent staff' in u['text'])
    claim = value['answers'][0]['claims'][0]
    claim['support'] = [{'unit_id':unit['unit_id'], 'quote':unit['text']}]
    value['answers'][0]['answer'] = 'P19 concerns competent staff.'
    value['legal_citations'] = [{**claim['support'][0], 'locator':'P19','index_hash':index['index_hash'],
        'field_path':['answers',0,'answer'],'start':0,'end':3}]
    value['case_assessments'] = [{'case_id':'staff-control','facts_hash':digest({'competence_claimed':True}),
        'question_ids':['gift'], 'conclusion':'A claim of competence needs evidence.',
        'reasons':'Controlled conditional case, not a factual finding.', 'support':claim['support'],
        'contrary':[], 'assumptions':['Claimed staff role.'], 'unresolved':['Actual competence.']}]
    return request, value


@pytest.mark.parametrize('fault', ['none','p20','omitted','detached','case_missing','case_facts','case_quote',
                                  'implicit_list','brackets','manifest_changed','quote_locations_changed'])
def test_actual_product_validator_enforces_source_locators_and_case_identity(circular_answer, fault):
    request, value = deepcopy(circular_answer)
    if fault == 'p20':
        value['answers'][0]['answer'] = 'P20 concerns competent staff.'
        value['legal_citations'][0]['locator'] = 'P20'
    elif fault == 'omitted': value['legal_citations'] = []
    elif fault == 'detached':
        unit = request['source_packet']['units'][0]
        value['answers'][0]['claims'][0]['support'] = [{'unit_id':unit['unit_id'],'quote':unit['text']}]
    elif fault == 'case_missing': value['case_assessments'] = []
    elif fault == 'case_facts': value['case_assessments'][0]['facts_hash'] = '0'*64
    elif fault == 'case_quote': value['case_assessments'][0]['support'][0]['quote'] = 'Invented legal rule.'
    elif fault == 'implicit_list': value['answers'][0]['answer'] += ' See paragraphs 15 and 16.'
    elif fault == 'brackets': value['answers'][0]['answer'] += ' See [19].'
    elif fault == 'manifest_changed': request['answer_acceptance']['acceptance_obligations'] = []
    elif fault == 'quote_locations_changed': request['answer_acceptance']['current_quote_locations'] = {}
    if fault == 'none':
        checked = answer.validate_answer(value, request)
        review = answer_evidence.product_review_request(request, checked)
        assert {'question:gift','staff-citation','case:staff-control'} == {r['id'] for r in review['requirements']}
    else:
        with pytest.raises(LegalMathError): answer.validate_answer(value, request)


def test_original_inventory_population_cannot_be_replaced_or_reworded(prepared):
    root, directory, _, _, request = prepared
    path = root/'artifacts/legal-integration-assessment/2026-10-08/input-inventory.json'
    manifest = {'profile':'product-answer-acceptance.v1', 'original_questions':request['original_questions'],
        **answer_acceptance.population_contract(loads(path.read_bytes()), ['gift']),
        'source_population':evidence_file(path,root),'cases':[],'source_documents':[]}
    answer_acceptance.validate_manifest(manifest, request['original_questions'], root)
    for key in ('acceptance_obligations','original_readings'):
        corrupt = deepcopy(manifest); corrupt[key].pop()
        with pytest.raises(LegalMathError): answer_acceptance.validate_manifest(corrupt,request['original_questions'],root)
    corrupt = deepcopy(manifest); corrupt['original_readings'][0]['statement'] = 'Only trigger matters.'
    with pytest.raises(LegalMathError): answer_acceptance.validate_manifest(corrupt,request['original_questions'],root)


@pytest.mark.parametrize('fault',['missing','fabricated'])
def test_review_preservation_requires_actual_source_quote(fault):
    from tests.tooling.test_legal_answer_evidence import request, result
    req = request(); value = result(req)
    if fault == 'missing': value['findings'][0]['source_support'] = []
    else: value['findings'][0]['source_support'][0]['quote'] = 'Fabricated authority.'
    with pytest.raises(LegalMathError): answer_evidence.validate_review(value,req)


def test_runtime_configuration_mismatch_stops_before_provider(tmp_path):
    work=small_workload()
    provider=FunctionProvider(lambda r: pytest.fail('Mismatched runtime dispatched'))
    guard=RouteBudgetProvider(provider,tmp_path,work,work['stages'],'2099-01-01T00:00:00+00:00')
    with pytest.raises(LegalMathError):
        guard.configure(machine_qualification=True,supplied_questions=False,semantic_stage=False)
    corrupt=deepcopy(work);corrupt['runtime']['outer_actions']=1
    assert not admission(corrupt,corrupt['stages'],deadline_utc='2099-01-01T00:00:00+00:00')['admitted']
    assert not provider.requests


def test_claimed_original_sha_cannot_authenticate_substituted_html():
    packet, index = source_index()
    unit = next(u for u in packet['units'] if 'at least one competent staff' in u['text'])
    with pytest.raises(LegalMathError) as error:
        build_index(packet, '<ol start="20"><li>' + escape(unit['text']) + '</li></ol>',
                    source_ref=index['source'], unit_ids=[unit['unit_id']])
    assert 'differs from claimed original' in error.value.details
    validate_citation(packet, index, unit_id=unit['unit_id'], quote='at least one competent staff', locator='P19')
    wrong = deepcopy(index); wrong['units'][unit['unit_id']]['locators'] = ['P20']
    wrong['index_hash'] = digest({k:v for k,v in wrong.items() if k != 'index_hash'})
    with pytest.raises(LegalMathError):
        validate_citation(packet, wrong, unit_id=unit['unit_id'], quote='at least one competent staff', locator='P20')


def test_emphasized_clause_is_preserved_but_unbound_index_cannot_certify():
    packet = {'units':[{'unit_id':'u','text':'Provider shall keep records.'}]}
    index = build_index(packet, '<ol><li><p><strong>Provider shall keep records.</strong></p></li></ol>',
                        source_ref={}, unit_ids=['u'])
    assert index['units']['u']['locators'] == ['P1']
    with pytest.raises(LegalMathError) as error:
        validate_citation(packet, index, unit_id='u', quote='records', locator='P1')
    assert 'Unbound' in error.value.details


def test_review_population_cannot_replace_original_obligations():
    base = read('requests/baseline.review.json')
    with pytest.raises(LegalMathError) as error:
        answer_evidence.review_request(base, base['proposed_answer'],
            [{'id':'invented', 'kind':'obligation', 'question_ids':['p10']}])
    assert 'population' in error.value.details
    req = answer_evidence.review_request(base, base['proposed_answer'])
    assert len(req['requirements']) == len(base['acceptance_obligations']) + len(base['cases']) + len(base['original_questions'])


def test_catalog_exposes_conditional_assumptions_rivals_and_tool_effects():
    value = {'answers':[{'question_id':'p10','answer':'Answer','claims':[{'conclusion':'Conclusion',
        'inference':'Inference','assumptions':['Condition A'],'unresolved':['Standard unknown']}],
        'conditional_alternatives':[{'condition':'If A','consequence':'Then B'}]}],
        'reading_account':[{'explanation':'Rival account'}],
        'tool_account':[{'explanation':'Tool account','limitation':'Supplied warrant',
                         'adapter_accounts':[{'effect_on_answer':'No added conclusion','limitation':'Finite profile'}]}]}
    texts = {r['text'] for r in answer_evidence.catalog(value)['fields'].values()}
    assert {'Condition A','Standard unknown','If A','Then B','Rival account','No added conclusion'} <= texts


def test_synthesis_binding_cannot_be_stripped_before_review(prepared):
    root, directory, ref, args, original = prepared
    result = whole.propose(root, ref, FunctionProvider(receipt), directory/'binding-review', **args)
    assert result['status'] == 'STRUCTURALLY_VALID_PROPOSAL'
    proposal = loads((directory/'binding-review/answer-proposal.json').read_bytes())
    synthesis = loads((directory/'binding-review/synthesis-request.json').read_bytes())
    proposal['interaction_hash'] = '0'*64
    with pytest.raises(LegalMathError):
        whole.prepare_answer_review(original, proposal, synthesis_request_value=synthesis)


def small_workload(**changes):
    values = dict(pieces=1,reader_claims=[2,2],selected_claims=2,all_claims=4,
                  candidates=1,formalized_candidates=1,dossier_groups=4)
    values.update(changes)
    return workload(**values)


@pytest.mark.parametrize('kind', ['settled','unknown','shared'])
def test_guarded_consumer_retains_failure_and_only_continues_settled_local_work(prepared, monkeypatch, kind):
    root,directory,ref,args,original = prepared
    partition = whole.partition
    def groups(value, **kwargs):
        result = partition(value, **kwargs); ids = list(result['registry']['records']); middle=len(ids)//2
        result['batches']=[ids[:middle],ids[middle:]]
        return result
    monkeypatch.setattr(whole,'partition',groups)
    calls=[]
    def respond(request):
        calls.append(request)
        if len(calls)==1:
            if kind=='settled': raise SettledProviderFailure('Controlled completed dispatch')
            if kind=='unknown': raise OSError('Connection lost; outcome unknown')
            raise LegalMathError('E_INTEGRITY',details='Shared source changed')
        return receipt(request)
    work = small_workload(); provider=FunctionProvider(respond)
    guard=RouteBudgetProvider(provider,directory/('budget-'+kind),work,work['stages'],
        (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),continue_settled_failures=True)
    result=whole.propose(root,ref,guard,directory/('guarded-'+kind),**args,
        dispatch_guard=guard.check,continue_independent_reviews=True)
    assert len(calls)==(2 if kind=='settled' else 1)
    assert result['completed_reviews']==(1 if kind=='settled' else 0)
    assert result['status']=='REJECTED' and result['failed_reviews'][0]['group']==0
    ledger=loads(guard.path.read_bytes());assert len(ledger['calls'])==len(calls)
    assert ledger['calls'][0]['status']==('SETTLED_FAILED' if kind=='settled' else 'FAILED')
    if kind=='settled':
        guard.check()
        from legalmath.interpretation.search.models import Settings
        with pytest.raises(LegalMathError) as error:
            guard.complete(calls[0],{},Settings())
        assert 'silently redispatched' in error.value.details
        assert len(calls)==2


def test_shared_adapter_failure_is_not_downgraded_to_optional(monkeypatch,tmp_path):
    backend=IndependentProductToolBackend(['legalruleml','logical-english']);seen=[]
    def fail(tool,*args):
        seen.append(tool);raise LegalMathError('E_INTEGRITY',details='Changed common evidence')
    monkeypatch.setattr(backend,'_run_one',fail)
    with pytest.raises(LegalMathError):backend.candidates({}, {}, tmp_path)
    assert seen==['legalruleml']


@pytest.mark.parametrize('changes,boundary', [({'candidates':17},'replay_candidates'),
    ({'candidates':16,'machine_qualification':True,'supplied_questions':True},'outer_actions'),
    ({'dossier_groups':65},'dossier_groups')])
def test_declared_workload_rejects_actual_runtime_impossibility(changes,boundary):
    work=small_workload(**changes)
    result=admission(work,{k:1000 for k in work['stages']},deadline_utc='2099-01-01T00:00:00+00:00')
    assert not result['admitted'] and boundary in {r['boundary'] for r in result['failures']}


def test_complete_raw_policy_carries_unlinked_exception(prepared):
    original=deepcopy(prepared[4])
    original['unlinked_material']={'text':'Matching copies may share an omitted holder; agreement alone is insufficient.'}
    prepared_value=whole.partition(original);prepared_value['raw_evidence_policy']='complete'
    reviews=[receipt(whole.review_request(prepared_value['registry'],g)) for g in prepared_value['batches']]
    req=whole.interaction_request(original,prepared_value,reviews)
    final=whole.synthesis_request(original,prepared_value,reviews,receipt(req))
    assert {r['record_id'] for r in final['dependency_records']}==set(prepared_value['registry']['records'])
    raw = whole.expand_dependencies(final)
    assert raw == [whole.expanded_record(prepared_value['registry'], r)
                   for r in prepared_value['registry']['records'].values()]
    assert 'Matching copies may share' in json.dumps(raw)


@pytest.mark.parametrize('consumer_profile,invalid_review', [
    ('literal',False),('answer-shared-context.v1',False),('answer-shared-context.v1',True)],
    ids=['literal','shared','invalid-review'])
def test_selected_complete_product_invokes_all_native_tools_and_executes_bound_review(consumer_profile,invalid_review):
    retained = os.environ.get('LEGAL_COMPLETION_PRODUCT_EVIDENCE')
    context = nullcontext(retained) if retained else tempfile.TemporaryDirectory(prefix='completion-product-',dir=ROOT/'artifacts')
    with context as td:
        directory=Path(td) / (consumer_profile + ('-invalid-review' if invalid_review else '')) if retained else Path(td)
        directory.mkdir(parents=True,exist_ok=True)
        questions=[{'question_id':'gift','text':'Selected gift control'}]
        save(directory/'acceptance.json',{'profile':'product-answer-acceptance.v1',
            'original_questions':questions,'acceptance_obligations':[{'id':'gift-exception','question_ids':['gift']}],
            'cases':[{'case_id':'gift-case','question_ids':['gift'],'facts':{'exception':True}}],
            'source_documents':[]})
        work=small_workload(tool_enabled=True,original_question_count=1,dossier_groups=8,answer_review_calls=1)
        def respond(request):
            if request.get('profile') == 'answer-shared-context.v1':
                from legalmath.interpretation.assurance.answer_transport import decode
                request = decode(request, expected_request_hash=request['request_hash'])
            if request['task'] == 'REVIEW_GROUNDED_PRODUCT_ANSWER':
                if invalid_review:
                    return {'verdict':'UNRESOLVED','findings':[]}
                return {'binding_hash':request['binding_hash'],'verdict':'UNRESOLVED',
                    'findings':[{'id':r['id'],'status':'UNRESOLVED','references':[], 'source_support':[],
                                 'reason':'Scripted fixture; no legal assessment.'} for r in request['requirements']]}
            if request['task'] not in {'REVIEW_DOSSIER_EVIDENCE','REVIEW_DOSSIER_INTERACTIONS','SYNTHESIZE_WHOLE_DOSSIER_ANSWER'}:
                return complete_responder(request)
            result = receipt(request)
            if request['task'] == 'SYNTHESIZE_WHOLE_DOSSIER_ANSWER':
                for row in result['tool_account']:
                    row['adapter_accounts'] = [{'tool_id':a['tool_id'], 'result_hash':a['result_hash'],
                        'disposition':'UNRESOLVED', 'question_ids':['gift'],
                        'effect_on_answer':'Scripted delivery control.', 'limitation':'No legal reasoning.'}
                        for a in request['tool_adapter_bindings'][row['key']]]
                result['case_assessments'] = [{'case_id':'gift-case','facts_hash':digest({'exception':True}),
                    'question_ids':['gift'],'conclusion':'Conditional fixture.','reasons':'No legal reasoning.',
                    'support':result['answers'][0]['claims'][0]['support'], 'contrary':[],
                    'assumptions':['Scripted control.'], 'unresolved':['Source warrant untested.']}]
            return result
        provider=FunctionProvider(respond)
        result=run_product(ROOT,directory/'product',provider,
            ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,sources=[source()],questions=questions,
            acceptance_ref=evidence_file(directory/'acceptance.json',ROOT),
            qualification={'limitations':['Synthetic scripted gift fixture, no legal-quality finding.'],'evidence':[]},
            required=work,deadline_utc=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),
            selected_tools=sorted(IndependentProductToolBackend.TOOL_IDS),settings=settings(),
            consumer_profile=consumer_profile,maximum_answer_output_bytes=16000,maximum_answer_fields=128,
            maximum_scoped_actions=12,scoped_rounds=1)
        assert result['investigation_complete'], result
        assert result['answer']['status']=='STRUCTURALLY_VALID_PROPOSAL',result
        if invalid_review:
            assert result['final_review']['status']=='REJECTED' and result['final_review']['error']=='ValidationError',result
        else:
            assert result['final_review']['status']=='UNRESOLVED' and result['final_review']['structurally_valid'],result
        req=loads((directory/'product/answer/answer-review-request.json').read_bytes())
        assert {r['id'] for r in req['requirements']}=={'question:gift','gift-exception','case:gift-case'}
        from legalmath.interpretation.assurance.answer_transport import decode
        requests = [decode(r,expected_request_hash=r['request_hash'])
                    if r.get('profile') == 'answer-shared-context.v1' else r for r in provider.requests]
        assert all((r.get('source_qualification') or r['context']['source_qualification'])['limitations']==[
            'Synthetic scripted gift fixture, no legal-quality finding.'] for r in requests)
        from legalmath.interpretation.assurance.optional_tools import adapter_results
        checks=req['context']['investigation']['optional_tools']['checks']
        assert {r['tool_id'] for c in checks for r in adapter_results(c)}==IndependentProductToolBackend.TOOL_IDS


def test_complete_product_requires_review_budget_before_dispatch(tmp_path):
    provider = FunctionProvider(lambda request: pytest.fail('Unreserved review reached provider'))
    with tempfile.TemporaryDirectory(prefix='review-admission-', dir=ROOT/'artifacts') as td:
        with pytest.raises(LegalMathError) as caught:
            run_product(ROOT, td, provider, ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
                sources=[source()], questions=[{'question_id':'gift','text':'Gift control'}],
                acceptance_ref={}, qualification={}, required=small_workload(),
                deadline_utc='2099-01-01T00:00:00+00:00', selected_tools=[], settings=settings())
    assert caught.value.code == 'E_AUTHORITY'
    assert not provider.requests


def test_shared_product_rejects_unqualified_consumer_reservation_before_investigation():
    provider = FunctionProvider(lambda request: pytest.fail('Unqualified consumer reached investigation'))
    with tempfile.TemporaryDirectory(prefix='consumer-admission-', dir=ROOT/'artifacts') as td:
        directory=Path(td)
        questions=[{'question_id':'gift','text':'Gift control'}]
        save(directory/'acceptance.json', {'profile':'product-answer-acceptance.v1',
            'original_questions':questions, 'acceptance_obligations':[{'id':'control','question_ids':['gift']}],
            'cases':[], 'source_documents':[]})
        with pytest.raises(LegalMathError) as caught:
            run_product(ROOT,directory/'product',provider,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
                sources=[source()],questions=questions,acceptance_ref=evidence_file(directory/'acceptance.json',ROOT),
                qualification={'limitations':['Synthetic fixture.'],'evidence':[]},
                required=small_workload(answer_review_calls=1),deadline_utc='2099-01-01T00:00:00+00:00',
                selected_tools=[],settings=settings(),consumer_profile='answer-shared-context.v1',
                maximum_answer_output_bytes=200000,maximum_answer_fields=10000,
                maximum_scoped_actions=12,scoped_rounds=1)
        assert caught.value.code=='E_RESOURCE_LIMIT' and caught.value.details['stage']=='MINIMUM_FINAL_REVIEW'
        assert not provider.requests
        assert not loads((directory/'product/minimum-consumer-preflight.json').read_bytes())['admitted']
