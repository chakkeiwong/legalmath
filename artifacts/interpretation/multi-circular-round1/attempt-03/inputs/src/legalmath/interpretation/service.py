"""Transactional interpretation records; only registered humans confer authority."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from ..canonical import digest
from ..errors import LegalMathError
from ..review.lifecycle import Lifecycle
from ..sources.intake import resolve_span
from ..ir.load import source_span_errors
from .contracts import V, TERMINAL, Packet, Proposal, parse, policy, validate, reference_policy


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def later(at, seconds):
    return (datetime.fromisoformat(at.replace('Z','+00:00'))+timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def ident(prefix):
    return prefix+'.'+uuid4().hex


class Interpretations:
    def __init__(self, db, clock=now):
        self.db, self.clock, self.lc = db, clock, Lifecycle(db)

    def _run(self, con, run_id, mutable=False):
        row = con.execute('SELECT * FROM interpretation_runs WHERE id=?',(run_id,)).fetchone()
        if not row: raise LegalMathError('E_NOT_FOUND')
        run = self.db.get(con,row['hash'])
        if mutable and (run['status'] in TERMINAL or row['invalidated'] or row['cancelled']):
            raise LegalMathError('E_JOB_STATE')
        return run

    def _owner(self, con, caller, run_id, role='author'):
        self.lc.require(con,caller,role)
        row = con.execute('SELECT owner FROM interpretation_runs WHERE id=?',(run_id,)).fetchone()
        if not row: raise LegalMathError('E_NOT_FOUND')
        if role == 'author' and row[0] != caller: raise LegalMathError('E_AUTHORITY')
        if role == 'meaning' and row[0] == caller: raise LegalMathError('E_AUTHORITY')

    def _save_run(self, con, run):
        run['revision'] += 1
        validate('run',run)
        h = self.db.put(con,'interpretation_run',run)
        con.execute('UPDATE interpretation_runs SET hash=? WHERE id=?',(h,run['run_id']))
        con.execute('INSERT INTO interpretation_history(run_id,kind,id,hash) VALUES(?,?,?,?)',(run['run_id'],'run',run['run_id'],h))
        return h

    def _save(self, con, kind, value, key=None):
        if kind in ('candidate','coverage','issue','action','report','evidence','issue-decision','review-decision'):
            validate(kind,value)
        key = key or value[kind.replace('-','_')+'_id' if kind not in ('issue-decision','review-decision') else 'decision_id']
        h = self.db.put(con,'interpretation_'+kind,value)
        con.execute('INSERT INTO interpretation_records VALUES(?,?,?,?) ON CONFLICT(run_id,kind,id) DO UPDATE SET hash=excluded.hash',(value['run_id'],kind,key,h))
        con.execute('INSERT INTO interpretation_history(run_id,kind,id,hash) VALUES(?,?,?,?)',(value['run_id'],kind,key,h))
        return h

    def _get(self, con, run_id, kind, key):
        row = con.execute('SELECT hash FROM interpretation_records WHERE run_id=? AND kind=? AND id=?',(run_id,kind,key)).fetchone()
        if not row: raise LegalMathError('E_NOT_FOUND')
        return self.db.get(con,row[0])

    def _list(self, con, run_id, kind):
        return [self.db.get(con,r[0]) for r in con.execute('SELECT hash FROM interpretation_records WHERE run_id=? AND kind=? ORDER BY rowid',(run_id,kind))]

    def _packet(self, con, run):
        return self.db.get(con,run['source_packet_hash'])

    def _validate_packet(self, con, value):
        packet = parse(Packet,value)
        ids = [u['unit_id'] for u in packet['units']]
        deps = [d['dependency_id'] for d in packet['dependencies']]
        if len(ids)!=len(set(ids)) or len(deps)!=len(set(deps)) or len(set(packet['family_ids']))!=len(packet['family_ids']):
            raise LegalMathError('E_DUPLICATE_ID')
        for u in packet['units']:
            if packet['authority']=='RETAINED_SOURCE':
                if not u['span'] or source_span_errors(u['span']) or resolve_span(self.db,con,u['span']) != u['text']:
                    raise LegalMathError('E_HASH_MISMATCH')
            elif u['span'] is not None: raise LegalMathError('E_SCHEMA')
        for d in packet['dependencies']:
            if d['source_hash'] and not con.execute('SELECT 1 FROM sources WHERE payload_hash=?',(d['source_hash'],)).fetchone():
                raise LegalMathError('E_DEPENDENCY')
        return packet

    def create(self, caller, key, packet, settings=None, predecessor=None):
        settings = policy(settings if settings is not None else reference_policy())
        def op(con):
            self.lc.require(con,caller,'author')
            p = self._validate_packet(con,packet)
            ph = self.db.put(con,'interpretation_packet',p)
            if predecessor:
                self._owner(con,caller,predecessor)
                old = self._run(con,predecessor)
                if old['status'] not in TERMINAL: raise LegalMathError('E_JOB_STATE')
                if self._packet(con,old)['source_key'] != p['source_key']: raise LegalMathError('E_REFERENCE')
            previous = con.execute('SELECT packet_hash FROM interpretation_sources WHERE source_key=?',(p['source_key'],)).fetchone()
            if previous and previous[0] != ph:
                # A source key cannot be silently replaced by a new investigation.
                raise LegalMathError('E_STALE_REVIEW')
            con.execute('INSERT OR IGNORE INTO interpretation_sources VALUES(?,?)',(p['source_key'],ph))
            run_id = ident('run'); at=self.clock()
            run = dict(schema_version=V,run_id=run_id,predecessor_run_id=predecessor,source_packet_hash=ph,
                       profile_id='ruleir.0.1',policy_id=settings['policy_id'],policy_hash=self.db.put(con,'interpretation_policy',settings),
                       created_at=at,deadline=later(at,settings['run_deadline_seconds']),status='INITIALIZING',rounds_issued=0,
                       actions_issued=0,no_progress_rounds=0,candidate_ids=[],issue_ids=[],action_ids=[],completed_initial_roles=[],
                       passed_mandatory_checks=[],coverage_id=ident('coverage'),report_id=None,revision=0)
            validate('run',run)
            rh=self.db.put(con,'interpretation_run',run)
            con.execute('INSERT INTO interpretation_runs(id,owner,packet_hash,source_key,hash) VALUES(?,?,?,?,?)',(run_id,caller,ph,p['source_key'],rh))
            coverage=dict(schema_version=V,coverage_id=run['coverage_id'],run_id=run_id,source_packet_hash=ph,inventory_unit_ids=[u['unit_id'] for u in p['units']],
                dispositions=[dict(unit_id=u['unit_id'],locator=u['locator'],disposition='UNRESOLVED',reason='Independent inventory; no reviewed disposition yet',target_refs=[]) for u in p['units']],
                required_dependency_ids=[d['dependency_id'] for d in p['dependencies']],acquired_dependency_ids=[d['dependency_id'] for d in p['dependencies'] if d['source_hash']],
                identified_family_ids=p['family_ids'],explored_family_ids=[],inventory_review_status='SYNTHETIC_FIXTURE' if p['authority']=='SYNTHETIC_FIXTURE' else 'UNREVIEWED',review_decision_id=None)
            self._save(con,'coverage',coverage)
            for d in p['dependencies']:
                if not d['source_hash']: self._issue(con,run,'DEPENDENCY',[],[],f"Acquire dependency {d['dependency_id']}",'Missing retained source')
            if predecessor:
                prior_issues={i['issue_id']:i for i in self._list(con,predecessor,'issue')}
                needed={i['issue_id'] for i in prior_issues.values() if i['resolution_state']=='UNRESOLVED'}
                for iid in list(needed):
                    parent=prior_issues[iid]
                    while parent['parent_issue_id']:
                        needed.add(parent['parent_issue_id']);parent=prior_issues[parent['parent_issue_id']]
                    needed.add(parent['root_id'])
                for prior in prior_issues.values():
                    if prior['issue_id'] not in needed: continue
                    # IDs are scoped by run. Preserve the complete root/parent chain,
                    # but require fresh resolution against the successor source packet.
                    child={**prior,'run_id':run_id,'source_unit_ids':[u for u in prior['source_unit_ids'] if u in {x['unit_id'] for x in p['units']}],
                        'candidate_ids':[],'resolution_state':'UNRESOLVED','processing_state':'OPEN','terminal_reason':None,
                        'resolution_evidence_refs':[],'attempted_action_ids':[],'revision':0}
                    self._save(con,'issue',child);run['issue_ids'].append(child['issue_id'])
                    self._save(con,'inherited-issue',dict(run_id=run_id,predecessor_run_id=predecessor,predecessor_issue_id=prior['issue_id'],predecessor_issue_hash=digest(prior),successor_issue_id=child['issue_id']),'inherited.'+child['issue_id'])
            self._save_run(con,run)
            return run
        return self.db.mutate(caller,key,dict(op='interpretation.create',packet=packet,policy=settings,predecessor=predecessor),op)

    def read(self, caller, run_id):
        with self.db.connect() as con:
            self.lc.require(con,caller)
            run=self._run(con,run_id)
            return dict(run=run,packet=self._packet(con,run),invalidated=bool(con.execute('SELECT invalidated FROM interpretation_runs WHERE id=?',(run_id,)).fetchone()[0]),
                hashes={r['id']:r['hash'] for r in con.execute('SELECT id,hash FROM interpretation_records WHERE run_id=?',(run_id,))},
                records={kind:self._list(con,run_id,kind) for kind in set(('coverage','candidate','issue','action','evidence','report','issue-decision','review-decision','frontier','observation','check'))|{r[0] for r in con.execute('SELECT DISTINCT kind FROM interpretation_records WHERE run_id=?',(run_id,))}})

    def _issue(self, con, run, kind, units, candidates, question, difference, parent=None):
        if not set(units)<=set(self._get(con,run['run_id'],'coverage',run['coverage_id'])['inventory_unit_ids']) or not set(candidates)<=set(run['candidate_ids']):
            raise LegalMathError('E_REFERENCE')
        issue_id=ident('issue')
        parent_record=self._get(con,run['run_id'],'issue',parent) if parent else None
        issue=dict(schema_version=V,issue_id=issue_id,root_id=parent_record['root_id'] if parent else issue_id,parent_issue_id=parent,
            run_id=run['run_id'],source_unit_ids=units,candidate_ids=candidates,kind=kind,question=question,observed_difference=difference,
            materiality='UNKNOWN',processing_state='OPEN',resolution_state='UNRESOLVED',terminal_reason=None,resolution_evidence_refs=[],
            attempted_action_ids=[],evidence_needed='Retained evidence and authenticated interpretation decision',affected_decisions=[self._packet(con,run)['selected_slice']],revision=0)
        self._save(con,'issue',issue);run['issue_ids'].append(issue_id)
        return issue

    def raise_issue(self, caller, key, run_id, kind, units, candidates, question, difference, parent=None):
        def op(con):
            self._owner(con,caller,run_id);run=self._run(con,run_id,True)
            issue=self._issue(con,run,kind,units,candidates,question,difference,parent)
            self._save_run(con,run);return issue
        return self.db.mutate(caller,key,dict(op='interpretation.issue',run=run_id,kind=kind,units=units,candidates=candidates,question=question,difference=difference,parent=parent),op)

    def _candidate(self, con, run, value, phase, action_id=None):
        p=parse(Proposal,value); packet=self._packet(con,run)
        if p['source_packet_hash'] != run['source_packet_hash']: raise LegalMathError('E_HASH_MISMATCH')
        if not set(p['source_unit_ids'])<=set(u['unit_id'] for u in packet['units']) or not set(p['family_ids'])<=set(packet['family_ids']):
            raise LegalMathError('E_REFERENCE')
        if p['parent_id']:
            parent=self._get(con,run['run_id'],'candidate',p['parent_id'])
            if phase=='BLIND_INITIAL': raise LegalMathError('E_AUTHORITY')
            if parent['source_packet_hash']!=p['source_packet_hash']: raise LegalMathError('E_HASH_MISMATCH')
        settings=self.db.get(con,run['policy_hash'])
        cid=ident('candidate')
        value=dict(schema_version=V,candidate_id=cid,run_id=run['run_id'],**p,issue_ids=[],status='ACTIVE',disposition_reason='Unreviewed interpretation proposal',
            scheduling_priority=0,score_purpose='INVESTIGATION_PRIORITY_ONLY',probability_of_legal_correctness=None,generation_phase=phase,action_id=action_id)
        validate('candidate',value)
        refs=set(p['source_unit_ids']) | {a['assumption_id'] for a in p['assumptions']} | {a['argument_id'] for a in p['arguments']}
        named=[a['assumption_id'] for a in p['assumptions']]+[a['argument_id'] for a in p['arguments']]
        if len(named)!=len(set(named)) or set(named)&set(p['source_unit_ids']): raise LegalMathError('E_DUPLICATE_ID')
        for a in p['assumptions']:
            if not set(a['provenance_refs'])<=set(p['source_unit_ids']): raise LegalMathError('E_REFERENCE')
            if a['status']=='SOURCE_SUPPORTED' and not a['provenance_refs']: raise LegalMathError('E_REFERENCE')
        for a in p['arguments']:
            if not set(a['premise_refs'])<=refs or not set(a['source_refs'])<=set(p['source_unit_ids']): raise LegalMathError('E_REFERENCE')
        graph={a['argument_id']:set(a['premise_refs']) & set(named) for a in p['arguments']}
        depths={}
        def visit(node,path):
            if node in path: raise LegalMathError('E_CYCLE')
            if len(path)>settings['max_dependency_depth']: raise LegalMathError('E_RESOURCE_LIMIT')
            if node not in depths: depths[node]=1+max((visit(child,path|{node}) for child in graph.get(node,())),default=0)
            if len(path)+depths[node]>settings['max_dependency_depth']+1: raise LegalMathError('E_RESOURCE_LIMIT')
            return depths[node]
        for node in graph: visit(node,set())
        all_arguments=set(graph)|{a['argument_id'] for c in self._list(con,run['run_id'],'candidate') for a in c['arguments']}
        if any(not set(a['opposes_argument_ids'])<=all_arguments for a in p['arguments']): raise LegalMathError('E_REFERENCE')
        coverage=self._get(con,run['run_id'],'coverage',run['coverage_id'])
        unexplored=set(coverage['identified_family_ids'])-set(coverage['explored_family_ids'])
        reserve_breadth=phase=='BLIND_INITIAL' and not set(p['family_ids'])&unexplored and settings['max_candidates']-len(run['candidate_ids'])<=len(unexplored)
        if reserve_breadth or len(run['candidate_ids'])>=settings['max_candidates'] or sum(len(c['arguments']) for c in self._list(con,run['run_id'],'candidate'))+len(p['arguments'])>settings['max_argument_nodes']:
            frontier=dict(run_id=run['run_id'],proposal=p,reason='Reserve space for unexplored families' if reserve_breadth else 'Candidate or argument budget exhausted')
            self._save(con,'frontier',frontier,cid)
            if p['bundle_hash']:
                self.lc.state(con,p['bundle_hash'])
                con.execute('INSERT INTO interpretation_bindings VALUES(?,?,?,?)',(p['bundle_hash'],run['run_id'],cid,digest(frontier)))
            self._issue(con,run,'SEARCH_INCOMPLETE',p['source_unit_ids'],[],'Explore retained frontier families','Candidate/argument cap left a proposal unexplored')
            return {'deferred':True,'frontier_id':cid}
        ch=self._save(con,'candidate',value);run['candidate_ids'].append(cid)
        if p['bundle_hash']:
            self.lc.state(con,p['bundle_hash'])
            con.execute('INSERT INTO interpretation_bindings VALUES(?,?,?,?)',(p['bundle_hash'],run['run_id'],cid,ch))
        for a in p['assumptions']:
            if a['status']!='SOURCE_SUPPORTED':
                issue=self._issue(con,run,'DEFINITION',p['source_unit_ids'],[cid],a['statement'],'Unsettled assumption: '+a['status'])
                value['issue_ids'].append(issue['issue_id'])
        # Candidate is immutable after this transaction; child revisions retain their parent.
        if value['issue_ids']:
            ch=self._save(con,'candidate',value)
            con.execute('UPDATE interpretation_bindings SET candidate_hash=? WHERE run_id=? AND candidate_id=?',(ch,run['run_id'],cid))
        coverage=self._get(con,run['run_id'],'coverage',run['coverage_id'])
        coverage['explored_family_ids']=sorted(set(coverage['explored_family_ids'])|set(p['family_ids']))
        for d in coverage['dispositions']:
            if d['unit_id'] in p['source_unit_ids']:
                d.update(disposition='IMPLEMENTED',reason='Proposed candidate; meaning requires review',target_refs=d['target_refs']+[cid])
        self._save(con,'coverage',coverage)
        return value

    def propose(self, caller, key, run_id, proposal):
        def op(con):
            self._owner(con,caller,run_id);run=self._run(con,run_id,True)
            value=self._candidate(con,run,proposal,'HUMAN_AUTHORED');self._save_run(con,run);return value
        return self.db.mutate(caller,key,dict(op='interpretation.propose',run=run_id,proposal=proposal),op)

    def inventory_check(self, caller, key, run_id):
        def op(con):
            self._owner(con,caller,run_id);run=self._run(con,run_id,True)
            coverage=self._get(con,run_id,'coverage',run['coverage_id'])
            existing={(i['kind'],tuple(i['source_unit_ids'])) for i in self._list(con,run_id,'issue')}
            for d in coverage['dispositions']:
                if d['disposition']=='UNRESOLVED' and ('SOURCE_COVERAGE',(d['unit_id'],)) not in existing:
                    self._issue(con,run,'SOURCE_COVERAGE',[d['unit_id']],[],'Account for independently inventoried '+d['locator'],'All proposals omitted this unit')
            self._save_run(con,run);return coverage
        return self.db.mutate(caller,key,dict(op='interpretation.inventory',run=run_id),op)

    def invalidate_source(self, caller, key, source_key, replacement, reason):
        def op(con):
            self.lc.require(con,caller,'meaning')
            if not isinstance(reason,str) or not reason.strip(): raise LegalMathError('E_SCHEMA')
            p=self._validate_packet(con,replacement)
            if p['source_key']!=source_key: raise LegalMathError('E_REFERENCE')
            ph=self.db.put(con,'interpretation_packet',p)
            if not con.execute('SELECT 1 FROM interpretation_sources WHERE source_key=?',(source_key,)).fetchone(): raise LegalMathError('E_NOT_FOUND')
            con.execute('UPDATE interpretation_sources SET packet_hash=? WHERE source_key=?',(ph,source_key))
            con.execute('UPDATE interpretation_runs SET invalidated=1 WHERE source_key=? AND packet_hash!=?',(source_key,ph))
            return dict(source_packet_hash=ph,reason=reason,authority='LOCAL_SYNTHETIC')
        return self.db.mutate(caller,key,dict(op='interpretation.invalidate',source=source_key,replacement=replacement,reason=reason),op)

    def decide_issue(self, caller, key, run_id, issue_id, revision, candidate_id, decision, rationale, objection, evidence_refs):
        def op(con):
            self._owner(con,caller,run_id,'meaning');run=self._run(con,run_id,True)
            issue=self._get(con,run_id,'issue',issue_id)
            if issue['revision'] != revision: raise LegalMathError('E_STALE_REVIEW')
            c=self._get(con,run_id,'candidate',candidate_id)
            if issue['candidate_ids'] and candidate_id not in issue['candidate_ids']: raise LegalMathError('E_REFERENCE')
            refs=set(u['unit_id'] for u in self._packet(con,run)['units']) | {e['evidence_id'] for e in self._list(con,run_id,'evidence') if e['validation_status']=='VALIDATED'}
            if not set(evidence_refs)<=refs: raise LegalMathError('E_REFERENCE')
            value=dict(schema_version=V,decision_id=ident('decision'),run_id=run_id,issue_id=issue_id,issue_revision=revision,
                candidate_hash=digest(c),source_packet_hash=run['source_packet_hash'],reviewer_principal=caller,reviewer_role='LEGAL_INTERPRETATION_REVIEWER',authority='LOCAL_SYNTHETIC',
                decision=decision,proposition=issue['question'],rationale=rationale,strongest_objection_response=objection,conditions=[],evidence_refs=evidence_refs,recorded_at=self.clock())
            self._save(con,'issue-decision',value)
            if decision=='RESOLVE_MEANING':
                # Structural missing evidence is not cured by an interpretation vote.
                if issue['kind'] in ('SOURCE_COVERAGE','DEPENDENCY','INTEGRITY','SEARCH_INCOMPLETE','MEMBER_FAILURE','FORMAL_MISMATCH','JAVA_MISMATCH'):
                    raise LegalMathError('E_RELEASE_BLOCKED')
                evidence=dict(schema_version=V,evidence_id=ident('evidence'),run_id=run_id,source_packet_hash=run['source_packet_hash'],kind='HUMAN_ADJUDICATION',
                    content_hash=digest(value),statement=issue['question'],source_unit_ids=issue['source_unit_ids'],validation_status='VALIDATED',authority='AUTHENTICATED_REVIEW',validator_id=caller,
                    action_id=None,review_decision_id=value['decision_id'],domain_hash=None,comparison_result=None,legal_source_commitment_resolved=True)
                self._save(con,'evidence',evidence)
                issue.update(resolution_state='RESOLVED_ADJUDICATION',processing_state='TERMINAL',terminal_reason='RESOLVED',resolution_evidence_refs=[evidence['evidence_id']])
            elif decision=='REQUIRE_EVIDENCE': issue['processing_state']='AWAITING_EVIDENCE'
            issue['revision']+=1;self._save(con,'issue',issue);self._save_run(con,run)
            return value
        return self.db.mutate(caller,key,dict(op='interpretation.decide_issue',run=run_id,issue=issue_id,revision=revision,candidate=candidate_id,decision=decision,rationale=rationale,objection=objection,evidence_refs=evidence_refs),op)

    def review_inventory(self, caller, key, run_id, source_packet_hash, unit_ids, rationale):
        def op(con):
            self._owner(con,caller,run_id,'meaning');run=self._run(con,run_id,True)
            if run['source_packet_hash']!=source_packet_hash: raise LegalMathError('E_STALE_REVIEW')
            cov=self._get(con,run_id,'coverage',run['coverage_id'])
            if unit_ids!=cov['inventory_unit_ids'] or not isinstance(rationale,str) or not rationale.strip(): raise LegalMathError('E_SCHEMA')
            decision=dict(run_id=run_id,source_packet_hash=source_packet_hash,unit_ids=unit_ids,rationale=rationale,reviewer=caller,authority='LOCAL_SYNTHETIC')
            did=ident('inventory-review');self._save(con,'inventory-review',decision,did)
            cov.update(inventory_review_status='REVIEWED',review_decision_id=did);self._save(con,'coverage',cov);self._save_run(con,run)
            return decision
        return self.db.mutate(caller,key,dict(op='interpretation.review-inventory',run_id=run_id,source_packet_hash=source_packet_hash,unit_ids=unit_ids,rationale=rationale),op)
