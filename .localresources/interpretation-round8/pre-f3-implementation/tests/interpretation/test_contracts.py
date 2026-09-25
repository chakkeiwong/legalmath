import copy
import pytest
from legalmath.interpretation.contracts import policy, reference_policy, validate
from legalmath.errors import LegalMathError

@pytest.mark.parametrize('change',[{'surprise':1},{'production_default':True},{'max_actions_total':True},{'max_initial_actions':1},{'max_actions_total':3},{'max_candidates':1000000},{'mandatory_checks':['report-integrity']},{'use':'PAID_RUN','token_cap':10,'cost_cap_minor_units':10,'billing_currency':'HKD'}])
def test_reject_unsafe_policies(change):
    with pytest.raises(LegalMathError): policy({**reference_policy(),**change})

def test_packaged_schema_matches_monograph(root):
    from pathlib import Path
    for p in (root/'docs/monograph/contracts').glob('*.schema.json'):
        assert p.read_bytes()==(root/'src/legalmath/schemas'/('interpretation-'+p.name)).read_bytes()

def test_run_validation_and_date(run):
    validate('run',run)
    with pytest.raises(LegalMathError): validate('run',{**run,'created_at':'2026-02-31T00:00:00.000000Z'})
