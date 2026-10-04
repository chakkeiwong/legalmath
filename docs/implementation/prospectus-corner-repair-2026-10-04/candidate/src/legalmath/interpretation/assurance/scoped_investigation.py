"""Bounded v2 investigation; live dispatch requires an explicit additional grant.

Local action limits never authorize model requests. Both the durable action
journal and the shared nonrefundable live allowance precede dispatch.
"""
from copy import deepcopy
from pathlib import Path

from ...canonical import canonical, digest, raw_digest, loads
from ...errors import LegalMathError
from ..search.models import Settings
from . import fidelity_v2
from .diversity import save
from .workflow import EvidenceJournal
from .grants import GrantedAllowance
from ..search.providers import CodexProvider
from .decomposition import compact_request
from . import decomposition, source_references, executable_references, executable_references_v2

PERSPECTIVES = ('source-first', 'qualification-first')


def missing_perspectives(attempts):
    completed = {a['role'] for a in attempts if a['status'] == 'VALIDATED_PROPOSAL'}
    return sorted(set(PERSPECTIVES) - completed)


def fully_assessed_pairs(batches):
    """A schema-valid UNASSESSED response is not a completed dimension review."""
    complete=set()
    for batch in batches:
        latest={};proposals=iter(batch['proposals'])
        for attempt in batch['attempts']:
            if attempt['status']=='VALIDATED_PROPOSAL':latest[attempt['role']]=next(proposals)
        for pair in map(tuple,batch['required_pairs']):
            rows=[next((r for r in latest.get(role,{}).get('checks',[]) if
                        (r['claim_id'],r['candidate_id'])==pair),None) for role in PERSPECTIVES]
            if all(r and all(r[key]['status']!='UNASSESSED' for key in
                             ('source_support','question_relation','executable_correspondence','authority')) for r in rows):
                complete.add(pair)
    return complete


def investigate(packet, claims, candidates, questions, provider, out, *, required_pairs=None,
                batch_size=12, maximum_rounds=3, maximum_actions=200, deadline_seconds=3600,
                settings=None, pair_order='claim-first', schedule='batch-first', reference_protocol='literal'):
    live = getattr(provider, 'live', True) is not False
    grant_binding = None
    if live:
        if not isinstance(provider, CodexProvider) or not isinstance(provider.allowance, GrantedAllowance):
            raise LegalMathError('E_AUTHORITY', details='Live scoped investigation requires a recorded additional grant')
        grant_binding = provider.allowance.verify()
        grant_binding.pop('used')  # Consumption changes; authorization identity must not.
    if (type(batch_size) is not int or not 1 <= batch_size <= 64 or
            type(maximum_rounds) is not int or not 1 <= maximum_rounds <= 6):
        raise LegalMathError('E_RESOURCE_LIMIT')
    if schedule not in ('batch-first', 'round-first') or reference_protocol not in (
            'literal', source_references.PROTOCOL, executable_references.PROTOCOL, executable_references_v2.PROTOCOL):
        raise LegalMathError('E_SCHEMA')
    settings = settings or Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000)
    pairs = sorted([list(p) for p in required_pairs] if required_pairs is not None else
                   [[c['claim_id'], r] for c in claims for r in candidates])
    if not pairs or len(pairs) > 4096 or len(pairs) != len(set(map(tuple, pairs))):
        raise LegalMathError('E_REFERENCE')
    if pair_order not in ('claim-first','candidate-first'):raise LegalMathError('E_SCHEMA')
    if pair_order=='candidate-first':pairs.sort(key=lambda p:(p[1],p[0]))
    batches = [pairs[i:i+batch_size] for i in range(0, len(pairs), batch_size)]
    # Validate every batch before reserving any action.
    # Retain the whole source packet, but send only the claims/candidates this
    # batch actually asks about. Unrelated matrix rows remain in other batches;
    # they cannot consume the context budget or disappear from the denominator.
    requests = []
    for batch in batches:
        claim_ids={p[0] for p in batch};candidate_ids={p[1] for p in batch}
        requests.append(fidelity_v2.request(packet,[c for c in claims if c['claim_id'] in claim_ids],
            {k:v for k,v in candidates.items() if k in candidate_ids},
            {k:v for k,v in questions.items() if k in candidate_ids},batch))
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    binding = {'protocol': fidelity_v2.PROTOCOL, 'requests': [digest(r) for r in requests],
        'reconciliation_policy':'explicit-followups.v1','request_transport':'exact-source-text.compact.v2',
        'route': deepcopy(getattr(provider, 'routing', provider.provider_id)),
        'provider': provider.provider_id, 'grant': grant_binding, 'settings': settings.model_dump(),
        'pairs': pairs, 'batch_size': batch_size, 'maximum_rounds': maximum_rounds,
        'implementation': {p.name: raw_digest(p.read_bytes()) for p in
                           (Path(__file__), Path(fidelity_v2.__file__),Path(decomposition.__file__))}}
    if pair_order!='claim-first':binding['pair_order']=pair_order
    if schedule!='batch-first':binding['schedule']='round-first.v1'
    if reference_protocol!='literal':
        binding['source_reference_protocol']=reference_protocol
        binding['implementation']['source_references.py']=raw_digest(Path(source_references.__file__).read_bytes())
        if reference_protocol == executable_references.PROTOCOL:
            binding['implementation']['executable_references.py']=raw_digest(Path(executable_references.__file__).read_bytes())
        if reference_protocol == executable_references_v2.PROTOCOL:
            binding['implementation']['executable_references_v2.py']=raw_digest(Path(executable_references_v2.__file__).read_bytes())
            from .integrated import implementation_identity
            # Parsing, rendering and schema dependencies are part of this
            # method too; changing them must not silently reuse old responses.
            binding['executable_method'] = implementation_identity()
    journal = EvidenceJournal(out/'model', binding, maximum_actions=maximum_actions,
                              maximum_per_issue=6, deadline_seconds=deadline_seconds)
    report = journal.report()
    blocked = next((a for a in report['actions'] if a['status'] in ('FAILED', 'INTERRUPTED', 'RESERVED')), None)
    # An exception or process interruption cannot become a transport retry on resume.
    stopped = {'kind': 'PRIOR_DISPATCH_FAILURE', 'sequence': blocked['sequence'],
               'status': blocked['status']} if blocked else None
    results = [{'required_pairs': [list(p) for p in batch], 'attempts': [],
                'proposals': [], 'diagnostics': [], 'reconciliation': None} for batch in batches]
    if blocked:
        for action in report['actions']:
            if action['status'] != 'EXECUTED': continue
            spec = action['spec']['inputs']['request']['investigation']
            row = results[spec['batch']]
            value = loads((journal.directory/action['result_file']).read_bytes())
            row['attempts'].append({'round': spec['round'], 'role': spec['perspective'],
                'receipt': {'sequence': action['sequence'], 'key': action['key'],
                            'result_hash': action['result_hash'], 'reused': True}, 'status': value['status']})
            if value['status'] == 'VALIDATED_PROPOSAL':
                row['proposals'].append(fidelity_v2.validate(value['value'], packet, claims,
                                        candidates, questions, row['required_pairs']))
            else: row['diagnostics'].append(value['diagnostic'])
        for row in results:
            if row['proposals']:
                row['reconciliation'] = fidelity_v2.reconcile(row['proposals'],
                    attempt=max(a['round'] for a in row['attempts']), maximum_attempts=maximum_rounds)

    def run_round(index, round_no):
        nonlocal stopped
        row = results[index]; batch = batches[index]; base = requests[index]
        # Capture once, before either perspective runs. No same-round exposure.
        prior = {'proposals': deepcopy(row['proposals']), 'diagnostics': deepcopy(row['diagnostics']),
                 'disputes': deepcopy(row['reconciliation']['disputes']) if row['reconciliation'] else []}
        for role in PERSPECTIVES:
            request = deepcopy(base)
            request['investigation'] = {'batch': index, 'round': round_no, 'perspective': role,
                'prior_round_evidence': prior if round_no > 1 else None,
                'instruction': 'Investigate source support and question relation separately. '
                'Retain conflicting explanations; do not force agreement or a known answer. '
                'Use prior diagnostics to repair response shape without manufacturing support.'}
            inputs = {'request': request, 'schema': fidelity_v2.FidelityV2.model_json_schema(),
                      'settings': settings.model_dump()}
            def dispatch(work):
                save(work/'request.json', request)
                wire = compact_request(request, profile='v2'); save(work/'wire-request.json', wire)
                if len(canonical(wire)) > settings.max_input_bytes:
                    raise LegalMathError('E_RESOURCE_LIMIT', details='Request exceeds bounded input size')
                answer = None
                try:
                    if reference_protocol == executable_references_v2.PROTOCOL:
                        ids = {p[1] for p in batch}
                        answer = executable_references_v2.complete(provider, wire, inputs['schema'], settings,
                            work/'source-references', readings={k:v for k,v in candidates.items() if k in ids},
                            questions={k:v for k,v in questions.items() if k in ids})
                    elif reference_protocol in (source_references.PROTOCOL, executable_references.PROTOCOL):
                        transport = executable_references if reference_protocol == executable_references.PROTOCOL else source_references
                        answer = transport.complete(provider, wire, inputs['schema'], settings,
                                                            work/'source-references')
                    else:
                        answer = provider.complete(wire, inputs['schema'], settings)
                    save(work/'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
                    if len(canonical(answer.value)) > settings.max_output_bytes:
                        raise LegalMathError('E_RESOURCE_LIMIT', details='Response exceeds bounded output size')
                    value = fidelity_v2.validate(answer.value, packet, claims, candidates, questions, batch)
                    return {'status': 'VALIDATED_PROPOSAL', 'value': value, 'provenance': answer.provenance}
                except LegalMathError as exc:
                    # A returned invalid selection is a response failure; a
                    # failed dispatch still opens the existing circuit breaker.
                    raw = work/'source-references/raw-response.json'
                    if answer is None and (reference_protocol == 'literal' or not raw.exists()): raise
                    if exc.code in ('E_INTEGRITY', 'E_AUTHORITY'): raise
                    response = {'value': answer.value, 'provenance': answer.provenance} if answer else loads(raw.read_bytes())
                    bad = []
                    if isinstance(response['value'], dict) and isinstance(exc.details, dict):
                        bad = [r for r in response['value'].get('checks', []) if isinstance(r, dict) and
                               r.get('claim_id') == exc.details.get('claim_id') and
                               r.get('candidate_id') == exc.details.get('candidate_id')]
                    return {'status': 'REJECTED_RESPONSE', 'diagnostic': {'error': exc.code, 'details': exc.details,
                        'offending_checks': bad if len(canonical(bad)) <= 12000 else []}, 'provenance': response['provenance']}
            try:
                value, receipt = journal.execute('scoped-fidelity', inputs, dispatch,
                    issue=f'batch.{index}.{role}', dependencies=[])
            except LegalMathError as exc:
                if exc.code in ('E_INTEGRITY', 'E_STALE_REVIEW', 'E_AUTHORITY'): raise
                stopped = {'kind': 'DISPATCH_STOPPED', 'error': exc.code, 'details': exc.details}
                break
            except Exception as exc:
                stopped = {'kind': 'DISPATCH_STOPPED', 'error': type(exc).__name__}
                break
            row['attempts'].append({'round': round_no, 'role': role, 'receipt': receipt, 'status': value['status']})
            if value['status'] == 'VALIDATED_PROPOSAL': row['proposals'].append(value['value'])
            else: row['diagnostics'].append(value['diagnostic'])
        if row['proposals']:
            row['reconciliation'] = fidelity_v2.reconcile(row['proposals'], attempt=round_no, maximum_attempts=maximum_rounds)
        save(out/'next-action.json', {'schedule': schedule, 'batch': index, 'completed_round': round_no,
            'stopped': stopped, 'next_round': round_no + 1 if round_no < maximum_rounds and not stopped else None,
            'reconciliation': row['reconciliation'], 'release_eligible': False})

    order = ([(b, r) for b in range(len(batches)) for r in range(1, maximum_rounds + 1)]
             if schedule == 'batch-first' else
             [(b, r) for r in range(1, maximum_rounds + 1) for b in range(len(batches))])
    finished = set()
    for index, round_no in order:
        if stopped: break
        if index in finished: continue
        run_round(index, round_no)
        row = results[index]
        if (row['reconciliation'] and row['reconciliation']['status'] == 'PROPOSED_JUDGMENTS_AGREE'
                and not missing_perspectives(row['attempts'])):
            finished.add(index)
    for row in results:
        row['missing_perspectives'] = missing_perspectives(row['attempts'])
    addressed={tuple(p) for b in results if not b['missing_perspectives'] for p in b['required_pairs']}
    assessed=fully_assessed_pairs(results)
    expected=set(map(tuple,pairs))
    issued_hashes=set()
    for action in journal.report()['actions']:
        ref_wire=journal.directory/f"action-{action['sequence']:04}"/'source-references/wire-request.json'
        wire=loads(ref_wire.read_bytes()) if ref_wire.exists() else compact_request(action['spec']['inputs']['request'],profile='v2')
        issued_hashes.add(digest(wire))
    live_calls=sum(c['request_hash'] in issued_hashes for c in loads(provider.allowance.path.read_bytes())['calls']) if live and provider.allowance.path.exists() else 0
    result={'schedule':schedule,'source_reference_protocol':reference_protocol,'continuation_policy':'explicit-followups.v1','status':'DISPATCH_BLOCKED' if stopped else 'UNCERTAINTY_REPORTED'
            if any(b['missing_perspectives'] or not b['reconciliation'] or
                   b['reconciliation']['status']!='PROPOSED_JUDGMENTS_AGREE' for b in results)
            else 'PROPOSED_JUDGMENTS_AGREE', 'batches':results,'stopped':stopped,
        'required_pairs':[list(p) for p in pairs], 'pairs_with_two_validated_proposals':len(addressed),
        'pairs_with_four_dimensions_assessed':len(assessed),
        'pairs_with_unassessed_dimensions':[list(p) for p in sorted(set(map(tuple,pairs))-assessed)],
        'pending_pairs':[list(p) for p in sorted(expected-addressed)],
        'journal_actions':journal.report()['consumed_actions'], 'pruned_pairs':[],
        'live_calls':live_calls,
        'live_call_accounting':'Issued shared-ledger reservations whose request hash belongs to this investigation',
        'legal_accuracy_established':False,'release_eligible':False}
    save(out/'result.json',result)
    save(out/'next-action.json',{'status':result['status'],'pending_pairs':result['pending_pairs'],
        'stopped':stopped,'automatic_processing_complete':True,'release_eligible':False})
    return result
