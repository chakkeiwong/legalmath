from copy import deepcopy
from itertools import product
import pytest
from legalmath.prospectus import cross_default_amount as module
from scripts.prospectus_amount_oracle import FACTS,classify,projection,scenarios

EXPR={'all':['default.notice',{'any':['default.c.accelerated',{'all':['default.c.overdue',{'not':'default.c.disputed'}]},'default.c.security']},
             {'not':'default.c.cured'},{'any':['default.quorum','default.other_at_receipt']},
             {'any':[{'not':'representative.c.entrusted'},'representative.c.express_permission']}]}
NODE={'conditions':EXPR}


@pytest.mark.parametrize('row',scenarios('bond'),ids=lambda r:r['id'])
def test_source_bound_amount_cases_match_integer_oracle(row):
    actual=module.analyze(row,NODE,'bond');assert projection(actual)==classify(row)
    assert actual['actual_default']=='NOT_ESTABLISHED'


def test_full_source_formula_with_derived_amount_and_withheld_conflicts():
    count=0
    for amount in ('200000000','200000000.01'):
        for world in product((False,True),repeat=len(FACTS)):
            row=deepcopy(scenarios('bond')[1]);row['payment']['amount']=amount;row['other_facts']=dict(zip(FACTS,world))
            assert projection(module.analyze(row,NODE,'bond'))==classify(row);count+=1
    for field in FACTS:
        for value in (None,'conflict'):
            row=deepcopy(scenarios('bond')[3]);row['other_facts'][field]=value
            assert projection(module.analyze(row,NODE,'bond'))==classify(row);count+=1
    assert count==1042


@pytest.mark.parametrize('kind',['negative','float','nan','scientific','zero-fx','negative-fx','unit','currency','event','instrument','eur-fx','override'])
def test_invalid_amount_inputs_refused(kind):
    row=deepcopy(next(r for r in scenarios('bond') if r['id']=='fx-exact'))
    if kind in ('negative','float','nan','scientific'):row['payment']['amount']={'negative':'-1','float':1.1,'nan':'NaN','scientific':'2e8'}[kind]
    elif kind=='zero-fx':row['payment']['fx']['rate']='0'
    elif kind=='negative-fx':row['payment']['fx']['rate']='-1'
    elif kind=='unit':row['payment']['fx']['unit']='SOURCE_PER_EUR'
    elif kind=='currency':row['payment']['fx']['source_currency']='GBP'
    elif kind=='event':row['payment']['fx']['event_id']='other'
    elif kind=='instrument':row['payment']['instrument_id']='other'
    elif kind=='eur-fx':row['payment']['currency']='EUR'
    else:row['other_facts']['default.c.overdue']=True
    with pytest.raises(ValueError):module.analyze(row,NODE,'bond')
