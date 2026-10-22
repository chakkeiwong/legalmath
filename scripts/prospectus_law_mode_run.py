"""Execute only the admitted assistance-label repair with cumulative bounds."""
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
from scripts.prospectus_law_mode_prepare import PLAN, REVIEW, PRIOR, SERVICE, BOUNDS
from scripts import prospectus_law_mode_evidence as evidence
from scripts.prospectus_calendar_run import resources as prior_resources

ATTEMPT = REL + '/attempts/law-applicability/attempt-009'
HERE = ROOT / ATTEMPT
TESTS = ['tests/prospectus_successor/test_law_assistance_mode.py',
         'tests/prospectus_successor/test_calendar_facts.py',
         'tests/prospectus_successor/test_ratio_facts.py',
         'tests/prospectus_successor/test_interval_validation.py',
         'tests/prospectus_successor/test_successor.py']
SUPPORT = [PLAN, 'scripts/prospectus_law_mode_prepare.py', 'scripts/prospectus_law_mode_run.py',
           'scripts/prospectus_law_mode_evidence.py', *TESTS]
STAGES = ('tests', 'calendar', 'original', *('native-' + r for r in evidence.ROUTES), 'seal')


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names.update(SUPPORT)
    names.update({'scripts/prospectus_calendar_evidence.py', 'scripts/prospectus_calendar_oracle.py',
                  'scripts/prospectus_calendar_run.py', 'scripts/prospectus_calendar_prepare.py'})
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def resources():
    paths = [HERE, ROOT / REVIEW, *(ROOT / n for n in SUPPORT),
             ROOT / REL / 'proposals/law-mode-235.json', ROOT / REL / 'proposals/law-mode-235-review.json',
             ROOT / REL / 'revisions/0235.json', ROOT / REL / 'closure-routes-2026-10-17-law-mode-235.json']
    files = set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    # Shared support is deliberately charged twice: this is a conservative bound.
    return prior_resources() + sum(p.stat().st_size for p in files if p.exists())


def freeze():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks['law-applicability']
    ad = read(HERE / 'admission.json')
    event = next(e for e in reversed(a.events()) if e.get('task') == task['id'])
    evidence.require(program['revision'] == 235 and ad['program_sha256'] == digest(program)
        and ad['binding'] == a.binding(task) and event['kind'] == 'ADMIT'
        and event['attempt'] == ATTEMPT and task['law_mode_repair']['bounds'] == BOUNDS,
        'Current unchanged law-mode admission required')
    before, current = read(ROOT / REVIEW / 'before-methods.json'), methods()
    production = {k: v for k, v in current.items() if k.startswith('src/')}
    evidence.require(set(production) == set(before)
        and {k for k in before if before[k] != production[k]} == {SERVICE}, 'Repair changed unrelated production')
    frozen = HERE / 'methods.json'
    if frozen.exists():
        evidence.require(read(frozen) == current, 'Frozen law-mode methods changed')
    else:
        write(frozen, current, exclusive=True)
        for name in [SERVICE, *SUPPORT]:
            dest = HERE / 'methods' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                stream.write((ROOT / name).read_bytes())
    return ad, current


def tests():
    argv = [sys.executable, '-c',
            'import sys;sys.dont_write_bytecode=True;sys.path[:0]=[sys.argv[1],sys.argv[2]];import pytest;raise SystemExit(pytest.main(sys.argv[3:]))',
            str(ROOT / 'src'), str(ROOT), '-q', '-p', 'no:cacheprovider', *TESTS,
            '--junitxml=' + str(HERE / 'tests.xml')]
    write(HERE / 'test-command.json', {'argv': argv, 'timeout_seconds': 100}, exclusive=True)
    with (HERE / 'tests.stdout').open('xb') as out, (HERE / 'tests.stderr').open('xb') as err:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                stdout=out, stderr=err, timeout=100)
    evidence.require(result.returncode == 0, 'Law-mode tests failed; read retained logs')
    suites = list(ET.parse(HERE / 'tests.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.get(k, '0')) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    evidence.require(counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped')),
                     'Incomplete law-mode test result')
    return counts


def seal(status, error=None):
    write(HERE / 'result.json', {'task': 'law-applicability', 'status': status, 'error': error,
        'scope': 'SUPPLIED_LEGAL_MODEL_ASSISTANCE_ATTRIBUTION', 'whole_task_complete': False,
        'whole_program_complete': False}, exclusive=True)
    write(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p)
        for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in {'outputs.json', 'admission.json'}}, exclusive=True)


def main(stage):
    evidence.require(stage in STAGES and not (HERE / 'outputs.json').exists(), 'Unknown stage or sealed attempt')
    index = STAGES.index(stage)
    started = {p.parent.name for p in (HERE / 'stages').glob('*/started.json')}
    ended = {p.parent.name for p in (HERE / 'stages').glob('*/result.json')}
    evidence.require(started == ended == set(STAGES[:index]), 'Repeated, skipped or interrupted stage')
    evidence.require(all(read(HERE / 'stages' / s / 'result.json')['status'] == 'PASS' for s in STAGES[:index]),
                     'Failed predecessor')
    target = HERE / 'stages' / stage
    target.mkdir(parents=True, exist_ok=False)
    write(target / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
        'command': ['.venv/bin/python', 'scripts/prospectus_law_mode_run.py', stage], 'plan': PLAN}, exclusive=True)
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
                    raise RuntimeError('Law-mode evidence forbids process/network actions')
            sys.addaudithook(audit)
        if stage == 'tests':
            details = tests()
        elif stage == 'calendar':
            details = evidence.calendar(ROOT, HERE)
        elif stage == 'original':
            details = evidence.original(ROOT, HERE)
        elif stage.startswith('native-'):
            details = evidence.native(ROOT, HERE, stage.removeprefix('native-'))
        else:
            evidence.require((HERE / 'RESULT.md').is_file(), 'Actual result note required')
            details = {'calendar': 19, 'original_valid': 21, 'original_refusals': 2, 'native_routes': 5}
        evidence.require(frozen == methods() and guard['blocked'] == 0, 'Unexpected mutation or action')
        seconds = time.monotonic() - tick
        cumulative = (read(ROOT / PRIOR / 'run-manifest.json')['cumulative_seconds']
            + read(ROOT / REVIEW / 'preparation-time.json')['seconds'] + seconds
            + sum(read(HERE / 'stages' / s / 'result.json')['seconds'] for s in STAGES[:index]))
        size = resources()
        evidence.require(cumulative < 600 and size + 2 * 1024**2 < 64 * 1024**2, 'Cumulative calendar/label bound exhausted')
        write(target / 'result.json', {'status': 'PASS', 'details': details, 'seconds': seconds,
            'cumulative_seconds_with_008': cumulative, 'cumulative_bytes_with_008': size, 'guard': guard}, exclusive=True)
        if stage == 'seal':
            write(HERE / 'run-manifest.json', {'git_commit': ad['git_commit'], 'plan': PLAN,
                'result': ATTEMPT + '/RESULT.md', 'interpreter': sys.executable,
                'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic',
                'methods': frozen, 'sources': REVIEW + '/reproduction.json',
                'commands': [read(HERE / 'stages' / s / 'started.json') for s in STAGES],
                'test_command': read(HERE / 'test-command.json'),
                'cumulative_seconds_with_008': cumulative, 'cumulative_bytes_with_008': size,
                'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
            seal('PASS')
        print(json.dumps({'stage': stage, 'status': 'PASS', 'details': details,
            'seconds': seconds, 'cumulative_seconds_with_008': cumulative}))
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        write(target / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
        if not (target / 'result.json').exists():
            write(target / 'result.json', {'status': 'FAIL', 'error': error, 'seconds': time.monotonic() - tick}, exclusive=True)
        seal('FAIL', error)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main(sys.argv[1])
