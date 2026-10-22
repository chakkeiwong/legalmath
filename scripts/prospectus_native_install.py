"""Bounded installed-location repair; preserves the original001 campaign."""
from copy import deepcopy
from datetime import datetime, timezone
from email.parser import BytesParser
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus import native_profile as profile, native_binding_acceptance as compare
from legalmath.prospectus.execution_authority import Authority, read, write, file_hash
from legalmath.prospectus.successor import process_ledger, sealed_runtime
from legalmath.prospectus.successor.contracts import digest

HERE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/native-confinement/attempt-002'
FAILED = HERE.parent / 'attempt-001'
PLAN = 'docs/plans/prospectus-native-confinement-location-repair-2026-10-14.md'
WHEELS = ROOT / '.localresources/prospectus/closure-runtime/wheels'
PRIOR = ROOT / compare.BASE / 'attempt-006'
OUTER = HERE / 'command-ledger.json'
NATIVE = HERE / 'native-ledger.json'
TEST = 'tests/prospectus/test_native_profile.py'
MODES = ('fresh', 'retained')


def save(name, value):
    write(HERE / name, value, exclusive=True)


def bindings():
    paths = [Path(__file__), ROOT / 'scripts/prospectus_native_installed_controls.py',
        ROOT / PLAN, ROOT / TEST, Path(profile.__file__),
        ROOT / 'pyproject.toml', FAILED / 'IMPLEMENTATION-REVIEW.md',
        *(ROOT / 'src/legalmath/prospectus/successor').glob('*.py')]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)}


def workspace():
    return Path(read(HERE / 'workspace.json')['directory'])


def python():
    return str(workspace() / 'environment/bin/python')


def run(name, argv, cwd=None):
    target = HERE / 'commands' / name
    target.mkdir(parents=True)
    save('commands/' + name + '/command.json', {'argv': argv, 'cwd': str(cwd or workspace()),
        'environment': {'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1'},
        'timeout': 120})
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1'}
    with (target / 'stdout').open('xb') as out, (target / 'stderr').open('xb') as err:
        result = subprocess.run(argv, cwd=cwd or workspace(), env=env, stdout=out, stderr=err, timeout=120)
    save('commands/' + name + '/result.json', {'returncode': result.returncode})
    if result.returncode:
        raise ValueError('Installed command failed: ' + name + '; see retained stderr')
    return {'returncode': result.returncode}


INSTALLED_RUNNER = r'''
import json,os,sys
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus import native_profile as product
from legalmath.prospectus.successor import process_ledger
base=Path(sys.argv[1]).resolve()
environment=Path(sys.executable).parent.parent.resolve()
assert Path(product.__file__).resolve().is_relative_to(environment)
name=sys.argv[2]
proof={'module_path':str(Path(product.__file__).resolve()),'python':sys.executable,
       'methods':product.methods(),'sys_path':sys.path,'cpu_gpu':'CPU only; GPUs intentionally hidden'}
product.write(base/'commands'/name/'installed-proof.json',proof)
with process_ledger.observe(base/'native-ledger.json'):
    raise SystemExit(product.main(sys.argv[3:]))
'''


def prepare():
    compare.verify_files(FAILED, read(FAILED / 'outputs.json'))
    assert len(process_ledger.checked(FAILED / 'command-ledger.json')['reservations']) == 5
    assert not process_ledger.checked(FAILED / 'native-ledger.json')['reservations']
    process_ledger.create(OUTER, 13, 5, 'Remaining13 of original18 commands; failed001 retains5; internal forks excluded')
    process_ledger.create(NATIVE, 6, 50, 'Four planned installed source native calls; two distinct diagnostic reservations')
    compare.verify_files(PRIOR, read(PRIOR / 'outputs.json'))
    old_workspace = Path(read(FAILED / 'workspace.json')['directory'])
    old_package = old_workspace / 'environment/lib/python3.11/site-packages/legalmath'
    expected_installed = read(FAILED / 'installed-methods.json')
    compare.verify_files(old_package, expected_installed)
    parent = ROOT / '.localresources/prospectus'
    temp = Path(tempfile.mkdtemp(prefix='native-confinement-002-', dir=parent)).resolve()
    assert temp.is_relative_to(ROOT) and not str(temp).startswith('/tmp/')
    shutil.copytree(old_workspace / 'environment', temp / 'environment', symlinks=True)
    save('workspace.json', {'directory': str(temp)})
    source = temp / 'source'
    source.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    locks, inventory = [], {}
    for wheel in sorted(WHEELS.glob('*.whl')):
        with zipfile.ZipFile(wheel) as archive:
            metadata = BytesParser().parsebytes(archive.read(next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))))
        hashed = file_hash(wheel)
        locks.append(f"{metadata['Name']}=={metadata['Version']} --hash=sha256:{hashed}")
        inventory[str(wheel.relative_to(ROOT))] = hashed
    assert inventory
    (HERE / 'dependencies.lock').write_text('\n'.join(locks) + '\n')
    save('wheel-inputs.json', inventory)
    (temp / 'installed_runner.py').write_text(INSTALLED_RUNNER)
    shutil.copyfile(temp / 'installed_runner.py', HERE / 'installed_runner.py')
    shutil.copyfile(ROOT / 'scripts/prospectus_native_installed_controls.py', temp / 'installed_controls.py')
    save('relocated-installation.json', {'from':str(old_workspace / 'environment'),
        'to':str(temp / 'environment'), 'prior_installed_methods':expected_installed,
        'prior_wheel':read(FAILED / 'built-wheel.json'),
        'dependency_metadata': {str(p.relative_to(temp / 'environment')):file_hash(p)
            for p in (temp / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')}})
    for name in bindings():
        target = HERE / 'method' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return {'workspace': str(temp), 'locked_wheels': len(inventory)}


def dependencies():
    compare.verify_files(ROOT, read(HERE / 'wheel-inputs.json'))
    return run('dependencies', [python(), '-m', 'pip', 'install', '--no-index', '--find-links', str(WHEELS),
        '--require-hashes', '-r', str(HERE / 'dependencies.lock')])


def build():
    (HERE / 'wheel').mkdir()
    result = run('build', [python(), '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--no-index',
        '--wheel-dir', str(HERE / 'wheel'), str(workspace() / 'source')])
    wheels = list((HERE / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    save('built-wheel.json', {'file': str(wheels[0].relative_to(HERE)), 'sha256': file_hash(wheels[0]),
        'source_methods': bindings()})
    return result


def install():
    wheel = read(HERE / 'built-wheel.json')
    assert file_hash(HERE / wheel['file']) == wheel['sha256']
    return run('install', [python(), '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall', str(HERE / wheel['file'])])


def inventory():
    package = workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    assert package.is_dir()
    installed = {str(p.relative_to(package)): file_hash(p) for p in
                 [package / 'prospectus/native_profile.py', *(package / 'prospectus/successor').glob('*.py')]}
    assert installed == profile.methods()
    save('installed-methods.json', installed)
    original = compare.snapshot(PRIOR / 'snapshot')
    private = workspace() / 'capture-inputs'
    private.mkdir()
    rows = deepcopy(original['files'])
    for path in (package / 'prospectus/successor/ocr_worker.py', package / 'prospectus/successor/native_inputs.py'):
        rows.append({'path': str(path), 'sha256': file_hash(path), 'size': path.stat().st_size, 'mode': 0o444})
    sources = {}
    for row in rows:
        target = private / (row['sha256'] + '.' + str(row['mode']))
        if not target.exists():
            old = PRIOR / 'snapshot/blobs' / row['sha256']
            source = old if old.exists() else Path(row['path'])
            shutil.copyfile(source, target)
            target.chmod(row['mode'])
        assert file_hash(target) == row['sha256']
        sources[row['path']] = str(target)
    directories = set(original['directories'])
    for row in rows:
        directories.update(str(p) for p in Path(row['path']).parents if str(p) != '/')
    spec = {'repository': str(ROOT), 'sources': sources, 'directories': sorted(directories),
        'ocr_python': '/home/chakwong/miniconda3/envs/tfgpu/bin/python', 'native_text_max_stream': 64*1024*1024}
    save('capture-spec.json', spec)
    save('expected-snapshot.json', {**original, 'files': sorted(rows, key=lambda r: r['path']),
                                   'directories': sorted(directories)})
    request = read(ROOT / compare.BASE / 'attempt-004/request.json')
    for mode in MODES:
        req = deepcopy(request)
        if mode == 'fresh':
            req['bundle']['documents'][0].pop('hybrid_ocr')
        save(mode + '-request.json', req)
    return {'installed_methods': len(installed), 'snapshot_files': len(rows)}


def cli(stage):
    if stage == 'controls':
        return run(stage, [python(), '-I', str(workspace() / 'installed_controls.py'), str(HERE)])
    if stage == 'capture':
        args = ['capture', '--spec', str(HERE / 'capture-spec.json'), '--output', str(HERE / 'profile')]
    elif stage == 'check':
        args = ['check', '--profile', str(HERE / 'profile'), '--profile-sha256',
                read(HERE / 'profile/capture-result.json')['profile_sha256'], '--output', str(HERE / 'profile-check')]
    else:
        action, mode = stage.split('-')
        args = [action, '--output', str(HERE / mode)]
        if action == 'source':
            args += ['--request', str(HERE / (mode + '-request.json')), '--profile', str(HERE / 'profile'),
                '--profile-sha256', read(HERE / 'profile/capture-result.json')['profile_sha256']]
    result = run(stage, [python(), '-I', str(workspace() / 'installed_runner.py'), str(HERE), stage, *args])
    proof = read(HERE / 'commands' / stage / 'installed-proof.json')
    assert proof['methods'] == profile.methods()
    if stage == 'capture':
        assert read(HERE / 'profile/snapshot/manifest.json') == read(HERE / 'expected-snapshot.json')
    return result


def compare_mode(mode):
    folder = HERE / mode
    actual = compare.products(folder)
    baseline = compare.products(ROOT / compare.BASE / 'attempt-004')
    compare.compare_products(baseline, actual)
    # Reconsume with checked source-equivalent code; installed verify already
    # ran its own consumer and retained the full answer.
    compare.consumer(ROOT, *actual)
    manifest = read(HERE / 'profile/snapshot/manifest.json')
    execution = read(folder / 'execution.json')
    receipts = execution['native_receipts']
    for index, receipt in enumerate(receipts):
        streams = [(folder / 'native' / str(index) / n).read_bytes() for n in ('stdin','stdout','stderr')]
        sealed_runtime.verify_receipt(receipt, manifest, receipt['argv'], *streams)
    worker = workspace() / 'environment/lib/python3.11/site-packages/legalmath/prospectus/successor/ocr_worker.py'
    assert receipts[1]['argv'][1] == str(worker)
    assert read(folder / 'verification.json')['answer_sha256'] == actual[1]['report_sha256']
    assert read(folder / 'stages/verify/result.json')['status'] == 'PASS'
    result = {'complete_source_units': len(actual[1]['source_map']['units']), 'full_semantics_equal': True,
              'installed_consumer_checked': True, 'installed_worker_path': str(worker),
              'answer_sha256': actual[1]['report_sha256']}
    save('comparison-' + mode + '.json', result)
    return result


def main():
    stage = sys.argv[1]
    allowed = {'prepare','build','install','inventory','capture','check','controls',
        *[a+'-'+b for b in MODES for a in ('source','construct','finish','verify','compare')]}
    assert stage in allowed
    authority = Authority(ROOT)
    _, tasks, _ = authority.spec()
    ad = read(HERE / 'admission.json')
    assert ad['binding'] == authority.binding(tasks['native-confinement'])
    assert not (HERE / 'outputs.json').exists()
    methods = bindings()
    if stage == 'prepare':
        save('frozen-methods.json', methods)
    else:
        assert methods == read(HERE / 'frozen-methods.json')
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    write(folder / 'started.json', {'command': ['.venv/bin/python','-m','scripts.prospectus_native_install',stage],
        'git_commit': ad['git_commit'], 'plan': PLAN, 'methods': methods, 'environment':sys.executable,
        'cpu_gpu':'CPU only; GPUs intentionally hidden','seeds':'N/A deterministic',
        'started_at':datetime.now(timezone.utc).isoformat()}, exclusive=True)
    def expired(signum, frame):
        raise TimeoutError('120-second installation stage bound; no duplicate launch')
    signal.signal(signal.SIGALRM,expired);signal.alarm(120)
    try:
        if stage == 'prepare':
            result = prepare()
        else:
            with process_ledger.observe(OUTER):
                if stage.startswith('compare-'):
                    result = compare_mode(stage.split('-')[1])
                elif stage in {'dependencies','build','install','inventory'}:
                    result = {'dependencies':dependencies,'build':build,'install':install,'inventory':inventory}[stage]()
                else:
                    result = cli(stage)
        assert methods == bindings()
        assert ad['binding'] == authority.binding(tasks['native-confinement'])
        outcome = {'status':'PASS','details':result,'wall_seconds':time.monotonic()-tick,
                   'outer_starts':len(process_ledger.checked(OUTER)['reservations']),
                   'native_starts':len(process_ledger.checked(NATIVE)['reservations'])}
    except BaseException as error:
        write(folder/'result.json', {'status':'FAIL','error':type(error).__name__+': '+str(error),
              'wall_seconds':time.monotonic()-tick},exclusive=True)
        raise
    finally:
        signal.alarm(0)
    write(folder/'result.json',outcome,exclusive=True)
    print(json.dumps(outcome))


if __name__ == '__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        main()
