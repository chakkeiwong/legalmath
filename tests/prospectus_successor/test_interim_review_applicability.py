"""Incomplete recognizable interim reviews cannot bypass category checks."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import interim_review, report_scope, service
from legalmath.prospectus.successor.contracts import digest
from test_interim_review import TEXT, UNKNOWN, exact_span, fixture, products


VARIANTS = {
    'scope-qualification': TEXT.replace('\nConclusion\n', '\nThis review excludes some financial statements.\nConclusion\n'),
    'conclusion-qualification': TEXT.replace('\nLisbon, 13', '\nExcept for an unresolved qualification.\nLisbon, 13'),
    'changed-criteria': TEXT.replace('as required by the CVM;', 'under other criteria;'),
    'prefix-commentary': 'The following report is quoted for discussion.\n' + TEXT,
}


@pytest.mark.parametrize('variant', list(VARIANTS))
@pytest.mark.parametrize('category', [
    'LIMITED_FINANCIAL_REVIEW', 'STATUTORY_FINANCIAL_AUDIT',
    'LIMITED_SUSTAINABILITY_ASSURANCE', 'COMMITTEE_REPORT'])
def test_changed_source_crossed_with_wrong_category_cannot_gain_support(tmp_path, variant, category):
    p1,p2,scope,text=fixture(tmp_path, VARIANTS[variant])
    facts=scope['reports'][0]['facts']
    facts['identity']['value']=category
    for field,value in report_scope.PROFILES[category].items():facts[field]['value']=value
    if category=='COMMITTEE_REPORT':facts['assurance_level']=deepcopy(UNKNOWN)
    # Supply all category-required textual facts, so missing generic fields
    # cannot accidentally make the guard test pass.
    for field in ('addressee','purpose','reliance_limits'):
        facts[field]={'status':'SUPPLIED','spans':[exact_span(text,text)]}
    answer=service.consume(products(p1,p2,scope),tmp_path,mode='current',include_artifacts=True)
    report=answer['source_reports'][0]
    assert report['status']=='INCOMPLETE_SOURCE_READING'
    assert report['unresolved_interim_review_fields']==['source_structure']
    for key in ('financial_statement_audit_opinion','limited_sustainability_assurance','committee_concurrence'):
        assert report['use_assessment'][key]=='NOT_ESTABLISHED_BY_THIS_READING'


def test_known_original_source_without_remaining_title_cannot_fall_through(tmp_path):
    _,p2,scope,_=fixture(tmp_path)
    selected=deepcopy(p2['payload']['source_report_readings'])
    row=selected['reports'][0]
    row['text']='Changed extraction has omitted the report title and section headings.'
    row['source_sha256']='b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
    row['pages']=[{'page':172,'mode':'raw'},{'page':173,'mode':'raw'}]
    row['characters']=[{'output':i,'source_offset':i,'character':c,'unit':'explicit-adverse-variant'} for i,c in enumerate(row['text'])]
    row['sha256']=digest({k:v for k,v in row.items() if k!='sha256'})
    facts=scope['reports'][0]['facts']
    codes={'identity':'STATUTORY_FINANCIAL_AUDIT',**report_scope.PROFILES['STATUTORY_FINANCIAL_AUDIT']}
    for key,fact in facts.items():
        if fact['status']=='SUPPLIED':
            fact['spans']=[exact_span(row['text'],row['text'])]
            if key in codes:fact['value']=codes[key]
    scope['readings_sha256']=digest(selected)
    scope['reports'][0]['reading_sha256']=row['sha256']
    report,=report_scope.explain(report_scope.admit(selected,scope))
    assert report['status']=='INCOMPLETE_SOURCE_READING'
    assert report['use_assessment']['financial_statement_audit_opinion']=='NOT_ESTABLISHED_BY_THIS_READING'


def test_unrelated_text_and_other_pages_do_not_acquire_interim_guard():
    reading={'text':'A separate unrelated statement.', 'source_sha256':'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7',
        'pages':[{'page':50,'mode':'raw'}]}
    assert interim_review.check(reading,{'identity':{'status':'SUPPLIED','value':'STATUTORY_FINANCIAL_AUDIT'}}) is None
