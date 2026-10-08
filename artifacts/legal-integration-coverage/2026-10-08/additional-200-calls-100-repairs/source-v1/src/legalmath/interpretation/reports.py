"""Terminal reports recompute every collection from persisted investigation state."""
from ..canonical import digest
from ..errors import LegalMathError
from .contracts import V, TERMINAL, validate
from .service import ident

class Reports:
    def __init__(self, service): self.s=service;self.db=service.db

    def stop(self, run_id):
        with self.db.connect() as con:
            run=self.s._run(con,run_id);p=self.db.get(con,run['policy_hash'])
            row=con.execute('SELECT invalidated,cancelled FROM interpretation_runs WHERE id=?',(run_id,)).fetchone()
            if row['invalidated']: return 'INTEGRITY_FAILURE'
            if row['cancelled']: return 'CANCELLED'
            if self.s.clock()>=run['deadline']: return 'DEADLINE'
            if run['actions_issued']>=p['max_actions_total']: return 'ACTION_LIMIT'
            if run['rounds_issued']>=p['max_resolution_rounds']: return 'ROUND_LIMIT'
            if run['no_progress_rounds']>=p['max_no_progress_rounds']: return 'NO_PROGRESS'
        return None

    def _material(self, con, run):
        rid=run['run_id'];p=self.db.get(con,run['policy_hash']);packet=self.s._packet(con,run)
        cov=self.s._get(con,rid,'coverage',run['coverage_id'])
        candidates=self.s._list(con,rid,'candidate');issues=self.s._list(con,rid,'issue')
        ids=lambda values,key:[v[key] for v in values]
        if ids(candidates,'candidate_id')!=run['candidate_ids'] or ids(issues,'issue_id')!=run['issue_ids']:
            raise LegalMathError('E_INTEGRITY')
        if [d['unit_id'] for d in cov['dispositions']]!=cov['inventory_unit_ids'] or cov['inventory_unit_ids']!=[u['unit_id'] for u in packet['units']]: raise LegalMathError('E_INTEGRITY')
        missing=sorted(set(cov['required_dependency_ids'])-set(cov['acquired_dependency_ids']))
        families=sorted(set(cov['identified_family_ids'])-set(cov['explored_family_ids']))
        roles=sorted(set(p['required_initial_roles'])-set(run['completed_initial_roles']))
        unresolved=[i['issue_id'] for i in issues if i['resolution_state']=='UNRESOLVED' and i['materiality'] in ('MATERIAL','UNKNOWN')]
        checks=[]
        if cov['inventory_review_status']=='REVIEWED':
            review=self.s._get(con,rid,'inventory-review',cov['review_decision_id'])
            self.s._owner(con,review['reviewer'],rid,'meaning')
            if review['source_packet_hash']!=run['source_packet_hash'] or review['unit_ids']!=cov['inventory_unit_ids']: raise LegalMathError('E_INTEGRITY')
        if candidates and cov['inventory_review_status']!='UNREVIEWED' and all(d['disposition']!='UNRESOLVED' for d in cov['dispositions']) and any(set(c['source_unit_ids'])==set(cov['inventory_unit_ids']) for c in candidates): checks.append('source-coverage')
        for issue in issues:
            if issue['root_id'] not in run['issue_ids'] or (issue['parent_issue_id'] and issue['parent_issue_id'] not in run['issue_ids']): raise LegalMathError('E_INTEGRITY')
            if issue['resolution_state']=='UNRESOLVED': continue
            if not issue['resolution_evidence_refs']: raise LegalMathError('E_INTEGRITY')
            for ref in issue['resolution_evidence_refs']:
                evidence=self.s._get(con,rid,'evidence',ref)
                if evidence['validation_status']!='VALIDATED' or evidence['source_packet_hash']!=run['source_packet_hash']: raise LegalMathError('E_INTEGRITY')
                self.db.get(con,evidence['content_hash'])
                if issue['resolution_state']=='RESOLVED_ADJUDICATION':
                    decision=self.s._get(con,rid,'issue-decision',evidence['review_decision_id'])
                    self.s._owner(con,decision['reviewer_principal'],rid,'meaning')
                    if decision['decision']!='RESOLVE_MEANING' or decision['issue_id']!=issue['issue_id']: raise LegalMathError('E_INTEGRITY')
        if not missing: checks.append('dependencies')
        if candidates:
            for c in candidates: validate('candidate',c)
            checks.extend(['candidate-validity','argument-register'])
        validated=self.s._list(con,rid,'check')
        # Reference/Java checks are issued only by the executable verifier, bound to a candidate.
        for name in ('reference-check','java-check'):
            if any(v['name']==name and v['passed'] and v['candidate_hash'] in {digest(c) for c in candidates} for v in validated): checks.append(name)
        checks.append('report-integrity')
        return dict(cov=cov,candidates=candidates,issues=issues,missing=missing,families=families,roles=roles,unresolved=unresolved,checks=checks,
                    incomplete=sorted(set(p['mandatory_checks'])-set(checks)))

    def finish(self, run_id, reason):
        with self.db.transaction() as con:
            run=self.s._run(con,run_id)
            if run['report_id']: return self.s._get(con,run_id,'report',run['report_id'])
            actual=self.stop_in(con,run)
            if actual: reason=actual
            m=self._material(con,run)
            if reason=='COMPLETE_FOR_REVIEW' and any(m[k] for k in ('missing','families','roles','unresolved','incomplete')): reason='HUMAN_REQUIRED'
            status={'CANCELLED':'CANCELLED','INTEGRITY_FAILURE':'FAILED_INTEGRITY','COMPLETE_FOR_REVIEW':'READY_FOR_REVIEW'}.get(reason,'BLOCKED_UNRESOLVED')
            terminal={'ACTION_LIMIT':'BUDGET_EXHAUSTED','ROUND_LIMIT':'ROUND_LIMIT','DEADLINE':'DEADLINE_REACHED','NO_PROGRESS':'NO_PROGRESS','CANCELLED':'CANCELLED','INTEGRITY_FAILURE':'INTEGRITY_FAILURE','HUMAN_REQUIRED':'DEPENDENCY_UNAVAILABLE'}
            for i in m['issues']:
                if i['resolution_state']=='UNRESOLVED':
                    i.update(processing_state='TERMINAL',terminal_reason=terminal.get(reason,'DEPENDENCY_UNAVAILABLE'),revision=i['revision']+1);self.s._save(con,'issue',i)
            report=dict(schema_version=V,report_id=ident('report'),run_id=run_id,source_packet_hash=run['source_packet_hash'],profile_id=run['profile_id'],run_status=status,
                selected_slice=self.s._packet(con,run)['selected_slice'],candidate_ids=run['candidate_ids'],all_issue_ids=run['issue_ids'],material_unresolved_issue_ids=m['unresolved'],coverage_id=run['coverage_id'],
                unexplored_family_ids=m['families'],missing_dependency_ids=m['missing'],missing_initial_roles=m['roles'],incomplete_mandatory_checks=m['incomplete'],processing_stop=reason,
                rounds_issued=run['rounds_issued'],actions_issued=run['actions_issued'],probability_of_legal_correctness=None,release_eligible=False,
                next_decision='Review exact candidate and source evidence' if status=='READY_FOR_REVIEW' else 'Resolve recorded uncertainty in an explicit successor investigation',
                next_decision_owner_role='meaning',evidence_limitations=['Deterministic scripted members; no measured English interpretation accuracy','LOCAL_SYNTHETIC authority; no bank approval','Formal checks concern encoded rules and stated test domains'],created_at=self.s.clock())
            if self.s._list(con,run_id,'search-config'):
                report['evidence_limitations']=['Bounded source-driven research search; independent legal accuracy not established',
                    'Provider identity and actual calls are retained in search records; fresh contexts can share model errors',
                    'LOCAL_SYNTHETIC reviewer registry; no bank approval','Formal checks concern encoded rules and declared domains']
            self.s._save(con,'report',report);run.update(status=status,report_id=report['report_id'],passed_mandatory_checks=m['checks']);self.s._save_run(con,run)
            self.db.audit(con,dict(event='interpretation.report',run_id=run_id,report_hash=digest(report)))
            return report

    def stop_in(self,con,run):
        row=con.execute('SELECT invalidated,cancelled FROM interpretation_runs WHERE id=?',(run['run_id'],)).fetchone()
        if row[0]: return 'INTEGRITY_FAILURE'
        if row[1]: return 'CANCELLED'
        if self.s.clock()>=run['deadline']: return 'DEADLINE'
        return None

    def cancel(self, caller, key, run_id):
        def op(con):
            self.s._owner(con,caller,run_id);run=self.s._run(con,run_id)
            if run['status'] not in TERMINAL: con.execute('UPDATE interpretation_runs SET cancelled=1 WHERE id=?',(run_id,))
            return dict(run_id=run_id,cancel_requested=True)
        result=self.db.mutate(caller,key,dict(op='interpretation.cancel',run_id=run_id),op)
        self.finish(run_id,'CANCELLED')
        return result

    def verify(self, caller, run_id):
        with self.db.connect() as con:
            self.s.lc.require(con,caller);run=self.s._run(con,run_id)
            report=self.s._get(con,run_id,'report',run['report_id']);validate('report',report)
            m=self._material(con,run)
            expected=dict(candidate_ids=run['candidate_ids'],all_issue_ids=run['issue_ids'],material_unresolved_issue_ids=m['unresolved'],missing_dependency_ids=m['missing'],
                unexplored_family_ids=m['families'],missing_initial_roles=m['roles'],incomplete_mandatory_checks=m['incomplete'])
            if any(report[k]!=v for k,v in expected.items()): raise LegalMathError('E_INTEGRITY')
            if report['actions_issued']!=run['actions_issued'] or len(self.s._list(con,run_id,'action'))!=run['actions_issued']: raise LegalMathError('E_INTEGRITY')
            return digest(report)
