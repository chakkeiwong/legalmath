"""Execute one reviewed source-baseline continuation without altering frozen validators."""
from datetime import datetime, timezone
from pathlib import Path
import json
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts import prospectus_registration_validation as previous
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash

retained = previous.retained
PLAN = 'docs/plans/prospectus-registration-baseline-review-2026-10-18.md'
REVIEW = ROOT / REL / 'reviews/registration-baseline-255'
HERE = ROOT / REL / 'attempts/entitlement/attempt-011'
STAGES = retained.STAGES
retained.HERE = HERE


def measured_seconds():
    old = read(ROOT / REL / 'attempts/entitlement/attempt-010/run-manifest.json')
    return (old['cumulative_measured_seconds'] + read(REVIEW / 'preflight.json')['seconds']
            + sum(read(p)['seconds'] for p in (HERE / 'stages').glob('*/result.json')))


def storage():
    extra = [REVIEW, HERE, ROOT / PLAN, Path(__file__),
             ROOT / REL / 'proposals/registration-baseline-255.json',
             ROOT / REL / 'proposals/registration-baseline-255-review.json',
             ROOT / REL / 'revisions/0255.json',
             ROOT / REL / 'closure-routes-2026-10-18-registration-baseline-255.json']
    files = set()
    for path in extra:
        if path.is_dir():
            files.update(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        elif path.is_file():
            files.add(path)
    return previous.storage() + sum(p.stat().st_size for p in files)


def methods_unchanged():
    original = read(retained.REVIEW / 'freeze.json')
    revised254 = read(previous.REVIEW / 'freeze.json')
    revised255 = read(REVIEW / 'freeze.json')
    current = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    retained.require(current == set(original['production']), 'Production inventory changed')
    corrections = {'tests/prospectus_successor/test_conversion_admission.py': revised254,
                   'tests/prospectus_successor/test_repairs.py': revised255}
    for name in corrections:
        retained.require(file_hash(retained.REVIEW / 'methods' / name) == original['methods'][name],
                         'Original test baseline changed: ' + name)
    for name, expected in {**original['methods'], **original['retained']}.items():
        retained.require(file_hash(ROOT / name) == (corrections[name][name] if name in corrections else expected),
                         'Frozen input/method changed: ' + name)
    for freeze in (revised254, revised255):
        for name, expected in freeze.items():
            retained.require(file_hash(ROOT / name) == expected, 'Reviewed wrapper/input changed: ' + name)


def authenticate():
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    admission = read(HERE / 'admission.json')
    retained.require(program['revision'] == 255 and admission['task'] == 'entitlement', 'Wrong admission')
    retained.require(admission['binding'] == auth.binding(tasks['entitlement']), 'Admission binding changed')
    event = next(e for e in reversed(auth.events()) if e.get('task') == 'entitlement')
    retained.require(event['kind'] == 'ADMIT' and event['attempt'] == str(HERE.relative_to(ROOT)), 'No active admission011')
    bounds = tasks['entitlement']['registration_baseline_review']['effective_bounds']
    retained.require(bounds == tasks['entitlement']['registration_validation']['effective_bounds'], 'Bounds changed')
    methods_unchanged()
    retained.require(measured_seconds() < 480 and storage() + 1024**2 < 160 * 1024**2, 'Cumulative ceiling')
    retained.source_graph.pdf_units = lambda *_: (_ for _ in ()).throw(ValueError('Six native calls already used'))
    return admission


def main():
    stage = sys.argv[1]
    retained.require(stage in STAGES, 'Unknown stage')
    for prerequisite in STAGES[:STAGES.index(stage)]:
        retained.require(read(HERE / 'stages' / prerequisite / 'result.json')['status'] == 'PASS',
                         'Prerequisite failed; reviewed continuation required')
    folder = HERE / 'stages' / stage
    write(folder / 'started.json', {'command': ['.venv/bin/python', str(Path(__file__).relative_to(ROOT)), stage],
          'at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}, exclusive=True)
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('120s stage bound')))
    signal.alarm(120)
    try:
        admission = authenticate()
        detail = retained.tests() if stage == 'tests' else retained.seal() if stage == 'seal' else retained.primary(stage)
        methods_unchanged()
        retained.require(measured_seconds() + time.monotonic() - start < 480
                         and storage() + 1024**2 < 160 * 1024**2, 'Cumulative ceiling')
        result = {'status': 'PASS', 'seconds': time.monotonic() - start, 'detail': detail}
    except Exception as exc:
        write(folder / 'result.json', {'status': 'FAIL', 'seconds': time.monotonic() - start,
              'error': type(exc).__name__ + ': ' + str(exc)}, exclusive=True)
        raise
    write(folder / 'result.json', result, exclusive=True)
    if stage == 'seal':
        write(HERE / 'run-manifest.json', {
            'git_commit': admission['git_commit'], 'plan': PLAN,
            'result': str((HERE / 'RESULT.md').relative_to(ROOT)), 'python': sys.version, 'interpreter': sys.executable,
            'environment': 'Existing .venv; imports pinned to this worktree',
            'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A; deterministic',
            'commands': [read(p) for p in sorted((HERE / 'stages').glob('*/started.json'))],
            'sources': read(retained.REVIEW / 'source-bindings.json'),
            'production_freeze': str((retained.REVIEW / 'freeze.json').relative_to(ROOT)),
            'wrapper_freezes': [str((p / 'freeze.json').relative_to(ROOT)) for p in (previous.REVIEW, REVIEW)],
            'stages': {p.parent.name: read(p) for p in (HERE / 'stages').glob('*/result.json')},
            'cumulative_measured_seconds': measured_seconds(), 'historical_unmeasured_seconds': 'UNKNOWN',
            'native_pdf_calls_this_admission': 0, 'source_campaign_native_pdf_calls': 6,
            'original_storage_limit_bytes': 80 * 1024**2, 'effective_storage_limit_bytes': 160 * 1024**2,
            'source_campaign_storage_before_manifest': storage(),
            'retained010_regression_failure': str((ROOT / REL / 'attempts/entitlement/attempt-010/outputs.json').relative_to(ROOT))}, exclusive=True)
        write(HERE / 'result.json', {'task': 'entitlement', 'status': 'PASS', 'scope': 'REGISTRATION_GROUP_PRIMARY_Q5',
              'whole_task_complete': False, 'whole_program_complete': False, 'summary': detail}, exclusive=True)
        write(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and p.name not in {'admission.json', 'outputs.json'} and '__pycache__' not in p.parts}, exclusive=True)
        retained.require(storage() < 160 * 1024**2, 'Final cumulative storage ceiling')
    signal.alarm(0)
    print(json.dumps({'stage': stage, **result}), flush=True)


if __name__ == '__main__':
    main()
