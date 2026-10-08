"""Deterministic breadth-first collection, bounded discrepancy investigation and recovery."""
import subprocess
import sys
import os
from pathlib import Path
from ..canonical import canonical, loads, digest
from ..errors import LegalMathError
from .actions import Actions
from .contracts import TERMINAL, Proposal, parse, V
from .service import ident, later

ROLES=('inventory','normative','controlled-language','alternatives')
PRIORITY={k:i for i, group in enumerate([('INTEGRITY','SOURCE_COVERAGE'),('DEPENDENCY','SCOPE'),('DEFINITION','EXCEPTION','MODALITY','TIME','FACT_MAPPING'),('FORMAL_MISMATCH','JAVA_MISMATCH'),('MEMBER_FAILURE','SEARCH_INCOMPLETE')]) for k in group}

class Controller:
    def __init__(self, service): self.s=service;self.db=service.db;self.actions=Actions(service)

    def configure(self, caller, key, run_id, members, repairs=None, verification_hashes=None):
        repairs=repairs or []
        verification_hashes=verification_hashes or []
        if not isinstance(verification_hashes,list) or len(verification_hashes)>24 or any(not isinstance(h,str) or len(h)!=64 for h in verification_hashes): raise LegalMathError('E_SCHEMA')
        if set(members)!=set(ROLES) or len(repairs)>3: raise LegalMathError('E_SCHEMA')
        for spec in [*members.values(),*repairs]:
            if not isinstance(spec,dict) or set(spec)!={'adapter','proposals'} or spec['adapter'] not in ('scripted','malformed','unavailable','timeout') or not isinstance(spec['proposals'],list) or len(spec['proposals'])>24: raise LegalMathError('E_SCHEMA')
            for proposal in spec['proposals']: parse(Proposal,proposal)
        if members['inventory']['proposals']: raise LegalMathError('E_SCHEMA')
        value=dict(run_id=run_id,members=members,repairs=repairs,verification_hashes=verification_hashes,authority='SYNTHETIC_FIXTURE')
        def op(con):
            self.s._owner(con,caller,run_id);run=self.s._run(con,run_id,True)
            if run['actions_issued'] or self.s._list(con,run_id,'configuration'): raise LegalMathError('E_JOB_STATE')
            self.s._save(con,'configuration',value,'configuration');return value
        return self.db.mutate(caller,key,dict(op='interpretation.configure',configuration=value),op)

    def _execute(self, action, packet, spec, worker):
        rid,aid=action['run_id'],action['action_id']
        if action['state']!='RESERVED': return
        action=self.actions.claim(rid,aid,worker);f=action['fencing_token']
        self.actions.dispatch(rid,aid,worker,f)
        request=dict(packet=packet,role=action['initial_role'],spec=spec)
        try:
            result=subprocess.run([sys.executable,'-m','legalmath.interpretation.member'],input=canonical(request),capture_output=True,timeout=action['timeout_seconds'],check=True)
            value=loads(result.stdout);state='SUCCEEDED'
        except subprocess.TimeoutExpired: value={'error':'TIMEOUT'};state='TIMED_OUT'
        except (subprocess.CalledProcessError,LegalMathError,ValueError): value={'error':'INVALID_OR_UNAVAILABLE_MEMBER'};state='FAILED'
        self.actions.complete(rid,aid,worker,f,value,state)

    def _ingest(self, con, run, action):
        # Exactly-once ingestion, independent of process restart.
        if self.s._list(con,run['run_id'],'ingested') and any(x['action_id']==action['action_id'] for x in self.s._list(con,run['run_id'],'ingested')): return False
        value=self.s._get(con,run['run_id'],'member-result',action['result_ref'])['result'] if action['result_ref'] else None
        good=action['state']=='SUCCEEDED' and isinstance(value,dict) and set(value)=={'inventory_unit_ids','proposals'} and isinstance(value['proposals'],list) and len(value['proposals'])<=24
        progress=False
        # A savepoint discards partial candidates if a member's whole response is malformed.
        con.execute('SAVEPOINT member_output')
        saved=loads(canonical(run))
        try:
            if not good: raise LegalMathError('E_SCHEMA')
            packet=self.s._packet(con,run)
            if action['initial_role']=='inventory':
                if value['inventory_unit_ids'] != [u['unit_id'] for u in packet['units']] or value['proposals']: raise LegalMathError('E_SCHEMA')
            elif value['inventory_unit_ids']: raise LegalMathError('E_SCHEMA')
            if action['kind']=='REPAIR' and len(value['proposals'])!=1: raise LegalMathError('E_SCHEMA')
            for p in value['proposals']:
                c=self.s._candidate(con,run,p,'BLIND_INITIAL' if action['kind']=='INITIAL_PROPOSAL' else 'SHARED_RESOLUTION',action['action_id'])
                progress=progress or not c.get('deferred',False)
            if action['initial_role'] and action['initial_role'] not in run['completed_initial_roles']: run['completed_initial_roles'].append(action['initial_role'])
            con.execute('RELEASE member_output')
        except LegalMathError:
            con.execute('ROLLBACK TO member_output');con.execute('RELEASE member_output');run.clear();run.update(saved)
            self.s._issue(con,run,'MEMBER_FAILURE',[],[],'Obtain a valid '+(action['initial_role'] or 'repair')+' response','Missing, malformed or unavailable member response')
            good=False
        action['substantive_outcome']='PROGRESS' if progress else ('NO_PROGRESS' if good else 'INVALID')
        self.s._save(con,'action',action)
        self.s._save(con,'ingested',dict(run_id=run['run_id'],action_id=action['action_id']),'ingested.'+action['action_id'])
        return progress

    def _reconcile(self, con, run):
        cs=self.s._list(con,run['run_id'],'candidate');existing=self.s._list(con,run['run_id'],'issue')
        # Reconcile propositions by explicit content; agreement carries no probability.
        texts={c['controlled_language'] for c in cs if c['generation_phase']=='BLIND_INITIAL'}
        if len(texts)>1 and not any(i['kind']=='SCOPE' and i['question']=='Reconcile competing initial propositions' for i in existing):
            self.s._issue(con,run,'SCOPE',[],[c['candidate_id'] for c in cs],'Reconcile competing initial propositions','Frozen initial readings differ')
        cov=self.s._get(con,run['run_id'],'coverage',run['coverage_id'])
        for d in cov['dispositions']:
            matches=[i for i in existing if i['kind']=='SOURCE_COVERAGE' and i['source_unit_ids']==[d['unit_id']]]
            if d['disposition']=='UNRESOLVED' and not matches:
                self.s._issue(con,run,'SOURCE_COVERAGE',[d['unit_id']],[],'Account for '+d['locator'],'Independent inventory unit omitted')
            elif d['disposition']=='IMPLEMENTED':
                # This closes the structural omission only; interpretation still needs meaning review.
                for issue in matches:
                    if issue['resolution_state']!='UNRESOLVED': continue
                    eid=ident('evidence');content=dict(unit=d['unit_id'],candidate_ids=d['target_refs'],check='source-reference-present')
                    ev=dict(schema_version=V,evidence_id=eid,run_id=run['run_id'],source_packet_hash=run['source_packet_hash'],kind='VALIDATED_REPAIR',content_hash=self.db.put(con,'repair-check',content),
                        statement='Previously omitted inventory unit is now explicitly referenced; meaning is unreviewed',source_unit_ids=[d['unit_id']],validation_status='VALIDATED',authority='SYNTHETIC_FIXTURE',validator_id='inventory-check',action_id=None,review_decision_id=None,domain_hash=None,comparison_result=None,legal_source_commitment_resolved=False)
                    self.s._save(con,'evidence',ev)
                    issue.update(resolution_state='RESOLVED_EVIDENCE',processing_state='TERMINAL',terminal_reason='RESOLVED',resolution_evidence_refs=[eid],revision=issue['revision']+1)
                    self.s._save(con,'issue',issue)
        from ..review.releases import Releases
        configuration=self.s._get(con,run['run_id'],'configuration','configuration')
        for vh in configuration['verification_hashes']:
            verification=self.db.get(con,vh)
            for c in cs:
                if c['bundle_hash']!=verification.get('bundle_hash'): continue
                Releases(self.db).check_evidence(con,c['bundle_hash'],verification['build_manifest_hash'],vh)
                for name in ('reference-check','java-check'):
                    record=dict(run_id=run['run_id'],name=name,passed=True,candidate_hash=digest(c),verification_hash=vh)
                    self.s._save(con,'check',record,name+'.'+c['candidate_id'])

    def drive(self, run_id):
        worker='worker.'+str(os.getpid())+'.'+Path(f'/proc/{os.getpid()}/stat').read_text().split()[21]+'.'+ident('lease')
        with self.db.transaction() as con:
            run=self.s._run(con,run_id)
            if run['status'] in TERMINAL: return run
            old=con.execute('SELECT * FROM interpretation_workers WHERE run_id=?',(run_id,)).fetchone()
            if old and old['lease_until']>self.s.clock(): raise LegalMathError('E_JOB_STATE')
            fence=old['fence']+1 if old else 1
            con.execute('INSERT INTO interpretation_workers VALUES(?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until,fence=excluded.fence',(run_id,worker,later(self.s.clock(),600),fence))
        try: return self._drive(run_id,worker)
        except Exception as exc:
            # Preserve failure information and a terminal report even after worker errors.
            with self.db.transaction() as con:
                self.s._save(con,'observation',dict(run_id=run_id,reason='Controller failure',error=type(exc).__name__),ident('observation'))
            from .reports import Reports
            return Reports(self.s).finish(run_id,'INTEGRITY_FAILURE')
        finally:
            with self.db.transaction() as con:
                con.execute('DELETE FROM interpretation_workers WHERE run_id=? AND owner=?',(run_id,worker))

    def _drive(self, run_id, worker):
        from .reports import Reports
        reports=Reports(self.s)
        self.actions.recover(run_id)
        with self.db.connect() as con:
            run=self.s._run(con,run_id);packet=self.s._packet(con,run);policy=self.db.get(con,run['policy_hash'])
            config=self.s._get(con,run_id,'configuration','configuration')
        # Each member sees the same source and its own scripted proposal, never peer outputs.
        for role in ROLES:
            if reports.stop(run_id): return reports.finish(run_id,reports.stop(run_id))
            with self.db.connect() as con:
                existing=[a for a in self.s._list(con,run_id,'action') if a['initial_role']==role]
            action=existing[0] if existing else self.actions.reserve(run_id,role=role,inputs=[run['source_packet_hash'],digest(config['members'][role])])
            if action['state']=='DISPATCHED': return reports.finish(run_id,'HUMAN_REQUIRED')
            self._execute(action,packet,config['members'][role],worker)
        with self.db.transaction() as con:
            run=self.s._run(con,run_id,True)
            for a in self.s._list(con,run_id,'action'):
                if a['kind']=='INITIAL_PROPOSAL': self._ingest(con,run,a)
            run['status']='RESOLVING';self._reconcile(con,run);self.s._save_run(con,run)
        while True:
            reason=reports.stop(run_id)
            if reason: return reports.finish(run_id,reason)
            with self.db.connect() as con:
                run=self.s._run(con,run_id);issues=[i for i in self.s._list(con,run_id,'issue') if i['resolution_state']=='UNRESOLVED'];actions=self.s._list(con,run_id,'action')
            if not issues: return reports.finish(run_id,'COMPLETE_FOR_REVIEW')
            eligible=[i for i in issues if sum(a['issue_root_id']==i['root_id'] for a in actions)<policy['max_actions_per_issue_root']]
            if not eligible or run['rounds_issued']>=len(config['repairs']): return reports.finish(run_id,'HUMAN_REQUIRED')
            # _list supplies stable creation order; stable sort preserves it within a priority.
            issue=sorted(eligible,key=lambda i:(PRIORITY[i['kind']],i['materiality']=='IMMATERIAL_REVIEWED'))[0]
            spec=config['repairs'][run['rounds_issued']]
            inputs=[run['source_packet_hash'],digest(spec)]
            # Identical failed questions are skipped, not blindly retried under new IDs.
            action=self.actions.reserve(run_id,kind='REPAIR',issue_id=issue['issue_id'],inputs=inputs,question=issue['question'])
            if action['state']!='RESERVED': return reports.finish(run_id,'NO_PROGRESS')
            self._execute(action,packet,spec,worker)
            with self.db.transaction() as con:
                run=self.s._run(con,run_id,True)
                before={i['issue_id'] for i in self.s._list(con,run_id,'issue') if i['resolution_state']!='UNRESOLVED'}
                a=self.s._get(con,run_id,'action',action['action_id']);self._ingest(con,run,a);self._reconcile(con,run)
                after={i['issue_id'] for i in self.s._list(con,run_id,'issue') if i['resolution_state']!='UNRESOLVED'}
                run['no_progress_rounds']=0 if after-before else run['no_progress_rounds']+1
                self.s._save_run(con,run)
