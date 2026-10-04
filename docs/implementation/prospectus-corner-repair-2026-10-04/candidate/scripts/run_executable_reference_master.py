#!/usr/bin/env python3
"""Offline executable-reference phases with preserved failures and bounded, evidenced repair."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts/executable-reference-assurance/2026-09-29'
DOC = ROOT/'docs/implementation/executable-reference-assurance'
PLAN = ROOT/'docs/plans/executable-reference-execution.md'
PYTHON = ROOT/'.venv/bin/python'
PHASES = ('D2', 'verify')
MAX_ATTEMPTS = 3


def now(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return str(Path(p).relative_to(ROOT))
def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_suffix('.tmp'); temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n'); temporary.replace(p)


def inputs():
    names = ['pyproject.toml', rel(PLAN), 'scripts/run_executable_reference_master.py',
        'scripts/executable_reference_checks.py', 'scripts/assurance_capacity_checks.py',
        'scripts/assurance_continuation_checks.py',
        'src/legalmath/interpretation/assurance/executable_references.py',
        'src/legalmath/interpretation/assurance/executable_references_v2.py',
        'src/legalmath/interpretation/assurance/scoped_investigation.py',
        'src/legalmath/interpretation/assurance/complete_investigation.py',
        'src/legalmath/interpretation/assurance/fidelity_v2.py',
        'src/legalmath/interpretation/assurance/semantics.py',
        'src/legalmath/interpretation/assurance/source_references.py',
        'src/legalmath/interpretation/search/formal.py',
        'tests/assurance/test_executable_references.py',
        'tests/assurance/test_executable_references_v2.py',
        'tests/assurance/test_executable_reference_master.py']
    # The manuscript is shared with another workstream. Snapshot every document
    # input and reject changes inside that snapshot, but permit later live edits.
    # Delivery compares the tested/current manuscript before copying any PDF.
    return {n: sha(ROOT/n) for n in names}


def material(root):
    return {str(p.relative_to(root)): sha(p) for name in ('src', 'tests', 'scripts', 'docs/monograph')
        for p in (root/name).rglob('*') if p.is_file() and p.suffix in ('.py', '.java', '.lean', '.json', '.tex', '.bib')
        and not str(p.relative_to(root)).startswith('docs/monograph/review/')}


def valid(receipt, *, current=True):
    path = ROOT/receipt['path']
    if not path.is_file() or sha(path) != receipt['sha256']: return False
    value = read(path)
    return (value['status'] == 'PASSED' and (not current or value['inputs'] == inputs()) and
        all((ROOT/p).is_file() and sha(ROOT/p) == h for p, h in value['outputs'].items()))


def state(): return read(OUT/'state.json') if (OUT/'state.json').exists() else {'phases': {}}


def status():
    value = state(); rows = {}
    for phase in PHASES:
        attempts = value['phases'].get(phase, []); passed = bool(attempts and valid(attempts[-1]))
        rows[phase] = {'status': 'PASSED' if passed else ('ATTEMPTS_EXHAUSTED' if len(attempts) >= MAX_ATTEMPTS
            else ('STALE_OR_FAILED' if attempts else 'PENDING')), 'attempts': len(attempts),
            'attempts_remaining': max(0, MAX_ATTEMPTS-len(attempts))}
    return {'phases': rows, 'live_authorized_remaining': 0, 'legal_correctness': 'NOT_ESTABLISHED',
            'scope': 'D2 offline increment with historical replay and isolated verification; D3 audit and D4-D6 remain.'}


def refresh():
    report = status(); pending = [p for p in PHASES if report['phases'][p]['status'] != 'PASSED']
    next_phase = pending[0] if pending else 'D3-audit'
    exhausted = bool(pending and report['phases'][next_phase]['status'] == 'ATTEMPTS_EXHAUSTED')
    result = {**report, 'at': now(), 'next_phase': next_phase, 'retry_exhausted': exhausted,
        'action': 'Preserve exhausted attempts; a separately reviewed engineering continuation is required.' if exhausted else
        ('Run the next audited offline phase; failed retries require executed repair evidence.' if pending else
         'Audit the imported Gregorian proof/domain boundaries; refresh D4 source work and the frozen prospective method.'),
        'successor_plan': 'docs/implementation/executable-reference-assurance/next-phase-plan.md',
        'no_live_or_issue_reset': True, 'historical_study_complete': False}
    save(OUT/'next-phase-plan.json', result); return result


def retry_evidence(phase, attempts):
    if not attempts: return {'kind': 'INITIAL_EXECUTION'}
    prior = attempts[-1]
    if valid(prior, current=False): return {'kind': 'SOURCE_REVALIDATION', 'prior_manifest': prior}
    note = DOC/f'{phase}-repair-{len(attempts)}.json'; value = read(note)
    if value.get('prior_manifest') != prior or not value.get('change'): raise RuntimeError('Detached repair note')
    focused = value['focused_result']; path = ROOT/focused['path']
    receipt = read(path)
    if (sha(path) != focused['sha256'] or receipt.get('exit_code') != 0 or
            receipt.get('input_hashes') != inputs() or not receipt.get('argv') or
            not (ROOT/receipt.get('log', '')).is_file() or
            sha(ROOT/receipt['log']) != receipt.get('log_sha256')):
        raise RuntimeError('Repair lacks a successful executed focused command')
    return {'kind': 'IMPLEMENTATION_REPAIR', 'prior_manifest': prior, 'repair': rel(note), 'sha256': sha(note)}


def command(argv, work, label, *, cwd=ROOT, timeout=1800):
    start = time.monotonic(); log = work/(label+'.log'); before = inputs()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(cwd/'src')+os.pathsep+str(cwd)}
    with log.open('w') as output:
        try: code = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired: code = 124
    receipt = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'exit_code': code, 'cpu_only': True,
        'elapsed_seconds': round(time.monotonic()-start, 3), 'log': rel(log), 'log_sha256': sha(log),
        'PYTHONPATH': env['PYTHONPATH'], 'live_calls': 0, 'input_hashes': before}
    save(work/(label+'-command.json'), receipt)
    if code: raise RuntimeError(f'{label} failed with exit {code}; see {rel(log)}')
    if inputs() != before: raise RuntimeError('Inputs changed during command')
    return receipt


def snapshot(work, name):
    target = Path('/tmp')/('legalmath-executable-reference-'+name)
    target.mkdir(exist_ok=False)
    exclusions = ['/.worktrees/', '/.venv/', '/.codex/', '/.agents/', '/.pytest_cache/', '/.hypothesis/',
                  '__pycache__/', '/.localresources/catala-toolchain', '/artifacts/executable-reference-assurance/']
    command(['rsync', '-a', *['--exclude='+x for x in exclusions], str(ROOT)+'/', str(target)+'/'], work, 'copy-snapshot')
    relative = '.worktrees/catala/.localresources/catala-toolchain'; tools = target/relative
    tools.mkdir(parents=True)
    command(['rsync', '-a', str((ROOT/'.localresources/catala-toolchain').resolve())+'/', str(tools)+'/'], work, 'copy-catala')
    (target/'.localresources/catala-toolchain').symlink_to('../'+relative)
    (target/'.venv').symlink_to(ROOT/'.venv', target_is_directory=True)
    # Stable individual reads avoid asserting an atomic concurrently edited tree.
    names = set(material(ROOT)) | set(inputs())
    for name in names:
        source = ROOT/name
        for _ in range(3):
            before = source.stat(); data = source.read_bytes(); after = source.stat()
            if (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size): break
        else: raise RuntimeError('Unstable input: '+name)
        (target/name).parent.mkdir(parents=True, exist_ok=True); (target/name).write_bytes(data)
    frozen = {name: sha(target/name) for name in sorted(names)}
    if any(frozen[n] != h for n, h in inputs().items()): raise RuntimeError('Phase implementation changed during freeze')
    with ZipFile(work/'tested-inputs.zip', 'w', ZIP_DEFLATED) as archive:
        for name in frozen: archive.write(target/name, name)
    result = {'path': str(target), 'inputs': frozen, 'archive_sha256': sha(work/'tested-inputs.zip'),
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    save(work/'snapshot.json', result); return target, result


def phase(name):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = state(); attempts = current['phases'].setdefault(name, [])
        if attempts and valid(attempts[-1]): return read(ROOT/attempts[-1]['path'])
        if len(attempts) >= MAX_ATTEMPTS: raise RuntimeError('Attempts exhausted; no reset')
        retry = retry_evidence(name, attempts)
        for predecessor in PHASES[:PHASES.index(name)]:
            rows = current['phases'].get(predecessor, [])
            if not rows or not valid(rows[-1]): raise RuntimeError('Predecessor requires verification: '+predecessor)
        attempt = len(attempts)+1; work = OUT/name/f'attempt-{attempt:02d}'; work.mkdir(parents=True, exist_ok=False)
        started = time.monotonic(); before = inputs()
        manifest = {'phase': name, 'attempt': attempt, 'status': 'RUNNING', 'started_at': now(), 'inputs': before,
            'plan': rel(PLAN), 'retry_evidence': retry, 'live_calls': 0, 'cpu_only': True,
            'seed': 'N/A: deterministic reference integrity and historical replay', 'commands': [],
            'argv': [sys.executable, *sys.argv], 'environment': str(PYTHON),
            'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
        save(work/'manifest.json', manifest)
        # Reserve the engineering attempt before subprocesses. Interruption is
        # spent history; it cannot reappear as an initial execution on restart.
        attempts.append({'path': rel(work/'manifest.json'), 'sha256': sha(work/'manifest.json')})
        save(OUT/'state.json', current)
        try:
            target, frozen = snapshot(work, name.lower()+f'-{attempt:02d}')
            manifest['snapshot'] = str(target)
            if name == 'D2':
                tests = ['tests/assurance/test_executable_references.py',
                    'tests/assurance/test_executable_references_v2.py',
                    'tests/assurance/test_executable_reference_master.py',
                    'tests/assurance/test_continuation_references.py',
                    'tests/assurance/test_continuation_scheduling.py',
                    'tests/assurance/test_continuation_integration.py',
                    'tests/assurance/test_successor_workflow.py',
                    'tests/assurance/test_successor_quote_diagnostics.py']
                manifest['commands'].append(command([PYTHON, '-m', 'pytest', '-q', *tests,
                    '--junitxml='+str(work/'tests.xml')], work, 'focused-tests', cwd=target))
                manifest['commands'].append(command([PYTHON, target/'scripts/executable_reference_checks.py',
                    work/'checks'], work, 'evidence-checks', cwd=target))
                manifest['result'] = read(work/'checks/result.json')
            else:
                manifest['commands'].append(command([PYTHON, '-m', 'pytest', '-q',
                    'tests/integration/test_api.py::test_api_evaluation_identity_and_restart'],
                    work, 'api-environment', cwd=target, timeout=90))
                manifest['commands'].append(command([PYTHON, '-m', 'pytest', '-q',
                    '--junitxml='+str(work/'full-regression.xml')], work, 'full-regression', cwd=target, timeout=3600))
                tree = ET.parse(work/'full-regression.xml').getroot()
                counts = {k: sum(int(s.get(k, 0)) for s in tree.iter('testsuite')) for k in ('tests', 'failures', 'errors', 'skipped')}
                manifest['regression'] = counts
                if not counts['tests'] or any(counts[k] for k in ('failures', 'errors', 'skipped')): raise RuntimeError(str(counts))
                doc_python = shutil.which('python3')
                manifest['commands'].append(command([doc_python, 'scripts/build_reader_facing_monograph.py'],
                    work, 'documents', cwd=target, timeout=1200))
                manifest['commands'].append(command([doc_python, 'scripts/check_monograph.py'], work, 'document-check', cwd=target))
                (work/'documents').mkdir()
                from pypdf import PdfReader
                manifest['documents'] = {}
                for filename in ('monograph.pdf', 'technical-companion.pdf', 'process-guide.pdf'):
                    p = target/'docs/monograph'/filename; shutil.copy2(p, work/'documents'/filename)
                    manifest['documents'][filename] = {'pages': len(PdfReader(p).pages), 'sha256': sha(p)}
            if any(sha(target/p) != h for p, h in frozen['inputs'].items()): raise RuntimeError('Frozen material input changed')
            if inputs() != before: raise RuntimeError('Owned phase input changed during execution')
            manifest['status'] = 'PASSED'
        except BaseException as exc:
            manifest.update(status='FAILED', error=type(exc).__name__, details=str(exc)[:6000])
        manifest.update(finished_at=now(), elapsed_seconds=round(time.monotonic()-started, 3),
            legal_correctness='NOT_ESTABLISHED', historical_study_complete=False)
        manifest['outputs'] = {rel(p): sha(p) for p in work.rglob('*') if p.is_file() and p != work/'manifest.json'}
        save(work/'manifest.json', manifest)
        attempts[-1] = {'path': rel(work/'manifest.json'), 'sha256': sha(work/'manifest.json')}
        save(OUT/'state.json', current); refresh()
        print(json.dumps({'phase': name, 'status': manifest['status'], 'details': manifest.get('details')}), flush=True)
        if manifest['status'] != 'PASSED': raise SystemExit(1)
        return manifest


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['phase', 'verify', 'status'])
    parser.add_argument('name', nargs='?', choices=['D2']); args = parser.parse_args()
    if args.action == 'status': print(json.dumps(status(), indent=2))
    elif args.action == 'verify': phase('verify')
    elif args.name: phase(args.name)
    else: parser.error('phase needs D2')


if __name__ == '__main__': main()
