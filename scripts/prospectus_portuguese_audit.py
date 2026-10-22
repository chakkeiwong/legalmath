"""Bounded Portuguese003 source-role consumers; admission stays with the authority."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

PROCESS_STARTED = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
HERE = BASE / 'attempts/portuguese-2008/attempt-003'
PRIOR = HERE.parent / 'attempt-001'
SECOND = HERE.parent / 'attempt-002'
PLAN = 'docs/plans/prospectus-portuguese-audit-roles-2026-10-16.md'
REVIEW = BASE / 'reviews/portuguese-audit-107/source-review.json'
AUDITS = ('consolidated', 'individual')
MUTATIONS = ('board', 'omitted-materiality', 'extra-board', 'missing-assurance')
CASES = ['positive-v1', 'positive-v2'] + [
    f'{mutation}-{audit}-{profile}' for mutation in MUTATIONS for audit in AUDITS
    for profile in ('v1', 'v2')] + ['wrong-date-v2', 'omitted-exception-v2']
TESTS = ['tests/prospectus_successor/test_report_scope.py',
         'tests/prospectus_successor/test_english_report_context.py',
         'tests/prospectus_successor/test_portuguese_audit_roles.py']


def file_hash(path):
    with Path(path).open('rb') as stream:
        h = sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(name, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if name.endswith('.gz'):
        data = gzip.compress(data, mtime=0)
    with (HERE / name).open('xb') as stream:
        stream.write(data)


def methods():
    paths = [*sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py')), Path(__file__)]
    paths += [ROOT / name for name in TESTS if (ROOT / name).is_file()]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def verify_bindings(name):
    assert all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items()), name


def forbid(*args, **kwargs):
    raise RuntimeError('Native/process/network execution forbidden in Portuguese003')


def boundaries():
    # Keep source_product available: its plain-text fixture path is in-process.
    subprocess.Popen = forbid
    os.system = forbid
    if hasattr(os, 'posix_spawn'):
        os.posix_spawn = forbid
    if hasattr(os, 'posix_spawnp'):
        os.posix_spawnp = forbid
    socket.create_connection = forbid
    socket.socket.connect = forbid
    socket.socket.connect_ex = forbid


def ledger():
    starts = list(HERE.glob('stage-*-start.json'))
    ends = list(HERE.glob('stage-*-result.json'))
    assert len(starts) == len(ends), 'An earlier stage is incomplete; do not duplicate it'
    elapsed = sum(read(p)['wall_seconds'] for p in ends)
    assert elapsed < 480, 'Cumulative execution bound reached'
    assert not any(read(p)['status'] == 'FAIL' for p in ends), 'A stage veto forbids further execution'
    return elapsed


def next_call(case):
    calls = len(list(HERE.glob('call-*.json')))
    assert calls < 24, 'Actual-consumer bound reached'
    save(f'call-{calls + 1:03d}.json', {'case': case, 'started_utc': datetime.now(timezone.utc).isoformat()})


def span(text, start, end):
    return {'start': start, 'end': end, 'quote': text[start:end]}


def scope_for(case):
    scope = deepcopy(read(SECOND / 'positive-v2-scope.json'))
    if case.endswith('-v2'):
        scope['context_profile'] = 'portuguese-report-context.v2'
    if case.startswith('positive'):
        return scope
    selected = {r['id']: r for r in read(PRIOR / 'selected-reading.json')['reports']}
    if case.startswith('wrong-date'):
        row = next(r for r in scope['reports'] if r['id'] == 'committee-2008-pt')
        text = selected[row['id']]['text']
        quote = '13 de Março de 2008'
        a = text.index(quote)
        row['facts']['report_date']['spans'] = [span(text, a, a + len(quote))]
        return scope
    if case.startswith('omitted-exception'):
        row = next(r for r in scope['reports'] if r['id'] == 'individual-2008-pt')
        text = selected[row['id']]['text']
        a = text.index('Normas Internacionais de Relato Financeiro em vigor tal como')
        b = text.index(', com excepção', a)
        row['facts']['criteria']['spans'][1] = span(text, a, b)
        return scope
    audit = next(a for a in AUDITS if f'-{a}-' in case)
    rid = audit + '-2008-pt'
    row = next(r for r in scope['reports'] if r['id'] == rid)
    text = selected[rid]['text']
    roles = next(r['roles'] for r in read(REVIEW)['reports'] if r['id'] == rid)
    board = roles['board_responsibilities']
    if case.startswith('board-'):
        row['facts']['conclusion']['spans'] = [deepcopy(board)]
    elif case.startswith('omitted-materiality-'):
        opinion, materiality = roles['financial_statement_opinion'], roles['opinion_materiality']
        row['facts']['conclusion']['spans'] = [span(text, opinion['start'], materiality['start']),
                                              span(text, materiality['end'], opinion['end'])]
    elif case.startswith('extra-board-'):
        row['facts']['conclusion']['spans'].append(deepcopy(board))
    elif case.startswith('missing-assurance-'):
        # Exact source words about financial information, but from board duties.
        row['facts']['assurance_level']['spans'] = [deepcopy(board)]
    else:
        raise ValueError(case)
    return scope


def common():
    assert file_hash(HERE / 'common-products.json.gz') == read(HERE / 'prepare-data.json')['common_sha256']
    products = read(HERE / 'common-products.json.gz')
    for name, product in products.items():
        service.verify(product, name)
    return products


def prepare():
    admission = read(HERE / 'admission.json')
    assert admission['task'] == 'portuguese-2008' and admission['revision'] == 107
    assert Path(service.__file__).resolve().is_relative_to(ROOT / 'src')
    verified = {}
    for prior in (PRIOR, SECOND):
        outputs = read(prior / 'outputs.json')
        assert all(file_hash(prior / p) == h for p, h in outputs.items()), str(prior)
        verified[prior.name] = {'files': len(outputs), 'outputs_sha256': file_hash(prior / 'outputs.json')}
    expected = read(REVIEW)['current_methods']
    assert all(file_hash(ROOT / p) == h for p, h in expected.items())
    for name in ('report_scope.py', 'report_context.py'):
        (HERE / 'before').mkdir(exist_ok=True)
        with (HERE / 'before' / name).open('xb') as stream:
            stream.write((ROOT / 'src/legalmath/prospectus/successor' / name).read_bytes())
    original = read(PRIOR / 'source-product.json.gz')
    service.verify(original, 'P1')
    request = deepcopy(original['payload']['request'])
    sources = {}
    for document in request['bundle']['documents']:
        assert file_hash(ROOT / document['path']) == document['sha256']
        sources[document['path']] = document['sha256']
    request['source_report_readings'] = read(PRIOR / 'reading-admission.json')
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)},
                      {'request': request, 'graph': original['payload']['graph']})
    p2 = service.construction_product(p1, ROOT)
    assert p2['payload']['source_report_readings'] == read(PRIOR / 'selected-reading.json')
    save('common-products.json.gz', {'P1': p1, 'P2': p2})
    bindings = {**admission['binding'], **sources}
    for prior in (PRIOR, SECOND):
        bindings.update({str((prior / p).relative_to(ROOT)): h for p, h in read(prior / 'outputs.json').items()})
    save('input-bindings.json', bindings)
    save('before-methods.json', methods())
    save('prepare-data.json', {'verified': verified, 'common_sha256': file_hash(HERE / 'common-products.json.gz'),
         'source_mode': 'Authenticated retained historical P1, fresh current P2 onward; no new extraction'})
    return {'verified_prior_files': sum(v['files'] for v in verified.values()), 'fresh_P2': True}


def run_case(case, frozen):
    verify_bindings('input-bindings.json')
    verify_bindings(frozen)
    products = common()
    scope = scope_for(case)
    next_call(case)
    print(json.dumps({'case': case, 'stage': 'actual-current-P3-to-final'}), flush=True)
    p1, p2 = products['P1'], products['P2']
    p3 = service.interpretation_product(p1, p2, {'source_report_scope': scope})
    later = {'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume({**products, **later}, ROOT)
    # Retain the complete actual output before interpreting or asserting it.
    save(case + '-scope.json', scope)
    save(case + '-products.json.gz', later)
    save(case + '-answer.json.gz', answer)
    assert answer['consumed_products'] == {k: v['sha256'] for k, v in {**products, **later}.items()}
    assert not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
    reports = {r['id']: r for r in answer['source_reports']}
    target = next((a + '-2008-pt' for a in AUDITS if f'-{a}-' in case),
                  'committee-2008-pt' if case.startswith('wrong-date') else
                  'individual-2008-pt' if case.startswith('omitted-exception') else None)
    for rid, report in reports.items():
        supported = case.endswith('v1') or case.startswith('positive') or rid != target
        assert report['status'] == ('CONDITIONAL_SUPPLIED_READING' if supported else 'INCOMPLETE_SOURCE_READING'), (case, rid)
        use = 'committee_concurrence' if rid.startswith('committee') else 'financial_statement_audit_opinion'
        assert report['use_assessment'][use] == ('SUPPLIED_SOURCE_SUPPORT' if supported else 'NOT_ESTABLISHED_BY_THIS_READING')
    verify_bindings(frozen)
    result = {'status': 'PASS', 'case': case, 'methods_sha256': file_hash(HERE / frozen),
              'reports': {rid: {'status': r['status'], 'context_issues': r['unresolved_context_fields']}
                          for rid, r in reports.items()}}
    save(case + '-case-result.json', result)
    return result


def baseline():
    a = run_case('positive-v1', 'before-methods.json')
    b = run_case('board-consolidated-v1', 'before-methods.json')
    assert all(r['status'] == 'CONDITIONAL_SUPPLIED_READING' for r in b['reports'].values())
    return {'baseline_reproduced': True, 'positive': a['reports'], 'board_only': b['reports']}


def candidate():
    assert read(HERE / 'stage-baseline-result.json')['details']['baseline_reproduced']
    before = read(HERE / 'before-methods.json')
    permitted = {'src/legalmath/prospectus/successor/report_scope.py',
                 'src/legalmath/prospectus/successor/report_context.py'}
    assert all(file_hash(ROOT / p) == h for p, h in before.items() if p not in permitted)
    spec = importlib.util.spec_from_file_location('legalmath.prospectus.successor._portuguese003_before', HERE / 'before/report_scope.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    context_name = 'legalmath.prospectus.successor.report_context'
    context_spec = importlib.util.spec_from_file_location(context_name, HERE / 'before/report_context.py')
    old_context = importlib.util.module_from_spec(context_spec)
    context_spec.loader.exec_module(old_context)
    current_context = importlib.import_module(context_name)
    selected = common()['P2']['payload']['source_report_readings']
    checks = {}
    for case in CASES:
        if not case.endswith('-v1'):
            continue
        # The old admission imports its context locally. Bind the saved old
        # dependency as well, so the comparator cannot share a changed checker.
        try:
            sys.modules[context_name] = old_context
            expected = old.admit(selected, scope_for(case))
        finally:
            sys.modules[context_name] = current_context
        checks[case] = expected == report_scope.admit(selected, scope_for(case))
    assert all(checks.values())
    assert all((ROOT / name).is_file() for name in TESTS)
    save('frozen-methods.json', methods())
    save('v1-compatibility.json', checks)
    return {'old_profile_exactly_equal': checks, 'candidate_methods_frozen': True}


def tests():
    verify_bindings('frozen-methods.json')
    import pytest
    with (HERE / 'tests.log').open('x') as output, redirect_stdout(output), redirect_stderr(output):
        code = pytest.main(['-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')])
    cases = list(ET.parse(HERE / 'tests.xml').getroot().iter('testcase'))
    result = {'exit_code': int(code), 'tests': len(cases),
              'failures': [t.attrib.get('name') for t in cases if any(t.find(k) is not None for k in ('failure', 'error', 'skipped'))],
              'pytest_args': ['-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')]}
    save('test-summary.json', result)
    assert code == 0 and not result['failures'], result
    verify_bindings('frozen-methods.json')
    return result


def compare():
    verify_bindings('input-bindings.json')
    verify_bindings('frozen-methods.json')
    checks, answers, scopes = {}, {}, {}
    base = common()
    selected = {r['id']: r for r in base['P2']['payload']['source_report_readings']['reports']}
    stable = None
    for case in CASES:
        result = read(HERE / (case + '-case-result.json'))
        answer = read(HERE / (case + '-answer.json.gz'))
        later = read(HERE / (case + '-products.json.gz'))
        scope = read(HERE / (case + '-scope.json'))
        answers[case], scopes[case] = answer, scope
        for name, product in later.items():
            service.verify(product, name)
        checks[case + ': complete actual product identities'] = answer['consumed_products'] == {k: v['sha256'] for k, v in {**base, **later}.items()}
        checks[case + ': actual answer integrity'] = answer['report_sha256'] == digest({k: v for k, v in answer.items() if k != 'report_sha256'})
        checks[case + ': actual supplied input'] = later['P3']['payload']['interpretation_input']['source_report_scope'] == scope
        checks[case + ': actual report output'] = answer['source_reports'] == report_scope.explain(later['P3']['payload']['source_report_scope'])
        checks[case + ': no independent/transaction permission'] = not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
        payloads = {k: {x: v for x, v in p['payload'].items() if x not in ('source_report_scope', 'interpretation_input')}
                    for k, p in later.items()}
        if stable is None:
            stable = payloads
        checks[case + ': contractual law financial payload equality'] = payloads == stable
        checks[case + ': actual run passed'] = result['status'] == 'PASS'
        for report in answer['source_reports']:
            rid = report['id']
            checks[case + ': external unknowns ' + rid] = all(report['facts'][f]['status'] == 'UNKNOWN' for f in report_scope.EXTERNAL)
            checks[case + ': no repayment availability promotion ' + rid] = all(report['use_assessment'][f] == 'NOT_ESTABLISHED_BY_THIS_READING' for f in ('bond_repayment_or_conversion', 'historical_availability'))
            def exact(value):
                if isinstance(value, list):
                    return all(exact(v) for v in value)
                if not isinstance(value, dict):
                    return True
                if {'start', 'end', 'quote', 'source_characters'} <= value.keys():
                    reading = selected[rid]
                    return (reading['text'][value['start']:value['end']] == value['quote'] and
                            value['source_characters'] == [c for c in reading['characters'] if value['start'] <= c['output'] < value['end']])
                return all(exact(v) for v in value.values())
            checks[case + ': all context anchors exact ' + rid] = exact(report['context_review'])
    positive = {r['id']: r for r in answers['positive-v2']['source_reports']}
    for case, answer in answers.items():
        checks[case + ': debt answers equal'] = answer['questions'] == answers['positive-v1']['questions']
        if case.endswith('-v2') and not case.startswith('positive'):
            target = next((a + '-2008-pt' for a in AUDITS if f'-{a}-' in case),
                          'committee-2008-pt' if case.startswith('wrong-date') else 'individual-2008-pt')
            reports = {r['id']: r for r in answer['source_reports']}
            checks[case + ': unaffected reports exactly equal'] = all(r == positive[rid] for rid, r in reports.items() if rid != target)
        if case.endswith('-v2') and case[:-2] + 'v1' in answers:
            other = case[:-2] + 'v1'
            checks[case + ': paired supplied facts equal'] = [r['facts'] for r in answer['source_reports']] == [r['facts'] for r in answers[other]['source_reports']]
            checks[case + ': profile is sole paired input change'] = {k: v for k, v in scopes[case].items() if k != 'context_profile'} == {k: v for k, v in scopes[other].items() if k != 'context_profile'}
    checks['all frozen old-profile checks pass'] = all(read(HERE / 'v1-compatibility.json').values())
    checks['focused tests pass without skip'] = read(HERE / 'stage-tests-result.json')['status'] == 'PASS'
    checks['new evidence below120MB'] = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) < 119_000_000
    output = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'actual_cases': CASES, 'failed': [k for k, v in checks.items() if not v]}
    save('comparison.json', output)
    assert output['status'] == 'PASS', output['failed']
    return {'checks': len(checks), 'failed': output['failed']}


def seal():
    ends = [read(p) for p in HERE.glob('stage-*-result.json')]
    passed = (HERE / 'comparison.json').is_file() and read(HERE / 'comparison.json')['status'] == 'PASS' and all(r['status'] == 'PASS' for r in ends)
    if passed:
        verify_bindings('input-bindings.json')
        verify_bindings('frozen-methods.json')
    assert (HERE / 'RESULT.md').is_file() and (HERE / 'NEXT-WORK.md').is_file()
    elapsed = sum(r['wall_seconds'] for r in ends) + time.monotonic() - PROCESS_STARTED
    assert elapsed < 480
    result = {'task': 'portuguese-2008', 'status': 'PASS' if passed else 'FAIL', 'task_complete': False,
              'meaning_of_status': 'Finite source-bound optional audit-role integration only; independent Portuguese/source acceptance remains open',
              'actual_consumer_calls': len(list(HERE.glob('call-*.json'))), 'wall_seconds': elapsed,
              'acceptance_blockers': ['Independent source-bound Portuguese review absent',
                  'Publication, historical availability and edition authenticity unknown',
                  'No unseen-language or new native/installed acceptance evidence'],
              'result_note': 'RESULT.md', 'next_action': 'Inspect authority and independent source-authority assessment; no automatic fourth admission'}
    save('result.json', result)
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
               if p.is_file() and p.name not in ('outputs.json', 'admission.json') and '__pycache__' not in p.parts}
    size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    assert size < 120_000_000
    save('outputs.json', outputs)
    return {'status': result['status'], 'files': len(outputs), 'bytes': size, 'wall_seconds': elapsed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'baseline', 'candidate', 'cases', 'tests', 'compare', 'seal'])
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    if args.stage == 'seal':
        print(json.dumps(seal()), flush=True)
        return
    assert not (HERE / 'outputs.json').exists()
    previous_elapsed = ledger()
    if args.stage not in ('prepare', 'baseline'):
        assert read(HERE / 'stage-baseline-result.json')['status'] == 'PASS'
    if args.stage in ('cases', 'tests', 'compare'):
        assert read(HERE / 'stage-candidate-result.json')['status'] == 'PASS'
    assert args.stage != 'cases' or args.case, 'Select one actual case for bounded execution'
    name = args.stage + ('-' + args.case if args.case else '')
    started = PROCESS_STARTED
    command = ['timeout', '120', '.venv/bin/python', '-m', 'scripts.prospectus_portuguese_audit', *sys.argv[1:]]
    save('stage-' + name + '-start.json', {'command': command, 'started_utc': datetime.now(timezone.utc).isoformat()})
    def expired(signum, frame):
        raise TimeoutError('Reviewed stage/cumulative time bound reached')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(max(1, min(118, int(480 - previous_elapsed))))
    boundaries()
    outcome = {'status': 'PASS'}
    try:
        outcome['details'] = run_case(args.case, 'frozen-methods.json') if args.stage == 'cases' else globals()[args.stage]()
    except Exception as error:
        outcome.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
        with (HERE / ('stage-' + name + '-traceback.txt')).open('x') as stream:
            traceback.print_exc(file=stream)
    finally:
        signal.alarm(0)
    outcome.update(wall_seconds=time.monotonic() - started, command=command,
                   environment=sys.executable, git_commit=read(HERE / 'admission.json')['git_commit'],
                   cpu_gpu='CPU only; GPUs intentionally hidden before product imports', random_seeds='N/A',
                   data_version='input-bindings.json; authenticated original PDF and sealed001/002',
                   plan=PLAN, result='RESULT.md', completed_utc=datetime.now(timezone.utc).isoformat())
    save('stage-' + name + '-result.json', outcome)
    print(json.dumps({'stage': name, 'status': outcome['status'], 'wall_seconds': outcome['wall_seconds'],
                      'error': outcome.get('error')}), flush=True)
    if outcome['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
