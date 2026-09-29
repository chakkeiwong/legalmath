from copy import deepcopy
from legalmath.interpretation.assurance.challenges import source_challenges,run_source_challenges,meaning_sensitive_change,executable_campaign
from legalmath.interpretation.search.formal import Comparisons
from .support import packet,reading
from tests.search.test_formal import AT


def test_source_challenges_distinguish_material_edits_and_harmless_controls():
    p=packet();p['units'][0]['text']='The bank must report at least 6 events (other than internal events) from 2026-06-01.'
    suite=run_source_challenges(p,meaning_sensitive_change)
    assert suite['passed']
    assert {r['kind'] for r in suite['cases']}=={'EXCEPTION_REMOVED','MODALITY_CHANGED','THRESHOLD_CHANGED','DATE_CHANGED','WHITESPACE_CONTROL'}
    assert not suite['legal_accuracy_evaluated']


def test_all_accept_and_all_reject_detectors_both_fail():
    p=packet();p['units'][0]['text']='A bank must comply (other than exempt banks).'
    assert not run_source_challenges(p,lambda a,b:False)['passed']
    assert not run_source_challenges(p,lambda a,b:True)['passed']


def test_exception_mutant_has_an_original_java_counterexample(root,tmp_path):
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    r=executable_campaign(reading(),packet(),checker)
    omission=next(x for x in r['mutants'] if x['kind']=='EXCEPTION_OMITTED')
    assert omission['behavior_changed']
    assert omission['comparison']['replays'][0]['java']['status'] != omission['comparison']['replays'][1]['java']['status']
