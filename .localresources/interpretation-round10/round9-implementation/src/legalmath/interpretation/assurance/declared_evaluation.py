"""Development comparison conditional on a public, declared predicate interface.

Expected programs and snapshots stay outside generation. Paraphrases are allowed;
source, factual meanings and the declared question must match exactly.
"""
from copy import deepcopy
from pathlib import Path
from time import monotonic
from ...canonical import digest,loads,canonical,raw_digest
from ...errors import LegalMathError
from ...ir.evaluate import evaluate
from ...java.manifest import run_java
from ..search.formal import Comparisons,bundle,project
from ..search.models import Settings
from .checkpoints import CheckpointQueue,task_spec,plan_tasks,seal
from .issue_search import (validate_issue,validate_hypotheses,hypothesis_request,
    merge_hypotheses,distinguish,audit_request,reconsideration_required)
from .monitor import save
from .transport import CompactProvider
from .evaluation import source_packet,prepare_study,reference_signatures

ARMS=('single-reader','isolated-readers','search','assurance')
PROFILE='declared-predicate-methods.v1'


def validate_public(public):
    if set(public)!={'packet','issue','at'}:raise LegalMathError('E_AUTHORITY',details='Only declared public inputs may reach a method')
    validate_issue(public['issue'],public['packet'])
    return public


def declared_reference_case(case):
    """Version a reference's question/type declaration without changing its function."""
    original_case_hash=digest(case)
    case=deepcopy(case);case.pop('packet_hash',None)
    packet=source_packet(case);ref=case['reference'];original=deepcopy(ref['binding_reading'])
    question=case['selected_slice']
    issue={'issue_id':'study.'+case['case_id'],'source_packet_hash':digest(packet),'question':question,
        'target':deepcopy(ref['evidence']),'facts':deepcopy(original['formalization']['facts']),
        'abstraction_assumptions':['The declared input vocabulary is supplied for this controlled comparison; its adequacy as a legal abstraction remains unverified.'],
        'retained_qualifications':['This predicate concerns the selected applicability condition, not whole-law compliance or licence possession.',
            'Case-dependent input classifications and incorporated authority remain external to the encoded predicate.']}
    for reading in [ref['binding_reading'],*ref.get('alternate_readings',[])]:
        reading['subject']=question
        reading['statement']='[TRUE_IS_SATISFIED] True means the selected applicability predicate is satisfied under the supplied classifications.'
        reading['assumptions']+=issue['abstraction_assumptions']+issue['retained_qualifications']
        validate_hypotheses({'readings':[reading],'vocabulary_concerns':[],'questions':[]},issue,packet,case['at'])
    reference_signatures(case,packet)
    provenance={'original_reading':original,'original_case_hash':original_case_hash,
        'change':'Question and predicate meaning declarations only; facts, scope, result, snapshots and accepted signatures preserved',
        'legal_reference_independently_verified':False}
    return case,{'packet':packet,'issue':issue,'at':case['at']},provenance


class MethodRun:
    def __init__(self,directory,public,provider,ledger,jdk,*,call_cap=24,deadline_seconds=3600):
        validate_public(public)
        if call_cap!=24 or not 30<=deadline_seconds<=3600:raise LegalMathError('E_RESOURCE_LIMIT')
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.public=public;self.provider=provider;self.ledger=Path(ledger);self.jdk=Path(jdk)
        self.cap=call_cap;self.deadline=monotonic()+deadline_seconds
        self.settings=Settings(timeout_seconds=180,max_input_bytes=200000,max_output_bytes=200000)
        self.route=digest(provider.routing)
        self.binding={'profile':PROFILE,'public_hash':digest(public),'route_hash':self.route,'cap':call_cap}
        path=self.directory/'binding.json'
        if path.exists() and loads(path.read_bytes())!=self.binding:raise LegalMathError('E_STALE_REVIEW')
        save(path,self.binding)

    def counted(self):
        return sum(len(r['attempts']) for p in (self.directory/'queues').glob('*/state.json')
                   for r in loads(p.read_bytes())['tasks'].values())

    def step(self,name,tasks):
        queue=CheckpointQueue(self.directory/'queues'/name,plan_tasks(tasks,self.route))
        remaining=self.cap-self.counted()
        if remaining<0:raise LegalMathError('E_INTEGRITY')
        if queue.report()['execution_complete']:return queue._results(queue._state())
        seconds=self.deadline-monotonic()
        if not remaining or seconds<=0:raise LegalMathError('E_RESOURCE_LIMIT')
        report=queue.run(lambda path:CompactProvider(self.provider,path/'transport'),self.ledger,self.settings,
            maximum_actions=remaining,deadline_seconds=seconds,backoff_seconds=10)
        if not report['execution_complete']:raise LegalMathError('E_JOB_STATE',details=report)
        return queue._results(queue._state())

    def generate(self,name,roles,prior=None):
        packet,issue,at=(self.public[k] for k in ('packet','issue','at'))
        tasks=[]
        for role in roles:
            request=hypothesis_request(issue,packet,role,prior=prior)
            request['instructions']+=' Return at most two readings in this bounded comparison; retain any further alternatives or vocabulary limitations explicitly in questions.'
            request['response_schema']['properties']['readings']['maxItems']=2
            tasks.append(task_spec('ISSUE_HYPOTHESES',request,
                {'packet':packet,'issue':issue,'at':at,'maximum_readings':2}))
        values=self.step(name,tasks)
        return {role:values[task['task_id']] for role,task in zip(roles,tasks)}

    def audit(self,name,merged,distinctions):
        packet,issue=(self.public[k] for k in ('packet','issue'))
        candidates=merged['candidates'];ids=list(candidates);tasks=[]
        for start in range(0,len(ids),4):
            required=ids[start:start+4]
            request=audit_request(issue,packet,candidates,distinctions,'source-critic')
            request['required_candidate_ids']=required
            request['instructions']+=' Return judgments for exactly required_candidate_ids; the other proposals remain context. Keep all substantive concerns.'
            tasks.append(task_spec('ISSUE_AUDIT',request,
                {'packet':packet,'candidates':{cid:candidates[cid] for cid in required}}))
        results=self.step(name,tasks)
        return {'source-critic-part-'+str(i):results[t['task_id']] for i,t in enumerate(tasks)}

    def execute(self,arm):
        if arm not in ARMS:raise LegalMathError('E_SCHEMA')
        packet,issue,at=(self.public[k] for k in ('packet','issue','at'))
        roles=('syntax-reader',) if arm=='single-reader' else ('syntax-reader','context-reader')
        responses=self.generate('initial',roles)
        merged=merge_hypotheses(responses,issue,packet,at)
        if arm in ('search','assurance'):
            responses.update(self.generate('challenge',('missing-reading-challenger',),merged))
            merged=merge_hypotheses(responses,issue,packet,at)
        distinctions=distinguish(issue,packet,merged['candidates'],Comparisons(self.directory/'java-initial',self.jdk,at))
        reviews={};history=[];cycles=0
        if arm=='assurance':
            reviews=self.audit('criticism',merged,distinctions);history.append(deepcopy(reviews))
            if reconsideration_required(reviews,merged):
                responses.update({'reconsideration':next(iter(self.generate('reconsideration',('discrepancy-reviser',),
                    {'proposals':merged,'criticisms':reviews}).values()))})
                merged=merge_hypotheses(responses,issue,packet,at)
                distinctions=distinguish(issue,packet,merged['candidates'],Comparisons(self.directory/'java-reconsidered',self.jdk,at))
                reviews=self.audit('reconsidered-criticism',merged,distinctions);history.append(deepcopy(reviews));cycles=1
        # No arm silently discards rejected proposals, even without an extra
        # recovery call. Such a proposal vetoes acceptance and remains evidence.
        from .recovery import invalid_generation_proposals
        invalid=invalid_generation_proposals(self.directory/'queues',issue,packet)
        result={'status':'COMPLETE','arm':arm,'profile':PROFILE,'source_packet_hash':digest(packet),
            'public_hash':digest(self.public),'merged':merged,'reviews':reviews,'review_history':history,
            'invalid_proposals':invalid,'cycles':cycles,'task_attempts':self.counted(),
            'java_cases':distinctions['java_cases'],'behavior_groups':len(distinctions['behavior_groups']),
            'release_eligible':False,'legal_accuracy_evaluated':False}
        save(self.directory/'result.json',result);seal(self.directory)
        return result


def score_declared(result,case,public,checker):
    """Score proposed behavior relative to an authored reference, not English truth."""
    validate_public(public)
    if result['status']!='COMPLETE':return {'status':'MISSING','signature':None,'reference_in_candidate_set':False}
    if (result['public_hash']!=digest(public) or result['source_packet_hash']!=digest(public['packet']) or
            digest(source_packet(case))!=digest(public['packet'])):raise LegalMathError('E_STALE_REVIEW')
    reference_signatures(case,public['packet']);reference=case['reference']
    if (reference['binding_reading']['formalization']['facts']!=public['issue']['facts'] or
            public['issue']['question']!=case['selected_slice']):raise LegalMathError('E_REFERENCE')
    signatures={};members={};unencoded=[]
    for cid,reading in result['merged']['candidates'].items():
        validate_hypotheses({'readings':[reading],'vocabulary_concerns':[],'questions':[]},public['issue'],public['packet'],public['at'])
        if reading['formalization'] is None:unencoded.append(cid);continue
        compiled=bundle(reading,public['packet'],public['at']);build=checker.build(compiled)
        cases=[{'bundle':compiled,'snapshot':s,'rule_id':'selected.control','valid_at':public['at'],'known_at':public['at']}
               for s in reference['snapshots']]
        outcomes=run_java(build['jar'],cases,checker.jdk,build['class_name'])
        if len(outcomes)!=len(cases):raise LegalMathError('E_INTEGRITY')
        signature=[]
        for snapshot,actual in zip(reference['snapshots'],outcomes):
            expected=evaluate(compiled,snapshot,'selected.control',public['at'],public['at'])
            if project(actual)!=project(expected):raise LegalMathError('E_INTEGRITY')
            signature.append(project(actual))
        key=digest(signature);signatures[key]=signature;members.setdefault(key,[]).append(cid)
    accepted={digest(s) for s in reference['accepted']}
    concerns=bool(unencoded or result['merged']['concerns'] or result['merged']['deferred'] or result['invalid_proposals']['records'])
    if result['reviews']:concerns=concerns or reconsideration_required(result['reviews'],result['merged'])
    unambiguous=len(signatures)==1 and not concerns
    return {'status':'ACCEPTED' if unambiguous else 'ABSTAIN',
        'reference_limitations':reference['limitations'],
        'public_abstraction_assumptions':public['issue']['abstraction_assumptions'],
        'signature':next(iter(signatures.values())) if unambiguous else None,
        'reference_in_candidate_set':bool(accepted & set(signatures)),
        'distinct_signatures':len(signatures),'excess_reference_signatures':len(set(signatures)-accepted),
        'candidate_signatures':signatures,'signature_members':members,'unencoded_candidates':unencoded,'uncertainty_retained':concerns,
        'meaning':'Conditional agreement with finite authored reference scenarios, not legal correctness',
        'release_eligible':False}
