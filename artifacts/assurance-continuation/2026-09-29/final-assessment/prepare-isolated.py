"""Copy the working inputs without modifying another worker's files."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[4]
DEST = Path('/tmp/legalmath-continuation-final-20260929')
OUT = ROOT/'artifacts/assurance-continuation/2026-09-29/final-assessment/isolation'
sys.path.insert(0, str(ROOT/'scripts'))
import run_assurance_continuation as runner


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


OUT.mkdir(exist_ok=False)
DEST.mkdir(exist_ok=False)
start = time.monotonic()
commands = []
initial = runner.regression_inputs()
reviewed = json.loads((runner.OUT/'reviewed-implementation.json').read_text())
assert all(sha(ROOT/p) == h for p,h in reviewed['inputs'].items())
try:
    exclusions = ['/.worktrees/', '/.venv/', '/.codex/', '/.agents/',
                  '/.pytest_cache/', '/.hypothesis/', '__pycache__/',
                  '/.localresources/catala-toolchain',
                  '/artifacts/assurance-continuation/2026-09-29/final-assessment/']
    cmd = ['rsync', '-a', *['--exclude='+x for x in exclusions], str(ROOT)+'/', str(DEST)+'/']
    commands.append(cmd)
    subprocess.run(cmd, check=True)
    # Original evidence resolves this toolchain inside .worktrees; preserve that
    # relative location rather than weakening the evidence-file boundary.
    relative = '.worktrees/catala/.localresources/catala-toolchain'
    target = DEST/relative
    target.mkdir(parents=True)
    cmd = ['rsync', '-a', str((ROOT/'.localresources/catala-toolchain').resolve())+'/', str(target)+'/']
    commands.append(cmd)
    subprocess.run(cmd, check=True)
    (DEST/'.localresources/catala-toolchain').symlink_to('../'+relative)
    (DEST/'.venv').symlink_to(ROOT/'.venv', target_is_directory=True)
    # Freeze each last material input from a stable read, including files added
    # during the data copy. This does not assert one atomic live-workspace state.
    names = set(runner.regression_inputs()) | set(reviewed['inputs']) | {
        'pyproject.toml', 'docs/plans/assurance-continuation-final-assessment.md'}
    for name in names:
        source, destination = ROOT/name, DEST/name
        for attempt in range(3):
            before = source.stat()
            data = source.read_bytes()
            after = source.stat()
            if (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                break
        else:
            raise RuntimeError('Material input remained unstable: '+name)
    frozen = {name: sha(DEST/name) for name in names}
    assert all(frozen.get(p) == h for p,h in reviewed['inputs'].items())
    with ZipFile(OUT/'tested-inputs.zip', 'w', ZIP_DEFLATED) as archive:
        for name in sorted(frozen):
            archive.write(DEST/name, name)
    source_now = runner.regression_inputs()
    deltas = {p:{'initial':initial.get(p), 'snapshot':frozen.get(p), 'current':source_now.get(p)}
              for p in set(initial)|set(frozen)|set(source_now)
              if len({initial.get(p),frozen.get(p),source_now.get(p)}) > 1}
    save('manifest.json', {'status':'SNAPSHOT_CREATED', 'snapshot':str(DEST),
         'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'script_sha256':sha(__file__), 'argv':[sys.executable,*sys.argv],
         'elapsed_seconds':round(time.monotonic()-start,3), 'commands':commands,
         'inputs':frozen, 'copy_time_changes':deltas, 'reviewed_inputs_unchanged':len(reviewed['inputs']),
         'archive_sha256':sha(OUT/'tested-inputs.zip'),
         'python_environment':str(ROOT/'.venv'), 'package_source':str(DEST/'src'),
         'cpu_only':True,'live_calls':0,
         'plan':'docs/plans/assurance-continuation-final-assessment.md'})
    print('Snapshot created:', DEST, 'material inputs:', len(frozen), flush=True)
except BaseException as error:
    save('failure.json', {'error':type(error).__name__, 'details':str(error),
                         'commands':commands,'elapsed_seconds':time.monotonic()-start})
    raise
