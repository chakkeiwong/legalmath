"""Optional installed prospectus stages with an explicit Linux native profile."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

from .successor import extraction, sealed_runtime, sealed_source, service
from .successor.contracts import bound_path, digest, validate_request

VERSION = 'prospectus-native-profile.v1'
PACKAGE = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    path = Path(path)
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def write(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data + b'\n')


def methods():
    paths = [Path(__file__), *(PACKAGE / 'prospectus/successor').glob('*.py')]
    return {str(p.relative_to(PACKAGE)): file_hash(p) for p in sorted(paths)}


def capture(spec, target):
    """Capture only caller-declared files; caller reviews and pins returned hash."""
    require(set(spec) == {'repository', 'sources', 'directories', 'ocr_python', 'native_text_max_stream'},
            'Capture requires exact explicit profile fields')
    root = Path(spec['repository']).resolve(strict=True)
    require(root.is_dir(), 'Repository must be a directory')
    interpreter = str(Path(spec['ocr_python']).absolute())
    require(interpreter in spec['sources'], 'OCR interpreter must be explicitly captured')
    cap = sealed_runtime.stream_bound(spec['native_text_max_stream'])
    target = Path(target)
    manifest = sealed_runtime.snapshot(target / 'snapshot', spec['sources'], spec['directories'])
    value = {'version': VERSION, 'repository': str(root), 'ocr_python': interpreter,
        'manifest_sha256': sealed_runtime.digest(manifest), 'methods': methods(),
        'trusted_runtime': sealed_runtime.trusted_runtime(), 'native_text_max_stream': cap,
        'native_reuse_allowed': False}
    write(target / 'profile.json', value)
    return {'profile_sha256': digest(value), 'manifest_sha256': value['manifest_sha256'],
            'files': len(manifest['files']), 'native_reuse_allowed': False}


def load_profile(folder, expected):
    folder = Path(folder).resolve(strict=True)
    value = read(folder / 'profile.json')
    fields = {'version', 'repository', 'ocr_python', 'manifest_sha256', 'methods',
              'trusted_runtime', 'native_text_max_stream', 'native_reuse_allowed'}
    require(set(value) == fields and value['version'] == VERSION and value['native_reuse_allowed'] is False,
            'Unsupported native profile')
    require(isinstance(expected, str) and digest(value) == expected, 'Pinned profile identity differs')
    require(value['methods'] == methods(), 'Installed product methods changed; recapture profile')
    require(value['trusted_runtime'] == sealed_runtime.trusted_runtime(), 'Trusted runtime changed; recapture profile')
    sealed_runtime.stream_bound(value['native_text_max_stream'])
    root = Path(value['repository']).resolve(strict=True)
    require(str(root) == value['repository'] and root.is_dir(), 'Repository identity changed')
    manifest = sealed_runtime.validate(read(folder / 'snapshot/manifest.json'))
    require(sealed_runtime.digest(manifest) == value['manifest_sha256'], 'Snapshot manifest identity differs')
    # Validate every declared blob before the first native child. run() later
    # seals and checks bytes again, closing the mutable-path interval.
    for row in manifest['files']:
        with sealed_runtime.sealed_file(folder / 'snapshot/blobs' / row['sha256'], row['sha256'], row['size']):
            pass
    return value, manifest


def preflight(request, profile, manifest):
    bundle = validate_request(request)
    root = Path(profile['repository'])
    interpreter = profile['ocr_python']
    worker = str(Path(extraction.__file__).with_name('ocr_worker.py').resolve())
    native_inputs = str(Path(worker).with_name('native_inputs.py'))
    text = shutil.which('pdftotext')
    require(bool(text), 'pdftotext is unavailable')
    text = str(Path(text).resolve(strict=True))
    files = {row['path']: row for row in manifest['files']}
    required = {text: file_hash(text), interpreter: file_hash(interpreter),
                worker: file_hash(worker), native_inputs: file_hash(native_inputs)}
    for doc in bundle['documents']:
        require(doc.get('format', 'pdf') == 'pdf' and bool(doc.get('hybrid_profile')),
                'This profile supports explicitly selected hybrid PDF sources')
        path = bound_path(root, doc['path'])
        require(file_hash(path) == doc['sha256'], 'Source bytes changed')
        required[str(path)] = doc['sha256']
        ocr, tessdata = extraction.scan_profile(doc, root, hybrid=True)
        for language, hashed in ocr['models'].items():
            required[str(tessdata / (language + '.traineddata'))] = hashed
        if doc.get('hybrid_ocr'):
            retained = doc['hybrid_ocr']
            require(set(retained) == {'path', 'sha256'} and
                    file_hash(bound_path(root, retained['path'])) == retained['sha256'],
                    'Retained OCR identity differs')
    for name, expected in required.items():
        require(name in files and files[name]['sha256'] == expected, 'Required profile file absent or changed: ' + name)
    for name in (text, interpreter):
        require(files[name]['mode'] == 0o555, 'Required executable is not executable')
    return required


@contextmanager
def cpu_environment(interpreter):
    updates = {'CUDA_VISIBLE_DEVICES': '-1', 'LEGALMATH_OCR_PYTHON': interpreter}
    before = {k: os.environ.get(k) for k in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def checked_stage(job, name):
    row = read(job / 'stages' / name / 'result.json')
    require(row.get('status') == 'PASS', 'Predecessor stage did not pass: ' + name)
    for key, hashed in row.get('files', {}).items():
        path = (job / key).resolve(strict=True)
        require(path.is_relative_to(job.resolve()) and file_hash(path) == hashed,
                'Predecessor file changed: ' + key)
    require(bool(row.get('files')), 'Predecessor file inventory missing')
    return row


def source(request, profile_folder, expected, job):
    profile, manifest = load_profile(profile_folder, expected)
    required = preflight(request, profile, manifest)
    runtime = sealed_source.SourceRuntime(Path(profile_folder) / 'snapshot', profile['manifest_sha256'],
        evidence_directory=job / 'native', native_text_max_stream=profile['native_text_max_stream'])
    with cpu_environment(profile['ocr_python']):
        p1 = sealed_source.source_product(request, Path(profile['repository']), runtime)
    require(len(runtime.receipts) == 2 * len(request['bundle']['documents']), 'Native source receipt denominator differs')
    write(job / 'P1.json.gz', p1)
    write(job / 'execution.json', {'profile': str(Path(profile_folder).resolve()), 'profile_sha256': expected,
        'request_sha256': digest(request), 'required_files': required, 'methods': methods(),
        'module_path': str(Path(__file__).resolve()), 'python': sys.executable,
        'native_receipts': runtime.receipts, 'native_reuse_allowed': False})
    return ['P1.json.gz', 'execution.json',
            *[str(p.relative_to(job)) for p in sorted((job / 'native').rglob('*')) if p.is_file()]]


def context(job):
    checked_stage(job, 'source')
    execution = read(job / 'execution.json')
    profile, manifest = load_profile(execution['profile'], execution['profile_sha256'])
    require(execution['methods'] == methods(), 'Execution methods differ')
    p1 = read(job / 'P1.json.gz')
    request = service.verify(p1, 'P1')['request']
    require(execution['request_sha256'] == digest(request), 'Execution request differs')
    return execution, profile, manifest, p1


def construct(job):
    _, profile, _, p1 = context(job)
    write(job / 'P2.json.gz', service.construction_product(p1, Path(profile['repository'])))
    return ['P2.json.gz']


def finish(job):
    _, profile, _, p1 = context(job)
    checked_stage(job, 'construct')
    p2 = read(job / 'P2.json.gz')
    p3 = service.interpretation_product(p1, p2)
    p4 = service.law_product(p1, p3)
    p5 = service.financial_product(p1, p2, p3)
    products = dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5)
    answer = service.consume(products, Path(profile['repository']), include_artifacts=True)
    for name in ('P3', 'P4', 'P5'):
        write(job / (name + '.json.gz'), products[name])
    write(job / 'answer.json.gz', answer)
    return ['P3.json.gz', 'P4.json.gz', 'P5.json.gz', 'answer.json.gz']


def verify(job):
    execution, profile, manifest, p1 = context(job)
    checked_stage(job, 'construct')
    checked_stage(job, 'finish')
    values = {k: read(job / (k + '.json.gz')) for k in ('P1', 'P2', 'P3', 'P4', 'P5')}
    answer = read(job / 'answer.json.gz')
    require(service.consume(values, Path(profile['repository']), include_artifacts=True) == answer,
            'Delivered answer differs from actual consumer')
    receipts = execution['native_receipts']
    documents = p1['payload']['graph']['documents']
    require(len(receipts) == 2 * len(documents), 'Missing native receipts')
    for i, row in enumerate(receipts):
        folder = job / 'native' / str(i)
        require(read(folder / 'receipt.json') == row, 'Native receipt inventory differs')
        sealed_runtime.verify_receipt(row, manifest, row['argv'],
            *[(folder / name).read_bytes() for name in ('stdin', 'stdout', 'stderr')])
        require(row['returncode'] == 0, 'Native command failed')
    for i, doc in enumerate(documents):
        first, second = receipts[2*i:2*i+2]
        target = doc['runtime'] if doc['fresh_extraction'] else doc['image_verification']['verification_runtime']
        require(doc['native_extraction']['sealed_execution'] == first and target['sealed_execution'] == second,
                'Native receipts were not delivered through source graph')
    require(answer['source_map'] == p1['payload']['graph'], 'Source graph differs in delivered answer')
    value = {'version': VERSION, 'profile_sha256': execution['profile_sha256'],
        'answer_sha256': answer['report_sha256'], 'consumed_products': answer['consumed_products'],
        'native_calls': len(receipts), 'native_reuse_allowed': False, 'independent_legal_acceptance': False}
    write(job / 'verification.json', value)
    return ['verification.json']


def stage(job, name, action, *, new=False):
    job = Path(job).resolve()
    if new:
        job.mkdir(parents=True, exist_ok=False)
    require(job.is_dir(), 'Existing execution directory required')
    marker = job / 'stages' / name
    marker.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    write(marker / 'started.json', {'command': sys.argv, 'python': sys.executable,
        'module_path': str(Path(__file__).resolve()), 'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only; GPUs intentionally hidden', 'methods': methods()})
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_alarm = signal.getitimer(signal.ITIMER_REAL)
    def expired(signum, frame):
        raise TimeoutError('120-second stage limit reached; previous evidence retained')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, min(previous_alarm[0], 120) if previous_alarm[0] else 120)
    try:
        names = action()
        files = {n: file_hash(job / n) for n in names}
        value = {'status': 'PASS', 'files': files, 'wall_seconds': time.monotonic() - start}
    except BaseException as error:
        write(marker / 'result.json', {'status': 'FAIL', 'error': type(error).__name__ + ': ' + str(error),
                                      'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_alarm[0]:
            signal.setitimer(signal.ITIMER_REAL, max(.001, previous_alarm[0] - (time.monotonic() - start)), previous_alarm[1])
    write(marker / 'result.json', value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('capture')
    p.add_argument('--spec', required=True)
    p.add_argument('--output', required=True)
    p = commands.add_parser('check')
    p.add_argument('--profile', required=True)
    p.add_argument('--profile-sha256', required=True)
    p.add_argument('--output', required=True)
    p = commands.add_parser('source')
    p.add_argument('--request', required=True)
    p.add_argument('--profile', required=True)
    p.add_argument('--profile-sha256', required=True)
    p.add_argument('--output', required=True)
    for name in ('construct', 'finish', 'verify'):
        p = commands.add_parser(name)
        p.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    job = Path(args.output).resolve()
    if args.action == 'capture':
        def action():
            receipt = capture(read(args.spec), job)
            write(job / 'capture-result.json', receipt)
            return ['profile.json', 'snapshot/manifest.json', 'snapshot/capture.json', 'capture-result.json']
    elif args.action == 'check':
        def action():
            profile, manifest = load_profile(args.profile, args.profile_sha256)
            write(job / 'check.json', {'profile_sha256': digest(profile), 'files': len(manifest['files']),
                                     'native_reuse_allowed': False})
            return ['check.json']
    elif args.action == 'source':
        def action():
            return source(read(args.request), args.profile, args.profile_sha256, job)
    else:
        def action():
            return {'construct': construct, 'finish': finish, 'verify': verify}[args.action](job)
    with cpu_environment(os.environ.get('LEGALMATH_OCR_PYTHON', sys.executable)):
        value = stage(job, args.action, action, new=args.action in ('capture', 'check', 'source'))
    print(json.dumps({'stage': args.action, 'output': str(job), **value}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
