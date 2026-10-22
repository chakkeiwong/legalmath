"""Bounded reasoning003: distinct causal hypotheses and source-first review."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gzip
from itertools import product
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback

START = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus import basf_default_f as default
from legalmath.prospectus.execution_authority import file_hash, read
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
GROUP = BASE / 'attempts/reasoning-corpus'
HERE = GROUP / 'attempt-003'
PRIOR = BASE / 'attempts/basf-meanings/attempt-013'
CURRENT = BASE / 'attempts/basf-meanings/attempt-019'
SUPPORT = BASE / 'reviews/default-causal-110'
PLAN = 'docs/plans/prospectus-default-causal-adjudication-2026-10-16.md'
STAGES = ('prepare', 'baseline', 'candidate', 'verify')
READINGS = ('both_conducts', 'either_qualified_conduct', 'cessation_or_qualified_disposal')
QUESTIONS = ('event_at_exercise', 'event_at_receipt', 'modeled_f_exercise', 'bc_quorum_condition_at_receipt')
FACTS = ('cessation', 'disposal', 'value_cessation', 'risk_cessation',
         'value_disposal', 'risk_disposal', 'value_joint', 'risk_joint')
# Fixed before any consumer run. Rows are exercise event, receipt event,
# modeled direct exercise, and the separate receipt-time quorum condition.
YNY, NYY, NNN = ['YES', 'NO', 'YES'], ['NO', 'YES', 'YES'], ['NO'] * 3
UNU, CNY = ['UNKNOWN', 'NO', 'UNKNOWN'], ['CONFLICT', 'NO', 'YES']
EXPECTED = {
    'joint-only-consequences': [YNY, YNY, YNY, YNY],
    'cessation-chain-with-both-conducts': [NYY, NYY, NYY, NYY],
    'joint-risk-conflict': [CNY, CNY, CNY, CNY],
    'joint-only-cured': [YNY, YNY, NNN, YNY],
    'joint-only-notice-unknown': [YNY, YNY, UNU, YNY],
    'joint-only-at-receipt': [NNN, YNY, NNN, YNY],
    'joint-only-at-exercise': [YNY, NNN, YNY, NNN],
    'joint-only-receipt-eligibility-unknown': [YNY, YNY, YNY, UNU],
}


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, compresslevel=1, mtime=0) if path.suffix == '.gz' else data)


def size(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def elapsed():
    return sum(read(p)['wall_seconds'] for p in (HERE / 'invocations').glob('*/result.json'))


def package():
    base = ROOT / 'src/legalmath'
    return {str(p.relative_to(base)): file_hash(p) for p in base.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def bindings():
    assert not (HERE / 'outputs.json').exists(), 'Sealed evidence is immutable'
    ad = read(HERE / 'admission.json')
    assert ad['task'] == 'reasoning-corpus' and ad['revision'] == 110
    assert all(file_hash(ROOT / name) == h for name, h in ad['binding'].items())
    assert package() == read(CURRENT / 'source-package.json')
    for name in ('protected-inputs.json', 'methods.json'):
        if (HERE / name).exists():
            assert all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items())
    assert size(HERE) + size(SUPPORT) < 20 * 1024 * 1024
    return ad


def cases():
    empty = dict.fromkeys(FACTS, False)
    joint = {**empty, 'cessation': True, 'disposal': True, 'value_joint': True, 'risk_joint': True}
    separate = {**empty, 'cessation': True, 'disposal': True,
                'value_cessation': True, 'risk_cessation': True}
    def make(name, exercise, receipt=None, **extra):
        receipt = exercise if receipt is None else receipt
        return {'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': {
            **{'exercise.' + k: v for k, v in exercise.items()},
            **{'receipt.' + k: v for k, v in receipt.items()},
            'notice': True, 'cured_before_exercise': False, 'quorum_at_receipt': False,
            'other_eligible_at_receipt': False, 'f_other_eligibility_at_receipt': True, **extra}}
    return [make('joint-only-consequences', joint),
            make('cessation-chain-with-both-conducts', separate),
            make('joint-risk-conflict', {**joint, 'risk_joint': 'conflict'}),
            make('joint-only-cured', joint, cured_before_exercise=True),
            make('joint-only-notice-unknown', joint, notice=None),
            make('joint-only-at-receipt', empty, joint),
            make('joint-only-at-exercise', joint, empty),
            make('joint-only-receipt-eligibility-unknown', joint, f_other_eligibility_at_receipt=None)]


def required(reading, question):
    names = {
        'both_conducts': ('cessation', 'disposal', 'value_joint', 'risk_joint'),
        'either_qualified_conduct': ('cessation', 'disposal', 'value_cessation', 'risk_cessation', 'value_disposal', 'risk_disposal'),
        'cessation_or_qualified_disposal': ('cessation', 'disposal', 'value_disposal', 'risk_disposal'),
    }[reading]
    receipt = question in ('event_at_receipt', 'bc_quorum_condition_at_receipt')
    names = {(('receipt.' if receipt else 'exercise.') + n) for n in names}
    if question == 'modeled_f_exercise': names |= {'notice', 'cured_before_exercise'}
    if question == 'bc_quorum_condition_at_receipt':
        names |= {'quorum_at_receipt', 'other_eligible_at_receipt', 'f_other_eligibility_at_receipt'}
    return sorted(names)


def direct(reading, question, world):
    prefix = 'receipt.' if question in ('event_at_receipt', 'bc_quorum_condition_at_receipt') else 'exercise.'
    c, d = world[prefix + 'cessation'], world[prefix + 'disposal']
    if reading == 'both_conducts':
        event = c and d and world[prefix + 'value_joint'] and world[prefix + 'risk_joint']
    elif reading == 'either_qualified_conduct':
        event = ((c and world[prefix + 'value_cessation'] and world[prefix + 'risk_cessation'])
                 or (d and world[prefix + 'value_disposal'] and world[prefix + 'risk_disposal']))
    else:
        assert reading == 'cessation_or_qualified_disposal'
        event = c or (d and world[prefix + 'value_disposal'] and world[prefix + 'risk_disposal'])
    if question == 'modeled_f_exercise': return event and world['notice'] and not world['cured_before_exercise']
    if question == 'bc_quorum_condition_at_receipt':
        return world['quorum_at_receipt'] or world['other_eligible_at_receipt'] or (event and world['f_other_eligibility_at_receipt'])
    return event


def oracle(reading, question, facts):
    names = required(reading, question)
    if any(facts.get(n) == 'conflict' for n in names): return 'CONFLICT'
    missing = [n for n in names if facts.get(n) is None]
    values = set()
    for bits in product((False, True), repeat=len(missing)):
        world = {n: facts[n] for n in names if n not in missing}
        world.update(zip(missing, bits))
        values.add(direct(reading, question, world))
    return 'UNKNOWN' if len(values) == 2 else 'YES' if True in values else 'NO'


def prepare():
    protected = {}
    for folder in (GROUP / 'attempt-001', GROUP / 'attempt-002', PRIOR, CURRENT):
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
        protected.update({str((folder / p).relative_to(ROOT)): h for p, h in read(folder / 'outputs.json').items()})
    sources = read(PRIOR / 'original-sources.json')
    for source in sources:
        for row in (source, *source['images']): protected[row['path']] = row['sha256']
    assert all(file_hash(ROOT / p) == h for p, h in protected.items())
    save('protected-inputs.json', protected)
    methods = {str(Path(__file__).relative_to(ROOT)): file_hash(Path(__file__)), PLAN: file_hash(ROOT / PLAN)}
    methods.update({'src/legalmath/' + p: h for p, h in package().items()})
    save('methods.json', methods)
    shutil.copyfile(__file__, HERE / 'frozen-runner.py')
    save('original-sources.json', sources)
    save('source-groups.json', read(PRIOR / 'profile.json')['groups'])
    examples = cases()
    for example in examples:
        f = example['facts']
        for prefix in ('exercise.', 'receipt.'):
            for kind, conduct in (('cessation', ('cessation',)), ('disposal', ('disposal',)), ('joint', ('cessation', 'disposal'))):
                if f[prefix + 'risk_' + kind] is True: assert f[prefix + 'value_' + kind] is True
                if f[prefix + 'value_' + kind] is True: assert all(f[prefix + k] is True for k in conduct)
        values = [[oracle(r, q, f) for r in READINGS] for q in QUESTIONS]
        assert values == EXPECTED[example['id']]
    save('scenarios.json', examples)
    save('predeclared-expectations.json', EXPECTED)
    profile = deepcopy(read(PRIOR / 'profile.json'))
    assert len(profile['scenarios']) == 16
    assert not {x['id'] for x in profile['scenarios']} & set(EXPECTED)
    profile['scenarios'].extend(examples)
    save('candidate-profile.json', profile)
    for name in ('SOURCE-FIRST-REVIEW.md', 'COMPARISON-ANNEX.md', 'RESPONSE-TEMPLATE.json'):
        shutil.copyfile(SUPPORT / name, HERE / name)
    save('review-packet.json', {'status': 'PREPARED_ONLY', 'reviewer': None, 'response': None,
        'source_first': 'SOURCE-FIRST-REVIEW.md', 'exposed_annex': 'COMPARISON-ANNEX.md',
        'source_groups': 'source-groups.json', 'original_sources': 'original-sources.json',
        'source_exposure': 'BASF documents already exposed in development; no unexposed evaluation cohort created',
        'independent_legal_acceptance': False, 'external_message_sent': False})
    save('history-accounting.json', {'retained_reasoning_attempts': ['attempt-001', 'attempt-002'],
        'prior_logical_bytes': sum(size(GROUP / n) for n in ('attempt-001', 'attempt-002')),
        'historical_wall_seconds': None,
        'reason': 'Prior001/002 failed commands have explicitly unavailable timers; no invented cumulative total',
        'new_seconds_limit': 180, 'new_logical_bytes_limit': 20 * 1024 * 1024, 'child_start_limit': 0})
    return {'new_scenarios': 8, 'existing_scenarios': 16, 'frozen_expectations': 96, 'source_images': 5}


def consume(profile):
    products = load(PRIOR / 'products.json.gz')
    old = read(PRIOR / 'prior-profiles.json')
    return default.consume(products, old, profile, ROOT,
        expected_prior_profiles_sha256=digest(old), expected_profile_sha256=digest(profile))


def baseline():
    result = consume(read(PRIOR / 'profile.json'))
    save('baseline-consumer.json.gz', result)
    assert result == load(PRIOR / 'default-consumer.json.gz')
    return {'complete_historical013_consumer_equal': True}


def candidate():
    result = consume(read(HERE / 'candidate-profile.json'))
    save('candidate-consumer.json.gz', result)
    old = load(HERE / 'baseline-consumer.json.gz')
    assert {k: v for k, v in result.items() if k != 'default_f_review'} == {k: v for k, v in old.items() if k != 'default_f_review'}
    before, after = old['default_f_review'], result['default_f_review']
    assert {k: v for k, v in before.items() if k not in ('profile_sha256', 'scenarios')} == {
        k: v for k, v in after.items() if k not in ('profile_sha256', 'scenarios')}
    assert after['scenarios'][:16] == before['scenarios']
    assert len(after['scenarios']) == 24
    actual, witnesses = {}, 0
    for example, row in zip(cases(), after['scenarios'][16:]):
        assert (row['id'], row['kind'], row['facts']) == (example['id'], example['kind'], example['facts'])
        assert row['selected_reading'] is None and row['actual_event_established'] is False
        values = [[row['readings'][r][q]['status'] for r in READINGS] for q in QUESTIONS]
        assert values == EXPECTED[row['id']]
        for reading in READINGS:
            for question in QUESTIONS:
                decision = row['readings'][reading][question]
                assert decision['status'] == oracle(reading, question, row['facts'])
                expected_truths = {'YES': {'true'}, 'NO': {'false'}, 'UNKNOWN': {'true', 'false'}, 'CONFLICT': set()}[decision['status']]
                assert set(decision['witnesses']) == expected_truths
                for truth, world in decision['witnesses'].items():
                    assert set(world) == set(required(reading, question))
                    assert all(type(value) is bool for value in world.values())
                    assert all(world[n] == row['facts'][n] for n in world if type(row['facts'].get(n)) is bool)
                    assert direct(reading, question, world) is (truth == 'true')
                    witnesses += 1
                statuses = {row['readings'][r][question]['status'] for r in READINGS}
                aggregate = ('CONFLICT_IN_ENUMERATED_READINGS' if 'CONFLICT' in statuses else
                    'ALL_ENUMERATED_YES' if statuses == {'YES'} else
                    'ALL_ENUMERATED_NO' if statuses == {'NO'} else
                    'UNRESOLVED_WITHIN_ENUMERATED_READINGS' if 'UNKNOWN' in statuses else
                    'DIFFERENT_ENUMERATED_DECISIONS')
                assert row['comparison'][question] == aggregate
        actual[row['id']] = dict(zip(QUESTIONS, values))
    save('actual-comparison.json', {'status': 'PASS', 'new_cases': actual, 'candidate_question_checks': 96,
        'witnesses_checked': witnesses, 'prior_complete_fields_and16_scenarios_equal': True,
        'ordinary_answer_unchanged': True, 'old_shared_cause_containment_not_transferable': True,
        'independent_legal_acceptance': False})
    return {'new_cases': len(actual), 'candidate_question_checks': 96, 'witnesses_checked': witnesses}


def verify():
    result = read(HERE / 'actual-comparison.json')
    response = read(HERE / 'RESPONSE-TEMPLATE.json')
    assert response['reviewer'] is None and response['independent_first_reading'] is None
    assert all(v is None for v in response['answers'].values())
    assert response['controlling_construction'] is None and response['independent_legal_acceptance'] is False
    assert read(HERE / 'review-packet.json')['external_message_sent'] is False
    assert result['new_cases']['joint-only-consequences']['event_at_exercise'] == YNY
    assert result['new_cases']['cessation-chain-with-both-conducts']['event_at_exercise'] == NYY
    save('verified-result.json', {'status': 'PASS', 'task_complete': False, 'production_changes': 0,
        'current_package_files': len(package()), 'source_first_packet_prepared': True,
        'independent_reading_received': False, 'counterexamples_consumed': True,
        'new_installed_evidence': False, 'third_party_defect_established': False})
    return read(HERE / 'verified-result.json')


def seal():
    error = None
    try: bindings()
    except Exception as exc: error = repr(exc)
    results = {p.parent.name: read(p) for p in (HERE / 'invocations').glob('*/result.json')}
    seconds = elapsed() + time.monotonic() - START
    limits = seconds < 180 and size(HERE) + size(SUPPORT) < 20 * 1024 * 1024
    passed = not error and limits and set(results) == set(STAGES) and all(r['status'] == 'PASS' for r in results.values())
    assert (HERE / 'RESULT.md').exists() and (HERE / 'NEXT-WORK.md').exists()
    save('run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'], 'plan': PLAN,
        'result': 'RESULT.md', 'environment': sys.executable, 'cpu_gpu': 'CPU only; GPU intentionally hidden before imports',
        'random_seeds': 'N/A deterministic', 'new_cumulative_seconds': seconds,
        'new_evidence_support_bytes_before_seal': size(HERE) + size(SUPPORT),
        'data_version': 'protected-inputs.json and original-sources.json', 'methods': 'methods.json',
        'history': read(HERE / 'history-accounting.json') if (HERE / 'history-accounting.json').exists() else None,
        'stages': results, 'binding_error': error, 'limits_passed': limits, 'child_starts': 0})
    save('result.json', {'task': 'reasoning-corpus', 'status': 'PASS' if passed else 'FAIL', 'task_complete': False,
        'result_note': 'RESULT.md', 'binding_error': error, 'limits_passed': limits,
        'independent_legal_acceptance': False, 'further_repairs_allowed': 0})
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in HERE.rglob('*')
               if p.is_file() and p.name not in ('outputs.json', 'execution.lock') and '__pycache__' not in p.parts}
    save('outputs.json', outputs)
    print(json.dumps({'status': 'PASS' if passed else 'FAIL', 'files': len(outputs), 'new_seconds': seconds}), flush=True)


def guard():
    def refuse(*args, **kwargs): raise RuntimeError('No child/native/network operation authorized in reasoning003')
    subprocess.Popen = refuse
    os.system = refuse
    if hasattr(os, 'posix_spawn'): os.posix_spawn = refuse
    if hasattr(os, 'posix_spawnp'): os.posix_spawnp = refuse
    socket.create_connection = refuse
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse


def main():
    stage = sys.argv[1]
    assert stage in (*STAGES, 'seal')
    if stage == 'seal': return seal()
    assert not (HERE / 'outputs.json').exists()
    assert len(list((HERE / 'invocations').glob('*/started.json'))) == len(list((HERE / 'invocations').glob('*/result.json')))
    for previous in STAGES[:STAGES.index(stage)]: assert read(HERE / 'invocations' / previous / 'result.json')['status'] == 'PASS'
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    command = ['timeout', '120', '.venv/bin/python', '-m', 'scripts.prospectus_default_causal_review', stage]
    save('invocations/' + stage + '/started.json', {'command': command, 'started_at': datetime.now(timezone.utc).isoformat(),
        'plan': PLAN, 'environment': sys.executable, 'cpu_gpu': 'CPU only; GPU intentionally hidden', 'random_seeds': 'N/A deterministic'})
    def expire(signum, frame): raise TimeoutError('Reviewed reasoning003 stage/cumulative bound; no retry')
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, max(0.1, min(118 - (time.monotonic() - START), 180 - elapsed())))
    outcome = {'status': 'PASS'}
    try:
        bindings()
        guard()
        outcome['details'] = globals()[stage]()
        bindings()
        assert elapsed() + time.monotonic() - START < 180
    except BaseException as exc:
        outcome.update(status='FAIL', error=repr(exc))
        (folder / 'traceback.txt').write_text(traceback.format_exc())
    finally: signal.setitimer(signal.ITIMER_REAL, 0)
    outcome.update(command=command, wall_seconds=time.monotonic() - START,
        git_commit=read(HERE / 'admission.json')['git_commit'], max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps({'stage': stage, 'status': outcome['status'], 'seconds': outcome['wall_seconds'], 'error': outcome.get('error')}), flush=True)
    if outcome['status'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
