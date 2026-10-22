"""Complete remaining printed BASF bars; supplied scope is not discovery."""
from copy import deepcopy
from pathlib import Path

from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, segments

DOC = 'basf-base-september-2022-exchange'
FINAL = 'basf-2032-final'
IMAGES = 'docs/implementation/prospectus-basf-scope-repair/source-review-001/'


def lines(page, first, last, document=DOC):
    return [f'{document}:p{page}:l{i}' for i in range(first, last + 1)]


def final(page, first, last):
    return lines(page, first, last, FINAL)


# Fixed extents from original page images, before candidate use. The common
# paragraphs outside each printed bar are deliberately absent from its body.
ISSUER = final(2, 10, 12)
CLEARING = final(3, 36, 51)
DAYCOUNT = final(5, 15, 32)
SCOPES = [
    ('permanent-global', lines(108,15,29), lines(108,30,35), False, CLEARING),
    ('temporary-global', lines(108,36,48), lines(108,49,81), True, CLEARING),
    ('ngn', lines(109,11,13)+lines(109,16,22), lines(109,14,15)+lines(109,23,50), True, CLEARING),
    ('cgn', lines(109,51,60), lines(109,61,63), False, CLEARING),
    ('cds-ownership', lines(109,64,74), lines(109,75,88)+lines(110,1,39), False, CLEARING),
    ('finance-guarantee', lines(110,81,83)+lines(111,1,4), lines(110,84,85)+lines(111,5,21), False, ISSUER),
    ('single-rate', lines(111,25,32), lines(111,33,37), True, final(4,1,10)),
    ('different-rates', lines(111,38,45), lines(111,46,57), False, final(4,1,10)),
    ('annual-no-stub', lines(112,4,17), lines(112,18,19), True, DAYCOUNT),
    ('annual-short', lines(112,20,30), lines(112,31,32), False, DAYCOUNT),
    ('multiple-periods', lines(112,33,47), lines(112,48,52), False, DAYCOUNT),
    ('long-coupon', lines(112,53,63), lines(112,67,84), False, DAYCOUNT),
    ('reference-period', lines(112,64,66)+lines(113,1,12), lines(112,85,87)+lines(113,13,18), False, DAYCOUNT),
    ('actual-365', lines(113,19,22), lines(113,23,24), False, DAYCOUNT),
    ('bond-basis', lines(113,25,29), lines(113,30,39), False, DAYCOUNT),
    ('eurobond-basis', lines(113,40,44), lines(113,45,48), False, DAYCOUNT),
    ('cad-interest', lines(113,49,56), lines(113,57,67), False, final(3,20,23)+CLEARING),
    ('global-payment', lines(113,70,76), lines(113,77,83)+lines(113,89,92)+lines(114,2,2), True, CLEARING),
    ('temporary-payment', lines(113,84,88)+lines(114,1,1), lines(113,89,92)+lines(114,2,2), True, CLEARING),
    ('cds-payment', lines(114,3,12), lines(114,13,28), False, CLEARING),
    ('clearing-discharge', lines(114,40,50), lines(114,51,52), True, CLEARING),
    ('non-euro-payment-day', lines(114,59,64), lines(114,65,67), False, final(3,20,23)),
    ('euro-payment-day', lines(114,68,72), lines(114,73,76), True, final(3,20,23)+final(5,35,40)),
    ('rmb-settlement', lines(115,20,26), lines(115,27,73)+lines(116,1,84)+lines(117,1,60), False, final(3,20,23)),
    ('non-cds-agent', lines(124,1,7), lines(124,8,14), True, CLEARING+final(7,22,29)),
    ('cds-agent', lines(124,15,21), lines(124,22,25), False, CLEARING),
    ('calculation-agent', lines(124,26,42), lines(124,43,44), True, final(6,22,25)+final(3,20,23)+final(7,24,29)),
    ('basf-tax', lines(125,3,9), lines(125,10,50), True, ISSUER),
    ('finance-tax', lines(125,51,57), lines(125,58,71)+lines(126,1,27), False, ISSUER),
    ('basf-default', lines(126,34,40), lines(126,41,75)+lines(127,1,45), True, ISSUER),
    ('finance-default', lines(127,46,52), lines(127,53,86)+lines(128,1,46), False, ISSUER),
    ('basf-substitution', lines(128,49,55), lines(128,56,61), True, ISSUER),
    ('finance-substitution', lines(128,62,68), lines(128,69,74), False, ISSUER),
    ('basf-substitution-guarantee', lines(129,5,11), lines(129,12,22), True, ISSUER),
    ('finance-substitution-guarantee', lines(129,23,29), lines(129,30,32), False, ISSUER),
    ('representative-vote', lines(130,3,9), lines(130,10,11), True, final(7,32,39)),
    ('representative-terms', lines(130,12,18), lines(130,19,22), False, final(7,32,39)),
    ('finance-amendment', lines(131,32,38), lines(131,39,41), False, ISSUER),
    ('unlisted-notice', lines(132,13,19), lines(132,30,34), False, final(7,44,47)),
    ('finance-process-agent', lines(132,50,56), lines(132,57,66), False, ISSUER),
    ('german-controls', lines(133,13,21), lines(133,22,24), True, final(7,50,53)),
    ('english-controls', lines(133,25,33), lines(133,34,36), False, final(7,50,53)),
    ('german-only', lines(133,37,43), lines(133,44,44), False, final(7,50,53)+final(8,1,4)),
]


def packet_for(root, source, construction, *, diagnose=False):
    root = Path(root)
    payload = service.verify(source, 'P1')
    request, graph = payload['request'], payload['graph']
    selected = service.verify(construction, 'P2', request['bundle'], {'P1':source['sha256']})
    assembly = selected['assembly']
    raw = {u['id']:u for u in graph['units']}
    units = {u['unit']:u for u in assembly['units']}
    review = {'kind':'DEVELOPMENT', 'reviewer':'Codex original-page remaining margin review',
              'reason':'Full printed conditions, cross-page bodies and final-term selections; actual events and independent adjudication remain open.'}
    groups, edges, conflicts = [], [], []
    for identity, governors, body, applies, premises in SCOPES:
        if any(units[u]['role'] != 'INSTRUCTION' for u in governors):
            raise ValueError('Changed governor role: ' + identity)
        retained = [u for u in body if units[u]['role'] != 'EXCLUDED']
        if any(units[u]['role'] not in ('OPERATIVE','UNKNOWN') for u in retained):
            raise ValueError('Unreviewed body role: ' + identity)
        if bool(retained) != applies:
            conflicts.append({'group':identity, 'expected_selected':applies, 'retained':retained})
            if not diagnose:
                raise ValueError('Printed applicability conflicts with construction: ' + identity)
        spans, targets = [], []
        for u in retained:
            parts = segments(graph, units[u], _raw=raw)
            if ''.join(p['source']['quote'] for p in parts) != units[u]['text']:
                raise ValueError('Incomplete exact selected text: ' + u)
            spans.append({'unit':u, 'start':0, 'end':len(units[u]['text'])})
            targets.extend({'source':p['source'], 'use':{'unit':u, 'start':p['start'], 'end':p['end']}} for p in parts)
        printed = [anchor(raw[u], end=11) if u == DOC+':p132:l13' else anchor(raw[u]) for u in governors]
        group = {'id':identity, 'raw_governors':[anchor(raw[u]) for u in governors],
                 'printed_governors':printed, 'raw_body':[anchor(raw[u]) for u in body],
                 'applicable_under_supplied_final_terms':applies, 'premises':[anchor(raw[u]) for u in premises],
                 'selected_spans':spans, 'targets':targets,
                 'roles':{u:units[u]['role'] for u in body},
                 'character_maps':{u:deepcopy(units[u].get('character_map', [])) for u in body},
                 'excluded_units':[u for u in body if units[u]['role']=='EXCLUDED'],
                 'questions':['Q1','Q2'], 'actual_event_established':False}
        groups.append(group)
        if applies:
            edges.extend({'id':'basf-remaining-margin:'+identity+':'+g['unit'].split(':',1)[1],
                          'kind':'governs','from':g,'to':targets,'questions':['Q1','Q2'],
                          'reason':review['reason']} for g in printed)
    image_names = [f'base-{p}' for p in list(range(108,118))+list(range(124,134))]
    image_names += [f'final-{p}' for p in (2,3,4,5,6,7,8)]
    return {'version':'basf-remaining-margins.v1', 'P1':source['sha256'], 'P2':construction['sha256'],
            'graph_sha256':digest(graph), 'assembly_sha256':digest(assembly), 'review':review,
            'groups':groups, 'construction_conflicts':conflicts,
            'anomalies':[
                {'kind':'STATUTORY_INTEREST_FOOTNOTE', 'sources':[anchor(raw[u]) for u in lines(111,78,80)],
                 'reason':'Printed below a footnote rule, not a conditional margin bar; historical statute interpretation remains separate.'},
                {'kind':'NONPRINTING_EXTRACTION_NOISE', 'sources':[anchor(raw[DOC+':p132:l12']), anchor(raw[DOC+':p132:l13'],12)],
                 'reason':'Original p132 image contains neither i.i.i.1. nor i.i.i.2.; the printed Im Fall von prefix is retained separately.'}],
            'images':{IMAGES+n+'.png':digest((root/(IMAGES+n+'.png')).read_bytes()) for n in image_names},
            'governing_admission':{'version':'prospectus-layout.v2','graph_sha256':digest(graph),
                                   'documents':[],'review':review,'governing':edges},
            'automatic_scope':False,'independent_legal_acceptance':False}


def admit(root, source, construction, packet, interpretation):
    expected = packet_for(root, source, construction)
    if packet != expected:
        raise ValueError('Remaining BASF scope differs from full reviewed print and selected occurrences')
    result = deepcopy(interpretation)
    old = result['governing_admission']
    if old['version'] != 'prospectus-layout.v2' or old['documents']:
        raise ValueError('Prior scope is not the protected explicit-occurrence input')
    addition = deepcopy(packet['governing_admission'])
    addition['governing'] = deepcopy(old['governing']) + addition['governing']
    if len({e['id'] for e in addition['governing']}) != len(addition['governing']):
        raise ValueError('Duplicate printed governing identity')
    result['governing_admission'] = addition
    return result
