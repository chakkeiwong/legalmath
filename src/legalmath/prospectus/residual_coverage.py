"""Explain exact reviewed heading spans without changing legal interpretation."""
from copy import deepcopy
import gzip
import json

from .successor.anchors import fields
from .successor.contracts import bound_path, digest

VERSION = 'basf-residual-coverage.v1'
KEY = 'residual_coverage_review'
REGISTERED_PROFILE_SHA256 = '350b4c3fe428648daf3d9f7341852757c39adc01ffdba2d0a31dfc177b9096f9'


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'headings',
            'h43', 'legal_scope_resolved', 'whole_task_complete'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or digest(profile) != REGISTERED_PROFILE_SHA256
            or profile['products_sha256'] != digest(products)
            or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k:v for k,v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Registered coverage profile or complete baseline changed')
    if profile['legal_scope_resolved'] is not False or profile['whole_task_complete'] is not False:
        raise ValueError('Coverage classification cannot establish legal completeness')
    graph = products['P1']['payload']['graph']
    selected = products['P2']['payload']
    assembly = selected['assembly']
    clauses = products['P3']['payload']['clauses']
    from .successor.meaning_coverage import explain
    coverage = explain(graph, selected['selected_contract'], assembly, clauses)
    if ordinary.get('meaning_coverage') != coverage:
        raise ValueError('Original occurrence coverage differs from source reconstruction')
    units = {r['unit']:r for r in assembly['units']}
    nodes = {n['id']:n for n in clauses['nodes']}
    if len(units) != len(assembly['units']) or len(nodes) != len(clauses['nodes']):
        raise ValueError('Duplicate source identities')
    headings = profile['headings']
    if not isinstance(headings, list) or len(headings) != 24:
        raise ValueError('Complete finite 24-heading review required')
    positions = {}
    seen = set()
    for row in headings:
        identity = row['node_id']
        if identity in seen or identity not in nodes:
            raise ValueError('Missing or duplicate reviewed heading node')
        seen.add(identity)
        node = nodes[identity]
        if (digest(node) != row['node_sha256'] or node['effect'] != 'unknown'
                or node['quote'] != row['quote'] or node['spans'] != row['spans']):
            raise ValueError('Reviewed heading source extent changed')
        for span, context in zip(row['spans'], row['contexts'], strict=True):
            unit = units[span['unit']]
            if context != {'unit':span['unit'], 'text':unit['text'], 'role':unit['role']}:
                raise ValueError('Adjacent source wording or role changed')
            start, end = span['start'], span['end']
            fragment = unit['text'][start:end]
            chars = {i for i in range(start, end) if not unit['text'][i].isspace()}
            if chars and (unit['role'] != 'OPERATIVE' or not unit['text'][end:].strip()):
                raise ValueError('Whole operative unit cannot become a heading')
            if positions.get(span['unit'], set()) & chars:
                raise ValueError('Heading spans overlap')
            positions.setdefault(span['unit'], set()).update(chars)
    pending = coverage['selected_body_pending']
    heading_units = []
    substantive = []
    for row in pending:
        count = len(positions.get(row['unit'], set()))
        if count:
            if row['role_unresolved'] or row['unknown_characters'] != count or row['uncovered_characters']:
                raise ValueError('Heading explanation would hide unresolved source content')
            heading_units.append(row['unit'])
        else:
            substantive.append(deepcopy(row))
    prefix = 'basf-base-september-2022-exchange:'
    missing_agent = [prefix+'p124:l43', prefix+'p124:l44']
    default_units = [prefix+'p127:l'+str(i) for i in range(12,17)]
    if {r['unit'] for r in substantive} != set(missing_agent+default_units):
        raise ValueError('Substantive residual inventory changed')
    review = ordinary.get('default_f_review', {})
    if (review.get('source_meaning_promoted') is not False
            or review.get('actual_default_established') is not False
            or [e['unit'] for e in review.get('unresolved_default_f', {}).get('evidence', [])] != default_units):
        raise ValueError('Conditional default source or uncertainty changed')
    h43 = profile['h43']
    raw = bound_path(root, h43['ledger_path']).read_bytes()
    if digest(raw) != h43['ledger_file_sha256']:
        raise ValueError('Original reference reconciliation changed')
    ledger = json.loads(gzip.decompress(raw))
    matches = [r for r in ledger['records'] if r['family'] == 'historical_candidate_lines' and r['index'] == 43]
    if len(matches) != 1 or digest(matches[0]) != h43['original_record_sha256'] or len(ledger['records']) != 60:
        raise ValueError('Original H43 provenance or denominator changed')
    anchors = [r['original'] for r in matches[0]['source_pieces']]
    if anchors != h43['source_pieces']:
        raise ValueError('Original H43 source anchors changed')
    source = {u['id']:u for u in graph['units']}
    for anchor in anchors:
        unit = source[anchor['unit']]
        if unit['source_sha256'] != anchor['source_sha256'] or unit['raw'][anchor['start']:anchor['end']] != anchor['quote']:
            raise ValueError('Original H43 source quotation changed')
    if any(r['id'] == 'H43' for r in ordinary['statutory_references']['records']):
        raise ValueError('H43 reading changed; a revised reconciliation is required')
    return {'version':VERSION, 'profile_sha256':digest(profile),
            'products_sha256':digest(products), 'ordinary_answer_sha256':digest(ordinary),
            'original_coverage_sha256':digest(coverage), 'original_pending_count':len(pending),
            'heading_units':sorted(heading_units),
            'heading_nonspace_characters':sum(len(v) for v in positions.values()),
            'reviewed_heading_spans':deepcopy(headings), 'substantive_pending':substantive,
            'unresolved_nonspace_characters':sum(r['unknown_characters'] for r in substantive),
            'default_conditionally_modeled_units':default_units, 'missing_agent_units':missing_agent,
            'default_actual_status':'UNKNOWN', 'heading_context_retained':True,
            'H43':{'id':'H43', 'source_pieces':anchors, 'original_record_sha256':h43['original_record_sha256'],
                   'citation':'WpHG 50(1)', 'status':'SOURCE_EDITION_AND_APPLICATION_OPEN',
                   'dependency':'historical-WpHG-50-1-publication'},
            'original_reference_count':60, 'statutory_profile_is_exhaustive':False,
            'legal_scope_resolved':False, 'whole_task_complete':False,
            'meaning':'Finite heading spans explain diagnostic uncertainty; original coverage, questions, operative text and substantive uncertainty remain unchanged'}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k:v for k,v in answer.items() if k != 'report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY, 'report_sha256')}
            != {k:v for k,v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Coverage explanation changed the complete prior answer')
    if answer.get(KEY) != evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256):
        raise ValueError('Coverage answer differs from source reconstruction')
    return {'status':'PASS', 'baseline_unchanged':True, 'headings':24, 'substantive_pending':7}
