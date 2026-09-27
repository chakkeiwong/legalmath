from copy import deepcopy
import pytest
from legalmath.canonical import loads
from legalmath.errors import LegalMathError
from legalmath.translation.frontend import interpret,validate_generation,request
from legalmath.translation.model import validate
from legalmath.translation.pipeline import translate
from .test_frontend import provider
from .v2_support import numeric_fixture,as_model


def test_multiple_outputs_helpers_and_criticism_use_one_reading(tmp_path):
    task,g=numeric_fixture();p=provider(g)
    state=interpret(task,tmp_path,p)
    assert state['status']=='INTERPRETED',state
    m=loads((tmp_path/state['models'][0]['path']).read_bytes())
    assert len(m['rules'])==18 and len(m['helpers'])==2
    assert len(p.requests)==2 and 'every output and helper' in p.requests[1]['instructions']
    assert request(task)['outputs']==task['outputs']
    assert request(task)['selected_question']==g['readings'][0]['statement']==task['packet']['units'][0]['text']
    assert translate(m,'catala')['status']=='TRANSLATED'
    rejected=translate(m,'ruleir')
    assert rejected['status']=='UNSUPPORTED'
    assert any(i['path']=='/profile' for i in rejected['capabilities']['issues'])
    assert interpret(task,tmp_path,p,resume=True)==state and len(p.requests)==2


@pytest.mark.parametrize('change',['output','helper','overlap','metadata'])
def test_executable_program_cannot_drift_from_retained_reading(change):
    m=as_model(*numeric_fixture())
    if change=='output':m['rules'][0]['scope']['name']='left'
    elif change=='helper':m['helpers'][1]['body']['op']='sub'
    elif change=='overlap':m['rules'][6]['body']['exceptions'][0]['value']['value']='8'
    else:m['rules'][6]['body']['exceptions'][0]['source_span_ids']=[]
    with pytest.raises(LegalMathError):validate(m)


@pytest.mark.parametrize('problem',['recursive','hidden_fact','wrong_arg','wrong_result','output_set','rounding','library'])
def test_malformed_or_unsupported_generation_rejected(problem):
    t,g=numeric_fixture();f=g['readings'][0]['formalization']
    if problem=='recursive':f['helpers'][1]['body']='(call double x)'
    elif problem=='hidden_fact':f['helpers'][1]['body']='ratio'
    elif problem=='wrong_arg':f['outputs'][11]['result']='(call double cash)'
    elif problem=='wrong_result':f['outputs'][0]['result']='(decimal 1 2)'
    elif problem=='output_set':f['outputs'].pop()
    elif problem=='rounding':f['outputs'][2]['result']='(round money_hkd silent ratio)'
    else:f['outputs'][0]['result']='(library external.eval cash)'
    with pytest.raises(LegalMathError):validate_generation(g,t)


def test_ambiguity_still_blocks_v2(tmp_path):
    t,g=numeric_fixture();g['questions']=['Which rounding policy is authorized?']
    state=interpret(t,tmp_path,provider(g));m=loads((tmp_path/state['models'][0]['path']).read_bytes())
    assert translate(m,'catala')['status']=='UNRESOLVED'


def test_generated_type_budget_is_reported_before_compiler_dispatch():
    m=as_model(*numeric_fixture());m['review'].update(origin='manual',reading=None)
    for i in range(16):
        typ='Record'+str(i)
        m['types'].append({'name':typ,'kind':'record','fields':[
            {'name':'amount','type':'integer','meaning':'Synthetic count','unit':'count'}],'cases':[]})
        m['facts'].append({'name':'record'+str(i),'type':typ,'description':'Synthetic observed record'})
    result=translate(m,'catala')
    assert result['status']=='UNSUPPORTED'
    assert '30 native types' in str(result['capabilities']['issues'])
