from copy import deepcopy
from hashlib import sha256
import json
import pytest
from jsonschema import ValidationError
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_references as refs, corpus_review as corpus
from legalmath.interpretation.assurance.phased import correction_input as gaps, warrant_references as warrants
from legalmath.interpretation.assurance.phased import review_repair, context_disposition
from tests.assurance.test_source_review_repair import product
from tests.assurance.test_bounded_product import envelope

def gap_request():
    values = [{'index_hash':'a'*64, 'locator':'P14', 'status':'NOT_VERIFIED_IN_DELIVERED_RECORDS'},
              {'index_hash':'b'*64, 'locator':'P15', 'status':'NOT_VERIFIED_IN_DELIVERED_RECORDS'}]
    return {gaps.FIELD:gaps.PROFILE, 'task':'CORRECT_REVIEWED_ANSWER',
        'downstream_input_profile':'exact-downstream-input-32k.v1',
        'payload':{'retained_source_gaps':values*50, 'original':{'conclusion':'Unknown.'}}}

def test_gap_encoding_preserves_every_occurrence_and_other_fields():
    request = gap_request()
    packed = gaps.pack(request)
    assert gaps.TABLE in packed and len(packed[gaps.TABLE]['values']) == 2
    assert gaps.expand(json.loads(json.dumps(packed))) == request
    assert len(packed['payload']['retained_source_gaps']['gap_occurrences']) == 100
    assert request == gap_request()

@pytest.mark.parametrize('damage',['negative','boolean','missing','reorder','change','unused','instructions','profile','task'])
def test_gap_corruption_rejected(damage):
    packed = gaps.pack(gap_request())
    indices = packed['payload']['retained_source_gaps']['gap_occurrences']
    if damage == 'negative': indices[0] = -1
    elif damage == 'boolean': indices[0] = False
    elif damage == 'missing': indices.pop()
    elif damage == 'reorder': indices[0],indices[1] = indices[1],indices[0]
    elif damage == 'change': packed[gaps.TABLE]['values'][0]['status'] = 'RESOLVED'
    elif damage == 'unused': packed[gaps.TABLE]['values'].append({'new':True})
    elif damage == 'instructions': packed[gaps.TABLE]['instructions'] += 'Changed.'
    elif damage == 'profile': packed[gaps.FIELD] = 'wrong'
    else: packed['task'] = 'OTHER'
    with pytest.raises(LegalMathError): gaps.expand(packed)

def warrant_setup(tmp_path):
    p = product(tmp_path, warrant_reference_profile=warrants.PROFILE, correction_input_profile=gaps.PROFILE)
    records = [r for r in p.route.records.values() if r['kind']=='source']
    answer = {'conclusion':'The claim is conditional; the facts remain unknown.'}
    request = p.request('ASSESS_REVIEW_WARRANT',envelope()['original_questions'][0],records,
        payload={'answer':answer,'issues':[{'id':'issue-0','text':'Test the condition.'}]}, expected=['review-0'])
    request[warrants.FIELD] = warrants.PROFILE
    shape = review_repair.warrant_schema(answer)
    binding = refs.prepare(request,shape)
    wire = {'considered':{'c0':binding['request']['required_considered'][0]}, 'source_gaps':[],
        'assertion_bindings':[], 'decisions':[{'issue_id':'issue-0','disposition':'WARRANTED',
        'basis':'DELIVERED_SOURCE','reason':'A conditional term needs correction.',
        'support':[{'span_id':0}], 'blocking_source_gaps':[], 'correction_target':'ANSWER_DEFECT',
        'answer_evidence':{'answer_field':'/conclusion'}}]}
    return p,request,binding,wire

def test_warrant_real_reference_roundtrip_and_product_identity(tmp_path):
    p,request,binding,wire = warrant_setup(tmp_path)
    result = refs.resolve(wire,json.loads(json.dumps(binding,sort_keys=True)),maximum_bytes=100000)
    evidence = result['decisions'][0]['answer_evidence']
    assert evidence == {'path':'/conclusion','quote':request['payload']['answer']['conclusion']}
    context_disposition.answer_quote(request['payload']['answer'],**evidence)
    identity = json.loads((p.directory/'identity.json').read_text())
    assert identity[warrants.FIELD] == warrants.PROFILE and identity[gaps.FIELD] == gaps.PROFILE
    correction = p.request('CORRECT_REVIEWED_ANSWER',envelope()['original_questions'][0],[],
        payload=gap_request()['payload'],expected=[])
    assert correction[gaps.FIELD] == gaps.PROFILE

@pytest.mark.parametrize('damage',['foreign_path','free_quote','stale_answer','issue','duplicate','lost',
    'empty_warrant','unknown_settled_target','blocking_gap'])
def test_warrant_invalid_evidence_or_population_rejected(tmp_path,damage):
    p,request,binding,wire = warrant_setup(tmp_path)
    row = wire['decisions'][0]
    if damage == 'foreign_path': row['answer_evidence']['answer_field'] = '/foreign'
    elif damage == 'free_quote': row['answer_evidence'] = {'path':'/conclusion','quote':'invented'}
    elif damage == 'stale_answer': binding['original_request']['payload']['answer']['conclusion'] += 'Changed.'
    elif damage == 'issue': row['issue_id'] = 'foreign'
    elif damage == 'duplicate': wire['decisions'].append(deepcopy(row))
    elif damage == 'lost': wire['decisions'] = []
    elif damage == 'empty_warrant': row['answer_evidence']['answer_field'] = ''
    elif damage == 'unknown_settled_target':
        row['correction_target']='UNDETERMINED'; row['disposition']='UNWARRANTED'
    else: row['blocking_source_gaps']=[{'gap_id':'not-delivered'}]
    with pytest.raises((LegalMathError,ValidationError)):
        result = refs.resolve(wire,binding,maximum_bytes=100000)
        e=result['decisions'][0]['answer_evidence']
        context_disposition.answer_quote(request['payload']['answer'],e['path'],e['quote'])

def put(root,name,value):
    path=root/name
    data=json.dumps(value).encode() if not isinstance(value,str) else value.encode()
    path.write_bytes(data)
    return {'path':name,'sha256':sha256(data).hexdigest()}

def corpus_setup(root):
    source=put(root,'source.txt','Exact source provision.')
    fidelity=put(root,'fidelity.json',{'fidelity_reconciled':True,'evidence':[source]})
    expected={'profile':corpus.PROFILE,'scope':'Original four conditional questions',
        'as_of':'2026-10-15T00:00:00+08:00','sources':{'s':source},'fidelity':fidelity,
        'answers':{q:put(root,q+'.json',{'answer':'Conditional'}) for q in corpus.QUESTIONS},
        'required_propositions':{q:['proposition-1'] for q in corpus.QUESTIONS}}
    h=digest(expected)
    support=[{'source_id':'s','source':source,'passage':source,'locator':'Clause 1','quote':'Exact source provision.'}]
    finding={'status':'QUALIFIED','finding':'Explicit scoped reviewer conclusion.','primary_evidence':support}
    note=put(root,'review.md','Fixture review: exercises evidence plumbing, not legal truth.')
    bundle={'profile':corpus.PROFILE,'context_hash':h,'scope':expected['scope'],'as_of':expected['as_of'],
        'reviewer':'Test fixture reviewer','review_note':note,
        'applicability':[{'source_id':'s','source':source,'scope':expected['scope'],'as_of':expected['as_of'],
        'version':'Fixture version','applicability':deepcopy(finding),'later_treatment':deepcopy(finding)}],
        'answer_use':[{'question':q,'answer':expected['answers'][q],'propositions':[{'id':'proposition-1',
        'status':'SUPPORTED','reason':'Fixture scoped review.','source_ids':['s'],'primary_evidence':support,
        'answer_evidence':[{'path':'/answer','quote':'Conditional'}]}]}
        for q in sorted(corpus.QUESTIONS)],
        'controls':{k:put(root,k+'.json',{'context_hash':h,'control':k,'expected':v,'observed':v,
        'execution_evidence':note}) for k,v in corpus.CONTROLS.items()}}
    return expected,bundle

def test_corpus_complete_fixture_and_real_missing_bundle_stays_blocked(tmp_path):
    expected,bundle=corpus_setup(tmp_path)
    missing=corpus.evaluate(tmp_path,expected)
    assert missing['status']=='BLOCKED' and len(missing['remaining'])==6
    result=corpus.evaluate(tmp_path,expected,put(tmp_path,'bundle.json',bundle))
    assert result['status']=='SUCCEEDED' and not result['legal_correctness_established']

@pytest.mark.parametrize('damage',['stale','date','scope','missing_source','duplicate','missing_answer',
    'proposition','no_support','false_quote','wrong_source','missing_control','wrong_control','tamper',
    'stale_answer','empty_review','empty_control'])
def test_corpus_rejects_missing_stale_or_fabricated_evidence(tmp_path,damage):
    expected,bundle=corpus_setup(tmp_path)
    if damage=='stale': bundle['context_hash']='0'*64
    elif damage=='date': bundle['as_of']='2026-10-26T00:00:00+08:00'
    elif damage=='scope': bundle['scope']='Different question'
    elif damage=='missing_source': bundle['applicability']=[]
    elif damage=='duplicate': bundle['applicability']*=2
    elif damage=='missing_answer': bundle['answer_use'].pop()
    elif damage=='proposition': bundle['answer_use'][0]['propositions']=[]
    elif damage=='no_support': bundle['applicability'][0]['later_treatment']['primary_evidence']=[]
    elif damage=='false_quote': bundle['answer_use'][0]['propositions'][0]['primary_evidence'][0]['quote']='Invented.'
    elif damage=='wrong_source': bundle['answer_use'][0]['propositions'][0]['primary_evidence'][0]['source_id']='other'
    elif damage=='missing_control': del bundle['controls']['false_attribution']
    elif damage=='stale_answer': bundle['answer_use'][0]['answer']=put(tmp_path,'stale.json',{'answer':'Different'})
    elif damage=='empty_review': bundle['review_note']=put(tmp_path,'empty.md','')
    elif damage=='empty_control':
        bundle['controls']['positive']=put(tmp_path,'empty-control.json',{'context_hash':digest(expected),
            'control':'positive','expected':'VALIDATED','observed':'VALIDATED',
            'execution_evidence':put(tmp_path,'empty.log','')})
    elif damage=='wrong_control':
        bundle['controls']['wrong_source']=put(tmp_path,'bad-control.json',{'context_hash':digest(expected),
            'control':'wrong_source','expected':'REJECTED','observed':'VALIDATED'})
    else: (tmp_path/'source.txt').write_text('Changed bytes.')
    with pytest.raises((LegalMathError,KeyError)):
        corpus.evaluate(tmp_path,expected,put(tmp_path,'bundle.json',bundle))

def test_corpus_unresolved_review_is_blocker_not_success(tmp_path):
    expected,bundle=corpus_setup(tmp_path)
    bundle['applicability'][0]['later_treatment']['status']='UNRESOLVED'
    bundle['answer_use'][0]['propositions'][0]['status']='REJECTED'
    result=corpus.evaluate(tmp_path,expected,put(tmp_path,'bundle.json',bundle))
    assert result['status']=='BLOCKED' and len(result['remaining'])==2

def test_corpus_handler_consumes_registered_expected_context(tmp_path,monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    sys.path.insert(0,'/home/chakwong/python/legalmath')
    path=Path(__file__).parents[2]/'scripts/legal_integration_qualification_continuation.py'
    spec=importlib.util.spec_from_file_location('tested_candidate_corpus_handler',path)
    handler=importlib.util.module_from_spec(spec);spec.loader.exec_module(handler)
    root=Path('/home/chakwong/python/legalmath')
    monkeypatch.setattr(handler,'ROOT',root)
    expected,bundle=corpus_setup(tmp_path)
    fidelity=json.loads((root/'artifacts/legal-mission-control/2026-10-13/master/corpus-qualification/attempt-6/corpus-reconciliation.json').read_text())
    sources={}
    for region in ('2023','2025','handbook'):
        receipt=json.loads((root/f'artifacts/legal-mission-control/2026-10-13/master/ownership-{region}/attempt-3/evidence.json').read_text())
        ownership=json.loads((root/receipt['ownership']['path']).read_text())
        sources[region]=ownership['source']
    expected.update(fidelity={'path':'fixture-fidelity.json','sha256':'fixture'},sources=sources)
    context_ref={'path':'fixture-expected.json','sha256':'fixture'}
    original_read=handler.read
    def fixture_read(path):
        if path==handler.ROOT/handler.PROGRAM:return {'corpus_review_evidence':{'expected_context':context_ref}}
        if path.name=='fixture-expected.json':return expected
        if path.name=='fixture-fidelity.json':return fidelity
        return original_read(path)
    original_verify=handler.verify
    def fixture_verify(root,reference):
        if reference.get('sha256')!='fixture':return original_verify(root,reference)
    observed=[]
    def consume(root,context,bundle=None):
        observed.append(context)
        return {'status':'BLOCKED','corpus_acceptance_complete':False,'remaining':['Explicit missing bundle']}
    monkeypatch.setattr(handler,'read',fixture_read)
    monkeypatch.setattr(handler,'verify',fixture_verify)
    original_ref=handler.ref
    monkeypatch.setattr(handler,'ref',lambda root,path: {'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}
        if Path(path).is_absolute() and Path(path).is_relative_to(tmp_path) else original_ref(root,path))
    monkeypatch.setattr(corpus,'evaluate',consume)
    result=handler.corpus(tmp_path/'registered')
    assert result['_node_status']=='BLOCKED' and observed==[expected] and 'review' in result
    expected['sources']['2023']={'path':'wrong','sha256':'wrong'}
    with pytest.raises(ValueError):handler.corpus(tmp_path/'wrong-source')

def test_product_wrapper_forwards_opt_in_profiles_before_execution(tmp_path,monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    sys.path.insert(0,'/home/chakwong/python/legalmath')
    path=Path(__file__).parents[2]/'scripts/legal_product_completion.py'
    spec=importlib.util.spec_from_file_location('candidate_product_wrapper',path)
    wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)
    from legalmath.interpretation.assurance import bounded_product, answer_acceptance
    from legalmath.interpretation.assurance.phased import context_references
    observed={}
    class ConstructorReached(Exception):pass
    def capture(*args,**kwargs):
        observed.update(kwargs)
        raise ConstructorReached()
    monkeypatch.setattr(bounded_product,'BoundedProduct',capture)
    monkeypatch.setattr(answer_acceptance,'validate_manifest',lambda *args:None)
    value=envelope()
    with pytest.raises(ConstructorReached):
        wrapper.run_product(tmp_path,tmp_path/'run',None,tmp_path,'2026-10-15',
            sources=[],questions=value['original_questions'],acceptance_ref=None,qualification={},
            required={'maximum_calls':1},deadline_utc='2026-10-27T00:00:00Z',selected_tools=[],settings=None,
            consumer_profile=bounded_product.PROFILE,bounded_envelope=value,bounded_encode=list,
            bounded_context_reference_profile=context_references.PROFILE,
            bounded_warrant_reference_profile=warrants.PROFILE,bounded_correction_input_profile=gaps.PROFILE)
    assert observed['context_reference_profile']==context_references.PROFILE
    assert observed['warrant_reference_profile']==warrants.PROFILE
    assert observed['correction_input_profile']==gaps.PROFILE
