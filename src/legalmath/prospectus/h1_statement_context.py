"""Exact reviewed statement context; supplied associations, not inferred authority."""
from copy import deepcopy
import json

from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'bes-h1-statement-context.v1'
MAP_SHA256 = '3a21bef6c704e4330122e1d2a35b6081a32c4fa7ba6d23a572da41e809dd3560'
GRAPH_SHA256 = '1ae6e118e00ea304349760480917e37ac0ee22b8b4ead6a532e8e1b5acd3559f'
PRIOR_SHA256 = 'ead9f7ed057c9d76b09d8b47059da0e5ba8fe2ee8fd2a29ff2cc6d14c6663f6c'
DOCUMENT = 'bes-interim-h1-2010'
SOURCE = 'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
LIMITS = {'supplied_source_specific_interpretation': True,
    'automatic_interpretation_established': False, 'source_authenticity_established': False,
    'intended_individual_unit_resolved': False, 'clipped_equity_restored': False,
    'incorporation_selected': False, 'financial_accuracy_established': False,
    'original_task_complete': False}


def compact(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode())


def target_at(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('Statement context requires an absolute field pointer')
    for token in pointer[1:].split('/'):
        key = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise ValueError('Statement context target is missing')
    return value


def check_associations(graph, prior, associations):
    """Check exact sources/targets independently of the complete answer digest."""
    if compact(associations) != MAP_SHA256:
        raise ValueError('Statement context differs from the reviewed associations')
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']):
        raise ValueError('Duplicate statement context source identity')
    for row in associations:
        source = row['source']
        u = units.get(source['unit'])
        if (u is None or u['document'] != DOCUMENT or u['source_sha256'] != SOURCE
                or not u['visible'] or source['bbox'] != u['bbox']
                or source['start'] != 0 or source['end'] != len(u['raw'])):
            raise ValueError('Statement context source identity or geometry changed')
        bind({'units':[u]}, {k:v for k,v in source.items() if k != 'bbox'})
        for target in row['targets']:
            if compact(target_at(prior, target['path'])) != target['sha256']:
                raise ValueError('Statement context target value changed')
        if row.get('group'):
            for pointer in row['group']['members'] + row['group']['subtotals']:
                target_at(prior, pointer)
    return True


def evaluate(graph, prior, profile, *, expected_profile_sha256):
    required = {'version','graph_sha256','prior_sha256','associations','limits'}
    fields(profile, required, required)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != GRAPH_SHA256 or digest(graph) != GRAPH_SHA256
            or profile['prior_sha256'] != PRIOR_SHA256 or digest(prior) != PRIOR_SHA256):
        raise ValueError('Pinned statement context profile, graph or complete answer changed')
    if profile['limits'] != LIMITS:
        raise ValueError('Statement context cannot establish source truth or incorporation')
    check_associations(graph, prior, profile['associations'])
    return {'version': VERSION, 'status':'SUPPLIED_STATEMENT_CONTEXT',
        'graph_sha256':GRAPH_SHA256, 'prior_sha256':PRIOR_SHA256,
        'profile_sha256':digest(profile), 'associations':deepcopy(profile['associations']),
        'reviewed_map_sha256':MAP_SHA256, 'limits':deepcopy(LIMITS)}


def explain(review):
    if (review['version'] != VERSION or review['limits'] != LIMITS
            or review['reviewed_map_sha256'] != MAP_SHA256
            or compact(review['associations']) != MAP_SHA256):
        raise ValueError('Statement context explanation differs from the reviewed result')
    return {'basis':'Supplied reading of the retained H1 statement headings and groups.',
        'associations':deepcopy(review['associations']),
        'meaning':'Dates identify both period length and year; units preserve the EPS exception. '
            'Tax and OCI headings identify groups, and EPS identifies profit attributable to Bank equity holders.',
        'limits':deepcopy(LIMITS)}
