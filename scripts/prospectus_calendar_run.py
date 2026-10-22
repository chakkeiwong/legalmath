"""Bounded original-task execution for source-bound calendar premises."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from scripts.prospectus_calendar_prepare import PLAN, REVIEW, ALLOWED, BOUNDS
from scripts import prospectus_calendar_evidence as evidence

ATTEMPT = REL + '/attempts/law-applicability/attempt-008'
HERE = ROOT / ATTEMPT
TESTS = ['tests/prospectus_successor/test_calendar_facts.py',
         'tests/prospectus_successor/test_ratio_facts.py',
         'tests/prospectus_successor/test_interval_validation.py',
         'tests/prospectus_successor/test_successor.py']
SUPPORT = [PLAN, 'scripts/prospectus_calendar_prepare.py', 'scripts/prospectus_calendar_run.py',
           'scripts/prospectus_calendar_evidence.py', 'scripts/prospectus_calendar_oracle.py', *TESTS]
STAGES = ('tests', 'consumers', 'regression', 'seal')


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names.update(SUPPORT)
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def resources():
    paths = [HERE, ROOT / REVIEW, *(ROOT / p for p in SUPPORT), *(ROOT / p for p in ALLOWED),
             ROOT / REL / 'proposals/calendar-234.json', ROOT / REL / 'proposals/calendar-234-review.json',
             ROOT / REL / 'revisions/0234.json', ROOT / REL / 'closure-routes-2026-10-17-calendar-234.json']
    files = set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    return sum(p.stat().st_size for p in files if p.exists())


def freeze():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks['law-applicability']
    ad = read(HERE / 'admission.json')
    event = next(e for e in reversed(a.events()) if e.get('task') == task['id'])
    evidence.require(program['revision'] == 234 and ad['program_sha256'] == digest(program)
        and ad['binding'] == a.binding(task) and event['kind'] == 'ADMIT'
        and event['attempt'] == ATTEMPT and task['calendar_premises']['bounds'] == BOUNDS,
        'Current unchanged calendar admission required')
    before = read(ROOT / REVIEW / 'before-methods.json')
    current = methods()
    production = {k: v for k, v in current.items() if k.startswith('src/')}
    evidence.require(set(production) - set(before) == {ALLOWED[0]}
        and not set(before) - set(production)
        and {k for k in before if before[k] != production[k]} == set(ALLOWED[1:]),
        'Production change escaped reviewed calendar integration')
    path = HERE / 'methods.json'
    if path.exists():
        evidence.require(read(path) == current, 'Frozen calendar implementation changed')
    else:
        write(path, current, exclusive=True)
        for name in [*ALLOWED, *SUPPORT]:
            destination = HERE / 'methods' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as out:
                out.write((ROOT / name).read_bytes())
    return ad, current


def tests():
    boot = (
        'import sys;sys.dont_write_bytecode=True;sys.path[:0]=[sys.argv[1],sys.argv[2]];'
        'import pytest;raise SystemExit(pytest.main(sys.argv[3:]))'
    )
    argv = [sys.executable, '-c', boot, str(ROOT / 'src'), str(ROOT),
            '-q', '-p', 'no:cacheprovider', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')]
    write(HERE / 'tests-command.json', {'argv': argv, 'timeout_seconds': 100,
          'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}, exclusive=True)
    with (HERE / 'tests.stdout').open('xb') as out, (HERE / 'tests.stderr').open('xb') as err:
        code = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=100,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}).returncode
    evidence.require(code == 0, 'Calendar tests failed; inspect retained stdout/stderr')
    suites = list(ET.parse(HERE / 'tests.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.get(k, '0')) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    evidence.require(counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped')),
                     'Invalid calendar test report')
    return counts


def seal_result(status, error=None):
    write(HERE / 'result.json', {'task': 'law-applicability', 'status': status,
          'scope': 'CONDITIONAL_SOURCE_BOUND_CALENDAR_PREMISES', 'whole_task_complete': False,
          'whole_program_complete': False, 'error': error}, exclusive=True)
    write(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
          if p.is_file() and p.name not in {'outputs.json', 'admission.json'}}, exclusive=True)


def main(stage):
    evidence.require(stage in STAGES, 'Unknown calendar stage')
    evidence.require(not (HERE / 'outputs.json').exists(), 'Sealed attempt cannot execute')
    index = STAGES.index(stage)
    completed = {p.parent.name for p in (HERE / 'stages').glob('*/result.json')}
    started = {p.parent.name for p in (HERE / 'stages').glob('*/started.json')}
    evidence.require(started == completed == set(STAGES[:index]), 'Repeated, skipped or interrupted stage')
    evidence.require(all(read(HERE / 'stages' / s / 'result.json')['status'] == 'PASS' for s in STAGES[:index]),
                     'Failed predecessor stage')
    target = HERE / 'stages' / stage
    target.mkdir(parents=True, exist_ok=False)
    write(target / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
          'command': ['.venv/bin/python', 'scripts/prospectus_calendar_run.py', stage],
          'plan': PLAN}, exclusive=True)
    tick = time.monotonic()
    signal.alarm(110)
    try:
        ad, frozen = freeze()
        guard = {'blocked': 0}
        if stage != 'tests':
            def audit(event, args):
                if event.startswith('socket.') or event in {
                    'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.spawn', 'pty.spawn'}:
                    guard['blocked'] += 1
                    raise RuntimeError('Calendar evidence forbids process/network actions')
            sys.addaudithook(audit)
        if stage == 'tests':
            details = tests()
        elif stage == 'consumers':
            details = evidence.cases(ROOT, HERE)
        elif stage == 'regression':
            details = evidence.regressions(ROOT, HERE)
        else:
            evidence.require((HERE / 'RESULT.md').is_file(), 'Detailed actual result required before sealing')
            actual = read(HERE / 'calendar-evidence.json')
            evidence.require(len(actual['cases']) == 19 and len(actual['refusals']) == 8
                and actual['permissive_mutant_detected'] is True, 'Incomplete calendar matrix')
            details = {'cases': 19, 'refusals': 8, 'original_valid': 21, 'original_refusals': 2}
        evidence.require(methods() == frozen and guard['blocked'] == 0, 'Method drift or unexpected action')
        seconds = time.monotonic() - tick
        cumulative = read(ROOT / REVIEW / 'preparation-time.json')['seconds'] + seconds + sum(
            read(HERE / 'stages' / s / 'result.json')['seconds'] for s in STAGES[:index])
        size = resources()
        evidence.require(cumulative < BOUNDS['cumulative_seconds']
            and size + BOUNDS['failure_reserve_bytes'] < BOUNDS['new_bytes'], 'Cumulative calendar resource limit')
        write(target / 'result.json', {'status': 'PASS', 'details': details, 'seconds': seconds,
            'cumulative_seconds': cumulative, 'new_bytes': size, 'guard': guard}, exclusive=True)
        if stage == 'seal':
            write(HERE / 'run-manifest.json', {'git_commit': ad['git_commit'], 'plan': PLAN,
                'result': ATTEMPT + '/RESULT.md', 'interpreter': sys.executable,
                'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic arithmetic',
                'commands': [read(HERE / 'stages' / s / 'started.json') for s in STAGES],
                'test_command': read(HERE / 'tests-command.json'),
                'methods': frozen, 'source_review': REVIEW + '/review.json',
                'synthetic_dates_sha256': file_hash(HERE / 'hypothetical-dates.txt'),
                'cumulative_seconds': cumulative, 'new_bytes': size,
                'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
            seal_result('PASS')
        print(json.dumps({'stage': stage, 'status': 'PASS', 'details': details,
                          'seconds': seconds, 'cumulative_seconds': cumulative, 'new_bytes': size}))
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        write(target / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
        if not (target / 'result.json').exists():
            write(target / 'result.json', {'status': 'FAIL', 'error': error,
                  'seconds': time.monotonic() - tick}, exclusive=True)
        seal_result('FAIL', error)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main(sys.argv[1])
