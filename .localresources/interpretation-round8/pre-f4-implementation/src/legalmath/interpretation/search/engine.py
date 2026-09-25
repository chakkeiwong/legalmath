"""Executable breadth-first generation and bounded UCT/BFS evidence investigation.

The search never marks legal meaning resolved. Every terminal state preserves its
frontier and is bound to the existing interpretation/release service.
"""
from copy import deepcopy
import fcntl
import math
from pathlib import Path
import time
from ...canonical import canonical, digest
from ...errors import LegalMathError
from ..contracts import reference_policy, parse, TERMINAL
from ..service import ident
from ..actions import Actions
from ..reports import Reports
from .models import (Settings,Generation,Reconstruction,DIMENSIONS,commitment,
                     generation_request,strict_output_schema,validate_generation)
from .formal import bundle, reconstruction_request
from .arguments import evaluate_arguments
from .questions import questions,behavioral_groups

INITIAL=('normative','controlled-language','alternatives')
MOVES=('exception-attachment','scope-and-definition-distinction','counterexample-repair')


def create_search(service,caller,key,packet,settings=None):
    settings=settings or Settings()
    if set(packet['family_ids'])!=set(DIMENSIONS):
        raise LegalMathError('E_SCHEMA',details='Search packets must declare all six interpretation dimensions')
    policy={**reference_policy(),'policy_id':'research-search.v1','use':'RESEARCH_SEARCH',
        'max_actions_total':settings.max_model_calls+1,'max_resolution_rounds':settings.max_model_calls,
        'max_actions_per_issue_root':settings.max_actions_per_root,
        'max_no_progress_rounds':settings.max_model_calls,'max_candidates':settings.max_candidates,
        'run_deadline_seconds':settings.deadline_seconds,'action_timeout_seconds':settings.timeout_seconds}
    run=service.create(caller,key,packet,policy)
    with service.db.transaction() as con:
        configurations=service._list(con,run['run_id'],'search-config')
        if configurations and configurations[0]['settings']!=settings.model_dump():
            raise LegalMathError('E_IDEMPOTENCY',details='Search settings changed under an existing run key')
        if not configurations:
            service._save(con,'search-config',{'run_id':run['run_id'],'settings':settings.model_dump(),
                'profile':'SOURCE_DRIVEN_RESEARCH_SEARCH','source_packet_hash':run['source_packet_hash']},'config')
    return run


def select_node(nodes,settings):
    roots_by_id={n['node_id']:n for n in nodes if n['parent'] is None}
    eligible=[n for n in nodes if (not n['expanded'] or n.get('repair_needed')) and n['depth']<settings.max_depth
              and roots_by_id[n['root']].get('issued_calls',0)<settings.max_actions_per_root]
    if not eligible:return None
    if settings.scheduler=='bfs':return min(eligible,key=lambda n:(n['depth'],n['order']))
    roots=[n for n in nodes if n['parent'] is None]
    total=max(1,sum(n['visits'] for n in roots))
    by_id={n['node_id']:n for n in nodes}
    def score(n):
        if n['visits']==0:return float('inf')
        visits=by_id[n['parent']]['visits'] if n['parent'] else total
        return n['reward']/n['visits']+(settings.exploration_weight_milli/1000)*math.sqrt(math.log(max(1,visits))/n['visits'])
    def descend(candidates):
        choice=max(candidates,key=lambda n:(score(n),-n['order']))
        if choice in eligible:return choice
        children=[n for n in nodes if n['parent']==choice['node_id'] and has_eligible(n)]
        return descend(children)
    def has_eligible(n):
        return n in eligible or any(has_eligible(c) for c in nodes if c['parent']==n['node_id'])
    return descend([n for n in roots if has_eligible(n)])


def backpropagate(nodes,node_id,reward):
    index={n['node_id']:n for n in nodes}
    while node_id is not None:
        node=index[node_id];node['visits']+=1;node['reward']+=reward;node_id=node['parent']


class Search:
    def __init__(self,service,caller,run_id,provider,checker):
        self.s=service;self.db=service.db;self.caller=caller;self.rid=run_id
        self.provider=provider;self.checker=checker;self.actions=Actions(service)
        with self.db.connect() as con:
            self.s._owner(con,caller,run_id)
            self.run=self.s._run(con,run_id);self.packet=self.s._packet(con,self.run)
            config=self.s._get(con,run_id,'search-config','config')
            self.settings=Settings.model_validate(config['settings'])
        self.state={'run_id':run_id,'nodes':[],'comparisons':[],'roundtrips':[],
            'failures':[],'initial':{},'frontier':[],'rounds':0,'no_progress':0,
            'model_calls':0,'provider_id':provider.provider_id,'live_provider':provider.live,
            'pending':None,'stop':None,'retrievals':[],'java_checks':[]}
        self.worker=ident('searchworker')

    def save(self):
        with self.db.transaction() as con:self.s._save(con,'search-state',self.state,'state')

    def issue(self,kind,question,units=None,candidates=None):
        with self.db.transaction() as con:
            run=self.s._run(con,self.rid,True)
            previous=[i for i in self.s._list(con,self.rid,'issue') if i['kind']==kind and i['question']==question]
            if previous:return previous[0]['issue_id']
            result=self.s._issue(con,run,kind,units or [],candidates or [],question,'Search evidence requires review')
            self.s._save_run(con,run);return result['issue_id']

    def stopped(self):
        with self.db.connect() as con:
            row=con.execute('SELECT invalidated,cancelled FROM interpretation_runs WHERE id=?',(self.rid,)).fetchone()
            run=self.s._run(con,self.rid)
        if row['invalidated']:return 'SOURCE_CHANGED'
        if row['cancelled'] or run['status']=='CANCELLED':return 'CANCELLED'
        if self.s.clock()>=run['deadline']:return 'DEADLINE'
        if self.state['model_calls']>=self.settings.max_model_calls:return 'CALL_LIMIT'
        return None

    def call(self,request,model,*,role=None,node=None,repairs_left=None):
        if repairs_left is None:repairs_left=self.settings.max_output_repairs
        if self.stopped():raise LegalMathError('E_RESOURCE_LIMIT',details=self.stopped())
        root_issue=None if role else self.issue('DEFINITION','Investigate reading '+node['root'])
        action=self.actions.reserve(self.rid,role=role,issue_id=root_issue,
            kind='INITIAL_PROPOSAL' if role else 'REPAIR',adapter=self.provider.provider_id,
            inputs=[digest(request)],question=request['task']+': '+(role or node['node_id']))
        if action['state']!='RESERVED':raise LegalMathError('E_JOB_STATE',details='No hidden repeat dispatch')
        action=self.actions.claim(self.rid,action['action_id'],self.worker)
        if node:
            root=next((n for n in self.state['nodes'] if n['node_id']==node['root']),None)
            if root:root['issued_calls']+=1
        self.state['model_calls']+=1;self.state['pending']=action['action_id'];self.save()
        with self.db.transaction() as con:
            self.s._save(con,'search-request',{'run_id':self.rid,'action_id':action['action_id'],
                'request':request,'schema':strict_output_schema(model)},action['action_id'])
        self.actions.dispatch(self.rid,action['action_id'],self.worker,action['fencing_token'])
        answer=None
        try:
            answer=self.provider.complete(request,strict_output_schema(model),self.settings)
            # Persist the raw response before attempting interpretation or validation.
            with self.db.transaction() as con:
                self.s._save(con,'search-response',{'run_id':self.rid,'action_id':action['action_id'],
                    'response':answer.value,'provenance':answer.provenance},action['action_id'])
            value=validate_generation(answer.value,self.packet) if model is Generation else parse(model,answer.value)
            accepted=self.actions.complete(self.rid,action['action_id'],self.worker,action['fencing_token'],
                {'response':answer.value,'provenance':answer.provenance})
            if not accepted:raise LegalMathError('E_JOB_STATE',details='Late, cancelled or stale response')
        except Exception as exc:
            if not isinstance(exc,(LegalMathError,ValueError,TimeoutError,OSError)):raise
            self.actions.complete(self.rid,action['action_id'],self.worker,action['fencing_token'],
                {'error':getattr(exc,'code',type(exc).__name__)},'FAILED')
            self.state['failures'].append({'action_id':action['action_id'],'stage':request['task'],
                'error':getattr(exc,'code',type(exc).__name__),'details':str(getattr(exc,'details',None) or exc)[:1000]})
            self.state['pending']=None;self.save()
            if not self.stopped():self.issue('MEMBER_FAILURE','Failed '+request['task']+' action '+action['action_id'])
            actual_root=next((n for n in self.state['nodes'] if node and n['node_id']==node['root']),None)
            root_available=actual_root is None or actual_root['issued_calls']<self.settings.max_actions_per_root
            if (answer is not None and repairs_left>0 and not self.stopped() and root_available
                    and getattr(exc,'code',None) in ('E_SCHEMA','E_REFERENCE','E_DUPLICATE_ID','E_TYPE')):
                # Repair only this member's malformed output; no peer answers enter the request.
                correction={**request,'task':'REPAIR_OUTPUT','invalid_response':answer.value,
                    'validation_error':getattr(exc,'code',type(exc).__name__),
                    'validation_details':str(getattr(exc,'details',None) or exc)[:1000],
                    'repair_of_request_hash':digest(request),
                    'allowed_source_unit_ids':[u['unit_id'] for u in self.packet['units']],
                    'repair_instruction':'Fix the contract/source-reference error using exact supplied units. '
                    'Preserve source uncertainty and valid substantive alternatives; never fabricate citations.'}
                target=node or {'node_id':'initial.'+role,'root':'initial.'+role}
                if role:
                    with self.db.transaction() as con:
                        run=self.s._run(con,self.rid,True);run['status']='RESOLVING';self.s._save_run(con,run)
                failure_index=len(self.state['failures'])-1
                try:
                    repaired=self.call(correction,model,node=target,repairs_left=repairs_left-1)
                    if repaired is not None:
                        self.state['failures'][failure_index]['repair']='VALIDATED_OUTPUT_ONLY_MEANING_UNRESOLVED'
                        self.state['failures'][failure_index]['repaired_response_hash']=digest(repaired);self.save()
                    return repaired
                finally:
                    if role and self.stopped() not in ('CANCELLED','SOURCE_CHANGED','DEADLINE'):
                        with self.db.transaction() as con:
                            run=self.s._run(con,self.rid,True);run['status']='INITIAL_PROPOSALS';self.s._save_run(con,run)
            return None
        self.state['pending']=None;self.save()
        return value

    def add(self,reading,parent=None):
        key=commitment(reading)
        duplicate=next((n for n in self.state['nodes'] if n['commitment']==key),None)
        if duplicate:return None
        if len(self.state['nodes'])>=self.settings.max_candidates:
            self.state['frontier'].append({'reading':reading,'parent':parent,'reason':'CANDIDATE_LIMIT'})
            self.issue('SEARCH_INCOMPLETE','Candidate cap leaves an unexpanded interpretation')
            return None
        node_id='node.'+key[:24];compiled=None;encoding_error=None
        try:compiled=bundle(reading,self.packet,self.checker.at)
        except LegalMathError as exc:encoding_error={'code':exc.code,'details':str(exc.details)}
        with self.db.transaction() as con:
            run=self.s._run(con,self.rid,True)
            bundle_hash=None
            if compiled:
                bundle_hash=self.db.put(con,'bundle',compiled)
                old=con.execute('SELECT author FROM bundles WHERE hash=?',(bundle_hash,)).fetchone()
                if old and old['author']!=self.caller:raise LegalMathError('E_AUTHORITY')
                con.execute("INSERT OR IGNORE INTO bundles VALUES(?,?,NULL,'DRAFT',1)",(bundle_hash,self.caller))
            parents={n['node_id']:n for n in self.state['nodes']}
            proposal={'source_packet_hash':run['source_packet_hash'],
                'source_unit_ids':sorted({q['unit_id'] for q in reading['citations']}),
                'family_ids':[reading['family']],'subject_unit':reading['subject'],
                'controlled_language':reading['statement'],'bundle_hash':bundle_hash,
                'assumptions':[{'assumption_id':node_id+'.a'+str(i),'statement':text,'provenance_refs':[],
                    'status':'PROVISIONAL'} for i,text in enumerate(reading['assumptions'])],
                'arguments':[],'parent_id':parents[parent]['candidate_id'] if parent else None,
                'revision_reason':reading['distinction']}
            # Register every generated commitment even when the legacy family reservation would
            # defer it: the search itself preserves its frontier before selecting refinements.
            candidate=self.s._candidate(con,run,proposal,'SHARED_RESOLUTION' if parent else 'BLIND_INITIAL')
            if candidate.get('deferred'):
                self.state['frontier'].append({'reading':reading,'parent':parent,'reason':'LEGACY_FAMILY_RESERVATION'})
                self.s._save_run(con,run);return None
            self.s._save_run(con,run)
        node={'node_id':node_id,'candidate_id':candidate['candidate_id'],'commitment':key,
            'reading':reading,'bundle_hash':bundle_hash,'encoding_error':encoding_error,
            'parent':parent,'root':parents[parent]['root'] if parent else node_id,
            'depth':parents[parent]['depth']+1 if parent else 0,'order':len(self.state['nodes']),
            'visits':0,'reward':0,'issued_calls':0,'expanded':False,'roundtrip_done':False,
            'repair_needed':False,'disposition':'UNREVIEWED'}
        self.state['nodes'].append(node)
        if encoding_error:self.issue('FORMAL_MISMATCH','Encoding unavailable for '+node_id,candidates=[candidate['candidate_id']])
        for question in reading['questions']:self.issue('DEFINITION',question,candidates=[candidate['candidate_id']])
        self.save()
        if compiled:
            checked=self.checker.verify(reading,self.packet)
            self.state['java_checks'].append({'node_id':node_id,'result':checked});self.save()
        return node

    def compare_new(self,node):
        if node['encoding_error']:return 0
        reward=0
        for other in self.state['nodes']:
            if other['node_id']==node['node_id'] or other['encoding_error']:continue
            pair=sorted([node['node_id'],other['node_id']])
            if any(c['pair']==pair for c in self.state['comparisons']):continue
            if len(self.state['comparisons'])>=self.settings.max_comparisons:
                self.issue('SEARCH_INCOMPLETE','Formal comparison cap reached');break
            result=self.checker.compare(node['reading'],other['reading'],self.packet)
            self.state['comparisons'].append({'pair':pair,'left_node_id':node['node_id'],
                'right_node_id':other['node_id'],'result':result})
            if result['status']=='DIFFERENT':
                reward+=1
                self.issue('FORMAL_MISMATCH','Distinguish '+pair[0]+' from '+pair[1],
                    candidates=[node['candidate_id'],other['candidate_id']])
            elif result['status'] not in ('EQUIVALENT_WITHIN_DOMAIN',):
                self.issue('DEFINITION','Comparison remains '+result['status']+' for '+pair[0]+' / '+pair[1])
        self.save();return reward

    def reconstruct(self,node):
        if node['encoding_error'] or node['roundtrip_done']:return
        root=next(n for n in self.state['nodes'] if n['node_id']==node['root'])
        if root['issued_calls']>=self.settings.max_actions_per_root:return
        original=node['reading'];compiled=bundle(original,self.packet,self.checker.at)
        value=self.call(reconstruction_request(original,compiled),Reconstruction,node=node)
        node['roundtrip_done']=value is not None
        if value:
            reconstructed={**deepcopy(original),'formalization':value['formalization']}
            try:result=self.checker.compare(original,reconstructed,self.packet)
            except LegalMathError as exc:result={'status':'ENCODING_ERROR','code':exc.code}
            self.state['roundtrips'].append({'node_id':node['node_id'],'reconstruction':value,'result':result})
            if result['status']!='EQUIVALENT_WITHIN_DOMAIN' or value['uncertainty']:
                self.issue('FORMAL_MISMATCH','Round-trip '+result['status']+' for '+node['node_id'])
            if result['status'] in ('DIFFERENT','ENCODING_ERROR','INCOMPARABLE_FACT_BINDINGS'):
                node['repair_needed']=True
        self.save()

    def retrieve(self,node):
        """Deterministic source lookup: actual retained text, no model-supplied URLs."""
        cited={q['unit_id'] for q in node['reading']['citations']}
        overlooked=[u for u in self.packet['units'] if u['unit_id'] not in cited]
        evidence={'node_id':node['node_id'],'retained_uncited_units':overlooked,
            'missing_dependencies':[d['dependency_id'] for d in self.packet['dependencies'] if d['source_hash'] is None]}
        self.state['retrievals'].append(evidence);self.save();return evidence

    def drive(self):
        lockpath=self.db.root/('search-'+self.rid+'.lock')
        with lockpath.open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise LegalMathError('E_JOB_STATE')
            with self.db.connect() as con:
                reports=self.s._list(con,self.rid,'search-report')
                if reports:return self.verify_report()
                saved=self.s._list(con,self.rid,'search-state')
            if saved:
                self.state=saved[-1]
                # A process interruption has unknown remote effects. Never redispatch it.
                self.state['stop']='INTERRUPTED_REVIEW_REQUIRED'
                if self.state['pending']:
                    self.state['failures'].append({'stage':'RECOVERY','action_id':self.state['pending'],
                        'error':'RESULT_UNKNOWN','details':'Dispatch is not retried or refunded'})
                self.save();return self.finish()
            try:return self._drive()
            except Exception as exc:
                self.state['failures'].append({'stage':'ENGINE','error':getattr(exc,'code',type(exc).__name__),
                    'details':str(getattr(exc,'details',None) or exc)[:1000]})
                terminal=self.stopped()
                self.state['stop']=terminal if terminal in ('CANCELLED','SOURCE_CHANGED','DEADLINE') else 'ENGINE_FAILURE';self.save()
                return self.finish()

    def _drive(self):
        self.save()
        # Independent local inventory action precedes generation; no member can remove a unit.
        a=self.actions.reserve(self.rid,role='inventory',inputs=[self.run['source_packet_hash']],adapter='frozen-inventory')
        a=self.actions.claim(self.rid,a['action_id'],self.worker);self.actions.dispatch(self.rid,a['action_id'],self.worker,a['fencing_token'])
        self.actions.complete(self.rid,a['action_id'],self.worker,a['fencing_token'],{'inventory':[u['unit_id'] for u in self.packet['units']]})
        for role in INITIAL:
            if self.stopped():break
            response=self.call(generation_request(self.packet,role),Generation,role=role)
            self.state['initial'][role]=response;self.save()
            if response is None and self.state['failures'] and self.state['failures'][-1]['error']=='E_DEPENDENCY':
                self.state['stop']='PROVIDER_UNAVAILABLE';break
        # Freeze all initial outputs before exposing any peer candidate to refinement.
        for response in self.state['initial'].values():
            if response:
                for reading in response['readings']:self.add(reading)
                for q in response['questions']:self.issue('DEFINITION',q)
        with self.db.transaction() as con:
            run=self.s._run(con,self.rid,True);run['status']='RESOLVING'
            run['completed_initial_roles']=['inventory']+[r for r,v in self.state['initial'].items() if v]
            self.s._save_run(con,run)
        self.s.inventory_check(self.caller,'search.inventory.'+self.rid,self.rid)
        self.issue('DEFINITION','Independent source interpretation and business-fact review is required')
        for dep in self.packet['dependencies']:
            if dep['source_hash'] is None:self.issue('DEPENDENCY','Acquire authority '+dep['dependency_id'])
        for node in list(self.state['nodes']):self.compare_new(node)
        while not self.stopped() and not self.state['stop'] and self.state['rounds']<self.settings.max_rounds:
            node=select_node(self.state['nodes'],self.settings)
            if node is None:self.state['stop']='FRONTIER_EXHAUSTED_WITH_UNRESOLVED_MEANING';break
            self.state['rounds']+=1
            retrieval=self.retrieve(node)
            diagnostics=[c for c in self.state['comparisons'] if node['node_id'] in c['pair']]
            drift=[r for r in self.state['roundtrips'] if r['node_id']==node['node_id']]
            request=generation_request(self.packet,'adversarial-investigator',parent=node['reading'],
                diagnostics=[{'encoding_error':node['encoding_error'],'retrieval':retrieval,
                    'roundtrip_diagnostics':[{'result_status':r['result']['status'],'uncertainty':r['reconstruction']['uncertainty']} for r in drift]},
                    *[{'pair':c['pair'],'status':c['result']['status'],'snapshot':c['result'].get('snapshot')} for c in diagnostics]],
                move=MOVES[(self.state['rounds']-1)%len(MOVES)])
            value=self.call(request,Generation,node=node);node['expanded']=True;node['repair_needed']=False;reward=0;new=[]
            if value:
                for reading in value['readings']:
                    child=self.add(reading,node['node_id'])
                    if child:new.append(child);reward+=self.compare_new(child)
                for q in value['questions']:self.issue('DEFINITION',q)
            # Only replayable behavioral distinctions contribute to this scheduling reward.
            backpropagate(self.state['nodes'],node['node_id'],reward)
            self.state['no_progress']=0 if new or reward else self.state['no_progress']+1
            self.save()
            if self.settings.reconstruction_required and not self.stopped():
                target=next((n for n in [*new,node] if not n['encoding_error'] and not n['roundtrip_done']),None)
                if target:self.reconstruct(target)
            if self.state['no_progress']>=self.settings.max_no_progress:
                self.state['stop']='NO_PROGRESS';break
        self.state['stop']=self.stopped() or self.state['stop'] or 'ROUND_LIMIT';self.save()
        return self.finish()

    def material(self):
        nodes=self.state['nodes'];edges=[]
        for c in self.state['comparisons']:
            if c['result']['status']=='DIFFERENT':edges.extend([c['pair'],list(reversed(c['pair']))])
        argumentation=evaluate_arguments([n['node_id'] for n in nodes],edges,maximum=self.settings.max_argument_nodes) if len(nodes)<=self.settings.max_argument_nodes else {'status':'ARGUMENT_LIMIT','legal_premises_verified':False}
        considered={v['dimension'] for r in self.state['initial'].values() if r for v in r['dimensions']}
        unresolved_units=sorted({d['unit_id'] for r in self.state['initial'].values() if r for d in r['coverage'] if d['status'] in ('DEFERRED','UNCERTAIN')})
        with self.db.connect() as con:
            issues=self.s._list(con,self.rid,'issue');requests=self.s._list(con,self.rid,'search-request')
            actions=self.s._list(con,self.rid,'action');responses=self.s._list(con,self.rid,'search-response')
        return {'candidate_ids':[n['candidate_id'] for n in nodes],
            'unexpanded_nodes':[n['node_id'] for n in nodes if not n['expanded']],
            'unreconstructed_nodes':[n['node_id'] for n in nodes if not n['roundtrip_done']],
            'unconsidered_dimensions':sorted(set(DIMENSIONS)-considered),
            'deferred_or_uncertain_units':unresolved_units,'argumentation':argumentation,
            'all_issue_ids':[i['issue_id'] for i in issues],
            'material_unresolved_issue_ids':[i['issue_id'] for i in issues if i['resolution_state']=='UNRESOLVED'],
            'request_hashes':[digest(r) for r in requests], 'action_hashes':[digest(a) for a in actions],
            'response_hashes':[digest(r) for r in responses],
            'java_check_hashes':[digest(c) for c in self.state.get('java_checks',[])],
            'distinguishing_questions':questions(nodes,self.state['comparisons'],self.packet,self.checker.at),
            'behavioral_groups':behavioral_groups(nodes,self.state['comparisons']),
            'pending_repairs':[n['node_id'] for n in nodes if n.get('repair_needed')],
            'formal_scope_complete':False,'independent_meaning_review':False}

    def finish(self):
        with self.db.connect() as con:run=self.s._run(con,self.rid)
        if run['status'] not in TERMINAL:
            Reports(self.s).finish(self.rid,'INTEGRITY_FAILURE' if self.state['stop']=='ENGINE_FAILURE' else 'HUMAN_REQUIRED')
        report=self.report_value()
        with self.db.transaction() as con:self.s._save(con,'search-report',report,'report')
        return report

    def report_value(self):
        return {'run_id':self.rid,'state_hash':digest(self.state),'source_packet_hash':self.run['source_packet_hash'],
            'status':{'ENGINE_FAILURE':'FAILED_INTEGRITY','SOURCE_CHANGED':'FAILED_INTEGRITY','CANCELLED':'CANCELLED'}.get(self.state['stop'],'BLOCKED_UNRESOLVED'),
            'stop':self.state['stop'],'settings':self.settings.model_dump(),'material':self.material(),
            'model_calls':self.state['model_calls'],'search_rounds':self.state['rounds'],
            'live_provider':self.state['live_provider'],'probability_of_legal_correctness':None,'release_eligible':False,
            'score_meaning':'Number of replayed behavioral differences; investigation priority only',
            'limits':['No independent legal adjudication','Finite source inventory and search budget',
                      'Fresh contexts do not establish model independence','Argument attacks encode behavioral incompatibility, not legal defeat',
                      'Round-trip consistency cannot establish fidelity to original English']}

    def verify_report(self):
        with self.db.connect() as con:
            self.state=self.s._get(con,self.rid,'search-state','state')
            report=self.s._get(con,self.rid,'search-report','report')
        if report!=self.report_value():raise LegalMathError('E_INTEGRITY')
        return report
