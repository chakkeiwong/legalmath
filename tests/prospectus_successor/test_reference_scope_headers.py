"""Current structural source bindings supersede stale auxiliary use lists."""
import pytest
from legalmath.prospectus.successor import reference_scope as module
from legalmath.prospectus.successor.contracts import TextUnit

def example():
    raw=TextUnit('source:p1:l1','source','a'*64,1,1,'§ 5',None,
        'source:p1:b1','de','retained-source').json()
    anchor={k:raw[k] for k in ('document','source_sha256')}
    anchor.update(unit=raw['id'],start=0,end=3,quote=raw['raw'])
    selected={'unit':raw['id'],'text':raw['raw'],'role':'HEADER','context':'selected-option',
        'source':{'document':'source','page':1},'original_sha256':raw['text_sha256'],
        'character_map':[{'start':0,'end':3,'source':dict(anchor)}]}
    piece={'start':0,'end':3,'text':raw['raw'],'raw_binding':anchor,
        'assembly_uses':[],'assembly_use_status':'MISSING'}
    return raw,selected,piece

def test_current_header_survives_missing_auxiliary_uses():
    raw,selected,piece=example()
    rows=module.current_headers(raw['raw'],[piece],{raw['id']:selected},{raw['id']:raw})
    assert rows==[{'start':0,'end':3,'section':'5','unit':raw['id'],
        'context':'selected-option','document':'source'}]

@pytest.mark.parametrize('change',['document','page','hash','empty-map','map-source','selected-text'])
def test_changed_header_binding_refused(change):
    raw,selected,piece=example()
    if change=='document':selected['source']['document']='other'
    elif change=='page':selected['source']['page']=2
    elif change=='hash':selected['original_sha256']='0'*64
    elif change=='empty-map':selected['character_map']=[]
    elif change=='map-source':selected['character_map'][0]['source']['unit']='other:p1:l1'
    else:selected['text']='§ 6'
    with pytest.raises(ValueError):
        module.current_headers(raw['raw'],[piece],{raw['id']:selected},{raw['id']:raw})

def test_unknown_role_is_not_promoted_to_header():
    raw,selected,piece=example();selected['role']='UNKNOWN'
    assert module.current_headers(raw['raw'],[piece],{raw['id']:selected},{raw['id']:raw})==[]
