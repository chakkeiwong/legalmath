"""Copy fixtures use the production source constructor and raw-byte hash."""
import pytest
from legalmath.prospectus import reference_requirements as module
from legalmath.prospectus.successor.contracts import TextUnit

def example():
    raw=TextUnit('source:p5:l48','source','a'*64,5,48,'8. März 2032',None,
                 'source:p5:b26','de','retained-source').json()
    raw['visible']=True
    selected={'unit':raw['id'],'text':raw['raw'],'original_sha256':raw['text_sha256'],
              'source':{'document':'source','page':5}}
    products={'P1':{'payload':{'graph':{'units':[raw]}}},
              'P2':{'payload':{'assembly':{'units':[selected]}}}}
    anchor={'unit':raw['id'],'document':'source','source_sha256':raw['source_sha256'],
            'start':0,'end':len(raw['raw']),'quote':raw['raw']}
    return products,selected,anchor

def test_production_direct_copy_passes():
    products,selected,anchor=example();module.Sources(products).retained(anchor)

@pytest.mark.parametrize('case',['text','original-hash','document','page','empty-map','source-hash','json-string-hash'])
def test_invalid_production_direct_copy_refused(case):
    products,selected,anchor=example()
    if case=='text':selected['text']='8. März 2031'
    elif case=='original-hash':selected['original_sha256']='0'*64
    elif case=='document':selected['source']['document']='other'
    elif case=='page':selected['source']['page']=4
    elif case=='empty-map':selected['character_map']=[]
    elif case=='source-hash':anchor['source_sha256']='b'*64
    else:
        wrong=module.digest(selected['text'])
        selected['original_sha256']=wrong
        products['P1']['payload']['graph']['units'][0]['text_sha256']=wrong
    with pytest.raises(ValueError):module.Sources(products).retained(anchor)
