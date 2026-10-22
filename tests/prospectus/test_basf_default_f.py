from copy import deepcopy

import pytest

from legalmath.prospectus.basf_default_f import analyze, comparison
from scripts.prospectus_default_f_scenarios import cases,EXPECTED


@pytest.mark.parametrize('scenario',cases(),ids=lambda r:r['id'])
def test_declared_temporal_causal_notice_and_conflict_effects(scenario):
    before=deepcopy(scenario);r=analyze(scenario)
    actual=([v['modeled_f_exercise']['status'] for v in r['readings'].values()],
            [v['bc_quorum_condition_at_receipt']['status'] for v in r['readings'].values()])
    assert actual==EXPECTED[scenario['id']]
    assert r['selected_reading'] is None and not r['actual_event_established'] and scenario==before


@pytest.mark.parametrize('change',['actual','typo-time','number','expected-answer'])
def test_unsupported_or_mislabeled_facts_cannot_disappear(change):
    s=cases()[2]
    if change=='actual':s['kind']='ACTUAL_TRANSACTION'
    elif change=='typo-time':s['facts']['reciept.cessation']=True
    elif change=='number':s['facts']['exercise.cessation']=1
    else:s['facts']['expected_answer']='YES'
    with pytest.raises(ValueError):analyze(s)


def test_agreement_is_separate_from_unknown_or_conflict():
    assert comparison(['YES','YES','YES'])=='ALL_ENUMERATED_YES'
    assert comparison(['NO','YES','YES'])=='DIFFERENT_ENUMERATED_DECISIONS'
    assert comparison(['UNKNOWN','YES','YES'])=='UNRESOLVED_WITHIN_ENUMERATED_READINGS'
    assert comparison(['CONFLICT','YES','YES'])=='CONFLICT_IN_ENUMERATED_READINGS'
