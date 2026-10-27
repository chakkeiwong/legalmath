from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import corpus_components as part
from tests.assurance.test_baseline_corpus_repairs import corpus_setup, put

def setup(root):
    full,bundle=corpus_setup(root)
    expected={k:v for k,v in full.items() if k!='answers'}
    expected['profile']=part.PROFILE
    def component(kind,row):
        value={k:bundle[k] for k in ('scope','as_of','reviewer','review_note')}
        value.update(profile=part.PROFILE,kind=kind,context_hash=digest(expected),review=deepcopy(row))
        return value
    source=component('source',bundle['applicability'][0])
    for duty in ('applicability','later_treatment'):
        source['review'][duty]['search_evidence']=[bundle['review_note']]
    answer=component('answer',bundle['answer_use'][0])
    return expected,source,answer

def test_sources_and_one_answer_run_without_other_answers(tmp_path):
    e,s,a=setup(tmp_path)
    sr=put(tmp_path,'source-review.json',s);ar=put(tmp_path,'answer-review.json',a)
    assert part.source_review(tmp_path,e,sr)['qualified']
    assert part.answer_review(tmp_path,e,a['review']['answer'],ar)['qualified']
    result=part.aggregate(tmp_path,e,{'s':sr},{a['review']['question']:{'answer':a['review']['answer'],'review':ar}})
    assert len(result['remaining'])==3
    assert not result['corpus_acceptance_complete']

def test_limitations_complete_research_but_do_not_qualify(tmp_path):
    e,s,_=setup(tmp_path);s['review']['later_treatment']['status']='UNRESOLVED'
    result=part.source_review(tmp_path,e,put(tmp_path,'review.json',s))
    assert result['review_complete'] and not result['qualified']
    assert result['status']=='REVIEWED_WITH_LIMITATIONS'

@pytest.mark.parametrize('damage',['scope','hash','date','source','quote','search','note'])
def test_source_integrity_controls(tmp_path,damage):
    e,s,_=setup(tmp_path)
    if damage=='scope':s['scope']='Changed'
    elif damage=='hash':s['context_hash']='0'*64
    elif damage=='date':s['as_of']='2026-10-26T00:00:00Z'
    elif damage=='source':s['review']['source_id']='foreign'
    elif damage=='quote':s['review']['applicability']['primary_evidence'][0]['quote']='Invented'
    elif damage=='search':s['review']['later_treatment']['search_evidence']=[]
    else:s['review_note']=put(tmp_path,'empty.md','')
    with pytest.raises(LegalMathError):part.source_review(tmp_path,e,put(tmp_path,'review.json',s))

def test_stale_answer_and_missing_propositions_rejected(tmp_path):
    e,_,a=setup(tmp_path)
    with pytest.raises(LegalMathError):
        part.answer_review(tmp_path,e,put(tmp_path,'changed.json',{'answer':'Changed'}),put(tmp_path,'review.json',a))
    a['review']['propositions']=[]
    with pytest.raises(LegalMathError):part.answer_review(tmp_path,e,a['review']['answer'],put(tmp_path,'review2.json',a))

def test_final_bridge_requires_all_original_answers(tmp_path):
    e,_,a=setup(tmp_path)
    with pytest.raises(LegalMathError):part.final_context(tmp_path,e,{a['review']['question']:a['review']['answer']})

def test_consume_components_preserves_fidelity_and_final_block(tmp_path):
    from legalmath.interpretation.assurance import corpus_review as corpus
    e,s,_=setup(tmp_path)
    sr=put(tmp_path,'source.json',s)
    registration=dict(expected_context=put(tmp_path,'context.json',e),components=put(tmp_path,'parts.json',
        dict(profile=part.PROFILE,context_hash=digest(e),sources={'s':sr},answers={})))
    fidelity=corpus.read(tmp_path,e['fidelity'])
    outcome=part.consume(tmp_path,registration,fidelity=fidelity,reconciled_sources=e['sources'])
    assert outcome['status']=='BLOCKED' and len(outcome['components'])==1
    assert not outcome['corpus_acceptance_complete']
    with pytest.raises(LegalMathError):
        part.consume(tmp_path,registration,fidelity={**fidelity,'changed':True},reconciled_sources=e['sources'])
