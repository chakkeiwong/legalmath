from copy import deepcopy
import json
import pytest
from jsonschema import ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_references as refs
from legalmath.interpretation.assurance.phased import context_references as exact
from legalmath.interpretation.assurance.phased import context_disposition as context
from tests.assurance.test_context_need_disposition import setup, checked
from tests.assurance.test_source_review_repair import product


def prepared(tmp_path, kinds=('SOURCE_TEXT', 'CLIENT_FACT')):
    args = setup(tmp_path, kinds)
    request = deepcopy(args[4])
    request[exact.FIELD] = exact.PROFILE
    binding = refs.prepare(request, args[5])
    wire = dict(considered={'c0': binding['request']['required_considered'][0]},
        reason='The conditional consequences preserve missing information.',
        source_gaps=[], assertion_bindings=[], context_needs=[],
        need_dispositions=[dict(need_id=r['need_id'],
            disposition='SUPPLIED_SOURCE' if r['route'] == 'SOURCE_TEXT' else 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER',
            reason='The consequence is expressly conditional.',
            answer_evidence={'answer_field':'/conclusion'}, support=[{'span_id':0}])
            for r in args[6]],
        review=dict(verdict='ACCEPT', issues=[], support=[{'span_id':0}]))
    return args, binding, wire


def decode_validate(args, binding, wire, maximum_bytes=100000):
    value = refs.resolve(wire, binding, maximum_bytes=maximum_bytes)
    checked(args, value)
    return value


def test_real_transport_roundtrip_and_optional_identity(tmp_path):
    args, binding, wire = prepared(tmp_path)
    value = decode_validate(args, json.loads(json.dumps(binding,sort_keys=True)), wire)
    assert all(d['answer_evidence']['quote'] == args[2]['conclusion'] for d in value['need_dispositions'])
    p = product(tmp_path/'opt', context_reference_profile=exact.PROFILE)
    assert json.loads((p.directory/'identity.json').read_text())['context_reference_profile'] == exact.PROFILE


def test_exact_prior_needs_restored_without_fuzzy_matching(tmp_path):
    args, binding, wire = prepared(tmp_path, ('SOURCE_TEXT','SOURCE_TEXT'))
    # Two distinct needs can point at the same source without being merged.
    request = deepcopy(binding['original_request'])
    request['payload']['prior_needs'][1]['original_need']['reason'] = 'A distinct necessary timing issue.'
    rows = request['payload']['prior_needs']
    args = (*args[:6],rows,*args[7:])
    binding = refs.prepare(request, args[5])
    wire['review']['verdict'] = 'UNRESOLVED'
    for d in wire['need_dispositions']:
        d['disposition'] = 'STILL_REQUIRED'
        d['answer_evidence'] = {'answer_field':''}
    value = decode_validate(args,binding,wire)
    assert value['context_needs'] == [r['original_need'] for r in rows]
    assert value['context_needs'][0] != value['context_needs'][1]


@pytest.mark.parametrize('damage',['false_quote','unknown_path','stale_answer','duplicate','lost',
    'delivery_waiver','fact_from_source','unsupported','expansion_limit','foreign_source'])
def test_adverse_controls(tmp_path, damage):
    args,binding,wire = prepared(tmp_path)
    if damage == 'false_quote':
        wire['need_dispositions'][0]['answer_evidence'] = {'path':'/conclusion','quote':'Invented.'}
    elif damage == 'unknown_path': wire['need_dispositions'][0]['answer_evidence']['answer_field']='/absent'
    elif damage == 'stale_answer': binding['original_request']['payload']['answer']['conclusion'] += 'changed'
    elif damage == 'duplicate': wire['need_dispositions'][1]=deepcopy(wire['need_dispositions'][0])
    elif damage == 'lost': wire['need_dispositions'].pop()
    elif damage == 'delivery_waiver': args[7]['need-0']={'status':'FAILED'}
    elif damage == 'fact_from_source': wire['need_dispositions'][1]['disposition']='SUPPLIED_SOURCE'
    elif damage == 'unsupported': wire['need_dispositions'][1]['support']=[]
    elif damage == 'foreign_source': wire['review']['support']=[{'span_id':999999}]
    with pytest.raises((LegalMathError,ValidationError)):
        decode_validate(args,binding,wire,maximum_bytes=10 if damage=='expansion_limit' else 100000)


def test_false_optional_legacy_quote_still_rejected(tmp_path):
    args=setup(tmp_path,('SOURCE_TEXT',))
    value=deepcopy(args[-1])
    value['need_dispositions'][0]['answer_evidence']['quote']='A false optional quote.'
    with pytest.raises(LegalMathError): checked(args,value)


def test_retained_failure_and_new_need_both_preserved(tmp_path):
    args,binding,wire=prepared(tmp_path,('CLIENT_FACT',))
    new=dict(kind='EXTERNAL_AUTHORITY',record_ids=[],locators=[],query='Later treatment',reason='Specific missing authority.')
    wire['context_needs']=[new]
    wire['review']['verdict']='UNRESOLVED'
    wire['need_dispositions'][0]['disposition']='STILL_REQUIRED'
    wire['need_dispositions'][0]['answer_evidence']={'answer_field':''}
    args[7]['need-0']={'status':'FAILED'}
    value=decode_validate(args,binding,wire)
    assert value['context_needs']==[args[6][0]['original_need'],new]


@pytest.mark.parametrize('damage',['bad_hash','assignment_as_source','fact_with_source','authority_with_locator'])
def test_new_need_schema_rejects_foreign_identity_and_type(tmp_path,damage):
    from jsonschema import validate
    args,binding,wire=prepared(tmp_path)
    wire['review']['verdict']='UNRESOLVED'
    new=dict(kind='SOURCE_TEXT',record_ids=[],locators=[],query='Exact missing text',reason='Needed.')
    if damage=='bad_hash': new['locators']=[{'index_hash':'invented','locator':'P14'}]
    elif damage=='assignment_as_source': new['record_ids']=[args[1]['id']+'-dependency']
    elif damage=='fact_with_source':
        new['kind']='CLIENT_FACT';new['record_ids']=[binding['request']['required_considered'][0]]
    else:
        new['kind']='EXTERNAL_AUTHORITY';new['locators']=[{'index_hash':'invented','locator':'P14'}]
    wire['context_needs']=[new]
    with pytest.raises(ValidationError): validate(wire,binding['schema'])


def test_pipeline_preparation_selects_profile_and_measures(tmp_path):
    from tests.assurance.test_bounded_product import envelope
    args=setup(tmp_path)
    p,item,answer,initial=args[:4]
    p.context_reference_profile=exact.PROFILE
    request,shape,*_=context.prepare(p,'p14',envelope()['original_questions'][0],answer,item,initial)
    assert request[exact.FIELD]==exact.PROFILE
    p.provider.reference_transport=True
    measured=p.dispatch.measure(request,shape)
    assert measured['bytes']>0 and measured['local_tokens']>0


@pytest.mark.parametrize('use_alias',[False,True])
def test_valid_new_source_need_uses_delivered_full_identity(tmp_path,use_alias):
    args,binding,wire=prepared(tmp_path,('SOURCE_TEXT',))
    source=args[4]['records'][0]
    wire['review']['verdict']='UNRESOLVED'
    identity = next(k for k,v in binding['aliases'].items() if v==source['id']) if use_alias else source['id']
    wire['context_needs']=[dict(kind='SOURCE_TEXT',record_ids=[identity],
        locators=[],query='Inspect a further relationship.',reason='Additional source question.')]
    value=decode_validate(args,binding,wire)
    assert value['context_needs'][0]['record_ids']==[source['id']]
