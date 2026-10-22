"""Source-reviewed distinctions between scope and substantive reference imports."""
from copy import deepcopy
import json
from pathlib import Path
from .anchors import fields
from .contracts import bound_path, digest
from .definition_applications import require
from . import reference_roles

VERSION = 'basf-cycle-dispositions.v1'
KEY = 'reference_cycle_disposition_review'
SPEC_SHA256 = '30cfcb540ded9b25045d101642025907dd56be82be95a06a6beae732f3e68959'
GRAPH_KEYS = ('reachable', 'source_cycles', 'dependency_cycles', 'scope_edges',
              'unresolved_edges', 'missing_targets', 'unsupported_priority')
PRESERVED_KEYS = tuple(k for k in GRAPH_KEYS if k not in ('dependency_cycles', 'scope_edges'))


def specification():
    value = json.loads(Path(__file__).with_name('cycle_dispositions_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(value) == SPEC_SHA256,
            'Registered cycle-disposition specification changed')
    return value


def partition_graph(graph, prior_scope_edges, roles):
    require(isinstance(roles, dict) and bool(roles)
            and all(isinstance(k, str) and k and v in ('APPLICATION_SCOPE', 'SUBSTANTIVE_IMPORT')
                    for k, v in roles.items()), 'Explicit typed relation roles required')
    before = reference_roles.review(graph, prior_scope_edges, expected_graph_sha256=digest(graph))
    relations = {e['id'].rsplit('#', 1)[0] for e in graph['edges']}
    require(set(roles) <= relations, 'Reviewed relation missing from source graph')
    substantive = {e['id'] for e in graph['edges']
                   if roles.get(e['id'].rsplit('#', 1)[0]) == 'SUBSTANTIVE_IMPORT'}
    require(not substantive.intersection(prior_scope_edges), 'Substantive import cannot be a scope edge')
    additional = [e['id'] for e in graph['edges']
                  if roles.get(e['id'].rsplit('#', 1)[0]) == 'APPLICATION_SCOPE']
    require(not set(additional).intersection(prior_scope_edges), 'New scope relation was already reviewed')
    after = reference_roles.review(graph, [*prior_scope_edges, *additional], expected_graph_sha256=digest(graph))
    require(all(before[k] == after[k] for k in PRESERVED_KEYS), 'Full source graph consequences changed')
    return {'graph_sha256': digest(graph), 'prior_scope_edges': deepcopy(prior_scope_edges),
        'additional_scope_edges': sorted(additional), 'prior_dependency_cycles': before['dependency_cycles'],
        **{k: after[k] for k in GRAPH_KEYS}}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'specification_sha256',
            'whole_task_complete', 'legal_truth_established'}
    fields(profile, keys, keys)
    spec = specification()
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
        and profile['specification_sha256'] == SPEC_SHA256
        and profile['products_sha256'] == digest(products) == spec['products_sha256']
        and profile['ordinary_answer_sha256'] == digest(ordinary) == spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False, 'Pinned cycle-disposition baseline differs')
    decisions = spec['decisions']
    references = {r['id']: r for r in products['P3']['payload']['interpretation_input']['reference_admission']['references']}
    nodes = {r['id']: r for r in products['P3']['payload']['clauses']['nodes']}
    for reference in decisions['references']:
        require(references.get(reference['id']) == reference, 'Complete reviewed reference differs')
    for node in decisions['nodes']:
        require(nodes.get(node['id']) == node, 'Complete operative meaning or prerequisites changed')
    for relative, checksum in decisions['source_pages'].items():
        path = bound_path(root, relative)
        require(path.stat().st_size < 16 * 1024**2 and digest(path.read_bytes()) == checksum,
                'Inspected original page changed')
    roles = {'reviewed-reference:' + r['id']: r['role'] for r in decisions['readings']}
    require(len(roles) == len(decisions['readings']) == len(decisions['references']) == 5,
            'Complete distinct source decisions required')
    questions = {}
    for question, graph in reference_roles.source_graphs(products).items():
        baseline = ordinary['reference_role_review']['questions'][question]
        before = reference_roles.review(graph, baseline['scope_edges'], expected_graph_sha256=digest(graph))
        require(before == baseline, 'Prior reference-role evidence changed')
        questions[question] = partition_graph(graph, baseline['scope_edges'], roles)
    content = {'readings': deepcopy(decisions['readings']), 'references': deepcopy(decisions['references']),
        'operative_nodes': deepcopy(decisions['nodes']), 'source_pages': deepcopy(decisions['source_pages']),
        'questions': questions, 'prior_answer_preserved': True, 'source_graph_preserved': True,
        'substantive_imports_preserved': True, 'general_role_discovery': False,
        'cycles_are_legal_circularity_proof': False, 'actual_event_established': False,
        'historical_law_established': False, 'whole_task_complete': False}
    require(digest(content) == spec['expected_content_sha256'], 'Source-reviewed graph consequences differ')
    return {KEY: {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), **content}}


def verify_answer(actual, ordinary, profile, products, root, *, expected_profile_sha256):
    expected = {**ordinary, **evaluate(products, ordinary, profile, root,
                                      expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256'] = digest({k: v for k, v in expected.items() if k != 'report_sha256'})
    require(actual == expected, 'Complete cycle-disposition answer differs from reconstruction')
    return {'status': 'PASS', 'whole_answer_equal': True, 'legal_truth_established': False}
