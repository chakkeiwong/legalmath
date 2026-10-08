import copy
import pytest
from legalmath.errors import LegalMathError

def test_unanimous_omission_is_visible(svc,run,proposal):
    for i in range(3): svc.propose('author',f'p{i}',run['run_id'],proposal)
    svc.inventory_check('author','inventory',run['run_id'])
    issues=svc.read('meaning',run['run_id'])['records']['issue']
    assert [(x['kind'],x['source_unit_ids']) for x in issues]==[('SOURCE_COVERAGE',['fn1'])]

def test_dependency_and_inventory_are_independent(svc,packet):
    packet['dependencies']=[{'dependency_id':'code','source_hash':None}]
    run=svc.create('author','new',packet)
    records=svc.read('meaning',run['run_id'])['records']
    assert records['issue'][0]['kind']=='DEPENDENCY'
    assert records['coverage'][0]['inventory_unit_ids']==['p10','fn1']

@pytest.mark.parametrize('change',[{'extra':'ignored'},{'authority':'SFC_APPROVED'},{'authority':'RETAINED_SOURCE'}])
def test_invalid_packets(svc,packet,change):
    with pytest.raises(LegalMathError): svc.create('author','bad',{**packet,**change})

def test_source_version_cannot_be_silently_replaced(svc,packet,run,proposal):
    packet['units'][1]['text']='Changed footnote'
    with pytest.raises(LegalMathError): svc.create('author','silently-new',packet)
    svc.invalidate_source('meaning','source-change',packet['source_key'],packet,'Retained correction')
    assert svc.read('author',run['run_id'])['invalidated']
    with pytest.raises(LegalMathError): svc.propose('author','stale',run['run_id'],proposal)

def test_retained_inventory_needs_registered_review(svc,case,root):
    from legalmath.sources.intake import import_spi,resolve_span
    from legalmath.interpretation.reports import Reports
    import_spi(svc.db,root)
    span=case['bundle']['source_spans'][0]
    with svc.db.connect() as con: text=resolve_span(svc.db,con,span)
    packet=dict(source_key='retained.test',authority='RETAINED_SOURCE',selected_slice='Retained span',units=[dict(unit_id='span',locator='Retained span',text=text,normative=True,span=span)],dependencies=[],family_ids=['literal'])
    run=svc.create('author','retained',packet)
    p=dict(source_packet_hash=run['source_packet_hash'],source_unit_ids=['span'],family_ids=['literal'],subject_unit='Synthetic',controlled_language='Unreviewed source meaning',bundle_hash=None,assumptions=[],arguments=[],parent_id=None,revision_reason='Test')
    svc.propose('author','retained.p',run['run_id'],p)
    with svc.db.connect() as con: assert 'source-coverage' not in Reports(svc)._material(con,svc._run(con,run['run_id']))['checks']
    with pytest.raises(LegalMathError):svc.review_inventory('author','forged',run['run_id'],run['source_packet_hash'],['span'],'Checked')
    svc.review_inventory('meaning','review-inventory',run['run_id'],run['source_packet_hash'],['span'],'Reviewed this declared slice, not the entire source corpus')
    with svc.db.connect() as con: assert 'source-coverage' in Reports(svc)._material(con,svc._run(con,run['run_id']))['checks']
