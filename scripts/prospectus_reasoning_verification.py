"""Bounded admitted finite-reasoning package and substantive evidence validator."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash
from legalmath.prospectus import basf_default_f as default
from legalmath.prospectus.default_f_certificates import context, certificate, verify_consumer, READINGS, QUESTIONS
from legalmath.prospectus.reasoning_certificates import check_result, identity
from legalmath.prospectus.successor.predicates import dispatch
from legalmath.prospectus.successor.contracts import digest

PRIOR = REL + '/attempts/basf-meanings/attempt-013'
BASELINE = REL + '/attempts/reasoning-corpus/attempt-003'
TESTS = ('tests/prospectus/test_reasoning_certificates.py',
         'tests/prospectus/test_build_contract.py', 'tests/prospectus/test_execution_authority.py')
METHODS = ('scripts/prospectus_reasoning_verification.py',
           'src/legalmath/prospectus/reasoning_certificates.py',
           'src/legalmath/prospectus/default_f_certificates.py',
           'src/legalmath/prospectus/basf_default_f.py',
           'src/legalmath/prospectus/successor/predicates.py',
           'src/legalmath/prospectus/semantics.py')
CONTROL_NAMES = ('formula', 'facts', 'status', 'decision', 'worlds', 'witness',
                 'source', 'whole-answer', 'candidate', 'limits', 'coverage',
                 'promoted-meaning', 'comparison', 'certificate-bool')


def load(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def save_compressed(path, value):
    with path.open('xb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as zipped:
            zipped.write((json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode())


def finite_checks():
    formulas = [True, False, 'a', {'not': 'a'}, {'all': ['a', 'b', 'c']},
                {'any': ['a', 'b', 'c']}, {'any': ['a', {'not': 'a'}]},
                {'all': ['a', {'not': 'a'}]},
                {'any': [{'all': ['a', {'not': 'b'}]}, 'c']},
                {'not': {'all': ['a', {'any': ['b', 'c']}]}}]
    counts, checked = Counter(), sha256()
    for expression in formulas:
        for values in product((False, True, None, 'conflict'), repeat=3):
            facts = dict(zip(('a', 'b', 'c'), values))
            result = dispatch(expression, facts)
            expected = check_result(expression, facts, result)
            absent = {k: v for k, v in facts.items() if v is not None}
            if dispatch(expression, absent) != result:
                raise ValueError('Explicit null and missing unknown differ')
            counts[expected['status']] += 1
            checked.update(identity([expression, facts, result, expected]).encode())
    boundaries = []
    for count in (12, 13):
        expression = {'all': ['f' + str(i) for i in range(count)]}
        result = dispatch(expression, {})
        boundaries.append(check_result(expression, {}, result))
    # A closed-world mutant must fail the open-world specification.
    try:
        check_result('a', {}, dispatch('a', {'a': False}))
    except ValueError:
        mutant_rejected = True
    else:
        raise ValueError('Incorrect closed-world mutant accepted')
    return {'cases': sum(counts.values()), 'statuses': dict(counts),
            'case_identity': checked.hexdigest(), 'boundary_results': boundaries,
            'closed_world_mutant_rejected': mutant_rejected,
            'legal_interpretation_proved': False}


def controls(certified, profile, bound, *, verifier=verify_consumer, test_acceptor=True):
    results = []
    for name in CONTROL_NAMES:
        altered, p = deepcopy(certified), deepcopy(profile)
        review = altered['default_f_review']
        row = review['scenarios'][0]
        result = row['readings'][READINGS[0]][QUESTIONS[0]]
        if name == 'formula':
            p['candidates'][0]['expressions'][QUESTIONS[0]] = True
        elif name == 'facts':
            row['facts']['exercise.cessation'] = True
        elif name in {'status', 'decision'}:
            result[name] = 'YES' if name == 'status' else 'TRUE'
        elif name == 'worlds':
            result['worlds'] += 1
        elif name == 'witness':
            result['witnesses']['true']['exercise.cessation'] = False
        elif name == 'source':
            p['sources'][0]['sha256'] = '0' * 64
        elif name == 'whole-answer':
            altered['tampered-unrelated-answer'] = True
        elif name == 'candidate':
            review['candidates'].pop()
        elif name == 'limits':
            result['limits']['max_facts'] = 13
        elif name == 'coverage':
            altered['reasoning_certificate']['certificates'].pop()
        elif name == 'promoted-meaning':
            review['source_meaning_promoted'] = True
        elif name == 'comparison':
            row['comparison'][QUESTIONS[0]] = 'ALL_ENUMERATED_YES'
        elif name == 'certificate-bool':
            altered['reasoning_certificate']['certificates'][0]['certificate']['checked']['true_worlds'] = True
        try:
            verifier(altered, p, expected_context=bound)
        except ValueError:
            results.append({'mutation': name, 'rejected': True})
        else:
            raise ValueError('Tampered consumer accepted: ' + name)
        if name in {'status', 'decision', 'worlds', 'witness', 'comparison'}:
            original = {k: v for k, v in altered.items() if k != 'reasoning_certificate'}
            rebased = {**bound, 'complete_consumer_sha256': identity(original)}
            try:
                certificate(original, p, expected_context=rebased)
            except ValueError:
                results[-1]['independent_semantic_rejection_after_digest_rebase'] = True
            else:
                raise ValueError('Semantic defect only rejected by digest mismatch: ' + name)
    if test_acceptor:
        try:
            controls(certified, profile, bound, verifier=lambda *_a, **_kw: True, test_acceptor=False)
        except ValueError as exc:
            if 'Tampered consumer accepted' not in str(exc):
                raise
        else:
            raise ValueError('Permissive certificate acceptor escaped rejection suite')
    return {'controls': results, 'permissive_acceptor_detected_by_rejection_contract': test_acceptor}


def inputs(root):
    profile = read(root / BASELINE / 'candidate-profile.json')
    baseline = load(root / BASELINE / 'candidate-consumer.json.gz')
    products = load(root / PRIOR / 'products.json.gz')
    preceding = read(root / PRIOR / 'prior-profiles.json')
    return profile, baseline, products, preceding


def run(root, attempt):
    profile, baseline, products, preceding = inputs(root)
    actual = default.consume_verified(products, preceding, profile, root,
        expected_prior_profiles_sha256=digest(preceding), expected_profile_sha256=digest(profile))
    original = {k: v for k, v in actual.items() if k != 'reasoning_certificate'}
    if original != baseline:
        raise ValueError('Complete actual consumer differs from retained baseline')
    bound = context(baseline, profile, products_sha256=digest(products), prior_profiles_sha256=digest(preceding))
    verification = verify_consumer(actual, profile, expected_context=bound)
    if verification['checked_answers'] != 288:
        raise ValueError('Existing24 by3 by4 conditional result coverage changed')
    finite, adverse = finite_checks(), controls(actual, profile, bound)
    save_compressed(attempt / 'certified-consumer.json.gz', actual)
    write(attempt / 'expected-context.json', bound, exclusive=True)
    write(attempt / 'finite-checks.json', finite, exclusive=True)
    write(attempt / 'controls.json', adverse, exclusive=True)
    write(attempt / 'verification.json', verification, exclusive=True)
    return {'actual_answers': verification['checked_answers'], 'new_finite_cases': finite['cases'],
            'mutations_rejected': len(adverse['controls']), 'complete_baseline_preserved': True}


def validate_submission(root, attempt, task):
    from legalmath.prospectus.execution_acceptance import checked_tests
    root, attempt = Path(root), Path(attempt)
    checked_tests(attempt / 'tests.xml', 35)
    profile, baseline, products, preceding = inputs(root)
    certified = load(attempt / 'certified-consumer.json.gz')
    if {k: v for k, v in certified.items() if k != 'reasoning_certificate'} != baseline:
        raise ValueError('Retained complete answer differs from original actual consumer')
    bound = context(baseline, profile, products_sha256=digest(products), prior_profiles_sha256=digest(preceding))
    if read(attempt / 'expected-context.json') != bound:
        raise ValueError('Expected original source context changed')
    actual = verify_consumer(certified, profile, expected_context=bound)
    if (read(attempt / 'verification.json') != actual or actual['checked_answers'] != 288
            or read(attempt / 'finite-checks.json') != finite_checks()
            or read(attempt / 'controls.json') != controls(certified, profile, bound)):
        raise ValueError('Retained substantive reasoning evidence disagrees with recomputation')
    result = read(attempt / 'result.json')
    manifest = read(attempt / 'run-manifest.json')
    methods = {name: file_hash(root / name) for name in METHODS}
    if (result.get('scope') != 'FINITE_ENGINEERING_ONLY' or result.get('whole_program_complete') is not False
            or manifest['methods'] != methods or not set(METHODS) <= set(task['inputs'])
            or manifest['status'] != 'PASS' or manifest['wall_seconds'] > 180
            or manifest['cpu_gpu'] != 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; no GPU framework used'):
        raise ValueError('Finite result scope, bound methods or resource record invalid')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    authority = Authority(ROOT)
    attempt = authority.path(args.attempt)
    admission = read(attempt / 'admission.json')
    if admission['task'] != 'reasoning-corpus' or admission['binding'] != authority.binding(admission['task_spec']):
        raise ValueError('Current frozen reasoning admission required')
    start = time.monotonic()
    def expired(_signum, _frame):
        raise TimeoutError('Cumulative180-second command ceiling')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(180)
    manifest = {'command': [sys.executable, '-m', 'scripts.prospectus_reasoning_verification',
                            '--attempt', args.attempt], 'git_commit': admission['git_commit'],
                'environment': {'python': sys.version, 'executable': sys.executable, 'PYTHONPATH': str(ROOT / 'src')},
                'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; no GPU framework used',
                'data_version': {'profile': file_hash(ROOT / BASELINE / 'candidate-profile.json'),
                                 'products': file_hash(ROOT / PRIOR / 'products.json.gz')},
                'random_seeds': 'N/A; deterministic finite enumeration',
                'methods': {name: file_hash(ROOT / name) for name in METHODS},
                'plan': 'docs/plans/prospectus-general-build-2026-10-17.md',
                'result': args.attempt + '/RESULT.md', 'outputs': args.attempt,
                'historical_cost': 'Prior admissions retained; unrecorded prior elapsed time remains unknown'}
    write(attempt / 'started.json', manifest, exclusive=True)
    status, error, summary = 'PASS', None, {}
    try:
        env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'CUDA_VISIBLE_DEVICES': '-1'}
        command = [sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml=' + str(attempt / 'tests.xml')]
        manifest['test_command'] = command
        with (attempt / 'tests.log').open('x') as log:
            subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=60, check=True)
        print(json.dumps({'stage': 'focused-tests', 'status': 'PASS'}), flush=True)
        summary = run(ROOT, attempt)
        print(json.dumps({'stage': 'actual-consumer-and-controls', 'status': 'PASS', **summary}), flush=True)
        if time.monotonic() - start > 180:
            raise ValueError('Cumulative package wall-time ceiling exceeded')
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
    signal.alarm(0)
    manifest.update(status=status, wall_seconds=time.monotonic() - start, error=error,
                    retained_bytes_before_seal=sum(p.stat().st_size for p in attempt.rglob('*') if p.is_file()))
    if manifest['retained_bytes_before_seal'] > 24 * 1024 * 1024:
        status = manifest['status'] = 'FAIL'
        error = manifest['error'] = 'Attempt artifacts exceed24MiB; remaining8MiB reserved for authority/docs'
    write(attempt / 'run-manifest.json', manifest, exclusive=True)
    write(attempt / 'result.json', {'task': 'reasoning-corpus', 'status': status,
        'scope': 'FINITE_ENGINEERING_ONLY', 'whole_program_complete': False,
        'summary': summary, 'error': error}, exclusive=True)
    (attempt / 'RESULT.md').write_text(
        '# Finite reasoning package\n\nStatus: ' + status + '.\n\n'
        + (json.dumps(summary, sort_keys=True) if status == 'PASS' else str(error)) + '\n\n'
        + 'The checked target is conditional Boolean consequence. Source meaning, candidate-set '
        'exhaustiveness, actual default and whole-build completion are not proved.\n\n'
        + '| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n'
        + '| --- | --- | --- | --- | --- | --- |\n'
        + ('| Accept finite optional verifier | Independent finite and actual consumer checks pass | '
           'All declared mutations rejected | Source/formula completeness | Continue source-to-answer phase | '
           'No legal-meaning promotion |\n' if status == 'PASS' else
           '| Reject candidate package | Failed | See retained error | Implementation or evidence defect | '
           'Review one changed repair; do not retry unchanged | No package/direction rejection |\n')
        + '\nPost-run red team: a legally wrong or incomplete supplied formula can pass a correct '
        'Boolean checker. The nonexhaustive alternative set and unresolved original source '
        'question remain. A counterexample to the checked truth table would overturn the '
        'finite inference result. Source interpretation remains the weakest evidence layer.\n')
    write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p)
        for p in sorted(attempt.rglob('*')) if p.is_file() and p.name != 'outputs.json'}, exclusive=True)
    print(json.dumps({'status': status, 'wall_seconds': manifest['wall_seconds'], 'error': error}), flush=True)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
