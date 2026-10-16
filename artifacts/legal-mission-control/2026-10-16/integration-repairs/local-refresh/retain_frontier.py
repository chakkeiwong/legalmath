"""Retain the newest exact P14 census, without granting retry eligibility."""
from pathlib import Path
from collections import Counter
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require, digest
from scripts.legal_integration_master import BASE, PROGRAM
from legalmath.interpretation.assurance.bounded_references import resolve

work = Path(__file__).resolve().parent
program = read(ROOT / PROGRAM)
common = ROOT / program['repair_execution']['common_directories']['p14']
dispatch = read(common / 'calls/dispatch.json')
ledger = read(ROOT / BASE / 'live-calls.json')
ledger_ref = ref(ROOT, BASE / 'live-calls.json')
phase = read(common / 'phases/reduction-p14-0/phase.json')
expected = {r['key'] for r in phase['contract']['calls']}
require(len(expected) == 90, 'Unexpected P14 synthesis population')
rows = []
for key, entry in sorted(dispatch['calls'].items()):
    directory = common / 'calls' / key
    result = read(directory / 'result.json')
    require(digest(result) == entry['result_hash'] and result['status'] == entry['status'],
            'Changed dispatch result')
    request, schema = read(directory / 'request.json'), read(directory / 'schema.json')
    require(digest(request) == result['request_hash'], 'Changed saved logical request')
    refs = {name: ref(ROOT, directory / (name + '.json')) for name in ('request', 'schema', 'result')}
    if key.startswith('detail-'):
        require(result['status'] == 'VALIDATED', 'Account frontier is not complete')
        disposition = 'RETAIN_ACCOUNT_SUCCESS'
        slot = result['provenance']['allowance_slot']
        refs['retained_initial'] = entry.get('retained_initial')
    else:
        require(key in expected, 'Unrecognized synthesis key')
        prepared = read(directory / 'reference-binding.json')
        refs['reference_binding'] = ref(ROOT, directory / 'reference-binding.json')
        wire_hash = digest(prepared['request'])
        slots = [i for i, r in enumerate(ledger['calls'], 1)
                 if r.get('stage_hash') == phase['admission']['sha256'] and r['request_hash'] == wire_hash]
        require(len(slots) <= 1, 'Repeated synthesis dispatch')
        slot = slots[0] if slots else None
        if slot:
            receipt_dir = ROOT / BASE / 'provider-evidence' / (f'{slot:04}-' + wire_hash[:16])
            receipt = read(receipt_dir / 'manifest.json')
            require(receipt['allowance_slot'] == slot and receipt['request_hash'] == wire_hash,
                    'Foreign synthesis receipt')
            require(read(receipt_dir / 'request.json') == prepared['request']
                    and read(receipt_dir / 'schema.json') == prepared['schema'], 'Changed wire contract')
            refs['receipt'] = ref(ROOT, receipt_dir / 'manifest.json')
            if result['status'] == 'VALIDATED':
                require(receipt['complete_output_present'] and
                        resolve(read(receipt_dir / 'result.json'), prepared, maximum_bytes=2_000_000) == result['value'],
                        'Synthesis success differs from actual response')
                disposition = 'RETAIN_SYNTHESIS_SUCCESS'
            else:
                require(not receipt['complete_output_present'], 'Unexpected completed rejection')
                disposition = 'CHARGED_FAILURE_NOT_AUTHORIZED_FOR_RETRY'
        else:
            require(result['status'] == 'FAILED' and result['error'] == 'E_RESOURCE_LIMIT'
                    and 'service circuit open' in result['reason'], 'Unsent request lacks local refusal')
            disposition = 'UNSENT_REQUIRES_VALID_SERVICE_AND_OWNER'
    rows.append(dict(key=key, disposition=disposition, slot=slot,
                     identity=entry['identity'], evidence=refs))
counts = dict(Counter(r['disposition'] for r in rows))
require(counts == {'RETAIN_ACCOUNT_SUCCESS': 36, 'RETAIN_SYNTHESIS_SUCCESS': 20,
    'CHARGED_FAILURE_NOT_AUTHORIZED_FOR_RETRY': 5, 'UNSENT_REQUIRES_VALID_SERVICE_AND_OWNER': 65},
    'P14 frontier changed')
require(ref(ROOT, BASE / 'live-calls.json') == ledger_ref, 'Census changed ledger')
save(work / 'p14-current-frontier.json', dict(profile='p14-retained-frontier-diagnostic.v1',
    counts=counts, rows=rows, dispatch=ref(ROOT, common / 'calls/dispatch.json'),
    phase=ref(ROOT, common / 'phases/reduction-p14-0/phase.json'), ledger=ledger_ref,
    provider_calls=0, automatic_retry_authorized=False, production_replay_completed=False,
    limit='Exact retained result and receipt census; a future continuation still needs production reconstruction, failure eligibility and reviewed authority.'))
print(counts)
