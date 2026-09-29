"""Bounded offline D3 reproduction from the archived D2 verification method."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PLAN = ROOT/'docs/plans/gregorian-profile-audit.md'
SNAPSHOT = ROOT/'artifacts/executable-reference-assurance/2026-09-29/verify/attempt-01/snapshot.json'


def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return str(Path(p).resolve().relative_to(ROOT))
def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n'); tmp.replace(p)


def audit(work, frozen):
    sys.path[:0] = [str(frozen/'src'), str(frozen), str(frozen/'scripts')]
    import run_eligibility_gap_closure as prior
    from legalmath.qualification import assurance, gregorian, proof
    from legalmath.canonical import digest
    result = prior.G4(work/'reproduction')
    if result['codec']['valid_dates'] != 3652059 or result['native']['executed_target_cases'] != 98:
        raise RuntimeError('Reproduction denominator changed')
    before = read(frozen/'docs/implementation/eligibility-gap-closure/G4/attempt-001/result.json')
    for name in ('calendar_theorem', 'codec', 'retained_readings'):
        if result[name] != before[name]: raise RuntimeError('Changed original G4 evidence: '+name)
    model, known = prior.date_fixture(); cases = []
    for status in ('unknown', 'conflict'):
        for fact_name in ('left', 'right'):
            case = deepcopy(known[0]); case['id'] = status+'.'+fact_name
            evidence_ids = ['calendar-conflict.a', 'calendar-conflict.b']
            case['snapshot']['facts'][fact_name] = {'type': 'date', 'status': status, **(
                {'reason': 'MISSING'} if status == 'unknown' else {'evidence_ids': evidence_ids})}
            if status == 'unknown': case['snapshot']['evidence'].pop('/'+fact_name)
            else: case['snapshot']['evidence']['/'+fact_name] = evidence_ids
            cases.append(case)
    native = assurance.run(model, cases, work/'abstention', prior.JDK, toolchain=prior.TOOLCHAIN)
    outcomes = []
    for target, result_target in native['targets'].items():
        if result_target['status'] != 'CHECKED' or len(result_target['cases']) != len(cases):
            raise RuntimeError('Incomplete factual-state target: '+str(result_target))
        for case, row in zip(cases, result_target['cases']):
            reason = 'INCOMPLETE_INPUTS' if case['id'].startswith('unknown') else 'CONFLICTING_INPUTS'
            # complete.v1 rejects incomplete/conflicting snapshots before any
            # native program runs, including for the left-only cutoff output.
            # This is one shared boundary, not independent target abstention.
            for name in ('after', 'on_or_after', 'same', 'cutoff'):
                value = row['result']['results'][name]
                if value['status'] != 'ABSTAIN' or value['reason'] != reason or value['execution'] is not None:
                    raise RuntimeError('Non-abstaining date comparison: '+str(row))
            outcomes.append({'target': target, 'case': case['id'], 'boundary_status': 'ABSTAIN', 'reason': reason,
                'actual': row['result']['results'], 'independent_formal_status': row['checks']['independent_formal_evaluation']})
    if native['summary']['independent_formal_matches'] != 0:
        raise RuntimeError('Partial facts falsely promoted to complete-value oracle matches')
    save(work/'result.json', {'status': 'D3_SCOPED_PROFILE_REPRODUCED', 'reproduction': result,
        'abstention': outcomes, 'abstention_summary': native['summary'],
        'known_date_cases_per_target': 49, 'additional_partial_cases_per_target': len(cases),
        'actual_native_executions': result['native']['executed_target_cases'],
        'shared_boundary_requests_without_native_execution': len(outcomes),
        'independent_abstention_methods': 1,
        'constructor_calendar_codec_runtime_claims_separate': True,
        'canonical_string_codec_evidence': 'EXHAUSTIVE_FINITE_CHECK_NOT_KERNEL_PROOF',
        'lifted_semantics': 'SHARED_PRE_EXECUTION_ABSTENTION_NOT_A_NEW_THEOREM',
        'whole_compiler_correctness': 'NOT_ESTABLISHED', 'legal_correctness': 'NOT_ESTABLISHED',
        'unknown_future_legal_generalization': 'NOT_ESTABLISHED', 'future_observations': 0,
        'invented_facts_for_retained_readings': False, 'human_quality_evidence': False, 'live_calls': 0})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--worker', type=Path)
    parser.add_argument('--repair', type=Path); args = parser.parse_args()
    if args.worker:
        return audit(args.worker, Path(read(SNAPSHOT)['path']))
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = OUT/'state.json'; state = read(state_path) if state_path.exists() else {'attempts': []}
        snapshot = read(SNAPSHOT); frozen = Path(snapshot['path'])
        bound = {'script': sha(__file__), 'plan': sha(PLAN), 'snapshot': sha(SNAPSHOT),
            'archive': snapshot['archive_sha256']}
        if sha(SNAPSHOT.parent/'tested-inputs.zip') != bound['archive']: raise RuntimeError('Changed source archive')
        def check_frozen():
            if any(sha(frozen/p) != h for p, h in snapshot['inputs'].items()): raise RuntimeError('Frozen source changed')
        check_frozen()
        attempts = state['attempts']; retry = None
        if attempts:
            previous = attempts[-1]; manifest = read(ROOT/previous['path'])
            intact = sha(ROOT/previous['path']) == previous['sha256'] and all(sha(ROOT/p) == h for p,h in manifest.get('outputs', {}).items())
            if intact and manifest['status'] == 'PASSED' and manifest['inputs'] == bound:
                print('Intact audit reused'); return
            if len(attempts) >= 3: raise RuntimeError('Three audit attempts exhausted')
            if not intact: raise RuntimeError('Corrupted previous audit evidence')
            if manifest['status'] == 'PASSED': retry = {'kind': 'SOURCE_REVALIDATION', 'prior': previous}
            else:
                repair = read(args.repair) if args.repair else {}
                if repair.get('prior') != previous or not repair.get('change'): raise RuntimeError('Bound causal repair required')
                receipt_path = ROOT/repair['focused']['path']; receipt = read(receipt_path)
                if (sha(receipt_path) != repair['focused']['sha256'] or receipt.get('exit_code') != 0 or
                        receipt.get('inputs') != bound or sha(ROOT/receipt['log']) != receipt['log_sha256']):
                    raise RuntimeError('Executed passing focused repair receipt required')
                retry = {'kind': 'IMPLEMENTATION_REPAIR', 'path': rel(args.repair), 'sha256': sha(args.repair)}
        work = OUT/f'attempt-{len(attempts)+1:02d}'; work.mkdir(exist_ok=False)
        started = time.monotonic()
        argv = [sys.executable, str(Path(__file__).resolve()), '--worker', str(work)]
        manifest = {'status': 'RUNNING', 'inputs': bound, 'snapshot': str(frozen), 'retry': retry,
            'plan': rel(PLAN), 'result': rel(work/'result.json'), 'command': argv,
            'environment': sys.executable, 'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
            'seed': 'N/A: deterministic theorem, exhaustive finite check and declared cases',
            'git_commit': snapshot['commit'], 'source_data': 'Unchanged G4 and nine retained UCITS readings',
            'started_at': datetime.now(timezone.utc).isoformat(), 'live_calls': 0}
        save(work/'manifest.json', manifest)
        attempts.append({'path': rel(work/'manifest.json'), 'sha256': sha(work/'manifest.json')}); save(state_path, state)
        try:
            with (work/'execution.log').open('w') as log:
                execution = subprocess.run(argv, cwd=frozen, stdout=log, stderr=subprocess.STDOUT, timeout=600,
                    env={**os.environ, 'PYTHONPATH': str(frozen/'src')+os.pathsep+str(frozen)})
            manifest['exit_code'] = execution.returncode
            if execution.returncode: raise RuntimeError('D3 execution failed; retain execution.log')
            check_frozen()
            if bound['script'] != sha(__file__) or bound['plan'] != sha(PLAN): raise RuntimeError('Audit method changed')
            manifest['status'] = 'PASSED'
        except BaseException as exc: manifest.update(status='FAILED', error=type(exc).__name__, details=str(exc))
        manifest['wall_seconds'] = round(time.monotonic()-started, 3)
        manifest['outputs'] = {rel(p): sha(p) for p in work.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        save(work/'manifest.json', manifest)
        attempts[-1] = {'path': rel(work/'manifest.json'), 'sha256': sha(work/'manifest.json')}; save(state_path, state)
        save(OUT/'next-phase-plan.json', {'last_status': manifest['status'], 'next_phase': 'D4' if manifest['status'] == 'PASSED' else 'D3-repair',
            'attempts_remaining': 3-len(attempts), 'live_calls_authorized': 0,
            'source_question': 'Retain exact authority editions and unresolved question dispositions',
            'legal_correctness': 'NOT_ESTABLISHED', 'future_observations': 0})
        print(json.dumps({'status': manifest['status'], 'manifest': attempts[-1], 'wall_seconds': manifest['wall_seconds']}))
        if manifest['status'] != 'PASSED': raise SystemExit(1)


if __name__ == '__main__': main()
