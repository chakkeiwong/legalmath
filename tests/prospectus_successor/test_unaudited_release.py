"""An explicitly unaudited issuer release cannot establish an audit opinion."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from test_report_scope import REVIEW, exact_span, products
from test_successor import request

TEXT=(Path(__file__).parent/'fixtures/bes_fy2010_release.txt').read_text()
TITLE='BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN 2010'
QUALIFICATION='Unaudited financial information under IFRS as implemented by the European Union'
UNKNOWN={'status':'UNKNOWN','reason':'Not established by this issuer release'}


def fixture(tmp_path, body=TEXT):
    req=request(tmp_path,[body]);req.pop('assembly');req.pop('scope')
    graph=service.source_product(req,tmp_path)['payload']['graph']
    text='\n'.join(u['raw'] for u in graph['units'])
    req['source_report_readings']={'version':'source-report-readings.v1','graph_sha256':digest(graph),'review':REVIEW,
        'reports':[{'id':'release','document':'d','source_sha256':req['bundle']['documents'][0]['sha256'],
                    'pages':[{'page':1,'mode':'raw'}],'text_sha256':digest(text.encode())}]}
    p1=service.source_product(req,tmp_path);p2=service.construction_product(p1,tmp_path)
    selected=p2['payload']['source_report_readings']
    facts={name:deepcopy(UNKNOWN) for name in report_scope.FACTS}
    for field,quote,value in [('identity','MATERIAL EVENT','UNAUDITED_FINANCIAL_RELEASE'),
        ('subject',TITLE,'CONSOLIDATED_FINANCIAL_RESULTS'),('assurance_level','Unaudited','UNAUDITED'),
        ('criteria',QUALIFICATION,None),('report_date','Lisbon, 31 January 2011',None)]:
        facts[field]={'status':'SUPPLIED','spans':[exact_span(text,quote if quote in text else text)],
                      **({'value':value} if value else {})}
    scope={'version':'source-report-scope.v1','readings_sha256':digest(selected),'review':REVIEW,
        'reports':[{'id':'release','reading_sha256':selected['reports'][0]['sha256'],'facts':facts}]}
    return p1,p2,scope,text


def direct(p2,scope):
    return report_scope.explain(report_scope.admit(p2['payload']['source_report_readings'],scope))[0]


def test_current_release_description_preserves_questions_and_unknown_opinion(tmp_path):
    p1,p2,scope,_=fixture(tmp_path)
    before=service.consume(products(p1,p2),tmp_path,mode='current',include_artifacts=True)
    after=service.consume(products(p1,p2,scope),tmp_path,mode='current',include_artifacts=True)
    report,=after['source_reports']
    assert report['status']=='CONDITIONAL_SUPPLIED_READING'
    assert report['use_assessment']['unaudited_financial_release']=='SUPPLIED_SOURCE_DESCRIPTION'
    for key in ('financial_statement_audit_opinion','limited_sustainability_assurance','committee_concurrence'):
        assert report['use_assessment'][key]=='NOT_ESTABLISHED_BY_THIS_READING'
    assert report['facts']['conclusion']['status']=='UNKNOWN'
    assert all(report['facts'][key]['status']=='UNKNOWN' for key in report_scope.EXTERNAL)
    assert report['facts']['assurance_level']['value']=='UNAUDITED'
    assert not report['unaudited_release_context']['publication_date_established']
    assert not report['unaudited_release_context']['independent_opinion_established']
    assert all(after[key]==before[key] for key in ('questions','dependencies','assembly'))
    assert not after['independent_legal_acceptance'] and not after['may_execute_transaction']


@pytest.mark.parametrize('kind',['STATUTORY_FINANCIAL_AUDIT','LIMITED_FINANCIAL_REVIEW',
                               'LIMITED_SUSTAINABILITY_ASSURANCE','COMMITTEE_REPORT'])
def test_consistent_false_profiles_refuse_current_interpretation(tmp_path,kind):
    p1,p2,scope,text=fixture(tmp_path)
    facts=scope['reports'][0]['facts'];facts['identity']['value']=kind
    for name,value in report_scope.PROFILES[kind].items():
        facts[name]={'status':'SUPPLIED','value':value,'spans':[exact_span(text,QUALIFICATION)]}
    if kind=='COMMITTEE_REPORT':facts['assurance_level']=deepcopy(UNKNOWN)
    with pytest.raises(ValueError,match='Unaudited issuer-release'):
        service.interpretation_product(p1,p2,{'source_report_scope':scope})


@pytest.mark.parametrize('field',['identity','subject','criteria','assurance_level','report_date'])
def test_unknown_essential_facts_withhold_release_reading(tmp_path,field):
    _,p2,scope,_=fixture(tmp_path);scope['reports'][0]['facts'][field]=deepcopy(UNKNOWN)
    assert direct(p2,scope)['status']=='INCOMPLETE_SOURCE_READING'


@pytest.mark.parametrize('field,quote',[('assurance_level','financial information'),
    ('subject','GROUP ACTIVITY AND RESULTS'),('criteria','IFRS'),
    ('criteria','Unaudited financial information under IFRS'),('report_date','31 January')])
def test_exact_but_incomplete_quotes_withhold_description(tmp_path,field,quote):
    _,p2,scope,text=fixture(tmp_path)
    scope['reports'][0]['facts'][field]['spans']=[exact_span(text,quote)]
    report=direct(p2,scope)
    assert report['status']=='INCOMPLETE_SOURCE_READING'
    assert field in report['unresolved_unaudited_release_fields']


def test_identical_footer_date_does_not_substitute_for_header_date(tmp_path):
    _,p2,scope,text=fixture(tmp_path)
    quote='Lisbon, 31 January 2011';start=text.rindex(quote)
    scope['reports'][0]['facts']['report_date']['spans']=[{'start':start,'end':start+len(quote),'quote':quote}]
    report=direct(p2,scope)
    assert report['status']=='INCOMPLETE_SOURCE_READING'
    assert report['unresolved_unaudited_release_fields']==['report_date']


@pytest.mark.parametrize('value',['AFFIRMATIVE_FINANCIAL_OPINION','NEGATIVE_ASSURANCE','CONCURRENCE_WITH_AUDITORS'])
def test_no_conclusion_fabricated_from_issuer_header(tmp_path,value):
    _,p2,scope,text=fixture(tmp_path)
    scope['reports'][0]['facts']['conclusion']={'status':'SUPPLIED','value':value,'spans':[exact_span(text,TITLE)]}
    with pytest.raises(ValueError,match='independent opinion conclusion'):direct(p2,scope)


@pytest.mark.parametrize('body',[TEXT.replace('Unaudited','Audited',1),
    TEXT.replace(' as implemented by the European Union','',1),
    TEXT.replace('IN 2010','IN 2011',1),'Commentary quotes the following release.\n'+TEXT,
    TEXT.replace('Lisbon, 31 January 2011','Lisbon, 1 February 2011',1)])
def test_unrecognized_new_profile_stays_incomplete(tmp_path,body):
    _,p2,scope,_=fixture(tmp_path,body)
    report=direct(p2,scope)
    assert report['status']=='INCOMPLETE_SOURCE_READING'
    assert report['unaudited_release_context']['status']=='UNRECOGNIZED_OR_INCOMPLETE_SOURCE_HEADER'


@pytest.mark.parametrize('mutation',['quote','reading','publication'])
def test_integrity_and_external_source_requirements_preserved(tmp_path,mutation):
    p1,p2,scope,_=fixture(tmp_path);row=scope['reports'][0]
    if mutation=='quote':row['facts']['criteria']['spans'][0]['quote']+=' changed'
    elif mutation=='reading':row['reading_sha256']='0'*64
    else:row['facts']['publication_date']=deepcopy(row['facts']['report_date'])
    with pytest.raises(ValueError):service.interpretation_product(p1,p2,{'source_report_scope':scope})
