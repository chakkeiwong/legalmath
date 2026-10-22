"""Source-reviewed section-5 printed scope; supplied scope is not discovery."""
from copy import deepcopy
from pathlib import Path

from legalmath.prospectus.successor import basf_agents, service
from legalmath.prospectus.successor.admissions import structure
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, segments, uses

REL = 'docs/implementation/prospectus-execution-authority/attempts/basf-margins/attempt-002'
DOC = 'basf-base-september-2022-exchange'
FINAL = 'basf-2032-final'
IMAGES = 'docs/implementation/prospectus-basf-scope-repair/source-review-001/'


def lines(page, first, last, document=DOC):
    return [f'{document}:p{page}:l{i}' for i in range(first, last + 1)]


# Fixed source extents were read from the original pages before candidate use.
# Selected subspans are separately derived from the protected construction maps.
SCOPES = [
    ('tax-basf', lines(118,24,30), lines(118,31,58), True, lines(2,10,12,FINAL)),
    ('tax-finance', lines(118,59,65), lines(118,66,81)+lines(119,1,8), False, lines(2,10,12,FINAL)),
    ('control-put', lines(119,13,23), lines(119,24,81)+lines(120,1,8), True, lines(6,5,8,FINAL)),
    ('par-call', lines(120,9,21), lines(120,22,79), True, lines(6,9,25,FINAL)),
    ('early-call', lines(120,80,89)+lines(121,1,2), lines(120,90,99)+lines(121,3,34), True, lines(6,22,25,FINAL)),
    ('holder-put', lines(121,35,45), lines(121,46,83), False, lines(6,35,43,FINAL)),
    ('rmb-call', lines(122,1,17), lines(122,18,32), False, lines(2,10,12,FINAL)+lines(6,44,46,FINAL)+lines(6,54,55,FINAL)),
    ('minimal-outstanding', lines(122,33,42), lines(122,43,56), True, lines(6,47,50,FINAL)+lines(6,56,57,FINAL)),
    ('transaction-call', lines(122,57,70), lines(122,71,105)+lines(123,1,34), False, lines(6,51,53,FINAL)+lines(6,58,59,FINAL)),
    ('make-whole', lines(123,38,49), lines(123,50,78), True, lines(6,22,25,FINAL)),
]


def packet_for(root, source, construction):
    """Construct the independently fixed review including raw and selected scope."""
    root=Path(root)
    payload=service.verify(source,'P1')
    request,graph=payload['request'],payload['graph']
    selected=service.verify(construction,'P2',request['bundle'],{'P1':source['sha256']})
    assembly=selected['assembly']
    raw={u['id']:u for u in graph['units']}
    units={u['unit']:u for u in assembly['units']}
    review={'kind':'DEVELOPMENT','reviewer':'Codex original-page section-5 scope review',
            'reason':'Complete printed section-5 bars and final-term selections; current supplied construction preserved; event facts and independent adjudication remain open.'}
    groups=[]; edges=[]
    for identity,governors,body,applies,premises in SCOPES:
        if any(units[u]['role']!='INSTRUCTION' for u in governors):
            raise ValueError('Redemption margin instruction role changed: '+identity)
        retained=[u for u in body if units[u]['role']!='EXCLUDED']
        if any(units[u]['role'] not in ('OPERATIVE','UNKNOWN') for u in retained):
            raise ValueError('Unreviewed body role in margin scope: '+identity)
        if bool(retained)!=applies:
            raise ValueError('Margin applicability differs from protected final-term selection: '+identity)
        spans=[{'unit':u,'start':0,'end':len(units[u]['text'])} for u in retained]
        pieces=basf_agents.source_pieces(graph,units,spans)
        # No synthetic or unmapped selected characters may enter a scope.
        for span in spans:
            actual=[p['source']['quote'] for p in pieces if p['use']==span['unit']]
            if ''.join(actual)!=units[span['unit']]['text']:
                raise ValueError('Incomplete selected-source accounting: '+span['unit'])
        targets=[{'source':p['source'],
                  'use':{'unit':u,'start':p['start'],'end':p['end']}}
                 for u in retained for p in segments(graph,units[u])]
        group={'id':identity,'governors':[anchor(raw[u]) for u in governors],
               'raw_body':[anchor(raw[u]) for u in body],
               'applicable_under_supplied_final_terms':applies,
               'premises':[anchor(raw[u]) for u in premises],
               'selected_spans':spans,'selected_pieces':pieces,
               'roles':{u:units[u]['role'] for u in body},
               'character_maps':{u:deepcopy(units[u].get('character_map',[])) for u in body},
               'excluded_units':[u for u in body if units[u]['role']=='EXCLUDED'],
               'questions':['Q1','Q2'],'actual_event_established':False}
        groups.append(group)
        if applies:
            for governor in group['governors']:
                edges.append({'id':'basf-redemption-margin:'+identity+':'+governor['unit'].split(':',1)[1],
                              'kind':'governs','from':governor,'to':targets,
                              'questions':['Q1','Q2'],'reason':review['reason']})
    return {'version':'basf-redemption-margins.v1','P1':source['sha256'],'P2':construction['sha256'],
            'graph_sha256':digest(graph),'assembly_sha256':digest(assembly),
            'review':review,'groups':groups,
            'shared_tax_notice_outside_both_bars':[anchor(raw[u]) for u in lines(119,9,12)],
            'tax_amount_definition_outside_make_whole_margin':[anchor(raw[u]) for u in lines(123,35,37)],
            'images':{IMAGES+name+'.png':digest((root/(IMAGES+name+'.png')).read_bytes())
                      for name in [*[f'base-{i}' for i in range(118,124)],'final-2','final-6']},
            'governing_admission':{'version':'prospectus-layout.v2','graph_sha256':digest(graph),
                                   'documents':[],'review':review,'governing':edges},
            'automatic_scope':False,'whole_margin_inventory_complete':False}


def admit(root, source, construction, packet, interpretation):
    """Validate the complete candidate against the fixed source extent."""
    expected=packet_for(root,source,construction)
    if packet!=expected:
        raise ValueError('BASF redemption margin differs from complete reviewed source scope')
    graph=source['payload']['graph']
    addition=packet['governing_admission']
    structure(graph,addition)
    result=deepcopy(interpretation)
    old=result.get('governing_admission')
    if old:
        structure(graph,old)
        if old['documents']:
            raise ValueError('Redemption scope cannot silently replace layout projections')
        addition=deepcopy(addition)
        old_edges=deepcopy(old['governing'])
        if old['version']=='prospectus-layout.v1':
            assembly=construction['payload']['assembly']
            prior_uses={}
            for edge in old_edges:
                targets=[]
                for source in edge['to']:
                    matches=[]
                    for q in edge['questions']:
                        key=(q,digest(source))
                        if key not in prior_uses:
                            prior_uses[key]=uses(graph,assembly,source,question=q)
                        matches.append(prior_uses[key])
                    if not all(len(m)==1 and m==matches[0] for m in matches):
                        raise ValueError('Prior margin target lacks an unambiguous selected occurrence')
                    targets.append({'source':source,'use':{k:matches[0][0][k] for k in ('unit','start','end')}})
                edge['to']=targets
        addition['governing']=old_edges+addition['governing']
    structure(graph,addition)
    result['governing_admission']=addition
    return result


def interpretation_input(root, source, construction, interpretation):
    """Load the sealed review; future product use must preserve its inputs."""
    from legalmath.prospectus.successor.contracts import read
    root=Path(root); here=root/REL
    manifest=read(here/'outputs.json')
    for name in ('v3/scope-review.json','SOURCE-REVIEW.md'):
        if digest((here/name).read_bytes())!=manifest[name]:
            raise ValueError('Retained redemption margin evidence changed: '+name)
    return admit(root,source,construction,read(here/'v3/scope-review.json'),interpretation)
