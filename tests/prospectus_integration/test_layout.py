from copy import deepcopy
import pytest
from legalmath.prospectus.successor.layout_adapter import project_layout


def example():
    units=[]
    for i,text in enumerate(('Insolvenz-', 'oder', 'Liquidation')):
        units.append({'id':str(i),'source_sha256':'a'*64,'page':1,'raw':text,'bbox':[0,i*2,20,i*2+1],
                      'words':[{'text':text,'start':0,'end':len(text),'bbox':[0,i*2,20,i*2+1]}]})
    doc={'texts':[{'self_ref':'r','text':'Insolvenzoder Liquidation','prov':[
        {'page_no':1,'bbox':{'l':0,'t':0,'r':21,'b':6,'coord_origin':'TOPLEFT'}}]}]}
    return units,doc


def test_normalized_text_is_never_emitted_as_legal_quote():
    units,doc=example()
    out=project_layout(units,doc,source_sha256='a'*64)
    assert not out['failures']
    mapped=out['mappings'][0]
    assert mapped['text']=='Insolvenz-\noder\nLiquidation'
    assert len(mapped['candidate_changes'])==1
    assert all(units[int(c['unit'])]['raw'][c['source_offset']]==c['character'] for c in mapped['characters'])


@pytest.mark.parametrize('text',['Insolvenz Liquidation','Insolvenzoder 5 Liquidation','Insolvenzoder not Liquidation','Liquidation Insolvenzoder'])
def test_lost_words_inserted_number_negation_and_order_fail(text):
    units,doc=example();doc['texts'][0]['text']=text
    assert project_layout(units,doc,source_sha256='a'*64)['failures']


def test_overlapping_regions_cannot_double_bind_source():
    units,doc=example();item=deepcopy(doc['texts'][0]);item['self_ref']='other';doc['texts'].append(item)
    result=project_layout(units,doc,source_sha256='a'*64)
    assert not result['mappings'] and len(result['failures'])==2


def test_changed_source_and_shifted_region_rejected():
    units,doc=example()
    with pytest.raises(ValueError,match='edition'):
        project_layout(units,doc,source_sha256='b'*64)
    doc['texts'][0]['prov'][0]['bbox']['l']=15
    assert project_layout(units,doc,source_sha256='a'*64)['failures']


def test_internal_legal_hyphen_deletion_is_not_accepted():
    units,doc=example();units[0]['raw']='write-down';units[0]['words'][0].update(text='write-down',end=10)
    doc['texts'][0]['text']='writedown oder Liquidation'
    assert project_layout(units,doc,source_sha256='a'*64)['failures']


@pytest.mark.parametrize('count',[0,2])
def test_missing_or_multiple_provenance_rejected(count):
    units,doc=example();doc['texts'][0]['prov']*=count
    out=project_layout(units,doc,source_sha256='a'*64)
    assert out['failures'] and not out['mappings']


def test_duplicate_occurrences_bind_geometry_and_page_without_text_search():
    units,doc=example()
    extra=deepcopy(units)
    for unit in extra:unit.update(id='page2-'+unit['id'],page=2)
    units+=extra
    out=project_layout(units,doc,source_sha256='a'*64)
    assert not out['failures']
    assert {c['unit'] for m in out['mappings'] for c in m['characters']}=={'0','1','2'}
    doc['texts'][0]['prov'][0]['page_no']=2
    out=project_layout(units,doc,source_sha256='a'*64)
    assert {c['unit'] for m in out['mappings'] for c in m['characters']}=={'page2-0','page2-1','page2-2'}


def test_list_marker_unicode_and_internal_whitespace_preserved():
    units,doc=example()
    text='(4)  😀 Café'
    units=units[:1];units[0].update(raw=text)
    units[0]['words']=[{'text':text,'start':0,'end':len(text),'bbox':[0,0,20,1]}]
    doc['texts'][0].update(text='😀 Café',marker='(4)',enumerated=True)
    out=project_layout(units,doc,source_sha256='a'*64)
    assert not out['failures'] and out['mappings'][0]['text']==text
    assert len(out['mappings'][0]['characters'])==len(text)


def test_invalid_word_offsets_rejected():
    units,doc=example();units[0]['words'][0]['start']=-len(units[0]['raw'])
    out=project_layout(units,doc,source_sha256='a'*64)
    assert out['failures']


def test_duplicate_source_identifiers_rejected():
    units,doc=example();units.append(deepcopy(units[0]))
    with pytest.raises(ValueError,match='Duplicate source'):
        project_layout(units,doc,source_sha256='a'*64)
