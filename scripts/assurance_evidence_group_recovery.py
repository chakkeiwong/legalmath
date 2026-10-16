"""Lossless group partition and exact saved-response recovery at the 90-call checkpoint."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from legalmath.canonical import raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run

ROOT = Path('/home/chakwong/python/legalmath')
TARGET = 'propagation.exception-challenger.007205b81b17778be99277e7'
SAVED = ROOT/run.RUN/'engineering-repairs/revision-02/frozen/scripts/assurance_evidence_maintenance.py'
SPEC = importlib.util.spec_from_file_location('assurance_group_repair_primitives', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def report(root):
    rows = run.accepted_rows(root)
    work = root/run.RUN
    state = run.state(root)
    result_path = work/'final-result.json'
    value = c.read(result_path) if result_path.exists() else {}
    return {'calls_used': run.Allowance(root).verify()['used'], 'remaining_calls': run.Allowance(root).verify()['remaining'],
        'state': state, 'accepted_reading_reviews': sum(len(r['value'].get('reading_updates', [])) for r in rows),
        'current_stop': c.read(work/'current-stop.json') if (work/'current-stop.json').exists() else None,
        'final_review_acceptance': value.get('final_review_acceptance'), 'checks': value.get('checks'),
        'final_review_findings': value.get('final_review_findings', []),
        'program_repair_frontier': c.read(work/'program-repair-frontier.json') if (work/'program-repair-frontier.json').exists() else []}


HELPER = '''
def partition_question_groups(value, question_aliases):
    # A group asserts the same status/evidence/reason for each listed ID. Splitting
    # the list by its already-bound reading preserves every such assertion.
    value = deepcopy(value)
    groups = []
    for group in value["questions"]:
        owners = {}
        for question_id in group["ids"]:
            if question_id not in question_aliases:
                c.fail("E_REFERENCE", "Foreign question alias in group partition")
            owner = question_aliases[question_id]["reading_id"]
            owners.setdefault(owner, []).append(question_id)
        groups += [{**group, "ids": ids} for ids in owners.values()]
    value["questions"] = groups
    return value

'''


TESTS = '''

def test_cross_reading_group_partition_preserves_every_assertion():
    value = {"questions": [{"ids": ["q0", "q1", "q2"], "status": "open", "reason": "Both need case facts.",
                            "evidence": [{"unit_id": "u", "quote": "Source"}]}]}
    aliases = {"q0": {"reading_id": "r0"}, "q1": {"reading_id": "r1"}, "q2": {"reading_id": "r0"}}
    repaired = p.partition_question_groups(value, aliases)
    before = {q: {k:v for k,v in g.items() if k != "ids"} for g in value["questions"] for q in g["ids"]}
    after = {q: {k:v for k,v in g.items() if k != "ids"} for g in repaired["questions"] for q in g["ids"]}
    assert before == after
    assert value["questions"][0]["ids"] == ["q0", "q1", "q2"]
    assert all(len({aliases[q]["reading_id"] for q in g["ids"]}) == 1 for g in repaired["questions"])


def test_group_partition_preserves_duplicate_for_coverage_veto():
    value = {"questions": [{"ids": ["q0", "q0"], "status": "open", "reason": "Missing facts.", "evidence": []}]}
    assert p.partition_question_groups(value, {"q0": {"reading_id": "r"}})["questions"][0]["ids"] == ["q0", "q0"]
    with error("E_REFERENCE"):
        p.partition_question_groups(value, {})


def test_partition_never_repairs_an_invented_quote():
    t, value, aliases = propagation_example()
    value["questions"][0]["evidence"] = [{"unit_id": "transport.source00", "quote": "Invented quotation"}]
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)
'''


def repair(root):
    run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 90:
        c.fail('E_AUTHORITY', 'Group partition repair requires the verified 90-call checkpoint')
    protocol = root/'scripts/assurance_evidence_protocol.py'
    PRIOR.replace(protocol, '\ndef validate_compact(value, task, reverse):', HELPER+'\ndef validate_compact(value, task, reverse):')
    PRIOR.replace(protocol,
        '    raw = translate(parse(CompactPropagation, value), reverse["tokens"])',
        '    raw = translate(partition_question_groups(parse(CompactPropagation, value), reverse["questions"]), reverse["tokens"])')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_cross_reading_group_partition_preserves_every_assertion' not in tests.read_text():
        tests.write_text(tests.read_text()+TESTS)
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.write_text(directory/'plan-and-audit.md', '''# Lossless group partition; remaining execution

Baseline: 90/100 calls, 62 accepted reading reviews, one complete rejected
response and a failed service correction for the same two readings. Inspect the
complete first response. Its group format may be normalized by partitioning IDs
by their pre-existing reading association, keeping each question's assigned
status, evidence and explanation exactly unchanged. This does not infer any new
answer, change a quotation, merge identities, or close any question. The same
strict validator then checks every quote, complete pair-identity coverage, unique
readings, dispositions and obligations. The adapter may still reject the output
on an independent substantive or integrity defect; such rejection must stand.

Audit correction: four remaining initial propagation calls cover six reading
reviews: the two-reading pair under both roles and the final singleton under
both roles. The prior statement that the singleton exceeded that cap was wrong.
Recovering the saved two-review response would bring accepted coverage to 64,
then these four calls can bring it to 70. Four final-review calls remain allocated,
with two repair calls left in the unchanged reserve. No third per-issue attempt
is authorized or needed for the offline group partition.

Skeptical audit: a generic statement could be weak for either reading, but the
partition cannot improve or worsen the statement assigned to any question.
It changes representation only. Reading-specific source fidelity and final
substantive review remain required. Tests preserve all per-question assertions,
duplicates for the coverage veto, and invalid-quote rejection. Replay the actual
provider bytes with a factory that forbids new calls, then activate only after
tests and exact full validation pass. No automatic clearing of general provider
halts is introduced. The rejected open-frontier patch did not execute because
its installation command had a Python syntax error; no source or state changed.
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
    probe = '''from pathlib import Path
import assurance_evidence_continuation as r
import assurance_evidence_core as c
root=Path('/home/chakwong/python/legalmath')
path=root/r.RUN/'tasks/propagation.exception-challenger.007205b81b17778be99277e7/attempt-01'
t=c.read(path/'task.json')
def forbid(**kwargs):
    raise AssertionError('No provider call permitted in offline replay')
row=r.attempt(root,t,provider_factory=forbid)
print(row['status'], row.get('error'), row.get('details') if row['status']!='VALIDATED' else len(row['value']['question_updates']))
assert row['status']=='VALIDATED'
assert r.Allowance(root).verify()['used']==90
'''
    with (directory/'saved-response-replay.log').open('w') as stream:
        replay = subprocess.run([str(root/'.venv/bin/python'), '-c', probe], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    record = {'status': 'REPAIR_VALIDATED' if test_result.returncode == replay.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('pre-repair-state.json', 'plan-and-audit.md', 'tests.log', 'saved-response-replay.log')],
        'provider_calls': 0, 'calls_used': run.Allowance(root).verify()['used']}
    c.save(directory/'repair-result.json', record)
    if record['status'] == 'REPAIR_VALIDATED':
        c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
        current = run.state(root)
        current['halt'] = None
        current['repair_reason'] = 'Complete saved response revalidated after lossless partition by original reading identity.'
        c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-3500:], 'replay': (directory/'saved-response-replay.log').read_text()[-3500:]}
