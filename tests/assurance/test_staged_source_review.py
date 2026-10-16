from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import staged_source_review as stage
from legalmath.interpretation.assurance.decomposition import merge_pieces
from legalmath.interpretation.assurance.semantics import merge_inventories, inventory_findings
from .test_evidence_route import two_pieces


def reviewed(request):
    p=request['source_packet']
    return {'request_binding':request['request_binding'],'checked_unit_ids':[u['unit_id'] for u in p['units']],
        'claims':[{'claim_id':c['claim_id'],'claim_hash':digest(c),'assessment':'QUESTIONED',
            'source_reading':'Reconciliation does not establish the governing ownership premise.',
            'support':c['evidence'],'contrary':[{'unit_id':p['units'][-1]['unit_id'],'quote':p['units'][-1]['text']}],
            'qualifications':['Record role and actor remain material.'],'missing_authorities':['Governing ownership rule'],
            'nonlocal_claim_ids':[r['claim_id'] for r in request['claim_catalogue'] if r['claim_id']!=c['claim_id']]}
            for c in request['claims']], 'unresolved_questions':['Fulfillment remains unformalized.']}


def test_assigned_claim_scope_dependencies_omissions_and_search_delivery(tmp_path):
    p,parts=two_pieces();inv=merge_pieces(p,parts);seen=[]
    def invoke(request,model,validate):
        seen.append(request)
        if request['task']=='REVIEW_SOURCE_CLAIMS':value=reviewed(request)
        else:
            value={'checked_unit_ids':[u['unit_id'] for u in p['units']], 'issues':[],
                'unresolved_questions':['Actor and governing standard still unresolved.']}
            if request['task']=='REVIEW_SOURCE_INTERACTIONS':
                value.update(request_binding=request['request_binding'],checked_claim_ids=[c['claim_id'] for c in request['claims']])
                value['checked_edges']=[{'claim_id':a,'related_claim_id':b} for a,b in request['required_edges']]
        return validate(value)
    result=stage.run(p,'atomic-reader',inv,invoke,tmp_path,batch_size=1)
    assert [r['task'] for r in seen]==['REVIEW_SOURCE_CLAIMS']*2+['REVIEW_SOURCE_INTERACTIONS','REVIEW_SOURCE_OMISSIONS']
    assert all(r['source_packet']==p for r in seen)
    assert all(len(r['claims'])==1 for r in seen[:2])
    assert seen[2]['claims']==inv['claims'] or set(c['claim_id'] for c in seen[2]['claims'])==set(c['claim_id'] for c in inv['claims'])
    inventories={'atomic-reader':result,'qualification-reader':deepcopy(result)}
    claims=merge_inventories(inventories)
    view=stage.search_view(inventories,claims)
    assert len(view['records'])==len(claims)
    assert all(len(r['readings'])==2 and r['readings'][0]['review']['contrary'] for r in view['records'])
    assert any(f['kind']=='CROSS_PIECE_UNRESOLVED' for f in inventory_findings(p,inventories))
    assert inv['claims']==result['claims'] and inv['uncertainties']==result['uncertainties']


@pytest.mark.parametrize('fault',['missing_claim','foreign_claim','changed_claim','missing_unit','foreign_dependency','false_quote'])
def test_false_completeness_and_unseen_dependency_are_rejected(fault):
    p,parts=two_pieces();inv=merge_pieces(p,parts)
    req=stage.review_request(p,'atomic-reader',inv,[inv['claims'][0]['claim_id']]);value=reviewed(req)
    if fault=='missing_claim':value['claims']=[]
    if fault=='foreign_claim':value['claims'][0]['claim_id']=inv['claims'][1]['claim_id']
    if fault=='changed_claim':value['claims'][0]['claim_hash']='0'*64
    if fault=='missing_unit':value['checked_unit_ids'].pop()
    if fault=='foreign_dependency':value['claims'][0]['nonlocal_claim_ids']=['invented']
    if fault=='false_quote':value['claims'][0]['support'][0]['quote']='Unquoted legal warrant'
    with pytest.raises(LegalMathError):stage.validate_review(value,req,inv)


def test_interaction_requires_both_exact_endpoints():
    p,parts=two_pieces();inv=merge_pieces(p,parts);ids=[c['claim_id'] for c in inv['claims']]
    req=stage.interaction_request(p,'reader',inv,[ids])
    value={'request_binding':req['request_binding'],'checked_claim_ids':ids[:1],
        'checked_edges':[{'claim_id':ids[0],'related_claim_id':ids[1]}],
        'checked_unit_ids':[u['unit_id'] for u in p['units']],'issues':[],'unresolved_questions':[]}
    with pytest.raises(LegalMathError):stage.validate_interaction(value,req,inv)
