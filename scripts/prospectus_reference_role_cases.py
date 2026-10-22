"""Freeze manually specified graph cases and original source evidence first."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import signal
import time
from scripts import prospectus_layout_labels as prior
from legalmath.prospectus.execution_authority import Authority
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reference_closure import close

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/reference-role-325'
PLAN = 'docs/plans/prospectus-reference-role-2026-10-19.md'
METHOD = 'scripts/prospectus_reference_role_cases.py'
READINGS = {
    'holder-option-self-scope': {'quote': 'diesem § 5 Absatz (3)',
        'unit': 'basf-base-september-2022-exchange:p119:l60',
        'start': 44, 'end': 65, 'role': 'PROCEDURE_DESCRIPTION_SCOPE',
        'reason': 'The notice must describe the procedure in this paragraph; the reference does not prove the event or exercise.'},
    'substitution-whole-scope': {'quote': 'dieses § 10',
        'unit': 'basf-base-september-2022-exchange:p129:l37',
        'start': 15, 'end': 26, 'role': 'DEFINITION_APPLICATION_SCOPE',
        'reason': 'The phrase restricts the affiliate definition to section10; imported AktG meaning and all substitution conditions remain separate.'}}


def edge(identity, a, b, resolved=True, kind='reference', authority=True):
    return {'id': identity, 'from': a, 'to': b, 'resolved': resolved, 'kind': kind, 'authority': authority}


def cases():
    values = []
    def add(identity, nodes, edges, roots, scope, reached, source, dependency,
            unresolved=None, missing=None, priority=None):
        values.append({'id': identity, 'graph': {'nodes': nodes, 'edges': edges, 'roots': roots},
            'scope_edges': scope, 'expected': {'reachable': reached, 'source_cycles': source,
                'dependency_cycles': dependency, 'scope_edges': sorted(scope),
                'unresolved_edges': unresolved or [], 'missing_targets': missing or [],
                'unsupported_priority': priority or []}})
    add('scope-self', ['a'], [edge('e', 'a', 'a')], ['a'], ['e'], ['a'], [['a']], [])
    add('substantive-self', ['a'], [edge('e', 'a', 'a')], ['a'], [], ['a'], [['a']], [['a']])
    add('mixed-two', ['a', 'b'], [edge('e', 'a', 'b'), edge('f', 'b', 'a')],
        ['a'], ['f'], ['a', 'b'], [['a', 'b']], [])
    add('true-two', ['a', 'b'], [edge('e', 'a', 'b'), edge('f', 'b', 'a')],
        ['a'], [], ['a', 'b'], [['a', 'b']], [['a', 'b']])
    add('scope-to-real-cycle', ['a', 'b', 'c'],
        [edge('e', 'a', 'b'), edge('f', 'b', 'c'), edge('g', 'c', 'b')],
        ['a'], ['e'], ['a', 'b', 'c'], [['b', 'c']], [['b', 'c']])
    add('disconnected-cycle', ['a', 'b'], [edge('e', 'b', 'b')], ['a'], [], ['a'], [], [])
    add('unresolved-scope', ['a'], [edge('e', 'a', 'a', False)], ['a'], ['e'], ['a'], [['a']], [], ['e'])
    add('missing-scope-target', ['a'], [edge('e', 'a', 'absent')], ['a'], ['e'], ['a'], [], [], missing=['absent'])
    add('null-target', ['a'], [edge('e', 'a', None, False)], ['a'], [], ['a'], [], [], ['e'])
    add('unsupported-priority', ['a', 'b'], [edge('e', 'a', 'b', kind='priority', authority=False)],
        ['a'], ['e'], ['a', 'b'], [], [], priority=['e'])
    add('parallel-distinct-roles', ['a'], [edge('e', 'a', 'a'), edge('f', 'a', 'a')],
        ['a'], ['e'], ['a'], [['a']], [['a']])
    add('empty-edge-set', ['a', 'b'], [], ['a'], [], ['a'], [], [])
    return values


def main():
    PREP.mkdir(parents=True, exist_ok=True)
    marker = PREP / 'case-preparation-start.json'
    assert not marker.exists(), 'Unchanged preparation retry refused'
    prior.save(marker, {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reference_role_cases'],
                        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 30})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Case preparation bound')))
    signal.alarm(30)
    try:
        assert any(e['kind'] == 'RECORD' and e.get('attempt') == prior.rel(prior.HERE) for e in Authority(ROOT).events())
        manifest = prior.read(prior.PRODUCTS)
        paths = {k: ROOT / v['path'] for k, v in manifest['products'].items()}
        for k, path in paths.items():
            assert prior.sha(path) == manifest['products'][k]['sha256']
        products = {k: prior.read(p) for k, p in paths.items()}
        original = prior.read(prior.HERE / 'ordinary-answer.json.gz')
        assert digest(original) == '3b9a3556cbbf0b87b33401ecffa25eae68140f50dd217fd5346beb40bf5e7fd1'
        p1, p2, p3 = (products[k]['payload'] for k in ('P1', 'P2', 'P3'))
        nodes = {u['unit']: u for u in p2['assembly']['units'] if u['role'] in ('OPERATIVE', 'UNKNOWN')}
        request = p1['request']
        edges = []
        for dep in p3['dependencies']:
            if 'source_use' not in dep or 'targets' not in dep:
                continue
            identity = dep['id']
            reviewed = identity.startswith('reviewed-reference:')
            assert reviewed or '@' in identity
            disposition = {} if reviewed else request.get('reference_dispositions', {}).get(identity.split('@')[0], {})
            for target in dep['targets'] or [None]:
                edges.append({'id': identity, 'from': dep['source_use']['unit'],
                    'to': None if target is None else target['unit'], 'kind': disposition.get('kind', 'reference'),
                    'resolved': dep['status'] == 'RESOLVED',
                    'authority': dep.get('authority') if reviewed else disposition.get('authority'),
                    'questions': dep['questions']})
        receipts = []
        for question in ('Q1', 'Q2'):
            roots = {k for k, v in nodes.items() if question in v['questions']}
            computed = close(nodes, [e for e in edges if question in e['questions']], roots)
            old = next(d for d in p3['dependencies'] if d['id'] == 'reference-closure:' + question)
            assert computed == {k: old[k] for k in ('roots', 'reachable', 'unresolved')}
            receipts.append({'question': question, 'graph_edges': sum(question in e['questions'] for e in edges),
                'closure_sha256': digest(computed), 'unresolved_count': len(computed['unresolved']),
                'cycle_witnesses': [x for x in computed['unresolved'] if x.startswith('Unsupported reference cycle:')]})
        source_rows = []
        for row in original['internal_references']['references']:
            if row['id'] in READINGS:
                reading = READINGS[row['id']]
                assert all(row['source'][k] == reading[k] for k in ('unit', 'quote', 'start', 'end'))
                source_rows.append({'reference': row, 'reading': reading})
        assert len(source_rows) == 2
        originals = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/base-' + str(n) + '.png'
                     for n in (119, 120, 128, 129)]
        originals += [row['path'] for row in original['internal_references']['source_documents']]
        evidence = {path: prior.sha(ROOT / path) for path in originals}
        prior.save(PREP / 'source-review.json', {'readings': source_rows, 'source_files': evidence,
            'graph_reproduction': receipts, 'products_sha256': digest(products),
            'ordinary_answer_sha256': digest(original), 'classification_is_supplied': True})
        prior.save(PREP / 'cases.json', {'cases': cases()})
        prior.save(PREP / 'cases-freeze.json', {'cases_sha256': prior.sha(PREP / 'cases.json'),
            'source_review_sha256': prior.sha(PREP / 'source-review.json'), 'source_files': evidence,
            'method': METHOD, 'method_sha256': prior.sha(ROOT / METHOD), 'plan': PLAN,
            'plan_sha256': prior.sha(ROOT / PLAN), 'frozen_at': datetime.now(timezone.utc).isoformat()})
        result = {'status': 'PASS', 'cases': len(cases()), 'complete_original_closures': 2,
                  'wall_seconds': time.monotonic() - start}
        prior.save(PREP / 'case-preparation.json', result)
        print(json.dumps(result))
    except BaseException as error:
        prior.save(PREP / 'case-preparation-failure.json', {'type': type(error).__name__,
                   'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
