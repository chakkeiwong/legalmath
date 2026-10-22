"""Exact retained page coverage must constrain the known incomplete BES link."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import contract_assembly, reviewed_references
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from legalmath.prospectus.successor.bes_statement_scope import check, INTRO, RELEASE

REVIEW = {"kind":"DEVELOPMENT", "reviewer":"test fixture", "reason":"Retained exact-source engineering control"}
UNITS = json.loads((Path(__file__).parent/'fixtures/bes_statement_scope/units.json').read_text())


def fixture():
    graph = {"units":deepcopy(UNITS), "references":[], "context":"synthetic-test"}
    raw = {u['id']:u for u in graph['units']}
    intros = [raw[f'bes-base-2010:p37:l{n}'] for n in range(1,9)]
    targets = [u for u in graph['units'] if u['source_sha256']==RELEASE and u['page'] in (37,38)]
    spec = {'operations':[{'unit':u['id'],'source_text_sha256':u['text_sha256'],
                          'role':'OPERATIVE','reason':'Retained source scope'} for u in intros+targets]}
    assembly=contract_assembly.assemble(graph,spec)
    source=anchor(intros[4])
    row={'id':'source-scope','form':'external','source':source,'from_use':source['unit'],'language':'en',
         'targets':[{'source':anchor(u),'use':u['id'],'language':'en'} for u in targets],
         'authority':anchor(intros[0]),'questions':['Q1','Q2'],'reason':'Complete supplied original target scope',
         'discovery_ids':[]}
    packet={'version':'reviewed-references.v2','assembly_sha256':digest(assembly),'review':REVIEW,'references':[row]}
    return graph,assembly,packet


@pytest.mark.parametrize('version',['reviewed-references.v1','reviewed-references.v2'])
def test_complete_original_pages_pass_both_existing_routes(version):
    graph,assembly,packet=fixture()
    packet['version']=version
    if version.endswith('v1'):del packet['references'][0]['discovery_ids']
    dependencies,edges=reviewed_references.admit(graph,assembly,packet)
    row,=dependencies
    assert row['status']=='RESOLVED' and len(row['targets'])==len(edges)==304
    result=row['statement_scope_check']
    assert result['status']=='COMPLETE_RETAINED_PAGE_TARGETS'
    assert result['pages']==[37,38] and len(result['restriction'])==3
    assert '9H10' in result['source_clause'][1]['quote']
    assert '9M10' in result['release_identity_and_qualification'][1]['quote']
    assert 'Unaudited' in result['release_identity_and_qualification'][2]['quote']
    assert not result['independent_legal_acceptance'] and not row['automatic_discovery']


@pytest.mark.parametrize('mutation',[
    'one_unit','omit_last','omit_page','partial_quote','duplicate','extra_cover','cover_replacement',
    'wrong_language','wrong_source','wrong_use','changed_text','missing_raw_unit','hidden_target',
    'excluded_restriction','missing_clause','wrong_questions','changed_selected_text','duplicate_order',
    'duplicate_raw_identity','duplicate_selected_identity','wrong_form','wrong_edition','wrong_page',
])
def test_adverse_source_or_target_scope_refuses(mutation):
    graph,assembly,packet=fixture()
    row=packet['references'][0]
    targets=row['targets']
    raw={u['id']:u for u in graph['units']}
    selected={u['unit']:u for u in assembly['units']}
    if mutation=='one_unit':row['targets']=targets[:1]
    elif mutation=='omit_last':targets.pop()
    elif mutation=='omit_page':row['targets']=targets[:210]
    elif mutation=='partial_quote':targets[0]['source']=anchor(raw[targets[0]['use']],0,5)
    elif mutation=='duplicate':targets[-1]=deepcopy(targets[0])
    elif mutation in ('extra_cover','cover_replacement'):
        u=raw['bes-release-9m10:p1:l0']
        value={'source':anchor(u),'use':u['id'],'language':'en'}
        if mutation=='extra_cover':targets.append(value)
        else:targets[-1]=value
    elif mutation=='wrong_language':targets[0]['language']='pt'
    elif mutation=='wrong_source':targets[0]['source']['source_sha256']='0'*64
    elif mutation=='wrong_use':targets[0]['use']=targets[1]['use']
    elif mutation=='changed_text':
        u=raw[targets[0]['use']];u['raw']+=' changed';u['text_sha256']=digest(u['raw'].encode())
    elif mutation=='missing_raw_unit':graph['units'].remove(raw[targets[-1]['use']])
    elif mutation=='hidden_target':raw[targets[-1]['use']]['visible']=False
    elif mutation=='excluded_restriction':selected['bes-base-2010:p37:l3']['role']='EXCLUDED'
    elif mutation=='missing_clause':selected['bes-base-2010:p37:l8']['role']='UNKNOWN'
    elif mutation=='wrong_questions':selected[targets[-1]['use']]['questions']=['Q1']
    elif mutation=='changed_selected_text':selected[targets[0]['use']]['text']='altered'
    elif mutation=='duplicate_order':raw[targets[1]['use']]['order']=raw[targets[0]['use']]['order']
    elif mutation=='duplicate_raw_identity':graph['units'].append(deepcopy(raw[targets[0]['use']]))
    elif mutation=='duplicate_selected_identity':assembly['units'].append(deepcopy(selected[targets[0]['use']]))
    elif mutation=='wrong_form':row['form']='named'
    elif mutation=='wrong_edition':
        for u in graph['units']:
            if u['source_sha256']==RELEASE:u['source_sha256']='0'*64
    elif mutation=='wrong_page':raw[targets[-1]['use']]['page']=39
    packet['assembly_sha256']=digest(assembly)
    with pytest.raises(ValueError):
        reviewed_references.admit(graph,assembly,packet)


def test_target_order_cannot_hide_an_omission_and_complete_permutation_is_valid():
    graph,assembly,packet=fixture()
    packet['references'][0]['targets'].reverse()
    assert check(graph,assembly,packet['references'][0])['target_units']==304


def test_each_line_of_known_reference_is_guarded():
    graph,assembly,packet=fixture()
    raw={u['id']:u for u in graph['units']}
    for index in (5,6,7,8):
        row=deepcopy(packet['references'][0])
        row['source']=anchor(raw[f'bes-base-2010:p37:l{index}'])
        row['from_use']=row['source']['unit']
        row['targets']=row['targets'][:1]
        with pytest.raises(ValueError,match='all 304'):
            check(graph,assembly,row)
