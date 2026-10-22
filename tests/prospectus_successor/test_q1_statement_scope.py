"""Q1 coverage must preserve its own supplement, periods and source set."""
from copy import deepcopy
import pytest

from legalmath.prospectus.successor import contract_assembly, reviewed_references
from legalmath.prospectus.successor.bes_q1_scope import INTRO, RELEASE, check
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_q1_scope_program import source_units, controls

UNITS=[u for u in source_units()['units'] if
       (u['source_sha256']==INTRO and u['page'] in (1,3)) or
       (u['source_sha256']==RELEASE and u['page'] in (1,36,37))]


def fixture():
    graph={'units':deepcopy(UNITS),'references':[],'context':'synthetic-test'}
    asm=contract_assembly.assemble(graph,{'operations':[
        {'unit':u['id'],'source_text_sha256':u['text_sha256'],'role':'OPERATIVE','reason':'Retained Q1 scope'} for u in graph['units']]})
    raw={u['id']:u for u in graph['units']}
    row={'id':'finite-q1','form':'external','source':anchor(raw['bes-supplement-4:p3:l28']),
         'from_use':'bes-supplement-4:p3:l28','language':'en',
         'targets':[{'source':anchor(u),'use':u['id'],'language':'en'} for u in graph['units'] if u['source_sha256']==RELEASE and u['page'] in (36,37)],
         'authority':anchor(raw['bes-supplement-4:p1:l22']),'questions':['Q1','Q2'],
         'reason':'Complete retained Q1 statements, preserving independent source unknowns','discovery_ids':[]}
    return graph,asm,{'version':'reviewed-references.v2','assembly_sha256':digest(asm),
                     'review':{'kind':'DEVELOPMENT','reviewer':'test fixture','reason':'Finite Q1 scope control'},'references':[row]}


@pytest.mark.parametrize('version',['v1','v2','v3'])
def test_complete_original_scope_preserves_unaudited_quarter(version):
    graph,asm,p=fixture(); p['version']='reviewed-references.'+version
    if version=='v1': del p['references'][0]['discovery_ids']
    deps,edges=reviewed_references.admit(graph,asm,p)
    scope=deps[0]['statement_scope_check']
    assert len(edges)==scope['target_units']==299 and scope['pages']==[36,37]
    assert scope['source_authenticity']=='NOT_ESTABLISHED' and scope['incorporation_status']=='UNRESOLVED'
    assert not scope['independent_legal_acceptance'] and scope['context_pages_do_not_expand_incorporation']
    assert 'three months ended 31' in scope['source_clause'][1]['quote']
    assert 'Unaudited financial information under IFRS as implemented by the European Union' in scope['release_identity_and_qualification'][2]['quote']
    assert 'for information purposes only.' in scope['restriction'][-1]['quote']


def test_all_declared_adverse_scope_changes_refuse():
    graph,asm,p=fixture(); found=controls(graph,asm,p)
    assert len(found)==15 and all(x['rejected'] for x in found)


@pytest.mark.parametrize('line',range(25,38))
def test_all_q1_clause_and_table_lines_are_guarded(line):
    graph,asm,p=fixture(); row=p['references'][0]
    key='bes-supplement-4:p3:l'+str(line)
    row['source']=anchor(next(u for u in graph['units'] if u['id']==key)); row['from_use']=key
    row['targets']=[v for v in row['targets'] if v['use']!='bes-release-q111:p36:l6']
    with pytest.raises(ValueError,match='all299'):
        reviewed_references.admit(graph,asm,p)


@pytest.mark.parametrize('key',['bes-supplement-4:p1:l22','bes-supplement-4:p1:l25',
                               'bes-supplement-4:p3:l0','bes-supplement-4:p3:l24','bes-supplement-4:p3:l39'])
def test_shared_purpose_annual_and_finance_clauses_do_not_select_q1(key):
    graph,asm,p=fixture(); row=p['references'][0]
    row['source']=anchor(next(u for u in graph['units'] if u['id']==key)); row['from_use']=key
    assert check(graph,asm,row) is None


@pytest.mark.parametrize('change',['duplicate_raw','duplicate_selected','duplicate_order','wrong_edition','changed_restriction','changed_cover','wrong_language'])
def test_source_and_selection_corruption_refuses(change):
    graph,asm,p=fixture(); row=p['references'][0]; raw={u['id']:u for u in graph['units']}
    if change=='duplicate_raw': graph['units'].append(deepcopy(raw[row['targets'][0]['use']]))
    elif change=='duplicate_selected': asm['units'].append(deepcopy(asm['units'][0]))
    elif change=='duplicate_order': raw[row['targets'][1]['use']]['order']=0
    elif change=='wrong_edition':
        for u in graph['units']:
            if u['source_sha256']==RELEASE: u['source_sha256']='0'*64
    elif change in ('changed_restriction','changed_cover'):
        u=raw['bes-supplement-4:p3:l29' if change=='changed_restriction' else 'bes-release-q111:p1:l2']
        u['raw']+=' changed'; u['text_sha256']=digest(u['raw'].encode())
    else: row['targets'][0]['language']='pt'
    p['assembly_sha256']=digest(asm)
    with pytest.raises(ValueError): reviewed_references.admit(graph,asm,p)


def test_complete_permutation_preserves_scope():
    graph,asm,p=fixture(); p['references'][0]['targets'].reverse()
    assert reviewed_references.admit(graph,asm,p)[0][0]['statement_scope_check']['target_units']==299
