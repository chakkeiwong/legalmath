from copy import deepcopy

import pytest

from legalmath.prospectus.basf_body_coverage import selected_sources, reviewed_roles
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


def fixture():
    raw={'id':'original','document':'base','source_sha256':'a'*64,'page':1,
         'raw':'[Agent], office','visible':True,'bbox':[1,2,3,4]}
    raw['text_sha256']=digest(raw['raw'].encode())
    selected={'unit':'selected','text':'Agent, office','character_map':[
        {'start':0,'end':5,'operation':'Text','source':anchor(raw,1,6)},
        {'start':5,'end':13,'operation':'Text','source':anchor(raw,7,15)}]}
    return {'units':[raw]},selected


def test_selected_offset_is_mapped_across_deleted_brackets():
    graph,unit=fixture();before=deepcopy((graph,unit))
    result=selected_sources(graph,unit,3,9)
    assert [(r['selected_start'],r['selected_end'],r['source']['start'],r['source']['end'],r['source']['quote'])
            for r in result]==[(3,5,4,6,'nt'),(5,9,7,11,', of')]
    assert (graph,unit)==before


@pytest.mark.parametrize('kind',['hole','overlap','wrong-raw-offset','changed-selected','duplicate-original','bad-range'])
def test_invalid_selected_source_mapping_refuses(kind):
    graph,unit=fixture();start,end=3,9
    if kind=='hole':unit['character_map'].pop()
    elif kind=='overlap':unit['character_map'].append(deepcopy(unit['character_map'][0]))
    elif kind=='wrong-raw-offset':unit['character_map'][0]['source']['start']=0
    elif kind=='changed-selected':unit['text']='Adent, office'
    elif kind=='duplicate-original':graph['units'].append(deepcopy(graph['units'][0]))
    else:start=-1
    with pytest.raises(ValueError):selected_sources(graph,unit,start,end)


def test_role_review_does_not_swallow_an_operative_suffix():
    row={'page':111,'line':71,'selected_text':'(2) Auflaufende Zinsen. Falls ...',
         'spans':[{'start':0,'end':31,'quote':'(2) Auflaufende Zinsen. Falls ...'}]}
    with pytest.raises(ValueError,match='wording changed'):reviewed_roles(row)
