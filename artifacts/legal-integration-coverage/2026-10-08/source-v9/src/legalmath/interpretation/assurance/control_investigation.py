"""Resume a retained tree with question-specific, bounded source checks."""
from copy import deepcopy
from pathlib import Path
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ..contracts import parse
from ..search.models import Settings
from ..search.providers import Completion
from ..search.formal import bundle
from .controls import Routing, routing_request, validate_routing, routing_plan, validate_plan
from .semantics import Fidelity, fidelity_request, validate_fidelity
from .workflow import CachedEvidenceProvider
from .diversity import save, identity


def investigate_scoped(packet, claims, candidates, questions, provider, out, **limits):
    """Explicit v2 route; legacy investigate/replay semantics are unchanged."""
    from .scoped_investigation import investigate as scoped
    return scoped(packet, claims, candidates, questions, provider, out, **limits)


class BoundedReader:
    """Retain raw responses before validation; an output repair is another call."""
    def __init__(self, provider, directory, binding, *, maximum_actions=48, reuse_from=()):
        self.directory = Path(directory)
        self.provider = CachedEvidenceProvider(provider, self.directory/'model', binding,
            maximum_actions=maximum_actions, deadline_seconds=21600)
        self.settings = Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000)
        self.stopped_reason = None
        self.reuse_from = []
        for earlier in reuse_from:
            if earlier.provider.routing != self.provider.routing:
                raise LegalMathError('E_AUTHORITY', details='Cannot reuse a different provider route as this reader')
            journal=earlier.provider.journal
            report=journal.report()  # Checks every retained result and artifact hash.
            if any(a['status']=='RESERVED' for a in report['actions']):
                raise LegalMathError('E_JOB_STATE', details='Continuation needs a finished evidence checkpoint')
            self.reuse_from.append((journal.directory,raw_digest(journal.path.read_bytes()),report['actions']))

    def _retained(self, request, model):
        settings=self.settings.model_dump();settings.pop('timeout_seconds',None)
        inputs={'request':request,'schema':model.model_json_schema(),'settings':settings}
        for directory,journal_hash,actions in self.reuse_from:
            for action in reversed(actions):
                if action['status']!='EXECUTED' or action['spec']['inputs']!=inputs:
                    continue
                path=directory/action['result_file'];raw=path.read_bytes();value=loads(raw)
                if identity(value)!=action['result_hash']:
                    raise LegalMathError('E_INTEGRITY',details='Retained response changed during continuation')
                save(self.directory/'reused-responses'/(digest(inputs)+'.json'),{
                    'request_hash':digest(request),'prior_journal':str(directory/'journal.json'),
                    'prior_journal_sha256':journal_hash,'prior_result':str(path),
                    'prior_result_sha256':raw_digest(raw),'prior_action':action['sequence'],
                    'new_live_invocation':False,'evidence_reused':True})
                return Completion(value['value'],{**value['provenance'],
                    'new_live_invocation':False,'evidence_reused':True})
        return None

    def call(self, request, model, validate):
        if self.stopped_reason is not None:
            return None
        wire = request
        for attempt in range(2):
            try:
                answer = self._retained(wire, model) or self.provider.complete(
                    wire, model.model_json_schema(), self.settings)
                value = validate(answer.value)
                return value
            except LegalMathError as exc:
                if exc.code in ('E_INTEGRITY', 'E_STALE_REVIEW', 'E_AUTHORITY'):
                    raise
                diagnostic = {'request_hash': digest(wire), 'error': exc.code, 'details': exc.details}
                save(self.directory/'diagnostics'/(digest(diagnostic)+'.json'), diagnostic)
                if exc.code == 'E_RESOURCE_LIMIT':
                    resources = self.provider.journal.report()
                    if (exc.details == 'Shared live allowance or reviewed increment exhausted'
                            or not resources['remaining_actions'] or resources['deadline_exhausted']):
                        self.stopped_reason = str(exc.details or 'Persistent resource limit')
                if exc.code not in ('E_SCHEMA', 'E_REFERENCE', 'E_DUPLICATE_ID') or attempt:
                    return None
                wire = {**request, 'output_repair': {'attempt': attempt+1, 'diagnostic': diagnostic,
                    'instruction': 'Repair serialization/evidence only. Preserve uncertainty; do not assert support to satisfy validation.'}}
        return None


def route_with_repair(packet, claims, candidates, controls, reader, out, role):
    """Retry an invalid whole inventory in bounded, exactly accounted chunks.

    A chunk sees the full source and control definitions. It cannot discard an
    item or borrow an assignment from the other reader. Failed chunks leave the
    whole routing judgment incomplete; no keyword or majority fallback applies.
    """
    request = routing_request(packet, claims, candidates, controls, role)
    value = reader.call(request, Routing,
                        lambda v: validate_routing(v, packet, claims, candidates, controls))
    if value is not None:
        return value
    if getattr(reader, 'stopped_reason', None):
        return None
    candidate_items = list(candidates.items())
    count = max((len(claims)+15)//16, (len(candidate_items)+5)//6)
    chunks = []
    complete = True
    for i in range(count):
        selected_claims = claims[i*16:(i+1)*16]
        selected_candidates = dict(candidate_items[i*6:(i+1)*6])
        request = routing_request(packet, selected_claims, selected_candidates, controls, role)
        request['routing_repair'] = {
            'kind': 'BOUNDED_INVENTORY_SPLIT', 'index': i, 'count': count,
            'whole_claims_hash': digest(claims), 'whole_candidates_hash': digest(candidates),
            'required_claim_ids': [c['claim_id'] for c in selected_claims],
            'required_candidate_ids': list(selected_candidates),
            'instruction': 'Use exactly these item IDs, including candidate dictionary keys. '
                           'Reading local_id is not its inventory identity. Preserve uncertainty.'}
        part = reader.call(request, Routing, lambda v: validate_routing(
            v, packet, selected_claims, selected_candidates, controls))
        save(out/(role+'.chunk-'+str(i)+'.json'), part)
        if part is None:
            complete = False
            if getattr(reader, 'stopped_reason', None):
                break
        else:
            chunks.append(part)
    if not complete:
        return None
    merged = {field: [row for chunk in chunks for row in chunk[field]]
              for field in ('claims', 'candidates')}
    # Missing questions are retained without asking another model to summarize
    # away a qualification. Oversized unions fail closed under the Routing cap.
    merged['missing_questions'] = list(dict.fromkeys(
        question for chunk in chunks for question in chunk['missing_questions']))
    try:
        return validate_routing(merged, packet, claims, candidates, controls)
    except LegalMathError as exc:
        if exc.code not in ('E_SCHEMA', 'E_REFERENCE', 'E_DUPLICATE_ID'):
            raise
        save(out/(role+'.unmerged.json'), {'chunks': chunks, 'error': exc.code})
        return None


def investigate(packet, claims, candidates, controls, reader, out, at, *, batch_size=12):
    from .fidelity_batches import FidelityBatches
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    binding = {'packet': digest(packet), 'claims': digest(claims), 'candidates': digest(candidates),
               'controls': digest(controls), 'at': at, 'batch_size': batch_size}
    binding_file = out/'binding.json'
    if binding_file.exists() and loads(binding_file.read_bytes()) != binding:
        raise LegalMathError('E_STALE_REVIEW')
    save(binding_file, binding)
    routes = []
    for role in ('normative-routing', 'qualification-routing'):
        value = route_with_repair(packet, claims, candidates, controls, reader, out, role)
        save(out/(role+'.json'), value)
        if value is not None:
            routes.append(value)
    if len(routes) != 2:
        result = {'status': 'ROUTING_INCOMPLETE', 'full_claims': len(claims), 'full_candidates': len(candidates),
                  'full_pair_count': len(claims)*len(candidates), 'execution_complete': False,
                  'stopped_reason': getattr(reader, 'stopped_reason', None),
                  'unexamined_pairs': len(claims)*len(candidates), 'release_eligible': False}
        save(out/'result.json', result); return result
    plan = routing_plan(packet, claims, candidates, controls, routes)
    validate_plan(plan, packet, claims, candidates)
    save(out/'routing-plan.json', plan)
    # Route the entire inventory; CONTEXT is a judgment of the old slice, not
    # authority to omit it from this new question-specific comparison.
    selected = [{**c, 'relevance': 'CONTROL'} for c in claims]
    ledger = FidelityBatches(out/'batches.json', plan['required_pairs'], batch_size=batch_size)
    completed = {}; concerns = []; unsupported = {}
    for cid, reading in candidates.items():
        try: bundle(reading, packet, at)
        except LegalMathError as exc: unsupported[cid] = exc.code
    # Retained response validation protects resume from edited pair-ledger claims.
    for filename in ledger.state['completed']:
        path = out/'responses'/filename
        part = loads(path.read_bytes())
        pairs = ledger.state['completed'][filename]
        validate_fidelity(part, packet, selected, candidates, [tuple(p) for p in pairs])
        if filename != digest(part)+'.json': raise LegalMathError('E_INTEGRITY')
        for check in part['checks']: completed[(check['claim_id'], check['candidate_id'])] = check
        concerns += part['additional_concerns']

    def accept(part, pairs):
        nonlocal concerns
        size = (sum(len(canonical(v)) for v in completed.values())
                + len(canonical(concerns)) + len(canonical(part)))
        if len(concerns) + len(part['additional_concerns']) > 1080 or size > 2*1024*1024:
            save(out/'overflow'/(digest(part)+'.json'), part)
            return False
        filename = digest(part)+'.json'
        save(out/'responses'/filename, part)
        ledger.record(filename, pairs)
        for check in part['checks']: completed[(check['claim_id'], check['candidate_id'])] = check
        concerns += part['additional_concerns']
        return True

    queue = [(batch, 0) for batch in ledger.batches()]
    while queue:
        batch, depth = queue.pop(0)
        encoded = [p for p in batch if p[1] not in unsupported]
        unencoded = [p for p in batch if p[1] in unsupported]
        if unencoded:
            part = {'checks': [{'claim_id': a, 'candidate_id': b, 'label': 'NOT_ESTABLISHED',
                'source_evidence': [], 'representation_quotes': [], 'rationale': 'Reading cannot be encoded: '+unsupported[b],
                'failing_stage': 'FORMALIZATION', 'question': 'Retain original meaning and investigate encoding.'}
                for a, b in unencoded], 'additional_concerns': []}
            if not accept(part, unencoded): break
        if not encoded: continue
        req = fidelity_request(packet, selected, candidates, encoded)
        req['control_plan'] = {'controls': plan['controls'], 'candidate_bindings': {
            b: plan['bindings']['candidates'][b] for a, b in encoded}}
        req['instructions'] += (' Judge only the actual typed question. A related requirement applies '
            'to a partial control only to the extent its stated output claims to decide it. Report '
            'misassigned claims or lost remote qualifications in additional_concerns.')
        part = reader.call(req, Fidelity, lambda v: validate_fidelity(v, packet, selected, candidates, encoded))
        if part is None:
            if getattr(reader, 'stopped_reason', None):
                break  # An undispatched budget refusal is pending, not a model finding.
            ledger.record('failed.'+digest([list(p) for p in encoded]), encoded, status='FAILED')
            if depth < 1 and len(encoded) > 1:
                queue[0:0] = [(p, depth+1) for p in ledger.split(encoded)]
            continue
        if not accept(part, encoded): break
    report = {'status': 'CHECKS_EXECUTED' if not ledger.pending else 'FIDELITY_INCOMPLETE',
              'execution_complete': not ledger.pending, **ledger.report(),
              'checks': list(completed.values()), 'additional_concerns': concerns,
              'excluded_pairs': plan['excluded_pairs'], 'full_pair_count': plan['full_pair_count'],
              'findings': plan['findings'], 'missing_questions': plan['missing_questions'],
              'unsupported_candidates': unsupported,
              'stopped_reason': getattr(reader, 'stopped_reason', None),
              'original_claims': len(claims), 'original_candidates': len(candidates),
              'legal_completeness_established': False, 'release_eligible': False}
    save(out/'result.json', report)
    return report
