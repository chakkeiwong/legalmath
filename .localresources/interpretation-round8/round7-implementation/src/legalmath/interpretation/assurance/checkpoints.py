"""Exact task checkpoints with independently counted dispatches and bounded repairs.

Completion means validated coverage of requested checks. It never denotes the
truth of a model's source interpretation or confers release authority.
"""
from copy import deepcopy
from pathlib import Path
import fcntl
import time
from ...canonical import canonical,digest,loads,raw_digest
from ...errors import LegalMathError
from ..contracts import parse
from ..search.providers import verify_allowance_checkpoint
from .decomposition import compact_request
from .journal import JournalProvider
from .monitor import save
from .semantics import (Fidelity,fidelity_request,validate_fidelity,
                        validate_fidelity_aggregate,fidelity_findings)
from .arguments import Criticism,evaluate_criticism
from .relevance import RelevanceReview,validate_relevance
from .transport import transient_service_failure


def method_hash():
    here=Path(__file__).parent
    paths=[Path(__file__),here/'semantics.py',here/'arguments.py',here/'relevance.py',
           here/'decomposition.py',here/'journal.py',here/'transport.py',
           here.parent/'contracts.py',here.parent/'search/providers.py']
    return digest({p.name:raw_digest(p.read_bytes()) for p in paths})


def task_spec(kind,request,context):
    schemas={'FIDELITY':Fidelity,'RELEVANCE':RelevanceReview,'CRITICISM':Criticism}
    if kind not in schemas:raise LegalMathError('E_SCHEMA')
    value={'kind':kind,'request':request,'schema':schemas[kind].model_json_schema(),'context':context}
    return {'task_id':'task.'+digest(value),**deepcopy(value)}


def plan_tasks(tasks,route_hash,*,maximum_attempts=3):
    if not tasks or len(tasks)>1024 or len({t['task_id'] for t in tasks})!=len(tasks):
        raise LegalMathError('E_RESOURCE_LIMIT')
    if type(maximum_attempts)is not int or not 1<=maximum_attempts<=3:raise LegalMathError('E_SCHEMA')
    return {'version':'legalmath.checkpoints.v1','method_hash':method_hash(),'route_hash':route_hash,
            'maximum_attempts':maximum_attempts,'tasks':deepcopy(tasks)}


def fidelity_plan(packet,claims,candidates,route_hash,*,batch_size=4,maximum_attempts=3):
    if type(batch_size)is not int or not 1<=batch_size<=64:raise LegalMathError('E_SCHEMA')
    ids=[c['claim_id'] for c in claims]
    if len(ids)!=len(set(ids)):raise LegalMathError('E_DUPLICATE_ID')
    pairs=[(c['claim_id'],cid) for c in claims if c['relevance']!='CONTEXT' for cid in candidates]
    if not pairs or len(pairs)>4096:raise LegalMathError('E_RESOURCE_LIMIT')
    tasks=[]
    for start in range(0,len(pairs),batch_size):
        batch=pairs[start:start+batch_size];request=fidelity_request(packet,claims,candidates,batch)
        tasks.append(task_spec('FIDELITY',request,{'packet':packet,'claims':claims,'candidates':candidates,
            'required_pairs':[list(p) for p in batch]}))
    return plan_tasks(tasks,route_hash,maximum_attempts=maximum_attempts)


def validate_task(task,value):
    context=task['context']
    if task['kind']=='FIDELITY':
        return validate_fidelity(value,context['packet'],context['claims'],context['candidates'],
                                 [tuple(p) for p in context['required_pairs']])
    if task['kind']=='RELEVANCE':
        return validate_relevance(value,context['packet'],context['claims'])
    result=parse(Criticism,value);evaluation=evaluate_criticism(result,context['packet'],context['candidates'])
    if set(context['candidates'])!={a['candidate_id'] for a in result['arguments']}:
        raise LegalMathError('E_REFERENCE',details='Every candidate needs a structured argument')
    if evaluation['status'] in ('ARGUMENT_LIMIT','CYCLIC_SUPPORT_UNRESOLVED'):
        raise LegalMathError('E_REFERENCE',details=evaluation)
    return result


def check_manifest(directory,expected_hash=None):
    directory=Path(directory).resolve();manifest=loads((directory/'manifest.json').read_bytes())
    if expected_hash is not None and digest(manifest)!=expected_hash:raise LegalMathError('E_INTEGRITY')
    for name,expected in manifest['files'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory) or raw_digest(path.read_bytes())!=expected:
            raise LegalMathError('E_INTEGRITY',details='Checkpoint file changed: '+name)
    return manifest


def seal(directory):
    manifest={'files':{str(p.relative_to(directory)):raw_digest(p.read_bytes()) for p in sorted(directory.rglob('*'))
                      if p.is_file() and p.name!='manifest.json'}}
    save(directory/'manifest.json',manifest);return digest(manifest)


def receipt(request,response,ledger_path,route_hash):
    ledger_path=Path(ledger_path).resolve();ledger=loads(ledger_path.read_bytes())
    provenance=response['provenance'];slot=provenance.get('allowance_slot')
    wire=compact_request(request);wire_hash=digest(wire)
    if (type(slot)is not int or not 1<=slot<=len(ledger['calls']) or
        ledger['calls'][slot-1]['request_hash']!=wire_hash or
        provenance.get('request_hash')!=wire_hash or provenance.get('provider_route_hash')!=route_hash):
        raise LegalMathError('E_INTEGRITY',details='Response has no matching route/reservation')
    if wire!=request and (provenance.get('original_request_hash')!=digest(request) or
        provenance.get('wire_request_hash')!=wire_hash or provenance.get('compact_request')!=wire):
        raise LegalMathError('E_INTEGRITY',details='Invalid exact-source transport mapping')
    return {'ledger_path':str(ledger_path),'ledger_checkpoint_hash':digest(ledger),'allowance_slot':slot,
            'wire_request_hash':wire_hash,'request_hash':digest(request),'response_hash':digest(response['value']),
            'route_hash':route_hash}


def verify_receipt(value,request,response,route_hash):
    if value['route_hash']!=route_hash or value['response_hash']!=digest(response['value']):
        raise LegalMathError('E_INTEGRITY')
    verify_allowance_checkpoint(value['ledger_path'],value['ledger_checkpoint_hash'])
    current=receipt(request,response,value['ledger_path'],route_hash)
    if any(current[k]!=value[k] for k in ('allowance_slot','wire_request_hash','request_hash','response_hash')):
        raise LegalMathError('E_INTEGRITY')


_REPAIR_KEYS = frozenset({
    'task', 'original_task', 'repair_of_request_hash', 'invalid_response',
    'validation_error_data', 'response_schema', 'repair_instruction',
})


def _validate_repair_request(request, task):
    """Keep a repair focused on output structure, never on the checked input.

    A repair may add validator feedback and the prior response, but the source
    packet, claims, candidates, pair list and protocol instructions are frozen
    by the task identity.  This check prevents a provider from changing the
    question after a failed attempt and then presenting the new answer as a
    repair of the old one.
    """
    base = task['request']
    if request.get('task') != 'REPAIR_OUTPUT' or request.get('original_task') != base.get('original_task',base['task']):
        raise LegalMathError('E_INTEGRITY', details='Repair changed the original task identity')
    if request.get('repair_of_request_hash') != digest(base):
        raise LegalMathError('E_INTEGRITY', details='Repair is not bound to its failed request')
    if request.get('response_schema') != task['schema']:
        raise LegalMathError('E_INTEGRITY', details='Repair changed the response schema')
    for key, value in base.items():
        if key not in _REPAIR_KEYS and request.get(key) != value:
            raise LegalMathError('E_INTEGRITY', details='Repair changed protected request field: '+key)
    if set(request) - set(base) - _REPAIR_KEYS:
        raise LegalMathError('E_INTEGRITY', details='Repair introduced an unreviewed request field')


def repair_request(task,prior):
    request=deepcopy(task['request'])
    if prior is not None and (prior/'response.json').exists():
        error=loads((prior/'outcome.json').read_bytes())
        request.update(task='REPAIR_OUTPUT',original_task=task['request'].get('original_task',task['request']['task']),
            repair_of_request_hash=digest(task['request']),invalid_response=loads((prior/'response.json').read_bytes())['value'],
            validation_error_data=error.get('details'),response_schema=task['schema'],
            repair_instruction='Repair only the reported structural/evidence errors; retain uncertainty, IDs and source. Do not assert legal certainty.')
    return request


class CheckpointQueue:
    def __init__(self,directory,plan):
        self.directory=Path(directory).resolve();self.directory.mkdir(parents=True,exist_ok=True)
        self.plan=deepcopy(plan);self.hash=digest(plan)
        if (type(plan['maximum_attempts'])is not int or not 1<=plan['maximum_attempts']<=3 or
                not plan['tasks'] or len(plan['tasks'])>1024 or
                len({t['task_id'] for t in plan['tasks']})!=len(plan['tasks'])):
            raise LegalMathError('E_SCHEMA')
        if plan['method_hash']!=method_hash():raise LegalMathError('E_STALE_REVIEW')
        for task in plan['tasks']:
            if task!=task_spec(task['kind'],task['request'],task['context']):raise LegalMathError('E_INTEGRITY')
        self.tasks={t['task_id']:t for t in plan['tasks']}
        path=self.directory/'plan.json'
        if path.exists():
            if loads(path.read_bytes())!=plan:raise LegalMathError('E_IDEMPOTENCY')
        else:save(path,plan)
        self.state_path=self.directory/'state.json'
        if not self.state_path.exists():save(self.state_path,{'plan_hash':self.hash,
            'tasks':{t:{'attempts':[],'import':None} for t in self.tasks}})

    def _state(self):
        if loads((self.directory/'plan.json').read_bytes())!=self.plan or method_hash()!=self.plan['method_hash']:
            raise LegalMathError('E_STALE_REVIEW')
        state=loads(self.state_path.read_bytes())
        if state['plan_hash']!=self.hash or set(state['tasks'])!=set(self.tasks):raise LegalMathError('E_INTEGRITY')
        return state

    def _record(self,task,entry,prior=None):
        path=(self.directory/entry['path']).resolve()
        if not path.is_relative_to(self.directory):raise LegalMathError('E_INTEGRITY')
        if entry['status']=='RESERVED':raise LegalMathError('E_JOB_STATE',details='Explicit recovery required for interrupted task')
        manifest=check_manifest(path,entry['manifest_hash'])
        if 'outcome.json' not in manifest['files']:raise LegalMathError('E_INTEGRITY')
        outcome=loads((path/'outcome.json').read_bytes())
        if outcome['task_id']!=task['task_id'] or outcome['status']!=entry['status']:raise LegalMathError('E_INTEGRITY')
        if entry['status']!='VALIDATED':return None
        required={'request.json','schema.json','response.json','receipt.json','validated.json'}
        if not required<=set(manifest['files']):raise LegalMathError('E_INTEGRITY')
        request=loads((path/'request.json').read_bytes());response=loads((path/'response.json').read_bytes())
        if (loads((path/'schema.json').read_bytes())!=task['schema'] or
                request!=repair_request(task,prior)):
            raise LegalMathError('E_INTEGRITY')
        if request != task['request']:
            _validate_repair_request(request, task)
        verify_receipt(loads((path/'receipt.json').read_bytes()),request,response,self.plan['route_hash'])
        result=validate_task(task,response['value'])
        if loads((path/'validated.json').read_bytes())!=result:raise LegalMathError('E_INTEGRITY')
        return result

    def _results(self,state):
        results={}
        for key,record in state['tasks'].items():
            if len(record['attempts'])>self.plan['maximum_attempts']:raise LegalMathError('E_INTEGRITY')
            entries=([record['import']] if record['import'] else [])+record['attempts']
            prior=None
            for entry in entries:
                result=self._record(self.tasks[key],entry,prior)
                if result is not None:
                    if key in results:raise LegalMathError('E_DUPLICATE_ID',details='Repeated completed task')
                    results[key]=result
                prior=(self.directory/entry['path']).resolve()
        return results

    def import_response(self,task_id,origin,manifest_directory,ledger_path):
        """Copy only an exact hash/route/reservation-verified historical response."""
        with (self.directory/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=self._state();self._results(state)
            task=self.tasks[task_id];entry=state['tasks'][task_id]
            if entry['import'] or entry['attempts']:raise LegalMathError('E_IDEMPOTENCY')
            origin=Path(origin).resolve();parent=Path(manifest_directory).resolve();manifest=check_manifest(parent)
            if not origin.is_relative_to(parent):raise LegalMathError('E_INTEGRITY')
            for name in ('request.json','schema.json','response.json','status.json'):
                if str((origin/name).relative_to(parent)) not in manifest['files']:raise LegalMathError('E_INTEGRITY')
            request=loads((origin/'request.json').read_bytes());schema=loads((origin/'schema.json').read_bytes())
            response=loads((origin/'response.json').read_bytes());status=loads((origin/'status.json').read_bytes())
            if (request!=task['request'] or schema!=task['schema'] or status.get('request_hash')!=digest(request)
                or status.get('response_hash')!=digest(response['value'])):raise LegalMathError('E_INTEGRITY')
            proof=receipt(request,response,ledger_path,self.plan['route_hash']);result=validate_task(task,response['value'])
            path=self.directory/'imports'/task_id;path.mkdir(parents=True,exist_ok=False)
            for name,value in [('request',request),('schema',schema),('response',response),('receipt',proof),('validated',result)]:
                save(path/(name+'.json'),value)
            save(path/'origin.json',{'path':str(origin),'manifest_hash':digest(manifest),'new_live_invocation':False})
            save(path/'outcome.json',{'task_id':task_id,'status':'VALIDATED','source':'RETAINED_COUNTED_ACTION'})
            entry['import']={'path':str(path.relative_to(self.directory)),'status':'VALIDATED','manifest_hash':seal(path)}
            save(self.state_path,state)

    def recover(self):
        """Explicitly record interrupted reservations; never automatically redispatch."""
        with (self.directory/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=self._state();recovered=0
            for key,record in state['tasks'].items():
                for entry in record['attempts']:
                    if entry['status']!='RESERVED':continue
                    path=(self.directory/entry['path']).resolve()
                    if not path.is_relative_to(self.directory):raise LegalMathError('E_INTEGRITY')
                    if (path/'manifest.json').exists():
                        outcome=loads((path/'outcome.json').read_bytes());entry.update(status=outcome['status'],manifest_hash=digest(check_manifest(path)))
                    else:
                        save(path/'outcome.json',{'task_id':key,'status':'INTERRUPTED','error':'NO_VALIDATED_COMPLETION',
                            'reservation_refunded':False})
                        entry.update(status='INTERRUPTED',manifest_hash=seal(path))
                    recovered+=1
            save(self.state_path,state);self._results(state);return recovered

    def report(self):
        state=self._state();results=self._results(state)
        pending=[key for key in self.tasks if key not in results]
        return {'plan_hash':self.hash,'status':'COMPLETE_CHECKS' if not pending else 'INCOMPLETE',
            'execution_complete':not pending,'tasks':len(self.tasks),'completed_tasks':len(results),
            'pending_task_ids':pending,'exhausted_task_ids':[k for k in pending
                if len(state['tasks'][k]['attempts'])>=self.plan['maximum_attempts']],
            'attempts':sum(len(r['attempts']) for r in state['tasks'].values()),
            'imported_tasks':sum(r['import'] is not None for r in state['tasks'].values()),
            'legal_accuracy_evaluated':False,'release_eligible':False}

    def aggregate_fidelity(self):
        state=self._state();results=self._results(state)
        if any(t['kind']!='FIDELITY' for t in self.tasks.values()):raise LegalMathError('E_SCHEMA')
        if set(results)!=set(self.tasks):raise LegalMathError('E_JOB_STATE',details='Incomplete fidelity task coverage')
        first=next(iter(self.tasks.values()))['context'];base={k:first[k] for k in ('packet','claims','candidates')}
        for task in self.tasks.values():
            if any(task['context'][k]!=base[k] for k in base):raise LegalMathError('E_INTEGRITY')
        combined={'checks':[],'additional_concerns':[]}
        for result in results.values():
            combined['checks'].extend(result['checks']);combined['additional_concerns'].extend(result['additional_concerns'])
        checked=validate_fidelity_aggregate(combined,base['packet'],base['claims'],base['candidates'])
        if len(canonical(checked))>2*1024*1024:raise LegalMathError('E_RESOURCE_LIMIT')
        save(self.directory/'aggregate.json',checked)
        findings=fidelity_findings(checked);save(self.directory/'findings.json',findings)
        return {'status':'UNRESOLVED' if findings else 'NO_ISSUE_DETECTED_IN_PROFILE','execution_complete':True,
            'pairs':len(checked['checks']),'findings':len(findings),'legal_accuracy_evaluated':False,'release_eligible':False}

    def run(self,provider_factory,ledger_path,settings,*,maximum_actions,deadline_seconds=14400,backoff_seconds=10):
        if type(maximum_actions)is not int or not 0<=maximum_actions<=500 or not 0<=backoff_seconds<=60:
            raise LegalMathError('E_RESOURCE_LIMIT')
        with (self.directory/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=self._state();results=self._results(state)
            began=time.monotonic();actions=0;consecutive_transport=0;stop=None
            for key,task in self.tasks.items():
                if key in results:continue
                record=state['tasks'][key]
                while len(record['attempts'])<self.plan['maximum_attempts']:
                    remaining=int(deadline_seconds-(time.monotonic()-began))
                    if actions>=maximum_actions or remaining<1:stop='SLICE_LIMIT';break
                    prior=self.directory/record['attempts'][-1]['path'] if record['attempts'] else None
                    request=repair_request(task,prior)
                    path=self.directory/'attempts'/key/f'attempt-{len(record["attempts"])+1:03}'
                    path.mkdir(parents=True,exist_ok=False)
                    save(path/'request.json',request);save(path/'schema.json',task['schema'])
                    entry={'path':str(path.relative_to(self.directory)),'status':'RESERVED','manifest_hash':None}
                    record['attempts'].append(entry);save(self.state_path,state);actions+=1
                    outcome={'task_id':key,'status':'FAILED'};transport_error=False
                    try:
                        provider=provider_factory(path)
                        journal=JournalProvider(provider,path/'call',maximum=1,deadline_seconds=min(remaining,settings.timeout_seconds+1))
                        answer=journal.complete(request,task['schema'],settings)
                        response={'value':answer.value,'provenance':answer.provenance};save(path/'response.json',response)
                        save(path/'receipt.json',receipt(request,response,ledger_path,self.plan['route_hash']))
                        result=validate_task(task,answer.value);save(path/'validated.json',result)
                        outcome['status']='VALIDATED';results[key]=result;consecutive_transport=0
                    except Exception as exc:
                        outcome.update(error=getattr(exc,'code',type(exc).__name__),details=getattr(exc,'details',str(exc)))
                        transport_error=transient_service_failure(exc)
                        consecutive_transport=consecutive_transport+1 if transport_error else 0
                        details_text=str(outcome.get('details','')).lower()
                        if outcome['error'] in ('E_INTEGRITY','E_STALE_REVIEW','E_AUTHORITY'):
                            stop='INTEGRITY_OR_AUTHORITY'
                        elif outcome['error']=='E_RESOURCE_LIMIT' and any(marker in details_text for marker in (
                                'allowance', 'increment', 'byte cap',
                                'assurance call/deadline limit')):
                            stop='ALLOWANCE_OR_RESOURCE_EXHAUSTED'
                        elif outcome['error']=='E_DEPENDENCY' and not transport_error:stop='DEPENDENCY'
                    save(path/'outcome.json',outcome);entry.update(status=outcome['status'],manifest_hash=seal(path))
                    save(self.state_path,state)
                    progress={'completed_tasks':len(results),'tasks':len(self.tasks),'slice_actions':actions,
                              'latest_status':outcome['status'],'task_id':key}
                    save(self.directory/'progress.json',progress);print(canonical(progress).decode(),flush=True)
                    if consecutive_transport>=2:stop='PROVIDER_CIRCUIT_OPEN'
                    if stop or outcome['status']=='VALIDATED':break
                    if transport_error and backoff_seconds:time.sleep(backoff_seconds)
                if stop:break
            result=self.report();result.update(slice_actions=actions,stop_reason=stop,
                                               wall_milliseconds=int((time.monotonic()-began)*1000))
            save(self.directory/'report.json',result);return result
