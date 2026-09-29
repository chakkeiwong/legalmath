"""Executable, bounded v2 investigation using retained or local providers.

Live adapters require a separately reviewed shared-allowance integration. This
route explicitly refuses them; its local action budget is not authorization for
live use. There are no hidden transport or schema retries.
"""
from copy import deepcopy
from pathlib import Path

from ...canonical import canonical, digest, raw_digest, loads
from ...errors import LegalMathError
from ..search.models import Settings
from . import fidelity_v2
from .diversity import save
from .workflow import EvidenceJournal


def investigate(packet, claims, candidates, questions, provider, out, *, required_pairs=None,
                batch_size=12, maximum_rounds=3, maximum_actions=200, deadline_seconds=3600,
                settings=None):
    if getattr(provider, 'live', True) is not False:
        raise LegalMathError('E_AUTHORITY', details='This local v2 route cannot authorize live dispatch')
    if (type(batch_size) is not int or not 1 <= batch_size <= 64 or
            type(maximum_rounds) is not int or not 1 <= maximum_rounds <= 6):
        raise LegalMathError('E_RESOURCE_LIMIT')
    settings = settings or Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000)
    pairs = sorted(required_pairs if required_pairs is not None else
                   [(c['claim_id'], r) for c in claims for r in candidates])
    if not pairs or len(pairs) > 4096 or len(pairs) != len(set(map(tuple, pairs))):
        raise LegalMathError('E_REFERENCE')
    batches = [pairs[i:i+batch_size] for i in range(0, len(pairs), batch_size)]
    # Validate every batch before reserving any action.
    requests = [fidelity_v2.request(packet, claims, candidates, questions, batch) for batch in batches]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    binding = {'protocol': fidelity_v2.PROTOCOL, 'requests': [digest(r) for r in requests],
        'route': deepcopy(getattr(provider, 'routing', provider.provider_id)),
        'provider': provider.provider_id, 'settings': settings.model_dump(),
        'pairs': pairs, 'batch_size': batch_size, 'maximum_rounds': maximum_rounds,
        'implementation': {p.name: raw_digest(p.read_bytes()) for p in
                           (Path(__file__), Path(fidelity_v2.__file__))}}
    journal = EvidenceJournal(out/'model', binding, maximum_actions=maximum_actions,
                              maximum_per_issue=6, deadline_seconds=deadline_seconds)
    report = journal.report()
    blocked = next((a for a in report['actions'] if a['status'] in ('FAILED', 'INTERRUPTED', 'RESERVED')), None)
    # An exception or process interruption cannot become a transport retry on resume.
    stopped = {'kind': 'PRIOR_DISPATCH_FAILURE', 'sequence': blocked['sequence'],
               'status': blocked['status']} if blocked else None
    results = []
    for index, (batch, base) in enumerate(zip(batches, requests)):
        proposals = []; attempts = []; diagnostics = []; reconciliation = None
        if blocked:
            for action in report['actions']:
                if action['status'] != 'EXECUTED':continue
                spec = action['spec']['inputs']['request']['investigation']
                if spec['batch'] != index:continue
                value = loads((journal.directory/action['result_file']).read_bytes())
                attempts.append({'round':spec['round'],'role':spec['perspective'],
                    'receipt':{'sequence':action['sequence'],'key':action['key'],
                               'result_hash':action['result_hash'],'reused':True},'status':value['status']})
                if value['status']=='VALIDATED_PROPOSAL':
                    proposals.append(fidelity_v2.validate(value['value'],packet,claims,candidates,questions,batch))
                else:diagnostics.append(value['diagnostic'])
            if proposals:
                reconciliation=fidelity_v2.reconcile(proposals,
                    attempt=max(a['round'] for a in attempts),maximum_attempts=maximum_rounds)
        for round_no in range(1, maximum_rounds+1):
            if stopped: break
            # Both requests in a round see only previous-round evidence. The
            # first round is therefore blind to any peer response.
            prior = {'proposals': deepcopy(proposals), 'diagnostics': deepcopy(diagnostics),
                     'disputes': deepcopy(reconciliation['disputes']) if reconciliation else []}
            for role in ('source-first', 'qualification-first'):
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
                    if len(canonical(request)) > settings.max_input_bytes:
                        raise LegalMathError('E_RESOURCE_LIMIT', details='Request exceeds bounded input size')
                    answer = provider.complete(request, inputs['schema'], settings)
                    save(work/'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
                    try:
                        if len(canonical(answer.value)) > settings.max_output_bytes:
                            raise LegalMathError('E_RESOURCE_LIMIT', details='Response exceeds bounded output size')
                        value = fidelity_v2.validate(answer.value, packet, claims, candidates, questions, batch)
                        return {'status': 'VALIDATED_PROPOSAL', 'value': value, 'provenance': answer.provenance}
                    except LegalMathError as exc:
                        if exc.code in ('E_INTEGRITY', 'E_AUTHORITY'): raise
                        return {'status': 'REJECTED_RESPONSE', 'diagnostic': {'error': exc.code, 'details': exc.details},
                                'provenance': answer.provenance}
                try:
                    value, receipt = journal.execute('scoped-fidelity', inputs, dispatch,
                        issue=f'batch.{index}.{role}', dependencies=[])
                except LegalMathError as exc:
                    if exc.code in ('E_INTEGRITY', 'E_STALE_REVIEW', 'E_AUTHORITY'): raise
                    stopped = {'kind':'DISPATCH_STOPPED','error':exc.code,'details':exc.details}
                    break
                except Exception as exc:
                    stopped = {'kind':'DISPATCH_STOPPED','error':type(exc).__name__}
                    break
                attempts.append({'round':round_no,'role':role,'receipt':receipt,'status':value['status']})
                if value['status']=='VALIDATED_PROPOSAL':proposals.append(value['value'])
                else:diagnostics.append(value['diagnostic'])
            if proposals:
                reconciliation=fidelity_v2.reconcile(proposals,attempt=round_no,maximum_attempts=maximum_rounds)
                if reconciliation['status']=='PROPOSED_JUDGMENTS_AGREE' and len(proposals)>=2:
                    break
            save(out/'next-action.json',{'batch':index,'completed_round':round_no,'stopped':stopped,
                'next_round':round_no+1 if round_no<maximum_rounds and not stopped else None,
                'reconciliation':reconciliation,'release_eligible':False})
        results.append({'required_pairs':[list(p) for p in batch],'attempts':attempts,
                        'proposals':proposals,'diagnostics':diagnostics,'reconciliation':reconciliation})
    addressed={tuple(p) for b in results if len(b['proposals'])>=2 for p in b['required_pairs']}
    expected=set(map(tuple,pairs))
    result={'status':'DISPATCH_BLOCKED' if stopped else 'UNCERTAINTY_REPORTED'
            if any(not b['reconciliation'] or b['reconciliation']['status']!='PROPOSED_JUDGMENTS_AGREE' for b in results)
            else 'PROPOSED_JUDGMENTS_AGREE', 'batches':results,'stopped':stopped,
        'required_pairs':[list(p) for p in pairs], 'pairs_with_two_validated_proposals':len(addressed),
        'pending_pairs':[list(p) for p in sorted(expected-addressed)],
        'journal_actions':journal.report()['consumed_actions'], 'pruned_pairs':[],
        'live_calls':0,'legal_accuracy_established':False,'release_eligible':False}
    save(out/'result.json',result)
    save(out/'next-action.json',{'status':result['status'],'pending_pairs':result['pending_pairs'],
        'stopped':stopped,'automatic_processing_complete':True,'release_eligible':False})
    return result
