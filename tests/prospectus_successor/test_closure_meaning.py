"""Hand-enumerated priority controls and corrected display/source admission."""
from copy import deepcopy
import itertools
import pytest
from scripts.prospectus_closure_fixtures import request, PREFIX, LOSS, REVIEW
from legalmath.prospectus.successor import source_graph, contract_assembly, clause_graph, service, corrections, annotation_bridge
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


def priority_fixture(tmp_path):
    req = request(tmp_path, [PREFIX + LOSS + ' The special rule overrides the ordinary rule.'])
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    nodes = clause_graph.nominate(assembly)
    loss = next(n for n in nodes if n['effect'] == 'principal_loss')
    loss.update(id='ordinary', conditions='ordinary_active')
    special = deepcopy(loss)
    special.update(id='special', polarity=False, conditions='special_active')
    final = deepcopy(loss)
    final.update(id='final', conditions='final_active')
    nodes[-1].update(effect='none', actor='issuer', affected='holder')
    req['clauses'] = nodes + [special, final]
    raw = graph['units'][0]
    scope = nodes[-1]['spans'][0]
    authority = anchor(raw, scope['start'], scope['end'])
    req['priority_admission'] = {'version':'reviewed-priorities.v1','assembly_sha256':digest(assembly),
        'review':REVIEW,'edges':[{'id':'special-over-ordinary','higher':'special','lower':'ordinary',
                                 'authority':authority,'reason':'Synthetic conditional legal priority'},
                                {'id':'final-over-special','higher':'final','lower':'special',
                                 'authority':authority,'reason':'Synthetic final priority'}]}
    return req


def test_acyclic_priority_matches_independent_three_rule_table(tmp_path):
    req = priority_fixture(tmp_path)
    for ordinary, special, final in itertools.product((False,True),repeat=3):
        req['observations'] = dict(ordinary_active=ordinary, special_active=special, final_active=final)
        # final defeats special; ordinary is suppressed only by an undefeated special.
        expect = 'YES' if final or ordinary and not special else 'NO'
        assert service.assess(req,tmp_path)['questions']['Q1']['status'] == expect


def test_priority_cycle_and_missing_authority_do_not_support_answer(tmp_path):
    req = priority_fixture(tmp_path)
    req['observations'] = dict(ordinary_active=True,special_active=True,final_active=True)
    edge = deepcopy(req['priority_admission']['edges'][0])
    edge.update(id='cycle',higher='ordinary',lower='final')
    req['priority_admission']['edges'].append(edge)
    answer=service.assess(req,tmp_path)['questions']['Q1']
    assert answer['status'] == 'UNKNOWN'
    assert any('cycle' in r for r in answer['unresolved'])
    req['priority_admission']['edges'][0]['authority']['quote']='unrelated'
    with pytest.raises(ValueError,match='quote changed'):
        service.assess(req,tmp_path)


def test_corrected_display_keeps_raw_quote_in_actual_service(tmp_path):
    raw_text = 'The N0tes are unsecured obligations of the Issuer.'
    display = 'The Notes are unsecured obligations of the Issuer.'
    req=request(tmp_path,[raw_text])
    graph=source_graph.build(req['bundle'],tmp_path)
    raw=graph['units'][0]
    req['correction_admission']={'version':'reviewed-corrections.v1','graph_sha256':digest(graph),'review':REVIEW,
        'entries':[{'id':'typo','source':anchor(raw),'operations':[{'kind':'replace','start':0,'end':len(raw_text),
                   'text':display,'reason':'Development whole-clause transcription control'}]}]}
    p1=service.source_product(req,tmp_path)
    assembly=service.construction_product(p1,tmp_path)['payload']['assembly']
    node=clause_graph.nominate(assembly)[0]
    node.update(effect='repayment',actor='issuer',affected='holder')
    packet=annotation_bridge.export(display,{'document':'d','source_sha256':raw['source_sha256'],
        'text_sha256':digest(display.encode())},[{'id':'a','label':'repayment','spans':[{'start':0,'end':len(display),'quote':display}]}],[])
    req['annotation_admission']={'version':'reviewed-annotation-meaning.v1','assembly_sha256':digest(assembly),'review':REVIEW,
        'packets':[{'id':'corrected','packet':packet,'map':[{'start':0,'end':len(display),'source':anchor(raw),
                'use':raw['id'],'correction':'typo'}]}],
        'meanings':[{'groups':['corrected:a'],'clause':{k:v for k,v in node.items() if k not in {'units','spans','quote','role','questions','origin'}}}]}
    report=service.assess(req,tmp_path)
    assert report['questions']['Q1']['status']=='NO'
    assert report['clause_graph']['nodes'][0]['quote']==raw_text
    assert report['source_map']['corrections']['entries'][0]['bbox'] is None
    export_record = {'packet':packet, 'map':[{'start':0,'end':len(display),'source':anchor(raw),'correction':'typo'}]}
    assert annotation_bridge.bound_evidence(report['source_map'], export_record) == [anchor(raw)]
    changed=deepcopy(req)
    changed['correction_admission']['entries'][0]['operations'][0]['kind']='uncertain'
    # A new correction alters construction binding, then semantic admission must
    # still reject the unverified reading after legitimately rebinding that parent.
    p1=service.source_product(changed,tmp_path)
    a=service.construction_product(p1,tmp_path)['payload']['assembly']
    changed['annotation_admission']['assembly_sha256']=digest(a)
    with pytest.raises(ValueError, match='uncertain text'):
        annotation_bridge.bound_evidence(p1['payload']['graph'], export_record)
    with pytest.raises(ValueError,match='uncertain text'):
        service.assess(changed,tmp_path)


def test_correction_insert_delete_and_partial_replacement_boundaries(tmp_path):
    req=request(tmp_path,['abXXcd'])
    graph=source_graph.build(req['bundle'],tmp_path)
    packet={'version':'reviewed-corrections.v1','graph_sha256':digest(graph),'review':REVIEW,'entries':[{
        'id':'edit','source':anchor(graph['units'][0]),'operations':[
            {'kind':'copy','start':0,'end':2,'text':'ab','reason':'copy'},
            {'kind':'delete','start':2,'end':4,'text':'','reason':'delete reviewed noise'},
            {'kind':'insert','start':4,'end':4,'text':'!','reason':'display insertion'},
            {'kind':'replace','start':4,'end':6,'text':'CD','reason':'reviewed replacement'}]}]}
    graph['corrections']=corrections.admit(graph,packet)
    assert graph['corrections']['entries'][0]['text']=='ab!CD'
    assert corrections.sources(graph,'edit',3,5)[0]['quote']=='cd'
    with pytest.raises(ValueError,match='Inserted'):
        corrections.sources(graph,'edit',0,5)
    with pytest.raises(ValueError,match='Partial replacement'):
        corrections.sources(graph,'edit',3,4)


def test_cross_document_exception_is_consumed_and_endpoints_are_bound(tmp_path):
    from scripts.prospectus_closure_fixtures import cross_document_fixture
    req = cross_document_fixture(tmp_path)
    for active, expected in [(False,'YES'), (True,'NO')]:
        req['observations'] = {'exempt':active}
        assert service.assess(req,tmp_path)['questions']['Q1']['status']==expected
    changed = deepcopy(req)
    changed['annotation_admission']['cross_document_relations'][0]['to']['packet_sha256'] = '0'*64
    with pytest.raises(ValueError, match='endpoint or packet changed'):
        service.assess(changed,tmp_path)
    changed = deepcopy(req)
    changed['annotation_admission']['cross_document_relations'][0]['to']['group'] = 'unrelated'
    with pytest.raises(ValueError, match='endpoint or packet changed'):
        service.assess(changed,tmp_path)
    req['annotation_admission']['cross_document_relations'] = []
    with pytest.raises(ValueError, match='relations differ'):
        service.assess(req,tmp_path)
