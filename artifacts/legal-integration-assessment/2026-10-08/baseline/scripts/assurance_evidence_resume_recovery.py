"""Fixed restart repair: reuse existing accepted correction at its quota limit."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from legalmath.canonical import raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run

ROOT = Path('/home/chakwong/python/legalmath')
SAVED = ROOT/run.RUN/'engineering-repairs/revision-05/frozen/scripts/assurance_evidence_schema_recovery.py'
SPEC = importlib.util.spec_from_file_location('assurance_prior_schema_recovery', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
report = PRIOR.report


def repair(root):
    run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 66:
        c.fail('E_AUTHORITY', 'Restart repair is bound to the 66-call checkpoint')
    code = root/'scripts/assurance_evidence_continuation.py'
    PRIOR.PRIOR.replace(code,
        '                if all(spending.get(issue, 0) < 2 for issue in task["issues"]):',
        '                if (root/RUN/"tasks"/task["id"]/"attempt-02/result.json").exists() or all(spending.get(issue, 0) < 2 for issue in task["issues"]):')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_existing_correction_reused_after_issue_quota_exhausted' not in tests.read_text():
        tests.write_text(tests.read_text()+'''

def test_existing_correction_reused_after_issue_quota_exhausted(root, monkeypatch):
    t = task()
    run.Allowance(root, t).reserve("a"*64)
    run.Allowance(root, t, correction=True).reserve("b"*64)
    c.save(root/run.RUN/"tasks"/t["id"]/"attempt-02/result.json", {})
    calls = []
    def replay(root, task, number=1, **kw):
        calls.append(number)
        return {"status": "FAILED", "error": "E_SCHEMA", "allowance_slot": 41} if number == 1 else {"status": "VALIDATED", "allowance_slot": 42}
    monkeypatch.setattr(run, "attempt", replay)
    monkeypatch.setattr(run, "refresh", lambda *args: None)
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 0)
    assert run.run_tasks(root, [t])
    assert calls == [1, 2]
    assert run.Allowance(root).verify()["used"] == 42
''')
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.write_text(directory/'plan-and-audit.md', '''# Restart correction reuse

An already counted second attempt must remain replayable after the per-issue
quota reaches two. The old guard incorrectly used the spending limit to block
offline reuse. Permit the second-attempt path when its saved result exists;
attempt() still verifies exact task, request, schema, provider bytes and receipt
before accepting it. No new dispatch is authorized by this condition, and the
allowance still blocks any unsaved third attempt. Test exhausted-quota replay
and execute the actual saved task with a provider factory that forbids calls.
This is an engineering repair with no change to scientific acceptance or budget.
''')
    frozen = directory/'frozen'
    hashes = c.code_material(root)
    hashes['pyproject.toml'] = raw_digest((root/'pyproject.toml').read_bytes())
    for name in hashes:
        target = frozen/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    env = {**os.environ, 'PYTHONPATH': str(frozen/'src')+os.pathsep+str(frozen/'scripts'),
           'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_VISIBLE_DEVICES': '-1'}
    with (directory/'tests.log').open('w') as stream:
        test_result = subprocess.run([str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *run.TESTS], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    probe = '''from pathlib import Path
import assurance_evidence_continuation as r
import assurance_evidence_core as c
root=Path('/home/chakwong/python/legalmath')
t=next(t for t in c.read(root/r.RUN/'initial-tasks.json') if t['id']=='propagation.structure-reader.57600220ca583138052e970c')
prior=r.Allowance(root).verify()['used']
saved=r.attempt
def forbid(**kwargs):
    raise AssertionError('Offline replay attempted a provider call')
def replay(*args,**kwargs):
    return saved(*args,**kwargs,provider_factory=forbid)
r.attempt=replay
assert r.run_tasks(root,[t])
assert r.Allowance(root).verify()['used']==prior
print('Exact saved correction reused; provider calls zero; used',prior)
'''
    with (directory/'restart-replay.log').open('w') as stream:
        replay = subprocess.run([str(root/'.venv/bin/python'), '-c', probe], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    record = {'status': 'REPAIR_VALIDATED' if test_result.returncode == replay.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('plan-and-audit.md', 'tests.log', 'restart-replay.log')],
        'provider_calls': 0, 'calls_used': run.Allowance(root).verify()['used']}
    c.save(directory/'repair-result.json', record)
    if record['status'] == 'REPAIR_VALIDATED':
        c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-2500:], 'replay': (directory/'restart-replay.log').read_text()[-2500:]}
