"""Conservative whole-route admission and durable, finite dispatch accounting."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path

from ...canonical import digest, loads
from ...errors import LegalMathError
from .monitor import save
from .failure_policy import SettledProviderFailure

STAGES = ('core', 'question_assignment', 'scoped', 'dossier_reviews', 'interaction', 'synthesis')
CORE_TASKS = {'SOURCE_INVENTORY', 'INVENTORY_CROSS_CHECK', 'REVIEW_SOURCE_CLAIMS',
              'REVIEW_SOURCE_INTERACTIONS', 'REVIEW_SOURCE_OMISSIONS', 'ABSTRACTION_PROPOSALS',
              'GENERATE', 'REFINE', 'SOURCE_FIDELITY', 'STRUCTURED_CRITICISM', 'SEMANTIC_REPAIR',
              'RECONSTRUCT', 'DERIVED_MAPPING', 'REPAIR_SOURCE_INVENTORY',
              'PROPOSE_DERIVED_MAPPING', 'REGISTERED_EXAMPLE_QUERIES'}
TASK_STAGES = {'DEFINE_EXACT_QUESTIONS':'question_assignment', 'SCOPED_SOURCE_FIDELITY':'scoped',
               'REVIEW_DOSSIER_EVIDENCE':'dossier_reviews', 'REVIEW_DOSSIER_INTERACTIONS':'interaction',
               'SYNTHESIZE_WHOLE_DOSSIER_ANSWER':'synthesis', 'REVIEW_GROUNDED_PRODUCT_ANSWER':'answer_review',
               **dict.fromkeys(CORE_TASKS, 'core')}


def find_budget(provider):
    seen=set()
    while provider is not None and id(provider) not in seen:
        seen.add(id(provider))
        if type(provider) is RouteBudgetProvider:return provider
        provider=getattr(provider,'provider',None)
    return None


def require(ok, details, code='E_RESOURCE_LIMIT'):
    if not ok:raise LegalMathError(code, details=details)


def ceildiv(n, d):
    require(type(n) is int and n >= 0 and type(d) is int and d > 0, 'Invalid workload count')
    return (n+d-1)//d


def workload(*, pieces, reader_claims, selected_claims, all_claims, candidates,
             formalized_candidates, source_batch=20, core_batch=32, scoped_batch=12,
             context_passes=1, interaction_batches=0, search_calls=6, abstraction_calls=3,
             semantic_rounds=0, other_core_calls=0, output_repairs=0, scoped_rounds=1,
             question_calls=3, dossier_groups=64, tool_enabled=False,
             derived_mapping_calls=0, example_query_calls=0, original_question_count=0,
             machine_qualification=False, supplied_questions=False, semantic_stage=False, answer_review_calls=0):
    """Counts are declared bounds or actual observations, never evidence of coverage.

    Candidate count must include deferred and repair-generated readings. Caller
    retains provenance for each count; insufficient capacity never drops rows.
    """
    counts = [pieces, *reader_claims, selected_claims, all_claims, candidates, formalized_candidates,
              context_passes, interaction_batches, search_calls, abstraction_calls, semantic_rounds,
              other_core_calls, output_repairs, scoped_rounds, question_calls, dossier_groups,
              derived_mapping_calls, example_query_calls, original_question_count, answer_review_calls]
    require(len(reader_claims) == 2 and all(type(n) is int and n >= 0 for n in counts)
        and pieces >= 1 and context_passes >= 1 and scoped_rounds >= 1
        and 0 <= selected_claims <= all_claims <= sum(reader_claims)
        and 0 <= formalized_candidates <= candidates and original_question_count <= 4,
        'Inconsistent workload population')
    require(all(type(flag) is bool for flag in (machine_qualification, supplied_questions, semantic_stage)),
            'Invalid product configuration')
    scoped_pairs, core_pairs = all_claims*candidates, selected_claims*candidates
    source_reads = 2*pieces
    source_reviews = sum(ceildiv(n, source_batch) for n in reader_claims)+2+interaction_batches
    inventory = context_passes*(source_reads+source_reviews)
    fidelity = ceildiv(selected_claims*formalized_candidates, core_batch)
    # A semantic repair can introduce source/candidate changes requiring the
    # entire inventory/fidelity again. Do not silently assume cache hits.
    core = ((inventory+abstraction_calls+fidelity+1)*(semantic_rounds+1)
            + search_calls + semantic_rounds + other_core_calls + derived_mapping_calls
            + example_query_calls)*(output_repairs+1)
    stages = {'core':core, 'question_assignment':question_calls,
        'scoped':2*ceildiv(scoped_pairs,scoped_batch)*scoped_rounds,
        'dossier_reviews':dossier_groups, 'interaction':1, 'synthesis':1}
    if answer_review_calls:
        stages['answer_review'] = answer_review_calls
    # Includes prepared requests and checks; final consumer currently does not
    # re-augment. Distinct typed targets can require candidate_count retrievals.
    tool_actions = (sum(stages[s] for s in ('core','question_assignment','scoped'))
        + (pieces*context_passes+1)*max(1,original_question_count)
        + candidates + 2*(semantic_rounds+1)) if tool_enabled else 0
    return {'stages':stages, 'total_calls':sum(stages.values()), 'core_pairs':core_pairs,
        'scoped_pairs':scoped_pairs, 'optional_tool_actions':tool_actions,
        'source_reads':source_reads, 'source_review_calls':source_reviews,
        'deterministic_unformalized_pairs':selected_claims*(candidates-formalized_candidates),
        'claim_population':all_claims, 'candidate_population':candidates,
        'explicit_constructor_reserves':{'PROPOSE_DERIVED_MAPPING':derived_mapping_calls*(output_repairs+1),
            'REGISTERED_EXAMPLE_QUERIES':example_query_calls*(output_repairs+1),
            'REPAIR_SOURCE_INVENTORY':2*semantic_rounds*(output_repairs+1)},
        'original_question_count':original_question_count,
        'runtime': {'replay_candidates': candidates, 'dossier_groups': dossier_groups,
            'outer_actions': (1 if supplied_questions else 4) + candidates *
                             (2 if machine_qualification else 1) + 1 + int(semantic_stage),
            'machine_qualification': machine_qualification,
            'supplied_questions': supplied_questions, 'semantic_stage': semantic_stage},
        'scope':'Conservative declared workload; output adequacy and legal quality unqualified.'}


def admission(required, remaining, *, deadline_utc, now=None, tool_remaining=200):
    require(set(remaining) == set(required['stages']) and set(remaining) in
            (set(STAGES), set(STAGES) | {'answer_review'})
            and all(type(n) is int and n >= 0 for n in remaining.values()), 'Invalid remaining allocation')
    current = now or datetime.now(timezone.utc)
    failures = [{'boundary':s, 'required':n, 'remaining':remaining[s]} for s,n in required['stages'].items() if n > remaining[s]]
    for name in ('core_pairs','scoped_pairs'):
        if required[name] > 4096:failures.append({'boundary':name, 'required':required[name], 'remaining':4096})
    if required['optional_tool_actions'] > tool_remaining:
        failures.append({'boundary':'optional_tool_actions','required':required['optional_tool_actions'],'remaining':tool_remaining})
    runtime = required.get('runtime')
    if runtime is None:
        failures.append({'boundary': 'runtime_configuration', 'reason': 'Unqualified runtime bounds'})
    else:
        flags = ('machine_qualification', 'supplied_questions', 'semantic_stage')
        if not all(type(runtime.get(k)) is bool for k in flags):
            failures.append({'boundary': 'runtime_configuration', 'reason': 'Missing or invalid configuration flags'})
        else:
            expected_actions = ((1 if runtime['supplied_questions'] else 4)
                + required['candidate_population'] * (2 if runtime['machine_qualification'] else 1)
                + 1 + int(runtime['semantic_stage']))
            if (runtime.get('outer_actions') != expected_actions
                    or runtime.get('replay_candidates') != required['candidate_population']):
                failures.append({'boundary': 'runtime_configuration', 'reason': 'Declared bounds disagree with configuration'})
        for name, cap in (('replay_candidates', 16), ('outer_actions', 32), ('dossier_groups', 64)):
            count = runtime.get(name)
            if type(count) is not int or not 1 <= count <= cap:
                failures.append({'boundary': name, 'required': count, 'remaining': cap})
    if current >= datetime.fromisoformat(deadline_utc):failures.append({'boundary':'absolute_deadline','deadline':deadline_utc})
    return {'admitted':not failures, 'required':deepcopy(required), 'remaining':deepcopy(remaining),
        'failures':failures, 'deadline_utc':deadline_utc, 'live_method_qualified':False}


class RouteBudgetProvider:
    """Guard shared by investigation and final consumer; underlying grant still applies.

    It cannot increase a grant or alter its stage assignment. An unknown task or
    interrupted reservation stops. The caller must supply the reviewed complete
    workload; bounds are not inferred from already executed calls.
    """
    def __init__(self, provider, directory, required, remaining, deadline_utc, *, continue_settled_failures=False):
        self.provider=provider; self.directory=Path(directory)
        self.live=provider.live; self.provider_id=provider.provider_id+'.whole-route.v1'
        self.allowance=getattr(provider,'allowance',None)
        self.plan={'required':deepcopy(required),'remaining':deepcopy(remaining),'deadline_utc':deadline_utc}
        require(type(continue_settled_failures) is bool, 'Invalid continuation policy')
        if continue_settled_failures:
            self.plan['continue_settled_failures'] = True
        self.routing={'provider':getattr(provider,'routing',provider.provider_id),'plan_hash':digest(self.plan)}
        self._authority_provider=provider
        self._authority_route=digest(getattr(provider,'routing',provider.provider_id))
        self._route_plan_hash=digest(self.plan)
        self._qualified_routing=deepcopy(self.routing)
        self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/'budget.json'
        with (self.directory/'budget.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.path.exists():require(loads(self.path.read_bytes())['plan']==self.plan, 'Route budget changed', 'E_STALE_REVIEW')
            else:save(self.path, {'plan':self.plan,'calls':[],'transitions':[]})

    def check(self):
        # This candidate has local evidence only. A future live successor must
        # bind its reviewed method and qualification; a caller boolean is not authority.
        require(self.live is False, 'Whole-route candidate has no reviewed live qualification', 'E_AUTHORITY')
        require(digest(self.plan)==self._route_plan_hash and self.routing==self._qualified_routing
                and self.provider is self._authority_provider
                and self._authority_route==digest(getattr(self.provider,'routing',self.provider.provider_id)),
                'Route provider or plan changed', 'E_STALE_REVIEW')
        state=loads(self.path.read_bytes())
        require(state['plan']==self.plan, 'Persisted route plan changed', 'E_INTEGRITY')
        require(all(c['status']=='RETURNED' or
                    (self.plan.get('continue_settled_failures') and c['status']=='SETTLED_FAILED'
                     and c.get('settlement') == 'provider_confirmed_no_result')
                    for c in state['calls']), 'Unresolved or failed route dispatch', 'E_JOB_STATE')
        require(all(t['admission']['admitted'] for t in state['transitions']),
                'Prior whole-route transition refused admission', 'E_JOB_STATE')
        checked=admission(self.plan['required'],self.plan['remaining'],deadline_utc=self.plan['deadline_utc'])
        require(checked['admitted'], checked)
        return state

    def transition(self, label, required_remaining):
        """Re-evaluate actual counts before a downstream stage, preserving history."""
        with (self.directory/'budget.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=self.check()
            used=Counter(c['stage'] for c in state['calls'])
            left={s:n-used[s] for s,n in self.plan['remaining'].items()}
            checked=admission(required_remaining,left,deadline_utc=self.plan['deadline_utc'])
            state['transitions'].append({'label':label,'after_calls':len(state['calls']),'admission':checked})
            save(self.path,state)
            require(checked['admitted'],checked)
            return checked

    def observe(self, *, claims=None, candidates=None):
        self.check()
        for label, actual in (('claim_population',claims),('candidate_population',candidates)):
            if actual is not None:
                require(type(actual) is int and 0 <= actual <= self.plan['required'][label],
                    {'boundary':label,'observed':actual,'declared_bound':self.plan['required'][label],
                     'decision':'Stop before dependent dispatch; retain all records.'})

    def configure(self, *, machine_qualification, supplied_questions, semantic_stage):
        """Reject a differently configured runtime before the first dispatch."""
        self.check()
        actual = {'machine_qualification': machine_qualification,
                  'supplied_questions': supplied_questions, 'semantic_stage': semantic_stage}
        require(all(self.plan['required']['runtime'][k] == v for k, v in actual.items()),
                {'boundary': 'runtime_configuration', 'actual': actual,
                 'declared': self.plan['required']['runtime']}, 'E_STALE_REVIEW')

    def complete(self,request,schema,settings):
        with (self.directory/'budget.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=self.check()
            task=request.get('original_task',request.get('task'))
            require(task in TASK_STAGES, {'unbudgeted_constructor':task}, 'E_AUTHORITY')
            stage=TASK_STAGES[task]
            require(stage in self.plan['remaining'], {'unreserved_stage':stage}, 'E_AUTHORITY')
            require(not any(c['status']=='SETTLED_FAILED' and c['request_hash']==digest(request)
                            for c in state['calls']), 'Settled failure cannot be silently redispatched', 'E_JOB_STATE')
            if task in {'REPAIR_SOURCE_INVENTORY','PROPOSE_DERIVED_MAPPING','REGISTERED_EXAMPLE_QUERIES'}:
                reserved=self.plan['required'].get('explicit_constructor_reserves',{}).get(task,0)
                require(type(reserved) is int and reserved > sum(c['task']==task for c in state['calls']),
                    {'unreserved_constructor':task,'reserved':reserved})
            used=Counter(c['stage'] for c in state['calls'])
            require(used[stage] < min(self.plan['remaining'][stage],self.plan['required']['stages'][stage]), 'Declared stage workload exhausted')
            row={'task':task,'stage':stage,'request_hash':digest(request),'schema_hash':digest(schema),'status':'DISPATCHED'}
            state['calls'].append(row);save(self.path,state)
            try:
                seconds=int((datetime.fromisoformat(self.plan['deadline_utc'])-datetime.now(timezone.utc)).total_seconds())
                require(seconds>=1,'Absolute route deadline exhausted')
                answer=self.provider.complete(request,schema,settings.model_copy(update={'timeout_seconds':min(seconds,settings.timeout_seconds)}))
                row.update(status='RETURNED',response_hash=digest(answer.value));save(self.path,state)
                return answer
            except Exception as exc:
                row.update(status='FAILED',error=getattr(exc,'code',type(exc).__name__));save(self.path,state)
                if isinstance(exc, SettledProviderFailure) and self.plan.get('continue_settled_failures'):
                    row.update(status='SETTLED_FAILED', settlement='provider_confirmed_no_result')
                    save(self.path, state)
                raise
