"""Retained, bounded stages for exact definition naming and syntax evidence."""
import ast
from collections import Counter
from datetime import datetime, timezone
import json
import os
import sys
import time

from scripts import prospectus_definition_declarations_trial as prep
from scripts import prospectus_reference_resolution_run as previous
from scripts import prospectus_reference_mentions_run as packaging

ROOT, AUTH, PREP, HERE = prep.ROOT, prep.AUTH, prep.PREP, prep.HERE
read, save, rel, sha = prep.read, prep.save, prep.rel, prep.sha
FILES = (prep.METHOD, prep.PLAN, 'scripts/prospectus_definition_declarations_run.py',
         'scripts/prospectus_definition_declarations_installed.py',
         'tests/prospectus_successor/test_definition_declarations.py', *prep.TARGETS,
         rel(HERE / 'development/repair-review.md'), rel(HERE / 'development/expectation-corrections.json'),
         rel(HERE / 'development/resumption-audit.md'), rel(HERE / 'development/cli-repair-review.md'))
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
    paths.add(AUTH / 'revisions/0357.json')
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
    previous.ROOT, previous.HERE = ROOT, HERE
    previous.execute(name, argv, timeout=timeout, cwd=cwd)


def frozen():
    for name, checksum in read(PREP / 'source-freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen source changed: ' + name
    if (HERE / 'methods.json').exists():
        for name, checksum in read(HERE / 'methods.json')['bindings'].items():
            assert sha(ROOT / name) == checksum, 'Frozen method changed: ' + name


def verify(report, reconciliation):
    request = read(PREP / 'request.json')
    expected = read(PREP / 'expected.json')
    lineage = read(PREP / 'lineage.json')
    text = request['source']['text']
    actual = {(r['start'], r['end']): r for r in report['names']}
    corrections = read(HERE / 'development/expectation-corrections.json')
    source_status = {(r['start'], r['end']): r for r in corrections['original_source_status']}
    errors = []
    assert len(actual) == len(report['names'])
    assert report['request_sha256'] == prep.digest(request)
    for result in (report, reconciliation):
        assert result['report_sha256'] == prep.digest({k: v for k, v in result.items() if k != 'report_sha256'})
        assert result['legal_truth_established'] is False and result['whole_task_complete'] is False
    for row in expected['tokens']:
        found = actual.get((row['start'], row['end']))
        qualification = source_status.get((row['start'], row['end']), {'status': 'DECLARATION_SYNTAX', 'syntax': row['syntax']})
        if (found is None or found['observed_syntax'] != row['syntax'] or
                found['syntax'] != qualification['syntax'] or found['status'] != qualification['status']):
            errors.append({'record': row['record'], 'start': row['start'], 'raw': row['raw'],
                'expected': {'observed_syntax': row['syntax'], **qualification}, 'actual': None if found is None else
                {k: found[k] for k in ('observed_syntax', 'syntax', 'status')}})
        elif found['source_projection'] != row['source_projection']:
            errors.append({'record': row['record'], 'reason': 'RAW_PROJECTION_DIFFERS'})
    expected_keys = {(r['start'], r['end']) for r in expected['tokens']}
    extras = sorted(set(actual) - expected_keys)
    for row in report['names'] + report['restrictions']:
        for item in [row] + ([row['syntax_evidence']] if row.get('syntax_evidence') else []):
            a, b = item['start'], item['end']
            assert text[a:b] == item['raw']
            assert item['source_projection'] == prep.old.old.project(request['source'], a, b)
        assert row.get('legal_declaration_established', False) is False
        assert row.get('governing_scope') is None
        assert row.get('resolved_extent') is None
    restrictions = [{k: r[k] for k in ('start', 'end', 'raw')} for r in report['restrictions']]
    if restrictions != expected['restrictions']:
        errors.append({'reason': 'PRINTED_RESTRICTIONS_DIFFER', 'actual': restrictions})
    assert reconciliation['retained_lineage'] == lineage
    assert reconciliation['reviewed_lineage_sha256'] == prep.digest(lineage)
    assert [r['record'] for r in reconciliation['records']] == [r['id'] for r in lineage['records']]
    for row, original in zip(reconciliation['records'], lineage['records']):
        assert row['retained_record_sha256'] == prep.digest(original)
        dependency = next(d for d in lineage['dependencies'] if d['record'] == row['record'])
        assert row['remaining_premises'] == dependency['remaining_premises']
        expected_tokens = [r for r in lineage['naming_tokens'] if r['record'] == row['record']]
        assert [t['token'] for t in row['naming_tokens']] == expected_tokens
    uses = Counter(u['origin'] for u in lineage['uses'])
    assert uses == {'ORIGINAL': 610, 'SUPPLEMENTAL': 2}
    assert not any(u['disposition'] == 'UNRECONCILED' for u in lineage['uses'])
    return {'status': 'PASS' if not errors and not extras else 'DEVELOPMENT_MISMATCH',
        'errors': errors, 'extra_names': extras, 'records': len(lineage['records']),
        'quoted_records': len({r['record'] for r in expected['tokens']}), 'naming_tokens': len(actual),
        'original_associations': uses['ORIGINAL'], 'supplemental_associations': uses['SUPPLEMENTAL'],
        'syntax_counts': dict(Counter(r['syntax'] for r in report['names'])),
        'observed_syntax_counts': dict(Counter(r['observed_syntax'] for r in report['names'])),
        'source_status_counts': dict(Counter(r['status'] for r in report['names'])),
        'printed_restrictions': len(restrictions), 'issues': report['issues'],
        'premises_preserved': True, 'whole_task_complete': False}


def diagnose():
    from legalmath.prospectus.successor.definition_declarations import discover, reconcile
    request = read(PREP / 'request.json')
    report = discover(request)
    reconciliation = reconcile(request, report, read(PREP / 'lineage.json'))
    result = verify(report, reconciliation)
    failures = []
    for case in read(PREP / 'independent-cases.json')['cases']:
        answer = discover(case['request'])
        actual = [{k: r[k] for k in ('start', 'end', 'raw', 'syntax')} for r in answer['names']]
        expected = [dict(r) for r in case['expected']]
        for correction in read(HERE / 'development/expectation-corrections.json')['arbitrary_fixture_corrections']:
            if correction['case'] == case['id']:
                row = next(r for r in expected if r['start'] == correction['old_start'] and r['end'] == correction['old_end'])
                assert row['raw'] == correction['raw']
                row.update(start=correction['start'], end=correction['end'])
        if actual != expected or (case['issue_required'] and not answer['issues']):
            failures.append({'case': case['id'], 'expected': expected, 'actual': actual,
                             'issues': answer['issues']})
    result.update(role='DEVELOPMENT_ONLY', promotion_evidence=False, independent_case_failures=failures,
                  method_bindings={n: sha(ROOT / n) for n in prep.TARGETS})
    return result


def freeze():
    functions = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    before = functions(ast.parse((PREP / 'baseline/service.py').read_text()))
    after = functions(ast.parse((ROOT / prep.TARGETS[1]).read_text()))
    assert before.keys() == after.keys()
    assert all(before[n] == after[n] for n in before if n not in ('configure', 'dispatch'))
    previous_attempt = AUTH / 'attempts/basf-references/attempt-095'
    for name, checksum in read(previous_attempt / 'outputs.json').items():
        assert sha(previous_attempt / name) == checksum
    save(HERE / 'methods.json', {'bindings': {n: sha(ROOT / n) for n in FILES},
        'production_map': packaging.package_files(ROOT / 'src/legalmath'),
        'unchanged_service_functions': sorted(n for n in before if n not in ('configure', 'dispatch')),
        'prior095_sealed_outputs_verified': True, 'prior_complete_answer_reexecuted': False})
    return {'status': 'PASS', 'unchanged_service_functions': len(before) - 2}


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        'tests/prospectus_successor/test_definition_declarations.py',
        'tests/prospectus_successor/test_reference_resolution.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py', '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / 'tests.xml').getroot()
    assert not any(int(r.attrib.get('failures', 0)) or int(r.attrib.get('errors', 0)) for r in suites)
    return {'status': 'PASS', 'tests': sum(int(r.attrib.get('tests', 0)) for r in suites)}


def ordinary():
    prefix = [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', 'prospectus']
    execute('ordinary-discovery', prefix + ['discover-definition-declarations', '--request', str(PREP / 'request.json'),
        '--output', str(HERE / 'ordinary-report.json')])
    execute('ordinary-reconciliation', prefix + ['reconcile-definition-declarations', '--request', str(PREP / 'request.json'),
        '--discovery', str(HERE / 'ordinary-report.json'), '--lineage', str(PREP / 'lineage.json'),
        '--output', str(HERE / 'ordinary-reconciliation.json')])
    return {'status': 'PASS', 'actual_cli': True}


def audit():
    result = verify(read(HERE / 'ordinary-report.json'), read(HERE / 'ordinary-reconciliation.json'))
    save(HERE / 'independent-verification.json', result)
    assert result['status'] == 'PASS' and not result['issues']
    return result


def package():
    packaging.ROOT, packaging.AUTH, packaging.HERE = ROOT, AUTH, HERE
    packaging.prep, packaging.execute = prep, execute
    return packaging.package()


def installed():
    execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B',
        str(ROOT / 'scripts/prospectus_definition_declarations_installed.py'), str(ROOT), str(HERE), str(PREP)], cwd=HERE)
    return read(HERE / 'installed-result.json')


def seal():
    assert (HERE / 'decision.md').exists()
    verification = read(HERE / 'independent-verification.json')
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'SOURCE_ONLY_DECLARATION_SYNTAX_AND_EXACT_TOKEN_LINEAGE',
        **{k: v for k, v in verification.items() if k not in ('errors', 'issues')},
        'ordinary_installed_equal': True, 'prior_full_answer_reexecuted': False, 'resources': costs(),
        'next_action': 'Review remaining governing scope, historical/onward law, default(f), office and incorporation; affected full-answer revalidation'}
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
        name = 'diagnostic-' + str(len(list((HERE / 'development').glob('*.json'))) + 1).zfill(3)
        result = {'status': 'DEVELOPMENT_FAILURE'}
        try:
            if stage == 'diagnose':
                result = diagnose()
            else:
                execute(name, [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
                    'tests/prospectus_successor/test_definition_declarations.py'])
                result = {'status': 'PASS', 'role': 'DEVELOPMENT_ONLY', 'promotion_evidence': False}
        except Exception as error:
            result.update(exception=type(error).__name__, reason=str(error))
            raise
        finally:
            result['wall_seconds'] = time.monotonic() - start
            save(HERE / 'development' / (name + '.json'), result)
        costs()
        print(json.dumps({k: v for k, v in result.items() if k != 'method_bindings'}, ensure_ascii=False))
        return
    for earlier in STAGES[:STAGES.index(stage)]:
        assert read(HERE / 'stages' / earlier / 'result.json')['status'] == 'PASS'
    folder = HERE / 'stages' / stage
    assert not folder.exists(), 'Unchanged stage retry refused'
    costs()
    start = time.monotonic()
    save(folder / 'started.json', {'command': sys.argv, 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[stage]()
        frozen(); costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps({k: v for k, v in result.items() if k not in ('resources', 'errors', 'issues')}, ensure_ascii=False))
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'reason': str(error), 'exception': type(error).__name__,
            'wall_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
