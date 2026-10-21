"""Authenticate the final diagnostic without renewing any execution limit."""
import copy
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('final_probe', WORK / 'probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def main():
    p.need(not p.AUTH.exists() and not p.PREFLIGHT.exists(), 'Final authority already retained')
    expected = {
        'authorization-initial.json':'6096cc0f20763c20ef37d0446e559f71b532e3d0147d9203f78eb076d96b8eed',
        'authorization.json':'5bb42a722968889cc4de288fbd80c73d22f59cf16a55c79fd1601dbead7e7bb6',
        'authorization-reviewed.json':'cbef5d09a4abe2b20b794b7426c017c6280f75804354fdc0a59b0a781579844a',
        'preflight.json':'a5d9a81673416f3fd86733f7725071a7876d7978c0b23bf61c186ac672f69fd6',
        'preflight-reviewed.json':'c5d33c56817dfa91d165d890bf3d4882dafe04aa8482524d5fae9c56ff46330c',
        'safe-stop.json':'499343bae53aedcc010c1d9dfebc69a3b81e43d035d9c656c0c318181e2bba41',
        'probe-reviewed-owner-clocks.py':'00d52d6b9faaa27c0fdfd0705fb225f81eaa665ec348fc1a739ef57d4781bbbc',
    }
    for name, value in expected.items():
        p.need(p.sha((WORK/name).read_bytes()) == value, 'Historical evidence changed: '+name)
    p.need(p.sha(p.PLAN.read_bytes()) ==
           'a00c76e222d125e17e77d3ebfeb697e4e6a0cf22bd672d938b74c0b807bfba30', 'Plan changed')
    original_result = p.ROOT/'docs/implementation/legal-mission-control/results/request-variants-2026-10-18.md'
    p.need(p.sha(original_result.read_bytes()) ==
           '06864aa64218f132b723086ee1f87217d5fa8ef574e18f61eec06b4bf17bed5d', 'Original result changed')
    compile((WORK/'probe.py').read_bytes(), str(WORK/'probe.py'), 'exec')
    controls_path = WORK/'offline-receipt-controls/result.json'
    controls = p.read(controls_path)
    p.need(controls['status'] == 'PASS' and controls['real_provider_calls'] == 0
           and controls['tested_source'] == p.ref(WORK/'probe.py')
           and controls['mission_copy_round_trip'] and controls['protected_live_state_unchanged'],
           'Receipt controls do not verify this runner')
    aggregate = p.read(p.verify(controls['aggregate']))
    for item in aggregate['outcomes']:
        p.verify(item['outcome']); p.verify(item['manifest'])
    provider = p.CodexProvider()
    allowance = p.CampaignAllowance(p.BASE, provider.routing, root=p.ROOT)
    ledger = allowance.check()
    old = p.read(WORK/'authorization-reviewed.json')
    p.need(old['maximum_calls'] == 6 and old['automatic_retries'] == 0
           and old['production_promotion'] is False, 'Original allocation changed')
    for field in ('grant', 'binding', 'plan', 'ledger_before', 'service_scope'):
        p.verify(old[field])
    p.need(provider.routing['model'] == old['model'] == 'gpt-6.1-sol'
           and p.digest(provider.routing) == old['routing_hash'], 'Model or route changed')
    grant = p.read(p.verify(old['grant']))
    p.need(p.digest(grant) == old['grant_hash'] and grant['deadline_utc'] == old['deadline_utc'],
           'Grant changed')
    before = p.read(p.verify(old['ledger_before']))
    p.need(ledger['calls'][:len(before['calls'])] == before['calls'], 'Historical charges changed')
    predecessors = [p.ref(WORK/name) for name in
                    ('authorization-initial.json', 'authorization.json', 'authorization-reviewed.json')]
    hashes = {item['sha256'] for item in predecessors}
    charged = [i+1 for i,row in enumerate(ledger['calls']) if row.get('stage_hash') in hashes]
    p.need(not charged and not list(WORK.glob('*/*/reservation.json')),
           'Prior diagnostic reservation requires reconciliation')
    p.need(not (WORK/'result.json').exists(), 'Diagnostic already settled')
    workers = [item['previous'] for item in p.read(WORK/'worker-attempts.json')]
    workers.append(p.read(WORK/'worker-start.json'))
    for worker in workers:
        identity = worker.get('process') or worker
        p.need(p.process_identity(identity['pid']) is None, 'Prior diagnostic PID still exists')
    p.need(len(old['arms']) == 6 and {(r['qid'],r['form']) for r in old['arms']} ==
           {(qid,form) for qid in p.FIXTURES for form in p.FORMS}, 'Arm allocation changed')
    equivalent = 0
    arms = []
    for qid,(source,request,schema) in p.fixtures(ledger).items():
        inline = p.expanded(schema)
        equivalent += p.equivalence_checks(schema, inline)
        for form in p.FORMS:
            row = next(r for r in old['arms'] if r['qid'] == qid and r['form'] == form)
            for field in ('request','schema','original_manifest','original_schema'):
                p.verify(row[field])
            payload, shape = p.verify(row['request']).read_bytes(), p.verify(row['schema']).read_bytes()
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
            arms.append(dict(qid=qid,form=form,exact_permitted_transformation=True))
    scope,directory,_ = allowance.service_scope()
    p.need(scope == old['service_scope'] and str(directory.relative_to(p.ROOT)) == old['service_directory'],
           'Shared service identity changed')
    running,alive,identities = p.master_owner_state()
    authorization = copy.deepcopy(old)
    authorization.update(source=p.ref(WORK/'probe.py'), review=p.ref(WORK/'writer-review.md'),
        previous_authorizations=predecessors, runner_revision='operational-evidence-writer.v3',
        revised_at_utc=p.utc(), revision_instruction=old['user_instruction'])
    p.AUTH.write_bytes(p.canonical(authorization))
    preflight = dict(status='PASS',authorization=p.ref(p.AUTH),fixture_authentication=True,
        schema_equivalence_controls=equivalent,arms=arms,receipt_controls=p.ref(controls_path),
        stopped_diagnostic_pids=[(w.get('process') or w)['pid'] for w in workers],
        predecessor_global_slots=charged,predecessor_reservations=0,
        ledger_calls_at_revalidation=len(ledger['calls']),global_call_ceiling=ledger['maximum'],
        global_calls_added=0,original_owner_attempts_reopened=False,grant_deadline_extended=False,
        exact_historical_evidence_preserved=expected,active_master_tasks=running,
        active_master_pids=[i['pid'] for i in alive],master_identities=identities,dispatch_ready=False,
        dispatch_prerequisites=['All existing master owners settle','Closed shared service circuit',
                               'Existing locks available','At least 305 seconds before original deadline'],
        source=p.ref(__file__),checked_at_utc=p.utc())
    p.save(p.PREFLIGHT,preflight)
    print(json.dumps({k:preflight[k] for k in ('status','authorization','schema_equivalence_controls',
        'receipt_controls','predecessor_global_slots','predecessor_reservations',
        'ledger_calls_at_revalidation','global_call_ceiling','active_master_tasks','active_master_pids',
        'dispatch_ready','dispatch_prerequisites')}))


if __name__ == '__main__':
    main()
