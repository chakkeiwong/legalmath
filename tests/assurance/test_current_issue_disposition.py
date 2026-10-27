from copy import deepcopy
from types import SimpleNamespace
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import current_issue_disposition as issue
from legalmath.interpretation.assurance.phased import retry_checkpoint as retry
from tests.assurance.test_baseline_corpus_repairs import put

def setup(root):
    original={'conclusion':'Original statement'}
    candidate={'conclusion':'If the request occurs, demonstration is required. No request is established.'}
    question={'question_id':'p14','text':'What follows conditionally?'}
    reviews=[{'status':'VALIDATED','value':{'verdict':'REJECT','issues':['Missing condition'],
        'considered':['d1']}}]
    assessments=[{'review_index':0,'original_review_hash':digest(reviews[0]),
        'result':{'status':'VALIDATED','value':{'decisions':[{'issue_id':'issue-0','disposition':'UNRESOLVED'}]}}}]
    source={'id':'s','kind':'source','text':'Demonstrate upon request.'}
    def citations(value,records):
        assert records==[source]
        for row in value['support']:
            if row['record_id']!='s' or row['quote'] not in source['text']:
                raise LegalMathError('E_INTEGRITY')
    p=SimpleNamespace(root=root,directory=root,route=SimpleNamespace(input_hash='input',records={'s':source}),
        citations=citations,acquisition_questions=lambda r:['p14'])
    value=dict(profile=issue.PROFILE,question_id='p14',question_hash=digest(question),input_hash='input',
        original_answer_hash=digest(original),current_answer_hash=digest(candidate),
        requirement_details_hash=digest([]),issue_population_hash=digest([{k:r[k] for k in
            ('id','review_index','review_hash','issue')} for r in issue.census(reviews,assessments)]),
        reviewer='Fixture reviewer',review_note=put(root,'review.md','Specific fixture review, not legal evidence.'),
        dispositions=[dict(id='0:issue-0',disposition='CONDITIONALLY_ADDRESSED',reason='States condition and unknown fact.',
            blocking_source_gaps=[],support=[{'record_id':'s','quote':source['text'],'locator':''}],
            answer_evidence={'path':'/conclusion','quote':candidate['conclusion']},
            necessary_premises=[{'description':'Request has occurred',
                'answer_evidence':{'path':'/conclusion','quote':'No request is established.'}}])])
    return p,question,original,candidate,reviews,assessments,value

def evaluate(root,damage=None):
    p,q,old,current,reviews,assessments,value=setup(root)
    if damage=='answer':current['conclusion']='Unconditional'
    elif damage=='population':value['dispositions']=[]
    elif damage=='duplicate':value['dispositions']*=2
    elif damage=='quote':value['dispositions'][0]['answer_evidence']['quote']='Invented'
    elif damage=='source':value['dispositions'][0]['support'][0]['record_id']='foreign'
    elif damage=='gap':value['dispositions'][0]['blocking_source_gaps']=[{'missing':True}]
    elif damage=='premise':value['dispositions'][0]['necessary_premises']=[]
    elif damage=='old':old['conclusion']='Changed predecessor'
    elif damage=='assessment':assessments[0]['original_review_hash']='wrong'
    elif damage=='still':value['dispositions'][0]['disposition']='STILL_REQUIRED'
    return issue.validate(p,'p14',q,old,current,[],reviews,assessments,value)

def test_reviewed_conditional_issue_is_settled_without_acceptance(tmp_path):
    r=evaluate(tmp_path)
    assert r['complete'] and not r['legal_acceptance'] and r['issue_count']==1

def test_necessary_issue_stays_pending(tmp_path):
    r=evaluate(tmp_path,'still')
    assert not r['complete'] and len(r['pending'])==1

def test_changed_supplementary_review_evidence_is_rejected(tmp_path):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    value['reviewed_evidence']=[put(tmp_path,'mapping.json',{'identity':'original'})]
    (tmp_path/'mapping.json').write_text('{}')
    with pytest.raises(LegalMathError):
        issue.validate(p,'p14',q,old,current,[],reviews,assessments,value)

def test_reassessed_warrant_does_not_change_original_issue_identity(tmp_path):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    assessments[0]['result']['value']['decisions'][0]['disposition']='WARRANTED'
    result=issue.validate(p,'p14',q,old,current,[],reviews,assessments,value)
    assert result['complete'] and not result['legal_acceptance']

@pytest.mark.parametrize('damage',['answer','population','duplicate','quote','source','gap','premise','old','assessment'])
def test_wrong_evidence_never_waives_issue(tmp_path,damage):
    with pytest.raises(LegalMathError):evaluate(tmp_path,damage)

def test_fixed_correction_caller_uses_exact_disposition_without_resampling(tmp_path,monkeypatch):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    ref=put(tmp_path,'disposition.json',value)
    p.capacity_checkpoint=put(tmp_path,'checkpoint.json',{'current_answer_issue_dispositions':{'p14':ref}})
    candidate={'status':'VALIDATED','value':current}
    held=dict(original_reviews=reviews,candidate=candidate,corrected_requirement_details=[],review_warrants=assessments)
    monkeypatch.setattr(retry,'fixed_correction',lambda *args:deepcopy(held))
    p.note=lambda *args:pytest.fail('Answer regenerated')
    p.review_warrants=lambda *args:pytest.fail('Historical warrant assessed again')
    p.audit_answer=lambda *args,**kwargs:[{'status':'VALIDATED','value':{'verdict':'ACCEPT'}}]
    p.audit_dependencies=lambda *args,**kwargs:[]
    actual,fresh,record=retry.resume_correction(p,'p14',q,{'value':old},[],[])
    assert actual==candidate and record['new_answer_calls']==0
    assert len(fresh)==1 and record['current_answer_issue_disposition']['complete']
    assert record['historical_warrant_reuse']=='AUTHENTICATED_FIXED_CORRECTION'
    assert not record['legal_acceptance']

def test_fresh_adverse_review_remains_a_blocker(tmp_path,monkeypatch):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    ref=put(tmp_path,'disposition.json',value)
    p.capacity_checkpoint=put(tmp_path,'checkpoint.json',{'current_answer_issue_dispositions':{'p14':ref}})
    candidate={'status':'VALIDATED','value':current}
    monkeypatch.setattr(retry,'fixed_correction',lambda *args:dict(original_reviews=reviews,
        candidate=candidate,corrected_requirement_details=[],review_warrants=assessments))
    p.review_warrants=lambda *args:pytest.fail('Historical warrant assessed again')
    p.audit_answer=lambda *args,**kwargs:[{'status':'VALIDATED','value':{'verdict':'REJECT'}}]
    p.audit_dependencies=lambda *args,**kwargs:[]
    _,fresh,_=retry.resume_correction(p,'p14',q,{'value':old},[],[])
    assert fresh[0]['value']['verdict']=='REJECT'

@pytest.mark.parametrize('damage',['missing_assessment','stale_answer','missing_issue'])
def test_bad_retained_disposition_fails_before_any_provider_call(tmp_path,monkeypatch,damage):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    if damage=='missing_assessment':assessments=[]
    elif damage=='stale_answer':value['current_answer_hash']='0'*64
    else:value['dispositions']=[]
    ref=put(tmp_path,'disposition.json',value)
    p.capacity_checkpoint=put(tmp_path,'checkpoint.json',{'current_answer_issue_dispositions':{'p14':ref}})
    monkeypatch.setattr(retry,'fixed_correction',lambda *args:dict(original_reviews=reviews,
        candidate={'status':'VALIDATED','value':current},corrected_requirement_details=[],review_warrants=assessments))
    p.review_warrants=lambda *args:pytest.fail('Fallback hides invalid disposition')
    p.audit_answer=lambda *args,**kwargs:pytest.fail('Fresh call before validation')
    p.audit_dependencies=p.audit_answer
    with pytest.raises(LegalMathError):retry.resume_correction(p,'p14',q,{'value':old},[],[])

def test_retained_pending_issue_stays_blocked_with_fresh_reviews(tmp_path,monkeypatch):
    p,q,old,current,reviews,assessments,value=setup(tmp_path)
    value['dispositions'][0]['disposition']='STILL_REQUIRED'
    ref=put(tmp_path,'disposition.json',value)
    p.capacity_checkpoint=put(tmp_path,'checkpoint.json',{'current_answer_issue_dispositions':{'p14':ref}})
    monkeypatch.setattr(retry,'fixed_correction',lambda *args:dict(original_reviews=reviews,
        candidate={'status':'VALIDATED','value':current},corrected_requirement_details=[],review_warrants=assessments))
    p.review_warrants=lambda *args:pytest.fail('Duplicate old warrant')
    fresh=[]
    p.audit_answer=lambda *args,**kwargs:fresh.append('answer') or []
    p.audit_dependencies=lambda *args,**kwargs:fresh.append('dependencies') or []
    _,results,_=retry.resume_correction(p,'p14',q,{'value':old},[],[])
    assert fresh==['answer','dependencies']
    assert results[-1]['status']=='FAILED' and results[-1]['assessments']
