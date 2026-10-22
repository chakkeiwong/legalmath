"""Source-specific H1 reference availability with retained historical limits."""
from copy import deepcopy
import json

from .successor.contracts import digest
from .successor.anchors import fields

VERSION = 'bes-h1-reference-availability.v1'
GRAPH_SHA256 = '1ae6e118e00ea304349760480917e37ac0ee22b8b4ead6a532e8e1b5acd3559f'
PRIOR_SHA256 = '85d689094777d18d8dee562af3af686277d308a5c8eca7f30819c8b8c7538ff8'
MAP_SHA256 = 'c9a4f49f1f9949437aa6bf7be0734e18cb9b936d4bd723ba64dcf9f8f70309e8'
DOCUMENT = 'bes-interim-h1-2010'
SOURCE = 'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
LIMITS = {'source_specific_supplied_review': True, 'address_availability_only': True,
    'historical_statuses_replaced': False, 'financial_reconciliation_established': False,
    'referenced_claims_proved': False, 'source_authenticity_established': False,
    'legal_incorporation_selected': False, 'implicit_references_complete': False,
    'automatic_interpretation_proved': False, 'original_task_complete': False}


def compact(value):
    return digest(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())


def at(value, pointer):
    if not isinstance(pointer,str) or not pointer.startswith(('/answer/','/cash_flow_review/')):
        raise ValueError('H1 reference target must identify an existing answer field')
    for token in pointer[1:].split('/'):
        key=token.replace('~1','/').replace('~0','~')
        if isinstance(value,list) and key.isdigit() and int(key)<len(value):
            value=value[int(key)]
        elif isinstance(value,dict) and key in value:
            value=value[key]
        else:
            raise ValueError('H1 reference target missing')
    return value


def check_source(source, units):
    unit=units.get(source.get('id'))
    if unit is None or unit['document']!=DOCUMENT or unit['source_sha256']!=SOURCE or not unit['visible']:
        raise ValueError('H1 reference original source changed')
    expected={k:unit[k] for k in ('id','document','source_sha256','page','order','bbox')}|{'quote':unit['raw']}
    if source!=expected:
        raise ValueError('H1 reference original source changed')
    return unit


def evaluate(graph, prior, profile, *, expected_profile_sha256):
    required={'version','graph_sha256','prior_sha256','map'}
    fields(profile,required,required)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['graph_sha256']!=GRAPH_SHA256 or digest(graph)!=GRAPH_SHA256
            or profile['prior_sha256']!=PRIOR_SHA256 or digest(prior)!=PRIOR_SHA256):
        raise ValueError('Pinned H1 reference profile, graph or complete prior answer changed')
    value=profile['map']
    if value['limits']!=LIMITS:
        raise ValueError('H1 reference availability cannot prove financial or legal correctness')
    if compact(value)!=MAP_SHA256:
        raise ValueError('H1 reference map differs from reviewed original addresses and current fields')
    units={u['id']:u for u in graph['units']}
    if len(units)!=len(graph['units']):
        raise ValueError('Duplicate H1 reference source identity')
    ordered=sorted((u for u in units.values() if u['document']==DOCUMENT),key=lambda u:(u['page'],u['order']))
    for row in value['registry']:
        head=check_source(row['heading'],units)
        end=check_source(row['end_exclusive'],units)
        selected=[u for u in ordered if (head['page'],head['order'])<=(u['page'],u['order'])<(end['page'],end['order'])]
        if len(selected)!=row['source_unit_count'] or compact(selected)!=row['source_units_sha256']:
            raise ValueError('H1 reference declared span changed')
        identities={u['id'] for u in selected}
        for section in row['delivered_sections']:
            at(prior,section['path'])
            for ref in section['direct_sources']:
                target=at(prior,ref['path'])
                if (ref['unit'] not in identities or compact(target)!=ref['sha256']
                        or units[ref['unit']]['raw'][ref['start']:ref['end']]!=target['quote']):
                    raise ValueError('H1 reference delivered source association changed')
    numbers={r['number'] for r in value['registry']}
    for row in value['references']:
        for source in row['sources']:
            check_source(source,units)
        if not set(row['destinations'])<=numbers:
            raise ValueError('H1 reference declaration missing')
        if row['kind']=='STATEMENT_NOTE_COLUMN' and (
                at(prior,row['reference_path'])!=row['original_note_anchor']
                or at(prior,row['row_label_path'])!=row['row_label']):
            raise ValueError('H1 statement reference context changed')
    for row in value['historical_states']:
        for source in row['sources']:
            check_source(source,units)
        if at(prior,row['historical_flag']['path'])!=row['historical_flag']['value']:
            raise ValueError('H1 historical reference status changed')
        for target in row['targets']:
            if compact(at(prior,target['path']))!=target['sha256']:
                raise ValueError('H1 current reference reading changed')
    for row in value['discrepancies']:
        for source in row['sources']:
            check_source(source,units)
        for target in row['targets']:
            at(prior,target)
    return {'version':VERSION,'status':'SUPPLIED_REFERENCE_ADDRESS_AVAILABILITY',
        'graph_sha256':GRAPH_SHA256,'prior_sha256':PRIOR_SHA256,'profile_sha256':digest(profile),
        'map_sha256':MAP_SHA256,'map':deepcopy(value)}


def explain(review):
    if review['version']!=VERSION or review['map_sha256']!=MAP_SHA256 or compact(review['map'])!=MAP_SHA256:
        raise ValueError('H1 reference explanation changed')
    return {'meaning':'The report references below identify printed note or policy addresses and the current readings available for them.',
        'historical_statuses':'Earlier unresolved labels describe earlier readings and remain unchanged. The following explanations identify later material and the questions it leaves open.',
        'current_states':deepcopy(review['map']['historical_states']),
        'source_discrepancies':deepcopy(review['map']['discrepancies']),
        'scope':'This supplied review covers explicit note mentions on pages51–173 and delivered statement-note fields. Implicit references and complete meaning remain outside this finite inventory.',
        'remaining':'Source authority, controlling-language priority, incorporation alternatives, clipped equity values and the individual-statement unit conflict remain unresolved. Reference availability does not establish financial reconciliation or legal effect.',
        'limits':deepcopy(LIMITS)}
