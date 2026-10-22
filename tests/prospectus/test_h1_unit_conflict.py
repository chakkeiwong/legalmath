"""Original finite unit interpretation and adverse dimensional controls."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from legalmath.prospectus import h1_unit_conflict as unit
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_h1_unit_oracle import verify

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'tests/prospectus_successor/fixtures/h1_unit_conflict.json.gz'

@pytest.fixture
def f():
    with gzip.open(FIXTURE,'rt') as stream:return json.load(stream)

def output(f):
    return unit.evaluate(f['graph'],f['prior'],f['profile'],ROOT,expected_profile_sha256=digest(f['profile']))

def test_original_unit_conflict_stays_unresolved(f):
    actual=output(f);proof=verify(actual,unit.explain(actual),f['profile'],f['graph'],f['prior'],f['original'],ROOT)
    assert proof['printed_scale_ratio']==1000 and proof['source_cells']==6
    assert actual['pages'][0]['cells'][1]['value'] is None
    assert all(r['raw_numeral_difference']==0 and r['same_unit_financial_equality'] is False for r in actual['comparisons'])

PROFILE_CASES=['unit','year','entity','row','duplicate-cell','omit-cell','column','page','boolean-offset',
    'missing-header','short-quote','image','source','graph','prior','review','resolved-unit','rescale','financial-equality']

def profile_change(p,name):
    p=deepcopy(p);page=p['pages'][0]
    if name=='unit':page['headers'][2]=deepcopy(p['pages'][1]['headers'][4])
    elif name=='year':page['headers'][3]=deepcopy(page['headers'][10])
    elif name=='entity':page['headers'][0]['quote']='BES Finance Ltd'
    elif name=='row':page['cells'][2]=deepcopy(page['cells'][3])
    elif name=='duplicate-cell':page['cells'][1]=deepcopy(page['cells'][0])
    elif name=='omit-cell':page['cells'].pop()
    elif name=='column':page['columns'][3]='2009-12-31 net'
    elif name=='page':page['page']=54
    elif name=='boolean-offset':page['headers'][0]['start']=False
    elif name=='missing-header':page['headers'].pop()
    elif name=='short-quote':page['headers'][0]['end']-=1;page['headers'][0]['quote']=page['headers'][0]['quote'][:-1]
    elif name=='image':page['image']['sha256']='0'*64
    elif name=='source':page['cells'][0]['source_sha256']='0'*64
    elif name=='graph':p['graph_sha256']='0'*64
    elif name=='prior':p['prior_sha256']='0'*64
    elif name=='review':p['review']['independent']=True
    else:p[name]=True
    return p

@pytest.mark.parametrize('name',PROFILE_CASES)
def test_repinned_profile_refused(f,name):
    p=profile_change(f['profile'],name)
    with pytest.raises(ValueError):unit.evaluate(f['graph'],f['prior'],p,ROOT,expected_profile_sha256=digest(p))

OUTPUT_CASES=['unit','scale','comparison','equality','dash-zero','date','entity','correction','rescale','authority',
    'selected-unit','selected-scope','cause','source','prose']

def output_change(value,explanation,name):
    a=deepcopy(value)
    if name=='unit':a['pages'][0]['cells'][0]['printed_unit']='EUR thousands'
    elif name=='scale':a['comparisons'][0]['printed_scale_ratio']=1
    elif name=='comparison':a['comparisons'][0]['raw_numeral_difference']=False
    elif name=='equality':a['comparisons'][0]['same_unit_financial_equality']=True
    elif name=='dash-zero':a['pages'][0]['cells'][1].update(value=0,status='SOURCE_NUMBER')
    elif name=='date':a['comparisons'][1]['period']='2009FY'
    elif name=='entity':a['entity']='BES Finance Ltd'
    elif name=='correction':a['official_unit_correction_established']=True
    elif name=='rescale':a['source_rescaled']=True
    elif name=='authority':a['may_execute_transaction']=True
    elif name=='selected-unit':a['resolved_unit']='EUR thousands'
    elif name=='selected-scope':a['selected_incorporation_reading']='overall-range'
    elif name=='cause':a['accounting_cause']='typo'
    elif name=='source':a['pages'][0]['cells'][0]['source']['unit']='another-source'
    elif name=='prose':explanation='The source unit is corrected to thousands.'
    return a,explanation

@pytest.mark.parametrize('name',OUTPUT_CASES)
def test_separate_checker_refuses_semantic_output_change(f,name):
    actual=output(f);a,e=output_change(actual,unit.explain(actual),name)
    with pytest.raises(ValueError):verify(a,e,f['profile'],f['graph'],f['prior'],f['original'],ROOT)

def test_image_bytes_checked_at_consumer_boundary(f,tmp_path):
    p=deepcopy(f['profile'])
    for page in p['pages']:
        path=tmp_path/str(page['page']);path.write_bytes((ROOT/page['image']['path']).read_bytes())
        page['image']['path']=str(path)
    (tmp_path/'53').write_bytes(b'altered')
    with pytest.raises(ValueError):unit.evaluate(f['graph'],f['prior'],p,tmp_path,expected_profile_sha256=digest(p))

def test_changed_original_occurrence_refused_by_separate_map(f):
    a=deepcopy(f);p=a['profile'];anchor=p['pages'][0]['cells'][0]
    u=next(u for u in a['graph']['units'] if u['id']==anchor['unit']);u['raw']='138 436';anchor['quote']='138 436'
    p['graph_sha256']=digest(a['graph']);actual=output(a)
    with pytest.raises(ValueError,match='Original source'):verify(actual,unit.explain(actual),p,a['graph'],a['prior'],a['original'],ROOT)
