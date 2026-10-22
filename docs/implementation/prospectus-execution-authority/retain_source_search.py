"""Retain bounded unresolved-source searches and verify existing consumer evidence."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = (ROOT / sys.argv[1]).resolve()
assert HERE.is_relative_to(Path(__file__).resolve().parent / 'attempts')
started = time.monotonic()


def read(name):
    return json.loads((HERE / name).read_text())


def h(path):
    return sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


review = read('search-review.json')
admission = read('admission.json')
assert review['task'] == admission['task'] and not review['source_recovered']
assert (HERE / 'RESULT.md').is_file() and (HERE / 'WORK-PLAN.md').is_file()
network = []
for r in review['requests']:
    headers = (HERE / r['headers']).read_text()
    assert '200 OK' in headers
    data = read(r['body'])
    assert isinstance(data['response_items'], list)
    argv = ['curl', '--fail', '--location', '--max-time', '25', '--max-filesize', '2097152',
            '--silent', '--show-error', '--dump-header', str((HERE / r['headers']).relative_to(ROOT)),
            '--output', str((HERE / r['body']).relative_to(ROOT)), '--write-out', '%{http_code} %{size_download} %{time_total}\n', r['url']]
    network.append({**r, 'argv': argv, 'http_status': 200, 'curl_exit_code': 0,
                    'body_sha256': h(HERE / r['body']), 'headers_sha256': h(HERE / r['headers']),
                    'returned_items': len(data['response_items']), 'bytes': (HERE / r['body']).stat().st_size,
                    'candidate_evidence': [{k: v.get(k) for k in ('title', 'snippet', 'originalURL', 'tstamp', 'linkToOriginalFile')} for v in data['response_items']]})
save('network.json', {'requests': network, 'original_content_downloads': 0, 'scope': 'Bounded archive queries only; not exhaustive internet coverage'})
helper_path = HERE.parents[1] / 'source-bes-dep-02/attempt-001/verify_retained.py'
spec = importlib.util.spec_from_file_location('retained_source_consumer', helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
reuse = helper.verify(review['dependency'])
save('reuse-result.json', reuse)
save('result.json', {'task': review['task'], 'status': 'PASS', 'task_complete': False,
    'meaning_of_status': 'Bounded source search retained and unchanged unresolved consumer verified; original source not recovered',
    'source_recovered': False, 'actual_downstream': 'reuse-result.json', 'source_review': 'search-review.json',
    'acceptance_blockers': [review['decision'], 'Original identity, historical authority and independent legal acceptance remain unresolved'],
    'next_source_route': review['next_source_route'], 'next_action': 'Continue independent ' + review['next_task'], 'result_note': 'RESULT.md'})
save('run-manifest.json', {'git_commit': admission['git_commit'],
    'command': 'timeout 120 .venv/bin/python ' + str(Path(__file__).resolve().relative_to(ROOT)) + ' ' + str(HERE.relative_to(ROOT)),
    'environment': '.venv; retained helper pins worktree src', 'cpu_gpu': 'CPU only; GPU intentionally hidden before imports',
    'random_seeds': 'N/A; deterministic verification', 'wall_seconds': time.monotonic() - started,
    'completed_utc': datetime.now(timezone.utc).isoformat(), 'data_version': reuse['outputs_sha256'],
    'bindings': {str(p.relative_to(ROOT)): h(p) for p in (Path(__file__).resolve(), helper_path)},
    'plan': 'WORK-PLAN.md', 'result': 'RESULT.md', 'artifact_paths': ['network.json', 'reuse-result.json', 'search-review.json']})
outputs = {str(p.relative_to(HERE)): h(p) for p in sorted(HERE.rglob('*')) if p.is_file()
           and p.name not in {'admission.json', 'outputs.json'} and '__pycache__' not in p.parts}
save('outputs.json', outputs)
print(json.dumps({'task': review['task'], 'status': 'PASS', 'task_complete': False, 'sealed_files': len(outputs), 'next_task': review['next_task']}))
