"""Malformed supplied dates cannot be mistaken for optional missing dates."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.contracts import VERSION, digest

TIME='2026-01-01T00:00:00Z'
FUTURE='2026-01-02T00:00:00Z'
PAST='2025-12-31T00:00:00Z'
FIELDS=('document_date','known_from','valid_from','valid_until')
BAD=[False,0,0.0,'',[],{},True,1,['2026-01-01'],'not-a-date',
     '2026-01-01','2026-01-01T00:00:00','2026-02-30T00:00:00Z']

def request(tmp_path):
    path=tmp_path/'source.txt';path.write_text('The Notes pay interest.')
    return {'version':VERSION,'bundle':{'instrument_id':'synthetic-document-time',
        'purpose':'review','issue_date':TIME,'effective_at':TIME,'known_at':TIME,
        'documents':[{'id':'d','path':str(path),'sha256':digest(path.read_bytes()),
            'format':'text','language':'en','authority':'Synthetic validation control',
            'document_date':TIME,'known_from':TIME}], 'dependencies':[]}}

@pytest.mark.parametrize('purpose',['issue_formation','amendment','event','review'])
@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('bad',BAD)
def test_supplied_malformed_date_refused_before_extraction(tmp_path,monkeypatch,purpose,field,bad):
    r=request(tmp_path);r['bundle']['purpose']=purpose
    d=r['bundle']['documents'][0];d[field]=bad;d['format']='pdf'
    def forbidden(*args,**kwargs):pytest.fail('Extraction reached with malformed metadata')
    monkeypatch.setattr(source_graph,'pdf_units',forbidden)
    with pytest.raises(ValueError):source_graph.build(r['bundle'],tmp_path)
    with pytest.raises(ValueError):service.source_product(r,tmp_path)

@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('missing',[True,False])
def test_omitted_and_null_dates_keep_existing_qualifications(tmp_path,field,missing):
    r=request(tmp_path);d=r['bundle']['documents'][0]
    if missing:d.pop(field,None)
    else:d[field]=None
    before=deepcopy(r)
    answer=service.assess(r,tmp_path);doc=answer['source_map']['documents'][0]
    assert r==before and doc['visible'] is True
    expected={'document_date':'document date not established','known_from':'knowledge time not established'}
    if field in expected:assert expected[field] in doc['issues']
    else:assert doc['issues']==[]
    assert answer['may_execute_transaction'] is False

@pytest.mark.parametrize('field,value,visible,purpose',[
    ('document_date',TIME,True,'issue_formation'),('document_date',FUTURE,False,'issue_formation'),
    ('document_date',FUTURE,True,'review'),('known_from',TIME,True,'review'),
    ('known_from',FUTURE,False,'review'),('valid_from',TIME,True,'review'),
    ('valid_from',FUTURE,False,'review'),('valid_until',TIME,False,'review'),
    ('valid_until',FUTURE,True,'review'),('valid_until',PAST,False,'review'),
    ('known_from','2026-01-01T08:00:00+08:00',True,'review'),
    ('valid_until','2026-01-01T08:00:00+08:00',False,'review')])
def test_explicit_boundary_expectations(tmp_path,field,value,visible,purpose):
    r=request(tmp_path);r['bundle']['purpose']=purpose;r['bundle']['documents'][0][field]=value
    graph=source_graph.build(r['bundle'],tmp_path)
    assert graph['documents'][0]['visible'] is visible
    assert all(u['visible'] is visible for u in graph['units'])

@pytest.mark.parametrize('field',FIELDS)
def test_other_exclusion_does_not_hide_malformed_field(tmp_path,field):
    r=request(tmp_path);r['bundle']['purpose']='issue_formation'
    d=r['bundle']['documents'][0];d.update(document_date=FUTURE,known_from=FUTURE,valid_from=FUTURE,valid_until=PAST)
    d[field]=False
    with pytest.raises(ValueError):service.assess(r,tmp_path)
