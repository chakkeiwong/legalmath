"""One bounded retained-source slice for remaining annual policies and events."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prospectus_annual_basis_source import AUTH, SOURCE, read, save, sha

WORK = ROOT / '.localresources/prospectus-preparation/annual-policies'
PLAN = 'docs/plans/prospectus-annual-policy-source-review-2026-10-22.md'


def main():
    start = time.monotonic()
    assert not WORK.exists(), 'No unchanged source-slice retry'
    post = read(AUTH / 'reviews/annual-basis-440/post-record.json')
    assert read(AUTH / 'program.json')['revision'] == 440
    assert post['event']['kind'] == 'RECORD' and post['retained_evidence_valid']
    old = SOURCE / 'attempt-016'
    assert sha(old / 'outputs.json') == post['event']['outputs_sha256']
    assert all(sha(old / p) == h for p, h in read(old / 'outputs.json').items())
    p1 = SOURCE / 'attempt-002/original-P1.json.gz'
    assert sha(p1) == read(SOURCE / 'attempt-003/candidate-P1-reference.json.gz')['file_sha256']
    selected = [u for u in read(p1)['payload']['graph']['units'] if u['document'] == 'bes-2010-en'
                and (103 <= u['page'] <= 114 or u['page'] == 187)]
    assert {u['page'] for u in selected} == set(range(103, 115)) | {187}
    save(WORK / 'source-units.json.gz', selected)
    text = '\n'.join(u['id'] + ' ' + u['raw'] for u in selected) + '\n'
    with (WORK / 'source.txt').open('x') as stream:
        stream.write(text)
    elapsed = time.monotonic() - start
    measured_bytes = sum(p.stat().st_size for p in WORK.iterdir())
    extra = [ROOT / PLAN, Path(__file__), AUTH / 'continuation-reviews/after-440.json']
    extra_bytes = sum(p.stat().st_size for p in extra if p.exists())
    allowed = (elapsed < 3 and post['costs']['cumulative_charged_seconds'] + elapsed < 2560 and
               measured_bytes + extra_bytes + 8192 < 2 * 1024**2 and
               post['costs']['cumulative_bytes'] + measured_bytes + extra_bytes + 2 * 1024**2 < 448 * 1024**2)
    save(WORK / 'source-review.json', {'status': 'PASS' if allowed else 'BOUND_EXCEEDED',
        'source': str(p1.relative_to(ROOT)), 'source_sha256': sha(p1), 'seconds': elapsed,
        'prior_charged_seconds': post['costs']['cumulative_charged_seconds'],
        'prior_bytes': post['costs']['cumulative_bytes'], 'extra_bytes': extra_bytes,
        'source_units': len(selected), 'plan': PLAN, 'plan_sha256': sha(ROOT / PLAN),
        'method_sha256': sha(Path(__file__)), 'command': sys.argv,
        'cpu_gpu': 'CPU_ONLY; no GPU imports', 'seeds': 'N/A deterministic'})
    assert allowed, 'Retain failed bounded slice; no retry'
    print(json.dumps({'status': 'PASS', 'source_units': len(selected), 'seconds': elapsed,
                      'source': str((WORK / 'source.txt').relative_to(ROOT))}), flush=True)


if __name__ == '__main__':
    main()
