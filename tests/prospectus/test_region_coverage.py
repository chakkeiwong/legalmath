from copy import deepcopy
import pytest

from legalmath.prospectus.region_coverage import VERSION,evaluate_regions
from legalmath.prospectus.successor.contracts import digest


@pytest.fixture
def example(tmp_path):
    (tmp_path/'source.pdf').write_bytes(b'synthetic source')
    (tmp_path/'page.png').write_bytes(b'synthetic render')
    source=digest((tmp_path/'source.pdf').read_bytes());raw='shall not mature'
    g={'units':[{'id':'u1','document':'d','source_sha256':source,'page':1,'order':0,
        'raw':raw,'text_sha256':digest(raw.encode()),'bbox':[10,10,95,20],
        'visible':True,'method':'pdftotext-bbox-layout','words':[
            {'text':'shall','start':0,'end':5,'bbox':[10,10,35,20]},
            {'text':'not','start':6,'end':9,'bbox':[40,10,55,20]},
            {'text':'mature','start':10,'end':16,'bbox':[60,10,95,20]}]}]}
    inventory={'version':VERSION,'source_graph_sha256':digest(g),'scope':'DECLARED_REGIONS_ONLY',
        'reviewer':{'identity':'test agent','basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
        'pages':[{'document':'d','source_path':'source.pdf','source_sha256':source,'page':1,
            'display_rect':[0,0,100,100],'render_path':'page.png','render_sha256':digest((tmp_path/'page.png').read_bytes()),
            'regions':[{'id':'maturity','bbox':[0,0,100,30],'kind':'paragraph',
                        'reason':'Required maturity statement','reading':raw}]}]}
    return g,inventory,tmp_path


def run(example):
    g,i,root=example
    return evaluate_regions(g,i,root,expected_inventory_sha256=digest(i))


def test_exact_full_paragraph_projects_and_does_not_claim_page_completeness(example):
    before=deepcopy(example[:-1]);result=run(example)
    assert result['regions'][0]['status']=='MATCHED_DECLARED_TEXT'
    assert result['regions'][0]['projection']['mappings'][0]['text']=='shall not mature'
    assert result['declared_readings_matched']
    assert not any(result[k] for k in ('page_complete','document_complete','may_claim_coverage','independent_legal_acceptance','raw_replaced','legal_scope_inferred'))
    assert example[:-1]==before


def test_positive_native_page_text_does_not_hide_missing_required_region(example):
    row=example[1]['pages'][0]['regions'][0];row.update(bbox=[0,40,100,80],kind='table',reading=None)
    result=run(example);region=result['regions'][0]
    assert region['status']=='REQUIRED_CONTENT_UNAVAILABLE'
    assert region['native_page_nonspace_characters']>0 and not region['retained_word_anchors']
    assert not result['declared_readings_matched']


def test_untranscribed_words_are_not_a_matched_reading(example):
    example[1]['pages'][0]['regions'][0]['reading']=None
    assert run(example)['regions'][0]['status']=='RETAINED_WORDS_WITHOUT_REVIEWED_TRANSCRIPTION'


@pytest.mark.parametrize('text',['shall mature','shall not','shall not mature tomorrow'])
def test_omitted_negation_or_qualifier_or_added_text_stays_unresolved(example,text):
    example[1]['pages'][0]['regions'][0]['reading']=text
    assert run(example)['regions'][0]['status']=='TRANSCRIPTION_OR_PROJECTION_UNRESOLVED'


def test_partial_word_intersection_is_visible_even_when_center_is_inside(example):
    example[1]['pages'][0]['regions'][0]['bbox']=[0,0,90,30]
    region=run(example)['regions'][0]
    assert region['status']=='PARTIAL_WORD_INTERSECTION'
    assert region['partial_word_anchors'][0]['quote']=='mature'


@pytest.mark.parametrize('where',['word','unit','missing_words','not_visible'])
def test_unknown_geometry_never_becomes_absent_or_covered(example,where):
    g,i,_=example;unit=g['units'][0]
    if where=='word':unit['words'][0]['bbox']=None
    elif where=='unit':unit['bbox']=None
    elif where=='missing_words':unit['words']=[]
    else:unit['visible']=False
    i['source_graph_sha256']=digest(g)
    assert run(example)['regions'][0]['status']=='UNRESOLVED_WORD_GEOMETRY'


@pytest.mark.parametrize('case',['missing_inventory','changed_inventory','changed_graph','duplicate_unit',
    'bad_text_hash','word_offset','word_quote','overlapping_words','foreign_source','source_changed','render_changed',
    'missing_render','path_escape','absolute_path','duplicate_page','unknown_page','bad_page','duplicate_region',
    'missing_region','invalid_box','outside_page','empty_reason','empty_reading','false_independence','false_scope','foreign_key'])
def test_invalid_inputs_refuse(example,case):
    g,i,root=example;pin=digest(i);page=i['pages'][0];region=page['regions'][0]
    repin=True
    if case=='missing_inventory':i['pages']=[]
    elif case=='changed_inventory':region['bbox']=[0,40,100,80];repin=False
    elif case=='changed_graph':g['units'][0]['raw']='changed';repin=False
    elif case=='duplicate_unit':g['units'].append(deepcopy(g['units'][0]));i['source_graph_sha256']=digest(g)
    elif case=='bad_text_hash':g['units'][0]['text_sha256']='bad';i['source_graph_sha256']=digest(g)
    elif case=='word_offset':g['units'][0]['words'][0]['end']=8;i['source_graph_sha256']=digest(g)
    elif case=='word_quote':g['units'][0]['words'][0]['text']='wrong';i['source_graph_sha256']=digest(g)
    elif case=='overlapping_words':g['units'][0]['words'].append(deepcopy(g['units'][0]['words'][0]));i['source_graph_sha256']=digest(g)
    elif case=='foreign_source':page['source_sha256']='0'*64
    elif case=='source_changed':(root/'source.pdf').write_bytes(b'changed')
    elif case=='render_changed':(root/'page.png').write_bytes(b'changed')
    elif case=='missing_render':page['render_path']='missing.png'
    elif case=='path_escape':page['render_path']='../outside.png'
    elif case=='absolute_path':page['render_path']=str(root/'page.png')
    elif case=='duplicate_page':i['pages'].append(deepcopy(page))
    elif case=='unknown_page':page['page']=2
    elif case=='bad_page':page['page']=True
    elif case=='duplicate_region':page['regions'].append(deepcopy(region))
    elif case=='missing_region':page['regions']=[]
    elif case=='invalid_box':region['bbox']=[10,0,10,20]
    elif case=='outside_page':region['bbox']=[0,0,120,20]
    elif case=='empty_reason':region['reason']=' '
    elif case=='empty_reading':region['reading']=''
    elif case=='false_independence':i['reviewer']['independent']=True
    elif case=='false_scope':i['scope']='COMPLETE_DOCUMENT'
    else:region['complete']=True
    with pytest.raises(ValueError):
        evaluate_regions(g,i,root,expected_inventory_sha256=digest(i) if repin else pin)
