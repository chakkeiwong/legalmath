"""One finite closure pass after the reviewed optional geometry repair."""
import argparse
from pathlib import Path
import time
from scripts.prospectus_geometry_program import ROOT, HERE, read, verify, write
from legalmath.prospectus.successor import closure_program as controller


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for stage in ('focused', 'consumer', 'matched'):
        folder = sorted((HERE / stage).glob('attempt-*/result.json'))[-1].parent
        verify(folder)
        if read(folder / 'result.json')['status'] != 'PASS':
            raise ValueError('Prerequisite did not pass: ' + stage)
    from scripts.prospectus_closure_attribution import report
    report(ROOT)
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    attempted = []
    for _ in range(9):
        state = controller.refresh(ROOT)
        write(args.output / 'status.json', state)
        ready = [r for r in state['phases'] if r['can_dispatch'] and not r['current'] and r['phase'] not in attempted]
        if not ready:
            break
        phase = ready[0]['phase']
        attempted.append(phase)
        write(args.output / 'progress.json', {'running':phase,'attempted':attempted})
        print('Starting ' + phase, flush=True)
        result = controller.execute(ROOT, phase)
        write(args.output / (phase + '.json'), result)
        print(phase + ' ' + str(result.get('engineering_checks',result.get('execution'))), flush=True)
    state = controller.refresh(ROOT)
    write(args.output / 'status.json', state)
    passed = all(r['current'] and r['engineering_checks']=='PASS' for r in state['phases'])
    write(args.output / 'result.json', {'status':'PASS' if passed else 'INCOMPLETE_OR_FAILED',
        'wall_seconds':time.monotonic()-start,'attempted':attempted,'legal_acceptance':'NOT_ESTABLISHED'})
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
