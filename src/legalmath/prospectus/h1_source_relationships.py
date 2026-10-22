"""Finite reviewed H1 source links; target availability is not reconciliation."""
from copy import deepcopy
import json

from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'bes-h1-current-relationships.v1'
MAP_SHA256 = '57db0c6f6085392989640154963277737a82cf190c9fded91358e54bb86f79e9'
GRAPH_SHA256 = '1ae6e118e00ea304349760480917e37ac0ee22b8b4ead6a532e8e1b5acd3559f'
PRIOR_SHA256 = 'b89acc59b09c7e81974e48b32633fa7eeb1840aebefdda4b2be6a4ef16e5362d'
DOCUMENT = 'bes-interim-h1-2010'
SOURCE = 'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
LIMITS = {'source_specific_supplied_review': True,
    'target_availability_is_financial_reconciliation': False,
    'financial_reconciliation_established': False, 'source_authenticity_established': False,
    'legal_incorporation_selected': False, 'automatic_interpretation_proved': False,
    'original_task_complete': False}


def compact_digest(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode())


def target_at(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/source_statement_cells/'):
        raise ValueError('H1 relationship target must identify a current statement field')
    for token in pointer[1:].split('/'):
        key = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not key.isdigit() or int(key) >= len(value):
                raise ValueError('H1 relationship target is missing')
            value = value[int(key)]
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise ValueError('H1 relationship target is missing')
    return value


def evaluate(graph, prior, profile, *, expected_profile_sha256):
    required = {'version', 'graph_sha256', 'prior_sha256', 'relationships', 'limits'}
    fields(profile, required, required)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != GRAPH_SHA256 or digest(graph) != GRAPH_SHA256
            or profile['prior_sha256'] != PRIOR_SHA256 or digest(prior) != PRIOR_SHA256):
        raise ValueError('Pinned H1 relationship profile, graph or complete prior answer changed')
    if profile['limits'] != LIMITS:
        raise ValueError('H1 relationship availability cannot establish financial or legal correctness')
    relationships = profile['relationships']
    if compact_digest(relationships) != MAP_SHA256:
        raise ValueError('H1 source relationships differ from the reviewed source map')
    required_prior = {'answer', 'cash_flow_review', 'cash_flow_explanation', 'risk_table_review',
        'risk_table_explanation', 'h1_scope_review', 'h1_scope_explanation',
        'h1_individual_unit_review', 'h1_individual_unit_explanation'}
    fields(prior, required_prior, required_prior)
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']):
        raise ValueError('Duplicate H1 relationship source identity')
    checked = []
    for relation in relationships:
        anchor = relation['source']
        unit = units.get(anchor['unit'])
        if (unit is None or unit['document'] != DOCUMENT or unit['source_sha256'] != SOURCE
                or not unit['visible'] or anchor['bbox'] != unit['bbox']
                or anchor['start'] != 0 or anchor['end'] != len(unit['raw'])):
            raise ValueError('H1 relationship original source occurrence changed')
        bind(graph, {key: value for key, value in anchor.items() if key != 'bbox'})
        for target in relation['targets']:
            if compact_digest(target_at(prior['answer'], target['path'])) != target['sha256']:
                raise ValueError('H1 relationship current target field changed')
        # These paths are explicitly contextual; they do not count as an
        # independently derived interpretation of their retained source text.
        for pointer in relation.get('context_paths', []):
            target_at(prior['answer'], pointer)
        checked.append(deepcopy(relation))
    return {'version': VERSION, 'status': 'SUPPLIED_CURRENT_SOURCE_RELATIONSHIPS',
        'graph_sha256': GRAPH_SHA256, 'prior_sha256': PRIOR_SHA256,
        'profile_sha256': digest(profile), 'reviewed_map_sha256': MAP_SHA256,
        'relationships': checked, 'limits': deepcopy(LIMITS)}


def explain(review):
    if (review['version'] != VERSION or review['limits'] != LIMITS
            or review['reviewed_map_sha256'] != MAP_SHA256
            or compact_digest(review['relationships']) != MAP_SHA256):
        raise ValueError('H1 reviewed relationship explanation changed')
    return {'basis': 'Supplied source-specific review of the retained H1 report.',
        'relationships': deepcopy(review['relationships']),
        'meaning': 'The listed source passages and relevant current fields are available together. '
            'Their links identify report context, table headings, footnotes and referenced note clauses.',
        'financial_reconciliation': 'The links do not reconcile net-of-tax equity movements with staff costs, '
            'align different reporting periods, or equate other changes with the full non-controlling-interest movement.',
        'preserved_limits': 'The clipped equity totals and currency, individual-statement unit conflict, '
            'source authority, Portuguese priority and alternative incorporation readings remain unresolved.',
        'limits': deepcopy(LIMITS)}
