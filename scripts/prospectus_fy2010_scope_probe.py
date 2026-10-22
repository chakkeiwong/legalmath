"""One bounded actual-consumer probe of FY2010 incorporation coverage."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts import prospectus_fy2010_product as fy
from legalmath.prospectus.execution_authority import Authority, file_hash
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

OUT = ROOT / '.localresources/prospectus-preparation/fy2010-scope/probe'
OLD = fy.BASE / 'attempts/source-bes-dep-08/attempt-006'
PLAN = 'docs/plans/prospectus-fy2010-scope-reconciliation-2026-10-22.md'


def save(name, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode()
    if name.endswith('.gz'):
        raw = gzip.compress(raw, compresslevel=1, mtime=0)
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    if size + len(raw) > 32 * 1024**2:
        raise ValueError('Probe32MiB ceiling')
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def main():
    tick = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=False)
    a = Authority(ROOT)
    program, _, _ = a.spec()
    if program['revision'] != 435:
        raise ValueError('Expected reviewed435baseline')
    event = next(e for e in reversed(a.events()) if e.get('attempt') == str(OLD.relative_to(ROOT))
                 and e['kind'] in {'RECORD', 'ACCEPT'})
    if not a.retained_evidence_valid(event):
        raise ValueError('Original006evidence changed')
    save('manifest.json', {'command': [sys.executable, '-B', '-m', 'scripts.prospectus_fy2010_scope_probe'],
         'plan': PLAN, 'revision': 435, 'original_event_sha256': event['sha256'],
         'git_commit': fy.read(OLD / 'admission.json')['git_commit'],
         'git_commit_role': 'Retained006baseline; current method hashes listed separately',
         'environment': {'executable': sys.executable, 'python': sys.version},
         'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic',
         'methods': fy.methods(), 'seconds_ceiling': 60, 'bytes_ceiling': 32 * 1024**2})
    ps = fy.load_products(OLD, 'after')
    before = service.consume(ps, ROOT, mode='frozen', include_artifacts=True)
    save('baseline-answer.json.gz', before)
    if before != fy.read(OLD / 'after-answer.json.gz'):
        raise ValueError('Original complete006answer changed')
    supplied = deepcopy(ps['P3']['payload']['interpretation_input'])
    row = supplied['reference_admission']['references'][0]
    removed = row['targets'].pop()
    save('omission-input.json.gz', supplied)
    revised = fy.products(ps['P1'], supplied)
    answer = service.consume(revised, ROOT, mode='frozen', include_artifacts=True)
    save('omission-answer.json.gz', answer)
    dep = next(d for d in answer['dependencies'] if d['id'] == 'reviewed-reference:' + row['id'])
    original = next(d for d in before['dependencies'] if d['id'] == dep['id'])
    result = {'status': 'REPRODUCED' if dep['status'] == 'RESOLVED' and len(dep['targets']) == 299 else 'NOT_REPRODUCED',
              'baseline_targets': len(original['targets']), 'altered_targets': len(dep['targets']),
              'altered_status': dep['status'], 'removed': removed,
              'scope_check_present': 'statement_scope_check' in dep,
              'complete_baseline_preserved': True, 'cells_unchanged': answer['source_statement_cells'] == before['source_statement_cells'],
              'original_obligations': {d['id']: d['status'] for d in answer['dependencies'] if d['id'].startswith('BES-DEP-')},
              'q3': answer['questions']['Q3']['status'], 'may_execute_transaction': answer['may_execute_transaction'],
              'independent_legal_acceptance': answer['independent_legal_acceptance'],
              'seconds': time.monotonic() - tick, 'answer_sha256': digest(answer),
              'code_sha256': file_hash(Path(__file__))}
    save('result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'baseline_targets', 'altered_targets', 'altered_status', 'seconds')}), flush=True)


if __name__ == '__main__':
    def expire(*_):
        raise TimeoutError('FY2010scope probe60seconds')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(60)
    tick = time.monotonic()
    try:
        main()
    except Exception as exc:
        if OUT.is_dir():
            save('failure.json', {'type': type(exc).__name__, 'message': str(exc), 'seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
