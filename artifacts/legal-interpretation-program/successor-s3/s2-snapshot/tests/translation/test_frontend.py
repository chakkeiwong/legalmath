from copy import deepcopy
import pytest
from legalmath.canonical import canonical,loads
from legalmath.errors import LegalMathError
from legalmath.translation.frontend import interpret,request,validate_generation
from legalmath.translation.model import from_reading,validate
from legalmath.translation.pipeline import translate
from tests.search.support import FunctionProvider
from .support import AT,fixture,model


def provider(g,verdict='SUPPORTED'):
    return FunctionProvider(lambda r: {'verdict':verdict,'findings':[]} if r['task']=='REVIEW' else deepcopy(g))


def test_interpret_once_translate_both_and_resume_without_calls(tmp_path):
    t,g=fixture();p=provider(g)
    state=interpret(t,tmp_path,p)
    assert state['status']=='INTERPRETED' and len(p.requests)==2
    m=loads((tmp_path/state['models'][0]['path']).read_bytes())
    for target in ('ruleir','catala'): assert translate(m,target)['status']=='TRANSLATED'
    assert len(p.requests)==2
    assert interpret(t,tmp_path,p,resume=True)==state
    assert len(p.requests)==2
    assert all('target' not in r and 'expected' not in r for r in p.requests)
    assert request(t)==p.requests[0]


def test_rival_and_unrepresented_readings_are_retained(tmp_path):
    t,g=fixture();r=deepcopy(g['readings'][0]);r['local_id']='rival'
    r['formalization']['result']='(> months (integer 6))';g['readings'].append(r)
    u=deepcopy(r);u.update(local_id='unrepresented',formalization=None);g['readings'].append(u)
    state=interpret(t,tmp_path,provider(g))
    assert {r['reading_id'] for r in state['models']}=={'threshold','rival'}
    assert state['unrepresented_readings']==['unrepresented']


@pytest.mark.parametrize('problem',['question','coverage','dependency','critic','ambiguity'])
def test_uncertainty_blocks_both_targets(tmp_path,problem):
    t,g=fixture();verdict='SUPPORTED'
    if problem=='question':g['questions']=['Which calendar convention applies?']
    if problem=='coverage':g['coverage'][0]['status']='DEFERRED'
    if problem=='dependency':t['packet']['dependencies']=[{'dependency_id':'missing','source_hash':None}]
    if problem=='critic':verdict='UNRESOLVED'
    if problem=='ambiguity':g['dimensions'][0]['status']='AMBIGUOUS'
    state=interpret(t,tmp_path,provider(g,verdict))
    m=loads((tmp_path/state['models'][0]['path']).read_bytes())
    for target in ('ruleir','catala'): assert translate(m,target)['status']=='UNRESOLVED'


def test_changed_interface_and_retained_expression_are_rejected():
    t,g=fixture();g['readings'][0]['formalization']['facts'][0]['meaning']='A different fact'
    with pytest.raises(LegalMathError):validate_generation(g,t)
    m=model();m['rules'][0]['body']['cmp']='gt'
    with pytest.raises(LegalMathError,match='integrity'):validate(m)
    m=model();m['interpretations'][0]['statement']='An unrelated interpretation'
    with pytest.raises(LegalMathError,match='integrity'):validate(m)


def test_changed_resume_file_and_task_rejected(tmp_path):
    t,g=fixture();p=provider(g);state=interpret(t,tmp_path,p)
    with pytest.raises(LegalMathError):interpret({**t,'question':'Changed question'},tmp_path,p,resume=True)
    path=tmp_path/state['models'][0]['path'];m=loads(path.read_bytes());m['review']['questions']=['Changed']
    path.write_bytes(canonical(m))
    with pytest.raises(LegalMathError):interpret(t,tmp_path,p,resume=True)
    assert len(p.requests)==2


def test_interrupted_dispatch_is_never_replayed(tmp_path):
    t,g=fixture()
    def crash(_):raise RuntimeError('interrupted process')
    p=FunctionProvider(crash)
    with pytest.raises(RuntimeError):interpret(t,tmp_path,p)
    resumed=interpret(t,tmp_path,p,resume=True)
    assert resumed['status']=='STOPPED' and resumed['failure']['code']=='E_JOB_STATE'
    assert len(p.requests)==1


def test_challenged_reading_repair_uses_same_shared_workflow(tmp_path):
    t,g=fixture();calls=[]
    def response(r):
        calls.append(r)
        return {'verdict':'CHALLENGED' if len(calls)==2 else 'SUPPORTED','findings':['Check boundary']} if r['task']=='REVIEW' else deepcopy(g)
    p=FunctionProvider(response);state=interpret(t,tmp_path,p)
    assert state['status']=='INTERPRETED' and len(calls)==4
    assert calls[2]['task']=='REFINE' and calls[2]['diagnostics'][0]['verdict']=='CHALLENGED'
