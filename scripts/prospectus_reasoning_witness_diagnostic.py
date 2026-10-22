"""Bounded retained diagnosis of nonunique within-process Z3 evidence."""
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.prospectus_calendar_evidence import load, save
from scripts.prospectus_solver_corpus_v2 import run, check_record, require
from scripts.prospectus_reasoning_acceptance_evidence import FIXTURE
from legalmath.prospectus.execution_authority import REL, write

REVIEW = REL + '/reviews/reasoning-witness-repair-263'


def changes(a, b, path=()):
    if type(a) is not type(b):
        return [{'path': list(path), 'before': a, 'after': b}]
    if isinstance(a, dict):
        if a.keys() != b.keys(): return [{'path': list(path), 'keys_changed': True}]
        return [r for k in a for r in changes(a[k], b[k], (*path, k))]
    if isinstance(a, list):
        if len(a) != len(b): return [{'path': list(path), 'length_changed': True}]
        return [r for i, (x, y) in enumerate(zip(a, b)) for r in changes(x, y, (*path, i))]
    return [] if a == b else [{'path': list(path), 'before': a, 'after': b}]


def main():
    tick = time.monotonic(); folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'before').mkdir()
    for name in ('scripts/prospectus_reasoning_acceptance.py', 'scripts/prospectus_reasoning_acceptance_evidence.py',
                 'scripts/prospectus_reasoning_type_repair.py', 'tests/prospectus/test_reasoning_acceptance.py'):
        shutil.copyfile(ROOT / name, folder / 'before' / Path(name).name)
    baseline = load(ROOT / REL / 'attempts/reasoning-corpus/attempt-010/source/solver-record.json.gz')
    rows = []
    for i in range(3):
        actual = run(ROOT, ROOT / FIXTURE)
        check = check_record(actual)
        diff = changes(baseline, actual)
        save(folder / ('replay-' + str(i) + '.json.gz'), actual)
        rows.append({'run': i, 'checks': check, 'changes': diff})
        require(time.monotonic() - tick < 60, 'Witness diagnostic time ceiling')
    write(folder / 'diagnostic.json', {'seconds': time.monotonic() - tick, 'runs': rows,
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_witness_diagnostic']}, exclusive=True)
    require(sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()) < 8 * 1024**2, 'Diagnostic storage ceiling')
    print(json.dumps({'runs': [{'run': r['run'], 'changes': len(r['changes']),
        'paths': [c['path'] for c in r['changes'][:8]]} for r in rows]}))


if __name__ == '__main__':
    main()
