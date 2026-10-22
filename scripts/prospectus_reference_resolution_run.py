"""Bounded, retained stages for source-only resolution and graph reconciliation."""
import ast
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts import prospectus_reference_resolution_trial as prep
from scripts import prospectus_reference_mentions_run as prior

ROOT, AUTH, PREP, HERE = prep.ROOT, prep.AUTH, prep.PREP, prep.HERE
read, save, rel, sha = prep.read, prep.save, prep.rel, prep.sha
FILES = (prep.METHOD, prep.PLAN, 'scripts/prospectus_reference_resolution_run.py',
         'scripts/prospectus_reference_resolution_installed.py',
         'tests/prospectus_successor/test_reference_resolution.py', *prep.TARGETS)
STAGES = ('freeze', 'tests', 'ordinary', 'audit', 'package', 'installed', 'seal')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    measured = base['combined_measured_seconds'] + extra
    for directory in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json', 'development/*.json'):
            measured += sum(read(p).get('wall_seconds', 0) for p in directory.glob(pattern))
    paths = {p for directory in (PREP, HERE) for p in directory.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0356.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / name).stat().st_size - start['production_bytes'][name]) for name in prep.TARGETS)
    charge = base['conservative_extra_seconds'] + 120
    assert measured + charge < prep.SECONDS_BOUND, 'Cumulative time exhausted'
    assert size < prep.BYTES_BOUND - 4 * 1024**2, 'Cumulative storage reserve reached'
    assert measured - base['combined_measured_seconds'] < 300, 'New command allowance exhausted'
    assert size - base['combined_bytes'] < 128 * 1024**2, 'New storage allowance exhausted'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charge,
            'combined_accounted_seconds': measured + charge, 'combined_bytes': size,
            'seconds_bound': prep.SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': prep.BYTES_BOUND,
            'prior_costs_reset': False, 'older_unmeasured_authoring_time': 'UNKNOWN'}


def execute(name, argv, timeout=100, cwd=ROOT):
    started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
           'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    logs = HERE / 'commands'
    logs.mkdir(exist_ok=True)
    with (logs / (name + '.log')).open('x') as output:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    save(logs / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'exit_code': result.returncode,
         'wall_seconds': time.monotonic() - started, 'timeout_seconds': timeout})
    assert result.returncode == 0, name + ' failed; inspect retained log'


def frozen():
    for name, checksum in read(PREP / 'source-freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen source changed: ' + name
    if (HERE / 'methods.json').exists():
        for name, checksum in read(HERE / 'methods.json')['bindings'].items():
            assert sha(ROOT / name) == checksum, 'Frozen method changed: ' + name


def interval_set(projection):
    # Independent character-set oracle, intentionally not resolver interval code.
    result = set()
    for piece in projection:
        raw = piece['source']
        if raw:
            identity = (raw['unit'], raw['document'], raw['source_sha256'])
            result.update((*identity, i) for i in range(raw['start'], raw['end']))
    return result


def anchor_set(anchor):
    return {(anchor['unit'], anchor['document'], anchor['source_sha256'], i)
            for i in range(anchor['start'], anchor['end'])}


def verify(report, graph_report=None):
    request = read(PREP / 'request.json')
    expected = read(PREP / 'expected.json')['records']
    prior_index = read(PREP / 'prior-index.json')
    index = {(r['start'], r['end'], r['kind']): r for r in report['mentions']}
    errors, keys = [], set()
    assert report['request_sha256'] == prep.old.digest(request)
    assert report['report_sha256'] == prep.old.digest({k: v for k, v in report.items() if k != 'report_sha256'})
    assert len(index) == len(report['mentions'])
    for row in expected:
        key = (row['start'], row['end'], row['kind'])
        keys.add(key)
        found = index.get(key)
        if found is None:
            errors.append({'record': row['record'], 'reason': 'MISSING_MENTION'})
            continue
        assert all(found[k] == row[k] for k in ('raw', 'source_projection'))
        target = found['resolution']
        if any(target[k] != row[k] for k in ('status', 'section', 'paths')):
            errors.append({'record': row['record'], 'raw': row['raw'], 'expected': {k: row[k] for k in ('status', 'section', 'paths')},
                           'actual': target})
    actual_nodes = [n for n in report['index'] if n['path']]
    fields = ('section', 'path', 'start', 'end', 'unit', 'document', 'context', 'printed_label')
    compared = [{k: n[k] for k in fields} for n in actual_nodes]
    if compared != prior_index:
        errors.append({'reason': 'PRINTED_INDEX_DIFFERS', 'actual_count': len(compared), 'expected_count': len(prior_index),
                       'first_differences': [{'actual': a, 'expected': b} for a, b in zip(compared, prior_index) if a != b][:4]})
    for node in report['index']:
        assert node['source_projection'] == prep.old.project(request['source'], node['start'], node['end'])
        assert node['text_sha256'] == prep.old.digest(request['source']['text'][node['start']:node['end']].encode())
    for row in report['mentions']:
        assert row['source_projection'] == prep.old.project(request['source'], row['start'], row['end'])
        target = row['resolution']
        if target['target_ids']:
            for path, ident in zip(target['paths'], target['target_ids']):
                node = next(n for n in report['index'] if n['id'] == ident)
                assert node['section'] == target['section'] and node['path'] == path
                if path:
                    frozen_node = next(n for n in prior_index if n['section'] == target['section'] and n['path'] == path)
                    assert all(node[k] == frozen_node[k] for k in fields)
                else:
                    header = next(h for h in request['source']['section_headers'] if h['start'] == node['start'])
                    assert request['source']['text'][header['start']:header['end']].split()[-1] == target['section']
                    end = min((h['start'] for h in request['source']['section_headers'] if h['start'] > node['start']),
                              default=len(request['source']['text']))
                    assert node['end'] == end
    assert all(report[k] is False for k in ('legal_truth_established', 'general_recall_established',
                                           'document_authenticity_established', 'whole_task_complete'))
    relations, containment, unions = Counter(), Counter(), Counter()
    if graph_report is not None:
        graph = read(PREP / 'reviewed-graph.json')
        assert graph_report['report_sha256'] == prep.old.digest({k: v for k, v in graph_report.items() if k != 'report_sha256'})
        assert [e['reviewed_edge'] for e in graph_report['edges']] == graph['references']
        assert graph_report['resolution_sha256'] == report['report_sha256']
        all_nodes = {n['id']: n for n in report['index']}
        node_sets = {k: interval_set(n['source_projection']) for k, n in all_nodes.items()}
        for edge, actual in zip(graph['references'], graph_report['edges']):
            source_set = anchor_set(edge['source'])
            matches = {}
            for row in report['mentions']:
                mention_set = interval_set(row['source_projection'])
                if not source_set & mention_set:
                    continue
                bound = all(p['source'] is not None or (p['kind'] == 'GENERATED_SEPARATOR'
                            and request['source']['text'][p['start']:p['end']].isspace()) for p in row['source_projection'])
                relation = ('EXACT_SOURCE_MATCH' if source_set == mention_set and bound else
                            'REVIEWED_SOURCE_CONTAINS_MENTION' if mention_set <= source_set and bound else
                            'MENTION_CONTAINS_REVIEWED_SOURCE' if source_set <= mention_set else 'PARTIAL_SOURCE_INTERSECTION')
                matches[row['id']] = relation
            assert {r['mention']: r['source_relation'] for r in actual['matches']} == matches
            assert actual['no_source_relation'] == (not matches)
            for match in actual['matches']:
                relations[match['source_relation']] += 1
                row = next(r for r in report['mentions'] if r['id'] == match['mention'])
                assert [t['anchor'] for t in match['targets']] == edge['targets']
                for target in match['targets']:
                    raw_set = anchor_set(target['anchor'])
                    expected_comparisons = []
                    for ident in row['resolution']['target_ids']:
                        container_set = node_sets[ident]
                        status = ('CONTAINED_IN_PRINTED_DESTINATION' if raw_set <= container_set else
                                  'PARTIAL_PRINTED_INTERSECTION' if raw_set & container_set else 'OUTSIDE_PRINTED_DESTINATION')
                        expected_comparisons.append({'container': ident, 'relation': status})
                        containment[status] += 1
                    assert target['printed_destinations'] == expected_comparisons
                    assert target['no_printed_destination'] == (not expected_comparisons)
                    union = set().union(*(node_sets[i] for i in row['resolution']['target_ids']))
                    status = ('NO_PRINTED_DESTINATION' if not expected_comparisons else
                              'CONTAINED_IN_PRINTED_DESTINATION_UNION' if raw_set <= union else
                              'PARTIAL_PRINTED_UNION_INTERSECTION' if raw_set & union else 'OUTSIDE_PRINTED_DESTINATION_UNION')
                    assert target['union_relation'] == status
                    unions[status] += 1
    return {'status': 'PASS' if not errors else 'DEVELOPMENT_MISMATCH', 'errors': errors,
            'original_records': len({r['record'] for r in expected}), 'original_expectations': len(expected),
            'distinct_expected_mentions': len(keys), 'actual_mentions': len(index),
            'extra_mentions': len(set(index) - keys), 'printed_paragraphs': len(actual_nodes),
            'index_issues': report['index_issues'], 'discovery_issues': report['discovery_issues'],
            'source_relations': dict(relations), 'target_relations': dict(containment), 'target_union_relations': dict(unions),
            'whole_task_complete': False, 'general_recall_established': False}


def diagnose():
    from legalmath.prospectus.successor.reference_resolution import resolve, reconcile
    request = read(PREP / 'request.json')
    report = resolve(request)
    graph = reconcile(request, report, read(PREP / 'reviewed-graph.json'))
    result = verify(report, graph)
    failures = []
    for case in read(PREP / 'independent-cases.json')['cases']:
        actual = resolve(case['request'])['mentions']
        comparison = [{'raw': r['raw'], **{k: r['resolution'][k] for k in ('status', 'section', 'paths')}} for r in actual]
        if comparison != case['expected']:
            failures.append({'case': case['id'], 'expected': case['expected'], 'actual': comparison})
    result.update(role='DEVELOPMENT_ONLY', promotion_evidence=False, independent_case_failures=failures,
                  method_bindings={n: sha(ROOT / n) for n in prep.TARGETS})
    return result


def freeze():
    functions = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    before = functions(ast.parse((PREP / 'baseline/service.py').read_text()))
    after = functions(ast.parse((ROOT / prep.TARGETS[1]).read_text()))
    assert before.keys() == after.keys()
    assert all(before[n] == after[n] for n in before if n not in ('configure', 'dispatch'))
    previous = AUTH / 'attempts/basf-references/attempt-094'
    for name, checksum in read(previous / 'outputs.json').items():
        assert sha(previous / name) == checksum
    save(HERE / 'methods.json', {'bindings': {n: sha(ROOT / n) for n in FILES},
         'production_map': prior.package_files(ROOT / 'src/legalmath'),
         'unchanged_service_functions': sorted(n for n in before if n not in ('configure', 'dispatch')),
         'prior094_sealed_outputs_verified': True, 'prior_complete_answer_reexecuted': False})
    return {'status': 'PASS', 'unchanged_service_functions': len(before) - 2}


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        'tests/prospectus_successor/test_reference_resolution.py',
        'tests/prospectus_successor/test_reference_mentions.py',
        'tests/prospectus_successor/test_paragraph_references.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py', '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / 'tests.xml').getroot()
    assert not any(int(r.attrib.get('failures', 0)) or int(r.attrib.get('errors', 0)) for r in suites)
    return {'status': 'PASS', 'tests': sum(int(r.attrib.get('tests', 0)) for r in suites)}


def ordinary():
    prefix = [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', 'prospectus']
    execute('ordinary-resolution', [*prefix, 'resolve-references', '--request', str(PREP / 'request.json'),
                                  '--output', str(HERE / 'ordinary-report.json')])
    execute('ordinary-reconciliation', [*prefix, 'reconcile-references', '--request', str(PREP / 'request.json'),
        '--resolution', str(HERE / 'ordinary-report.json'), '--reviewed-graph', str(PREP / 'reviewed-graph.json'),
        '--output', str(HERE / 'ordinary-graph.json')])
    return {'status': 'PASS', 'source_resolution_precedes_reviewed_graph': True, 'actual_cli': True}


def audit():
    result = verify(read(HERE / 'ordinary-report.json'), read(HERE / 'ordinary-graph.json'))
    save(HERE / 'independent-verification.json', result)
    assert result['status'] == 'PASS' and result['extra_mentions'] == 0
    assert not result['index_issues'] and not result['discovery_issues']
    return result


def package():
    # Reuse the already reviewed offline wheel routine with this attempt's
    # explicit inputs. No historical files or methods are modified.
    prior.ROOT, prior.AUTH, prior.HERE, prior.prep, prior.execute = ROOT, AUTH, HERE, prep, execute
    return prior.package()


def installed():
    execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B',
        str(ROOT / 'scripts/prospectus_reference_resolution_installed.py'), str(ROOT), str(HERE), str(PREP)], cwd=HERE)
    return read(HERE / 'installed-result.json')


def seal():
    verification = read(HERE / 'independent-verification.json')
    decision = HERE / 'decision.md'
    assert decision.exists() and (HERE / 'graph-dispositions.json').exists()
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
              'result_kind': 'SOURCE_ONLY_PRINTED_RESOLUTION_AND_REVIEWED_GRAPH_RECONCILIATION',
              **{k: v for k, v in verification.items() if k not in ('errors', 'index_issues', 'discovery_issues')},
              'ordinary_installed_equal': True, 'reviewed_edges_preserved': 47,
              'statutory_records_retained': 12, 'prior_full_answer_reexecuted': False,
              'resources': costs(), 'next_action': 'Original62 definitions/612 associations, then seven original gap classes and full-answer revalidation'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
         'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
         'environment': str(ROOT / '.venv/bin/python'), 'installed_environment': read(HERE / 'package.json')['python'],
         'cpu_gpu': 'CPU;GPU intentionally hidden', 'seeds': 'N/A deterministic',
         'data_version': sha(PREP / 'request.json'), 'wall_time': costs(), 'plan': prep.PLAN,
         'result': rel(HERE / 'result.json')})
    return result


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    stage = sys.argv[1]
    assert stage in ('diagnose', 'probe') or stage in STAGES
    frozen()
    if stage in ('diagnose', 'probe'):
        assert not (HERE / 'methods.json').exists(), 'Reviewed repair required after formal freeze'
        start = time.monotonic()
        name = 'diagnostic-' + str(len(list((HERE / 'development').glob('*.json'))) + 1).zfill(3) + '.json'
        try:
            if stage == 'diagnose':
                result = diagnose()
            else:
                execute('development-tests-' + name.removesuffix('.json'), [str(ROOT / '.venv/bin/python'),
                    '-m', 'pytest', '-q', 'tests/prospectus_successor/test_reference_resolution.py'])
                result = {'status': 'PASS', 'role': 'DEVELOPMENT_ONLY', 'promotion_evidence': False}
        except Exception as error:
            result = {'status': 'DEVELOPMENT_FAILURE', 'exception': type(error).__name__, 'reason': str(error)}
            raise
        finally:
            result['wall_seconds'] = time.monotonic() - start
            save(HERE / 'development' / name, result)
        costs()
        print(json.dumps({k: v for k, v in result.items() if k not in ('method_bindings',)}, ensure_ascii=False))
        return
    for previous in STAGES[:STAGES.index(stage)]:
        assert read(HERE / 'stages' / previous / 'result.json')['status'] == 'PASS'
    folder = HERE / 'stages' / stage
    assert not folder.exists(), 'Unchanged stage retry refused'
    costs()
    start = time.monotonic()
    save(folder / 'started.json', {'command': sys.argv, 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[stage]()
        frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps({k: v for k, v in result.items() if k not in ('resources', 'errors', 'index_issues', 'discovery_issues')}, ensure_ascii=False))
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'reason': str(error), 'exception': type(error).__name__,
             'wall_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
