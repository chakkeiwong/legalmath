"""Original compact assessment with separately retained native process accounting."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import service, process_ledger
from legalmath.prospectus.successor.contracts import read


def evaluate(output):
    result = {}
    for name in ('portuguese', 'correction'):
        case = ROOT / 'docs/implementation/prospectus-integration-closure/inputs/R0/cases' / name
        try:
            result[name] = {'report': service.assess(read(case / 'request.json'), case)}
        except (ValueError, FileNotFoundError) as exc:
            result[name] = {'error': type(exc).__name__ + ': ' + str(exc)}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with Path(output).open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def commands(root, state):
    if state == 'model-missing':
        return []
    source = root / 'docs/implementation/prospectus-integration-closure/inputs/R0/cases/portuguese/source.pdf'
    return [['pdftotext', '-bbox-layout', '-enc', 'UTF-8', str(source), '-'],
            ['/home/chakwong/miniconda3/envs/tfgpu/bin/python',
             str(root / 'src/legalmath/prospectus/successor/ocr_worker.py')]]


def counted_evaluate(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    state = read(ROOT / 'docs/implementation/prospectus-integration-closure/inputs/R0/recovery.json')['state']
    allowed = commands(ROOT, state)
    ledger = output.with_name(output.name + '.processes.json')
    process_ledger.create(ledger, 2, 0,
        'Incremental current probe only; prior recovery call count UNKNOWN; not a cumulative reset')
    with process_ledger.observe(ledger):
        counted = subprocess.Popen
        position = 0
        def exact(*args, **kwargs):
            nonlocal position
            argv = args[0] if args else kwargs.get('args')
            if position >= len(allowed) or argv != allowed[position] or kwargs.get('shell'):
                raise RuntimeError('Unreviewed recovery probe subprocess')
            position += 1
            return counted(*args, **kwargs)
        subprocess.Popen = exact
        try:
            evaluate(output)
        finally:
            subprocess.Popen = counted
    rows = process_ledger.checked(ledger)['reservations']
    if position != len(allowed) or [r['argv'] for r in rows] != allowed or any(r['state'] != 'STARTED' for r in rows):
        raise ValueError('Incomplete recovery probe process accounting')


def test_actual_consumers(pytestconfig):
    counted_evaluate(Path(pytestconfig.option.xmlpath).with_name('assessment.json'))


if __name__ == '__main__':
    counted_evaluate(Path(sys.argv[1]))
