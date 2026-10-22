"""Source reachability survives supplied scope roles without hiding real cycles."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reference_roles import review
from scripts.prospectus_reference_role_oracle import verify

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / 'docs/implementation/prospectus-execution-authority/reviews/reference-role-325/cases.json').read_text())['cases']


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_authored_case_and_permutation(case):
    graph, scopes = deepcopy(case['graph']), case['scope_edges']
    result = review(graph, scopes, expected_graph_sha256=digest(graph))
    assert {k: result[k] for k in case['expected']} == case['expected']
    verify(graph, scopes, result)
    for key in ('nodes', 'edges', 'roots'):
        graph[key].reverse()
    changed = review(graph, list(reversed(scopes)), expected_graph_sha256=digest(graph))
    assert {k: changed[k] for k in case['expected']} == case['expected']


@pytest.mark.parametrize('kind', ['graph-pin', 'duplicate-node', 'duplicate-edge', 'duplicate-root',
                                  'missing-root', 'missing-source', 'unknown-kind', 'false-null-resolution',
                                  'nonboolean', 'unknown-scope', 'duplicate-scope', 'extra-field'])
def test_invalid_graph_refused(kind):
    graph = deepcopy(CASES[0]['graph'])
    scopes = ['e']
    if kind == 'duplicate-node': graph['nodes'].append('a')
    elif kind == 'duplicate-edge': graph['edges'].append(deepcopy(graph['edges'][0]))
    elif kind == 'duplicate-root': graph['roots'].append('a')
    elif kind == 'missing-root': graph['roots'] = ['absent']
    elif kind == 'missing-source': graph['edges'][0]['from'] = 'absent'
    elif kind == 'unknown-kind': graph['edges'][0]['kind'] = ['scope']
    elif kind == 'false-null-resolution': graph['edges'][0]['to'] = None
    elif kind == 'nonboolean': graph['edges'][0]['resolved'] = 1
    elif kind == 'unknown-scope': scopes = ['absent']
    elif kind == 'duplicate-scope': scopes.append('e')
    elif kind == 'extra-field': graph['edges'][0]['automatically_true'] = True
    checksum = '0' * 64 if kind == 'graph-pin' else digest(graph)
    with pytest.raises(ValueError):
        review(graph, scopes, expected_graph_sha256=checksum)


def test_long_chain_has_no_recursive_stack_dependency():
    nodes = [str(n) for n in range(2500)]
    edges = [{'id': str(n), 'from': str(n), 'to': str(n + 1), 'kind': 'reference',
              'resolved': True, 'authority': True} for n in range(2499)]
    graph = {'nodes': nodes, 'edges': edges, 'roots': ['0']}
    actual = review(graph, [], expected_graph_sha256=digest(graph))
    assert actual['reachable'] == sorted(nodes)
    assert not actual['source_cycles'] and not actual['dependency_cycles']
