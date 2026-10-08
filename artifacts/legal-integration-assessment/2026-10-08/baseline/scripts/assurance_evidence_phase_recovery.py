"""Reviewed dependency repair for independent historical source tasks."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

from legalmath.canonical import raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run

ROOT = Path('/home/chakwong/python/legalmath')
SAVED = ROOT/run.RUN/'engineering-repairs/revision-02/frozen/scripts/assurance_evidence_maintenance.py'
SPEC = importlib.util.spec_from_file_location('assurance_prior_maintenance', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def report(root):
    rows = run.task_rows(root)
    return {'calls_used': run.Allowance(root).verify()['used'], 'state': run.state(root),
            'accepted_readings': sum(len(r['value'].get('reading_updates', [])) for r in run.accepted_rows(root)),
            'recent_results': [{k: row[k] for k in ('task', 'attempt', 'status', 'error', 'details', 'allowance_slot') if k in row}
                               for row in rows[-8:]],
            'current_stop': c.read(root/run.RUN/'current-stop.json') if (root/run.RUN/'current-stop.json').exists() else None}


def repair(root):
    run.verify(root)
    if run.Allowance(root).verify()['used'] != 47:
        c.fail('E_AUTHORITY', 'Independent-scope dependency repair is bound to the 47-call checkpoint')
    code = root/'scripts/assurance_evidence_continuation.py'
    replace = PRIOR.replace
    replace(code, 'if status["phases"].get(p, {}).get("status") != "COMPLETED"',
            'if status["phases"].get(p, {}).get("status") not in ("COMPLETED", "COMPLETED_WITH_OPEN_TASKS")')
    replace(code, 'if current["phases"].get(phase, {}).get("status") == "COMPLETED":',
            'if current["phases"].get(phase, {}).get("status") in ("COMPLETED", "COMPLETED_WITH_OPEN_TASKS"):')
    replace(code, '        if any(r["status"] != "VALIDATED" for r in final_rows):',
            '        if any(r["status"] != "VALIDATED" for r in final_rows) and not all(t["phase"] == "scope" for t in batch):')
    replace(code, '    current["phases"][phase] = {"status": "COMPLETED", "result": c.receipt(work/"phase-result.json", root)}',
            '    current["phases"][phase] = {"status": data.get("status", "COMPLETED"), "result": c.receipt(work/"phase-result.json", root)}')
    replace(code, '            data = {"tasks": [t["id"] for t in scheduled]}',
            '''            accepted_ids = {r["task"] for r in accepted_rows(root)}
            unaccepted = [t["id"] for t in scheduled if t["id"] not in accepted_ids]
            data = {"tasks": [t["id"] for t in scheduled], "unaccepted_tasks": unaccepted,
                    "status": "COMPLETED_WITH_OPEN_TASKS" if phase == "scope" and unaccepted else "COMPLETED"}''')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_failed_historical_scope_does_not_block_unrelated_readings' not in tests.read_text():
        tests.write_text(tests.read_text()+'''

def test_failed_historical_scope_does_not_block_unrelated_readings(root, monkeypatch):
    monkeypatch.setattr(run, "attempt", lambda *a, **kw: {"status": "FAILED", "error": "E_SCHEMA", "allowance_slot": None})
    assert run.run_tasks(root, [task(0, "scope"), task(1, "scope")])
    run.phase_done(root, "pilot", {"tasks": ["pair"]})
    run.phase_done(root, "scope", {"status": "COMPLETED_WITH_OPEN_TASKS", "unaccepted_tasks": ["historical"]})
    assert run.state(root)["phases"]["scope"]["status"] == "COMPLETED_WITH_OPEN_TASKS"
    assert c.read(root/run.RUN/"next-phase-plan.json")["next_phase"] == "propagation"
''')
    work = root/run.RUN
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.write_text(directory/'dependency-audit.md', '''# Dependency audit before execution

The failed mixed-gift scope correction belongs to an independent historical
source family and is excluded from the current circular's propagation inputs.
Blocking that work after a schema failure or one upstream outage is a wrong
dependency, not a source-validity veto for the current-circular readings.
Complete remaining historical attempts within unchanged issue limits and mark
the phase COMPLETED_WITH_OPEN_TASKS if any remain unaccepted. Never call it a
successful correction. Propagation still requires all 70 accepted reading
dispositions before checks and final review. Two consecutive provider failures
still halt dispatch. Original quotas, sources, prior failed calls and receipts
remain unchanged. This repair permits only independent work and establishes no
legal conclusion. Tests verify the distinct phase status and next-phase action.
''')
    frozen = directory/'frozen'
    hashes = c.code_material(root)
    hashes['pyproject.toml'] = raw_digest((root/'pyproject.toml').read_bytes())
    for name in hashes:
        target = frozen/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    with (directory/'tests.log').open('w') as stream:
        result = subprocess.run([str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *run.TESTS], cwd=frozen,
            env={**os.environ, 'PYTHONPATH': str(frozen/'src')+os.pathsep+str(frozen/'scripts'),
                 'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_VISIBLE_DEVICES': '-1'},
            stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    record = {'status': 'REPAIR_VALIDATED' if result.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('pre-repair-state.json', 'dependency-audit.md', 'tests.log')],
        'calls_used': run.Allowance(root).verify()['used'], 'provider_calls': 0}
    c.save(directory/'repair-result.json', record)
    if record['status'] != 'REPAIR_VALIDATED':
        c.fail('E_INTEGRITY', 'Dependency repair tests failed')
    c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
    current = run.state(root)
    current['halt'] = None
    current['repair_reason'] = 'Independent historical source correction retained as unresolved; unrelated current-source reviews may proceed.'
    c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root))}
