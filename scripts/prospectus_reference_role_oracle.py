"""Independent repeated-reachability oracle; no production graph imports."""
from collections import deque


def expected(graph, scope_edges):
    nodes = set(graph['nodes'])
    edges = graph['edges']
    adjacency = {n: [] for n in nodes}
    for e in edges:
        if e['to'] in nodes:
            adjacency[e['from']].append(e['to'])

    def reachable(starts, adj):
        found = set(starts)
        pending = deque(starts)
        while pending:
            for other in adj.get(pending.popleft(), []):
                if other not in found:
                    found.add(other)
                    pending.append(other)
        return found

    reached = reachable(graph['roots'], adjacency)

    def cycles(removed):
        active = {e['from'] for e in edges if e['from'] in reached and e['id'] not in removed}
        active |= {e['to'] for e in edges if e['from'] in reached and e['to'] in reached and e['id'] not in removed}
        adj = {n: [] for n in active}
        for e in edges:
            if e['id'] not in removed and e['from'] in active and e['to'] in active:
                adj[e['from']].append(e['to'])
        closure = {n: reachable([n], adj) for n in active}
        groups, used = [], set()
        for n in sorted(active):
            if n in used:
                continue
            group = sorted(m for m in closure[n] if n in closure[m])
            used.update(group)
            if len(group) > 1 or n in adj[n]:
                groups.append(group)
        return sorted(groups)

    selected = [e for e in edges if e['from'] in reached]
    return {'reachable': sorted(reached),
            'source_cycles': cycles(set()), 'dependency_cycles': cycles(set(scope_edges)),
            'scope_edges': sorted(scope_edges),
            'unresolved_edges': sorted(e['id'] for e in selected if not e['resolved']),
            'missing_targets': sorted({e['to'] for e in selected if e['to'] is not None and e['to'] not in nodes}),
            'unsupported_priority': sorted(e['id'] for e in selected if e['kind'] == 'priority' and not e['authority'])}


def verify(graph, scope_edges, actual):
    wanted = expected(graph, scope_edges)
    assert {k: actual[k] for k in wanted} == wanted, 'Graph differs from independent reachability oracle'
    assert actual['legal_truth_established'] is False
    assert actual['classification_basis'] == 'SUPPLIED_REVIEWED_SCOPE; other edges remain conservative'
    return {'status': 'PASS', 'independent_graph_oracle': True,
            'source_components': len(wanted['source_cycles']),
            'remaining_components': len(wanted['dependency_cycles'])}


def source_graphs(products):
    """Independently expand retained reference records, retaining parallel edges."""
    construction = products['P2']['payload']['assembly']['units']
    selected = {u['unit']: u['questions'] for u in construction if u['role'] in {'UNKNOWN', 'OPERATIVE'}}
    decisions = products['P1']['payload']['request'].get('reference_dispositions', {})
    records = [r for r in products['P3']['payload']['dependencies'] if {'source_use', 'targets'} <= r.keys()]
    result = {q: {'nodes': list(selected), 'roots': [n for n, qs in selected.items() if q in qs], 'edges': []}
              for q in ('Q1', 'Q2')}
    for row in records:
        if row['id'].startswith('reviewed-reference:'):
            kind, authority = 'reference', bool(row['authority'])
        else:
            policy = decisions.get(row['id'][:row['id'].index('@')], {})
            kind, authority = policy.get('kind', 'reference'), bool(policy.get('authority'))
        destinations = [x['unit'] for x in row['targets']] if row['targets'] else [None]
        for number, destination in enumerate(destinations):
            edge = {'id': '%s#%d' % (row['id'], number), 'from': row['source_use']['unit'],
                    'to': destination, 'kind': kind, 'authority': authority,
                    'resolved': row['status'] == 'RESOLVED'}
            for question in result:
                if question in row['questions']:
                    result[question]['edges'].append(dict(edge))
    return result
