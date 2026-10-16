"""Fixed offline recovery of a complete response with conservative alternate fields."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from legalmath.canonical import raw_digest
import assurance_evidence_core as c
import assurance_evidence_continuation as run

TARGET = 'propagation.structure-reader.57600220ca583138052e970c'
ROOT = Path('/home/chakwong/python/legalmath')
SAVED = ROOT/run.RUN/'engineering-repairs/revision-02/frozen/scripts/assurance_evidence_maintenance.py'
SPEC = importlib.util.spec_from_file_location('assurance_schema_repair_primitives', SAVED)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def report(root):
    rows = run.task_rows(root)
    return {'calls_used': run.Allowance(root).verify()['used'], 'state': run.state(root),
        'accepted_reading_reviews': sum(len(r['value'].get('reading_updates', [])) for r in run.accepted_rows(root)),
        'failed_attempts': [{k: row[k] for k in ('task', 'attempt', 'error', 'details', 'allowance_slot') if k in row}
                           for row in rows if row['status'] != 'VALIDATED'],
        'current_time': c.now(), 'window_ends': run.Allowance(root).verify()['ends_at']}


def repair(root):
    run.verify(root)
    work = root/run.RUN
    if run.Allowance(root).verify()['used'] != 66:
        c.fail('E_AUTHORITY', 'Alternate response-shape repair is bound to the 66-call checkpoint')
    target = work/'tasks'/TARGET/'attempt-02'
    request = c.read(target/'task.json')['request']
    if request['obligations']:
        return {'status': 'REPAIR_REJECTED_MISSING_OBLIGATIONS', 'obligations': request['obligations']}
    protocol = root/'scripts/assurance_evidence_protocol.py'
    code = root/'scripts/assurance_evidence_continuation.py'
    PRIOR.replace(protocol, 'def validate(value, task, reverse):', 'def validate_compact(value, task, reverse):')
    if 'def validate(value, task, reverse):' not in protocol.read_text():
        protocol.write_text(protocol.read_text()+'''

def validate(value, task, reverse):
    try:
        return validate_compact(value, task, reverse)
    except c.LegalMathError as exc:
        if exc.code != "E_SCHEMA" or task["request"]["kind"] != "propagation":
            raise
        from assurance_evidence_response_adapter import validate as validate_alternate
        return validate_alternate(value, task, reverse)
''')
    PRIOR.replace(code, 'row.get("error") == "E_REFERENCE":', 'row.get("error") in ("E_REFERENCE", "E_SCHEMA"):')
    # Count dependency failures before launching any corrective requests. A
    # timeout repair is permitted for one failed paired task, not a failing route.
    PRIOR.replace(code, '        final_rows = []\n        for task, row in pairs:',
        '''        if consecutive_failures(root) >= 2:
            return halt(root, "Two consecutive provider failures; no corrective dispatch before route recovery.")
        final_rows = []
        for task, row in pairs:''')
    tests = root/'tests/assurance/test_assurance_evidence_continuation.py'
    if 'test_lossless_unresolved_response_adapter_preserves_every_quote' not in tests.read_text():
        tests.write_text(tests.read_text()+'''

def test_lossless_unresolved_response_adapter_preserves_every_quote():
    t, value, aliases = propagation_example()
    value.pop("legal_correctness")
    value.pop("obligations")
    value["kind"] = "propagation"
    value["role"] = t["role"]
    value["questions"][0]["status"] = "unresolved"
    value["readings"][0]["assumptions"] = ["Assumption "+str(i) for i in range(7)]
    value["questions"][0]["evidence"] = [{"unit_id": "transport.source00", "quote": "Complete retained source."} for _ in range(5)]
    result = p.validate(value, t, aliases)
    assert len(result["reading_updates"][0]["added_assumptions"]) == 7
    assert all(len(q["evidence"]) == 5 for q in result["question_updates"])
    assert all(q["status"] == "REMAINS_OPEN" for q in result["question_updates"])
    value["questions"][0]["ids"] = ["transport.q00"]
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)


def test_adapter_cannot_infer_missing_obligation_or_mismatched_role():
    t, value, aliases = propagation_example()
    value.pop("legal_correctness")
    value.pop("obligations")
    value.update(kind="propagation", role="exception-challenger")
    value["questions"][0]["status"] = "unresolved"
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)
    value["role"] = t["role"]
    t["request"]["obligations"] = [{"id": "must-answer"}]
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)
''')
    versions = work/'engineering-repairs'
    directory = versions/f"revision-{len(list(versions.glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'pre-repair-state.json', run.state(root))
    c.save(directory/'pre-repair-report.json', report(root))
    c.write_text(directory/'plan-and-audit.md', '''# Lossless alternate-shape recovery

Baseline: 66 counted calls, 30 accepted reading reviews. The saved corrective
response has complete reading and question material but uses status unresolved,
longer evidence/assumption lists, and explicit kind/role fields. Its selected
readings have no original obligation rows, so an empty obligation list can be
reconstructed without inventing a review. Missing legal-correctness language is
supplied only as the system restriction NOT_ESTABLISHED.

Accept only this explicit alternate shape. Preserve every quote, reason,
assumption and question. Check exact binding and role, every source quotation,
complete original question pair identities, unique selected readings, existing
program presence, and conservative challenge handling. Never infer omitted
obligation findings. The transport's shortness limits are convenience bounds,
not source-validity criteria. The new bounds remain finite and preserve the
complete received response. Raw provider bytes and original rejection remain
immutable; a new offline validation record links to them.

Skeptical audit: renaming unresolved to REMAINS_OPEN cannot close a question;
larger lists must still have every quote checked. Reject unknown extra fields,
wrong roles, missing coverage, invented quotes, or nonempty omitted obligations.
The route's response-shape compliance remains unreliable; do not mistake this
adapter for legal validation. Tests attack completeness and missing-obligation
inference. Also enforce the two-provider-failure stop before launching any
correction, including timeout splits. This is a controller repair, not a new
scientific claim or allowance. Execute frozen tests and replay the actual saved
response before activation; no provider call is required.
''')
    frozen = directory/'frozen'
    hashes = c.code_material(root)
    hashes['pyproject.toml'] = raw_digest((root/'pyproject.toml').read_bytes())
    for name in hashes:
        target_file = frozen/name
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target_file)
    env = {**os.environ, 'PYTHONPATH': str(frozen/'src')+os.pathsep+str(frozen/'scripts'),
           'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_VISIBLE_DEVICES': '-1'}
    with (directory/'tests.log').open('w') as stream:
        test_result = subprocess.run([str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *run.TESTS], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    probe = '''from pathlib import Path
import assurance_evidence_continuation as r
import assurance_evidence_core as c
root=Path('/home/chakwong/python/legalmath')
path=root/r.RUN/'tasks/propagation.structure-reader.57600220ca583138052e970c/attempt-02'
task=c.read(path/'task.json')
row=r.attempt(root,task,2)
print(row['status'],row.get('error'),len(row.get('value',{}).get('reading_updates',[])))
if row['status']!='VALIDATED':
    print(row.get('details'))
    raise SystemExit(1)
'''
    with (directory/'saved-response-replay.log').open('w') as stream:
        replay = subprocess.run([str(root/'.venv/bin/python'), '-c', probe], cwd=frozen,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    record = {'status': 'REPAIR_VALIDATED' if test_result.returncode == replay.returncode == 0 else 'REPAIR_REJECTED',
        'created_at': c.now(), 'frozen_root': str(frozen.relative_to(root)), 'code_hashes': hashes,
        'references': [c.receipt(work/'manifest.json', root)]+[c.receipt(directory/n, root) for n in
            ('pre-repair-state.json', 'pre-repair-report.json', 'plan-and-audit.md', 'tests.log', 'saved-response-replay.log')],
        'provider_calls': 0, 'calls_used': run.Allowance(root).verify()['used']}
    c.save(directory/'repair-result.json', record)
    if record['status'] != 'REPAIR_VALIDATED':
        return {'status': record['status'], 'tests': (directory/'tests.log').read_text()[-6500:],
                'replay': (directory/'saved-response-replay.log').read_text()[-3500:]}
    c.save(work/'active-revision.json', {'receipt': c.receipt(directory/'repair-result.json', root)})
    current = run.state(root)
    current['halt'] = None
    current['repair_reason'] = 'Lossless alternate-shape response validated offline; original raw output and charged calls preserved.'
    c.save(work/'state.json', current)
    return {'status': record['status'], 'calls_used': record['calls_used'], 'revision': str(directory.relative_to(root)),
            'tests': (directory/'tests.log').read_text()[-300:], 'replay': (directory/'saved-response-replay.log').read_text()[-1000:]}
