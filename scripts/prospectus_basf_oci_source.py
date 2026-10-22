"""Immutable original-page preparation before implementing the supplied reading."""
from datetime import datetime, timezone
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
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'basf-references/attempt-003'
PRIOR = BASE / 'basf-incorporation/attempt-003'
PLAN = 'docs/plans/prospectus-basf-oci-note-2026-10-15.md'


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def bindings():
    assert not (HERE / 'outputs.json').exists()
    ad = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    for name in ('source-methods.json', 'protected-inputs.json'):
        if (HERE / name).exists():
            assert all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items())
    return ad


def prepare():
    protected = {str((PRIOR / p).relative_to(ROOT)): h for p, h in read(PRIOR / 'outputs.json').items()}
    protected[str((PRIOR / 'outputs.json').relative_to(ROOT))] = file_hash(PRIOR / 'outputs.json')
    assert all(file_hash(ROOT / p) == h for p, h in protected.items())
    save('protected-inputs.json', protected)
    names = [Path(__file__), ROOT / PLAN, HERE / 'EXECUTION-AUDIT.md', Path(process_ledger.__file__)]
    save('source-methods.json', {str(p.relative_to(ROOT)): file_hash(p) for p in names})
    for p in names:
        target = HERE / 'source-methods' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    shutil.copyfile(PRIOR / 'products.json.gz', HERE / 'products.json.gz')
    p = load(HERE / 'products.json.gz')
    doc = next(d for d in p['P1']['payload']['request']['bundle']['documents'] if d['id'] == 'basf-annual-2022-exchange')
    assert file_hash(ROOT / doc['path']) == doc['sha256']
    save('original-source.json', doc)
    units = [u for u in p['P1']['payload']['graph']['units'] if u['document'] == doc['id'] and u['page'] == 256]
    assert len(units) == 59
    save('page256-units.json', units)
    renderer = Path(shutil.which('pdftoppm')).resolve(strict=True)
    save('renderer.json', {'path': str(renderer), 'sha256': file_hash(renderer)})
    process_ledger.create(HERE / 'native-ledger.json', 1, 77, 'One original annual2022 page256 render;no extraction/OCR')
    process_ledger.create(HERE / 'command-ledger.json', 5, 0, 'Render,build,install,replay;one repair spare')
    return {'source_occurrences': len(units), 'protected_prior': str(PRIOR.relative_to(ROOT))}


def render():
    assert read(HERE / 'invocations/prepare/result.json')['status'] == 'PASS'
    renderer, doc = read(HERE / 'renderer.json'), read(HERE / 'original-source.json')
    assert file_hash(Path(renderer['path'])) == renderer['sha256']
    assert file_hash(ROOT / doc['path']) == doc['sha256']
    target = HERE / 'page256.png'
    assert not target.exists()
    argv = [renderer['path'], '-f', '256', '-l', '256', '-singlefile', '-scale-to', '1800',
            '-png', str(ROOT / doc['path']), str(target.with_suffix(''))]
    folder = HERE / 'commands/render'
    folder.mkdir(parents=True, exist_ok=False)
    save('commands/render/started.json', {'argv': argv, 'timeout': 110, 'cpu_gpu': 'CPU only'})
    tick = time.monotonic()
    with (folder / 'stdout').open('xb') as out, (folder / 'stderr').open('xb') as err:
        with process_ledger.observe(HERE / 'command-ledger.json'), process_ledger.observe(HERE / 'native-ledger.json'):
            result = subprocess.run(argv, stdout=out, stderr=err, timeout=110,
                                    env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
    save('commands/render/result.json', {'returncode': result.returncode, 'wall_seconds': time.monotonic() - tick})
    assert result.returncode == 0
    save('rendered-source.json', {'document': doc['id'], 'path': doc['path'], 'sha256': doc['sha256'],
        'page': 256, 'image_path': str(target.relative_to(ROOT)), 'image_sha256': file_hash(target),
        'renderer': renderer, 'native_render_reservations': 1, 'native_extractions': 0,
        'historical_visible_native_reservation_lower_bound': 78, 'source_http_lower_bound': 9})
    return {'rendered_pages': 1, 'source_occurrences': 59, 'new_native_render': 1, 'http_calls': 0}


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'render'}
    ad = bindings()
    if stage == 'render':
        assert read(HERE / 'invocations/prepare/result.json')['status'] == 'PASS'
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_basf_oci_source', stage],
        'git_commit': ad['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'random_seeds': 'N/A deterministic',
        'cpu_gpu': 'CPU only;child CUDA_VISIBLE_DEVICES=-1'})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second source-stage limit;no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        details = globals()[stage]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 500 * 1024 * 1024
        result = {'status': 'PASS', 'stage': stage, 'details': details,
                  'wall_seconds': time.monotonic() - tick, 'retained_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
            'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
