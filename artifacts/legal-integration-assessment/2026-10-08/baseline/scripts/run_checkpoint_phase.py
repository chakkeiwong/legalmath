"""Execute only frozen round-seven requests through durable, counted tasks."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.checkpoints import CheckpointQueue,seal
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.assurance.arguments import evaluate_criticism
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Allowance,CodexProvider,verify_allowance_checkpoint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round7'
CONTRACTS=ROOT/'docs/implementation/interpretation-round7/contracts'


def run(phase,directory):
    if phase not in ('E1','E2','E3'):raise ValueError('Unreviewed phase')
    directory=Path(directory).resolve()
    if directory.exists() or not directory.is_relative_to(OUT/phase):raise ValueError('Use a new phase attempt directory')
    contract=loads((CONTRACTS/(phase+'.json')).read_bytes())
    plan=loads((CONTRACTS/contract['plan_file']).read_bytes())
    if digest(plan)!=contract['plan_hash']:raise LegalMathError('E_INTEGRITY')
    baseline=loads((ROOT/'.localresources/interpretation-round7/baseline.json').read_bytes())
    old=ROOT/'artifacts/interpretation/round2/live-allowance.json'
    if digest(loads(old.read_bytes()))!=baseline['old_allowance_hash']:raise LegalMathError('E_STALE_REVIEW')
    for name,expected in baseline['protected'].items():
        if raw_digest((ROOT/name).read_bytes())!=expected:raise LegalMathError('E_INTEGRITY',details=name)
    ledger=OUT/'live-allowance.json'
    verify_allowance_checkpoint(ledger,digest({'maximum':500,'calls':[]}))
    before=loads(ledger.read_bytes())
    settings=Settings.model_validate(contract['settings'])
    provider=CodexProvider(allowance=Allowance(ledger,500,reservation_ceiling=contract['reservation_ceiling']))
    if digest(provider.routing)!=plan['route_hash']:raise LegalMathError('E_STALE_REVIEW',details='Provider route changed')
    directory.mkdir(parents=True);save(directory/'contract.json',contract);save(directory/'allowance-before.json',before)
    queue=CheckpointQueue(OUT/'workqueues'/phase,plan)
    report=queue.report()
    if phase=='E2' and not report['imported_tasks']:
        seed=ROOT/'artifacts/interpretation/round6/D1S/attempt-02/live'
        queue.import_response(plan['tasks'][0]['task_id'],seed/'calls/call-000',seed,old)
    # A fresh wrapper per action retains failed calls while the queue enforces
    # the two-failure circuit and three-attempt task ceiling across restarts.
    def factory(path):
        return CompactProvider(provider,path/'transport')
    began=monotonic()
    report=queue.run(factory,ledger,settings,maximum_actions=contract['maximum_actions'],
        deadline_seconds=contract['deadline_seconds'],backoff_seconds=10)
    after=loads(ledger.read_bytes());used=len(after['calls'])-len(before['calls'])
    if after['calls'][:len(before['calls'])]!=before['calls'] or not 0<=used<=contract['maximum_actions']:
        raise LegalMathError('E_INTEGRITY')
    summary={'phase':phase,'engineering_status':'COMPLETE_CHECKS' if report['execution_complete'] else 'INCOMPLETE',
        'queue_report':report,'new_live_calls':used,'additional_grant_used':len(after['calls']),
        'additional_grant_remaining':500-len(after['calls']),'wall_milliseconds':int((monotonic()-began)*1000),
        'legal_accuracy_evaluated':False,'ranking_established':False,'release_eligible':False}
    if phase=='E2' and report['execution_complete']:
        summary['fidelity']=queue.aggregate_fidelity()
        for name in ('aggregate.json','findings.json'):
            save(directory/name,loads((queue.directory/name).read_bytes()))
    elif phase in ('E1','E3'):
        results=queue._results(queue._state());save(directory/'results.json',results)
        if phase=='E3' and results:
            task=plan['tasks'][0];value=next(iter(results.values()))
            evaluation=evaluate_criticism(value,task['context']['packet'],task['context']['candidates'])
            save(directory/'argument-evaluation.json',evaluation)
            summary['argument_status']=evaluation['status']
    save(directory/'summary.json',summary);save(directory/'allowance-after.json',after)
    save(directory/'queue-snapshot.json',{'plan_hash':digest(plan),'state':queue._state(),
        'files':{str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in sorted(queue.directory.rglob('*'))
                 if p.is_file() and p.name!='.lock'}})
    seal(directory)
    print(canonical({k:v for k,v in summary.items() if k!='queue_report'}).decode(),flush=True)
    if not report['execution_complete']:raise SystemExit(2)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--phase',required=True,choices=('E1','E2','E3'))
    parser.add_argument('--out',required=True);args=parser.parse_args();run(args.phase,args.out)
