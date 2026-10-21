"""Inspect retained transport evidence; never dispatch or change production state."""
import collections
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib
from urllib.parse import urlsplit

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    started = time.monotonic()
    ledger_bytes = (BASE / 'live-calls.json').read_bytes()
    ledger = json.loads(ledger_bytes)
    config = tomllib.loads((BASE / 'campaign-routing.toml').read_text())
    name = config.get('model_provider', 'openai')
    fields = config.get('model_providers', {}).get(name, {})
    routing = dict(model=config.get('model'), provider=name, fields={
        k: fields[k] for k in ('name', 'base_url', 'wire_api',
                              'requires_openai_auth', 'env_key') if k in fields})
    route_hash = sha(json.dumps(routing, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False).encode())
    grant = read(BASE / 'live-grant.json')
    assert route_hash == grant['routing_hash']
    endpoint = urlsplit(fields.get('base_url', ''))
    receipts = []
    for slot in range(3312, 3336):
        charge = ledger['calls'][slot - 1]
        directory = BASE / 'provider-evidence' / f"{slot:04}-{charge['request_hash'][:16]}"
        manifest = read(directory / 'manifest.json')
        assert manifest['allowance_slot'] == slot
        assert manifest['request_hash'] == charge['request_hash']
        for filename, details in manifest['files'].items():
            assert sha((directory / filename).read_bytes()) == details['retained_sha256']
        assert sha((directory / 'request.json').read_bytes()) == charge['request_hash']
        events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines() if line.strip()]
        errors = [e.get('message') for e in events if e.get('type') == 'error']
        warnings = [e['item']['message'] for e in events
                    if e.get('item', {}).get('type') == 'error']
        receipts.append(dict(slot=slot, manifest=str((directory / 'manifest.json').relative_to(ROOT)),
            request_hash=charge['request_hash'], schema_hash=manifest['files']['schema.json']['retained_sha256'],
            complete_output_present=manifest['complete_output_present'],
            completed_turn=any(e.get('type') == 'turn.completed' for e in events),
            terminal_errors=errors, cli_warnings=warnings))
    assert receipts[0]['request_hash'] == receipts[1]['request_hash']
    assert receipts[0]['schema_hash'] == receipts[1]['schema_hash']
    binding = read(BASE / 'current-binding.json')
    scope = ROOT / Path(binding['phase_service_scope']['path']).parent
    recovery = read(scope / 'service-recovery.json')
    circuit = read(scope / 'service-circuit.json')
    journal = read(WORK / 'live/p14/product/calls/dispatch.json')['calls']
    program_path = ROOT / 'docs/implementation/legal-mission-control/integration-master.json'
    program = read(program_path)
    revision = next(program[k] for k in ('repair_execution', 'complete_account_capacity_repair',
        'account_reconstruction_repair', 'account_instruction_repair', 'lossless_account_repair',
        'account_capacity_repair') if program.get(k))
    roots = {**revision['recoveries'], **program.get('settled_recovery', {}).get('recoveries', {})}
    root_counts = {q: len(read(ROOT / pointer['path'])['account_recovery']['roots'])
                   for q, pointer in roots.items()}
    order = sorted(('p10', 'p14', 'evidence', 'gatecoin'), key=lambda q: root_counts[q])
    forced = revision.get('service_continuation', {}).get('question')
    if forced:
        order = [forced] + [q for q in order if q != forced]
    state = read(BASE / 'execution-state.json')
    sources = ['scripts/legal_integration_campaign.py', 'scripts/legal_integration_phased_live.py',
        'scripts/legal_integration_synthesis_resolution.py',
        'src/legalmath/interpretation/assurance/bounded_provider.py',
        'src/legalmath/interpretation/search/providers.py']
    result = dict(at_utc=datetime.now(timezone.utc).isoformat(),
        command='.venv-context/bin/python ' + str(Path(__file__).resolve().relative_to(ROOT)),
        plan=str((WORK / 'service-execution-audit.md').relative_to(ROOT)),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment='.venv-context; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        seeds='N/A: deterministic receipt inspection', provider_calls_made_by_audit=0,
        campaign_model=routing['model'], campaign_provider=name,
        campaign_endpoint=dict(scheme=endpoint.scheme, host=endpoint.hostname,
                               port=endpoint.port, path=endpoint.path),
        routing_hash=route_hash, routing_matches_grant=True,
        program_sha256=sha(program_path.read_bytes()),
        inspected_source_hashes={p: sha((ROOT / p).read_bytes()) for p in sources},
        calls_at_start=len(ledger['calls']), calls_at_finish=len(read(BASE / 'live-calls.json')['calls']),
        ledger_unchanged=(BASE / 'live-calls.json').read_bytes() == ledger_bytes,
        receipt_hashes_valid=True, failed_request_3312_exactly_retried_at_3313=True,
        receipt_counts=dict(collections.Counter('completed' if r['complete_output_present']
            and r['completed_turn'] else 'no_complete_output' for r in receipts)),
        inspected_receipts=receipts,
        p14_journal_statuses=dict(collections.Counter(r['status'] for r in journal.values())),
        p14_retained_validations=sum(r['status'] == 'VALIDATED' and 'retained_initial' in r for r in journal.values()),
        reserved_requests={k: v for k, v in journal.items() if v['status'] == 'RESERVED'},
        retry_policy=binding['service_recovery_policy'], retry_charges_used=len(recovery['charges']),
        latest_retry=recovery['charges'][-1], service_circuit=circuit,
        historical_priority=revision.get('service_continuation'),
        historical_ordering_root_counts=root_counts, effective_question_order=order,
        pending_command_tasks=[t['id'] for t in program['tasks'] if t['executor'] == 'command'
            and state['tasks'][t['id']]['status'] in ('PENDING', 'RUNNING')],
        integration_complete=False, upstream_service_origin='NOT_ESTABLISHED_FROM_RETAINED_ERROR',
        wall_seconds=round(time.monotonic() - started, 3))
    path = WORK / 'service-execution-audit.json'
    assert not path.exists(), 'Retain the first audit; use a new explicit observation for another run'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('at_utc', 'campaign_model', 'campaign_provider',
        'routing_matches_grant', 'receipt_counts', 'p14_journal_statuses', 'p14_retained_validations',
        'effective_question_order', 'ledger_unchanged', 'provider_calls_made_by_audit',
        'wall_seconds')}, indent=2))


if __name__ == '__main__':
    main()
