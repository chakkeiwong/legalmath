import pytest
from legalmath.translation.resources import preflight
from .v2_support import fixture_v2,as_model


def output_model(count=1,expression='x',facts=1):
    return as_model(*fixture_v2([('x' if i==0 else 'x'+str(i),'integer') for i in range(facts)],
        [('result'+str(i),'integer','true',expression) for i in range(count)],
        text='Synthetic resource control: return the declared integer calculation in every output.'))


def test_interface_counts_and_precise_overflow():
    good=preflight(output_model(count=40,facts=40))
    assert good['supported'] and good['dimensions']['outputs']['actual']==40
    manual=output_model(facts=40)
    manual['review'].update(origin='manual',reading=None)
    manual['facts'].append({**manual['facts'][0],'name':'x40'})
    bad=preflight(manual)
    assert not bad['supported'] and bad['issues']==[{'dimension':'inputs','reason':'E_RESOURCE_LIMIT','actual':41,'minimum':1,'maximum':40}]


@pytest.mark.parametrize('count,expected',[(14,30),(15,32)])
def test_generated_types_include_state_encoding(count,expected):
    types=[{'name':'Record'+str(i),'kind':'record','fields':[{'name':'flag','type':'bool','meaning':'Flag','unit':'Boolean'}],'cases':[]} for i in range(count)]
    m=as_model(*fixture_v2([('x'+str(i),t['name']) for i,t in enumerate(types)],
        [('r'+str(i),t['name'],'true','x'+str(i)) for i,t in enumerate(types)],types=types,
        text='Return each independent observed record without changing its flag.'))
    report=preflight(m)
    assert report['dimensions']['generated_types']['actual']==expected
    assert report['supported']==(count==14)
    if count==15:assert report['issues'][0]['dimension']=='generated_types'


def test_source_expansion_reports_actual_utf8_bytes():
    expr='(+ x x)'
    for _ in range(4):expr='(+ '+expr+' '+expr+')'
    report=preflight(output_model(40,expr))
    size=report['dimensions']['candidate_source_bytes']
    assert not report['supported'] and size['actual']>64000
    assert report['issues'][0]['dimension']=='candidate_source_bytes'


def test_encoded_depth_not_just_frontend_depth():
    typ='integer'
    for _ in range(6):typ='list['+typ+']'
    m=as_model(*fixture_v2([('xs',typ)],[('value',typ,'true','xs')],text='Return the observed nested list.'))
    report=preflight(m)
    assert not report['supported'] and report['dimensions']['generated_type_depth']['actual']>12
