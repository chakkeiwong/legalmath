"""Bounded source preparation for the original annual accounting-note reading."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
SOURCE = AUTH / 'attempts/source-bes-dep-09'
WORK = ROOT / '.localresources/prospectus-preparation/annual-basis'
PLAN = 'docs/plans/prospectus-annual-basis-estimates-2026-10-22.md'
PDF = ROOT / 'docs/implementation/prospectus-integration-closure/bes-original-acquisition/attempt-001/bes-2010-en.pdf'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2).encode()
    if path.suffix == '.gz':
        data = gzip.compress(data, mtime=0)
    with path.open('xb') as stream:
        stream.write(data)


def prepare():
    started = time.monotonic()
    assert not WORK.exists(), 'No unchanged preparation retry'
    assert read(AUTH / 'program.json')['revision'] == 439
    post = read(AUTH / 'reviews/english-applicability-439/post-record.json')
    event = post['event']
    assert event['kind'] == 'RECORD' and sha(SOURCE / 'attempt-015/outputs.json') == event['outputs_sha256']
    assert all(sha(SOURCE / 'attempt-015' / p) == h for p, h in read(SOURCE / 'attempt-015/outputs.json').items())
    p1 = SOURCE / 'attempt-002/original-P1.json.gz'
    reference = read(SOURCE / 'attempt-003/candidate-P1-reference.json.gz')
    assert sha(p1) == reference['file_sha256']
    assert sha(PDF) == 'f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'
    graph = read(p1)['payload']['graph']
    selected = [u for u in graph['units'] if u['document'] == 'bes-2010-en' and u['page'] in (103, 114, 115, 184, 185, 186)]
    assert {u['page'] for u in selected} == {103, 114, 115, 184, 185, 186}
    save(WORK / 'source-units.json.gz', selected)
    prior = post['costs']['cumulative_charged_seconds']
    prior += read(AUTH / 'reviews/annual-note-roadmap-439/index.json')['seconds']
    save(WORK / 'preparation.json', {'status': 'PREPARED', 'source': str(p1.relative_to(ROOT)),
        'source_sha256': sha(p1), 'pdf': str(PDF.relative_to(ROOT)), 'pdf_sha256': sha(PDF),
        'prior_record': event['sha256'], 'prior_charged_seconds': prior,
        'prior_bytes': post['costs']['cumulative_bytes'], 'previous_substantive_ceiling_seconds': 1960,
        'reviewed_substantive_ceiling_seconds': 2560, 'new_seconds': 600, 'new_bytes': 128 * 1024**2,
        'cumulative_bytes_limit': 448 * 1024**2, 'plan': PLAN, 'plan_sha256': sha(ROOT / PLAN),
        'method_sha256': sha(Path(__file__)), 'seconds': time.monotonic() - started,
        'cpu_gpu': 'CPU_ONLY; no GPU imports', 'seeds': 'N/A deterministic',
        'command': '.venv/bin/python -B -m scripts.prospectus_annual_basis_source prepare'})
    return {'status': 'PREPARED', 'source_units': len(selected), 'seconds': time.monotonic() - started}


def render(page):
    assert page in (115, 185)
    assert read(WORK / 'preparation.json')['pdf_sha256'] == sha(PDF)
    binary = shutil.which('pdftoppm')
    assert binary is not None, 'Existing pdftoppm required; no installation authorized by this command'
    prefix = WORK / ('page-' + str(page))
    logpath = WORK / ('render-' + str(page) + '.log')
    assert not Path(str(prefix) + '.png').exists() and not logpath.exists(), 'No render retry'
    argv = [binary, '-f', str(page), '-l', str(page), '-scale-to', '2000', '-singlefile', '-png', str(PDF), str(prefix)]
    start = time.monotonic()
    with logpath.open('x') as log:
        result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=10,
                                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
    image = Path(str(prefix) + '.png')
    save(WORK / ('render-' + str(page) + '.json'), {'argv': argv, 'exit_code': result.returncode,
        'seconds': time.monotonic() - start, 'renderer_sha256': sha(Path(binary)),
        'image_sha256': sha(image) if image.is_file() else None, 'source_sha256': sha(PDF),
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    assert result.returncode == 0 and image.is_file()
    return {'status': 'RENDERED', 'page': page, 'image': str(image.relative_to(ROOT))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'render'])
    parser.add_argument('--page', type=int)
    args = parser.parse_args()
    print(json.dumps(prepare() if args.action == 'prepare' else render(args.page)))
