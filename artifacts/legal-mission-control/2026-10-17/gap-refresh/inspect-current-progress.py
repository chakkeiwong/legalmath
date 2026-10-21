"""Inspect saved results only; do not dispatch, repair, or modify authority."""
import collections
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased import account_contract, account_recovery
from legalmath.interpretation.assurance.answer_acceptance import MENTION, BRACKET_NUMBER
from jsonschema import Draft202012Validator

WORK = Path(__file__).resolve().parent
MASTER = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
EVIDENCE = ROOT / 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-7/live/common/evidence'
PLAN = ROOT / 'docs/implementation/legal-mission-control/results/gap-refresh-progress-2026-10-17.md'

def read(path):
    return json.loads(path.read_text())

def ref(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def receipt(slot):
    paths = list((MASTER / 'provider-evidence').glob(str(slot) + '-*/manifest.json'))
    assert len(paths) == 1, (slot, 'ambiguous receipt')
    path = paths[0]
    value = read(path)
    for name, row in value['files'].items():
        content = (path.parent / name).read_bytes()
        assert len(content) == row['bytes']
        assert hashlib.sha256(content).hexdigest() == row['retained_sha256']
    return path, value

def main():
    started = time.monotonic()
    call = EVIDENCE / 'calls/detail-25-part-1'
    paths = [call / (n + '.json') for n in ('request', 'schema', 'result', 'raw', 'wire-response')]
    initial = [ref(p) for p in paths]
    request, schema, result, raw, wire = [read(p) for p in paths]
    assert result['status'] == 'FAILED'
    assert result['reason'] == 'Numbered assertion has no document/proposition binding'
    assert result['request_hash'] == digest(request)
    dispatch = read(EVIDENCE / 'calls/dispatch.json')['calls']
    assert dispatch[call.name]['status'] == 'FAILED'
    assert dispatch[call.name]['result_hash'] == digest(result)
    fields = [{'path': p, 'text': text, 'mentions': [m.group(0) for m in MENTION.finditer(text)]}
              for p, text in account_contract.prose_fields(raw['value'])
              if MENTION.search(text) or BRACKET_NUMBER.search(text)]
    assert fields and raw['value']['assertion_bindings'] == []
    violations = [{'path': '/' + '/'.join(map(str, e.absolute_path)), 'validator': e.validator}
                  for e in Draft202012Validator(account_contract.schema()).iter_errors(raw['value'])]
    assert {r['path'] for r in violations} == {r['path'] for r in fields}
    assert all(r['validator'] == 'pattern' for r in violations)
    slot = raw['provenance']['allowance_slot']
    receipt_path, saved_receipt = receipt(slot)
    assert saved_receipt['complete_output_present'] is True
    assert read(receipt_path.parent / 'result.json') == wire['value']
    provider_request = read(receipt_path.parent / 'request.json')
    assert 'Numbered provision labels do not belong in free prose' in provider_request['instructions']
    assert 'including hypothetical and missing-source references' in provider_request['account_instructions']
    original, typed = account_recovery.baseline_request(request, schema, root=ROOT)
    assert typed and 'account_correction' not in request
    correction = account_recovery.correction_value({
        'raw': ref(call / 'raw.json'), 'prose_fields': [r['path'] for r in fields],
        'required_source_gaps': raw['value']['source_gaps']})
    account_recovery.validate_retained_correction(ROOT, correction, original)
    assert initial == [ref(p) for p in paths]

    ledger = read(MASTER / 'live-calls.json')['calls']
    recovery_path = ROOT / 'artifacts/legal-mission-control/2026-10-16/delayed-service/service/service-recovery.json'
    recovery = read(recovery_path)
    retries = []
    for charge in recovery['charges']:
        failed = charge['failed_slot']
        if failed not in (2418, 2446):
            continue
        old_path, old = receipt(failed)
        new_path, new = receipt(failed + 1)
        due = datetime.fromisoformat(charge['next_retry_at_utc'])
        issued = datetime.fromtimestamp(int(ledger[failed]['issued_at_ns']) / 1e9, timezone.utc)
        assert issued >= due
        assert ledger[failed - 1]['request_hash'] == ledger[failed]['request_hash'] == charge['request_hash']
        assert ledger[failed - 1]['stage_hash'] == ledger[failed]['stage_hash'] == charge['stage']['sha256']
        assert old['complete_output_present'] is False and new['complete_output_present'] is True
        for name in ('request.json', 'schema.json'):
            assert (old_path.parent / name).read_bytes() == (new_path.parent / name).read_bytes()
        assert ref(old_path)['sha256'] == charge['receipt_sha256']
        assert ref(old_path.parent / 'schema.json')['sha256'] == charge['schema_hash']
        events = [json.loads(line) for line in (old_path.parent / 'events.jsonl').read_text().splitlines()]
        terminals = [e for e in events if e.get('type') == 'turn.failed']
        assert len(terminals) == 1
        key = Path(charge['stage']['path']).parent.name.removeprefix('call-')
        output = read(EVIDENCE / 'calls' / key / 'result.json')
        assert dispatch[key]['status'] == output['status'] == 'VALIDATED'
        assert output['provenance']['allowance_slot'] == failed + 1
        retries.append({'failed_slot': failed, 'replacement_slot': failed + 1, 'account': key,
            'due_at_utc': due.isoformat(), 'issued_at_utc': issued.isoformat(),
            'seconds_after_due': (issued - due).total_seconds(),
            'terminal_message': terminals[0]['error']['message'],
            'exact_request_and_schema': True, 'validated_account': True,
            'failure_receipt': ref(old_path), 'replacement_receipt': ref(new_path),
            'account_result': ref(EVIDENCE / 'calls' / key / 'result.json')})
    assert len(retries) == 2
    details = read(EVIDENCE / 'requirement-details.json')
    state = read(MASTER / 'execution-state.json')
    report = {'profile': 'integration-progress-diagnostic.v1',
        'at_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': ['.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'environment': str(ROOT / '.venv/bin/python'),
        'devices': 'CPU-only file/schema inspection; CUDA_VISIBLE_DEVICES=-1; no GPU work',
        'random_seeds': 'N/A: deterministic checks of retained evidence',
        'wall_seconds': time.monotonic() - started, 'reviewed_plan': ref(PLAN),
        'source': ref(Path(__file__)), 'failure_inputs': initial,
        'rejection': {'key': call.name, 'slot': slot, 'reason': result['reason'],
            'offending_fields': fields, 'schema_violations': violations,
            'complete_provider_output': True, 'no_output_service_retry_eligible': False,
            'wire_guidance_present': True, 'retained_correction_annotation_valid': True,
            'production_resume_compatibility': 'NOT_TESTED',
            'corrected_legal_answer': 'NOT_PRODUCED', 'provider_receipt': ref(receipt_path),
            'correction_proposal_only': correction},
        'delayed_retries': retries, 'observed_calls': len(ledger),
        'observed_root_results': dict(collections.Counter(d['result']['status'] for d in details)),
        'observed_delayed_allocations': len(recovery['charges']),
        'observed_owner_status': state['tasks']['acquire-evidence']['status'],
        'new_provider_calls': 0, 'new_owner_attempts': 0, 'new_repairs': 0,
        'production_inputs_changed': False, 'legal_acceptance': False, 'integration_complete': False,
        'next_action': 'Keep existing worker; settlement and reviewed allocation precede any correction dispatch.'}
    out = WORK / 'current-progress-diagnostic.json'
    with out.open('x') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'result': str(out.relative_to(ROOT)), 'slot': slot,
        'rejected_paths': [r['path'] for r in fields], 'retries_verified': len(retries),
        'observed_root_results': report['observed_root_results'], 'calls': len(ledger),
        'production_resume_tested': False, 'new_provider_calls': 0}, indent=2))

if __name__ == '__main__':
    main()
