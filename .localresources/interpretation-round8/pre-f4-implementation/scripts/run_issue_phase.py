"""Fixed bounded successor study; public retained evidence and counted calls only."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from time import monotonic
from legalmath.canonical import digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.checkpoints import (
    CheckpointQueue,task_spec,plan_tasks,fidelity_plan,seal,check_manifest,
)
from legalmath.interpretation.assurance.issue_search import (
    hypothesis_request,merge_hypotheses,distinguish,audit_request,
    reconsideration_required,uncertainty_report,
)
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.recovery import invalid_generation_proposals
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Allowance,CodexProvider,verify_allowance_checkpoint
from legalmath.interpretation.search.formal import Comparisons,bundle
from legalmath.java.host_package import prepare_interpretation,run as run_host

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round8'
DOC=ROOT/'docs/implementation/interpretation-round8'
LEDGER=ROOT/'artifacts/interpretation/round7/live-allowance.json'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
AT='2026-09-24T00:00:00.000000Z'


def prior(phase):
    state=loads((OUT/'state.json').read_bytes())['phases'][phase]
    if state['status']!='PASSED':raise LegalMathError('E_JOB_STATE')
    manifest=ROOT/state['attempts'][-1]['path']
    if raw_digest(manifest.read_bytes())!=state['attempts'][-1]['sha256']:raise LegalMathError('E_INTEGRITY')
    directory=manifest.parent/'live';check_manifest(directory)
    return directory


class Study:
    def __init__(self,phase,directory):
        self.phase,self.directory=phase,Path(directory).resolve()
        if self.directory.exists() or not self.directory.is_relative_to(OUT/phase):raise LegalMathError('E_IDEMPOTENCY')
        self.contract=loads((DOC/'contracts'/f'{phase}.json').read_bytes())
        self.baseline=loads((ROOT/'.localresources/interpretation-round8/baseline.json').read_bytes())
        verify_allowance_checkpoint(LEDGER,self.baseline['allowance_checkpoint_hash'])
        self.before=loads(LEDGER.read_bytes());self.used_before=len(self.before['calls'])
        self.provider=CodexProvider(allowance=Allowance(LEDGER,500,reservation_ceiling=self.contract['reservation_ceiling']))
        if digest(self.provider.routing)!=self.contract['route_hash']:raise LegalMathError('E_STALE_REVIEW')
        self.settings=Settings(timeout_seconds=180,max_input_bytes=200000,max_output_bytes=200000)
        self.directory.mkdir(parents=True);self.began=monotonic();self.reports={}
        save(self.directory/'contract.json',self.contract);save(self.directory/'allowance-before.json',self.before)

    def queue(self,name,plan):
        # Shared ceilings persist across supervisor attempts. Requests are frozen
        # before dispatch; a resumed phase reuses successful task records.
        if monotonic()-self.began>self.contract['deadline_seconds']:raise LegalMathError('E_RESOURCE_LIMIT')
        queue=CheckpointQueue(OUT/'workqueues'/self.phase/name,plan)
        def factory(path):return CompactProvider(self.provider,path/'transport')
        report=queue.run(factory,LEDGER,self.settings,maximum_actions=self.contract['maximum_actions'],
            deadline_seconds=max(1,self.contract['deadline_seconds']-(monotonic()-self.began)),backoff_seconds=10)
        self.reports[name]=report;save(self.directory/'queue-reports.json',self.reports)
        if not report['execution_complete']:raise LegalMathError('E_JOB_STATE',details=report)
        return queue,queue._results(queue._state())

    def hypotheses(self,name,issue,packet,roles,prior_value=None):
        tasks=[task_spec('ISSUE_HYPOTHESES',hypothesis_request(issue,packet,role,prior=prior_value),
            {'issue':issue,'packet':packet,'at':AT}) for role in roles]
        plan=plan_tasks(tasks,self.contract['route_hash']);_,values=self.queue(name,plan)
        return {role:values[task['task_id']] for role,task in zip(roles,tasks)}

    def audit(self,name,issue,packet,candidates,distinctions,roles):
        tasks=[task_spec('ISSUE_AUDIT',audit_request(issue,packet,candidates,distinctions,role),
            {'packet':packet,'candidates':candidates}) for role in roles]
        _,values=self.queue(name,plan_tasks(tasks,self.contract['route_hash']))
        return {role:values[task['task_id']] for role,task in zip(roles,tasks)}

    def compare(self,name,issue,packet,merged):
        return distinguish(issue,packet,merged['candidates'],Comparisons(self.directory/name,JDK,AT))

    def finish(self,summary):
        after=loads(LEDGER.read_bytes())
        if after['calls'][:self.used_before]!=self.before['calls']:raise LegalMathError('E_INTEGRITY')
        used=len(after['calls'])-self.used_before
        if not 0<=used<=self.contract['maximum_actions']:raise LegalMathError('E_INTEGRITY')
        summary.update(phase=self.phase,new_calls=used,grant_used=len(after['calls']),grant_remaining=500-len(after['calls']),
            wall_milliseconds=int((monotonic()-self.began)*1000),legal_accuracy_evaluated=False,release_eligible=False)
        save(self.directory/'summary.json',summary);save(self.directory/'allowance-after.json',after)
        save(self.directory/'queue-snapshot.json',{'files':{
            str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in sorted((OUT/'workqueues'/self.phase).rglob('*'))
            if p.is_file() and p.name!='.lock'}})
        seal(self.directory);print(summary,flush=True)


def run(phase,directory):
    study=Study(phase,directory)
    source=loads((DOC/'source.json').read_bytes());packet=source['packet']
    trigger=loads((DOC/'trigger-issue.json').read_bytes())
    issue=loads((DOC/'qualification-issue.json').read_bytes())
    if phase=='F1':
        responses=study.hypotheses('trigger-readers',trigger,packet,('syntax-reader','context-reader'))
        merged=merge_hypotheses(responses,trigger,packet,AT)
        save(study.directory/'responses.json',responses);save(study.directory/'merged.json',merged)
        distinctions=study.compare('java',trigger,packet,merged)
        claims=source['trigger_claims']
        queue,_=study.queue('trigger-fidelity',fidelity_plan(packet,claims,merged['candidates'],study.contract['route_hash']))
        fidelity=queue.aggregate_fidelity()
        for name in ('aggregate.json','findings.json'):save(study.directory/name,loads((queue.directory/name).read_bytes()))
        study.finish({'status':'CHECKS_COMPLETED','candidates':len(merged['candidates']),
            'behavior_groups':len(distinctions['behavior_groups']),'java_cases':distinctions['java_cases'],'fidelity':fidelity})
    elif phase=='F2':
        responses=study.hypotheses('blind-readers',issue,packet,('syntax-reader','context-reader'))
        initial=merge_hypotheses(responses,issue,packet,AT)
        save(study.directory/'blind-responses.json',responses);save(study.directory/'blind-merged.json',initial)
        responses.update(study.hypotheses('missing-reader',issue,packet,('missing-reading-challenger',),initial))
        merged=merge_hypotheses(responses,issue,packet,AT)
        save(study.directory/'responses.json',responses);save(study.directory/'merged.json',merged)
        distinctions=study.compare('java',issue,packet,merged)
        study.finish({'status':'CHECKS_COMPLETED','candidates':len(merged['candidates']),
            'behavior_groups':len(distinctions['behavior_groups']),'java_cases':distinctions['java_cases'],
            'deferred':len(merged['deferred']),'generation_concerns':len(merged['concerns'])})
    elif phase=='F3':
        previous=prior('F2');responses=loads((previous/'responses.json').read_bytes())
        merged=loads((previous/'merged.json').read_bytes())
        distinctions=loads((previous/'java/issue-distinction-report.json').read_bytes())
        recovery=invalid_generation_proposals(OUT/'workqueues/F2',issue,packet)
        save(study.directory/'invalid-proposal-history.json',recovery)
        if recovery['records']:
            # A schema repair can change substantive formulas. Ask a fresh
            # reader to recover omitted possibilities; never rewrite raw scope.
            feedback={'validated_proposals':merged['candidates'],'unvalidated_proposals':recovery['records'],
                'instruction':'Review every retained invalid proposal for lost semantic alternatives. Propose missing source-supported readings, or explain remaining uncertainty. Do not treat invalid prose scope as executable or discard a proposal merely because formatting failed.'}
            rescued=study.hypotheses('repair-history-reconsideration',issue,packet,('discrepancy-reviser',),feedback)
            responses.update({'repair-history-reviser':next(iter(rescued.values()))})
            merged=merge_hypotheses(responses,issue,packet,AT)
            distinctions=study.compare('recovered-java',issue,packet,merged)
            save(study.directory/'recovered-merged.json',merged)
        reviews=study.audit('english-critics',issue,packet,merged['candidates'],distinctions,
                            ('syntax-source-critic','context-source-critic'))
        save(study.directory/'english-reviews.json',reviews)
        # Added evidence is visible only after both English readers and critics.
        bilingual=loads((DOC/'parallel-source.json').read_bytes())['packet']
        revised_issue=deepcopy(issue);revised_issue['source_packet_hash']=digest(bilingual)
        parallel_distinctions=study.compare('parallel-java',revised_issue,bilingual,merged)
        parallel=study.audit('parallel-critic',revised_issue,bilingual,merged['candidates'],parallel_distinctions,
            ('parallel-language-critic-no-assumed-precedence',))
        reviews.update(parallel);history=[{'cycle':0,'reviews':deepcopy(reviews),'candidates_hash':digest(merged['candidates'])}]
        cycles=0
        while reconsideration_required(reviews,merged) and cycles<2:
            cycles+=1
            feedback={'prior_readings':merged['candidates'],'criticisms':reviews,
                'generation_concerns':merged['concerns'],'deferred_hypotheses':merged['deferred'],
                'earlier_review_rounds_retained':len(history),
                'instruction':'Retain prior proposals; propose source-supported additions or explain why concerns remain unresolved.'}
            new=study.hypotheses(f'reconsider-{cycles}',revised_issue,bilingual,('discrepancy-reviser',),feedback)
            responses.update({f'discrepancy-reviser-{cycles}':v for v in new.values()})
            merged=merge_hypotheses(responses,revised_issue,bilingual,AT)
            distinctions=study.compare(f'reconsider-java-{cycles}',revised_issue,bilingual,merged)
            reviews=study.audit(f'reconsider-audit-{cycles}',revised_issue,bilingual,merged['candidates'],distinctions,
                (f'reconsideration-source-critic-{cycles}',))
            history.append({'cycle':cycles,'reviews':deepcopy(reviews),'candidates_hash':digest(merged['candidates'])})
            save(study.directory/f'cycle-{cycles}.json',{'responses':responses,'merged':merged,'reviews':reviews})
        report=uncertainty_report(merged,reviews,cycles,2);report['review_history']=history
        report['invalid_proposal_history']=recovery
        save(study.directory/'uncertainty.json',report);save(study.directory/'merged.json',merged)
        save(study.directory/'source-packet.json',bilingual);save(study.directory/'issue.json',revised_issue)
        save(study.directory/'distinctions.json',distinctions if cycles else parallel_distinctions)
        study.finish({'status':'CHECKS_COMPLETED','interpretation_status':report['status'],
            'cycles':cycles,'candidates':len(merged['candidates']),'deferred':len(merged['deferred'])})
    elif phase=='F4':
        previous=prior('F1');merged=loads((previous/'merged.json').read_bytes())
        distinctions=loads((previous/'java/issue-distinction-report.json').read_bytes())
        uncertainty=loads((prior('F3')/'uncertainty.json').read_bytes())
        # Package every candidate; no implicit winner selected by order or votes.
        packages={}
        raw=ROOT/source['english_raw_path'];raw_bytes=raw.read_bytes()
        if raw_digest(raw_bytes)!=source['english_raw_hash']:raise LegalMathError('E_INTEGRITY')
        for cid,reading in merged['candidates'].items():
            compiled=bundle(reading,packet,AT)
            cases=[{'id':'trigger.'+str(i),'bundle':compiled,'snapshot':s,'rule_id':'selected.control',
                'valid_at':AT,'known_at':AT,'expected':distinctions['outputs'][cid][i]['python']}
                for i,s in enumerate(distinctions['scenarios'])]
            destination=study.directory/'packages'/cid
            metadata=prepare_interpretation(reading,packet,cases,{source['english_url']:raw_bytes},destination,JDK,AT)
            value=run_host(destination,cases[0]['snapshot'],'selected.control',AT,JDK)
            packages[cid]={'metadata':metadata,'host_sample':value}
        save(study.directory/'packages.json',packages);save(study.directory/'uncertainty.json',uncertainty)
        study.finish({'status':'DRAFT_PACKAGES_CHECKED','packages':len(packages),
            'interpretation_status':uncertainty['status'],'bank_integration_accepted':False})
    else:raise ValueError('Unreviewed live phase')


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--phase',required=True,choices=('F1','F2','F3','F4'))
    parser.add_argument('--out',required=True);args=parser.parse_args();run(args.phase,args.out)
