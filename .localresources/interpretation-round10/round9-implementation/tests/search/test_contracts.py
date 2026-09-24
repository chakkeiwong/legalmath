from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import validate_generation, commitment, generation_request, Settings
from tests.search.support import generation, packet


def test_valid_response_and_initial_context_separation():
    assert validate_generation(generation(),packet())['readings']
    a=generation_request(packet(),'normative');b=generation_request(packet(),'alternatives')
    assert a['parent'] is None and b['parent'] is None and a['diagnostics']==b['diagnostics']==[]
    assert 'readings' not in a['source_packet']


@pytest.mark.parametrize('defect',['quote','authority','missing_dimension','missing_unit','duplicate','fact_ref'])
def test_untrusted_response_rejected(defect):
    value=generation()
    if defect=='quote':value['readings'][0]['citations'][0]['quote']='greater than six'
    if defect=='authority':value['release_eligible']=True
    if defect=='missing_dimension':value['dimensions'].pop()
    if defect=='missing_unit':value['coverage']=[]
    if defect=='duplicate':value['readings']*=2
    if defect=='fact_ref':value['readings'][0]['formalization']['facts'][0]['source_unit_ids']=['missing']
    with pytest.raises(LegalMathError):validate_generation(value,packet())


def test_equivalent_formula_does_not_merge_different_fact_meanings():
    a=generation()['readings'][0];b=deepcopy(a)
    b['formalization']['facts'][0]['meaning']='Thirty-day approximations'
    assert commitment(a)!=commitment(b)


def test_unbounded_settings_rejected():
    from pydantic import ValidationError
    for kwargs in ({'max_model_calls':999},{'exploration_weight_milli':float('nan')},{'max_depth':0}):
        with pytest.raises(ValidationError):Settings(**kwargs)
