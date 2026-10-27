from copy import deepcopy
from dataclasses import replace
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.phased import context_disposition as context, group_review, review_contract
from legalmath.interpretation.assurance.phased.context_bridge import select_context
from legalmath.interpretation.assurance.phased.source_review import assignments
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.providers import Completion
from jsonschema import ValidationError
from tests.assurance.test_source_review_repair import product, decision
from tests.assurance.test_bounded_product import envelope, Scripted


def setup(tmp_path, kinds=('SOURCE_TEXT', 'CLIENT_FACT')):
    p = product(tmp_path, review_assignment_profile=review_contract.PROFILE)
    item = assignments(p, 'p14', [])[0]
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    answer = {'conclusion': 'If a request is made, the duty applies; actual consent remains unknown.',
              'support': [dict(record_id=sources[-1]['id'], quote=sources[-1]['text'], locator='')]}
    original = decision(sources[0], 'UNRESOLVED')
    original.update(considered=[item['id']], context_needs=[dict(kind=k, reason='Necessary '+k,
        record_ids=[sources[-1]['id']] if k == 'SOURCE_TEXT' else [], locators=[], query='') for k in kinds])
    initial = dict(status='VALIDATED', value=original)
    request, shape, rows, receipts, failures = context.prepare(p, 'p14', envelope()['original_questions'][0],
        answer, item, initial)
    value = decision(sources[0])
    value.update(considered=[item['id']], need_dispositions=[dict(need_id=row['need_id'],
        disposition='SUPPLIED_SOURCE' if row['route']=='SOURCE_TEXT' else 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER',
        reason='The explicit conditional consequence does not assert actual consent.',
        answer_evidence=dict(path='/conclusion', quote=answer['conclusion']),
        support=[dict(record_id=sources[-1]['id'], quote=sources[-1]['text'], locator='')]) for row in rows])
    return p, item, answer, initial, request, shape, rows, failures, value


def checked(args, value=None):
    p, item, answer, initial, request, shape, rows, failures, expected = args
    context.validate(p, 'p14', value or expected, answer, item, rows, request['records'], failures)


@pytest.mark.parametrize('kinds', [('SOURCE_TEXT', 'CLIENT_FACT'), ('EXTERNAL_AUTHORITY',), ()])
def test_explicit_conditional_dispositions_account_for_all_need_kinds(tmp_path, kinds):
    args = setup(tmp_path, kinds)
    checked(args)
    assert args[3]['value']['verdict'] == 'UNRESOLVED'
    assert {r['id'] for r in args[4]['records']} == {
        r['id'] for r in args[0].route.records.values() if r['kind']=='source'}


@pytest.mark.parametrize('damage', ['lost', 'duplicate', 'false_quote', 'bad_path', 'unsupported_waiver',
    'invent_fact', 'invent_authority', 'unreviewed_mapping', 'necessary_accept', 'false_source'])
def test_adverse_disposition_controls(tmp_path, damage):
    args = setup(tmp_path, ('SOURCE_TEXT','CLIENT_FACT','EXTERNAL_AUTHORITY'))
    value = deepcopy(args[-1])
    dispositions = value['need_dispositions']
    if damage == 'lost': dispositions.pop()
    elif damage == 'duplicate': dispositions[1] = deepcopy(dispositions[0])
    elif damage == 'false_quote': dispositions[1]['answer_evidence']['quote'] = 'Consent is established.'
    elif damage == 'bad_path': dispositions[1]['answer_evidence']['path'] = '/absent'
    elif damage == 'unsupported_waiver': dispositions[1]['support'] = []
    elif damage == 'invent_fact': dispositions[1]['disposition'] = 'SUPPLIED_SOURCE'
    elif damage == 'invent_authority': dispositions[2]['disposition'] = 'SUPPLIED_SOURCE'
    elif damage == 'unreviewed_mapping': dispositions[0]['disposition'] = 'MAPPING_CLARIFIED'
    elif damage == 'necessary_accept': dispositions[1]['disposition'] = 'STILL_REQUIRED'
    else: dispositions[0]['support'][0]['quote'] = 'Fabricated evidence.'
    with pytest.raises((LegalMathError, ValidationError)): checked(args, value)


def test_still_required_fact_and_failed_source_selection_remain_unresolved(tmp_path):
    args = setup(tmp_path)
    value = deepcopy(args[-1])
    value['verdict'] = 'UNRESOLVED'
    value['context_needs'] = deepcopy(args[3]['value']['context_needs'])
    for row in value['need_dispositions']: row['disposition'] = 'STILL_REQUIRED'
    args[7]['need-0'] = dict(status='FAILED', reason='No eligible source')
    checked(args, value)
    value['need_dispositions'][0]['disposition'] = 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER'
    with pytest.raises(LegalMathError): checked(args, value)


def test_scope_filter_precedes_hit_limit_and_expansion(tmp_path):
    p = product(tmp_path)
    sources = [r for r in p.route.records.values() if r['kind']=='source']
    p.route.limits = replace(p.route.limits, retrieval_hits=1, window_neighbors=3)
    # The forbidden result must not occupy the single allowed hit slot.
    chosen = p.route.retrieve('consent duty', allowed_record_ids=[sources[0]['id']])
    assert chosen['hit_ids'] == chosen['record_ids'] == [sources[0]['id']]
    assert sources[-1]['id'] in chosen['scope']['excluded_record_ids']
    assert not p.route.retrieve('nonexistentlexeme', allowed_record_ids=[sources[0]['id']])['record_ids']
    assert not p.route.retrieve('duty', allowed_record_ids=[])['record_ids']


def test_explicit_foreign_request_is_not_silently_filtered(tmp_path, monkeypatch):
    p = product(tmp_path)
    item = assignments(p, 'p14', [])[0]
    sources = [r for r in p.route.records.values() if r['kind']=='source']
    monkeypatch.setattr(p, 'acquisition_questions', lambda row: ['p14'] if row==sources[0] else ['gatecoin'])
    need = dict(kind='SOURCE_TEXT', reason='Compare provision', record_ids=[sources[-1]['id']], locators=[], query='')
    with pytest.raises(LegalMathError): select_context(p, 'p14', item, [need], scoped=True)


def test_enumerated_mapping_bypasses_retrieval_and_is_bound_to_original(tmp_path, monkeypatch):
    args = setup(tmp_path, ('SOURCE_TEXT',))
    p,item,answer,initial = args[:4]
    need = initial['value']['context_needs'][0]
    need.update(record_ids=[],query='Provide the response-key mapping.')
    save(tmp_path/'mapping.json', dict(needs=[dict(assignment_id=item['id'],
        decision_hash=digest(initial['value']), need_hash=digest(need))]))
    save(tmp_path/'individual.json', dict(mapping_needs=evidence_file(tmp_path/'mapping.json', tmp_path)))
    save(tmp_path/'checkpoint.json', dict(individual_reviews=evidence_file(tmp_path/'individual.json', tmp_path)))
    p.capacity_checkpoint = evidence_file(tmp_path/'checkpoint.json', tmp_path)
    def forbidden(*a, **k): raise AssertionError('Mapping request reached source retrieval')
    monkeypatch.setattr(p.route,'retrieve',forbidden)
    request,shape,rows,receipts,failures = context.prepare(p,'p14',envelope()['original_questions'][0],answer,item,initial)
    assert rows[0]['route']=='ASSIGNMENT_MAPPING' and not receipts and not failures
    assert request['payload']['item'] == item
    value = deepcopy(args[-1])
    value['need_dispositions'][0]['disposition'] = 'MAPPING_CLARIFIED'
    context.validate(p,'p14',value,answer,item,rows,request['records'],failures)
    initial['value']['reason'] += 'changed'
    with pytest.raises(LegalMathError): context.need_rows(p,item,initial)


def test_context_dispositions_survive_real_wire_schema_and_saved_reload(tmp_path):
    args = setup(tmp_path)
    p,item,answer,initial,request,shape,rows,failures,_ = args
    binding = bounded_references.prepare(request,shape)
    reloaded = json.loads(json.dumps(binding,sort_keys=True))
    assert bounded_references.prepare(reloaded['original_request'],reloaded['original_schema']) == binding
    wire = dict(considered={'c0':binding['request']['required_considered'][0]},
        reason='The conditional consequences are stated without assuming consent.',
        source_gaps=[],assertion_bindings=[],context_needs=[],
        need_dispositions=[dict(need_id=row['need_id'],
            disposition='SUPPLIED_SOURCE' if row['route']=='SOURCE_TEXT' else 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER',
            reason='The conditional answer leaves actual consent open.',
            answer_evidence=dict(path='/conclusion',quote=answer['conclusion']), support=[dict(span_id=0)]) for row in rows],
        review=dict(verdict='ACCEPT',issues=[],support=[dict(span_id=0)]))
    value = bounded_references.resolve(wire,reloaded,maximum_bytes=100000)
    context.validate(p,'p14',value,answer,item,rows,request['records'],failures)


def test_exact_retained_authority_is_supplied_without_waiving_other_authority(tmp_path, monkeypatch):
    args = setup(tmp_path, ('EXTERNAL_AUTHORITY',))
    p,item,answer,initial = args[:4]
    need = initial['value']['context_needs'][0]
    source = [r for r in p.route.records.values() if r['kind']=='source'][-1]
    save(tmp_path/'retained.json',dict(needs=[dict(assignment_id=item['id'],
        decision_hash=digest(initial['value']),need_hash=digest(need),
        record_ids=[source['id']],reason='This exact request asks for an already-retained passage.')]))
    save(tmp_path/'individual.json',dict(retained_source_needs=evidence_file(tmp_path/'retained.json',tmp_path)))
    save(tmp_path/'checkpoint.json',dict(individual_reviews=evidence_file(tmp_path/'individual.json',tmp_path)))
    p.capacity_checkpoint=evidence_file(tmp_path/'checkpoint.json',tmp_path)
    request,shape,rows,receipts,failures=context.prepare(p,'p14',envelope()['original_questions'][0],answer,item,initial)
    assert rows[0]['route']=='SOURCE_TEXT' and rows[0]['original_need']['kind']=='EXTERNAL_AUTHORITY'
    assert not failures and source['id'] in receipts[0]['delivered_ids']
    value=deepcopy(args[-1]);value['need_dispositions'][0]['disposition']='SUPPLIED_SOURCE'
    context.validate(p,'p14',value,answer,item,rows,request['records'],failures)
    with pytest.raises(LegalMathError): checked(args,value)
    monkeypatch.setattr(p,'acquisition_questions',lambda r:['gatecoin'] if r['id']==source['id'] else ['p14'])
    _,_,_,_,failures=context.prepare(p,'p14',envelope()['original_questions'][0],answer,item,initial)
    assert failures
    initial['value']['reason'] += 'changed'
    with pytest.raises(LegalMathError): context.need_rows(p,item,initial)


def test_product_reaches_fact_only_and_untyped_continuations_once(tmp_path, monkeypatch):
    args = setup(tmp_path, ('CLIENT_FACT',))
    p,item,answer,initial = args[:4]
    second = deepcopy(initial)
    other = assignments(p,'p14',[])[1]
    second['value'].update(considered=[other['id']],context_needs=[])
    monkeypatch.setattr(group_review,'run',lambda *a,**k:deepcopy([initial,second]))
    observed=[]
    def complete(request,shape,settings):
        observed.append(request)
        rows=request['payload']['prior_needs']
        value=deepcopy(args[-1])
        value['considered']=request['required_considered']
        value['need_dispositions'][0]['need_id']=rows[0]['need_id']
        return Completion(value,{})
    p.provider.complete=complete
    reviews=p.audit_answer('p14',envelope()['original_questions'][0],answer,[])
    assert len(observed)==2 and all(r['status']=='VALIDATED' and r['value']['verdict']=='ACCEPT' for r in reviews)
    assert all(r['context_continuation']['original_review']['value']['verdict']=='UNRESOLVED' for r in reviews)
    assert p.audit_answer('p14',envelope()['original_questions'][0],answer,[])==reviews
    assert len(observed)==2


def test_warrants_include_actual_assignment_and_reuse_across_changed_group_order(tmp_path):
    args=setup(tmp_path)
    p,item,answer,initial=args[:4]
    other=assignments(p,'p14',[])[1]
    source=p.route.records[item['origin_id']]
    reject=dict(status='VALIDATED',value={**decision(source,'REJECT'),
        'considered':[item['id']],'issues':['The evidence description is inaccurate.']})
    sibling=deepcopy(reject)
    sibling['value']['considered']=[other['id']]
    seen=[]
    def complete(request,shape,settings):
        seen.append(request)
        assert request['payload']['assigned_review_targets']
        return Completion(dict(considered=request['required_considered'],source_gaps=[],assertion_bindings=[],
            decisions=[dict(issue_id=r['id'],disposition='UNWARRANTED',basis='QUESTION_SCOPE',
                reason='No such claim appears in this answer.',support=[],blocking_source_gaps=[])
                for r in request['payload']['issues']]),{})
    p.provider.complete=complete
    first=p.review_warrants('p14',envelope()['original_questions'][0],dict(value=answer),[reject],[])
    second=p.review_warrants('p14',envelope()['original_questions'][0],dict(value=answer),[sibling,reject],[])
    assert len(seen)==2 and first[2] and second[2]
    assert seen[0]['payload']['assigned_review_targets']==[item]


def test_invalid_context_canary_withholds_bulk_but_adverse_issues_run(tmp_path, monkeypatch):
    args=setup(tmp_path)
    p,item,answer,initial=args[:4]
    other=assignments(p,'p14',[])[1]
    source=p.route.records[item['origin_id']]
    reject=dict(status='VALIDATED',value={**decision(source,'REJECT'),
        'considered':[item['id']],'issues':['Check the answer evidence description.']})
    sibling=deepcopy(initial)
    sibling['value']['considered']=[other['id']]
    monkeypatch.setattr(group_review,'run',lambda *a,**k:deepcopy([reject,initial,sibling]))
    original=p.provider.complete
    def complete(request,shape,settings):
        result=original(request,shape,settings)
        if request['task']=='ASSESS_REVIEW_WARRANT':
            for row in result.value['decisions']: row['blocking_source_gaps']=[]
        return result
    p.provider.complete=complete
    reviews=p.audit_answer('p14',envelope()['original_questions'][0],answer,[])
    assert [r['task'] for r in p.provider.requests]==['ASSESS_REVIEW_WARRANT','AUDIT_EXPLICIT_DEPENDENCY_CONTEXT']
    assert reviews[-1]['context_continuation_deferred']
    assert reviews[0]['value']['verdict']=='REJECT' and reviews[1]['value']['verdict']=='UNRESOLVED'
