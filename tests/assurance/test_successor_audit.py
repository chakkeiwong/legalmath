"""Evidence promotion rejects detached summaries and altered action files."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import scoped_investigation
from tests.search.support import FunctionProvider
from .test_round16 import scoped_fixture

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('successor_evidence_audit',ROOT/'scripts/assurance_successor_audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


@pytest.fixture
def evidence(tmp_path):
    p,c,r,q,v=scoped_fixture()
    scoped_investigation.investigate(p,c,r,q,FunctionProvider(lambda _:deepcopy(v)),tmp_path,
        maximum_rounds=1,maximum_actions=2)
    return tmp_path,p,c,r,q


def test_original_judgments_reconstruct_from_executed_actions(evidence):
    d,*inputs=evidence
    result=audit.check_scoped_result(d/'result.json',*inputs)
    assert result['executed_actions']==2
    assert audit.audit_journals(d)[0]['executed']==2


@pytest.mark.parametrize('change',['proposal','count','receipt','raw'])
def test_phase_summary_cannot_bypass_original_evidence(evidence,change):
    d,*inputs=evidence;p=d/'result.json';v=json.loads(p.read_text())
    if change=='proposal':v['batches'][0]['proposals']=[]
    elif change=='count':v['pairs_with_four_dimensions_assessed']+=1
    elif change=='receipt':v['batches'][0]['attempts'][0]['receipt']['result_hash']='0'*64
    else:(d/'model/action-0000/raw-response.json').write_text('{}')
    p.write_text(json.dumps(v))
    with pytest.raises(LegalMathError):audit.check_scoped_result(p,*inputs)
