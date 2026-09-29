"""Retain unfinished source-bound proposal sets without certifying their meaning."""
from pathlib import Path
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import evidence_file,read_evidence
from legalmath.interpretation.assurance.semantics import check_quotes,validate_inventory,merge_inventories
from legalmath.interpretation.search.models import Reading
from legalmath.interpretation.contracts import parse
from assurance_successor_audit import journal_receipt
import json


def read(path):return json.loads(Path(path).read_text())


def collect(root,task):
    """Read only the task's active revision and verify its retained producer journal."""
    root=Path(root).resolve();arm=task['ensemble']
    if arm.get('dossier'):
        d=read_evidence(arm['dossier'],root)
        packet=read_evidence(d['packet'],root);candidates=read_evidence(d['candidates'],root)
        receipt={'profile':'complete-dossier-proposals','dossier':arm['dossier'],
                 'packet':d['packet'],'candidates':d['candidates']}
    else:
        if not arm.get('evidence_directory'):return None
        directory=(root/arm['evidence_directory']).resolve()
        if not directory.is_relative_to(root):raise LegalMathError('E_REFERENCE')
        state_path=directory/'current-state.json'
        if not state_path.exists():return None
        state=read(state_path);revision=state['revision']
        history=read(directory/'revisions.json')
        row=next((r for r in history if r['revision']==revision),None)
        if row is None or digest(row['binding'])!=revision:raise LegalMathError('E_INTEGRITY')
        current=directory/'revisions'/revision
        journal,state=journal_receipt(current/'core/actions/journal.json')
        actions=[a for a in state['actions'] if a['spec']['stage']=='interpretation' and a['status']=='EXECUTED']
        if not actions:return None
        action=actions[-1];result=read(journal.directory/action['result_file'])
        location=Path(result['directory']).resolve()
        expected=(journal.directory/f"action-{action['sequence']:04}"/'interpretation').resolve()
        if location!=expected or not location.is_relative_to(root):raise LegalMathError('E_INTEGRITY')
        if not (location/'candidates.json').exists():return None
        packet=read(location/'packet.json');candidates=read(location/'candidates.json')
        initial=read(location/'inventories-initial.json')
        for inventory in initial.values():validate_inventory(inventory,packet)
        initial_claims=merge_inventories(initial)
        receipt={'profile':'unfinished-investigation-proposals.v1','revision':revision,
            'producer_journal':evidence_file(journal.path,root),'producer_action':action['sequence'],
            'packet':evidence_file(location/'packet.json',root),
            'candidates':evidence_file(location/'candidates.json',root),
            'initial_inventories':evidence_file(location/'inventories-initial.json',root),
            'initial_claims_retained':len(initial_claims),'active_claims':evidence_file(location/'claims.json',root),
            'active_claim_count':len(read(location/'claims.json')),
            'core_execution_complete':result['report']['execution_complete'],
            'source_fidelity_established':False,'complete_investigation':False}
    if digest(packet)!=task['shared_packet_hash']:raise LegalMathError('E_INTEGRITY',details='Partial result differs from frozen shared packet')
    for candidate in candidates.values():
        if parse(Reading,candidate)!=candidate:raise LegalMathError('E_SCHEMA')
        check_quotes(candidate['citations'],packet)
    return {'packet':packet,'candidates':candidates,'receipt':receipt,
            'legal_correctness_established':False,'release_eligible':False}
