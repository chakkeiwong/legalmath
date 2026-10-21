"""Exercise actual P14 reconstruction without dispatching its missing call."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import PROGRAM, BASE, TOKENIZER
from scripts.legal_integration_campaign import provider
from scripts.legal_integration_phased_live import LIVE
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_account_successor import CHECKPOINT, checked
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import (
    account_contract, account_encoding, account_instructions, account_input, account_output,
    downstream_instructions,
)
from legalmath.interpretation.assurance.phased.evidence_store import load_exact

WORK = Path(__file__).resolve().parent.relative_to(ROOT)
began = time.monotonic()
program = read(ROOT / PROGRAM)
revision = program['repair_execution']
frozen = read(ROOT / WORK / 'baseline.json')
archives = {r['previous']['path']: r['archive'] for r in frozen['archived']}
before = ref(ROOT, BASE / 'live-calls.json')
require(before['sha256'] == archives[str(BASE / 'live-calls.json')]['sha256'], 'Ledger moved after freeze')
common = Path(revision['common_directories']['p14'])
dispatch = read(ROOT / common / 'calls/dispatch.json')
envelope = read(ROOT / program['prerequisite_repair']['source']['path'])
service = provider()

def forbidden(*args, **kwargs):
    raise AssertionError('Provider completion/reservation forbidden in local replay')

service.complete = forbidden
service.allowance.reserve = forbidden
encode = tokenizer(ROOT / TOKENIZER)
product = PhasedProduct(ROOT, ROOT / WORK / 'production-replay', service, envelope, encode,
    limits=Limits(), active_questions=['p14'], phase_admit=forbidden, phase_identity='local-replay',
    requirement_account_profile=account_contract.PROFILE,
    requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,
    requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,
    requirement_account_recovery=revision['recoveries']['p14'],
    downstream_input_profile=revision['downstream_input_profile'],
    downstream_instruction_profile=downstream_instructions.PROFILE)
product.retained_acquisition = load_exact(ROOT / LIVE / 'acquisition/investigation.json')
rows = {key: {name: ref(ROOT, common / 'calls' / key / (filename + '.json'))
    for name, filename in (('request', 'request'), ('schema', 'schema'), ('result', 'result'))}
    for key in dispatch['calls']}
rows['detail-87']['reference_binding'] = ref(ROOT, common / 'calls/detail-87/reference-binding.json')
receipts = list((ROOT / BASE / 'provider-evidence').glob('2333-*/manifest.json'))
require(len(receipts) == 1, 'Ambiguous P14 provider receipt')
checkpoint = {
    'profile': CHECKPOINT, 'question': 'p14', 'input_hash': dispatch['input_hash'],
    'provider_binding': product.dispatch.provider_binding, 'failed_key': 'detail-87', 'failed_slot': 2333,
    'dispatch': ref(ROOT, common / 'calls/dispatch.json'),
    'phase': ref(ROOT, common / 'phases/call-detail-87/phase.json'),
    'ledger': archives[str(BASE / 'live-calls.json')], 'recovery': revision['recoveries']['p14'],
    'receipt': ref(ROOT, receipts[0]), 'rows': rows,
}
seen, successes, missing, measurements = [], [], [], []
original = product.dispatch.call

def replay_call(key, request, schema, validate):
    require(key in rows and key not in seen, 'Changed or duplicate P14 assignment')
    row = rows[key]
    require(request == read(ROOT / row['request']['path'])
        and schema == read(ROOT / row['schema']['path']),
        'Production reconstruction changed exact P14 request or schema')
    seen.append(key)
    measurements.append({'key': key, 'measurement': product.dispatch.measure(request, schema)})
    if dispatch['calls'][key]['status'] == 'FAILED':
        require(key == 'detail-87' and not missing,
            'First missing request differs from the reviewed P14 outage')
        require(prepare(request, schema) == read(ROOT / row['reference_binding']['path']),
            'Production reconstruction changed the failed wire request or schema')
        path = ROOT / WORK / 'failed-production-request.json'
        # Preserve actual constructor order: canonical JSON reorders hash-alias traversal.
        path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n')
        row['production_request'] = ref(ROOT, path)
        missing.append(key)
        # Keep the authenticated failure so later saved responses are also checked.
        return read(ROOT / row['result']['path'])
    result = original(key, request, schema, validate)
    require(result == read(ROOT / row['result']['path']) and result['status'] == 'VALIDATED',
        'P14 exact successful result changed on reuse')
    successes.append(key)
    return result

product.dispatch.call = replay_call
try:
    product.requirement_details()
except LegalMathError as exc:
    require(exc.code == 'E_DEPENDENCY' and exc.details ==
        'Inventory cannot replace source-grounded requirement accounts',
        'Replay hit a different product failure')
else:
    raise AssertionError('Production replay did not reach the exact interrupted request')
require(set(seen) == set(rows) and len(seen) == 36 and len(successes) == 35
    and missing == ['detail-87'],
    'Incomplete actual P14 replay')
save(ROOT / WORK / 'account-successor.json', checkpoint)
pointer = ref(ROOT, WORK / 'account-successor.json')
checked(ROOT, pointer)
require(ref(ROOT, BASE / 'live-calls.json') == before, 'Replay changed provider ledger')
report = {'verdict': 'PASS', 'provider_calls': 0, 'ledger_unchanged': True,
    'ledger': checkpoint['ledger'], 'checkpoint': pointer, 'production_reconstruction': True,
    'exact_contracts': len(seen), 'exact_successes': len(successes), 'first_missing_key': missing[0],
    'wire_contract_preserved': True, 'wire_contract_scope': 'failed detail-87 only; 35 saved results reuse original provenance',
    'execution_order': seen, 'measurements': measurements,
    'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'command': '.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)),
    'environment': sys.executable, 'devices': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
    'seeds': 'N/A: deterministic exact replay', 'wall_seconds': time.monotonic() - began,
    'source': ref(ROOT, Path(__file__)), 'plan': ref(ROOT, WORK / 'plan-review.md'),
    'legal_acceptance': False}
save(ROOT / WORK / 'successor-replay.json', report)
print({k: report[k] for k in ('verdict', 'provider_calls', 'exact_contracts', 'exact_successes',
    'first_missing_key', 'wall_seconds')}, flush=True)
