"""Reproduce and verify exact-quantity refusals through retained real consumers."""
import argparse
from copy import deepcopy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
sys.dont_write_bytecode = True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as authority_digest
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor import service, contract_terms, financial_profiles
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_comparative_oracle import require

SOURCE = REL+'/attempts/finance-conventions'
RETAINED = REL+'/attempts/entitlement/attempt-003'
PREPARATION = REL+'/continuation-reviews/exact-quantity-preparation'
REVIEW = REL+'/reviews/exact-quantity-214'
RECORD = REL+'/continuation-reviews/exact-quantity-214-record'
PLAN = 'docs/plans/prospectus-exact-quantity-refusal-2026-10-17.md'
TESTS = ('tests/prospectus/test_exact_quantity_refusal.py', 'tests/prospectus/test_semantics.py',
    'tests/prospectus/test_joined_eligibility.py', 'tests/prospectus_successor/test_closure_finance.py',
    'tests/prospectus_successor/test_closure_coupon_anchor.py', 'tests/prospectus_successor/test_initial_coupon.py',
    'tests/prospectus_successor/test_bond_basis.py', 'tests/prospectus/test_build_contract.py')
METHODS = ('scripts/prospectus_exact_quantity.py', 'scripts/prospectus_comparative_oracle.py',
    'src/legalmath/prospectus/semantics.py', 'src/legalmath/prospectus/build_contract.py',
    'src/legalmath/prospectus/successor/fixed_coupon.py', 'src/legalmath/prospectus/successor/coupon_amounts.py',
    'src/legalmath/prospectus/successor/contract_terms.py', 'src/legalmath/prospectus/successor/financial_profiles.py',
    'src/legalmath/prospectus/successor/service.py', 'scripts/prospectus_closure_fixtures.py', *TESTS)
METHODS = tuple(sorted(set(METHODS) | {
    str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath/prospectus/successor').glob('*.py')
} | {'src/legalmath/prospectus/eligibility.py'}))
SELECTOR = {'version': 'exact-quantity-refusal.v1', 'preparation_seconds': 90, 'candidate_seconds': 180,
    'validation_seconds': 180, 'new_seconds': 450, 'new_bytes': 40*1024**2, 'reserve_bytes': 262144,
    'historical_unrecorded_seconds': 'UNKNOWN; no cumulative runtime claim',
    'network_package_install_extraction_OCR_model_GPU': 0}


def load(path):
    with gzip.open(path, 'rt') as stream: return json.load(stream)


def helper():
    spec = importlib.util.spec_from_file_location('retained_quantity_consumers', ROOT/RETAINED/'run_rounding.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def selected_v4_packet():
    ps = load(ROOT/SOURCE/'attempt-002/selected-definitive-products.json.gz')
    for phase, product in ps.items(): service.verify(product, phase)
    return ps['P1']['payload']['graph'], ps['P2']['payload']['assembly'], deepcopy(ps['P1']['payload']['request']['term_interpretations'])


def compressed(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode(), mtime=0))


def baseline(name):
    manifest = read(ROOT/RETAINED/'outputs.json'); path = ROOT/RETAINED/'baseline'/name
    require(file_hash(path) == manifest['baseline/'+name], 'Sealed full answer changed')
    return load(path) if name.endswith('.gz') else read(path)


def actual_checks():
    h = helper(); valid, refusals = [], []
    for family in ('danske', 'shell-global', 'shell-definitive'):
        for route in ('direct', 'selected'):
            ps = h.products_for(route) if family == 'danske' else h.shell_products(route+'-'+family.split('-')[1])
            for entitled in (True, False):
                supplied, rounding = h.inputs(ps, route)
                for row in supplied['holdings']: row['entitled'] = entitled
                record = h.consume(ps, route) if entitled else h.consume(ps, route, supplied, rounding)
                name = (route+'-original' if family == 'danske' else 'shell-'+route+'-'+family.split('-')[1])
                name += '-'+('active' if entitled else 'excluded')+'.json.gz'
                h.assert_valid(record, route, supplied)
                require(digest(record) == digest(baseline(name)), 'Complete valid answer changed: '+name)
                valid.append({'case': name, 'full_record_sha256': digest(record), 'equal': True})
                # Holding principal is a genuine premise in both source routes.
                bad = deepcopy(supplied); bad['holdings'][0]['principal'] = '1/0'
                rejected = h.consume(ps, route, bad, rounding)
                expected = 'UNSUPPORTED' if route == 'direct' else 'ValueError'
                require(rejected['boundary'] == expected, 'Wrong invalid-principal boundary')
                reason = (rejected['answer']['questions']['Q5']['unresolved'] if route == 'direct' else [rejected['error']])
                require(any('nonzero denominator' in r for r in reason), 'Unrelated refusal hides parser defect')
                if route == 'direct':
                    for q in ('Q1', 'Q2', 'Q3', 'Q4', 'Q6'):
                        require(digest(rejected['answer']['questions'][q]) == digest(record['answer']['questions'][q]),
                                'Invalid principal changed unrelated question')
                refusals.append({'case': name, 'changed_input': {'holdings[0].principal': '1/0'},
                    'boundary': expected, 'reason': reason, 'actual_record_sha256': digest(rejected)})
    for entitled in (True, False):
        v2 = h.original_v2(entitled)
        name = 'v2-'+('active' if entitled else 'excluded')+'-None.json'
        require(digest(v2) == digest(baseline(name)), 'Complete valid v2 result changed')
        valid.append({'case': name, 'full_record_sha256': digest(v2), 'equal': True})
    probe = read(ROOT/PREPARATION/'baseline.json')
    for row in probe['cases']:
        require(row['outcome'].get('exception') == 'ZeroDivisionError', 'Original reproduced failure missing')
        result = financial_profiles.assess({'instrument_id': probe['graph']['instrument_id']}, row['scenario'], probe['graph'])
        require(result['status'] == 'UNSUPPORTED' and any('nonzero denominator' in s for s in result['unresolved']),
                'Original exact-quantity crash not repaired')
        refusals.append({'probe': row['field'], 'entitled': row['entitled'], 'result': result})
    graph, assembly, packet = selected_v4_packet()
    for key in ('issue_principal', 'calculation_amount', 'fixed_coupon_amount', 'broken_coupon_amount'):
        bad = deepcopy(packet); bad['terms'][key]['value'] = '1/0'
        try: contract_terms.admit(graph, assembly, bad)
        except ValueError as exc:
            require('nonzero denominator' in str(exc), 'Wrong selected amount refusal')
            refusals.append({'selected_v4': key, 'boundary': 'ValueError', 'reason': str(exc)})
        else: raise ValueError('Invalid selected amount accepted')
    require(len(valid) == 14 and len(refusals) == 22, 'Incomplete financial comparison matrix')
    return {'valid': valid, 'refusals': refusals, 'full_valid_comparisons': len(valid),
            'actual_refusals': len(refusals), 'task_complete': False, 'whole_program_complete': False}


def storage(attempt):
    files = {ROOT/n for n in (*METHODS, PLAN)}
    files |= {p for d in (ROOT/REVIEW, ROOT/PREPARATION, ROOT/RECORD, attempt) for p in d.rglob('*') if p.is_file()}
    files |= set((ROOT/REL/'proposals').glob('exact-quantity-214*.json'))
    files.add(ROOT/REL/'revisions/0214.json')
    new = sum(p.stat().st_size for p in files if p.is_file())
    require(new+262144 < SELECTOR['new_bytes'], 'New exact-quantity storage/reserve ceiling')
    return {'new_bytes': new, 'new_ceiling': SELECTOR['new_bytes'], 'reserve': 262144}


def frozen():
    f = read(ROOT/REVIEW/'frozen.json')
    require(f['methods'] == {n: file_hash(ROOT/n) for n in METHODS}, 'Exact-quantity methods changed')
    require(f['inputs'] == {n: file_hash(ROOT/n) for n in f['inputs']}, 'Exact-quantity evidence changed')
    return f


def validate_submission(root, attempt, task):
    require(Path(root).resolve() == ROOT and task.get('exact_quantity') == SELECTOR, 'Wrong exact-quantity validation context')
    start = time.monotonic(); passed = False; old = signal.getsignal(signal.SIGALRM)
    def expired(_s, _f): raise ValueError('Exact-quantity acceptance180second ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(180)
    try:
        f = frozen(); attempt = Path(attempt); result = read(attempt/'result.json'); manifest = read(attempt/'run-manifest.json')
        require(set(METHODS)|set(f['inputs'])|{REVIEW+'/frozen.json'} <= set(task['inputs']), 'Unbound exact-quantity evidence')
        require(result['status'] == 'PASS' and result['task_complete'] is False and result['whole_program_complete'] is False
                and manifest['methods'] == f['methods'] and manifest['inputs'] == f['inputs'], 'Invalid exact-quantity result')
        checked_tests(ROOT/REVIEW/'tests.xml', f['tests'])
        actual = actual_checks()
        require(digest(load(attempt/'actual-checks.json.gz')) == digest(actual), 'Actual financial replay differs')
        storage(attempt)
        prep = read(ROOT/REVIEW/'preparation.json')['seconds']; elapsed = time.monotonic()-start
        require(prep <= 90 and manifest['wall_seconds'] <= 180 and elapsed <= 180
                and prep+manifest['wall_seconds']+elapsed <= 450, 'Exact-quantity incremental time ceiling')
        passed = True
        return True
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, old)
        print(json.dumps({'stage': 'exact-quantity-validation', 'seconds': time.monotonic()-start, 'passed': passed}), flush=True)


def prepare():
    import xml.etree.ElementTree as ET
    folder = ROOT/REVIEW; folder.mkdir(parents=True, exist_ok=True); start = time.monotonic()
    ledger = folder/'preparation.json'
    prep = read(ledger) if ledger.exists() else {'seconds': read(ROOT/PREPARATION/'baseline.json')['wall_seconds'], 'stages': []}
    index = len(prep['stages']); error = None
    try:
        # Assert the exact reviewed three-line change against retained pre-edit bytes.
        before = (ROOT/PREPARATION/'pre-edit-semantics.py').read_text()
        expected = before.replace('    return Fraction(value)\n', '    try:\n        return Fraction(value)\n    except ZeroDivisionError as exc:\n        raise ValueError("Exact quantity requires a nonzero denominator") from exc\n', 1)
        require((ROOT/'src/legalmath/prospectus/semantics.py').read_text() == expected, 'Parser repair exceeds reviewed scope')
        inputs = {PLAN, PREPARATION+'/baseline.json', PREPARATION+'/pre-edit-semantics.py',
            RETAINED+'/run_rounding.py', RETAINED+'/outputs.json', REVIEW+'/preparation.json'}
        h = helper()
        for route in ('direct', 'selected'):
            inputs |= {SOURCE+'/attempt-003/'+route+'-'+p+'.json.gz' for p in ('P1', 'P2', 'P3', 'P4', 'P5')}
            for form in ('global', 'definitive'): inputs.add(SOURCE+'/attempt-002/'+route+'-'+form+'-products.json.gz')
            for family, ps in [('danske', h.products_for(route)), ('global', h.shell_products(route+'-global')),
                               ('definitive', h.shell_products(route+'-definitive'))]:
                inputs |= {d['path'] for d in ps['P1']['payload']['request']['bundle']['documents']}
                prefix = route+'-original' if family == 'danske' else 'shell-'+route+'-'+family
                inputs |= {RETAINED+'/baseline/'+prefix+'-'+state+'.json.gz' for state in ('active', 'excluded')}
        inputs |= {SOURCE+'/attempt-001/source-P1.json.gz', SOURCE+'/attempt-001/definitive-scenario.json'}
        inputs |= {RETAINED+'/baseline/v2-'+state+'-None.json' for state in ('active', 'excluded')}
        xml, log = folder/f'tests-{index:02d}.xml', folder/f'tests-{index:02d}.log'
        with log.open('x') as stream:
            subprocess.run([sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml='+str(xml)], cwd=ROOT,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT/'src'), 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=stream, stderr=subprocess.STDOUT, timeout=max(1, 90-prep['seconds']-(time.monotonic()-start)), check=True)
        tests = sum(int(s.attrib.get('tests', 0)) for s in ET.parse(xml).getroot().iter('testsuite'))
        (folder/'tests.xml').write_bytes(xml.read_bytes())
        inputs |= {str(p.relative_to(ROOT)) for p in (xml, log, folder/'tests.xml')}
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)
        (folder/f'failure-{index:02d}.txt').write_text(traceback.format_exc(limit=8))
    elapsed = time.monotonic()-start; prep['seconds'] += elapsed
    prep['stages'].append({'seconds': elapsed, 'status': 'FAIL' if error else 'PASS', 'error': error})
    prep.update(command=[sys.executable, '-m', 'scripts.prospectus_exact_quantity', 'prepare'], cpu_gpu='CPU_ONLY; CUDA_VISIBLE_DEVICES=-1')
    write(ledger, prep)
    if error:
        print(json.dumps({'stage': 'exact-preparation', 'error': error, 'seconds': prep['seconds']})); return 1
    f = {'methods': {n: file_hash(ROOT/n) for n in METHODS}, 'inputs': {n: file_hash(ROOT/n) for n in sorted(inputs)},
         'tests': tests, 'selector': SELECTOR}
    write(folder/'frozen.json', f, exclusive=True)
    state = storage(ROOT/SOURCE/'attempt-004')
    require(state['new_bytes']+20*1024**2+262144 < SELECTOR['new_bytes'], 'Exact-quantity admission storage forecast')
    history_files = {p for name in (SOURCE, REL+'/attempts/entitlement')
        for p in (ROOT/name).rglob('*') if p.is_file()}
    history_manifests = {str(p.relative_to(ROOT)): file_hash(p) for p in history_files
        if p.name in {'run-manifest.json', 'started.json', 'outputs.json'}}
    write(folder/'preflight.json', {**state, 'authority_copy_forecast': 20*1024**2,
        'retained_finance_and_entitlement_bytes': sum(p.stat().st_size for p in history_files),
        'historical_manifest_hashes': history_manifests,
        'historical_costs': 'All001–003 and borrowed entitlement evidence retained; unknown old shell durations not imputed'}, exclusive=True)
    auth = Authority(ROOT); program, _, _ = auth.spec(); require(program['revision'] == 213, 'Expected213 baseline')
    proposal = deepcopy(program); proposal['revision'] = 214
    task = next(t for t in proposal['tasks'] if t['id'] == 'finance-conventions'); prior = task['dossier']
    task.update(dossier=PLAN, exact_quantity=SELECTOR, timeout_seconds=210,
        reason='Repair reproduced exact-quantity crash at shared parser; preserve all valid source-bound coupon outputs and refusal qualifications')
    task['inputs'] = sorted(set(task['inputs'])|inputs|set(METHODS)|{prior, REVIEW+'/frozen.json', REVIEW+'/preflight.json'})
    proposal['budgets'][task['budget_key']]['maximum_new_attempts'] = 4
    proposal['build_contract']['criteria'][task['id']] = [
        {'id': 'exact-quantity-refusal', 'basis': 'NAMED_CONDITIONAL_CHECK', 'validator': 'exact-quantity-refusal.v1',
         'description': 'Reproduced invalid rational inputs refused with valid complete financial answers preserved'},
        {'id': 'remaining-finance-coverage', 'basis': 'ORIGINAL_TASK_ACCEPTANCE', 'validator': None,
         'description': 'All original finance requirements remain; parser repair alone cannot complete finance'}]
    review = {'baseline': authority_digest(program), 'changes': ['Normalize only zero-denominator parsing failure',
        'Actual direct/selected/v2/v3 preservation and malformed-input refusals', 'Retain all historical tasks and costs'],
        'skeptical_audit': {'verdict': 'PASS_AFTER_REPRODUCED_FAILURE_AND_CALLER_AUDIT', 'plan': PLAN,
            'findings': ['Six original consumer crashes retained before editing', 'Every accepted value still returns Fraction(value)',
                         'No broad engine exception swallowing or zero substitution', 'Shared eligibility and selected-amount callers covered',
                         'Actual source-bound full answers are primary; finite unit tests are supporting evidence']},
        'evidence_contract': {'question': 'Do malformed exact quantities follow refusal interfaces without changing valid results?',
            'baseline': RETAINED+'/baseline', 'primary': 'Complete valid actual answers unchanged; specific malformed-input refusals',
            'promotion_veto': 'Changed valid values, unintended exception, manufactured zero or changed source premise',
            'continuation_veto': 'Corrupt baseline, method drift, declared incremental limits', 'explanatory': ['test totals', 'runtime'],
            'not_concluded': ['payment entitlement', 'source interpretation correctness', 'package superiority', 'whole build completion'],
            'artifacts': SOURCE+'/attempt-004'}, 'scope_unchanged': True, 'budget_unchanged': False,
        'delivery_scope_changed': True, 'delivery_authorization': proposal['build_contract']['authorization'],
        'original_obligations_preserved': True,
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 3, 'new_maximum': 4,
            'retained_attempts': [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']],
            'reason': 'Distinct reproduced numeric-input defect outside the previous rounding repair',
            'next_discriminating_check': 'Original crash scenarios now refuse; original valid whole consumers unchanged',
            'stop_condition': '90preparation/180candidate/180acceptance seconds;40MiB new including authority copies; no unchanged retry',
            'same_scope_authorization': 'User-directed general build and continued repairs without external opinions'}}
    write(ROOT/REL/'proposals/exact-quantity-214.json', proposal, exclusive=True)
    write(ROOT/REL/'proposals/exact-quantity-214-review.json', review, exclusive=True)
    print(json.dumps({'stage': 'prepared214', 'tests': tests, 'seconds': prep['seconds'], **state})); return 0


def run(attempt_name):
    auth = Authority(ROOT); attempt = auth.path(attempt_name); admission = read(attempt/'admission.json')
    program, tasks, _ = auth.spec(); task = tasks['finance-conventions']
    require(admission['binding'] == auth.binding(task) and admission['task_spec'] == task
            and admission['program_sha256'] == authority_digest(program) and task['exact_quantity'] == SELECTOR, 'Current exact-quantity admission required')
    event = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(event['kind'] == 'ADMIT' and event['attempt'] == attempt_name, 'New finance admission required')
    f = frozen(); start = time.monotonic(); status, error, result = 'PASS', None, {}
    manifest = {'command': [sys.executable, '-m', 'scripts.prospectus_exact_quantity', 'run', '--attempt', attempt_name],
        'git_commit': admission['git_commit'], 'environment': {'python': sys.version, 'executable': sys.executable},
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic refusal and equality checks',
        'plan': PLAN, 'result': attempt_name+'/RESULT.md', 'methods': f['methods'], 'inputs': f['inputs'],
        'data_version': f['inputs'], 'bounds': SELECTOR}
    write(attempt/'started.json', manifest, exclusive=True)
    def expired(_s, _f): raise TimeoutError('Exact-quantity candidate180second ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(180)
    try:
        storage(attempt); result = actual_checks(); frozen()
        compressed(attempt/'actual-checks.json.gz', result)
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__+': '+str(exc)
        (attempt/'failure-trace.txt').write_text(traceback.format_exc(limit=10))
    signal.alarm(0); manifest.update(wall_seconds=time.monotonic()-start, status=status, error=error)
    try: manifest['storage'] = storage(attempt)
    except Exception as exc: status, error = 'FAIL', str(exc); manifest.update(status=status, error=error)
    write(attempt/'run-manifest.json', manifest, exclusive=True)
    write(attempt/'result.json', {'task': task['id'], 'status': status, 'error': error,
        'full_valid_comparisons': result.get('full_valid_comparisons'), 'actual_refusals': result.get('actual_refusals'),
        'task_complete': False, 'whole_program_complete': False}, exclusive=True)
    (attempt/'RESULT.md').write_text('# Exact-quantity refusal repair\n\nStatus: '+status+'.\n\n'
        +'| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n'
        +('| Retain repair pending acceptance | Complete valid answers preserved; invalid quantities refused | No wrong refusal or changed valid result | Broader finance/source coverage | Record, refresh, continue | Original finance and build incomplete |\n'
          if status == 'PASS' else '| Reject candidate | Failed | See trace | Local replay or implementation defect | Reviewed changed repair | No package-direction rejection |\n')
        +'\nThe parser returns the same Fraction for every accepted input. Only a zero-denominator parsing exception becomes ValueError. No catch surrounds the whole calculation and no invalid value becomes zero.\n\n'
        +'Post-run red team: the finite consumer corpus does not establish every financial convention or actual entitlement. Missing source and event facts remain explicit. A changed valid value or wrong refusal would overturn this engineering result. Inputs, methods, exact commands, environment and timings are retained in the manifest.\n')
    write(attempt/'outputs.json', {p.name: file_hash(p) for p in attempt.iterdir() if p.is_file() and p.name != 'outputs.json'}, exclusive=True)
    print(json.dumps({'stage': 'exact-candidate', 'status': status, 'error': error, 'seconds': manifest['wall_seconds']})); return int(status != 'PASS')


def record(attempt_name):
    folder = ROOT/RECORD; folder.mkdir(parents=True, exist_ok=True); start = time.monotonic(); error = None; process = None
    try:
        with (folder/'command.log').open('x') as log:
            process = subprocess.run([sys.executable, '-m', 'scripts.prospectus_control', 'record', '--attempt', attempt_name],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=210, check=False)
    except Exception as exc: error = type(exc).__name__+': '+str(exc)
    event = next(e for e in reversed(Authority(ROOT).events()) if e.get('attempt') == attempt_name)
    result = {'wall_seconds': time.monotonic()-start, 'error': error, 'exit_code': process.returncode if process else None,
        'kind': event['kind'], 'reason': event.get('reason'), 'build_acceptances': event.get('build_acceptances', []),
        'event_sha256': event['sha256'], 'command_log_sha256': file_hash(folder/'command.log')}
    write(folder/'receipt.json', result, exclusive=True); print(json.dumps(result))
    return int('exact-quantity-refusal' not in result['build_acceptances'])


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['prepare', 'run', 'record']); p.add_argument('--attempt'); a = p.parse_args()
    if a.action == 'prepare': return prepare()
    if not a.attempt: p.error('--attempt required')
    return run(a.attempt) if a.action == 'run' else record(a.attempt)


if __name__ == '__main__': raise SystemExit(main())
