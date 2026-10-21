"""No-call replay of real candidate packets and the retained P14 output."""
from pathlib import Path
from hashlib import sha256
import json
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
STAGE = WORK/'staging'
sys.path[:0] = [str(STAGE/'src'), str(STAGE), str(ROOT)]
from legalmath.canonical import digest, canonical
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundDispatch, BoundedProduct
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.phased import capacity_policy as policy, capacity_checkpoint
from legalmath.interpretation.assurance.arguments import evaluate_criticism
from legalmath.interpretation.assurance.monitor import save

OLD = ROOT/'artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry'
BASE = ROOT/'artifacts/legal-mission-control/2026-10-13/master'


def read(path):
    return json.loads(path.read_text())


def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha256(path.read_bytes()).hexdigest())


def main():
    program = read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
    envelope = read(ROOT/program['prerequisite_repair']['source']['path'])
    encode = tokenizer(ROOT/'.localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken')
    route = ContextRoute(envelope, encode, limits=Limits())
    service = BoundedCodexProvider(ROOT, BASE, encode, route.limits, routing_file=BASE/'campaign-routing.toml')
    dispatch = BoundDispatch(service, WORK/'replay-measurements', route)
    dispatch.capacity_manager = object()  # Measure-only opt-in; call is never invoked.
    reports = {}
    for question in ('p10','p14','evidence','gatecoin'):
        row = read(OLD/'requests'/(question+'.json'))
        reports[question] = dispatch.measure(row['request'], row['schema'])
    folder = OLD/'live/p14/product/calls'
    calls = {}
    for key in ('candidates-p14', 'criticism-p14'):
        directory = folder/key
        row = {name: ref(directory/(name+'.json')) for name in ('request','schema','result')}
        if key == 'criticism-p14':
            row.update(mode='OUTPUT_BUDGET_REVALIDATION',
                reference_binding=ref(directory/'reference-binding.json'),
                transport_manifest=ref(BASE/'provider-evidence/3449-38a69a1728a57217/manifest.json'))
        else:
            row['mode'] = 'VALIDATED'
        calls[key] = row
    checkpoint_path = WORK/'replay-checkpoint.json'
    save(checkpoint_path, dict(profile=capacity_checkpoint.PROFILE, input_hash=route.input_hash, calls=calls))
    class NoCalls:
        live = False
        def complete(self, *args):
            raise AssertionError('Replay must never dispatch')
    product = BoundedProduct(ROOT, WORK/'p14-output-replay-reviewed', NoCalls(), envelope, encode,
        limits=route.limits, active_questions=['p14'], common_capacity_profile=policy.PROFILE,
        capacity_checkpoint=ref(checkpoint_path))
    req = read(folder/'criticism-p14/request.json')
    schema = read(folder/'criticism-p14/schema.json')
    result = product.dispatch.call('criticism-p14', req, schema,
        lambda value: evaluate_criticism(value, req['source_packet'], list(req['candidates'])))
    assert result['status'] == 'VALIDATED'
    evaluation = evaluate_criticism(result['value'], req['source_packet'], list(req['candidates']))
    assert evaluation['status'] == 'UNRESOLVED' and not evaluation['candidate_pruning_authorized']
    assert read(folder/'criticism-p14/result.json')['status'] == 'FAILED'
    # Reconstruct the actual failed baseline arm using its completed preparation
    # and calls. Unfinished reviews/warrants are intercepted locally. This checks
    # the generated answer/review requests, rather than hand-replaying their JSON.
    from legalmath.interpretation.assurance.phased.product import PhasedProduct
    from legalmath.interpretation.assurance.phased.account_contract import PROFILE as ACCOUNT
    from legalmath.interpretation.assurance.phased.account_encoding import PROFILE as ENCODING
    from legalmath.interpretation.assurance.phased.account_instructions import PROFILE as INSTRUCTIONS
    from legalmath.interpretation.assurance.phased.account_input import CAPACITY_PROFILE as ACCOUNT_CAPACITY
    from legalmath.interpretation.assurance.phased.account_output import PROFILE as ACCOUNT_OUTPUT
    from legalmath.interpretation.assurance.phased.downstream_input import CAPACITY_PROFILE as DOWNSTREAM_CAPACITY
    from legalmath.errors import LegalMathError
    arm = OLD/'live/arms/p14/baseline'
    journal = read(arm/'calls/dispatch.json')
    retained_calls = {}
    for key, recorded in journal['calls'].items():
        if recorded['status'] != 'VALIDATED': continue
        row = {n:ref(arm/'calls'/key/(n+'.json')) for n in ('request','schema','result')}
        row.update(mode='VALIDATED', dispatch=ref(arm/'calls/dispatch.json'))
        retained_calls[key] = row
    save(WORK/'baseline-replay-checkpoint.json',dict(profile=capacity_checkpoint.PROFILE,
        input_hash=route.input_hash,calls=retained_calls))
    class MissingOnly(NoCalls):
        reference_transport = True
        def __init__(self): self.requests=[]
        def complete(self,request,schema,settings):
            self.requests.append(request)
            raise LegalMathError('E_DEPENDENCY',details='Offline replay: missing work recorded, no provider called')
    probe = MissingOnly()
    revision = program['repair_execution']
    baseline = PhasedProduct(ROOT,WORK/'baseline-arm-wire-replay',probe,envelope,encode,limits=route.limits,
        active_questions=['p14'], maximum_calls=8100, maximum_corrections=1,
        phase_identity='offline-retained-arm-replay.v1',phase_admit=lambda name,count:dict(name=name,count=count),
        requirement_account_profile=ACCOUNT,requirement_account_input_profile=ENCODING,
        requirement_account_instruction_profile=INSTRUCTIONS,requirement_account_capacity_profile=ACCOUNT_CAPACITY,
        requirement_account_output_profile=ACCOUNT_OUTPUT, downstream_input_profile=revision['downstream_input_profile'],
        downstream_instruction_profile=revision['downstream_instruction_profile'],downstream_capacity_profile=DOWNSTREAM_CAPACITY,
        retained_preparation=program['candidate_capacity_retry']['checkpoints']['p14'],
        common_capacity_profile=policy.PROFILE,capacity_checkpoint=ref(WORK/'baseline-replay-checkpoint.json'))
    baseline.install_dispatch_admission()
    from scripts.legal_integration_phased_live import LIVE
    from legalmath.interpretation.assurance.phased.evidence_store import load_exact
    outcome=(load_exact(baseline.directory/'result.json') if (baseline.directory/'result.json').exists()
        else baseline.answer(load_exact(ROOT/LIVE/'acquisition/investigation.json')))
    assert outcome['answers']['p14']['answer']['value']==read(arm/'calls/answer-p14/result.json')['value']
    missing = [dict(key=p.parent.name,request=read(p.with_name('request.json')),result=read(p))
        for p in baseline.dispatch.directory.glob('*/result.json')]
    assert missing and all(r['request']['task'] in ('ASSESS_REVIEW_WARRANT','AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS')
        and r['result']['reason']=='Offline replay: missing work recorded, no provider called' for r in missing)
    imported=[read(p) for p in (baseline.directory/'capacity').glob('*/result.json')
        if read(p).get('provenance',{}).get('capacity_checkpoint')]
    assert len(imported)>=len(retained_calls)
    report = dict(verdict='PASS', provider_calls=0, source_packets=reports,
        p14=dict(replayed=True, original_failure_preserved=True, raw_bytes=24273, canonical_tokens=3909,
            current_output_tokens=policy.STAGES['STRUCTURED_CRITICISM'].output_tokens,
            current_output_bytes=policy.STAGES['STRUCTURED_CRITICISM'].output_bytes,
            result=ref(product.directory/'capacity/criticism-p14/result.json'),
            evaluation_status=evaluation['status'], legal_questions=len(evaluation['questions'])),
        retained_baseline=dict(result=ref(baseline.directory/'result.json'), preserved_calls=len(imported),
            answer_unchanged=True, missing_warrant_leaves=sum(r['request']['task']=='ASSESS_REVIEW_WARRANT' for r in missing),
            previously_blocked_source_reviews=sum(r['request']['task']=='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS' for r in missing),
            external_calls=0),
        legal_acceptance=False, scope='Capacity and exact reuse only; substantive criticism remains unresolved')
    save(WORK/'production-replay.json', report)
    print(json.dumps(dict(verdict=report['verdict'], provider_calls=0, p14=report['p14'],
        inputs={q:dict(tokens=m['local_tokens'], bytes=m['bytes']) for q,m in reports.items()}), indent=2))


if __name__ == '__main__':
    main()
