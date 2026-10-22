"""Source-enumerated reference roles and independent full-graph expectations."""
from copy import deepcopy
from scripts import prospectus_reference_role_oracle as graph_oracle
from legalmath.prospectus.successor.contracts import digest

VERSION = 'basf-cycle-dispositions.v1'
KEY = 'reference_cycle_disposition_review'
ROLES = {
    'temporary-global-self-scope': 'SUBSTANTIVE_IMPORT',
    'tax-call-forward-amount': 'SUBSTANTIVE_IMPORT',
    'tax-call-reverse-conditions': 'APPLICATION_SCOPE',
    'additional-amounts-backward-scope': 'SUBSTANTIVE_IMPORT',
    'depository-proof-scope': 'APPLICATION_SCOPE',
}
READINGS = {
    'temporary-global-self-scope': 'The certificate is treated as an exchange request under the specified procedure; the reference imports its requirements and does not establish completed exchange.',
    'tax-call-forward-amount': 'The tax-call repayment imports the early amount definition; the complete tax-call conditions and accrued interest remain.',
    'tax-call-reverse-conditions': 'For the purposes of section 5(2), the early amount equals the repayment amount; this reverse link sets the application of that definition.',
    'additional-amounts-backward-scope': 'The specified flat tax and solidarity surcharge are excluded from the imported category for additional amounts; the category and its other exceptions remain substantive.',
    'depository-proof-scope': 'The Depotbank definition applies to the preceding proof route; the certificate, certified copy, institution qualifications and alternative lawful procedures remain.',
}
NODES = (
    'basf-global:exchange-certification', 'basf-redemption:tax',
    'basf-redemption:early-amount-definition', 'basf-payment:german_flat_tax',
    'basf-notices:holding-proof',
)
NEW_SCOPES = {
    'reviewed-reference:tax-call-reverse-conditions',
    'reviewed-reference:depository-proof-scope',
}


def content(products, ordinary, decisions):
    assert {r['id']: r['role'] for r in decisions['readings']} == ROLES
    assert {r['id']: r['reading'] for r in decisions['readings']} == READINGS
    references = {r['id']: r for r in products['P3']['payload']['interpretation_input']['reference_admission']['references']}
    nodes = {r['id']: r for r in products['P3']['payload']['clauses']['nodes']}
    assert decisions['references'] == [references[k] for k in ROLES]
    assert decisions['nodes'] == [nodes[k] for k in NODES]
    graphs = graph_oracle.source_graphs(products)
    questions = {}
    for question, graph in graphs.items():
        baseline = ordinary['reference_role_review']['questions'][question]
        old = baseline['scope_edges']
        assert {k: baseline[k] for k in graph_oracle.expected(graph, old)} == graph_oracle.expected(graph, old)
        extra = [e['id'] for e in graph['edges'] if e['id'].rsplit('#', 1)[0] in NEW_SCOPES]
        assert {e.rsplit('#', 1)[0] for e in extra} == NEW_SCOPES
        expected = graph_oracle.expected(graph, [*old, *extra])
        assert all(expected[k] == baseline[k] for k in ('reachable', 'source_cycles', 'missing_targets', 'unresolved_edges', 'unsupported_priority'))
        questions[question] = {'graph_sha256': digest(graph), 'prior_scope_edges': old,
            'additional_scope_edges': sorted(extra), 'prior_dependency_cycles': baseline['dependency_cycles'],
            **expected}
    return {'readings': deepcopy(decisions['readings']),
        'references': deepcopy(decisions['references']), 'operative_nodes': deepcopy(decisions['nodes']),
        'source_pages': deepcopy(decisions['source_pages']), 'questions': questions,
        'prior_answer_preserved': True, 'source_graph_preserved': True,
        'substantive_imports_preserved': True, 'general_role_discovery': False,
        'cycles_are_legal_circularity_proof': False, 'actual_event_established': False,
        'historical_law_established': False, 'whole_task_complete': False}


def verify(actual, ordinary, products, profile, expected):
    report = {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary), **expected}
    wanted = {**ordinary, KEY: report}
    wanted['report_sha256'] = digest({k: v for k, v in wanted.items() if k != 'report_sha256'})
    assert actual == wanted, 'Complete answer differs from frozen source/graph expectation'
    return {'status': 'PASS', 'whole_answer_equal_to_independent_expectation': True,
        'source_readings': 5, 'components_reviewed': 4, 'dependency_components_retained': 2}
