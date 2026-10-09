from copy import deepcopy
import pytest
from scripts.prospectus_closure_fixtures import cross_document_fixture, REVIEW
from legalmath.prospectus.successor import source_graph, contract_assembly, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


@pytest.mark.parametrize('form',['named','relative','external','amendment'])
def test_reviewed_reference_scope_edition_and_authority(tmp_path, form):
    req = cross_document_fixture(tmp_path)
    graph = source_graph.build(req['bundle'],tmp_path)
    assembly = contract_assembly.assemble(graph,req['assembly'])
    a,b = [anchor(u) for u in graph['units']]
    row = {'id':'specified-reference','form':form,'source':a,'from_use':a['unit'],'language':'en',
           'targets':[{'source':b,'use':b['unit'],'language':'en'}],'authority':a,
           'questions':['Q1','Q2'],'reason':'Synthetic supplied reference, not automatic discovery'}
    req['reference_admission'] = {'version':'reviewed-references.v1','assembly_sha256':digest(assembly),
                                 'review':REVIEW,'references':[row]}
    result = service.assess(req,tmp_path)
    assert any(d['id']=='reviewed-reference:specified-reference' and d['status']=='RESOLVED' for d in result['dependencies'])
    changed = deepcopy(req)
    changed['reference_admission']['references'][0]['targets'][0]['source']['source_sha256'] = '0'*64
    with pytest.raises(ValueError,match='edition mismatch'):
        service.assess(changed,tmp_path)
    changed = deepcopy(req)
    changed['reference_admission']['references'][0]['authority']['quote'] = 'unrelated'
    with pytest.raises(ValueError,match='quote changed'):
        service.assess(changed,tmp_path)
    changed = deepcopy(req)
    changed['reference_admission']['references'][0]['targets'][0]['language'] = 'de'
    with pytest.raises(ValueError,match='language/question'):
        service.assess(changed,tmp_path)
    req['reference_admission']['references'].append({**row,'id':'return','form':'relative','source':b,'from_use':b['unit'],
        'authority':b,'targets':[{'source':a,'use':a['unit'],'language':'en'}]})
    answer = service.assess(req,tmp_path)['questions']['Q1']
    assert answer['status']=='UNKNOWN'
    assert any('cycle' in str(d) for d in service.assess(req,tmp_path)['dependencies'])
