"""Recorded source capitalization alignment and complete offline validation."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from legalmath.canonical import raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_protocol as protocol
import assurance_evidence_quote_alignment as alignment
from assurance_evidence_group_recovery import report

ROOT = Path('/home/chakwong/python/legalmath')
SAVED = ROOT/run.RUN/'engineering-repairs/revision-02/frozen/scripts/assurance_evidence_maintenance.py'
SPEC = importlib.util.spec_from_file_location('assurance_quote_repair_primitives', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def repair(root):
    run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 90:
        c.fail('E_AUTHORITY', 'Source capitalization repair is bound to the 90-call checkpoint')
    path = work/'tasks/propagation.exception-challenger.007205b81b17778be99277e7/attempt-01'
    task = c.read(path/'task.json')
    raw = c.read(path/'result.json')['rejected_value']
    _, _, aliases = protocol.transport(task)
    corrected, proof = alignment.align(raw, task, aliases)
    if not proof:
        c.fail('E_REFERENCE', 'No unique source capitalization repair found')
    p = root/'scripts/assurance_evidence_protocol.py'
    PRIOR.replace(p,
        'def validate(value, task, reverse):\n    try:',
        'def validate(value, task, reverse):\n    from assurance_evidence_quote_alignment import align\n    value, quote_alignment = align(value, task, reverse)\n    try:')
    # Do not replace a useful compact-schema error with an unrelated alternate-shape error.
    PRIOR.replace(p,
        '        if exc.code != "E_SCHEMA" or task["request"]["kind"] != "propagation":',
        '        if exc.code != "E_SCHEMA" or task["request"]["kind"] != "propagation" or set(value) != {"binding_hash", "kind", "role", "readings", "questions"}:')
    controller = root/'scripts/assurance_evidence_continuation.py'
    PRIOR.replace(controller,
        '        row["rejected_value"] = raw\n        row["value"] = protocol.validate(raw, task, reverse)',
        '''        row["rejected_value"] = raw
        from assurance_evidence_quote_alignment import align
        row["source_quote_case_repairs"] = align(raw, task, reverse)[1]
        row["value"] = protocol.validate(raw, task, reverse)''')
    PRIOR.replace(controller,
        '                    row = {**row, "status": "VALIDATED", "value": validated,',
        '''                    from assurance_evidence_quote_alignment import align
                    row = {**row, "status": "VALIDATED", "value": validated,
                           "source_quote_case_repairs": align(c.read(folder/"result.json"), task, reverse)[1],''')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_quote_case_alignment_preserves_raw_and_records_unique_span' not in tests.read_text():
        tests.write_text(tests.read_text()+'''

def test_quote_case_alignment_preserves_raw_and_records_unique_span():
    from assurance_evidence_quote_alignment import align
    t = task()
    t["request"]["source_packet"]["units"][0]["text"] = "Prefix: the source remains intact."
    value = {"evidence": [{"unit_id": "u0", "quote": "The source remains intact."}]}
    fixed, proof = align(value, t, {"tokens": {"u0": "unit.original"}})
    assert value["evidence"][0]["quote"].startswith("The")
    assert fixed["evidence"][0]["quote"].startswith("the")
    assert proof[0]["start"] == 8
    assert proof[0]["original_quote"] == value["evidence"][0]["quote"]


def test_quote_case_alignment_rejects_ambiguity_and_word_changes():
    from assurance_evidence_quote_alignment import align
    t = task()
    aliases = {"tokens": {"u0": "unit.original"}}
    for source, quote in [("the source; the source", "The source"), ("The legal source", "The valid source"), ("the source", "the  source")]:
        t["request"]["source_packet"]["units"][0]["text"] = source
        value = {"unit_id": "u0", "quote": quote}
        fixed, proof = align(value, t, aliases)
        assert fixed == value and proof == []
''')
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'source-capitalization-proof.json', {'original_result': c.receipt(path/'result.json', root), 'repairs': proof})
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.write_text(directory/'plan-and-audit.md', '''# Explicit source capitalization repair and remaining execution

The original response quoted an initial capital letter where the retained source
has a lower-case letter within its sentence. The original quotation is not exact
and remains preserved in the provider output and rejected response. The derived
quotation is taken from one unique contiguous source span. Every differing
character must be an ASCII alphabetic case change; whitespace, punctuation,
Unicode letters, wording, source identity and quote length cannot change.
The proof records original and exact quotations, source hash and span offsets.
All ordinary exact-quotation checks run after this explicit repair. This is a
source transcription repair, not evidence of legal entailment or permission to
substitute approximate quotations. Ambiguous or altered-word matches fail.

Also retain the reviewed group partition: each question keeps its original
status, reason and evidence, while groups are separated by their already-bound
reading identity. No missing response or question disposition is invented.

Execute the full test suite and actual saved-response replay with provider calls
forbidden. If that passes, the two reading reviews can be recovered without a
third attempt. The four remaining initial calls cover six undispatched reviews,
including the singleton under both roles. Four final calls and two repair calls
remain inside the unchanged total of 100. Complete source and phase coverage
still gate runtime checks and final review. Audit passes for this narrowly
defined, fully recorded repair; raw model source fidelity remains a known risk.
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
    raise AssertionError('Offline replay cannot call a provider')
row=r.attempt(root,t,provider_factory=forbid)
if row['status']!='VALIDATED':
    wire,schema,aliases=r.protocol.transport(t)
    r.protocol.validate(row['rejected_value'],t,aliases)
print(row['status'],len(row.get('value',{}).get('reading_updates',[])),row.get('source_quote_case_repairs'))
assert row['status']=='VALIDATED'
assert r.Allowance(root).verify()['used']==90
'''
    with (directory/'saved-response-replay.log').open('w') as stream:
        replay = subprocess.run([str(root/'.venv/bin/python'), '-c', probe], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    record = {'status': 'REPAIR_VALIDATED' if test_result.returncode == replay.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('source-capitalization-proof.json', 'pre-repair-state.json', 'plan-and-audit.md', 'tests.log', 'saved-response-replay.log')],
        'provider_calls': 0, 'calls_used': run.Allowance(root).verify()['used']}
    c.save(directory/'repair-result.json', record)
    if record['status'] == 'REPAIR_VALIDATED':
        c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
        current = run.state(root)
        current['halt'] = None
        current['repair_reason'] = 'Complete saved response revalidated after recorded group partition and unique source capitalization repair.'
        c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-4000:], 'replay': (directory/'saved-response-replay.log').read_text()[-4000:]}
