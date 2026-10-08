"""Bounded single-reading recovery, preserving canonical issue spending."""
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
SPEC = importlib.util.spec_from_file_location('assurance_repair_primitives', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def report(root):
    rows = run.task_rows(root)
    failed = [r for r in rows if r['status'] != 'VALIDATED']
    work = root/run.RUN
    current = run.state(root)
    return {'calls_used': run.Allowance(root).verify()['used'], 'state': current,
            'accepted_reading_reviews': sum(len(r['value'].get('reading_updates', [])) for r in run.accepted_rows(root)),
            'failed_attempts': [{k: r[k] for k in ('task', 'attempt', 'error', 'details', 'allowance_slot') if k in r} for r in failed],
            'repair_record': c.read(work/'active-revision.json'),
            'current_time': c.now(), 'window_ends': run.Allowance(root).verify()['ends_at']}


HELPER = '''
def split_timeout_task(task):
    request = task["request"]
    if task["phase"] != "propagation" or request["kind"] != "propagation" or len(request["selected"]) != 2:
        c.fail("E_AUTHORITY", "Single-reading timeout repair requires a paired propagation request")
    result = []
    for cid in request["selected"]:
        child = deepcopy(task)
        child["id"] = task["id"]+".single."+digest(cid)[:12]
        child["issues"] = ["reading."+cid+"."+task["role"]]
        if not set(child["issues"]) <= set(task["issues"]):
            c.fail("E_AUTHORITY", "Split repair changed canonical issue")
        child["counted_repair"] = True
        r = child["request"]
        r["selected"] = [cid]
        for name in ("readings", "questions", "reading_hashes", "prior_assessments"):
            r[name] = {cid: r[name][cid]}
        r["question_inventory"] = [q for q in r["question_inventory"] if q["reading_id"] == cid]
        r["obligations"] = [o for o in r["obligations"] if cid in o["candidate_ids"]]
        r["timeout_repair"] = {"original_task": task["id"],
            "cause_under_test": "Reduce two complete reading dispositions to one; original timeout cause remains unproved.",
            "instruction": "Review this one selected reading and every supplied original question. Complete sources and prior assessment are retained. This is the final permitted attempt on this canonical issue."}
        r.pop("binding_hash")
        r["binding_hash"] = digest(r)
        protocol.transport(child)
        result.append(child)
    expected = {(q["reading_id"], q["question_id"]) for q in request["question_inventory"]}
    actual = [(q["reading_id"], q["question_id"]) for child in result for q in child["request"]["question_inventory"]]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        c.fail("E_INTEGRITY", "Single-reading repair lost or duplicated an original question")
    return result


def recover_timeout(root, task, row):
    if not (row.get("error") == "E_RESOURCE_LIMIT" and "Codex call deadline" in str(row.get("details"))
            and task["phase"] == "propagation" and task["request"]["kind"] == "propagation"
            and len(task["request"]["selected"]) == 2):
        return [row]
    children = split_timeout_task(task)
    definitions = root/RUN/"timeout-repairs"/(task["id"]+".json")
    if definitions.exists():
        if c.read(definitions) != children:
            c.fail("E_INTEGRITY", "Saved split timeout repair changed")
    else:
        c.save(definitions, children)
    # Each child owns the same canonical issue and its remaining counted attempt.
    # Completed child outputs recover normally; no attempt or journal is reset.
    refresh(root, "Split timed-out paired task into complete single-reading repair attempts")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, root, child) for child in children]
        return [future.result() for future in futures]


def unresolved_task_ids(root, tasks):
    rows = accepted_rows(root)
    identities = {(row["role"], update["reading_id"]) for row in rows
                  for update in row["value"].get("reading_updates", [])}
    ids = {row["task"] for row in rows}
    return [task["id"] for task in tasks if not (
        all((task["role"], cid) in identities for cid in task["request"]["selected"])
        if task["phase"] == "propagation" and task["request"]["kind"] == "propagation" else task["id"] in ids)]

'''


TESTS = '''

def paired_task():
    t, value, aliases = propagation_example()
    r = t["request"]
    second = "reading.second"
    first = r["selected"][0]
    r["selected"].append(second)
    r["readings"] = {first: {"subject": "first"}, second: {"subject": "second"}}
    r["questions"] = {first: {"question": "first"}, second: {"question": "second"}}
    r["reading_hashes"][second] = "e"*64
    r["prior_assessments"][second] = {"formalization": None}
    r["question_inventory"].append({"reading_id": second, "question_id": "question.1", "text": "Date?"})
    r["obligations"] = [{"id": "obligation.shared", "candidate_ids": [first, second], "dimension": "time"}]
    t["issues"] = ["reading."+cid+"."+t["role"] for cid in r["selected"]]
    r.pop("binding_hash")
    r["binding_hash"] = digest(r)
    return t


def test_timeout_split_preserves_complete_sources_and_pair_question_ids():
    original = paired_task()
    children = run.split_timeout_task(original)
    assert len(children) == 2
    assert {i for child in children for i in child["issues"]} == set(original["issues"])
    assert all(child["counted_repair"] for child in children)
    assert all(child["request"]["source_packet"] == original["request"]["source_packet"] for child in children)
    assert sum(len(t["request"]["question_inventory"]) for t in children) == 3
    assert all(len(t["request"]["selected"]) == 1 for t in children)
    assert children == run.split_timeout_task(original)


def test_split_timeout_recovery_reuses_children_without_new_call(root, monkeypatch):
    t = paired_task()
    children = run.split_timeout_task(t)
    calls = []
    def attempt_child(root, task):
        calls.append(task["id"])
        return {"task": task["id"], "status": "VALIDATED"}
    monkeypatch.setattr(run, "attempt", attempt_child)
    failure = {"error": "E_RESOURCE_LIMIT", "details": "Codex call deadline"}
    assert len(run.recover_timeout(root, t, failure)) == 2
    saved = c.read(root/run.RUN/"timeout-repairs"/(t["id"]+".json"))
    assert saved == children
    assert len(calls) == 2


def test_split_acceptance_satisfies_original_task_without_merging_ids(root, monkeypatch):
    task = paired_task()
    rows = [{"task": "split."+str(i), "role": task["role"], "value": {"reading_updates": [{"reading_id": cid}]}}
            for i, cid in enumerate(task["request"]["selected"])]
    monkeypatch.setattr(run, "accepted_rows", lambda root: rows)
    assert run.unresolved_task_ids(root, [task]) == []
    rows.pop()
    assert run.unresolved_task_ids(root, [task]) == [task["id"]]
'''


def repair(root):
    run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 53:
        c.fail('E_AUTHORITY', 'Timeout protocol repair is bound to the verified 53-call checkpoint')
    code = root/'scripts/assurance_evidence_continuation.py'
    replace = PRIOR.replace
    replace(code, '\ndef run_tasks(root, tasks, pilot=False):', HELPER+'\ndef run_tasks(root, tasks, pilot=False):')
    replace(code, 'correction=bool(correction) or task.get("program_repair", False)',
            'correction=bool(correction) or task.get("program_repair", False) or task.get("counted_repair", False)')
    replace(code, '            final_rows.append(row)', '            final_rows.extend(recover_timeout(root, task, row))')
    replace(code, '            accepted_ids = {r["task"] for r in accepted_rows(root)}\n            unaccepted = [t["id"] for t in scheduled if t["id"] not in accepted_ids]',
            '            unaccepted = unresolved_task_ids(root, scheduled)')
    # Program repair lookup must include any singleton tasks; they are not in the
    # immutable original two-reading task inventory.
    replace(code, '    originals = {t["id"]: t for t in c.read(root/RUN/"initial-tasks.json")}',
            '''    originals = {t["id"]: t for t in c.read(root/RUN/"initial-tasks.json")}
    for path in (root/RUN/"timeout-repairs").glob("*.json"):
        originals.update({t["id"]: t for t in c.read(path)})''')
    # A failed task is counted once. No model correction can bypass the per-issue cap.
    replace(code,
        '                refresh(root, "Exact response-validation repair triggered for "+task["id"])\n                row = attempt(root, task, number=2, correction=row)',
        '''                spending = Allowance(root).verify()["new_issue_spending"]
                if all(spending.get(issue, 0) < 2 for issue in task["issues"]):
                    refresh(root, "Exact response-validation repair triggered for "+task["id"])
                    row = attempt(root, task, number=2, correction=row)''')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_timeout_split_preserves_complete_sources_and_pair_question_ids' not in tests.read_text():
        tests.write_text(tests.read_text()+TESTS)
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.save(directory/'pre-repair-report.json', report(root))
    c.write_text(directory/'plan-and-audit.md', '''# Bounded timeout repair and execution plan

Baseline: saved continuation at 53/100 charged calls, 10 accepted reading reviews,
three historical scope corrections, and all 46 original obligations still open.
The renewed user instruction is to continue execution. The original 48-hour
window and every canonical issue's two additional attempts remain unchanged.

Question: can a complete single-reading response finish within the existing
300-second provider ceiling when a paired response timed out? This is an
execution-protocol hypothesis; input size is not a legal promotion criterion and
the root cause of the timeout remains unproved. Split only a recorded timeout,
retain complete source units and the complete original selected reading, own
assessment and all its original questions. Exact disjoint pair-identity coverage
must equal the timed-out task. Source texts and shared obligations remain intact.
Each singleton spends the same canonical issue's remaining counted repair attempt.

Execute the two singleton repairs, then continue the saved propagation schedule.
Every response must pass the existing exact quotation, question coverage,
identity and conservative disposition checks. No partially accepted task can
satisfy the full phase. Two consecutive provider failures, expired authorization,
budget exhaustion, changed receipts or incomplete phase coverage remain vetoes.
Run conditional program repairs within the remaining reserve, keeping exhausted
or rejected programs challenged. Run checks only after all 70 reading reviews,
then final reviews from actual completed outputs. Refresh the plan between each
batch, repair and phase. Preserve all old failures and snapshots.

Default audit: existing model, route, deadline, sources and scientific acceptance
rules are baselines; singleton output is the tested repair hypothesis. Early
diagnostics are actual request sizes, exact split coverage and the first two
responses. No model change, source truncation, allowance reset or automatic legal
closure is permitted. A successful response does not establish legal truth.

Skeptical audit: the source packet is still substantial, so the repair may still
time out; the same issue cannot be retried again after its singleton call. The
paired peer succeeded, which permits testing response workload as a bounded
alternative explanation. The split cannot merge identical question text across
readings, erase a prior failure, or bypass final coverage. Tests cover those
conditions plus original spending and restart invariants. Audit permits the
bounded repair and continuation after frozen tests and actual-packet preflight.
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
        tests_result = subprocess.run([str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *run.TESTS],
            cwd=frozen, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    probe = '''from pathlib import Path
import assurance_evidence_continuation as r
import assurance_evidence_core as c
from legalmath.canonical import canonical
root=Path('/home/chakwong/python/legalmath')
tasks=c.read(root/r.RUN/'initial-tasks.json')
failed='propagation.structure-reader.972bf17b15b8dcaa02c184ce'
t=next(t for t in tasks if t['id']==failed)
for child in r.split_timeout_task(t):
    wire,schema,aliases=r.protocol.transport(child)
    print(child['id'], len(canonical(wire)), len(child['request']['question_inventory']), child['issues'])
'''
    with (directory/'actual-preflight.log').open('w') as stream:
        preflight = subprocess.run([str(root/'.venv/bin/python'), '-c', probe], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    record = {'status': 'REPAIR_VALIDATED' if tests_result.returncode == preflight.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('pre-repair-state.json', 'pre-repair-report.json', 'plan-and-audit.md', 'tests.log', 'actual-preflight.log')],
        'calls_used': run.Allowance(root).verify()['used'], 'provider_calls': 0}
    c.save(directory/'repair-result.json', record)
    if record['status'] != 'REPAIR_VALIDATED':
        return {'status': record['status'], 'tests': (directory/'tests.log').read_text()[-7000:],
                'preflight': (directory/'actual-preflight.log').read_text()[-3000:], 'calls_used': record['calls_used']}
    c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
    current = run.state(root)
    current['halt'] = None
    current['repair_reason'] = 'Reviewed singleton timeout repair under unchanged canonical issue limits; resumed by user instruction.'
    c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-300:], 'preflight': (directory/'actual-preflight.log').read_text()[-2000:]}
