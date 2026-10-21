"""Authenticate the scheduling amendment and same six arms; no provider calls."""
import copy
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_preflight_probe', WORK / 'probe-independent.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def main():
    p.need(not p.AUTH.exists() and not p.PREFLIGHT.exists(), 'Preflight already retained; inspect it')
    predecessors = [p.ref(WORK / name) for name in (
        'authorization-initial.json', 'authorization.json',
        'authorization-reviewed.json', 'authorization-final.json')]
    expected = (
        '6096cc0f20763c20ef37d0446e559f71b532e3d0147d9203f78eb076d96b8eed',
        '5bb42a722968889cc4de288fbd80c73d22f59cf16a55c79fd1601dbead7e7bb6',
        'cbef5d09a4abe2b20b794b7426c017c6280f75804354fdc0a59b0a781579844a',
        '3e6251860cce090263bd5e16f6caaefbd073580d58a690d5d31e4eefdb38ced8')
    p.need(tuple(x['sha256'] for x in predecessors) == expected, 'Historical authorities changed')
    old = p.read(p.verify(predecessors[-1]))
    for field in ('grant', 'binding', 'source', 'plan', 'review', 'ledger_before', 'service_scope'):
        p.verify(old[field])
    p.need(old['maximum_calls'] == 6 and old['automatic_retries'] == 0
           and old['production_promotion'] is False, 'Original allowance changed')
    stop = p.read(WORK / 'independent-stop.json')
    p.need(stop['status'] == 'STOPPED_BEFORE_RESERVATION' and stop['trusted_identity_verified']
           and not stop['diagnostic_slots'] and stop['reservations'] == 0
           and stop['retained_source_sha256'] == old['source']['sha256'], 'Predecessor stop not verified')
    controls_path = WORK / 'offline-independent-controls-final/result.json'
    controls = p.read(controls_path)
    p.need(controls['status'] == 'PASS' and controls['real_provider_calls'] == 0
           and controls['production_ledger_writes'] == 0
           and controls['tested_source'] == p.ref(WORK / 'probe-independent.py'),
           'Controls do not verify this exact runner')
    p.verify(controls['source'])
    for reference in controls['receipt_outcomes']:
        p.verify(reference)
    provider = p.CodexProvider()
    allowance = p.CampaignAllowance(p.BASE, provider.routing, root=p.ROOT)
    ledger = allowance.check()
    p.need(provider.routing['model'] == old['model'] == 'gpt-6.1-sol'
           and p.digest(provider.routing) == old['routing_hash'], 'Model or route changed')
    grant = p.read(p.verify(old['grant']))
    p.need(p.digest(grant) == old['grant_hash'] and grant['deadline_utc'] == old['deadline_utc'],
           'Grant changed')
    before = p.read(p.verify(old['ledger_before']))
    p.need(ledger['calls'][:len(before['calls'])] == before['calls'], 'Historical charges changed')
    hashes = set(expected)
    charged = [i+1 for i,row in enumerate(ledger['calls']) if row.get('stage_hash') in hashes]
    p.need(not charged and not list(WORK.glob('*/*/reservation.json')),
           'Prior diagnostic reservation requires reconciliation')
    scope, directory, _ = allowance.service_scope()
    p.need(scope == old['service_scope'] and str(directory.relative_to(p.ROOT)) == old['service_directory'],
           'Shared service identity changed')
    stage_ref = p.read(p.BASE / 'current-stage.json')
    stage = p.read(p.verify(stage_ref))
    p.need(stage['profile'] == 'integration-current-stage.v2'
           and stage['grant_hash'] == ledger['grant_hash']
           and stage['binding_hash'] == p.digest(p.read(p.verify(old['binding']))),
           'Current stage does not support separate accounting')
    equivalent = 0
    for qid,(source,request,schema) in p.fixtures(ledger).items():
        inline = p.expanded(schema)
        equivalent += p.equivalence_checks(schema, inline)
        for form in p.FORMS:
            row = next(r for r in old['arms'] if r['qid'] == qid and r['form'] == form)
            for field in ('request', 'schema', 'original_manifest', 'original_schema'):
                p.verify(row[field])
            payload = p.verify(row['request']).read_bytes()
            shape = p.verify(row['schema']).read_bytes()
            expected_payload = (json.dumps(request,ensure_ascii=False,sort_keys=True,indent=2).encode()
                                if form == 'pretty-json' else (source/'request.json').read_bytes())
            expected_shape = p.canonical(inline) if form == 'inline-schema' else (source/'schema.json').read_bytes()
            p.need(payload == expected_payload and shape == expected_shape,
                   'Non-equivalent request transformation')
            p.need(json.loads(payload) == request and p.digest(json.loads(payload)) == row['request_hash']
                   and p.digest(json.loads(shape)) == row['schema_hash'], 'Semantic identity changed')
            p.validate_output_schema(json.loads(shape))
            p.Draft202012Validator.check_schema(json.loads(shape))
            p.need(p.expanded(json.loads(shape)) == inline, 'Schema constraints changed')
            command = provider.command(p.ROOT/row['request']['path'].rsplit('/',1)[0],
                                       p.ROOT/row['schema']['path'], WORK/'unused-offline-output.json')
            p.need(any('request_max_retries=0' in arg for arg in command)
                   and any('stream_max_retries=0' in arg for arg in command), 'CLI retries enabled')
    authorization = copy.deepcopy(old)
    authorization.update(source=p.ref(WORK/'probe-independent.py'),
        review=p.ref(WORK/'independent-review.md'), plan=p.ref(p.PLAN), original_plan=old['plan'],
        stop_receipt=p.ref(WORK/'independent-stop.json'), previous_authorizations=predecessors,
        runner_revision='independent-diagnostic-scheduling.v1', revised_at_utc=p.utc(),
        revision_instruction='why is this necessary? these tasks do not depend on each other')
    p.AUTH.write_bytes(p.canonical(authorization))
    p.save(p.PREFLIGHT, dict(status='PASS',authorization=p.ref(p.AUTH),
        source=p.ref(__file__), controls=p.ref(controls_path), schema_equivalence_controls=equivalent,
        original_arms_unchanged=True, predecessor_global_slots=charged, predecessor_reservations=0,
        current_stage=stage_ref, calls_used_at_check=len(ledger['calls']), global_ceiling=ledger['maximum'],
        provider_calls_made=0, owner_attempts_reopened=False, deadline_renewed=False,
        runtime_checks=['Exact prior-worker identity and deduplication lock', 'Closed shared circuit',
                        'Authenticated v2 accounting and unchanged authority', 'Original deadline and global budget'],
        checked_at_utc=p.utc()))
    print(json.dumps(p.read(p.PREFLIGHT)))


if __name__ == '__main__':
    main()
