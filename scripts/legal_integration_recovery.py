"""One reviewed repair of the existing master; no new grant or attempt reset."""
from dataclasses import replace, asdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import math
import os
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import BASE, DOC, TOKENIZER, QUESTIONS, TOOLS, read, save, ref, require
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer, citation_dependencies, _indexed_locator_spans
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, AUDIT, PROFILE
from legalmath.interpretation.search.providers import Completion

REPAIR = BASE / 'live-repair'
LIMITS = replace(Limits(), records_per_request=2)
ARM_BUFFER = 16
COMMON_CAP = 640


class ReferenceRehearsal:
    """Exercise findings and quotations at the wire, with no legal conclusions."""
    live = False
    reference_transport = True

    def __init__(self): self.requests = []

    def complete(self, request, schema, settings):
        self.requests.append({'task': request['task'], 'request_hash': digest(request)})
        props = schema['properties']
        spans = request['response_spans']
        def quote(rid=None, locator=False):
            # Prefer a small bounded span over an entire large source chunk.
            candidates = [s for s in spans if rid is None or s['record_id'] == rid]
            selected = min(candidates, key=lambda s: s['end_codepoint']-s['start_codepoint'])
            return {'span_id': selected['span_id']}
        def leaf(value, path=()):
            if isinstance(value, str) and value: return list(path), value[:200]
            items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else []
            for k, v in items:
                found = leaf(v, (*path, k))
                if found: return found
            return None
        if 'records' in props:
            rows = []
            for record in request['records']:
                row = {'id': record['id'], 'status': 'UNRESOLVED', 'findings': [],
                       'open_dependencies': ['Scripted exercise; substantive interpretation is unresolved.']}
                if request['task'] == 'REVIEW_REQUIREMENTS':
                    observed = leaf(record['value'])
                    row['observations'] = ([] if observed is None else [{'record_id': record['id'],
                        'path': observed[0], 'quote': observed[1],
                        'statement': 'This exact field is a retained requirement or metadata observation, not law.'}])
                else:
                    row['findings'] = [{'statement': 'Source text retained with its unresolved analysis.',
                        'support': [quote(record['id'])], 'contrary': []}]
                rows.append(row)
            value = {'records': rows}
        elif 'readings' in props:
            units = request['source_packet']['units']
            value = {'readings': [{'local_id': 'candidate.scope', 'family': 'scope',
                'subject': 'Conditional source reading', 'statement': 'The governing standard is unresolved.',
                'distinction': 'Facts and standards are separate.', 'citations': [quote(units[0]['unit_id'])],
                'assumptions': [], 'questions': ['Which standard applies?'], 'formalization': None}],
                'dimensions': [{'dimension': d, 'status': 'AMBIGUOUS', 'source_unit_ids': [units[0]['unit_id']],
                    'explanation': 'Scripted control.'} for d in ('scope','definitions','exceptions','modality','time','dependencies')],
                'coverage': [{'unit_id': u['unit_id'], 'status': 'UNCERTAIN', 'reason': 'Not interpreted.'} for u in units],
                'questions': ['Substantive review required.']}
        elif 'arguments' in props:
            value = {'arguments': [], 'attacks': [], 'preferences': [], 'cases': [], 'case_queries': [],
                     'questions': ['No warranted argument in scripted mechanics.']}
        else:
            support = [quote(locator=True)] if spans else []
            if 'verdict' in props:
                value = {'verdict': 'UNRESOLVED', 'considered': request['required_considered'],
                    'reason': 'Scripted exercise retains uncertainty.', 'support': support,
                    'issues': ['Actual legal interpretation is not established.'], 'source_gaps': []}
            else:
                value = {'conclusion': 'The retained conditional answer depends on standards and facts.',
                    'support': support, 'contrary': [], 'assumptions': [],
                    'unresolved': ['Retain original source and requirement accounts; substantive review remains open.'],
                    'alternatives': [{'condition': 'The required premise is established', 'consequence': 'Reassess the conclusion.'}],
                    'considered': request['required_considered'], 'source_gaps': []}
        return Completion(value, {'provider': 'SCRIPTED_REFERENCE_REHEARSAL', 'live': False})


def make_product(directory, service=None):
    return BoundedProduct(ROOT, ROOT/directory, service or ReferenceRehearsal(),
        read(ROOT/BASE/'combined-envelope.json'), tokenizer(ROOT/TOKENIZER),
        limits=LIMITS, maximum_calls=4096)


def selected_canary_records(product, question):
    route = product.route
    if question != 'gatecoin':
        wanted = {'p10': ['P10','FN1'], 'p14': ['P14','FN5'], 'evidence': ['P11','FN1']}[question]
        index = route.envelope['legal_indexes'][0]
        ids = []
        for locator in wanted:
            spans = _indexed_locator_spans(index, route.units, locator)
            require(bool(spans), 'Missing canary provision '+locator)
            for s in spans:
                ids.extend(r['id'] for r in route.records.values() if r['kind']=='source' and
                    r['unit_id']==s['unit_id'] and r['start']<s['end'] and r['end']>s['start'])
        return list(dict.fromkeys(ids)), {'source_index': index['index_hash'], 'locators': wanted}
    phrases = ['The transactions described in the 7th scenario did not exist',
               'The 5th to 7th scenarios prima facie fall outside']
    ids = []
    for phrase in phrases:
        found = [r for r in route.records.values() if r['kind']=='source' and phrase in r['text']]
        require(bool(found), 'Missing Gatecoin source anchor: '+phrase)
        ids.append(found[0]['id'])
    return list(dict.fromkeys(ids)), {'exact_anchors': phrases,
        'limitation': 'Exact unit quotes; rendered paragraph review does not yet create a complete legal index.'}


def prepare_requests():
    from scripts.legal_integration_campaign import provider
    directory = ROOT/REPAIR
    require(not (ROOT/BASE/'recovery-approval.json').exists(), 'Approved recovery is immutable')
    directory.mkdir(parents=True, exist_ok=True)
    dry, service = make_product(REPAIR/'preparation'), provider()
    dry.dispatch.provider = service  # Measurement only; no allowance check or call.
    packets, blocked = dry.route.reading_plan()
    dependencies, unresolved = citation_dependencies(dry.route.envelope)
    bridges, bridge_blocks = dry.route.dependency_packets(dependencies)
    require(not (blocked+unresolved+bridge_blocks), 'Recovery has undeliverable source records')
    measurements = [dry.dispatch.measure(p['request'], p['schema']) for p in packets+bridges]
    save(directory/'acquisition-measurements.json', measurements)
    canary_refs = []
    for q in dry.route.envelope['original_questions']:
        ids, rationale = selected_canary_records(dry, q['question_id'])
        packet = dry.route.make_packet('READ_SOURCE', ids, reader='repair-canary', question_ids=[q['question_id']])
        request = dry.request('AUDIT_ANSWER_AGAINST_SOURCE', q, [dry.route.records[i] for i in ids],
            payload={'conclusion': 'A recorded action alone conclusively establishes full compliance; '
                'no further legal standard, contrary passage or client fact matters.',
                'control': 'Deliberately unsupported overstatement; reject it using the supplied source.'}, expected=ids)
        path = directory/'canaries'/(q['question_id']+'.json')
        save(path, {'question': q['question_id'], 'reading': packet, 'review_request': request,
            'review_schema': AUDIT, 'source_selection': rationale,
            'reading_measurement': dry.dispatch.measure(packet['request'],packet['schema']),
            'review_measurement': dry.dispatch.measure(request,AUDIT)})
        canary_refs.append(ref(ROOT,path))
    source_count = sum(r['kind']=='source' for r in dry.route.records.values())
    populations = {q: {'requirements': sum(r['kind'] in ('obligation','reading','case') and dry.applicable(r,q)
        for r in dry.route.records.values()), 'source_chunks': source_count} for q in QUESTIONS}
    for p in populations.values():
        p.update(common_call_cap=COMMON_CAP, answer_call_cap=p['requirements']+(source_count+1)//2+ARM_BUFFER,
                 comparison_call_cap=6, arms=['baseline',*TOOLS])
    scope = {'canaries':8,'acquisition':len(packets+bridges),'common_preparation':4*COMMON_CAP,
        'answers':7*sum(p['answer_call_cap'] for p in populations.values()),
        'comparisons':144,'cross_question_reviews':42}
    charged = len(read(ROOT/BASE/'live-calls.json')['calls'])
    total = charged+sum(scope.values())
    require(total <= 8100,'Recovery stages exceed unchanged global ceiling')
    result = {'scope':scope,'populations':populations,'charged_before_repair':charged,
        'total_including_first_execution':total,'global_ceiling':8100,'limits':asdict(LIMITS),
        'canaries':canary_refs,'acquisition_measurements':ref(ROOT,directory/'acquisition-measurements.json'),
        'disposition':'Prepared local recovery only; no service authority until qualification and approved migration.',
        'maximum_provider_input_tokens':max(m['provider']['local_tokens'] for m in measurements),
        'arm_buffer':ARM_BUFFER,'common_cap':COMMON_CAP,'source_review_group_minimum':2,
        'uncertainty':'Finite stage caps can still refuse adaptive work; no silent retries or omission.'}
    save(directory/'resource-envelope.json', result)
    return result


def rehearse():
    from scripts.legal_product_completion import run_product
    service = ReferenceRehearsal()
    envelope = read(ROOT/BASE/'combined-envelope.json')
    directory = ROOT/REPAIR/'rehearsal-qualified'
    implementation = [ref(ROOT,p) for p in (Path(__file__).relative_to(ROOT),
            Path('src/legalmath/interpretation/assurance/bounded_references.py'),
            Path('src/legalmath/interpretation/assurance/bounded_product.py'),
            Path('src/legalmath/interpretation/assurance/bounded_context.py'))]
    save(directory/'implementation-at-start.json',implementation)
    result = run_product(ROOT,directory,service,Path('/unused-jdk'),'2026-10-13T00:00:00Z',
        sources=[],questions=envelope['original_questions'],acceptance_ref=None,qualification={},
        required={'maximum_calls':4096},deadline_utc=read(ROOT/BASE/'live-grant.json')['deadline_utc'],
        selected_tools=[],settings=None,consumer_profile=PROFILE,bounded_envelope=envelope,
        bounded_encode=tokenizer(ROOT/TOKENIZER),bounded_limits=LIMITS)
    outcome = {'scripted_calls':len(service.requests),'retained_calls':len(read(directory/'calls/dispatch.json')['calls']),
        'live_calls':0,'trace':result['trace'],
        'questions':{q: {'status':v.get('status','EXECUTED'),'reason':v.get('reason'),
            'answer_validated':v.get('answer',{}).get('status')=='VALIDATED'} for q,v in result['answers'].items()},
        'input_hash':digest(envelope),'legal_acceptance':False,
        'implementation':implementation}
    save(directory/'summary.json',outcome)
    return outcome


def activate():
    from scripts import legal_integration_campaign as campaign
    campaign.LIVE = REPAIR/'live'
    campaign.LIMITS = LIMITS
    campaign.CANARIES = REPAIR/'canaries'
    campaign.RESOURCES = REPAIR/'resource-envelope.json'
    campaign.ARM_BUFFER = ARM_BUFFER
    campaign.COMMON_CAP = COMMON_CAP
    campaign.SOURCE_REVIEW_GROUP_MINIMUM = 2


def approval_packet():
    from scripts.legal_mission_execution import verify
    grant = read(ROOT/BASE/'live-grant.json')
    proposal = read(ROOT/BASE/'approval-proposal.json')
    resources = read(ROOT/REPAIR/'resource-envelope.json')
    rehearsal = read(ROOT/REPAIR/'rehearsal-qualified/summary.json')
    require(all(v['answer_validated'] for v in rehearsal['questions'].values()),
            'Repaired original-input rehearsal did not reach every answer')
    for reference in rehearsal['implementation']: verify(ROOT,reference)
    replacements = {}
    for old in proposal['bindings']:
        current = ref(ROOT,old['path'])
        if current != old:
            archive = ref(ROOT,BASE/'approved-code'/old['path'])
            require(archive['sha256']==old['sha256'],'Missing approved-code archive')
            replacements[old['path']] = {'previous':old,'archive':archive,'current':current}
    snapshot = ROOT/REPAIR/'ledger-before.json'
    ledger = read(ROOT/BASE/'live-calls.json')
    require(len(ledger['calls'])==resources['charged_before_repair'],'Ledger changed during preparation')
    if snapshot.exists(): require(read(snapshot)==ledger,'Recovery ledger checkpoint changed')
    else: save(snapshot,ledger)
    state_snapshot = ROOT/REPAIR/'execution-before.json'
    from scripts.legal_integration_master import STATE
    if not state_snapshot.exists(): save(state_snapshot,read(ROOT/STATE))
    now = datetime.now(timezone.utc)
    # Acquisition and subsequent independent branches use two isolated providers.
    seconds_required = math.ceil(resources['scope']['canaries']*120 + (
        sum(resources['scope'].values())-resources['scope']['canaries'])*120/2 + 1800)
    seconds_available = math.floor((datetime.fromisoformat(grant['deadline_utc'])-now).total_seconds())
    require(seconds_available>=seconds_required,'Complete remaining stage caps exceed original deadline')
    evidence = [REPAIR/'resource-envelope.json',REPAIR/'rehearsal-qualified/summary.json',
        REPAIR/'verification.json',DOC/'integration-master-recovery-approval.md',
        Path('scripts/legal_integration_recovery.py'),
        Path('src/legalmath/interpretation/assurance/bounded_references.py')]
    bindings = [ref(ROOT,p) for p in evidence]+resources['canaries']
    result = {'profile':'integration-master-recovery-proposal.v1','grant_hash':digest(grant),
        'global_ceiling':grant['maximum_calls'],'deadline_utc':grant['deadline_utc'],
        'replacements':list(replacements.values()),'bindings':bindings,
        'ledger_before':ref(ROOT,snapshot),'execution_before':ref(ROOT,state_snapshot),
        'resources':ref(ROOT,REPAIR/'resource-envelope.json'),'seconds_required':seconds_required,
        'seconds_available_at_preparation':seconds_available,'attempts':'Original first attempts retained; one acquisition recovery only.',
        'command':'.venv-context/bin/python scripts/legal_integration_recovery.py approve-and-run',
        'resume_command':'.venv-context/bin/python scripts/legal_integration_master.py live'}
    save(ROOT/REPAIR/'approval-proposal.json',result)
    return result


def approve_and_run():
    from scripts.legal_mission_execution import verify
    from scripts.legal_integration_master import MasterExecution,PROGRAM,STATE
    from scripts import legal_integration_campaign as campaign
    path = ROOT/BASE/'recovery-approval.json'
    require(not path.exists(),'Recovery already approved; use master live to resume')
    proposal = read(ROOT/REPAIR/'approval-proposal.json')
    grant = read(ROOT/BASE/'live-grant.json')
    require(proposal['grant_hash']==digest(grant),'Original grant changed')
    for r in proposal['bindings']: verify(ROOT,r)
    for row in proposal['replacements']:
        verify(ROOT,row['archive']); verify(ROOT,row['current'])
    require(read(ROOT/BASE/'live-calls.json')==read(ROOT/proposal['ledger_before']['path']),
            'Ledger changed since approval preparation')
    remaining=(datetime.fromisoformat(grant['deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
    require(remaining>=proposal['seconds_required'],'Approval no longer fits original clock')
    save(path,{'profile':'integration-master-recovery-approval.v1','approved':True,
        'approval_text':'User approved the concrete repair and reallocation within the original grant, '
            'including eight fresh canaries and 479 acquisition calls; first charges and deadline retained.',
        'proposal':ref(ROOT,REPAIR/'approval-proposal.json'),'grant_hash':digest(grant),
        'approved_at_utc':datetime.now(timezone.utc).isoformat()})
    execution=MasterExecution(ROOT,PROGRAM,STATE)
    for q in QUESTIONS:
        execution.retry('acquire-'+q,'Reviewed bounded reference/observation/output recovery; first attempt retained.')
    activate()
    return campaign.live()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','rehearse','approval-packet','approve-and-run'])
    args=parser.parse_args()
    actions={'prepare':prepare_requests,'rehearse':rehearse,'approval-packet':approval_packet,
             'approve-and-run':approve_and_run}
    print(json.dumps(actions[args.action](),indent=2))


if __name__=='__main__': main()
