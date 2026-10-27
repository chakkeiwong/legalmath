"""Capture production warrant requests for saved adverse context decisions.

No provider invocation or acceptance decision is permitted by this diagnostic.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import os
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts import legal_integration_phased_live as live, legal_integration_campaign as campaign
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read, save, ref, require, digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import review_repair
from legalmath.interpretation.assurance.phased.source_review import assignments

class Captured(BaseException):
    pass

HERE = isolation.HERE
SOURCE = ROOT/isolation.RUNTIME/'arms/p14/baseline'
NAMES = ('context-review-52f9d8408f730498e1a374b0.json',
         'context-review-f8e46deb40aec27916cc9661.json')
TARGETS = {
    'product_fn2': ['source:d996fc27b2d2e.u41.7404:0'],
    'product_fn3': ['source:d996fc27b2d2e.u42.7511:0'],
    'product_fn4': ['source:d996fc27b2d2e.u43.7658:0'],
    'handbook_legal_status_continuation': ['source:handbook.oct2024.page7:0',
        'source:handbook.oct2024.page8:0', 'source:handbook.oct2024.page9:0'],
    'network_paragraphs_9_and_14': ['source:dfdc3eb665b8e.u0.0:2'],
    'complete_retained_appendix': ['source:d4b586a37635c.u0.0:0',
        'source:d4b586a37635c.u0.0:1', 'source:d4b586a37635c.u0.0:2'],
}

def coverage(ids):
    present = set(ids)
    return {name: dict(delivered=[rid for rid in values if rid in present],
        not_delivered=[rid for rid in values if rid not in present])
        for name, values in TARGETS.items()}

started = time.monotonic()
inputs = [(ref(ROOT, SOURCE/name), read(SOURCE/name)) for name in NAMES]
require(all(row['result']['status']=='VALIDATED' and
    row['result']['value']['verdict']=='REJECT' for _, row in inputs), 'Changed adverse baseline')
seed = read(ROOT/HERE/'seed.json')
program = deepcopy(read(ROOT/live.PROGRAM))
tag = digest(dict(seed=seed, script=Path(__file__).read_bytes().hex(),
    inputs=[pointer for pointer, _ in inputs]))[:16]
folder = HERE/'adverse-context-preflight'/tag
require(not (ROOT/folder/'result.json').exists(), 'Completed diagnostic already exists; read it')
program['review_repair']['deployment'].update(runtime=str(folder/'runtime'),
    arm_checkpoints=seed['arm_checkpoints'])
live.ROOT = campaign.ROOT = ROOT
service = campaign.provider()
def forbidden(*args, **kwargs):
    raise AssertionError('Offline diagnostic attempted provider dispatch')
service.complete = service.check_service = forbidden
service.check = lambda: read(ROOT/live.BASE/'live-calls.json')
captured = {}
def stop_at_audit(product, qid, question, answer, details, **kwargs):
    captured.update(product=product, qid=qid, question=question, answer=answer, details=details)
    raise Captured()
selected = lambda path: program if Path(path)==ROOT/live.PROGRAM else read(path)
print('Preparing unchanged product offline; provider methods forbidden.', flush=True)
with (patch.object(live, 'read', selected), patch.object(live, 'phase_admit',
        lambda owner: lambda name, count: dict(offline=True, owner=owner, name=name, count=count)),
        patch.object(PhasedProduct, 'audit_answer', stop_at_audit)):
    try:
        live.product_route('p14', None, service)
    except Captured:
        pass
require(captured.get('qid')=='p14', 'Wrong product entry')
p = captured['product']
answer, question, details = (captured[k] for k in ('answer', 'question', 'details'))
require(p.directory.is_relative_to(ROOT/folder), 'Diagnostic escaped its offline directory')
table = {row['id']: row for row in assignments(p, 'p14', p.current_dependencies)}
rows = []
for pointer, retained in inputs:
    require(ref(ROOT, ROOT/pointer['path'])==pointer, 'Adverse baseline changed')
    identity = retained['item']['id']
    require(table[identity]==retained['item'] and digest(answer)==retained['answer_hash'],
        'Wrong answer or assignment')
    call = {}
    def capture_call(key, request, schema, validate):
        call.update(key=key, request=request, schema=schema)
        raise Captured()
    with patch.object(p.dispatch, 'call', capture_call):
        try:
            review_repair.review_warrants(p, 'p14', question,
                dict(status='VALIDATED', value=answer), [retained['result']], details)
        except Captured:
            pass
    require(call and call['request']['task']=='ASSESS_REVIEW_WARRANT', 'Warrant builder not captured')
    payload = call['request']['payload']
    require(payload['answer']==answer and payload['review']==retained['result']['value']
        and payload['assigned_review_targets']==[retained['item']], 'Warrant context changed')
    target = folder/(identity+'.json')
    save(ROOT/target, call)
    delivered = [record['id'] for record in call['request']['records']]
    rows.append(dict(assignment=identity, context_receipt=pointer,
        context_delivered_ids=retained['delivered_ids'], warrant_delivered_ids=delivered,
        added_ids=sorted(set(delivered)-set(retained['delivered_ids'])),
        omitted_ids=sorted(set(retained['delivered_ids'])-set(delivered)),
        target_coverage=coverage(delivered), request=ref(ROOT,target),
        measurement=p.dispatch.measure(call['request'],call['schema'])))
    print(dict(captured=identity, records=len(delivered)), flush=True)
journal = p.directory/'calls/dispatch.json'
require(not journal.exists() or not read(journal)['calls'], 'Offline diagnostic reserved a call')
result = dict(at_utc=datetime.now(timezone.utc).isoformat(),
    engineering_status='CAPTURED', provider_calls=0, legal_acceptance=False,
    question='Which exact sources will the production warrant builder deliver for two saved new adverse reviews?',
    answer_hash=digest(answer), rows=rows,
    limits='Delivery only; targets are not universally necessary. No verdict is relabelled. Capturing a request does not validate its legal reasoning or the correction outcome.',
    wall_seconds=time.monotonic()-started)
save(ROOT/folder/'result.json', result)
print(dict(result=str(folder/'result.json'), provider_calls=0, captured=len(rows)), flush=True)
