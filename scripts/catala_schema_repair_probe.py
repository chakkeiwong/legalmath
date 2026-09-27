#!/usr/bin/env python3
"""One exposed format-repair probe: at most one generation and one critic."""
from pathlib import Path
import subprocess
import sys
import time
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.catala.native.converter import convert
from legalmath.catala.native.runtime import verify_cases
from legalmath.interpretation.search.providers import Allowance, CodexProvider, verify_allowance_checkpoint
from scripts.catala_gap_study import ROOT, LEDGER, Recorded, inputs, JDK, TOOLCHAIN


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def main():
    started = time.monotonic()
    out = ROOT / 'artifacts/catala/gap-closure/schema-repair-probe'
    out.mkdir(parents=True, exist_ok=False)
    historical = loads((out.parent / 'study/freeze.json').read_bytes())
    verify_allowance_checkpoint(LEDGER, historical['checkpoint_hash'])
    balance = loads(LEDGER.read_bytes()); ceiling = historical['ceiling']
    if min(balance['maximum'], ceiling) - len(balance['calls']) < 2:
        write(out / 'result.json', {'status': 'SKIPPED_BUDGET', 'ceiling': ceiling})
        return
    packet = loads((out.parent / 'source-review-successor/packet.json').read_bytes())
    row = next(r for r in packet['corpus'] if r['task']['task_id'].endswith('.netassets'))
    files = {**inputs(), str(Path(__file__).relative_to(ROOT)): raw_digest(Path(__file__).read_bytes())}
    freeze = {'task_hash': digest(row['task']), 'private_reference_hash': digest(row['cases']),
              'source_packet_hash': digest(packet), 'inputs': files,
              'shared_start': len(balance['calls']), 'maximum_dispatches': 2, 'ceiling': ceiling,
              'criterion': 'Executable generation, source critic SUPPORTED, and exact hidden references pass.',
              'nonclaims': 'Exposed debugging task; no superiority, generalization or legal adjudication.',
              'plan': 'docs/implementation/catala/gap-closure/post-run-repair.md'}
    write(out / 'freeze.json', freeze)
    write(out / 'private-reference.json', row)
    for name in files:
        path = out / 'reviewed-sources' / name
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / name).read_bytes())
    provider = Recorded(CodexProvider(allowance=Allowance(LEDGER, 500, reservation_ceiling=ceiling)), out / 'calls', 2)
    state = convert(row['task'], out / 'conversion', provider, JDK, **TOOLCHAIN, max_revisions=0)
    result = {'status': state['status'], 'conversion': state, 'ranking': 'UNSUPPORTED'}
    if state['status'] == 'READY_FOR_BEHAVIOR_CHECK':
        report = verify_cases(out / 'conversion' / state['build_directory'], row['cases'], JDK, compiler=TOOLCHAIN['compiler'])
        write(out / 'verification.json', report)
        result.update(status='PASS', cases=report['passed'], verification_hash=digest(report))
    result.update(dispatches=len(list((out / 'calls').glob('*.request.json'))),
                  shared_end=len(loads(LEDGER.read_bytes())['calls']))
    write(out / 'result.json', result)
    write(out / 'run-manifest.json', {
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': sys.argv, 'python': sys.executable, 'jdk': str(JDK),
        'CPU_GPU': 'CPU; no GPU libraries', 'seed': 'N/A unseeded model diagnostic',
        'wall_ms': int((time.monotonic() - started) * 1000), 'data_version': digest(row),
        'freeze_hash': digest(freeze), 'plan': freeze['plan'], 'result': 'result.json', 'result_hash': digest(result)})
    print(result['status'], result['dispatches'], 'dispatches', flush=True)


if __name__ == '__main__':
    main()
