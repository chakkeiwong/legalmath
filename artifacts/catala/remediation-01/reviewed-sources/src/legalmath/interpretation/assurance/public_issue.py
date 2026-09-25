"""Reusable, resumable entry point for a declared-source interpretation question."""
from pathlib import Path
from datetime import datetime,timezone
from time import monotonic
import fcntl
from ...canonical import loads,digest,raw_digest
from ...errors import LegalMathError
from ...java.manifest import toolchain
from ..search.providers import Allowance,CodexProvider,verify_allowance_checkpoint
from ..outputs import descriptor
from .declared_evaluation import MethodRun,validate_public,ARMS
from .checkpoints import CheckpointQueue,seal,check_manifest
from .monitor import save


def implementation_hash():
    root=Path(__file__).resolve().parents[2]
    sources=(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts
             and p.suffix in ('.py','.java','.json','.sql'))
    return digest({str(p.relative_to(root)):raw_digest(p.read_bytes()) for p in sorted(sources)})


def run_public_issue(public,out,ledger,jdk,*,arm='assurance',deadline_seconds=3600,
                     resume=False,recover=False,provider=None):
    validate_public(public)
    if arm not in ARMS or type(deadline_seconds)is not int or not 30<=deadline_seconds<=3600:
        raise LegalMathError('E_SCHEMA')
    out=Path(out).resolve();ledger=Path(ledger).resolve();jdk=Path(jdk).resolve()
    jdk,jdk_version=toolchain(jdk)
    if not ledger.is_file():raise LegalMathError('E_AUTHORITY',details='An existing authorized allowance is required')
    grant=loads(ledger.read_bytes())
    if type(grant.get('maximum'))is not int or not isinstance(grant.get('calls'),list):raise LegalMathError('E_SCHEMA')
    if out.exists() and not resume and not recover:raise LegalMathError('E_IDEMPOTENCY')
    out.mkdir(parents=True,exist_ok=True)
    with (out/'.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise LegalMathError('E_JOB_STATE',details='Another operation owns this issue run')
        path=out/'run.json';existing=loads(path.read_bytes()) if path.exists() else None
        if existing:
            verify_allowance_checkpoint(ledger,existing['allowance_checkpoint_hash'])
            ceiling=existing['reservation_ceiling']
        else:
            if resume or recover:raise LegalMathError('E_JOB_STATE',details='No retained issue run to resume')
            ceiling=len(grant['calls'])+24
            if ceiling>grant['maximum']:raise LegalMathError('E_RESOURCE_LIMIT',details='The declared run needs up to 24 available calls')
        provider=provider or CodexProvider(allowance=Allowance(ledger,grant['maximum'],reservation_ceiling=ceiling))
        route=digest(provider.routing)
        binding={'public_hash':digest(public),'arm':arm,'implementation_hash':implementation_hash(),
            'provider_route_hash':route,'ledger_path':str(ledger),'jdk_path':str(jdk),
            'jdk_version':jdk_version,
            'deadline_seconds':deadline_seconds,'call_cap':24}
        if existing and existing['binding']!=binding:raise LegalMathError('E_STALE_REVIEW')
        if not existing:
            existing={'binding':binding,'allowance_checkpoint_hash':digest(grant),'initial_calls':len(grant['calls']),
                'reservation_ceiling':ceiling,'wall_milliseconds':0,'status':'PREPARED','recoveries':[]}
            save(out/'public.json',public);save(path,existing)
        elif loads((out/'public.json').read_bytes())!=public:raise LegalMathError('E_INTEGRITY')
        if existing['status']=='COMPLETE':
            if recover:raise LegalMathError('E_IDEMPOTENCY')
            verify_allowance_checkpoint(ledger,existing['final_allowance_checkpoint_hash'])
            check_manifest(out/'result')
            check_manifest(out/'work')
            for planfile in sorted((out/'work/queues').glob('*/plan.json')):
                queue=CheckpointQueue(planfile.parent,loads(planfile.read_bytes()))
                if not queue.report()['execution_complete']:raise LegalMathError('E_INTEGRITY')
            return loads((out/'result/report.json').read_bytes())
        if existing['status']=='RUNNING' and not recover:
            raise LegalMathError('E_JOB_STATE',details='Interrupted dispatch requires explicit recovery')
        if recover:
            if existing['status'] not in ('RUNNING','FAILED'):raise LegalMathError('E_JOB_STATE')
            count=0
            for planfile in sorted((out/'work/queues').glob('*/plan.json')):
                queue=CheckpointQueue(planfile.parent,loads(planfile.read_bytes()));count+=queue.recover()
            if existing.get('active_since_utc'):
                elapsed=max(0,int((datetime.now(timezone.utc)-datetime.fromisoformat(existing['active_since_utc'])).total_seconds()*1000))
                existing['wall_milliseconds']+=elapsed
            record={'at':datetime.now(timezone.utc).isoformat(),'recovered_tasks':count,
                'allowance_checkpoint_hash':digest(loads(ledger.read_bytes())),'reservation_refunded':False,
                'timing':'Conservative elapsed time through recovery for interrupted execution'}
            existing['recoveries'].append(record);existing.update(status='RECOVERED',active_since_utc=None)
            save(path,existing);return {'status':'RECOVERED','recovery':record,'release_eligible':False}
        if existing['status']=='FAILED' and not resume:raise LegalMathError('E_JOB_STATE')
        remaining=deadline_seconds-existing['wall_milliseconds']/1000
        if remaining<30:raise LegalMathError('E_RESOURCE_LIMIT',details='Retained issue execution-time limit exhausted')
        existing.update(status='RUNNING',active_since_utc=datetime.now(timezone.utc).isoformat());save(path,existing)
        began=monotonic()
        try:
            result=MethodRun(out/'work',public,provider,ledger,jdk,deadline_seconds=remaining).execute(arm)
            after=loads(ledger.read_bytes());calls=len(after['calls'])-existing['initial_calls']
            if not 0<=calls<=24:raise LegalMathError('E_INTEGRITY')
            from .issue_search import reconsideration_required
            concerns=bool(result['behavior_groups']>1 or result['merged']['concerns'] or result['merged']['deferred'] or
                result['invalid_proposals']['records'] or any(r['formalization'] is None for r in result['merged']['candidates'].values()))
            if result['reviews']:concerns=concerns or reconsideration_required(result['reviews'],result['merged'],behavior_groups=result['behavior_groups'])
            report={'status':'UNCERTAINTY_RETAINED' if concerns else 'NO_DISCREPANCY_REPORTED',
                'question':public['issue']['question'],'result':result,'model_calls':calls,
                'output_descriptors':{cid:descriptor(reading,public['issue']['question'])
                    for cid,reading in result['merged']['candidates'].items() if reading['formalization'] is not None},
                'limits':{'model_calls':24,'readings_per_request':2,'criticism_targets_per_request':4,
                    'attempts_per_task':3,'reconsideration_cycles':1,'boolean_facts':4,
                    'execution_seconds':deadline_seconds},
                'executed_comparison':'work/'+('java-reconsidered' if result['cycles'] else 'java-initial')+'/issue-distinction-report.json',
                'accounting_scope':'All allowance reservations since this run started; schedule runs serially on this allowance',
                'binding':binding,'release_eligible':False,'legal_accuracy_evaluated':False,
                'legal_correctness_probability':None}
            save(out/'result/report.json',report);seal(out/'result')
            existing.update(status='COMPLETE',final_allowance_checkpoint_hash=digest(after))
            return report
        except BaseException as exc:
            # Keyboard interruption keeps a recoverable state; no implicit refund.
            if isinstance(exc,Exception):existing.update(status='FAILED',error=getattr(exc,'code',type(exc).__name__),
                details=getattr(exc,'details',str(exc)))
            raise
        finally:
            existing['wall_milliseconds']+=int((monotonic()-began)*1000)
            existing['active_since_utc']=None;save(path,existing)


def execute_cli(args):
    public=loads(Path(args.public).read_bytes())
    return run_public_issue(public,args.out,args.allowance,args.jdk,arm=args.method,
        deadline_seconds=args.deadline_seconds,resume=args.resume,recover=args.recover)
