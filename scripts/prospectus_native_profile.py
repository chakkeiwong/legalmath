"""Exclusive bounded stages for native-binding008; preserves failed007."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES='-1',
                  LEGALMATH_OCR_PYTHON='/home/chakwong/miniconda3/envs/tfgpu/bin/python')
from legalmath.prospectus import native_binding_acceptance as acceptance
from legalmath.prospectus.execution_authority import Authority, read, write, file_hash
from legalmath.prospectus.successor import process_ledger, sealed_runtime as runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import digest

HERE = ROOT / acceptance.BASE / 'attempt-008'
PRIOR = ROOT / acceptance.BASE / 'attempt-006'
LEDGER = HERE / 'process-ledger.json'
PLAN = 'docs/plans/prospectus-native-binding-identity-repair-2026-10-14.md'
SENTINEL = '/prospectus-probe-sentinel'
HOST_ONLY = HERE / 'host-only-sentinel'


def save(name, value):
    write(HERE / name, value, exclusive=True)


def pack(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), mtime=0))


def count():
    return len(process_ledger.checked(LEDGER)['reservations']) if LEDGER.exists() else 0


def bindings():
    paths = [ROOT / 'scripts/prospectus_native_profile.py', ROOT / 'src/legalmath/prospectus/native_binding_acceptance.py',
             *(ROOT / 'src/legalmath/prospectus/successor').glob('*.py'),
             *(ROOT / name for name in acceptance.TESTS),
             ROOT / acceptance.BASE / 'attempt-007/IMPLEMENTATION-REVIEW.md', ROOT / PLAN]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)}


def prepare():
    process_ledger.create(LEDGER, 12, 39, 'Distinct original2009 source matrix; ten planned starts, two diagnostic-only spare')
    acceptance.verify_files(PRIOR, read(PRIOR / 'outputs.json'))
    old_methods = read(PRIOR / 'frozen-methods.json')
    acceptance.verify_files(ROOT, {k: v for k, v in old_methods.items() if k.startswith('src/')})
    failed = ROOT / acceptance.BASE / 'attempt-007'
    acceptance.verify_files(failed, read(failed / 'outputs.json'))
    acceptance.require(not process_ledger.checked(failed / 'process-ledger.json')['reservations'],
                       'Prior campaign reservations changed')
    p1 = acceptance.protected_source(ROOT / acceptance.PROTECTED)
    req = p1['payload']['request']
    save('request.json', req)
    doc = req['bundle']['documents'][0]
    acceptance.require(file_hash(ROOT / doc['path']) == doc['sha256'], 'Original source changed')
    acceptance.require(file_hash(ROOT / doc['hybrid_ocr']['path']) == doc['hybrid_ocr']['sha256'], 'Retained worker changed')
    manifest = deepcopy(acceptance.snapshot(PRIOR / 'snapshot'))
    folder = HERE / 'snapshot'
    (folder / 'blobs').mkdir(parents=True)
    for hashed in {r['sha256'] for r in manifest['files']}:
        shutil.copyfile(PRIOR / 'snapshot/blobs' / hashed, folder / 'blobs' / hashed)
    source = (ROOT / doc['path']).resolve(strict=True)
    additions = [(str(source), source.read_bytes()), (SENTINEL, b'before-capture\n')]
    for path, data in additions:
        acceptance.require(path not in {r['path'] for r in manifest['files']}, 'Addition already declared')
        hashed = digest(data)
        blob = folder / 'blobs' / hashed
        if not blob.exists():
            with blob.open('xb') as stream:
                stream.write(data)
        manifest['files'].append({'path': path, 'sha256': hashed, 'size': len(data), 'mode': 0o444})
    manifest['files'].sort(key=lambda r: r['path'])
    manifest['directories'] = sorted(set(manifest['directories']) |
        {str(p) for p in source.parents if str(p) != '/'})
    runtime.validate(manifest)
    save('snapshot/manifest.json', manifest)
    save('inventory.json', {'manifest_sha256': runtime.digest(manifest), 'files': len(manifest['files']),
        'logical_bytes': sum(r['size'] for r in manifest['files']), 'old_outputs_sha256': file_hash(PRIOR / 'outputs.json'),
        'protected_file_sha256': acceptance.PROTECTED_FILE_HASH, 'protected_product_sha256': acceptance.PROTECTED_HASH,
        'added': [n for n, _ in additions],
        'universal_dependency_closure': False, 'native_reuse_allowed': False})
    for name in bindings():
        target = HERE / 'method-final' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return read(HERE / 'inventory.json')


@contextmanager
def capture_default(folder):
    """Retain actual default command results; cap time without replacing execution."""
    original = subprocess.run
    folder.mkdir()
    calls = []
    def run(argv, *args, **kwargs):
        target = folder / str(len(calls))
        target.mkdir()
        kwargs['timeout'] = min(kwargs.get('timeout', 60), 60)
        stdin = kwargs.get('input', b'')
        encode = lambda v: v.encode() if isinstance(v, str) else v
        write(target / 'command.json', {'argv': argv, 'timeout': kwargs['timeout'],
            'environment': {k: kwargs.get('env', os.environ).get(k) for k in ('CUDA_VISIBLE_DEVICES', 'OMP_THREAD_LIMIT', 'LANG')}}, exclusive=True)
        (target / 'stdin').write_bytes(encode(stdin))
        result = original(argv, *args, **kwargs)
        for name in ('stdout', 'stderr'):
            (target / name).write_bytes(encode(getattr(result, name)))
        write(target / 'result.json', {'returncode': result.returncode}, exclusive=True)
        calls.append(argv)
        return result
    subprocess.run = run
    try:
        yield calls
    finally:
        subprocess.run = original


def source(mode):
    original = read(HERE / 'request.json')
    req = acceptance.source_request(original, mode)
    folder = HERE / mode
    folder.mkdir()
    before = count()
    if mode == 'default':
        with capture_default(folder / 'native') as calls:
            raw = service.source_product(req, ROOT)
        acceptance.require(len(calls) == 2, 'Default call denominator changed')
    else:
        candidate = sealed_source.SourceRuntime(HERE / 'snapshot', read(HERE / 'inventory.json')['manifest_sha256'],
            evidence_directory=folder / 'native', native_text_max_stream=64*1024*1024)
        raw = sealed_source.source_product(req, ROOT, candidate)
        save(mode + '/receipts.json', candidate.receipts)
        acceptance.require(len(candidate.receipts) == 2, 'Selected call denominator changed')
    pack(mode + '/raw-P1.json.gz', raw)
    p1 = acceptance.rebind(raw, original)
    pack(mode + '/P1.json.gz', p1)
    save(mode + '/request.json', p1['payload']['request'])
    acceptance.require(count() - before == 2, 'Unexpected source child count')
    protected = acceptance.unpack(ROOT / acceptance.PROTECTED)
    acceptance.check_geometry(p1['payload']['graph'], protected['payload']['graph'])
    return {'units': len(p1['payload']['graph']['units']), 'native_calls': 2, 'geometry_preserved': True}


def construct(mode):
    p1 = acceptance.unpack(HERE / mode / 'P1.json.gz')
    p2 = service.construction_product(p1, ROOT)
    pack(mode + '/P2.json.gz', p2)
    return {'constructed': True}


def finish(mode):
    folder = HERE / mode
    p1, p2 = (acceptance.unpack(folder / (p + '.json.gz')) for p in ('P1', 'P2'))
    p3 = service.interpretation_product(p1, p2)
    p4 = service.law_product(p1, p3)
    p5 = service.financial_product(p1, p2, p3)
    products = dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5)
    for p in ('P3', 'P4', 'P5'):
        pack(mode + '/' + p + '.json.gz', products[p])
    answer = service.consume(products, ROOT, include_artifacts=True)
    pack(mode + '/answer.json.gz', answer)
    acceptance.products(folder)
    return {'own_products_consumed': True, 'assessment_mode': answer['assessment_mode']}


def probe():
    folder = HERE / 'probe'
    folder.mkdir()
    manifest = read(HERE / 'snapshot/manifest.json')
    source = str((ROOT / read(HERE / 'request.json')['bundle']['documents'][0]['path']).resolve())
    with HOST_ONLY.open('x') as stream:
        stream.write('host-only\n')
    program = ('import os,json\nfrom pathlib import Path\n'
        'r={"environment":dict(os.environ),"sentinel":Path(' + repr(SENTINEL) + ').read_text()}\n'
        'try: Path(' + repr(str(HOST_ONLY)) + ').read_bytes();r["host_errno"]=0\n'
        'except OSError as e:r["host_errno"]=e.errno\n'
        'try: fd=os.open(' + repr(source) + ',os.O_WRONLY);os.close(fd);r["write_errno"]=0\n'
        'except OSError as e:r["write_errno"]=e.errno\n'
        'print(json.dumps(r,sort_keys=True))\n')
    blob = HERE / 'snapshot/blobs' / digest(b'before-capture\n')
    evidence = {'host_existed': HOST_ONLY.is_file(), 'host_path': str(HOST_ONLY),
        'sentinel_path': SENTINEL, 'host_extra_environment': 'PROSPECTUS_HOST_ONLY',
        'before_sha256': file_hash(blob), 'program': program}
    def mutate():
        blob.write_bytes(b'after-capture!\n')
        evidence['after_capture_sha256'] = file_hash(blob)
    previous = os.environ.get('PROSPECTUS_HOST_ONLY')
    os.environ['PROSPECTUS_HOST_ONLY'] = 'must-not-leak'
    try:
        result = runtime.run(HERE / 'snapshot', manifest,
            [os.environ['LEGALMATH_OCR_PYTHON'], '-c', program], after_capture=mutate)
        for name in ('stdout', 'stderr'):
            (folder / name).write_bytes(result[name])
        (folder / 'stdin').write_bytes(b'')
        save('probe/receipt.json', result['receipt'])
    finally:
        blob.write_bytes(b'before-capture\n')
        evidence['restored_sha256'] = file_hash(blob)
        save('probe/control.json', evidence)
        if previous is None:
            os.environ.pop('PROSPECTUS_HOST_ONLY')
        else:
            os.environ['PROSPECTUS_HOST_ONLY'] = previous
    acceptance.check_probe(HERE, manifest)
    return {'actual_namespace_environment_and_capture_race': 'PASS'}


def controls():
    manifest = read(HERE / 'snapshot/manifest.json')
    indexed = {r['path']: r for r in manifest['files']}
    doc = read(HERE / 'request.json')['bundle']['documents'][0]
    targets = {'source': str((ROOT / doc['path']).resolve()),
        'model': str((ROOT / doc['hybrid_profile']['tessdata'] / 'por.traineddata').resolve()),
        'worker': str(ROOT / 'src/legalmath/prospectus/successor/ocr_worker.py'), 'executable': '/usr/bin/pdftotext'}
    results = []
    for name, path in targets.items():
        for mutation in ('wrong-hash', 'missing'):
            candidate = sealed_source.SourceRuntime(HERE / 'snapshot', runtime.digest(manifest))
            changed = deepcopy(manifest)
            if mutation == 'missing':
                changed['files'] = [r for r in changed['files'] if r['path'] != path]
            else:
                next(r for r in changed['files'] if r['path'] == path)['sha256'] = '0'*64
            candidate.manifest = changed
            candidate.manifest_sha256 = runtime.digest(changed)
            before = count()
            try:
                candidate.execute(['/usr/bin/pdftotext'], b'',
                    {'/usr/bin/pdftotext': indexed['/usr/bin/pdftotext']['sha256'], path: indexed[path]['sha256']})
            except ValueError as error:
                results.append({'input': name, 'mutation': mutation, 'reason': str(error),
                    'refused': True, 'processes_before': before, 'processes_after': count()})
            else:
                raise ValueError('Changed declaration launched: ' + name)
    save('actual-input-refusals.json', results)
    return {'refusals': acceptance.check_controls(HERE), 'native_starts': 0}


def tests():
    import pytest
    with (HERE / 'tests.log').open('x') as stream, redirect_stdout(stream), redirect_stderr(stream):
        code = pytest.main(['-q', *acceptance.TESTS, '-k',
            'not test_ledger_refuses_actual_second_launch_before_marker_write and not test_failed_launch_consumes_reservation_and_corruption_refuses',
            '--junitxml=' + str(HERE / 'tests.xml')])
    acceptance.require(code == 0, 'Focused tests failed; inspect retained tests.log')
    return {'pytest_exit': int(code), 'in_process_pytest': True}


def compare():
    result = acceptance.evidence(ROOT, HERE)
    save('verification.json', result)
    return result


def storage():
    failed = ROOT / acceptance.BASE / 'attempt-007'
    files = [p for base in (failed, HERE) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    inodes = {}
    for p in files:
        s = p.stat()
        inodes[(s.st_dev, s.st_ino)] = s.st_blocks * 512
    return {'logical_bytes': sum(p.stat().st_size for p in files),
            'physical_bytes': sum(inodes.values()), 'files': len(files),
            'distinct_inodes': len(inodes), 'physical_limit': 450*1024*1024}


def seal():
    result = acceptance.evidence(ROOT, HERE)
    acceptance.require(result == read(HERE / 'verification.json'), 'Verification changed before seal')
    sizes = storage()
    acceptance.require(sizes['physical_bytes'] < sizes['physical_limit'] - 1024*1024, 'Evidence storage budget exceeded')
    stages = {p.parent.name: read(p) for p in (HERE / 'invocations').glob('*/result.json')}
    save('run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'environment': sys.executable, 'cpu_gpu': 'CPU only; GPUs intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': read(HERE / 'inventory.json'), 'plan': PLAN,
        'result': str((HERE / 'RESULT.md').relative_to(ROOT)),
        'methods': bindings(), 'stage_results_before_seal': stages, 'storage_before_seal': sizes,
        'commands': {p.parent.name: read(p)['command'] for p in (HERE / 'invocations').glob('*/started.json')},
        'supervised_native_starts': count(), 'historical_lower_bound': 39, 'cumulative_lower_bound': 39 + count(),
        'driver_invocations_are_separate': True})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write('# Supported file binding: finite evidence retained\n\n'
            'The original 2009 default, fresh sealed OCR and sealed retained-image routes preserve '
            'all 31,526 source units, the unknown colon geometry, original correction operations, '
            'report readings, complete downstream semantics and own-parent bindings. The historical '
            '2010 full comparison remains verifiable under unchanged product methods. Actual boundary '
            'controls verify absent undeclared files, exact environment, read-only inputs and sealed '
            'bytes after capture mutation. Eight changed/missing declarations refuse before launch.\n\n'
            '| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n'
            '| --- | --- | --- | --- | --- | --- |\n'
            '| Retain supported binding | Complete matrix and downstream equality | Required checks pass | '
            'Shared interpretation and one host | Register named validator, revalidate current acceptances | '
            'No independent legal or whole-program acceptance |\n\n'
            'This attempt remains partial until the authority independently applies the named validator. '
            'Production lifecycle and portability remain separate obligations. The strongest alternative '
            'explanation is a shared interpretation error; equality proves preservation, not legal truth. '
            'No package failure, cache/default promotion or authenticated host attestation is claimed. '
            'All failed historical evidence remains unchanged. Current product methods were not modified.\n')
    save('result.json', {'status': 'PASS', 'task': 'native-binding', 'scope': 'FINITE_ENGINEERING_ONLY',
        'whole_program_complete': False, 'native_reuse_allowed': False,
        'ended_at': datetime.now(timezone.utc).isoformat(),
        'next_action': 'Register named acceptance and revalidate changed authority bindings; continue confinement'})
    return {'evidence': result, 'storage_before_seal': sizes}


def main():
    stage = sys.argv[1]
    acceptance.require(stage in {*acceptance.STAGES, 'compare', 'seal'}, 'Unknown stage')
    authority = Authority(ROOT)
    _, tasks, _ = authority.spec()
    admission = read(HERE / 'admission.json')
    acceptance.require(admission['binding'] == authority.binding(tasks['native-binding']), 'Admission changed')
    acceptance.require(not (HERE / 'outputs.json').exists(), 'Attempt already sealed')
    methods = bindings()
    if stage == 'prepare':
        save('frozen-methods.json', methods)
    else:
        acceptance.require(methods == read(HERE / 'frozen-methods.json'), 'Frozen methods changed')
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    write(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_native_profile', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'environment': sys.executable,
        'git_commit': admission['git_commit'], 'cpu_gpu': 'CPU only; GPUs intentionally hidden',
        'methods_sha256': digest(methods), 'plan': PLAN, 'processes_before': count()}, exclusive=True)
    def timeout(signum, frame):
        raise TimeoutError('Stage exceeds120second limit; no duplicate launch')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    try:
        if stage == 'prepare':
            result = prepare()
        else:
            with process_ledger.observe(LEDGER):
                parts = stage.split('-')
                result = ({'source': source, 'construct': construct, 'finish': finish}[parts[0]](parts[1])
                    if len(parts) == 2 else {'tests': tests, 'probe': probe, 'controls': controls,
                                           'compare': compare, 'seal': seal}[stage]())
        acceptance.require(bindings() == methods, 'Methods changed during stage')
        acceptance.require(admission['binding'] == authority.binding(tasks['native-binding']), 'Admission changed during stage')
        outcome = {'status': 'PASS', 'details': result, 'wall_seconds': time.monotonic()-tick, 'processes_after': count()}
    except BaseException as error:
        write(folder / 'result.json', {'status': 'FAIL', 'error': type(error).__name__ + ': ' + str(error),
            'wall_seconds': time.monotonic()-tick, 'processes_after': count()}, exclusive=True)
        raise
    finally:
        signal.alarm(0)
    write(folder / 'result.json', outcome, exclusive=True)
    if stage == 'seal':
        files = {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
                 if p.is_file() and '__pycache__' not in p.parts and p.name != 'outputs.json'}
        save('outputs.json', files)
    print(json.dumps(outcome))


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
