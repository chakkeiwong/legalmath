"""Exercise production reconstruction and fresh phase admission without wire calls."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys, time, json
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import BASE, PROGRAM, TOKENIZER
from scripts.legal_integration_campaign import provider
from scripts.legal_integration_phased_live import LIVE
from scripts.legal_mission_execution import read, save, ref, require
from legalmath.canonical import digest, canonical
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_instructions, account_input, account_output, downstream_instructions, account_recovery
from legalmath.interpretation.assurance.phased.admission import admit
from legalmath.interpretation.assurance.phased.evidence_store import load_exact

WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery')
q = sys.argv[1]
require(q in ('p10', 'evidence'), 'Unknown replay question')
began = time.monotonic()
p = read(ROOT / PROGRAM)
baseline = read(ROOT / WORK / 'baseline.json')
held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
for path in (BASE / 'live-calls.json', BASE / 'current-binding.json', BASE / 'live-grant.json', PROGRAM):
    require(ref(ROOT,path)['sha256'] == held[str(path)]['sha256'], 'Comparator changed')
directory = WORK / ('receipt-replay' if q == 'p10' else 'focused-replay') / q
require(not (ROOT / directory).exists(), 'Never overwrite replay')
recovery = ref(ROOT, WORK / ('recovery-' + q + ('-v2' if q == 'p10' else '') + '.json'))
checkpoint = read(ROOT / recovery['path'])
isolated = directory / 'admission-base'
for name in ('current-binding.json', 'live-grant.json', 'live-calls.json'):
    save(ROOT / isolated / name, read(ROOT / BASE / name))
service = provider()
def forbidden(*a, **kw): raise AssertionError('Provider calls/reservation prohibited')
service.complete = forbidden
service.allowance.reserve = forbidden
class ReachedMissing(BaseException): pass
admissions = []
product = PhasedProduct(ROOT, ROOT / directory / 'product', service,
    read(ROOT / p['prerequisite_repair']['source']['path']), tokenizer(ROOT / TOKENIZER),
    limits=Limits(), maximum_calls=8100, active_questions=[q],
    phase_admit=forbidden, phase_identity=held[str(BASE / 'current-binding.json')]['sha256'],
    requirement_account_profile=account_contract.PROFILE,
    requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,
    requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE, requirement_account_recovery=recovery,
    downstream_input_profile=p['repair_execution']['downstream_input_profile'],
    downstream_instruction_profile=downstream_instructions.PROFILE)
product.retained_acquisition = load_exact(ROOT / LIVE / 'acquisition/investigation.json')
def admission(name,count):
    pointer = admit(ROOT, isolated, directory / 'admission', name, count, owner='prepare-' + q)
    phase = read(product.directory / 'phases' / name / 'phase.json')
    keys = phase['logical_dispatches']
    require(count == len(keys) == 1, 'Unexpected first phase population')
    key = keys[0]
    admissions.append({'phase':name,'key':key,'stage':pointer})
    if q == 'evidence': require(key == 'detail-25-part-1', 'Different evidence correction')
    raise ReachedMissing()
product.phase_admit = admission
product.install_dispatch_admission()
captured = {}
original = product.run_phase
def capture(name,calls):
    if q == 'evidence' and name == 'call-detail-25-part-1':
        require(len(calls) == 1, 'Unexpected correction calls')
        request = calls[0]['request']
        annotation = request.get('account_correction')
        require(annotation is not None, 'No actual correction annotation')
        base, _ = account_recovery.baseline_request(request,calls[0]['schema'],root=ROOT)
        account_recovery.validate_retained_correction(ROOT, annotation, base)
        require(annotation['prose_fields'] == ['/assumptions/2','/unresolved/0','/unresolved/5'], 'Changed correction scope')
        captured.update(key=calls[0]['key'], request=request, schema=calls[0]['schema'])
    return original(name,calls)
product.run_phase = capture
try:
    records = [r for r in product.route.records.values() if r['kind'] in ('obligation','reading','case')]
    targets = (4,25) if q == 'evidence' else (0,10,11)
    for i in targets:
        record = records[i]
        scope = set(product.requirement_questions(record))
        questions = [x for x in product.route.envelope['original_questions'] if x['question_id'] in scope]
        sources = product.route.retrieve(canonical(record['value']).decode())['record_ids']
        for question in questions: sources += product.route.retrieve(question['text'])['record_ids']
        sources = [rid for rid in dict.fromkeys(sources) if scope & product.acquisition_questions(product.route.records[rid])]
        product.note('detail-' + str(i),'ASSESS_ORIGINAL_REQUIREMENT',questions,
            [product.route.records[r] for r in sources],{**record,
            'coverage':'Delivered sources join requirement and applicable question retrieval. Absence from this local selection is not absence from the corpus or the law; identify incomplete coverage explicitly.'},[record['id']])
except ReachedMissing:
    pass
else: raise AssertionError('Expected first undispatched request')
require(len(admissions) == 1, 'No actual phase admission')
dispatch = read(product.dispatch.directory / 'dispatch.json')
require(all(r['status'] == 'VALIDATED' for r in dispatch['calls'].values()), 'Invalid reuse')
for key, row in dispatch['calls'].items():
    require('retained_initial' in row, 'Replay did not authenticate saved success')
reused_slots = sorted(row['retained_initial']['allowance_slot'] for row in dispatch['calls'].values()
    if 'allowance_slot' in row['retained_initial'])
if q == 'p10':
    require(reused_slots == [2190] and admissions[0]['key'] != 'detail-10', 'Charged receipt was not reused')
for path in (BASE / 'live-calls.json', BASE / 'current-binding.json', BASE / 'live-grant.json', PROGRAM):
    require(ref(ROOT,path)['sha256'] == held[str(path)]['sha256'], 'Replay changed production authority')
for path in baseline['dispatch_census']:
    require(ref(ROOT,path)['sha256'] == held[path]['sha256'], 'Replay changed old dispatch')
if captured: save(ROOT / directory / 'correction-request.json',captured)
report = dict(verdict='PASS', question=q, recovery=recovery, provider_calls=0,
    production_constructor=True, actual_phase_admission=True, isolated_admission=True,
    exact_successes=len(dispatch['calls']), first_missing=admissions[0],
    reused_receipt_slots=reused_slots,
    correction_scope_verified=bool(captured), ledger_unchanged=True, old_dispatches_unchanged=True,
    source=ref(ROOT,Path(__file__)), at_utc=datetime.now(timezone.utc).isoformat(),
    command=[sys.executable,str(Path(__file__).relative_to(ROOT)),q],
    environment=sys.executable, devices='CPU only; CUDA_VISIBLE_DEVICES=-1',
    wall_seconds=time.monotonic()-began, legal_acceptance=False,
    target_roots=list(targets),
    limitation='Focused constructor and first new phase; checkpoint integrity checked; remaining constructors and final answers untested.')
save(ROOT / WORK / ('replay-' + q + ('-v2' if q == 'p10' else '') + '.json'),report)
print(json.dumps({k:report[k] for k in ('verdict','question','exact_successes','first_missing','wall_seconds')}),flush=True)
