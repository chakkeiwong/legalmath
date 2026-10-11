"""Fixed bounded validation actions; no candidate worktree edits during a run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
BASE = ROOT/'docs/implementation/prospectus-integration-closure'
PLAN = 'docs/plans/prospectus-basf-status-pledge-execution-2026-10-10.md'
TEST = 'tests/prospectus_successor/test_closure_basf_status_pledge.py'
ACTIONS = {
    'admission': (600, 'basf-pledge-admission', [TEST+'::test_basf_pledge_admission_rejects_source_or_meaning_mutation']),
    'smoke': (600, 'basf-pledge-smoke', [TEST+'::test_basf_pledge_p3_smoke_and_definition_omission',
                                     TEST+'::test_basf_pledge_unreviewed_definition_cannot_be_operative']),
    'focused': (1500, 'basf-pledge', [
        TEST+'::test_basf_pledge_remaining_real_omissions',
        TEST+'::test_basf_pledge_changed_reviewed_image_rejects_before_assessment',
        TEST+'::test_basf_pledge_downstream_mutation_rejects',
        TEST+'::test_basf_pledge_definition_effect_requires_actual_question_evidence']),
    'aggregate': (4500, 'successor', ['tests/prospectus_successor', 'tests/prospectus/test_closure_mechanisms.py']),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=ACTIONS)
    args = parser.parse_args()
    limit, prefix, tests = ACTIONS[args.action]
    if args.action in {'focused', 'aggregate'}:
        assert 'Measured-bound review' in (ROOT/PLAN).read_text(), 'Review early diagnostics first'
    checks = BASE/'checks'
    number = 1
    while any((checks/f'{prefix}-{number:03d}{suffix}').exists()
              for suffix in ('.xml', '.log', '-manifest.json')):
        number += 1
    name = f'{prefix}-{number:03d}'
    xml, log, manifest = [checks/(name+suffix) for suffix in ('.xml', '.log', '-manifest.json')]
    paths = {*sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py')),
             *sorted((ROOT/'scripts').glob('prospectus_closure_*.py')),
             *sorted((ROOT/'tests/prospectus_successor').glob('*.py')),
             ROOT/'scripts/prospectus_delivery.py', ROOT/PLAN,
             ROOT/'scripts/author_basf_status_pledge_packet.py',
             BASE/'basf-status-pledge/SOURCE-REVIEW.md',
             BASE/'basf-status-pledge/OPTION-COMPARISON-CORRECTION.md',
             *sorted(BASE.glob('basf-*/review.json'))}
    def method():
        return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    before = method()
    command = [str(ROOT/'.venv/bin/python'), '-m', 'scripts.prospectus_delivery',
               '--program', 'closure', 'check', *tests, '--junitxml='+str(xml.relative_to(ROOT))]
    row = dict(command=command, timeout_seconds=limit, method=before,
               git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               environment={'python':sys.executable, 'version':sys.version, 'CUDA_VISIBLE_DEVICES':'-1'},
               cpu_gpu='CPU; GPU intentionally hidden; no probe',
               random_seeds='N/A deterministic controls; aggregate Hypothesis defaults and counterexamples retained',
               data_version='Original BASF editions and reviewed source packets; exact hashes in method',
               plan_file=PLAN, result_file=str(xml.relative_to(ROOT)),
               result_note=str((BASE/'basf-status-pledge/RESULT.md').relative_to(ROOT)),
               driver={'path':str(Path(__file__)), 'sha256':sha(Path(__file__))},
               started_at=datetime.now(timezone.utc).isoformat(), status='RUNNING')
    save(manifest, row)
    tick = time.monotonic()
    try:
        run = subprocess.run(command, cwd=ROOT, env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},
                             capture_output=True, timeout=limit)
        log.write_bytes(run.stdout+run.stderr)
        row['exit_code'] = run.returncode
        if xml.exists():
            row['counts'] = {k:sum(int(s.get(k,0)) for s in ET.parse(xml).getroot().iter('testsuite'))
                             for k in ('tests','failures','errors','skipped')}
            row['result_sha256'] = sha(xml)
        row['method_unchanged'] = before == method()
        counts = row.get('counts', {})
        row['status'] = 'PASS' if (run.returncode == 0 and counts.get('tests',0)>0 and
            not any(counts[k] for k in ('failures','errors','skipped')) and row['method_unchanged']) else 'FAIL'
    except subprocess.TimeoutExpired as exc:
        log.write_bytes((exc.stdout or b'')+(exc.stderr or b''))
        row.update(status='TIMEOUT', error=f'Exceeded {limit}s; review before any retry',
                   method_unchanged=before == method())
    except Exception as exc:
        row.update(status='FAIL', error=type(exc).__name__+': '+str(exc))
    row['wall_seconds'] = time.monotonic()-tick
    save(manifest, row)
    print(json.dumps({k:v for k,v in row.items() if k not in {'method','environment'}}, ensure_ascii=False), flush=True)
    if row['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
