"""Finite assessment-state and evidence-binding repair; no budget extensions."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from scripts.legal_gap_program import ROOT, OUT as PRIOR, read, save, ref, check_ref
from scripts.legal_integration_repair import OUT as PREDECESSOR, budgets

OUT = ROOT / 'artifacts/legal-integration-assessment/2026-10-08'
DOC = ROOT / 'docs/implementation/legal-integration-assessment'
PLAN = ROOT / 'docs/plans/legal-integration-assessment-program.md'
ACTIONS = ('assess-check', 'assess-execute', 'assess-status', 'assess-verify')


def baseline():
    path = OUT / 'baseline.json'
    if path.exists():
        value = read(path)
        for row in value['copies']:
            check_ref(row['copy'])
        return value
    from scripts.legal_integration_repair import verify as verify_predecessor
    checked = verify_predecessor()
    paths = [p for base in ('src/legalmath', 'scripts', 'tests/assurance', 'tests/tooling')
             for p in (ROOT / base).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.json', '.java', '.lean', '.sql')]
    paths += [PLAN, ROOT / 'docs/plans/legal-integration-repair-program.md']
    paths += [p for p in (ROOT / 'docs/implementation/legal-integration-repair').rglob('*') if p.is_file()]
    copies = []
    for p in sorted(set(paths)):
        target = OUT / 'baseline' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        copies.append({'live': ref(p), 'copy': ref(target)})
    mutable = {PRIOR / name for name in ('provider-allowance.json', 'repairs.json', 'provider.lock')}
    receipts = [ref(p) for base in (PRIOR, PREDECESSOR) for p in sorted(base.rglob('*'))
                if p.is_file() and p not in mutable and p.name != '.lock'
                and not p.name.endswith(('-wal', '-shm'))]
    for name in ('provider-allowance.json', 'repairs.json'):
        save(OUT / 'baseline' / name, read(PRIOR / name))
    value = {'captured_at': time.time(), 'predecessor_verification': checked,
             'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'copies': copies, 'predecessor_evidence': receipts, 'budgets': budgets()}
    save(path, value)
    return value


def check():
    value = baseline()
    return {'status': 'BASELINE_PRESERVED', 'files': len(value['copies']),
            'predecessor_files': len(value['predecessor_evidence']), 'budgets': budgets()}


def status():
    return {'state': read(OUT / 'state.json') if (OUT / 'state.json').exists() else 'PREPARED',
            'budgets': budgets()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.action == 'assess-status':
        result = status()
    else:
        with (OUT / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = globals()[args.action.removeprefix('assess-')]()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
