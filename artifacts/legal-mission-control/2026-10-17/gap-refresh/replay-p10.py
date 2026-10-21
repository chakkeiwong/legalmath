"""Capture the actual failing request without a provider call or reservation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
from copy import deepcopy
import json
import shutil
import sys
import time
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import BASE, PROGRAM, TOKENIZER
from scripts.legal_integration_campaign import provider
from scripts.legal_integration_phased_live import LIVE
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_instructions, account_input, account_output, downstream_instructions, account_receipt
from legalmath.interpretation.assurance.phased.evidence_store import load_exact

WORK = Path(__file__).resolve().parent
mode = sys.argv[1] if len(sys.argv) > 1 else 'before'
require(mode in ('before', 'after'), 'Unknown replay mode')
began = time.monotonic()
program = read(ROOT / PROGRAM)
revision = program['repair_execution']
ledger = ref(ROOT, BASE / 'live-calls.json')
common = ROOT / revision['common_directories']['p10']
directory = WORK / ('replay-p10-' + mode)
require(not directory.exists(), 'Never overwrite a replay')
shutil.copytree(common / 'calls', directory / 'calls')
service = provider()
def forbidden(*args, **kwargs):
    raise AssertionError('No provider completion or reservation in local replay')
service.complete = forbidden
service.allowance.reserve = forbidden
# The after replay tests constructor/dispatch identity locally. Current live
# binding is deliberately not adopted until the complete repair is reviewed.
service.allowance.check = lambda: read(ROOT / BASE / 'live-calls.json')
product = PhasedProduct(ROOT, directory, service,
    read(ROOT / program['prerequisite_repair']['source']['path']), tokenizer(ROOT / TOKENIZER),
    limits=Limits(), maximum_calls=8100, active_questions=['p10'],
    phase_admit=forbidden, phase_identity='local-exact-replay',
    requirement_account_profile=account_contract.PROFILE,
    requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,
    requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,
    requirement_account_recovery=revision['recoveries']['p10'],
    downstream_input_profile=revision['downstream_input_profile'],
    downstream_instruction_profile=downstream_instructions.PROFILE)
product.retained_acquisition = load_exact(ROOT / LIVE / 'acquisition/investigation.json')
checkpoint = read(ROOT / revision['recoveries']['p10']['path'])
old, schema, _, _ = account_receipt.checked(ROOT, checkpoint, 'detail-10', checkpoint['completed_account_receipts']['detail-10'])
seen, changes = [], []
def diff(a, b, path=''):
    if type(a) is not type(b):
        changes.append({'path':path, 'kind':'type'})
    elif isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b: changes.append({'path':path+'/'+key, 'kind':'missing'})
            else: diff(a[key], b[key], path+'/'+key)
    elif isinstance(a, list):
        if len(a) != len(b): changes.append({'path':path, 'kind':'length', 'old':len(a),'new':len(b)})
        for i, (x, y) in enumerate(zip(a, b)): diff(x, y, path+'/'+str(i))
    elif a != b: changes.append({'path':path,'kind':'value','old':a,'new':b})
original = product.dispatch.call
def capture(key, request, actual_schema, validate):
    seen.append(key)
    if key != 'detail-10':
        require(key in read(common / 'calls/dispatch.json')['calls'], 'Replay reached first missing assignment: '+key)
        return original(key, request, actual_schema, validate)
    (WORK / ('p10-request-' + mode + '.json')).write_text(json.dumps(request, ensure_ascii=False, indent=2)+'\n')
    a, b = deepcopy(old), deepcopy(request)
    for name in ('account_output_profile', 'account_capacity_profile'):
        a.pop(name, None); b.pop(name, None)
    diff(a, b)
    report = dict(mode=mode, differences=changes, schema_equal=schema==actual_schema,
        old_record_ids=[r['id'] for r in a['records']], current_record_ids=[r['id'] for r in b['records']],
        same_record_population={r['id']:r for r in a['records']}=={r['id']:r for r in b['records']})
    save(WORK / ('p10-diff-' + mode + '.json'), report)
    try:
        result = original(key, request, actual_schema, validate)
    except LegalMathError as exc:
        require(mode=='before' and exc.code=='E_INTEGRITY' and exc.details=='Receipt reuse changed source, assignment, instructions or response schema', 'Unexpected replay failure')
        report['reproduced_error'] = exc.details
    else:
        require(mode=='after' and result['status']=='VALIDATED', 'Repaired receipt did not validate')
        report['receipt_reused'] = True
    require(ref(ROOT, BASE / 'live-calls.json') == ledger, 'Local replay moved ledger')
    report.update(provider_calls=0, ledger_unchanged=True, seen=seen, wall_seconds=time.monotonic()-began)
    save(WORK / ('p10-replay-' + mode + '.json'), report)
    print({k:v for k,v in report.items() if k not in ('differences','seen','old_record_ids','current_record_ids')}, flush=True)
    raise SystemExit(0)
product.dispatch.call = capture
product.requirement_details()
raise AssertionError('Replay never reached detail-10')
