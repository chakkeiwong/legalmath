"""Authenticated meaning acceptance and release checks for investigation-origin bundles."""
from ..canonical import digest
from ..errors import LegalMathError
from .contracts import V
from .service import Interpretations, ident
from .reports import Reports


def checked_report(service, con, run):
    if not run['report_id']: raise LegalMathError('E_RELEASE_BLOCKED')
    report=service._get(con,run['run_id'],'report',run['report_id'])
    material=Reports(service)._material(con,run)
    mapping={'candidate_ids':run['candidate_ids'],'all_issue_ids':run['issue_ids'],'material_unresolved_issue_ids':material['unresolved'],
        'missing_dependency_ids':material['missing'],'unexplored_family_ids':material['families'],'missing_initial_roles':material['roles'],
        'incomplete_mandatory_checks':material['incomplete']}
    if any(report[k]!=v for k,v in mapping.items()): raise LegalMathError('E_INTEGRITY')
    return report,material


def eligible_candidate(service,con,run,c):
    report,material=checked_report(service,con,run)
    row=con.execute('SELECT invalidated,cancelled,owner,source_key FROM interpretation_runs WHERE id=?',(run['run_id'],)).fetchone()
    current=con.execute('SELECT packet_hash FROM interpretation_sources WHERE source_key=?',(row['source_key'],)).fetchone()
    if row['invalidated'] or row['cancelled'] or current[0]!=run['source_packet_hash'] or report['run_status']!='READY_FOR_REVIEW' or any(material[k] for k in ('unresolved','missing','families','roles','incomplete')):
        raise LegalMathError('E_RELEASE_BLOCKED')
    if not c['bundle_hash'] or set(c['source_unit_ids'])!=set(material['cov']['inventory_unit_ids']): raise LegalMathError('E_RELEASE_BLOCKED')
    for issue in material['issues']:
        if issue['resolution_state']=='RESOLVED_ADJUDICATION' and (not issue['candidate_ids'] or c['candidate_id'] in issue['candidate_ids']):
            evidence=[service._get(con,run['run_id'],'evidence',ref) for ref in issue['resolution_evidence_refs']]
            decisions=[service._get(con,run['run_id'],'issue-decision',e['review_decision_id']) for e in evidence]
            if not any(d['candidate_hash']==digest(c) for d in decisions): raise LegalMathError('E_RELEASE_BLOCKED')
    checks=service._list(con,run['run_id'],'check')
    for name in ('reference-check','java-check'):
        matches=[v for v in checks if v['name']==name and v['passed'] and v['candidate_hash']==digest(c)]
        if not matches: raise LegalMathError('E_RELEASE_BLOCKED')
        from ..review.releases import Releases
        for v in matches:
            report_v=service.db.get(con,v['verification_hash'])
            Releases(service.db).check_evidence(con,c['bundle_hash'],report_v['build_manifest_hash'],v['verification_hash'])
    return report


class MeaningReview:
    def __init__(self,service): self.s=service;self.db=service.db

    def decide(self, caller, key, run_id, candidate_id, candidate_hash, report_hash, source_packet_hash, decision, rationale, objection, evidence_refs):
        def op(con):
            self.s._owner(con,caller,run_id,'meaning');run=self.s._run(con,run_id)
            c=self.s._get(con,run_id,'candidate',candidate_id);report,_=checked_report(self.s,con,run)
            if digest(c)!=candidate_hash or digest(report)!=report_hash or run['source_packet_hash']!=source_packet_hash: raise LegalMathError('E_STALE_REVIEW')
            if not set(evidence_refs)<=set(u['unit_id'] for u in self.s._packet(con,run)['units']): raise LegalMathError('E_REFERENCE')
            if decision=='ACCEPT_MEANING':
                eligible_candidate(self.s,con,run,c)
                if set(evidence_refs)!=set(u['unit_id'] for u in self.s._packet(con,run)['units']): raise LegalMathError('E_RELEASE_BLOCKED')
            value=dict(schema_version=V,decision_id=ident('decision'),run_id=run_id,reviewer_principal=caller,reviewer_role='LEGAL_INTERPRETATION_REVIEWER',authority='LOCAL_SYNTHETIC',
                candidate_hash=candidate_hash,report_hash=report_hash,source_packet_hash=source_packet_hash,decision=decision,proposition=c['controlled_language'],rationale=rationale,
                strongest_objection_response=objection,conditions=[],evidence_refs=evidence_refs,recorded_at=self.s.clock())
            self.s._save(con,'review-decision',value);return value
        return self.db.mutate(caller,key,dict(op='interpretation.meaning',run=run_id,candidate_id=candidate_id,candidate_hash=candidate_hash,report_hash=report_hash,source_packet_hash=source_packet_hash,decision=decision,rationale=rationale,objection=objection,evidence_refs=evidence_refs),op)

    def supersede(self, caller, key, run_id, predecessor_id, predecessor_report_hash, reason):
        def op(con):
            self.s._owner(con,caller,run_id,'meaning');run=self.s._run(con,run_id);previous=self.s._run(con,predecessor_id)
            if run['predecessor_run_id']!=predecessor_id or not isinstance(reason,str) or not reason.strip(): raise LegalMathError('E_REFERENCE')
            report,_=checked_report(self.s,con,previous)
            if digest(report)!=predecessor_report_hash: raise LegalMathError('E_STALE_REVIEW')
            if self.s._packet(con,run)['source_key']!=self.s._packet(con,previous)['source_key']: raise LegalMathError('E_REFERENCE')
            inherited=self.s._list(con,run_id,'inherited-issue')
            for issue in self.s._list(con,predecessor_id,'issue'):
                if issue['resolution_state']!='UNRESOLVED': continue
                matches=[i for i in inherited if i['predecessor_issue_id']==issue['issue_id'] and i['predecessor_issue_hash']==digest(issue)]
                if not matches or any(self.s._get(con,run_id,'issue',i['successor_issue_id'])['resolution_state']=='UNRESOLVED' for i in matches): raise LegalMathError('E_RELEASE_BLOCKED')
            if not any(d['decision']=='ACCEPT_MEANING' for d in self.s._list(con,run_id,'review-decision')): raise LegalMathError('E_RELEASE_BLOCKED')
            value=dict(run_id=run_id,predecessor_id=predecessor_id,predecessor_report_hash=predecessor_report_hash,successor_report_hash=digest(self.s._get(con,run_id,'report',run['report_id'])),reviewer=caller,reason=reason,authority='LOCAL_SYNTHETIC')
            self.s._save(con,'supersession',value,'supersession.'+predecessor_id);return value
        return self.db.mutate(caller,key,dict(op='interpretation.supersede',run_id=run_id,predecessor_id=predecessor_id,predecessor_report_hash=predecessor_report_hash,reason=reason),op)


def guard(db, con, bundle_hash):
    """All bound runs must authorize this exact bundle, or have an explicit reviewed successor."""
    s=Interpretations(db)
    bindings=con.execute('SELECT * FROM interpretation_bindings WHERE bundle_hash=?',(bundle_hash,)).fetchall()
    if not bindings: return []  # Existing manually reviewed MVP route.
    authorized=[]
    def acceptable(run_id, visited):
        if run_id in visited: raise LegalMathError('E_CYCLE')
        run=s._run(con,run_id)
        # Latest decision for each candidate wins; a later rejection revokes acceptance.
        decisions={d['candidate_hash']:d for d in s._list(con,run_id,'review-decision')}
        for c in s._list(con,run_id,'candidate'):
            if c['bundle_hash']!=bundle_hash: continue
            d=decisions.get(digest(c))
            if d and d['decision']=='ACCEPT_MEANING':
                try:
                    report=eligible_candidate(s,con,run,c)
                    s._owner(con,d['reviewer_principal'],run_id,'meaning')
                    if d['report_hash']==digest(report) and d['source_packet_hash']==run['source_packet_hash']:
                        authorized.append(d);return
                except LegalMathError: pass
        for row in con.execute("SELECT run_id,hash FROM interpretation_records WHERE kind='supersession'"):
            successor=db.get(con,row['hash'])
            if successor['predecessor_id']!=run_id: continue
            next_run=s._run(con,row['run_id'])
            if next_run['predecessor_run_id']!=run_id or successor['predecessor_report_hash']!=digest(s._get(con,run_id,'report',run['report_id'])): continue
            s._owner(con,successor['reviewer'],row['run_id'],'meaning')
            acceptable(row['run_id'],visited|{run_id});return
        raise LegalMathError('E_RELEASE_BLOCKED')
    for rid in sorted({b['run_id'] for b in bindings}): acceptable(rid,set())
    return authorized
