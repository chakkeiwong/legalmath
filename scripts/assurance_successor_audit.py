"""Recheck preserved evidence independently of phase-summary status flags."""
from pathlib import Path
from copy import deepcopy
from collections import Counter,defaultdict
import hashlib

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal, loads
from legalmath.interpretation.assurance import fidelity_v2, scoped_investigation


def journal_receipt(path):
    path = Path(path)
    envelope = loads(path.read_bytes())
    binding = envelope['value']['binding']
    journal = EvidenceJournal(path.parent, binding['inputs'],
        maximum_actions=binding['maximum_actions'],
        maximum_per_issue=binding['maximum_per_issue'],
        deadline_seconds=binding['deadline_seconds'])
    state = journal.report()  # Checks envelope, action identity, result and files.
    return journal, state


def check_scoped_result(path, packet, claims, candidates, questions):
    """Rebuild judgments from journal rows rather than trusting inline copies."""
    path = Path(path)
    result = loads(path.read_bytes())
    journal, state = journal_receipt(path.parent/'model/journal.json')
    consumed = set();continuation=[]
    policy=state['binding']['inputs'].get('reconciliation_policy','legacy-labels.v1')
    if policy not in ('legacy-labels.v1','explicit-followups.v1'):raise LegalMathError('E_INTEGRITY')
    if policy=='explicit-followups.v1' and result.get('continuation_policy')!=policy:raise LegalMathError('E_INTEGRITY')
    for index, batch in enumerate(result['batches']):
        reconstructed = []
        for attempt in batch['attempts']:
            receipt = attempt['receipt']
            seq = receipt['sequence']
            if type(seq) is not int or not 0 <= seq < len(state['actions']) or seq in consumed:
                raise LegalMathError('E_INTEGRITY', details='Invalid or duplicate scoped receipt')
            consumed.add(seq)
            action = state['actions'][seq]
            spec = action['spec']['inputs']['request']['investigation']
            if (action['status'] != 'EXECUTED' or action['key'] != receipt['key'] or
                action['result_hash'] != receipt['result_hash'] or
                spec['batch'] != index or spec['perspective'] != attempt['role'] or
                spec['round'] != attempt['round']):
                raise LegalMathError('E_INTEGRITY', details='Scoped receipt differs from executed action')
            stored = loads((journal.directory/action['result_file']).read_bytes())
            if stored['status'] != attempt['status']:
                raise LegalMathError('E_INTEGRITY', details='Changed scoped action status')
            if stored['status'] == 'VALIDATED_PROPOSAL':
                reconstructed.append(fidelity_v2.validate(stored['value'], packet, claims,
                    candidates, questions, batch['required_pairs']))
        if reconstructed != batch['proposals']:
            raise LegalMathError('E_INTEGRITY', details='Scoped proposals differ from executed responses')
        if batch['missing_perspectives'] != scoped_investigation.missing_perspectives(batch['attempts']):
            raise LegalMathError('E_INTEGRITY')
        if reconstructed:
            round_no=max(a['spec']['inputs']['request']['investigation']['round']
                            for a in state['actions']
                            if a['spec']['inputs']['request']['investigation']['batch'] == index)
            maximum=state['binding']['inputs']['maximum_rounds']
            current=fidelity_v2.reconcile(reconstructed,attempt=round_no,maximum_attempts=maximum)
            if policy=='legacy-labels.v1':
                old=deepcopy(reconstructed)
                for proposal in old:
                    for row in proposal['checks']:row['followup_questions']=[]
                reconciliation=fidelity_v2.reconcile(old,attempt=round_no,maximum_attempts=maximum)
                reconciliation.pop('continuation_policy');reconciliation['proposals']=reconstructed
            else:reconciliation=current
            if reconciliation != batch['reconciliation']:
                raise LegalMathError('E_INTEGRITY', details='Changed reconciliation')
            continuation.append({'batch':index,'recorded_policy':policy,'current_status':current['status'],
                'remaining_rounds':maximum-round_no,
                'additional_followup_needed':current['additional_processing_required'] and not reconciliation['additional_processing_required']})
    if consumed != {a['sequence'] for a in state['actions'] if a['status'] == 'EXECUTED'}:
        raise LegalMathError('E_INTEGRITY', details='Executed scoped judgment omitted')
    expected = set(map(tuple, result['required_pairs']))
    addressed = {tuple(p) for b in result['batches'] if not b['missing_perspectives']
                 for p in b['required_pairs']}
    assessed = scoped_investigation.fully_assessed_pairs(result['batches'])
    if (result['pairs_with_two_validated_proposals'] != len(addressed) or
        result.get('pairs_with_four_dimensions_assessed',len(assessed)) != len(assessed) or
        set(map(tuple, result['pending_pairs'])) != expected-addressed):
        raise LegalMathError('E_INTEGRITY', details='Changed scoped denominator or completion count')
    return {'status':'EXECUTED_SCOPED_EVIDENCE_RECHECKED', 'required_pairs':len(expected),
            'executed_actions':len(consumed), 'assessed_pairs':len(assessed),
            'current_continuation_checks':continuation,
            'legal_accuracy_established':False}


def audit_journals(directory):
    receipts = []
    for path in sorted(Path(directory).rglob('journal.json')):
        envelope = loads(path.read_bytes())
        # Other components have separate journal formats and their own verifier.
        if not (isinstance(envelope, dict) and set(envelope) == {'value','sha256'} and
                isinstance(envelope.get('value'), dict) and
                'maximum_per_issue' in envelope['value'].get('binding', {})):
            continue
        _, state = journal_receipt(path)
        receipts.append({'path':str(path), 'actions':len(state['actions']),
            'executed':sum(a['status']=='EXECUTED' for a in state['actions']),
            'failed_or_interrupted':sum(a['status']!='EXECUTED' for a in state['actions'])})
    return receipts


def check_pdf_result(path,root,expected_issues):
    """Verify a completed visual investigation without rebuilding peer order."""
    path=Path(path);root=Path(root);result=loads(path.read_bytes())
    expected={row['issue_id']:row for row in expected_issues}
    proposals=defaultdict(list);roles=defaultdict(set);followed=set();executed=0
    for job in result['jobs']:
        ident=(str(job['page'])+'-'+str(job['batch'])+'-'+job['role'])
        directory=path.parent/job['document']/ident
        journal,state=journal_receipt(directory/'journal.json')
        ids=set(job['issue_ids'])
        if len(ids)!=len(job['issue_ids']) or not ids<=set(expected):raise LegalMathError('E_INTEGRITY')
        for issue in ids:
            row=expected[issue];image=root/row['raster']
            if (row['document']!=job['document'] or row['page']!=job['page'] or
                hashlib.sha256(image.read_bytes()).hexdigest()!=row['original']['raster_sha256'] or
                state['binding']['inputs']['rendered_image']!=row['original']['raster_sha256']):
                raise LegalMathError('E_INTEGRITY',details='Visual judgment source changed')
            if job['role'] in roles[issue]:raise LegalMathError('E_INTEGRITY',details='Repeated visual role')
            roles[issue].add(job['role'])
            if job['role']=='discrepancy-followup':followed.add(issue)
        returned=[]
        for action in state['actions']:
            if action['status']=='EXECUTED':returned.append(loads((directory/action['result_file']).read_bytes()))
        valid=[v for v in returned if v['status']=='VALIDATED_PROPOSAL']
        summary={k:v for k,v in job['result'].items() if k!='reuse_receipt'}
        if valid:
            if len(valid)!=1 or summary!=valid[0]:raise LegalMathError('E_INTEGRITY',details='Detached visual result')
            rows=valid[0]['value']['judgments']
            if len(rows)!=len(ids) or {r['issue_id'] for r in rows}!=ids:raise LegalMathError('E_INTEGRITY')
            for row in rows:proposals[row['issue_id']].append({'role':job['role'],**row})
            executed+=1
        elif summary['status']=='UNRESOLVED_AFTER_REPAIR_LIMIT':
            if len(state['actions'])!=3 or summary['diagnostics']!=returned:raise LegalMathError('E_INTEGRITY')
        elif summary['status']=='FOLLOWUP_UNRESOLVED':
            if job['role']!='discrepancy-followup':raise LegalMathError('E_INTEGRITY')
        else:raise LegalMathError('E_INTEGRITY',details='Unexplained missing visual proposal')
    reconstructed=[]
    for ident in sorted(expected):
        if not {'pixel-first','qualification-first'}<=roles[ident]:raise LegalMathError('E_INTEGRITY')
        rows=proposals[ident]
        agrees=len(rows)>=2 and len({(r['disposition'],r['printed_text']) for r in rows})==1
        reconstructed.append({'issue_id':ident,'proposals':rows,
            'status':'TWO_VISUAL_PROPOSALS_AGREE' if agrees else 'VISUAL_UNCERTAINTY_RETAINED',
            'followup_attempted':ident in followed,'source_materiality_certified':False})
    if (result['items']!=reconstructed or result['total']!=len(expected) or
        result['counts']!=dict(Counter(r['status'] for r in reconstructed))):
        raise LegalMathError('E_INTEGRITY',details='Changed visual denominator or summary')
    return {'status':'COMPLETED_VISUAL_EVIDENCE_RECHECKED','issues':len(expected),
            'validated_jobs':executed,'counts':result['counts'],'source_materiality_certified':False}
