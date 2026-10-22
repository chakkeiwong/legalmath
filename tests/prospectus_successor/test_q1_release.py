"""The second inspected issuer release cannot borrow a different period/date."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import report_scope, service
from test_unaudited_release import fixture as base_fixture, direct, QUALIFICATION, UNKNOWN
from test_report_scope import exact_span, products

TEXT=(Path(__file__).parent/'fixtures/bes_q12011_release.txt').read_text()
TITLE='BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN 1Q11'
DATE='Lisbon, 2 May 2011'

def fixture(tmp_path, body=TEXT):
    p1,p2,scope,text=base_fixture(tmp_path,body)
    facts=scope['reports'][0]['facts']
    facts['subject']['spans']=[exact_span(text,TITLE if TITLE in text else text)]
    facts['report_date']['spans']=[exact_span(text,DATE if DATE in text else text)]
    return p1,p2,scope,text

def test_current_q1_release_preserves_dependency_and_question_verdicts(tmp_path):
    p1,p2,scope,_=fixture(tmp_path)
    before=service.consume(products(p1,p2),tmp_path,mode='current',include_artifacts=True)
    after=service.consume(products(p1,p2,scope),tmp_path,mode='current',include_artifacts=True)
    r,=after['source_reports']
    assert r['status']=='CONDITIONAL_SUPPLIED_READING'
    assert r['unaudited_release_context']['profile']=='bes-english-q12011-release.v1'
    assert r['unaudited_release_context']['printed_release_date']=='2011-05-02'
    assert not r['unaudited_release_context']['publication_date_established']
    assert r['use_assessment']['unaudited_financial_release']=='SUPPLIED_SOURCE_DESCRIPTION'
    assert r['use_assessment']['financial_statement_audit_opinion']=='NOT_ESTABLISHED_BY_THIS_READING'
    assert r['facts']['conclusion']['status']=='UNKNOWN'
    assert all(r['facts'][k]['status']=='UNKNOWN' for k in report_scope.EXTERNAL)
    assert all(after[k]==before[k] for k in ('questions','dependencies','assembly','source_map'))
    assert not after['independent_legal_acceptance'] and not after['may_execute_transaction']

@pytest.mark.parametrize('kind',['STATUTORY_FINANCIAL_AUDIT','LIMITED_FINANCIAL_REVIEW',
                               'LIMITED_SUSTAINABILITY_ASSURANCE','COMMITTEE_REPORT'])
def test_false_q1_report_profiles_refuse_public_interpretation(tmp_path,kind):
    p1,p2,scope,text=fixture(tmp_path)
    facts=scope['reports'][0]['facts'];facts['identity']['value']=kind
    for name,value in report_scope.PROFILES[kind].items():
        facts[name]={'status':'SUPPLIED','value':value,'spans':[exact_span(text,QUALIFICATION)]}
    if kind=='COMMITTEE_REPORT':facts['assurance_level']=deepcopy(UNKNOWN)
    with pytest.raises(ValueError,match='Unaudited issuer-release'):
        service.interpretation_product(p1,p2,{'source_report_scope':scope})

@pytest.mark.parametrize('field,quote',[('assurance_level','financial information'),
    ('subject','GROUP ACTIVITY AND RESULTS'),('criteria','IFRS'),
    ('criteria','Unaudited financial information under IFRS'),('report_date','2 May')])
def test_missing_q1_qualification_withholds_description(tmp_path,field,quote):
    _,p2,scope,text=fixture(tmp_path)
    scope['reports'][0]['facts'][field]['spans']=[exact_span(text,quote)]
    r=direct(p2,scope)
    assert r['status']=='INCOMPLETE_SOURCE_READING'
    assert field in r['unresolved_unaudited_release_fields']

@pytest.mark.parametrize('field',['identity','subject','criteria','assurance_level','report_date'])
def test_unknown_q1_essential_fact_withholds_description(tmp_path,field):
    _,p2,scope,_=fixture(tmp_path);scope['reports'][0]['facts'][field]=deepcopy(UNKNOWN)
    assert direct(p2,scope)['status']=='INCOMPLETE_SOURCE_READING'

@pytest.mark.parametrize('body',[TEXT.replace('IN 1Q11','IN 2010',1),
    TEXT.replace(DATE,'Lisbon, 31 January 2011',1),
    TEXT.replace('IN 1Q11','IN 2Q11',1),TEXT.replace(' as implemented by the European Union','',1),
    'Commentary quotes this issuer release.\n'+TEXT])
def test_crossed_or_uninspected_source_form_stays_incomplete(tmp_path,body):
    _,p2,scope,_=fixture(tmp_path,body)
    r=direct(p2,scope)
    assert r['status']=='INCOMPLETE_SOURCE_READING'
    assert r['unaudited_release_context']['status']=='UNRECOGNIZED_OR_INCOMPLETE_SOURCE_HEADER'

@pytest.mark.parametrize('extra',[False,True])
def test_q1_footer_cannot_supply_header_date(tmp_path,extra):
    _,p2,scope,text=fixture(tmp_path)
    a=text.rindex(DATE);assert a!=text.index(DATE)
    spans=[{'start':a,'end':a+len(DATE),'quote':DATE}]
    if extra:spans.append(exact_span(text,DATE))
    scope['reports'][0]['facts']['report_date']['spans']=spans
    assert direct(p2,scope)['unresolved_unaudited_release_fields']==['report_date']

@pytest.mark.parametrize('value',['AFFIRMATIVE_FINANCIAL_OPINION','NEGATIVE_ASSURANCE','CONCURRENCE_WITH_AUDITORS'])
def test_q1_heading_cannot_supply_an_independent_conclusion(tmp_path,value):
    _,p2,scope,text=fixture(tmp_path)
    scope['reports'][0]['facts']['conclusion']={'status':'SUPPLIED','value':value,'spans':[exact_span(text,TITLE)]}
    with pytest.raises(ValueError,match='independent opinion conclusion'):direct(p2,scope)
