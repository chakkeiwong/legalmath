from copy import deepcopy
import pytest
from scripts import prospectus_residual_coverage as runner
from scripts import prospectus_residual_oracle as oracle
from legalmath.prospectus import residual_coverage as module
from legalmath.prospectus.successor.contracts import digest


@pytest.fixture(scope='module')
def retained():
    products,answer=runner.baseline()
    profile=runner.read(runner.PREP/'profile.json')
    return products,answer,profile


def test_complete_source_reconciliation_and_input_preservation(retained):
    products,answer,profile=retained
    before=digest({'products':products,'answer':answer,'profile':profile})
    expected=oracle.predict(products,answer)
    result=module.evaluate(products,answer,profile,runner.ROOT,expected_profile_sha256=digest(profile))
    assert {k:result[k] for k in expected}==expected
    assert len(result['heading_units'])==24 and len(result['substantive_pending'])==7
    assert result['heading_nonspace_characters']+result['unresolved_nonspace_characters']==960
    assert result['H43']['status']=='SOURCE_EDITION_AND_APPLICATION_OPEN'
    assert not result['statutory_profile_is_exhaustive']
    assert not result['legal_scope_resolved'] and not result['whole_task_complete']
    assert digest({'products':products,'answer':answer,'profile':profile})==before


@pytest.mark.parametrize('change',['remove','duplicate','broaden','context','H43','completion'])
def test_profile_mutation_is_refused_even_when_caller_repins(retained,change):
    products,answer,original=retained;profile=deepcopy(original)
    if change=='remove':profile['headings'].pop()
    elif change=='duplicate':profile['headings'][0]=deepcopy(profile['headings'][1])
    elif change=='broaden':profile['headings'][0]['spans'][-1]['end']+=4
    elif change=='context':profile['headings'][0]['contexts'][-1]['text']+=' changed'
    elif change=='H43':profile['h43']['source_pieces']=[]
    else:profile['whole_task_complete']=True
    with pytest.raises(ValueError,match='Registered coverage'):
        module.evaluate(products,answer,profile,runner.ROOT,expected_profile_sha256=digest(profile))
