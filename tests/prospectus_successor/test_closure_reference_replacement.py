"""Recognized citations must reach the reviewed consumer without scope leakage."""
from copy import deepcopy
import pytest
from scripts.prospectus_closure_fixtures import request, REVIEW, PREFIX
from legalmath.prospectus.successor import source_graph, contract_assembly, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


def fixture(tmp_path):
    req = request(tmp_path, ['Condition 2 applies.', PREFIX])
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    first, second = [anchor(u) for u in graph['units']]
    row = {'id':'actual-citation', 'form':'named', 'source':first, 'from_use':first['unit'],
           'language':'en', 'targets':[{'source':second, 'use':second['unit'], 'language':'en'}],
           'authority':first, 'questions':['Q1'], 'reason':'Explicit synthetic reference decision',
           'discovery_ids':[graph['references'][0]['id']]}
    req['reference_admission'] = {'version':'reviewed-references.v2', 'assembly_sha256':digest(assembly),
                                  'review':REVIEW, 'references':[row]}
    return req, graph, assembly


def test_reference_replacement_is_question_local(tmp_path):
    req, graph, _ = fixture(tmp_path)
    deps = service.assess(req,tmp_path)['dependencies']
    unresolved = [d for d in deps if d['status']=='UNRESOLVED']
    assert unresolved and all(d['questions']==['Q2'] for d in unresolved)
    assert next(d for d in deps if d['id']=='reviewed-reference:actual-citation')['status']=='RESOLVED'
    req['reference_admission']['references'][0]['questions']=['Q1','Q2']
    assert all(d['status']=='RESOLVED' for d in service.assess(req,tmp_path)['dependencies'])
    # v1 remains additive: an old packet never silently claims a proposal.
    req['reference_admission']['version']='reviewed-references.v1'
    del req['reference_admission']['references'][0]['discovery_ids']
    assert any(d['status']=='UNRESOLVED' for d in service.assess(req,tmp_path)['dependencies'])


@pytest.mark.parametrize('change',['missing','foreign','outside','duplicate'])
def test_reference_replacement_rejects_invalid_discovery_claim(tmp_path,change):
    req, graph, _ = fixture(tmp_path)
    row=req['reference_admission']['references'][0]
    if change=='missing':
        row['discovery_ids']=['invented-reference']
    elif change=='foreign':
        row['source']=row['authority']=anchor(graph['units'][1])
        row['from_use']=row['source']['unit']
    elif change=='outside':
        row['source']=anchor(graph['units'][0],12)
    else:
        req['reference_admission']['references'].append({**deepcopy(row),'id':'duplicate-decision'})
    with pytest.raises(ValueError,match='discovered source|multiple reviewed'):
        service.assess(req,tmp_path)


def test_reference_replacement_does_not_cover_other_selected_copy(tmp_path):
    req, graph, _ = fixture(tmp_path)
    a,b=[anchor(u) for u in graph['units']]
    req['assembly']['ast']={'version':'contract-ast.v2','root':'seq','nodes':[
        {'id':'seq','kind':'Sequence','children':['a','a','b']},
        {'id':'a','kind':'Text','source':a},{'id':'b','kind':'Text','source':b}]}
    assembly=contract_assembly.assemble(graph,req['assembly'])
    rows=assembly['units']
    packet=req['reference_admission']
    packet['assembly_sha256']=digest(assembly)
    row=packet['references'][0]
    row.update(from_use=rows[0]['unit'],authority=b,questions=['Q1','Q2'])
    row['targets'][0]['use']=rows[2]['unit']
    deps=service.assess(req,tmp_path)['dependencies']
    remaining=[d for d in deps if d['status']=='UNRESOLVED' and d.get('source_use')]
    assert len(remaining)==1 and remaining[0]['source_use']['unit']==rows[1]['unit']


def test_reference_edges_from_different_questions_do_not_form_cycle(tmp_path):
    req=request(tmp_path,[PREFIX,'A separate supplied definition.'])
    graph=source_graph.build(req['bundle'],tmp_path)
    assembly=contract_assembly.assemble(graph,req['assembly'])
    a,b=[anchor(u) for u in graph['units']]
    rows=[]
    for i,(source,destination,question) in enumerate(((a,b,'Q1'),(b,a,'Q2'))):
        rows.append({'id':str(i),'form':'relative','source':source,'from_use':source['unit'],
            'language':'en','authority':source,'questions':[question],'reason':'Separate question dependency',
            'targets':[{'source':destination,'use':destination['unit'],'language':'en'}], 'discovery_ids':[]})
    req['reference_admission']={'version':'reviewed-references.v2','assembly_sha256':digest(assembly),
        'review':REVIEW,'references':rows}
    assert all(d['status']=='RESOLVED' for d in service.assess(req,tmp_path)['dependencies'])
    rows[1]['questions']=['Q1']
    assert any('cycle' in str(d) for d in service.assess(req,tmp_path)['dependencies'])
