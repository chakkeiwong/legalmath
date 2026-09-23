"""Append-only post-search correspondence analysis, separate from legal release."""
from pathlib import Path
from ...canonical import digest
from ...domain import timestamp
from ...errors import LegalMathError
from ..service import ident
from .alignment import review_packet, validate_correspondence
from .formal import Comparisons
from .models import commitment


def _access(service, con, caller, run_id, review=False):
    if review:
        service._owner(con, caller, run_id, 'meaning')
        return
    try:
        service._owner(con, caller, run_id)
    except LegalMathError as exc:
        if exc.code != 'E_AUTHORITY':
            raise
        service._owner(con, caller, run_id, 'meaning')


def _context(service, con, run_id, left_id, right_id):
    run = service._run(con, run_id)
    row = con.execute('SELECT invalidated,cancelled,source_key FROM interpretation_runs WHERE id=?', (run_id,)).fetchone()
    current = con.execute('SELECT packet_hash FROM interpretation_sources WHERE source_key=?', (row['source_key'],)).fetchone()
    if row['invalidated'] or row['cancelled'] or current[0] != run['source_packet_hash']:
        raise LegalMathError('E_STALE_REVIEW')
    state = service._get(con, run_id, 'search-state', 'state')
    report = service._get(con, run_id, 'search-report', 'report')
    if (report['state_hash'] != digest(state) or report['source_packet_hash'] != run['source_packet_hash']
            or report['status'] not in ('BLOCKED_UNRESOLVED', 'READY_FOR_REVIEW')):
        raise LegalMathError('E_INTEGRITY')
    nodes = {n['node_id']: n for n in state['nodes']}
    if left_id == right_id or left_id not in nodes or right_id not in nodes:
        raise LegalMathError('E_REFERENCE')
    selected = [nodes[left_id], nodes[right_id]]
    for n in selected:
        if n['commitment'] != commitment(n['reading']) or n['encoding_error']:
            raise LegalMathError('E_INTEGRITY')
        candidate = service._get(con, run_id, 'candidate', n['candidate_id'])
        if candidate['bundle_hash'] != n['bundle_hash']:
            raise LegalMathError('E_INTEGRITY')
    return run, state, report, [n['reading'] for n in selected], service._packet(con, run)


def _bound(service, con, run_id, alignment_id):
    saved = service._get(con, run_id, 'alignment-proposal', alignment_id)
    context = _context(service, con, run_id, saved['left_node_id'], saved['right_node_id'])
    _, state, report, readings, packet = context
    if saved['search_state_hash'] != digest(state) or saved['report_hash'] != digest(report):
        raise LegalMathError('E_STALE_REVIEW')
    checked = validate_correspondence(saved['proposal'], *readings, packet)
    if saved['proposal_hash'] != checked['proposal_hash']:
        raise LegalMathError('E_INTEGRITY')
    return saved, context


def packet(service, caller, run_id, left_id, right_id):
    with service.db.connect() as con:
        _access(service, con, caller, run_id)
        _, state, report, readings, source = _context(service, con, run_id, left_id, right_id)
    return {**review_packet(*readings, source), 'run_id': run_id,
            'left_node_id': left_id, 'right_node_id': right_id,
            'search_state_hash': digest(state), 'report_hash': digest(report)}


def propose(service, caller, key, run_id, left_id, right_id, proposal):
    def op(con):
        service._owner(con, caller, run_id)
        _, state, report, readings, source = _context(service, con, run_id, left_id, right_id)
        checked = validate_correspondence(proposal, *readings, source)
        alignment_id = 'alignment.' + digest({'proposal': checked['proposal_hash'], 'left':left_id, 'right':right_id})[:32]
        old = [v for v in service._list(con, run_id, 'alignment-proposal') if v['alignment_id'] == alignment_id]
        if old:
            return old[0]
        value = {'run_id': run_id, 'alignment_id': alignment_id, 'proposer': caller,
                 'left_node_id': left_id, 'right_node_id': right_id,
                 'search_state_hash': digest(state), 'report_hash': digest(report),
                 'proposal_hash': checked['proposal_hash'], 'proposal': checked['proposal'],
                 'changed_declarations': checked['changed_declarations'], 'status': 'UNREVIEWED',
                 'release_eligible': False, 'recorded_at': service.clock()}
        service._save(con, 'alignment-proposal', value, alignment_id)
        return value
    return service.db.mutate(caller, key, {'op':'alignment.propose', 'run':run_id,
        'left':left_id, 'right':right_id, 'proposal':proposal}, op)


def _reviews(service, con, run_id, alignment_id):
    return [r for r in service._list(con, run_id, 'alignment-review') if r['alignment_id'] == alignment_id]


def analyze(service, caller, key, run_id, alignment_id, at, domain, jdk):
    timestamp(at)
    if jdk is None:
        raise LegalMathError('E_DEPENDENCY', details='Server toolchain required')
    with service.db.connect() as con:
        service._owner(con, caller, run_id)
        saved, context = _bound(service, con, run_id, alignment_id)
        reviews = _reviews(service, con, run_id, alignment_id)
        if reviews and reviews[-1]['decision'] == 'REJECT':
            raise LegalMathError('E_RELEASE_BLOCKED', details='Rejected correspondence requires a new proposal or review')
    # Local compilation is outside the transaction. Recheck immutable inputs,
    # source status and a concurrently arriving rejection before recording it.
    analysis_id = ident('alignment-analysis')
    checker = Comparisons(Path(service.db.root)/'alignment-java'/run_id/analysis_id, jdk, at, domain)
    readings, source = context[3], context[4]
    java_checks = [checker.verify(r, source) for r in readings]
    result = checker.compare_conditional(*readings, source, saved['proposal'])

    def op(con):
        service._owner(con, caller, run_id)
        current, _ = _bound(service, con, run_id, alignment_id)
        if current != saved:
            raise LegalMathError('E_STALE_REVIEW')
        current_reviews = _reviews(service, con, run_id, alignment_id)
        if current_reviews and current_reviews[-1]['decision'] == 'REJECT':
            raise LegalMathError('E_RELEASE_BLOCKED')
        value = {'run_id': run_id, 'analysis_id': analysis_id, 'alignment_id': alignment_id,
                 'proposal_hash': saved['proposal_hash'], 'source_packet_hash': digest(source),
                 'at': at, 'domain': domain, 'result': result, 'java_checks': java_checks,
                 'review_hashes_at_analysis': [digest(r) for r in current_reviews],
                 'recorded_at': service.clock(), 'release_eligible': False}
        service._save(con, 'alignment-analysis', value, analysis_id)
        return value
    return service.db.mutate(caller, key, {'op':'alignment.analyze', 'run':run_id,
        'alignment':alignment_id, 'at':at, 'domain':domain, 'proposal_hash':saved['proposal_hash']}, op)


def review(service, caller, key, run_id, alignment_id, expected_hash, decision, rationale, evidence_refs):
    if decision not in ('ACCEPT_FOR_CONDITIONAL_ANALYSIS', 'REJECT', 'UNRESOLVED') or not rationale.strip():
        raise LegalMathError('E_SCHEMA')

    def op(con):
        _access(service, con, caller, run_id, review=True)
        saved, context = _bound(service, con, run_id, alignment_id)
        if saved['proposal_hash'] != expected_hash:
            raise LegalMathError('E_STALE_REVIEW')
        if not evidence_refs or not set(evidence_refs) <= {u['unit_id'] for u in context[4]['units']}:
            raise LegalMathError('E_REFERENCE')
        decision_id = ident('alignment-review')
        value = {'run_id': run_id, 'decision_id': decision_id, 'alignment_id': alignment_id,
                 'proposal_hash': expected_hash, 'reviewer': caller, 'decision': decision,
                 'rationale': rationale, 'evidence_refs': evidence_refs, 'recorded_at': service.clock(),
                 'authority': 'LOCAL_REVIEWER_ATTESTATION_NOT_VERIFIED_HUMAN_IDENTITY',
                 'legal_source_commitment_resolved': False, 'release_eligible': False}
        service._save(con, 'alignment-review', value, decision_id)
        return value
    return service.db.mutate(caller, key, {'op':'alignment.review','run':run_id,'alignment':alignment_id,
        'expected_hash':expected_hash,'decision':decision,'rationale':rationale,'evidence_refs':evidence_refs}, op)


def read(service, caller, run_id, alignment_id):
    with service.db.connect() as con:
        _access(service, con, caller, run_id)
        saved, _ = _bound(service, con, run_id, alignment_id)
        reviews = _reviews(service, con, run_id, alignment_id)
        analyses = [a for a in service._list(con, run_id, 'alignment-analysis') if a['alignment_id'] == alignment_id]
    return {'proposal': saved, 'analyses': analyses, 'reviews': reviews,
            'current_decision': reviews[-1]['decision'] if reviews else 'UNREVIEWED',
            'release_eligible': False, 'legal_source_commitment_resolved': False}
