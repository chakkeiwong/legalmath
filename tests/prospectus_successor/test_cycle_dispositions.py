"""Role distinctions must preserve source reachability and genuine dependencies."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor.cycle_dispositions import partition_graph
from scripts.prospectus_reference_role_oracle import expected


def edge(name, a, b, resolved=True):
    return {'id': name + '#0', 'from': a, 'to': b, 'kind': 'reference', 'resolved': resolved, 'authority': True}


def test_scope_reaches_real_cycle_and_preserves_unknown_target():
    graph = {'nodes': ['a', 'b', 'c'], 'roots': ['a'], 'edges': [
        edge('scope', 'a', 'b'), edge('body', 'b', 'c'), edge('back', 'c', 'b'), edge('missing', 'c', 'absent', False)]}
    before = deepcopy(graph)
    actual = partition_graph(graph, [], {'scope': 'APPLICATION_SCOPE', 'body': 'SUBSTANTIVE_IMPORT'})
    wanted = expected(graph, ['scope#0'])
    assert {k: actual[k] for k in wanted} == wanted
    assert actual['dependency_cycles'] == [['b', 'c']]
    assert actual['missing_targets'] == ['absent'] and actual['unresolved_edges'] == ['missing#0']
    assert graph == before


def test_reverse_amount_scope_keeps_forward_dependency_and_substantive_self_loop():
    graph = {'nodes': ['tax', 'amount', 'exchange'], 'roots': ['tax', 'exchange'], 'edges': [
        edge('forward', 'tax', 'amount'), edge('reverse', 'amount', 'tax'), edge('procedure', 'exchange', 'exchange')]}
    actual = partition_graph(graph, [], {'reverse': 'APPLICATION_SCOPE', 'forward': 'SUBSTANTIVE_IMPORT', 'procedure': 'SUBSTANTIVE_IMPORT'})
    assert actual['source_cycles'] == [['amount', 'tax'], ['exchange']]
    assert actual['dependency_cycles'] == [['exchange']]
    assert actual['reachable'] == ['amount', 'exchange', 'tax']
    assert actual['scope_edges'] == ['reverse#0']


def test_unresolved_scope_does_not_resolve_source():
    graph = {'nodes': ['a'], 'roots': ['a'], 'edges': [edge('scope', 'a', None, False)]}
    actual = partition_graph(graph, [], {'scope': 'APPLICATION_SCOPE'})
    assert actual['unresolved_edges'] == ['scope#0']
    assert actual['dependency_cycles'] == []


@pytest.mark.parametrize('roles', [{}, {'absent': 'APPLICATION_SCOPE'}, {'a': 'RESOLVED'}, {'a': True}, {3: 'APPLICATION_SCOPE'}])
def test_unsupported_role_refused(roles):
    graph = {'nodes': ['x'], 'roots': ['x'], 'edges': [edge('a', 'x', 'x')]}
    with pytest.raises(ValueError):
        partition_graph(graph, [], roles)


@pytest.mark.parametrize('role', ['APPLICATION_SCOPE', 'SUBSTANTIVE_IMPORT'])
def test_existing_scope_cannot_be_reclassified(role):
    graph = {'nodes': ['x'], 'roots': ['x'], 'edges': [edge('a', 'x', 'x')]}
    with pytest.raises(ValueError):
        partition_graph(graph, ['a#0'], {'a': role})


def test_permutations_keep_all_graph_consequences():
    graph = {'nodes': ['a', 'b'], 'roots': ['a', 'b'], 'edges': [edge('scope', 'a', 'b'), edge('body', 'b', 'a')]}
    roles = {'scope': 'APPLICATION_SCOPE', 'body': 'SUBSTANTIVE_IMPORT'}
    first = partition_graph(graph, [], roles)
    for value in graph.values():
        value.reverse()
    second = partition_graph(graph, [], roles)
    assert {k: v for k, v in first.items() if k != 'graph_sha256'} == {k: v for k, v in second.items() if k != 'graph_sha256'}
