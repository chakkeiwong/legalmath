"""Exact-source assisted readings and lexical proposals, with unresolved meaning.

An interval candidate records containment in a retained alternative. It does
not decide which declaration governs a use or supply a missing declaration.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

from .anchors import fields
from .contracts import digest
from .definition_discovery import discover

PROFILE_SHA256 = '0240723df59dcd885914486f75eee06df00b92164c7fe9cf4bde1c71f1279be4'
PREFIX = 'definition-source:'


def specification(structural=False):
    if structural:
        from .structural_roles import definition_specification
        return definition_specification('scopes')
    path = Path(__file__).with_name('definition_scopes_spec.json.gz')
    spec = json.loads(gzip.decompress(path.read_bytes()))
    if digest(spec) != PROFILE_SHA256:
        raise ValueError('Definition source registered profile changed')
    return spec


def packet(structural=False):
    spec=specification(structural)
    return {'profile':spec['profile'],'profile_sha256':digest(spec)}


def interval_candidates(use, alternatives):
    def valid(interval):
        return (isinstance(interval, (list, tuple)) and len(interval) == 2
                and all(type(v) is int for v in interval) and 0 <= interval[0] < interval[1])
    if (not valid(use) or not isinstance(alternatives, list)
            or any(not isinstance(row, list) or any(not valid(x) for x in row) for row in alternatives)):
        raise ValueError('Invalid definition membership interval')
    a, b = use
    return [i for i, extent in enumerate(alternatives) if any(x <= a and b <= y for x, y in extent)]


def admit(graph, selected, request):
    if 'definition_sources' not in request:
        return None
    value = request['definition_sources']
    fields(value, {'profile', 'profile_sha256', 'applications'}, {'profile', 'profile_sha256'})
    structural=value['profile'].endswith('.structural-v1')
    spec = specification(structural)
    profile_hash=digest(spec)
    if {k:value[k] for k in ('profile','profile_sha256')} != {'profile': spec['profile'], 'profile_sha256': profile_hash}:
        raise ValueError('Definition source requires the exact registered profile')
    assembly = selected['assembly']
    if structural:
        from .structural_roles import verify
        verify(graph,assembly,request.get('structural_roles'))
    text = assembly.get('continuous_text')
    if not isinstance(text, str):
        raise ValueError('Definition source requires actual selected continuous text')
    actual = {'source_graph_sha256': digest(graph), 'assembly_sha256': digest(assembly),
              'selected_contract_sha256': digest(selected['selected_contract']),
              'selected_text_sha256': hashlib.sha256(text.encode()).hexdigest()}
    if actual != spec['bindings']:
        raise ValueError('Definition source selection differs from retained evidence')
    lexical = discover({'text':text, 'text_sha256':actual['selected_text_sha256'], 'language':spec['language'],
        'regions':[{'id':'selected-contract','language':spec['language'],'selected':True,'start':0,'end':len(text)}]})
    exact = {}
    for i, use in enumerate(lexical['uses']):
        exact.setdefault((use['start'], use['end']), []).append(i)
    records = deepcopy(spec['records'])
    for record in records:
        alternatives = [[[spec['intervals'][index]['start'], spec['intervals'][index]['end']]
                         for index in scope['extent']] for scope in record['scope_alternatives']]
        for use in record['uses']:
            interval = spec['intervals'][use['interval']]
            a, b = interval['start'], interval['end']
            use.update(interval_candidates=interval_candidates([a,b], alternatives),
                lexical_exact=exact.get((a,b), []),
                lexical_overlap_only=[i for i, row in enumerate(lexical['uses'])
                                      if row['start'] < b and a < row['end']
                                      and (row['start'],row['end']) != (a,b)],
                governing_scope=None, meaning=None)
        record.update(status='UNRESOLVED', scope_admitted=False, meaning_admitted=False)
    report = {'version':'definition-source-review.v1', 'profile':spec['profile'], 'profile_sha256':profile_hash,
        **{k:deepcopy(spec[k]) for k in ('bindings','intervals','source_pieces','preamble_reading',
                                       'section_readings','known_misses','remaining')},
        'records':records, 'lexical':lexical,
        'membership_meaning':'Arithmetic containment in retained alternative intervals only',
        'scope_admitted':False, 'meaning_admitted':False, 'general_recall_established':False,
        'provenance_gaps_repaired':False}
    if 'applications' in value:
        from . import definition_applications
        report['application_supplement'] = definition_applications.admit(text,value['applications'],report)
    return report


def dependencies(report):
    if report is None:
        return []
    return [{'id':PREFIX+r['id'], 'kind':'DEFINITION_SOURCE', 'questions':['Q1','Q2'],
             'status':'UNRESOLVED', 'profile_sha256':report['profile_sha256'], 'record_sha256':digest(r),
             'uncertainties':['GOVERNING_SCOPE_NOT_ADMITTED','MEANING_NOT_ADMITTED']}
            for r in report['records']]


def verify_consumed(graph, selected, request, semantic):
    expected = admit(graph, selected, request)
    if expected is None:
        if 'definition_sources' in semantic:
            raise ValueError('Consumed definition source lacks supplied evidence')
        return None
    if digest(semantic.get('definition_sources')) != digest(expected):
        raise ValueError('Consumed definition source differs from reconstruction')
    required = dependencies(expected)
    observed = [d for d in semantic['dependencies'] if d['id'].startswith(PREFIX)]
    if digest(observed) != digest(required):
        raise ValueError('Consumed definition dependencies differ from reconstruction')
    ids = {d['id'] for d in required}
    shapes = {'Q1': set(), 'Q2': {'compulsory_common', 'possible_common', 'common_only'}}
    for key in ('Q1','Q2'):
        parent = semantic['questions'][key]
        if set(parent.get('subquestions', {})) != shapes[key]:
            raise ValueError('Consumed definition question shape differs from declared questions')
        for answer in (parent, *parent.get('subquestions', {}).values()):
            values = [i for i in answer['unresolved'] if i.startswith(PREFIX)]
            if set(values) != ids or len(values) != len(ids):
                raise ValueError('Consumed definition question hides or invents uncertainty')
            if answer['status'] not in ('UNKNOWN','CONFLICT') or answer['value'] is not None:
                raise ValueError('Consumed definition question resolves uncertainty')
    return expected
