"""Execute the reviewed sixteen-job declared-interface development diagnostic."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic
from datetime import datetime,timezone
from legalmath.canonical import digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.declared_evaluation import MethodRun,score_declared
from legalmath.interpretation.assurance.evaluation import prepare_study,summarize
from legalmath.interpretation.assurance.checkpoints import seal,check_manifest,CheckpointQueue
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.search.providers import Allowance,CodexProvider,verify_allowance_checkpoint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round9'
DOC=ROOT/'docs/implementation/interpretation-round9'
LEDGER=ROOT/'artifacts/interpretation/round7/live-allowance.json'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def recover_job(blind_id):
    """Explicit interrupted-job recovery after the supervisor process is stopped."""
    contract=loads((DOC/'live-contract.json').read_bytes());frozen=loads((DOC/'study.json').read_bytes())
    if digest(frozen)!=contract['study_hash']:raise LegalMathError('E_STALE_REVIEW')
    jobs={j['blind_id']:j for j in frozen['study']['jobs']}
    if blind_id not in jobs:raise LegalMathError('E_REFERENCE')
    supervisor=loads((OUT/'state.json').read_bytes())['phases']['G2']
    if supervisor['status'] not in ('REPAIR_REQUIRED','REPAIRED_PENDING_REVIEW'):
        raise LegalMathError('E_JOB_STATE',details='Stop or recover the supervisor before recovering a job')
    directory=OUT/'jobs'/blind_id
    if (directory/'scored.json').exists():raise LegalMathError('E_IDEMPOTENCY')
    assignment=loads((directory/'assignment.json').read_bytes());job=jobs[blind_id]
    if assignment['job']!=job or assignment['public_hash']!=digest(frozen['public_interfaces'][job['case_id']]):
        raise LegalMathError('E_STALE_REVIEW')
    verify_allowance_checkpoint(LEDGER,digest(assignment['allowance_before']))
    timing_path=directory/'execution-time.json'
    if timing_path.exists():
        timing=loads(timing_path.read_bytes())
        if timing.get('active_since_utc'):
            start=datetime.fromisoformat(timing['active_since_utc'])
            timing['wall_milliseconds']+=max(0,int((datetime.now(timezone.utc)-start).total_seconds()*1000))
            timing.update(active_since_utc=None,hard_termination_time_unavailable=True,
                accounting='Conservative elapsed wall time through recovery; no execution-time refund')
            save(timing_path,timing)
    recovered=0
    for p in sorted((directory/'method/queues').glob('*/plan.json')):
        recovered+=CheckpointQueue(p.parent,loads(p.read_bytes())).recover()
    save(directory/'recovery.json',{'assignment_hash':digest(assignment),'recovered_tasks':recovered,
        'allowance_checkpoint_hash':digest(loads(LEDGER.read_bytes())),'reservation_refunded':False})
    print({'job':blind_id,'recovered_tasks':recovered,'reservation_refunded':False},flush=True)


def run(directory):
    directory=Path(directory).resolve()
    if directory.exists() or not directory.is_relative_to(OUT/'G2'):raise LegalMathError('E_IDEMPOTENCY')
    contract=loads((DOC/'live-contract.json').read_bytes())
    frozen=loads((DOC/'study.json').read_bytes())
    if digest(frozen)!=contract['study_hash']:raise LegalMathError('E_STALE_REVIEW')
    study=frozen['study'];cases={c['case_id']:c for c in study['cases']}
    rebuilt=prepare_study(study['contract'],[{k:v for k,v in c.items() if k!='packet_hash'} for c in study['cases']])
    if rebuilt!=study:raise LegalMathError('E_INTEGRITY')
    verify_allowance_checkpoint(LEDGER,contract['allowance_checkpoint_hash'])
    before=loads(LEDGER.read_bytes());directory.mkdir(parents=True)
    save(directory/'contract.json',contract);save(directory/'allowance-before.json',before)
    rows=[]
    for job in study['jobs']:
        jobdir=OUT/'jobs'/job['blind_id'];rowfile=jobdir/'scored.json'
        if rowfile.exists():
            check_manifest(jobdir);row=loads(rowfile.read_bytes())
            if any(row[k]!=job[k] for k in job):raise LegalMathError('E_STALE_REVIEW')
            rows.append(row);continue
        case=cases[job['case_id']];public=frozen['public_interfaces'][job['case_id']]
        if jobdir.exists():
            if not (jobdir/'recovery.json').exists():raise LegalMathError('E_JOB_STATE',details='Interrupted job needs explicit recovery; never silently redispatch')
            assignment=loads((jobdir/'assignment.json').read_bytes());recovery=loads((jobdir/'recovery.json').read_bytes())
            if (assignment['job']!=job or assignment['public_hash']!=digest(public) or
                    recovery['assignment_hash']!=digest(assignment)):raise LegalMathError('E_STALE_REVIEW')
            verify_allowance_checkpoint(LEDGER,digest(assignment['allowance_before']))
            prior=assignment['allowance_before']
        else:
            jobdir.mkdir(parents=True);prior=loads(LEDGER.read_bytes())
            save(jobdir/'assignment.json',{'job':job,'public_hash':digest(public),'allowance_before':prior})
        first=len(prior['calls'])
        if first+24>contract['reservation_ceiling']:raise LegalMathError('E_RESOURCE_LIMIT')
        provider=CodexProvider(allowance=Allowance(LEDGER,500,reservation_ceiling=first+24))
        if digest(provider.routing)!=contract['route_hash']:raise LegalMathError('E_STALE_REVIEW')
        timing_path=jobdir/'execution-time.json'
        timing=loads(timing_path.read_bytes()) if timing_path.exists() else {'wall_milliseconds':0}
        if timing.get('active_since_utc'):raise LegalMathError('E_JOB_STATE',details='Unrecovered execution time')
        spent=timing['wall_milliseconds']
        remaining_seconds=3600-spent/1000
        save(timing_path,{**timing,'active_since_utc':datetime.now(timezone.utc).isoformat()})
        began=monotonic()
        try:
            if remaining_seconds<30:raise LegalMathError('E_RESOURCE_LIMIT',details='Job execution-time limit exhausted')
            result=MethodRun(jobdir/'method',public,provider,LEDGER,JDK,deadline_seconds=remaining_seconds).execute(job['arm'])
            outcome=score_declared(result,case,public,Comparisons(jobdir/'scoring-java',JDK,public['at']))
        except LegalMathError as exc:
            # Integrity failures invalidate the experiment and cannot become a
            # model-quality row. Service circuits require explicit recovery.
            if exc.code in ('E_INTEGRITY','E_STALE_REVIEW','E_AUTHORITY'):raise
            if isinstance(exc.details,dict) and exc.details.get('stop_reason') in (
                    'PROVIDER_CIRCUIT_OPEN','DEPENDENCY','INTEGRITY_OR_AUTHORITY','ALLOWANCE_OR_RESOURCE_EXHAUSTED'):
                raise
            result={'status':'FAILED','error':exc.code,'details':exc.details}
            outcome={'status':'MISSING','signature':None,'reference_in_candidate_set':False}
            save(jobdir/'failure.json',result)
        finally:
            spent+=int((monotonic()-began)*1000)
            save(timing_path,{**timing,'wall_milliseconds':spent,'active_since_utc':None})
        after=loads(LEDGER.read_bytes());calls=len(after['calls'])-first
        if after['calls'][:first]!=prior['calls'] or not 0<=calls<=24:raise LegalMathError('E_INTEGRITY')
        row={**job,'packet_hash':case['packet_hash'],'budget':24,'calls':calls,
            'wall_seconds':str(spent/1000),'outcome':outcome,'method_result_hash':digest(result)}
        save(rowfile,row);save(jobdir/'allowance-after.json',after);seal(jobdir)
        rows.append(row);save(directory/'progress.json',{'jobs':len(rows),'total':len(study['jobs']),
            'grant_used':len(after['calls']),'latest':job,'outcome':outcome['status']})
        print({'completed_jobs':len(rows),'total':len(study['jobs']),'case':job['case_id'],
               'arm':job['arm'],'calls':calls,'outcome':outcome['status']},flush=True)
    summary=summarize(study,rows,live=True)
    summary['profile']=frozen['profile'];summary['candidate_recovery']={arm:{
        'jobs':sum(r['arm']==arm for r in rows),
        'reference_in_set':sum(r['arm']==arm and r['outcome']['reference_in_candidate_set'] for r in rows),
        'excess_signature_total':sum(r['outcome'].get('excess_reference_signatures',0) for r in rows if r['arm']==arm)}
        for arm in ('single-reader','isolated-readers','search','assurance')}
    after=loads(LEDGER.read_bytes());summary['grant_used']=len(after['calls'])
    summary['new_calls']=len(after['calls'])-len(before['calls'])
    save(directory/'results.json',rows);save(directory/'summary.json',summary)
    save(directory/'allowance-after.json',after)
    save(directory/'job-manifests.json',{j['blind_id']:digest(check_manifest(OUT/'jobs'/j['blind_id'])) for j in study['jobs']})
    seal(directory);print({k:v for k,v in summary.items() if k not in ('comparisons',)},flush=True)


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--out');g.add_argument('--recover-job');args=p.parse_args()
    if args.recover_job:recover_job(args.recover_job)
    else:run(args.out)
