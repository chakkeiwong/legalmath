from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import corpus_review as corpus
from legalmath.interpretation.assurance import corpus_components as part
from tests.assurance.test_baseline_corpus_repairs import corpus_setup,put
from tests.assurance.test_corpus_components import setup

@pytest.mark.parametrize('consumer',['independent','final'])
@pytest.mark.parametrize('damage',['missing','invented','wrong_field','empty','blank',
    'wrong_type','outside','bad_escape','negative','leading_zero','scalar'])
def test_actual_consumers_reject_bad_answer_attribution(tmp_path,consumer,damage):
    if consumer=='independent':
        expected,_,review=setup(tmp_path)
        prop=review['review']['propositions'][0]
    else:
        expected,review=corpus_setup(tmp_path)
        prop=review['answer_use'][0]['propositions'][0]
    quote={'path':'/answer','quote':'Conditional'}
    if damage=='missing': prop.pop('answer_evidence')
    else:
        if damage=='invented':quote['quote']='This was never said.'
        elif damage=='wrong_field':quote['path']='/conclusion'
        elif damage=='blank':quote['quote']='  '
        elif damage=='wrong_type':quote['quote']=3
        elif damage=='outside':quote['path']='/missing/0'
        elif damage=='bad_escape':quote['path']='/~2'
        elif damage=='negative':quote['path']='/answer/-1'
        elif damage=='leading_zero':quote['path']='/answer/00'
        elif damage=='scalar':quote['path']='/answer/field'
        prop['answer_evidence']=[] if damage=='empty' else [quote]
    ref=put(tmp_path,'damaged-review.json',review)
    with pytest.raises(LegalMathError):
        if consumer=='independent':part.answer_review(tmp_path,expected,review['review']['answer'],ref)
        else:corpus.evaluate(tmp_path,expected,ref)

def test_exact_field_nested_arrays_and_json_pointer_escapes():
    answer={'a/b':{'~key':['first','Precise conditional statement.']},
        'other':'A different statement.'}
    corpus.answer_support(answer,[dict(path='/a~1b/~0key/1',quote='conditional statement')])
    for path in ('/a~1b/~0key/01','/a~1b/~0key/-1','/a~1b/~0key/2','/other'):
        with pytest.raises(LegalMathError):
            corpus.answer_support(answer,[dict(path=path,quote='conditional statement')])

def test_unresolved_omission_does_not_need_invented_positive_quote(tmp_path):
    expected,_,review=setup(tmp_path)
    prop=review['review']['propositions'][0]
    prop.update(status='UNRESOLVED',reason='Required explanation is absent.')
    prop.pop('answer_evidence')
    result=part.answer_review(tmp_path,expected,review['review']['answer'],put(tmp_path,'missing.json',review))
    assert not result['qualified'] and result['remaining']
