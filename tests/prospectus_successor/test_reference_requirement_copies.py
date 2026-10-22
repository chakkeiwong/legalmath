"""Direct source copies require exact identity; missing maps cannot hide edits."""
from copy import deepcopy
import pytest
from legalmath.prospectus import reference_requirements as module

def example():
    raw={'id':'source:p5:l48','document':'source','source_sha256':'a'*64,
         'page':5,'raw':'8. März 2032','visible':True,'text_sha256':module.digest('8. März 2032')}
    selected={'unit':raw['id'],'text':raw['raw'],'original_sha256':raw['text_sha256'],
              'source':{'document':'source','page':5}}
    products={'P1':{'payload':{'graph':{'units':[raw]}}},
              'P2':{'payload':{'assembly':{'units':[selected]}}}}
    anchor={'unit':raw['id'],'document':'source','source_sha256':raw['source_sha256'],
            'start':0,'end':len(raw['raw']),'quote':raw['raw']}
    return products,selected,anchor

def test_exact_direct_copy_passes():
    products,selected,anchor=example();module.Sources(products).retained(anchor)

@pytest.mark.parametrize('case',['text','original-hash','document','page','empty-map','source-hash'])
def test_invalid_direct_copy_refused(case):
    products,selected,anchor=example()
    if case=='text':selected['text']='8. März 2031'
    elif case=='original-hash':selected['original_sha256']='0'*64
    elif case=='document':selected['source']['document']='other'
    elif case=='page':selected['source']['page']=4
    elif case=='empty-map':selected['character_map']=[]
    else:anchor['source_sha256']='b'*64
    with pytest.raises(ValueError):module.Sources(products).retained(anchor)
