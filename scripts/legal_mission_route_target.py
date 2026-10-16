"""Retained-target production-transport diagnostic; no model or legal evaluation.

The retained inventory is incomplete and the readings came from another run.
Local capture checks input delivery only. Scripted reviews deliberately retain
UNRESOLVED status and cannot certify completeness or legal support.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import sys
import time

from legalmath.canonical import canonical, digest, loads
from legalmath.domain import timestamp
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import (
    abstractions, evidence_tables, fidelity_v2, source_context, source_references,
    staged_source_review,
)
from legalmath.interpretation.assurance.decomposition import partition, piece_request
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.optional_tools import ToolSession, adapter_results
from legalmath.interpretation.assurance.route_admission import admission, workload
from legalmath.interpretation.assurance.semantics import Inventory, Fidelity, fidelity_request, merge_inventories
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.outputs import CONVENTION
from legalmath.interpretation.search.formal import bundle
from legalmath.interpretation.search.models import Generation, Settings, generation_request
from legalmath.interpretation.search.providers import Completion
from scripts.legal_integration_tools import ProductToolBackend

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol-inventory-window'
REPAIR = ROOT/'artifacts/legal-mission-control/2026-10-11/route-repair'
PARTIAL = ROOT/'artifacts/legal-mission-control/2026-10-10/evidence-route-design/requests/retained-partial-cross.json'
HISTORY = ROOT/'artifacts/legal-integration-coverage/2026-10-08/inputs.json'
LIMITS = Settings(max_input_bytes=200000, max_output_bytes=200000,
    max_logical_input_bytes=evidence_tables.MAXIMUM, max_expanded_output_bytes=evidence_tables.MAXIMUM)


def read(path):
    return loads(Path(path).read_bytes())


def ref(path):
    return {'path':str(Path(path).relative_to(ROOT)), 'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


class Captured(Exception):
    """Intentional stop after actual encoded input reaches a local provider."""


class LocalBoundary:
    live = False
    provider_id = 'test.retained-target-boundary'

    def __init__(self, directory, context):
        self.directory, self.source_context = directory, context
        self.source_context_root = ROOT
        self.scripted_review = False
        self.last = None

    def complete(self, wire, schema, settings):
        directory = sorted(self.directory.glob('call-*'))[-1]/'source-references'
        expected = read(directory/'expanded-wire-request.json')
        decoded = evidence_tables.decode(wire, expected_request_hash=digest(expected),
            expected_packet_hash=digest(expected['source_packet']))
        require(decoded == expected, 'Transport changed exact evidence')
        source_context.check_envelope(decoded, self.source_context)
        self.last = {'task':decoded['task'], 'encoded_bytes':len(canonical(wire)),
            'logical_bytes':len(canonical(expected)), 'schema_bytes_separate':len(canonical(schema)),
            'wire_hash':digest(wire), 'prepared_hash':digest(expected),
            'source_units':len(decoded['source_packet']['units']),
            'tool_checks_delivered':len(decoded.get('external_tool_context',{}).get('checks',[])),
            'transport':ref(directory/'encoding-validation.json')}
        if not self.scripted_review:
            raise Captured('Input delivered; response and legal reasoning deliberately untested')
        units = [u['unit_id'] for u in decoded['source_packet']['units']]
        if decoded['task'] == 'REVIEW_SOURCE_CLAIMS':
            spans = decoded['source_references']['spans']
            texts = {u['unit_id']:u['text'] for u in decoded['source_packet']['units']}
            rows = []
            for claim in decoded['claims']:
                unit = claim['evidence'][0]['unit_id']
                whole = next(s['span_id'] for s in spans if s['unit_id'] == unit
                    and s['start_codepoint'] == 0 and s['end_codepoint'] == len(texts[unit]))
                rows.append({'claim_id':claim['claim_id'], 'claim_hash':digest(claim),
                    'assessment':'UNRESOLVED', 'source_reading':claim['statement'],
                    'support':[{'span_ids':[whole]}], 'contrary':[],
                    'qualifications':['SCRIPTED DELIVERY ONLY: the attached source has not been legally assessed.'],
                    'missing_authorities':[], 'nonlocal_claim_ids':[]})
            value = {'request_binding':decoded['request_binding'], 'checked_unit_ids':units,
                'claims':rows, 'unresolved_questions':['Incomplete original inventory; second reader absent.']}
        elif decoded['task'] == 'REVIEW_SOURCE_OMISSIONS':
            value = {'checked_unit_ids':units, 'issues':[],
                'unresolved_questions':['SCRIPTED ONLY. Two source units have no retained inventory; independent qualification reader absent.']}
        else:
            raise RuntimeError('Unreviewed scripted response task')
        return Completion(value, {'provider':self.provider_id, 'scripted':True, 'live_calls':0})


def qualify(directory):
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    require(ref(PARTIAL)['sha256'] == 'bd405ed5813f45e6e3519d760bb652fc0bcc2b210b2cbd5d2cd1fa8b90211dec', 'Partial evidence changed')
    require(ref(HISTORY)['sha256'] == '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf', 'Historical evidence changed')
    packet_path = Path(read(RUN/'baseline/result.json')['details']['interpretation_directory'])/'packet.json'
    packet, context = read(packet_path), read(RUN/'qualified-source-context.json')
    # This decoder reads the sealed prototype format only. Every new request
    # below uses the current production codec through CompactProvider.
    from scripts.legal_mission_evidence_route_design import decode as read_old_format
    retained = read(PARTIAL)
    inventory = read_old_format(retained['wire'], expected_request_hash=retained['prepared_hash'],
        expected_packet_hash=context['compact_packet_hash'])['inventory']
    claims = merge_inventories({'atomic-reader':inventory})
    require((len(packet['units']),len(claims),len(inventory['units'])) == (55,78,53), 'Target population changed')
    missing_units = sorted({u['unit_id'] for u in packet['units']} - {u['unit_id'] for u in inventory['units']})
    history = read(HISTORY)
    mapping = {}
    for old in history['packet']['units']:
        matches = [u for u in packet['units'] if u['text'].count(old['text']) == 1]
        require(len(matches) == 1, 'Ambiguous historical source mapping')
        mapping[old['unit_id']] = matches[0]['unit_id']

    def remap(node):
        if isinstance(node,dict):
            return {k:mapping[v] if k == 'unit_id' and v in mapping else
                [mapping.get(x,x) for x in v] if k == 'source_unit_ids' else remap(v)
                for k,v in node.items()}
        if isinstance(node,list):return [remap(v) for v in node]
        return deepcopy(node)

    candidates, questions = remap(history['candidates']), remap(history['questions'])
    require(len(candidates) == 12 and set(questions) == set(candidates), 'Reading population changed')
    selected = [c for c in claims if c['relevance'] != 'CONTEXT']
    formalized, unformalized = {}, {}
    for cid, reading in candidates.items():
        try:bundle(reading,packet,timestamp('2026-10-10T00:00:00.000000Z'))
        except LegalMathError as exc:unformalized[cid] = exc.code
        else:formalized[cid] = reading
    require((len(selected),len(formalized),len(unformalized)) == (67,6,6), 'Core classification changed')
    save(directory/'input-classification.json', {'source_mapping':mapping, 'uncovered_source_units':missing_units,
        'partial_inventory_complete':False, 'actual_claims':len(claims), 'formalized_readings':list(formalized),
        'unformalized_readings':unformalized, 'not_a_same_run_dossier':True,
        'original_claims_hash':digest(claims), 'inputs':[ref(packet_path),ref(PARTIAL),ref(HISTORY),ref(RUN/'qualified-source-context.json')]})
    results = {}
    deadline = datetime.fromisoformat(read(REPAIR/'admission.json')['expires_utc'])
    for arm in ('baseline','candidate'):
        out = directory/arm
        local = LocalBoundary(out/'transport',context)
        tools = ToolSession(ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)),out/'tools') if arm == 'candidate' else None
        provider = CompactProvider(local,local.directory,reference_protocol=source_references.PROTOCOL,
            input_profile=evidence_tables.PROFILE,optional_tools=tools)
        records = []

        def measure(request, model, *, scripted=False, stage_candidates=None):
            require(datetime.now(timezone.utc) < deadline, 'Original attempt deadline exhausted')
            local.last = None
            local.scripted_review = scripted
            record = {'task':request['task'], 'request_hash':digest(request),
                'assigned_pairs':request.get('required_pairs',[]), 'scripted_review':scripted}
            try:
                if tools is not None and stage_candidates is not None:
                    tools.candidates(packet,stage_candidates)
                answer = provider.complete(request,model.model_json_schema(),LIMITS)
                record.update(status='SCRIPTED_RESPONSE_DELIVERED', **local.last)
                return answer.value
            except Captured:
                record.update(status='INPUT_DELIVERED_NO_RESPONSE', **local.last)
                return None
            except LegalMathError as exc:
                record.update(status='REFUSED',error=exc.code,details=exc.details)
                return None
            finally:
                records.append(record)
                save(out/'requests.json',records)

        pieces = partition(packet,20000,32)
        for i,piece in enumerate(pieces):
            # Same source piece on each role, different instruction identity.
            for role in ('atomic-reader','qualification-reader'):
                measure(piece_request(piece,role,i,len(pieces),digest(packet)),Inventory)

        def invoke(request,model,validate):
            value = measure(request,model,scripted=True)
            return validate(value) if value is not None else None

        reviewed = staged_source_review.run(packet,'atomic-reader',inventory,invoke,out/'scripted-source-review',batch_size=20)
        if reviewed is not None:
            require(merge_inventories({'atomic-reader':reviewed}) == claims, 'Scripted review changed raw claims')
            view = staged_source_review.search_view({'atomic-reader':reviewed},claims)
            findings = [{'kind':'PARTIAL_RETAINED_INVENTORY','uncovered_unit_ids':missing_units,
                'missing_reader':'qualification-reader','qualification':'Scripted findings are legally unassessed.'}]
            for role in ('normative','controlled-language','alternatives'):
                request = generation_request(packet,role)
                request['instructions'] += CONVENTION
                request.update(reviewed_source_evidence=view,source_inventory_findings=findings)
                measure(request,Generation)
        for role in ('actor-component-reader','scope-time-reader'):
            measure(abstractions.request(packet,role),abstractions.AbstractionBatch)

        core_pairs = [(c['claim_id'],cid) for c in selected for cid in formalized]
        core_assigned = []
        for start in range(0,len(core_pairs),32):
            pairs = core_pairs[start:start+32]
            scoped_candidates = {k:v for k,v in formalized.items() if k in {cid for _,cid in pairs}}
            measure(fidelity_request(packet,claims,formalized,pairs),Fidelity,stage_candidates=scoped_candidates)
            core_assigned.extend(pairs)
        require(core_assigned == core_pairs, 'Core pair assignment changed')
        all_pairs = sorted((c['claim_id'],cid) for c in claims for cid in candidates)
        scoped_assigned = Counter()
        from legalmath.interpretation.assurance.scoped_investigation import PERSPECTIVES
        for start in range(0,len(all_pairs),12):
            pairs = all_pairs[start:start+12]
            claim_ids, candidate_ids = {a for a,_ in pairs}, {b for _,b in pairs}
            stage_candidates = {k:v for k,v in candidates.items() if k in candidate_ids}
            for role in PERSPECTIVES:
                request = fidelity_v2.request(packet,[c for c in claims if c['claim_id'] in claim_ids],
                    stage_candidates,{k:v for k,v in questions.items() if k in candidate_ids},pairs)
                request['investigation'] = {'batch':start//12,'round':1,'perspective':role,'prior_round_evidence':None,
                    'instruction':'Investigate source support and question relation separately. '
                    'Retain conflicting explanations; do not force agreement or a known answer. '
                    'Use prior diagnostics to repair response shape without manufacturing support.'}
                measure(request,fidelity_v2.FidelityV2,stage_candidates=stage_candidates)
                scoped_assigned.update(pairs)
        require(set(scoped_assigned) == set(all_pairs) and set(scoped_assigned.values()) == {2}, 'Scoped perspective assignment changed')
        delivered = [r for r in records if r['status'] != 'REFUSED']
        report = tools.report() if tools is not None else None
        save(out/'tool-report.json',report)
        results[arm] = {'request_count':len(records),'delivered':len(delivered),
            'refusals':[{'task':r['task'],'error':r['error'],'details':r['details']} for r in records if r['status'] == 'REFUSED'],
            'maximum_delivered_wire_bytes':max((r['encoded_bytes'] for r in delivered),default=0),
            'maximum_delivered_logical_bytes':max((r['logical_bytes'] for r in delivered),default=0),
            'maximum_separate_schema_bytes':max((r['schema_bytes_separate'] for r in delivered),default=0),
            'reviewed_claims':len(view['records']) if reviewed is not None else 0,
            'core_pairs_assigned':len(core_pairs), 'deterministic_unformalized_pairs':len(selected)*len(unformalized),
            'scoped_pairs_assigned_both_perspectives':len(scoped_assigned),
            'tool_ids_observed':sorted({a['tool_id'] for c in (report or {}).get('checks',[]) for a in adapter_results(c)}),
            'records':ref(out/'requests.json'),'tool_report':ref(out/'tool-report.json')}

    # A deliberately optimistic scenario already refutes the original budget:
    # only 78 claims split over two readers, no context repeat, semantic repair,
    # nominated interaction, or malformed-output repair. Not a safe live bound.
    required = workload(pieces=5,reader_claims=[39,39],selected_claims=67,all_claims=78,
        candidates=12,formalized_candidates=6,source_batch=20,core_batch=32,scoped_batch=12,
        context_passes=1,interaction_batches=0,search_calls=6,abstraction_calls=3,
        semantic_rounds=0,output_repairs=0,tool_enabled=True)
    eligibility = admission(required,{'core':23,'question_assignment':3,'scoped':82,
        'dossier_reviews':64,'interaction':1,'synthesis':1},deadline_utc='2026-10-12T04:28:01+00:00')
    require(not eligibility['admitted'], 'Unexpected feasibility: review the original allocation')
    result = {'status':'RETAINED_TARGET_DIAGNOSTIC_COMPLETE_LIVE_REFUSED', 'arms':results,
        'budget_scenario':'Optimistic hybrid lower scenario; not a complete live workload bound',
        'original_allocation_check':eligibility, 'source_units':55,'uncovered_inventory_units':missing_units,
        'actual_partial_claims':78,'historical_readings':12,'legal_quality_evaluated':False,
        'actual_response_qualification':False,'all_constructors_qualified':False,'tool_benefit_evaluated':False,
        'new_live_calls':0,'remaining_constructors':['second independent complete inventory',
            'nominated source interactions','abstraction challenger with actual prior models',
            'search refinements and output repairs','semantic repairs/context repeats','actual dossier and final answer on original target'],
        'command':'.venv/bin/python scripts/legal_mission_route_repair.py run',
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':{'python':sys.version,'device':'CPU; CUDA_VISIBLE_DEVICES=-1 set by master','seed':'N/A: deterministic input diagnostic'},
        'data_version':[ref(PARTIAL),ref(HISTORY),ref(packet_path)],
        'plan':ref(ROOT/'docs/plans/legal-mission-route-repair.md'), 'method':ref(Path(__file__)),
        'finished_utc':datetime.now(timezone.utc).isoformat(), 'wall_milliseconds':round(1000*(time.monotonic()-started))}
    save(directory/'result.json',result)
    return result
