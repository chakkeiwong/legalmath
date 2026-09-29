"""Re-execute the failed boundary assertion against frozen built targets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]; OUT = Path(__file__).parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
snapshot_path = ROOT/'artifacts/executable-reference-assurance/2026-09-29/verify/attempt-01/snapshot.json'
snapshot = read(snapshot_path); frozen = Path(snapshot['path'])
bound = {'script': sha(OUT/'run.py'), 'plan': sha(ROOT/'docs/plans/gregorian-profile-audit.md'),
    'snapshot': sha(snapshot_path), 'archive': snapshot['archive_sha256']}
if '--worker' in sys.argv:
    sys.path[:0] = [str(frozen/'src'), str(frozen)]
    from legalmath.translation import pipeline
    from legalmath.canonical import digest
    folder = OUT/'attempt-01/abstention'; cases = read(folder/'cases.json')
    for target in ('ruleir', 'catala'):
        for case in cases:
            result = pipeline.execute_all(folder/target, case['snapshot'], case['valid_at'], case['known_at'],
                frozen/'.localresources/java-toolchain/jdk-17.0.20.1+1')
            reason = 'INCOMPLETE_INPUTS' if case['id'].startswith('unknown') else 'CONFLICTING_INPUTS'
            assert all(v['status'] == 'ABSTAIN' and v['reason'] == reason and v['execution'] is None
                for v in result['results'].values())
    print('8 target-route requests abstained at the common complete.v1 boundary; 0 native executions.')
else:
    log = OUT/'repair-focus-02.log'; argv = [sys.executable, str(Path(__file__).resolve()), '--worker']
    started = time.monotonic()
    with log.open('w') as f:
        run = subprocess.run(argv, cwd=frozen, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
            'PYTHONPATH': str(frozen/'src')+os.pathsep+str(frozen)}, stdout=f, stderr=subprocess.STDOUT, timeout=60)
    receipt = OUT/'repair-focus-02.json'; receipt.write_text(json.dumps({'argv': argv, 'exit_code': run.returncode,
        'inputs': bound, 'script_sha256': sha(__file__), 'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log),
        'cpu_only': True, 'wall_seconds': time.monotonic()-started}, indent=2)+'\n')
    if run.returncode: raise SystemExit(run.returncode)
    prior = read(OUT/'state.json')['attempts'][-1]
    (OUT/'repair-01-with-path-fix.json').write_text(json.dumps({'prior': prior,
        'change': 'The failed harness expected native UNKNOWN/CONFLICT under complete.v1. Policy and pipeline inspection establishes shared pre-execution ABSTAIN. Check status, exact reason and execution=None, retain the failed attempt, and count 8 boundary requests separately from 98 native executions. Also normalize a relative repair-note path before recording its root-relative identity; the first retry invocation failed on that path conversion before reserving a new attempt.',
        'focused': {'path': str(receipt.relative_to(ROOT)), 'sha256': sha(receipt)}}, indent=2)+'\n')
    print(log.read_text())
