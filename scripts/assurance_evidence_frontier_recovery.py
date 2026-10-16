"""Resume only independent unspent tasks; retain exhausted reviews as an explicit veto."""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from legalmath.canonical import canonical, digest, raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_protocol as protocol

ROOT = Path('/home/chakwong/python/legalmath')
SAVED = ROOT/run.RUN/'engineering-repairs/revision-02/frozen/scripts/assurance_evidence_maintenance.py'
SPEC = importlib.util.spec_from_file_location('assurance_frontier_primitives', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def report(root):
    rows = run.accepted_rows(root)
    value = {'calls_used': run.Allowance(root).verify()['used'], 'allowance': {k:v for k,v in run.Allowance(root).verify().items()
             if k not in ('new_issue_spending', 'combined_issue_spending')}, 'state': run.state(root),
        'accepted_reading_reviews': sum(len(r['value'].get('reading_updates', [])) for r in rows)}
    value['pending_tasks'] = run.unresolved_task_ids(root, [t for t in c.read(root/run.RUN/'initial-tasks.json') if t['phase']=='propagation'])
    return value


def repair(root):
    active = run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 90:
        c.fail('E_AUTHORITY', 'Independent frontier repair requires the 90-call checkpoint')
    if run.consecutive_failures(root) >= 2:
        c.fail('E_DEPENDENCY', 'Two-provider-failure veto cannot be cleared by this repair')
    # Only our own rejected candidate edits are replaced with their validated
    # snapshot. No user files or source material are restored or reconstructed.
    for name in ('scripts/assurance_evidence_protocol.py', 'scripts/assurance_evidence_continuation.py'):
        shutil.copyfile(root/active['frozen_root']/name, root/name)
    controller = root/'scripts/assurance_evidence_continuation.py'
    PRIOR.replace(controller,
        '        if any(r["status"] != "VALIDATED" for r in final_rows) and not all(t["phase"] == "scope" for t in batch):\n            return halt(root, "Pilot or phase has an unaccepted response; dependent phases blocked.")',
        '''        failures = [r for r in final_rows if r["status"] != "VALIDATED"]
        if failures and not all(t["phase"] == "scope" for t in batch):
            by_id = {t["id"]: t for t in batch}
            spending = Allowance(root).verify()["new_issue_spending"]
            independent_exhausted = not pilot and all(
                r["task"] in by_id and by_id[r["task"]]["phase"] == "propagation" and
                all(spending.get(issue, 0) >= 2 for issue in by_id[r["task"]]["issues"])
                for r in failures)
            if not independent_exhausted:
                return halt(root, "Unaccepted response blocks dependent work; no issue limit is reset.")
            c.save(root/RUN/"exhausted-reading-frontier.json", [
                {"task": r["task"], "status": "UNACCEPTED_ATTEMPTS_EXHAUSTED", "receipt": r.get("receipt")}
                for r in failures])
            refresh(root, "Exhausted reading reviews stay unaccepted; independent undispatched reviews may continue")''')
    PRIOR.replace(controller,
        '    tasks = c.read(root/RUN/"initial-tasks.json")\n    propagation = [t for t in tasks if t["phase"] == "propagation"]',
        '''    tasks = c.read(root/RUN/"initial-tasks.json")
    overrides = root/RUN/"explicit-response-contracts.json"
    if overrides.exists():
        replacements = c.read(overrides)
        updated = []
        for task in tasks:
            entry = replacements.get(task["id"])
            if entry:
                if digest(task) != entry["original_task_hash"]:
                    c.fail("E_INTEGRITY", "Explicit response contract detached from original task")
                task = entry["task"]
            updated.append(task)
        tasks = updated
    propagation = [t for t in tasks if t["phase"] == "propagation"]''')
    PRIOR.replace(controller,
        '        phase_done(root, phase, data)\n    return result(root)',
        '''        if phase == "propagation" and data.get("unaccepted_tasks"):
            data["status"] = "BLOCKED_INCOMPLETE_REVIEWS"
            phase_done(root, phase, data)
            halt(root, "Independent propagation finished with unaccepted exhausted reviews; complete coverage still blocks checks and final review.")
            return result(root)
        phase_done(root, phase, data)
    return result(root)''')
    definitions = c.read(work/'initial-tasks.json')
    overrides = {}
    for task in definitions:
        if task['phase'] != 'propagation' or (work/'tasks'/task['id']).exists():
            continue
        t = deepcopy(task)
        request = t['request']
        request['response_schema'] = protocol.CompactPropagation.model_json_schema()
        request['instructions'] += (' Return exactly response_schema: binding_hash, readings, questions, obligations, legal_correctness. '
            'Do not add kind or role. Include every question alias exactly once, keeping groups within one reading. '
            'Copy quotations character-for-character, including initial capitalization. An empty repairs list is required '
            'when there is no concrete executable-program defect. Copy the supplied binding_hash without recomputing it.')
        request.pop('binding_hash')
        request['binding_hash'] = digest(request)
        protocol.transport(t)
        overrides[t['id']] = {'original_task_hash': digest(task), 'task': t}
    if len(overrides) != 4:
        c.fail('E_INTEGRITY', 'Expected exactly four unspent initial tasks covering six reviews')
    override_path = work/'explicit-response-contracts.json'
    if override_path.exists() and c.read(override_path) != overrides:
        c.fail('E_INTEGRITY', 'Previously saved response contracts changed')
    c.save(override_path, overrides)
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_exhausted_independent_review_does_not_reset_or_block_other_tasks' not in tests.read_text():
        tests.write_text(tests.read_text()+'''

def test_exhausted_independent_review_does_not_reset_or_block_other_tasks(root, monkeypatch):
    t0, t1 = task(0), task(1)
    class Budget:
        def verify(self):
            return {"used": 90, "new_issue_spending": {"issue.0": 2, "issue.1": 1}}
    monkeypatch.setattr(run, "Allowance", lambda *a, **kw: Budget())
    monkeypatch.setattr(run, "refresh", lambda *a: None)
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 0)
    def response(root, t, **kw):
        return {"task": t["id"], "status": "FAILED" if t["issues"] == ["issue.0"] else "VALIDATED", "error": "E_DEPENDENCY"}
    monkeypatch.setattr(run, "attempt", response)
    assert run.run_tasks(root, [t0,t1])
    frontier=c.read(root/run.RUN/"exhausted-reading-frontier.json")
    assert frontier[0]["task"]==t0["id"]
    assert frontier[0]["status"]=="UNACCEPTED_ATTEMPTS_EXHAUSTED"


def test_two_provider_failures_still_veto_independent_frontier(root, monkeypatch):
    monkeypatch.setattr(run, "attempt", lambda root,t: {"task":t["id"],"status":"FAILED","error":"E_DEPENDENCY"})
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 2)
    assert not run.run_tasks(root, [task(0),task(1)])
    assert "Two consecutive" in run.state(root)["halt"]
''')
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.write_text(directory/'plan-and-audit.md', '''# Independent frontier execution; no exhausted-issue override

Baseline: 90/100 charged calls, 62 accepted reading reviews. The complete first
response for two exception-challenger readings omits one of 31 original questions;
its second attempt disconnected. Representation and source-capitalization repairs
cannot invent that missing disposition. Both candidate repairs remain rejected.
Restore only the two agent-owned controller/protocol files from validated
revision 06, preserving rejected snapshots and original evidence.

Four unspent propagation tasks cover the remaining six independent reviews.
Include the exact response schema inside these requests to address observed
response-shape drift; all complete source text and original identities remain.
The original task definitions stay immutable and are hash-linked to the declared
overrides. The old exhausted review stays failed, but does not prevent these
independent tasks from running. Two consecutive provider failures, source/receipt
corruption, expiry and total/phase/repair/issue caps remain true vetoes.

After independent work, any missing review yields BLOCKED_INCOMPLETE_REVIEWS.
No runtime or final phase may begin on that incomplete input. A pending request
asks the user whether to authorize exactly one additional counted attempt on the
two exhausted issues within the same 100-call ceiling; this repair does not
assume approval or change the amendment. Original call counts stay unchanged.

Skeptical audit: availability of other budget is not authority to retry an
exhausted issue. Complete coverage is required before downstream conclusions.
The final singleton is covered by the four remaining initial calls, correcting
the earlier mistaken count. Tests check independent continuation and the route
failure veto; actual modified requests preflight before activation. This is a
controller and transport repair, not a legal correctness claim.
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
        test_result = subprocess.run([str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *run.TESTS],
            cwd=frozen, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    sizes = [{'task': v['task']['id'], 'bytes': len(canonical(protocol.transport(v['task'])[0]))} for v in overrides.values()]
    c.save(directory/'actual-preflight.json', sizes)
    record = {'status': 'REPAIR_VALIDATED' if test_result.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root), c.receipt(override_path, root)]+[c.receipt(directory/n, root) for n in
            ('pre-repair-state.json', 'plan-and-audit.md', 'tests.log', 'actual-preflight.json')],
        'provider_calls': 0, 'calls_used': run.Allowance(root).verify()['used']}
    c.save(directory/'repair-result.json', record)
    if record['status'] == 'REPAIR_VALIDATED':
        c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
        current = run.state(root)
        current['halt'] = None
        current['repair_reason'] = 'Independent unspent tasks resume; exhausted missing reviews remain explicit and block downstream phases.'
        c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-4500:], 'preflight': sizes}
