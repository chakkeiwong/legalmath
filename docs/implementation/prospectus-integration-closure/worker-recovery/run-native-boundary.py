"""Bounded actual read/child/confinement controls; never authorizes reuse."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-worker-recovery-2026-10-10.md'
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
OCR_PYTHON = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
MODEL = ROOT / 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata'
TRACE_LIMIT = 10_000_000
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'CUDA_VISIBLE_DEVICES': '-1',
       'OMP_THREAD_LIMIT': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import read_context  # noqa: E402
from legalmath.prospectus.successor.contracts import read, write  # noqa: E402

TINY = '''import json,os,subprocess,sys
from pathlib import Path
def value(path):
    try: return {'value':Path(path).read_text()}
    except OSError as exc: return {'error':type(exc).__name__}
external=Path(sys.argv[1])
if len(sys.argv)>2:
    print(json.dumps({'pid':os.getpid(),'read':value(external)}))
else:
    child=subprocess.run([sys.executable,__file__,str(external),'child'],capture_output=True,text=True,check=True)
    print(json.dumps({'pid':os.getpid(),'declared':value('declared.txt'),
        'undeclared':value(external),'symlink':value('link.txt'),
        'missing':value('missing.txt'),'child':json.loads(child.stdout)}))
'''

LAUNCHER = '''import json,subprocess,sys
from pathlib import Path
case=Path(__file__).resolve().parent
spec={'source':str(case/'scan.pdf'),'tessdata':str(case/'models'),
      'language':'eng','dpi':300,'max_pages':2}
run=subprocess.run([sys.executable,str(case/'ocr_worker.py')],input=json.dumps(spec),text=True,capture_output=True)
sys.stdout.write(run.stdout)
sys.stderr.write(run.stderr)
raise SystemExit(run.returncode)
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (TRACE_LIMIT, TRACE_LIMIT))


def trace_argv(log, argv):
    return ['/usr/bin/strace', '-f', '-yy', '-s', '64', '-e',
            'trace=%file,%process,read,pread64,mmap', '-o', str(log), *argv]


def confined(case, argv, ocr=False):
    mounts = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-all', '--clearenv',
        '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
        '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
        '--tmpfs', '/tmp', '--ro-bind', str(case), '/case', '--chdir', '/case']
    if ocr:
        prefix = str(OCR_PYTHON.parent.parent)
        mounts += ['--ro-bind', prefix, prefix]
    for key, value in ENV.items():
        mounts += ['--setenv', key, value]
    return mounts + ['--', *argv]


def main():
    if Path(read_context.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/read_context.py':
        raise RuntimeError('Wrong worktree imported')
    folder = PACKAGE / 'native-boundary/attempt-001'
    if folder.exists():
        raise RuntimeError('Inspect retained attempt before a changed-method retry')
    folder.mkdir(parents=True)
    baseline_dir = PACKAGE / 'ocr-baseline/attempt-001'
    manifest = read(baseline_dir / 'manifest.json')
    if any(sha(baseline_dir / name) != value for name, value in manifest['files'].items()):
        raise RuntimeError('Protected baseline changed')
    worker = ROOT / 'src/legalmath/prospectus/successor/ocr_worker.py'
    method = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, worker,
        ROOT / 'src/legalmath/prospectus/successor/read_context.py']}
    started = {'version': 'native-read-diagnostic.v1',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': ['timeout', '90', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
        'environment': ENV, 'orchestrator': sys.executable, 'ocr_python': str(OCR_PYTHON),
        'ocr_interpreter_sha256': sha(OCR_PYTHON),
        'versions': {name: subprocess.check_output([name, '--version'], text=True).splitlines()[0]
                     for name in ('strace', 'bwrap')},
        'seeds': 'N/A deterministic controls', 'timeout_seconds': 90,
        'trace_limit_bytes': TRACE_LIMIT, 'evidence_limit_bytes': 100_000_000,
        'metadata_reserve_bytes': 1_048_576,
        'data_version': {'ocr_baseline_manifest_sha256': sha(baseline_dir / 'manifest.json')},
        'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT))}
    write(folder / 'started.json', started)
    commands = []
    tick = time.monotonic()

    def call(name, argv, cwd):
        run = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, text=True,
                             timeout=30, preexec_fn=file_limit)
        (folder / (name + '.stdout')).write_text(run.stdout)
        (folder / (name + '.stderr')).write_text(run.stderr)
        commands.append({'name': name, 'argv': argv, 'cwd': str(cwd), 'returncode': run.returncode})
        write(folder / 'commands.json', commands)
        if run.returncode:
            raise RuntimeError(name + ' failed: ' + run.stderr[-1600:])
        return json.loads(run.stdout)

    try:
        with tempfile.TemporaryDirectory(prefix='prospectus-native-', dir='/tmp') as location, \
                tempfile.TemporaryDirectory(prefix='prospectus-external-', dir='/tmp') as external_root:
            case = Path(location)
            external = Path(external_root) / 'undeclared.txt'
            external.write_text('first external value')
            (case / 'declared.txt').write_text('declared value')
            (case / 'link.txt').symlink_to(external)
            (case / 'tiny.py').write_text(TINY)
            write(folder / 'fixture.json', {'worker_sha256': sha(case / 'tiny.py'),
                'declared_sha256': sha(case / 'declared.txt'), 'external_sha256': sha(external),
                'external_path': str(external), 'case_root': str(case)})
            context = read_context.ReadContext(case, case / 'snapshots')
            control = context.tool(['/usr/bin/python3', str(case / 'tiny.py'), str(external)],
                                   inputs=['tiny.py', 'declared.txt'], env=ENV, timeout=10)
            if control.returncode:
                raise RuntimeError('ReadContext adverse control failed')
            control_data = json.loads(control.stdout)
            write(folder / 'control.json', control_data)
            write(folder / 'read-context.json', context.manifest())
            if not read_context.current(case, context.manifest()) or read_context.reusable(case, context.manifest()):
                raise RuntimeError('Native reuse veto absent before mutation')
            for name, content in [('tiny-first', 'first external value'), ('tiny-changed', 'changed external value')]:
                external.write_text(content)
                log = folder / (name + '.trace')
                output = call(name, trace_argv(log, ['/usr/bin/python3', str(case / 'tiny.py'), str(external)]), case)
                write(folder / (name + '.json'), output)
                if any(output[key] != {'value': content} for key in ('undeclared', 'symlink')) or (
                        output['child']['read'] != {'value': content} or
                        output['declared'] != {'value': 'declared value'} or
                        output['missing'] != {'error': 'FileNotFoundError'}):
                    raise RuntimeError('Tiny direct/child/symlink oracle failed')
                trace = log.read_text()
                if log.stat().st_size >= TRACE_LIMIT or any(token not in trace for token in
                        (str(external), 'declared.txt', 'link.txt', 'missing.txt', 'ENOENT')):
                    raise RuntimeError('Tiny trace lost a required path or exceeded limit')
                child_lines = [line for line in trace.splitlines() if line.startswith(str(output['child']['pid']) + ' ')]
                if not any(str(external) in line for line in child_lines):
                    raise RuntimeError('Trace omitted actual child external read')
                if not read_context.current(case, context.manifest()) or read_context.reusable(case, context.manifest()):
                    raise RuntimeError('Unbound native input incorrectly became reusable')
            denied = call('tiny-confined', confined(case, ['/usr/bin/python3', '/case/tiny.py', str(external)]), case)
            if denied['declared'] != {'value': 'declared value'} or any(
                    denied[key] != {'error': 'FileNotFoundError'} for key in ('undeclared', 'symlink', 'missing')) or (
                    denied['child']['read'] != {'error': 'FileNotFoundError'}):
                raise RuntimeError('Confined fixture admitted external read or lost declared input')
            write(folder / 'tiny-confined.json', denied)
            (case / 'models').mkdir()
            shutil.copy2(BASE / 'packages/scan/attempt-001/new-scan.pdf', case / 'scan.pdf')
            shutil.copy2(MODEL, case / 'models/eng.traineddata')
            shutil.copy2(worker, case / 'ocr_worker.py')
            (case / 'launch-ocr.py').write_text(LAUNCHER)
            expected = read(baseline_dir / 'raw-worker.json')
            expected['runtime'] = {key: value for key, value in expected['runtime'].items()
                                   if key not in {'interpreter_sha256', 'worker_sha256', 'language_models', 'dependency_assurance'}}
            if sha(case / 'scan.pdf') != expected['source_sha256'] or (
                    sha(case / 'models/eng.traineddata') != '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'):
                raise RuntimeError('Copied OCR input differs')
            log = folder / 'ocr.trace'
            actual = call('ocr-traced', trace_argv(log, [str(OCR_PYTHON), str(case / 'launch-ocr.py')]), case)
            write(folder / 'ocr-traced.json', actual)
            trace = log.read_text()
            if log.stat().st_size >= TRACE_LIMIT or any(name not in trace for name in
                    ('scan.pdf', 'eng.traineddata', 'ocr_worker.py')):
                raise RuntimeError('Actual worker trace missing required input or exceeded limit')
            enclosed = call('ocr-confined', confined(case, [str(OCR_PYTHON), '/case/launch-ocr.py'], ocr=True), case)
            write(folder / 'ocr-confined.json', enclosed)
            if actual != expected or enclosed != expected:
                raise RuntimeError('Traced/confined actual OCR differs from full protected baseline')
            write(folder / 'ocr-inputs.json', {'pdf_sha256': sha(case / 'scan.pdf'),
                'model_sha256': sha(case / 'models/eng.traineddata'), 'worker_sha256': sha(case / 'ocr_worker.py'),
                'launcher_sha256': sha(case / 'launch-ocr.py')})
        if method != {name: sha(ROOT / name) for name in method}:
            raise RuntimeError('Method changed during native probe')
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise RuntimeError('Evidence cap exceeded')
        result = {'status': 'PASS', 'read_observation': 'DIRECT_CHILD_SYMLINK_CHANGED_FILE_AND_NEGATIVE_LOOKUP_OBSERVED',
            'fixture_boundary': 'DECLARED_READ_OK_EXTERNAL_DIRECT_CHILD_SYMLINK_DENIED',
            'actual_ocr': 'TRACED_AND_CONFINED_FULL_BASELINE_EQUAL',
            'read_context_current_after_undeclared_change': True, 'read_context_reusable': False,
            'trace_complete_for_reuse': False, 'production_policy_changed': False,
            'limits': ['Broad runtime mounts are not immutable dependency closure',
                'proc/device reads, environment and negative lookups need complete binding',
                'Trace/path hashes do not eliminate races; host portability untested'],
            'evidence_payload_bytes': payload, 'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    write(folder / 'result.json', result)
    write(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
