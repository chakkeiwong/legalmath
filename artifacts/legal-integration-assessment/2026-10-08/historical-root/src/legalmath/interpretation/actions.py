"""Atomic reservation/outbox accounting. Dispatch is at most once without remote deduplication."""
from ..canonical import digest
from ..errors import LegalMathError
from .contracts import V, TERMINAL
from .service import ident, later

class Actions:
    def __init__(self, service): self.s=service;self.db=service.db

    def reserve(self, run_id, *, role=None, issue_id=None, kind='INITIAL_PROPOSAL', inputs, adapter='scripted', question='Read the frozen source packet'):
        signature=digest(dict(role=role,issue=issue_id,kind=kind,inputs=inputs,adapter=adapter,question=question))
        with self.db.transaction() as con:
            old=con.execute('SELECT action_id FROM interpretation_outbox WHERE run_id=? AND signature=?',(run_id,signature)).fetchone()
            if old: return self.s._get(con,run_id,'action',old[0])
            run=self.s._run(con,run_id,True);p=self.db.get(con,run['policy_hash'])
            if self.s.clock()>=run['deadline'] or run['actions_issued']>=p['max_actions_total']: raise LegalMathError('E_RESOURCE_LIMIT')
            actions=self.s._list(con,run_id,'action');root=None
            if kind=='INITIAL_PROPOSAL':
                if run['status'] not in ('INITIALIZING','INITIAL_PROPOSALS') or role not in p['required_initial_roles'] or any(a['initial_role']==role for a in actions): raise LegalMathError('E_JOB_STATE')
                if sum(a['kind']=='INITIAL_PROPOSAL' for a in actions)>=p['max_initial_actions']: raise LegalMathError('E_RESOURCE_LIMIT')
                round_no=0;run['status']='INITIAL_PROPOSALS'
            else:
                if run['status']!='RESOLVING' or role is not None: raise LegalMathError('E_JOB_STATE')
                issue=self.s._get(con,run_id,'issue',issue_id);root=issue['root_id']
                if issue['resolution_state']!='UNRESOLVED': raise LegalMathError('E_JOB_STATE')
                if sum(a['issue_root_id']==root for a in actions)>=p['max_actions_per_issue_root'] or run['rounds_issued']>=p['max_resolution_rounds']: raise LegalMathError('E_RESOURCE_LIMIT')
                run['rounds_issued']+=1;round_no=run['rounds_issued']
            aid=ident('action')
            action=dict(schema_version=V,action_id=aid,run_id=run_id,issue_root_id=root,initial_role=role,round=round_no,kind=kind,
                question=question,success_criterion='Validated new evidence or explicit unresolved outcome',input_hashes=inputs,adapter_id=adapter,idempotency_key=ident('dispatch'),
                state='RESERVED',issued_at=self.s.clock(),timeout_seconds=p['action_timeout_seconds'],fencing_token=0,lease_owner=None,result_ref=None,substantive_outcome='PENDING',
                issued_charge=1,token_reservation=None,cost_reservation_minor_units=None,remote_idempotency='NOT_APPLICABLE')
            self.s._save(con,'action',action)
            con.execute('INSERT INTO interpretation_outbox(action_id,run_id,signature) VALUES(?,?,?)',(aid,run_id,signature))
            run['actions_issued']+=1;run['action_ids'].append(aid)
            if root:
                issue['attempted_action_ids'].append(aid);issue['revision']+=1;issue['processing_state']='INVESTIGATING';self.s._save(con,'issue',issue)
            self.s._save_run(con,run);self.db.audit(con,dict(event='interpretation.reserve',action=aid,charge=1))
            return action

    def claim(self, run_id, action_id, worker):
        with self.db.transaction() as con:
            self.s._run(con,run_id,True)
            a=self.s._get(con,run_id,'action',action_id)
            row=con.execute('SELECT * FROM interpretation_outbox WHERE action_id=?',(action_id,)).fetchone()
            if a['state']!='RESERVED' or (row['lease_until'] and row['lease_until']>self.s.clock()): raise LegalMathError('E_JOB_STATE')
            a['fencing_token']+=1;a['lease_owner']=worker
            self.s._save(con,'action',a)
            con.execute('UPDATE interpretation_outbox SET fence=?,lease_until=? WHERE action_id=?',(a['fencing_token'],later(self.s.clock(),a['timeout_seconds']),action_id))
            return a

    def dispatch(self, run_id, action_id, worker, fence):
        with self.db.transaction() as con:
            run=self.s._run(con,run_id,True);a=self.s._get(con,run_id,'action',action_id)
            row=con.execute('SELECT lease_until FROM interpretation_outbox WHERE action_id=?',(action_id,)).fetchone()
            if a['state']!='RESERVED' or a['lease_owner']!=worker or a['fencing_token']!=fence or row[0]<=self.s.clock() or run['deadline']<=self.s.clock(): raise LegalMathError('E_JOB_STATE')
            a['state']='DISPATCHED';self.s._save(con,'action',a)
            return a

    def complete(self, run_id, action_id, worker, fence, result, state='SUCCEEDED'):
        if state not in ('SUCCEEDED','FAILED','TIMED_OUT'): raise LegalMathError('E_SCHEMA')
        with self.db.transaction() as con:
            run=self.s._run(con,run_id);a=self.s._get(con,run_id,'action',action_id)
            row=con.execute('SELECT invalidated,cancelled FROM interpretation_runs WHERE id=?',(run_id,)).fetchone()
            lease=con.execute('SELECT lease_until FROM interpretation_outbox WHERE action_id=?',(action_id,)).fetchone()[0]
            valid=(a['state']=='DISPATCHED' and a['lease_owner']==worker and a['fencing_token']==fence and lease>self.s.clock() and run['deadline']>self.s.clock() and run['status'] not in TERMINAL and not any(row))
            if not valid:
                self.s._save(con,'observation',dict(run_id=run_id,action_id=action_id,result=result,reason='Late, expired, cancelled or fenced completion'),ident('observation'))
                return False
            ref=ident('result');self.s._save(con,'member-result',dict(run_id=run_id,action_id=action_id,result=result),ref)
            a.update(state=state,result_ref=ref,substantive_outcome='PENDING' if state=='SUCCEEDED' else 'UNAVAILABLE')
            self.s._save(con,'action',a);return True

    def recover(self, run_id):
        with self.db.transaction() as con:
            run=self.s._run(con,run_id)
            for a in self.s._list(con,run_id,'action'):
                lease=con.execute('SELECT lease_until FROM interpretation_outbox WHERE action_id=?',(a['action_id'],)).fetchone()[0]
                if a['state']=='DISPATCHED' and (not lease or lease<=self.s.clock() or run['status'] in TERMINAL):
                    a.update(state='RESULT_UNKNOWN',substantive_outcome='UNAVAILABLE',fencing_token=a['fencing_token']+1)
                    self.s._save(con,'action',a)
                    self.db.audit(con,dict(event='interpretation.recover_dispatched',action=a['action_id'],refund=0))
