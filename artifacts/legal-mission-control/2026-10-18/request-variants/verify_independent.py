"""Post-run receipt/accounting verification, no provider dispatch."""
import importlib.util
import json
from pathlib import Path
import subprocess

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_verification_probe', WORK/'probe-independent.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def main():
    output = WORK / 'independent-verification.json'
    p.need(not output.exists(), 'Verification already retained')
    result = p.read(WORK / 'result.json')
    authorization = p.read(p.verify(result['authorization']))
    preflight = p.read(p.PREFLIGHT)
    p.need(preflight['status'] == 'PASS' and preflight['authorization'] == p.ref(p.AUTH),
           'Wrong preflight authority')
    for field in ('source', 'plan', 'original_plan', 'review', 'grant', 'binding', 'stop_receipt',
                  'ledger_before', 'service_scope'):
        p.verify(authorization[field])
    for reference in authorization['previous_authorizations']:
        p.verify(reference)
    p.need(result['calls_used'] == 6 and result['shared_stop'] is None
           and len(result['outcomes']) == 6, 'Diagnostic did not settle all six arms')
    ledger = p.read(p.BASE / 'live-calls.json')
    p.save(WORK / 'ledger-after.json', ledger)
    own = [i+1 for i,row in enumerate(ledger['calls'])
           if row.get('stage_hash') in p.authority_hashes(authorization)]
    p.need(own == result['global_slots'] and len(own) == 6, 'Unexpected diagnostic charges')
    before = p.read(p.verify(authorization['ledger_before']))
    p.need(ledger['calls'][:len(before['calls'])] == before['calls'], 'Historical charges changed')
    seen = set()
    receipts = []
    for outcome in result['outcomes']:
        qid, form = outcome['qid'], outcome['form']
        p.need((qid, form) not in seen, 'Repeated diagnostic arm')
        seen.add((qid, form))
        directory = WORK / qid / form
        p.need(p.read(directory/'outcome.json') == outcome, 'Retained outcome changed')
        p.need(outcome['classification'] == 'VALID_STRUCTURED_RESPONSE'
               and not outcome['original_schema_errors'] and not outcome['production_promoted'],
               'Result does not establish the declared schema screen')
        manifest = p.read(directory/'manifest.json')
        for reference in manifest['files'].values():
            p.verify(reference)
        row = next(r for r in authorization['arms'] if (r['qid'],r['form']) == (qid,form))
        response = p.read(directory/'result.json')
        for key in ('original_schema', 'schema'):
            p.Draft202012Validator(p.read(p.verify(row[key]))).validate(response)
        events = [json.loads(line) for line in (directory/'events.jsonl').read_bytes().splitlines()]
        p.need(any(e.get('type') == 'turn.completed' for e in events), 'Missing completed turn')
        p.need(not any(e.get('item', {}).get('type') in
                      {'command_execution','mcp_tool_call','web_search','file_change'} for e in events),
               'Unexpected tools used by provider')
        slot = outcome['global_slot']
        charge = ledger['calls'][slot-1]
        p.need(charge['stage_hash'] == p.ref(p.AUTH)['sha256']
               and charge['request_hash'] == row['request_hash'], 'Wrong request charge')
        p.need(p.read(directory/'reservation.json')['global_slot'] == slot, 'Wrong reservation')
        receipts.append(dict(qid=qid, form=form, slot=slot,
                             outcome=p.ref(directory/'outcome.json'), manifest=p.ref(directory/'manifest.json')))
    p.need(seen == {(q,f) for q in p.FIXTURES for f in p.FORMS}, 'Missing test arm')
    start = p.read(WORK/'concurrent-start.json')
    p.need(all(i['alive'] for i in start['p10_workers']) and start['diagnostic_reservations'],
           'No verified overlap with original master workers')
    master_slots = [i for i in range(min(own), max(own)+1) if i not in own]
    p.save(output, dict(status='PASS', question='Can independent request variants run without waiting for P10?',
        scheduling_result='All six dispatched while the original master workers remained active',
        result=p.ref(WORK/'result.json'), authorization=p.ref(p.AUTH), preflight=p.ref(p.PREFLIGHT),
        overlap=p.ref(WORK/'concurrent-start.json'), ledger_snapshot=p.ref(WORK/'ledger-after.json'),
        diagnostic_slots=own, intervening_non_diagnostic_slots=master_slots, receipts=receipts,
        all_original_schemas_valid=True, extra_calls=0, owner_attempts_reopened=False,
        legal_acceptance=False, integration_complete=False, statistically_supported_ranking=False,
        source=p.ref(__file__), checked_at_utc=p.utc(),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip(),
        environment=str(p.ROOT/'.venv/bin/python'), devices='CPU only; GPU intentionally hidden',
        seed='N/A: provider seed unavailable; no ranking',
        plan=authorization['plan']))
    print(json.dumps({k:p.read(output)[k] for k in ('status','diagnostic_slots',
          'intervening_non_diagnostic_slots','all_original_schemas_valid','legal_acceptance')}))


if __name__ == '__main__':
    main()
