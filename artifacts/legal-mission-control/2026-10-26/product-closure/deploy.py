"""Bounded transactional deployment; archives current bytes and preserves authority."""
from pathlib import Path
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime,timezone
from unittest.mock import patch
import argparse,importlib,json,os,shutil,subprocess,sys,time
ROOT=Path('/home/chakwong/python/legalmath')
WORK=Path('artifacts/legal-mission-control/2026-10-26/product-closure')
TREE=Path('/tmp/legalmath-product-closure-20261026')
OLD=Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,save,ref,verify,require,digest,process_alive
from scripts.legal_integration_master import BASE,DOC,PROGRAM,STATE,PLAN
from scripts import legal_baseline_corpus_deployment as transaction
REVIEW=Path('docs/plans/legal-product-closure-2026-10-26.md')
def now():return datetime.now(timezone.utc).isoformat()
def sources():return [r['path'] for r in read(ROOT/WORK/'local-result-v3.json')['sources']]
def source_files():return {r['path']:r['candidate'] for r in read(ROOT/WORK/'local-result-v3.json')['sources']}
def locks(binding):
    return [OLD/'worker.lock',OLD/'arm.lock',OLD/'live/supervisor.lock',
        *transaction.lock_paths(ROOT,binding,[])]
def idle():
    requested=read(ROOT/WORK/'handover-request.json')
    require(not process_alive(requested['supervisor']),'Original supervisor is still active')
    done=read(ROOT/OLD/'probe-capacity-fix/finished.json')
    require(done['refresh_exit']==0 and done['at_utc']>=requested['at_utc'],'Original cleanup incomplete')
    require(len(read(ROOT/BASE/'live-calls.json')['calls'])==requested['calls'],'Dispatch occurred after handover')
    for pointer in requested['journals']+requested['phases']:verify(ROOT,pointer)
    return requested
def imports():
    for name in list(sys.modules):
        if name=='scripts' or name.startswith('scripts.') or name=='legalmath' or name.startswith('legalmath.'):
            del sys.modules[name]
    sys.path[:0]=[str(TREE/'src'),str(TREE)]
    import scripts
    scripts.__path__=[str(TREE/'scripts')]
    for name in ('legal_mission_execution','legal_integration_master','legal_mission_control',
            'legal_integration_campaign','legal_integration_qualification_continuation',
            'legal_repaired_retry_continuation','legal_product_closure'):
        importlib.import_module('scripts.'+name).ROOT=ROOT
def stage():
    require(not (ROOT/WORK/'baseline.json').exists(),'Closure already staged')
    require(all(r['exit_code']==0 for r in read(ROOT/WORK/'admission-results.json'))
        and len(read(ROOT/WORK/'admission-results.json'))==3,'Admission incomplete')
    checked=read(ROOT/WORK/'local-result-v2.json');require(checked['verdict']=='PASS','Candidate failed')
    for row in checked['sources']:
        verify(ROOT,row['candidate'])
        if row['before']:verify(ROOT,row['before'])
        else:require(not (ROOT/row['path']).exists(),'New path appeared')
    binding=read(ROOT/BASE/'current-binding.json')
    with ExitStack() as stack:
        transaction.acquire_locks(ROOT,stack,locks(binding));handover=idle()
        paths=list(dict.fromkeys([PROGRAM,STATE,DOC/'mission.json',PLAN,BASE/'current-binding.json',
            BASE/'current-stage.json',BASE/'live-calls.json',*map(Path,sources())]))
        archived=[];absent=[]
        for p in paths:
            if not (ROOT/p).exists():absent.append(str(p));continue
            target=WORK/'before'/p;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/p,ROOT/target)
            archived.append(dict(previous=ref(ROOT,p),archive=ref(ROOT,target)))
        baseline=dict(archived=archived,absent_paths=absent,
            changed_paths=sources()+[str(PLAN)],implementation_paths=sources(),
            calls=handover['calls'],at_utc=now())
        save(ROOT/WORK/'baseline.json',baseline)
    held={r['previous']['path']:r['archive'] for r in archived}
    save(ROOT/WORK/'handover.json',dict(**handover,settled=True,supervisor_ended=True))
    target=WORK/'registration-stage'
    plan=(ROOT/PLAN).read_text()+('\n\n## Product closure amendment, 26 October 2026\n\n'
        'Execute docs/plans/legal-product-closure-2026-10-26.md under the existing task graph. '
        'Preserve all prior attempts, calls, reservations and the deadline. Conditional-answer '
        'issue dispositions must bind every old objection to the actual answer version. '
        'Independent corpus source reviews can complete with documented limitations; final '
        'qualification still requires every original answer and adverse controls. '
        'Use the tested equivalent Unicode validation predicate; full integrity checks remain. '
        'After each package retain its evidence, refresh the ready set, continue independent '
        'work, and report exact remaining blockers. No local test closes the legal mission.\n')
    (ROOT/target).mkdir(parents=True,exist_ok=True);(ROOT/target/'master-plan.md').write_text(plan)
    revision=dict(profile='reviewed-product-closure.v1',work=str(WORK),prior_detours=68,
        additional_consolidated_revision=1,calls_added=0,attempts_added=0,replacements_added=0,
        attempts_reset=False,reopened_nodes=[],review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),
        baseline=ref(ROOT,WORK/'baseline.json'),handover=ref(ROOT,WORK/'handover.json'),
        prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],
        prior_binding=held[str(BASE/'current-binding.json')],
        phase_identity=held[str(BASE/'current-binding.json')]['sha256'],
        master_plan=dict(path=str(PLAN),sha256=ref(ROOT,target/'master-plan.md')['sha256']),
        implementation={name:dict(path=name,sha256=pointer['sha256']) for name,pointer in source_files().items()},
        checkpoint_activation='UNSTARTED_P14_BASELINE_ONLY',
        arm_checkpoints={'p14':{'baseline':ref(ROOT,WORK/'p14-checkpoint.json')}},
        corpus_components=read(ROOT/WORK/'corpus-registration.json'),
        substantive_evidence={'p14_dispositions':ref(ROOT,WORK/'p14-current-dispositions-v2.json'),
            'p14_review':ref(ROOT,WORK/'p14-current-disposition-result-v2.json'),
            'source_reviews':ref(ROOT,WORK/'corpus-independent-result.json')})
    revision['result']=ref(ROOT,WORK/'local-result-v2.json')
    require(not (ROOT/OLD/'live/arms/p14/baseline').exists(),
        'Cannot change checkpoint of a started P14 baseline')
    imports()
    from scripts import legal_product_closure as closure
    from scripts.legal_integration_acceptance_revision import historical_projection
    previous=read(ROOT/PROGRAM);program=closure.expected_program(previous,revision,ROOT)
    save(ROOT/target/'program.json',program)
    pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,target/'program.json')['sha256'])
    state=read(ROOT/STATE);state['program_hash']=digest(program)
    state['events'].append(dict(task_id=None,action='PRODUCT_CLOSURE_DEPLOYMENT',at_utc=now(),
        calls_added=0,attempts_added=0,review=revision['review']))
    save(ROOT/target/'state.json',state)
    mapping=closure.aliases(baseline)
    mapping[(str(PROGRAM),revision['prior_program']['sha256'])]=revision['prior_program']
    binding['bindings']=historical_projection(binding['bindings'],mapping)
    binding.update(program=pointer,product_closure=revision,predecessor=revision['prior_binding'],
        phase_service_predecessor=revision['prior_binding'])
    binding['bindings'] += [pointer,revision['master_plan'],revision['review'],revision['result'],*revision['implementation'].values(),
        *revision['substantive_evidence'].values(),*revision['corpus_components'].values(),
        revision['arm_checkpoints']['p14']['baseline']]
    known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
    binding['historical_archives'] += [r for r in archived if (r['previous']['path'],r['previous']['sha256']) not in known]
    save(ROOT/target/'binding.json',binding)
    prior_stage=read(ROOT/read(ROOT/BASE/'current-stage.json')['path'])
    stage={**prior_stage,'binding_hash':digest(binding)}
    save(ROOT/WORK/'successor-stage.json',stage)
    save(ROOT/target/'current-stage.json',ref(ROOT,WORK/'successor-stage.json'))
    mission=historical_projection(read(ROOT/DOC/'mission.json'),mapping)
    mission['integration_master'].update(program=pointer,plan=revision['master_plan'],product_closure=revision)
    reason='Execute reviewed current-answer, corpus and validation repair; adopt checkpointed owners, then continue independent product work and audit substantive gaps.'
    mission['next_task_reason']=reason
    mission['history'].append(dict(id='product-closure-2026-10-26',task_id='product-contribution',
        kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
        next_task_reason=reason,recorded_at_utc=now(),result_evidence=[pointer,revision['review'],revision['result']]))
    save(ROOT/target/'mission.json',mission)
    return dict(staged=True,calls=baseline['calls'],attempts_added=0)
def overrides():
    stage=WORK/'registration-stage'
    result={ROOT/name:ROOT/pointer['path'] for name,pointer in source_files().items()}
    result.update({ROOT/p:ROOT/stage/name for p,name in [(PROGRAM,'program.json'),(STATE,'state.json'),
        (DOC/'mission.json','mission.json'),(PLAN,'master-plan.md'),(BASE/'current-binding.json','binding.json'),
        (BASE/'current-stage.json','current-stage.json')]})
    return result
def validate():
    transaction.assert_unchanged(ROOT,read(ROOT/WORK/'baseline.json'));idle();imports()
    from scripts import legal_mission_control as control
    from scripts.legal_integration_master import MasterExecution
    from scripts.legal_integration_campaign import provider
    changes=overrides();originals={n:getattr(Path,n) for n in ('read_text','read_bytes','is_file','exists')}
    start=time.monotonic()
    with ExitStack() as stack:
        for name,method in originals.items():
            stack.enter_context(patch.object(Path,name,lambda p,*a,_method=method,**k:_method(changes.get(p,p),*a,**k)))
        mission=read(ROOT/DOC/'mission.json');control.verify_refs(ROOT,mission)
        result=control.validate(mission,read(ROOT/DOC/'tools.json'),ROOT)
        require(result['detours_since_advance']==69,'Wrong retained detour total')
        ledger=provider().check();require(len(ledger['calls'])==read(ROOT/WORK/'baseline.json')['calls'],'Unexpected charge')
        view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    receipt=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,elapsed_seconds=time.monotonic()-start,
        detours=69,execution=view['execution'],ready=view['ready'],running=view['running'],blocked=view['blocked'],
        files={str(p.relative_to(ROOT)):ref(ROOT,v) for p,v in changes.items()})
    save(ROOT/WORK/'staged-verification.json',receipt)
    return {k:receipt[k] for k in ('verdict','elapsed_seconds','execution','ready','running')}
def commit():
    receipt=read(ROOT/WORK/'staged-verification.json');require(receipt['verdict']=='PASS','Staging not verified')
    for pointer in receipt['files'].values():verify(ROOT,pointer)
    binding=read(ROOT/BASE/'current-binding.json')
    with ExitStack() as stack:
        transaction.acquire_locks(ROOT,stack,locks(binding));idle()
        transaction.assert_unchanged(ROOT,read(ROOT/WORK/'baseline.json'))
        writes=[dict(path=str(p.relative_to(ROOT)),before=ref(ROOT,p) if p.exists() else None,replacement=ref(ROOT,v))
            for p,v in overrides().items()]
        save(ROOT/WORK/'registration.json',dict(profile='baseline-corpus-deployment-transaction.v1',status='PREPARED',writes=writes))
        transaction.finish_transaction(ROOT,WORK/'registration.json')
    return dict(committed=True,provider_calls=0)
def verify_installed():
    receipt=read(ROOT/WORK/'staged-verification.json')
    for path,pointer in receipt['files'].items():
        require(ref(ROOT,path)['sha256']==pointer['sha256'],'Installed bytes differ '+path)
    from scripts.legal_integration_campaign import provider
    count=len(provider().check()['calls'])
    require(count==read(ROOT/WORK/'baseline.json')['calls'],'Unexpected deployment calls')
    start=time.monotonic()
    with (ROOT/WORK/'installed-refresh.stdout').open('x') as out,(ROOT/WORK/'installed-refresh.stderr').open('x') as err:
        code=subprocess.call(['.venv/bin/python','scripts/legal_mission_control.py','refresh'],cwd=ROOT,stdout=out,stderr=err)
    result=dict(verdict='PASS' if code==0 else 'FAIL',exit_code=code,calls=count,provider_calls=0,
        elapsed_seconds=time.monotonic()-start,at_utc=now())
    save(ROOT/WORK/'installed-verification.json',result);require(code==0,'Installed refresh failed')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['stage','validate','commit','verify_installed'])
    print(json.dumps(globals()[parser.parse_args().action](),indent=2))
