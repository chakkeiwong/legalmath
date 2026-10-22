"""Conditional graph analysis of explicitly reviewed source-scope references."""
from copy import deepcopy
from collections import deque
from .anchors import fields
from .contracts import bound_path, digest
from .definition_discovery import require
from .reference_closure import KINDS

VERSION = 'reference-role-review.v1'
KEY = 'reference_role_review'
SOURCE_REVIEW_SHA256 = '51f2ff62b819f2ac57cf369df5ad9452f1d6926f4f047b2dfd24978ff59cb143'
SCOPE_REFERENCES = {'reviewed-reference:holder-option-self-scope',
                    'reviewed-reference:substitution-whole-scope'}


def _components(nodes, edges):
    """Iterative two-pass components; recursion depth is independent of input."""
    outgoing = {n: [] for n in nodes}
    reverse = {n: [] for n in nodes}
    loops = set()
    for edge in edges:
        a, b = edge['from'], edge['to']
        if a in nodes and b in nodes:
            outgoing[a].append(b)
            reverse[b].append(a)
            if a == b:
                loops.add(a)
    seen, order = set(), []
    for root in sorted(nodes):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(outgoing[root]))]
        while stack:
            vertex, children = stack[-1]
            other = next(children, None)
            if other is None:
                order.append(vertex)
                stack.pop()
            elif other not in seen:
                seen.add(other)
                stack.append((other, iter(outgoing[other])))
    seen, groups = set(), []
    for root in reversed(order):
        if root in seen:
            continue
        members, stack = [], [root]
        seen.add(root)
        while stack:
            vertex = stack.pop()
            members.append(vertex)
            for other in reverse[vertex]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        if len(members) > 1 or root in loops:
            groups.append(sorted(members))
    return sorted(groups)


def review(graph, scope_edges, *, expected_graph_sha256):
    fields(graph, {'nodes', 'edges', 'roots'}, {'nodes', 'edges', 'roots'})
    require(digest(graph) == expected_graph_sha256, 'Source graph identity changed')
    nodes, edges, roots = (graph[k] for k in ('nodes', 'edges', 'roots'))
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 100000
            and all(isinstance(n, str) and n for n in nodes)
            and len(set(nodes)) == len(nodes), 'Bounded distinct source vertices required')
    available = set(nodes)
    require(isinstance(roots, list) and len(roots) <= len(nodes)
            and all(isinstance(n, str) and n in available for n in roots)
            and len(set(roots)) == len(roots), 'Known distinct roots required')
    require(isinstance(edges, list) and len(edges) <= 50000, 'Bounded source edges required')
    identities, adjacency = set(), {n: [] for n in nodes}
    for edge in edges:
        keys = {'id', 'from', 'to', 'kind', 'resolved', 'authority'}
        fields(edge, keys, keys)
        identity, a, b = edge['id'], edge['from'], edge['to']
        require(isinstance(identity, str) and identity and identity not in identities,
                'Distinct edge identities required')
        identities.add(identity)
        require(isinstance(a, str) and a in available
                and (b is None or isinstance(b, str) and b)
                and isinstance(edge['kind'], str) and edge['kind'] in KINDS and type(edge['resolved']) is bool
                and type(edge['authority']) is bool, 'Invalid typed reference edge')
        require(b is not None or edge['resolved'] is False, 'A null reference cannot be resolved')
        if b in available:
            adjacency[a].append(b)
    require(isinstance(scope_edges, list) and all(isinstance(s, str) and s in identities for s in scope_edges)
            and len(scope_edges) == len(set(scope_edges)), 'Explicit distinct existing scope edges required')
    reached, pending = set(roots), deque(roots)
    while pending:
        for other in adjacency[pending.popleft()]:
            if other not in reached:
                reached.add(other)
                pending.append(other)
    selected = [e for e in edges if e['from'] in reached]
    scoped = set(scope_edges)
    # Scope links still reach their targets. A real cycle accessible only by
    # such a link must remain a dependency-cycle diagnostic.
    return {'version': VERSION, 'graph_sha256': digest(graph), 'reachable': sorted(reached),
        'source_cycles': _components(reached, selected),
        'dependency_cycles': _components(reached, [e for e in selected if e['id'] not in scoped]),
        'scope_edges': sorted(scope_edges),
        'unresolved_edges': sorted(e['id'] for e in selected if not e['resolved']),
        'missing_targets': sorted({e['to'] for e in selected if e['to'] is not None and e['to'] not in available}),
        'unsupported_priority': sorted(e['id'] for e in selected if e['kind'] == 'priority' and not e['authority']),
        'classification_basis': 'SUPPLIED_REVIEWED_SCOPE; other edges remain conservative',
        'legal_truth_established': False}


def source_graphs(products):
    p1, p2, p3 = (products[k]['payload'] for k in ('P1', 'P2', 'P3'))
    units = [u for u in p2['assembly']['units'] if u['role'] in ('OPERATIVE', 'UNKNOWN')]
    dispositions = p1['request'].get('reference_dispositions', {})
    result = {}
    for question in ('Q1', 'Q2'):
        edges = []
        for row in p3['dependencies']:
            if 'source_use' not in row or 'targets' not in row or question not in row['questions']:
                continue
            reviewed = row['id'].startswith('reviewed-reference:')
            require(reviewed or '@' in row['id'], 'Unrecognized source-reference record')
            disposition = {} if reviewed else dispositions.get(row['id'].split('@')[0], {})
            for index, target in enumerate(row['targets'] or [None]):
                edges.append({'id': row['id'] + '#' + str(index), 'from': row['source_use']['unit'],
                    'to': None if target is None else target['unit'],
                    'kind': disposition.get('kind', 'reference'), 'resolved': row['status'] == 'RESOLVED',
                    'authority': bool(row.get('authority') if reviewed else disposition.get('authority'))})
        result[question] = {'nodes': [u['unit'] for u in units], 'edges': edges,
                           'roots': [u['unit'] for u in units if question in u['questions']]}
    return result


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'source_review',
            'scope_references', 'legal_truth_established'}
    fields(profile, keys, keys)
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
            and profile['products_sha256'] == digest(products)
            and profile['ordinary_answer_sha256'] == digest(ordinary)
            and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            and KEY not in ordinary, 'Pinned source-role profile or prior answer changed')
    require(profile['scope_references'] == sorted(SCOPE_REFERENCES)
            and profile['legal_truth_established'] is False,
            'Only the explicitly reviewed source roles are admitted')
    sources = profile['source_review']
    require(digest(sources) == SOURCE_REVIEW_SHA256, 'Reviewed source classifications changed')
    for relative, checksum in sources['source_files'].items():
        path = bound_path(root, relative)
        require(path.stat().st_size <= 64 * 1024**2 and digest(path.read_bytes()) == checksum,
                'Original source or image changed')
    require(sources['products_sha256'] == digest(products)
            and sources['ordinary_answer_sha256'] == digest(ordinary), 'Source review uses a different baseline')
    actual_references = {r['id']: r for r in ordinary['internal_references']['references']}
    for row in sources['readings']:
        require(actual_references.get(row['reference']['id']) == row['reference'], 'Complete reviewed target changed')
    graphs = source_graphs(products)
    reports = {}
    for question, graph in graphs.items():
        ids = [e['id'] for e in graph['edges'] if e['id'].rsplit('#', 1)[0] in SCOPE_REFERENCES]
        require({e.rsplit('#', 1)[0] for e in ids} == SCOPE_REFERENCES, 'Reviewed scope edges missing')
        reports[question] = review(graph, ids, expected_graph_sha256=digest(graph))
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
        'source_review': deepcopy(sources), 'questions': reports,
        'original_answer_preserved': True, 'legal_truth_established': False,
        'historical_application_established': False, 'automatic_role_discovery': False,
        'meaning': 'Conditional source-role analysis; genuine remaining reference and rule uncertainty is retained'}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    require(answer.get('report_sha256') == digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            and {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
                == {k: v for k, v in ordinary.items() if k != 'report_sha256'},
            'Reference-role review changed the prior answer')
    require(answer.get(KEY) == evaluate(products, ordinary, profile, root,
                                       expected_profile_sha256=expected_profile_sha256),
            'Reference-role answer differs from full reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'questions': 2}
