"""History-preserving closure amendment; never grants calls or legal acceptance."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,verify,require,historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection

KEY='product_closure'
PROFILE='reviewed-product-closure.v1'
WORK='artifacts/legal-mission-control/2026-10-26/product-closure'

def aliases(baseline):
    changed=set(baseline['changed_paths'])
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in baseline['archived'] if r['previous']['path'] in changed}

def expected_program(old,revision,root):
    baseline=read(Path(root)/revision['baseline']['path'])
    value=historical_projection(old,aliases(baseline))
    value[KEY]=deepcopy(revision)
    value['protected_evidence'] += [revision[k] for k in ('review','result','baseline','handover')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'] += list(revision.get('substantive_evidence',{}).values())
    # The master validator passes the final protected reference as the plan.
    value['protected_evidence'].append(revision['master_plan'])
    return value

def validate(program,root,plan_reference):
    from scripts.legal_mission_execution import validate_program
    root=Path(root);r=program[KEY]
    if r.get('runtime'):
        return validate_runtime(program,root,plan_reference)
    if r.get('followthrough'):
        return validate_followthrough(program,root,plan_reference)
    require(r['profile']==PROFILE and r['work']==WORK and r['prior_detours']==68
        and r['additional_consolidated_revision']==1 and r['calls_added']==0
        and r['attempts_added']==0 and r['replacements_added']==0
        and r['attempts_reset'] is False and r['reopened_nodes']==[],
        'Unreviewed product closure scope')
    for k in ('review','result','baseline','handover','prior_program','prior_state','prior_binding','master_plan'):
        verify(root,r[k])
    b=read(root/r['baseline']['path']);old=read(root/r['prior_program']['path'])
    require(KEY not in old,'Repeated closure amendment')
    held={x['previous']['path']:x['archive'] for x in b['archived']}
    for x in b['archived']:
        require(x['previous']['sha256']==x['archive']['sha256'],'Changed historical bytes')
        verify(root,x['archive'])
    from scripts.legal_integration_master import PROGRAM,STATE,BASE
    for key,path in [('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')]:
        require(r[key]==held[str(path)],'Wrong closure predecessor')
    require(set(r['implementation'])==set(b['implementation_paths']),'Changed closure source population')
    for p in r['implementation'].values():verify(root,p)
    for p in r.get('substantive_evidence',{}).values():verify(root,p)
    if r.get('arm_checkpoints'):
        from scripts.legal_integration_master import BASE
        require(set(r['arm_checkpoints'])=={'p14'} and set(r['arm_checkpoints']['p14'])=={'baseline'},
            'Unreviewed answer checkpoint selection')
        before=old['repaired_retry_continuation']['arm_checkpoints']['p14']['baseline']
        verify(root,before);after=r['arm_checkpoints']['p14']['baseline'];verify(root,after)
        expected=read(root/before['path'])
        expected['current_answer_issue_dispositions']={'p14':r['substantive_evidence']['p14_dispositions']}
        require(read(root/after['path'])==expected,'Checkpoint changed beyond reviewed issue dispositions')
        require(r['checkpoint_activation']=='UNSTARTED_P14_BASELINE_ONLY',
            'Unreviewed checkpoint migration')
    if r.get('corpus_components'):
        for p in r['corpus_components'].values():verify(root,p)
    with historical_evidence(root,aliases(b)):validate_program(old,root)
    checks=read(root/r['result']['path']);handover=read(root/r['handover']['path'])
    require(checks['verdict']=='PASS' and checks['provider_calls']==0 and checks['legal_acceptance'] is False,
        'Closure candidate not verified')
    for p in checks['evidence']:verify(root,p)
    require(handover['settled'] and handover['reserved_dispatches']==0
        and handover['supervisor_ended'],'Unsafe closure handover')
    require(r['phase_identity']==read(root/r['prior_binding']['path']).get('product_closure',{}).get(
        'phase_identity',r['prior_binding']['sha256']),
        'Changed retained phase identity')
    require(plan_reference==r['master_plan'] and program==expected_program(old,r,root),
        'Closure altered graph, budgets or unrelated authority')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def validate_history(program,state,root):
    if program[KEY].get('runtime'):
        return validate_runtime_history(program,state,root)
    from scripts.legal_repaired_retry_continuation import validate_history as predecessor
    root=Path(root);r=program[KEY];old=read(root/r['prior_program']['path'])
    if r.get('followthrough'):
        return validate_followthrough_history(program,state,root)
    before=read(root/r['prior_state']['path']);baseline=read(root/r['baseline']['path'])
    with historical_evidence(root,aliases(baseline)):predecessor(old,state,root)
    require(state['events'][:len(before['events'])]==before['events'],'Lost closure history')
    for tid,prior in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(prior['attempts']),'Lost closure attempt '+tid)
        for a,b in zip(prior['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed retained attempt '+tid)
        if prior['status'] not in ('RUNNING','PENDING'):
            require(prior==current,'Reopened settled closure task '+tid)

def expected_followthrough(old,fix,root):
    baseline=read(Path(root)/fix['baseline']['path'])
    value=historical_projection(old,aliases(baseline))
    value[KEY]['followthrough']=deepcopy(fix)
    for task in value['tasks']:
        if task['id']=='baseline-p14':task['maximum_attempts']+=1
    value['protected_evidence'] += [fix[k] for k in ('review','result','baseline','handover')]
    value['protected_evidence'] += list(fix['implementation'].values())
    value['protected_evidence'] += list(fix['corpus_components'].values())
    value['protected_evidence'].append(fix['master_plan'])
    return value

def validate_followthrough(program,root,plan_reference):
    from scripts.legal_mission_execution import validate_program
    from scripts.legal_integration_master import PROGRAM,STATE,BASE
    fix=program[KEY]['followthrough']
    require(fix['profile']=='product-closure-followthrough.v1'
        and fix['work']==WORK+'/followthrough' and fix['additional_detours']==0
        and fix['calls_added']==fix['replacements_added']==0
        and fix['attempt_additions']=={'baseline-p14':1}
        and fix['attempts_reset'] is False,'Unreviewed closure follow-through')
    for key in ('review','result','baseline','handover','prior_program','prior_state','prior_binding','master_plan'):
        verify(root,fix[key])
    baseline=read(root/fix['baseline']['path'])
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    require(len(held)==len(baseline['archived']),'Duplicate follow-through archive')
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed follow-through history')
        verify(root,row['archive'])
    for key,path in [('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')]:
        require(fix[key]==held[str(path)],'Wrong follow-through predecessor')
    require(set(fix['implementation'])==set(baseline['implementation_paths']),'Changed follow-through source population')
    for pointer in [*fix['implementation'].values(),*fix['corpus_components'].values()]:verify(root,pointer)
    old=read(root/fix['prior_program']['path']);before=read(root/fix['prior_state']['path'])
    require('followthrough' not in old[KEY],'Repeated follow-through')
    require(before['tasks']['baseline-p14']['status']=='FAILED'
        and len(before['tasks']['baseline-p14']['attempts'])==8,'Wrong recovered P14 attempt')
    target=fix['resolved_veto']
    require(target in before.get('continuation_vetoes',[])
        and target['code']=='E_INTEGRITY'
        and target['reason']=='Capacity reuse changed substantive schema'
        and target['evidence']==[fix['schema_failure']],'Wrong schema veto recovery')
    verify(root,fix['schema_failure'])
    result=read(root/fix['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0
        and result['legal_acceptance'] is False,'Unverified follow-through')
    for pointer in result['evidence']:verify(root,pointer)
    handover=read(root/fix['handover']['path'])
    require(handover['settled'] and handover['supervisor_ended']
        and handover['reserved_dispatches']==0,'Unsafe follow-through handover')
    with historical_evidence(root,aliases(baseline)):validate_program(old,root)
    require(plan_reference==fix['master_plan']
        and program==expected_followthrough(old,fix,root),'Changed unrelated follow-through scope')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def validate_followthrough_history(program,state,root):
    fix=program[KEY]['followthrough'];baseline=read(root/fix['baseline']['path'])
    old=read(root/fix['prior_program']['path']);before=read(root/fix['prior_state']['path'])
    with historical_evidence(root,aliases(baseline)):validate_history(old,before,root)
    require(set(state['tasks'])==set(before['tasks'])
        and state['events'][:len(before['events'])]==before['events'],'Lost follow-through state')
    for tid,prior in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(prior['attempts']),'Lost follow-through attempt')
        for a,b in zip(prior['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed follow-through attempts')
        if tid!='baseline-p14' and prior['status'] not in ('PENDING','RUNNING'):
            require(current==prior,'Reopened unrelated follow-through task')
    require(state.get('resolved_continuation_vetoes',[])[:len(before.get('resolved_continuation_vetoes',[]))]
        ==before.get('resolved_continuation_vetoes',[]),'Lost prior veto resolutions')
    target=fix['resolved_veto']
    require(any(row.get('veto')==target and row.get('review')==fix['review']
        and row.get('evidence')==fix['result'] for row in state.get('resolved_continuation_vetoes',[])),
        'Missing checked schema-veto resolution')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[]) if v!=target),
        'Lost independent follow-through veto')

def runtime_directory():
    from scripts.legal_integration_master import PROGRAM
    value=read(ROOT/PROGRAM)[KEY]
    return ROOT/value.get('runtime',value.get('followthrough',value))['work']


def expected_runtime(old, revision, root):
    baseline=read(Path(root)/revision['baseline']['path'])
    value=historical_projection(old,aliases(baseline))
    value[KEY]['runtime']=deepcopy(revision)
    value['acquisition_fairness_profile']=revision['acquisition_fairness_profile']
    value['protected_evidence'] += [revision[k] for k in ('review','result','baseline','handover')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(revision['master_plan'])
    return value


def validate_runtime(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    from scripts.legal_integration_master import PROGRAM, STATE, BASE
    root=Path(root);r=program[KEY]['runtime']
    require(r['profile']=='product-closure-runtime.v1'
        and r['work']==WORK+'/followthrough/runtime-deployment'
        and r['calls_added']==r['attempts_added']==r['replacements_added']==0
        and r['additional_detours']==0 and r['attempts_reset'] is False
        and r['acquisition_fairness_profile']=='independent-acquisition-before-answer-drain.v1'
        and r['review_budget_yield_profile']=='preserve-review-population-on-branch-exhaustion.v1',
        'Unreviewed runtime repair scope')
    for key in ('review','result','baseline','handover','prior_program','prior_state','prior_binding','master_plan'):
        verify(root,r[key])
    baseline=read(root/r['baseline']['path']);held={x['previous']['path']:x['archive'] for x in baseline['archived']}
    require(len(held)==len(baseline['archived']), 'Duplicate runtime archive')
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed runtime predecessor bytes')
        verify(root,row['archive'])
    for key,path in [('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')]:
        require(r[key]==held[str(path)], 'Wrong runtime predecessor')
    require(set(r['implementation'])==set(baseline['implementation_paths']), 'Changed runtime source population')
    for pointer in r['implementation'].values():verify(root,pointer)
    old=read(root/r['prior_program']['path'])
    require('runtime' not in old[KEY], 'Repeated runtime amendment')
    result=read(root/r['result']['path']);handover=read(root/r['handover']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0
        and result['legal_acceptance'] is False,'Unverified runtime repair')
    for pointer in result['evidence']:verify(root,pointer)
    require(handover['settled'] and handover['supervisor_ended'] and handover['reserved_dispatches']==0,
        'Unsafe runtime handover')
    with historical_evidence(root,aliases(baseline)):validate_program(old,root)
    require(plan_reference==r['master_plan'] and program==expected_runtime(old,r,root),
        'Runtime repair altered unrelated scope or authority')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def validate_runtime_history(program, state, root):
    root=Path(root);r=program[KEY]['runtime'];b=read(root/r['baseline']['path'])
    old=read(root/r['prior_program']['path']);before=read(root/r['prior_state']['path'])
    with historical_evidence(root,aliases(b)):validate_history(old,before,root)
    require(set(state['tasks'])==set(before['tasks'])
        and state['events'][:len(before['events'])]==before['events'],'Lost runtime predecessor state')
    for tid,prior in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(prior['attempts']), 'Lost runtime attempt')
        for a,b in zip(prior['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()), 'Changed runtime attempt history')
        if prior['status'] not in ('PENDING','RUNNING'):
            require(current==prior, 'Runtime repair reopened a settled task')
    require(state.get('resolved_continuation_vetoes',[])[:len(before.get('resolved_continuation_vetoes',[]))]
        ==before.get('resolved_continuation_vetoes',[]), 'Lost runtime veto history')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),
        'Runtime repair waived a global veto')

def corpus():
    from scripts.legal_integration_master import PROGRAM
    from scripts.legal_mission_execution import save
    from scripts.legal_integration_qualification_continuation import corpus as consume
    program=read(ROOT/PROGRAM);revision=program[KEY].get('followthrough',program[KEY])
    for pointer in revision['corpus_components'].values():verify(ROOT,pointer)
    directory=runtime_directory()/'corpus-handler';directory.mkdir(parents=True,exist_ok=True)
    result=consume(directory)
    save(directory/'result.json',dict(**result,attempts_added=0,provider_calls=0,
        prior_corpus_attempts_retained=True,legal_acceptance=False))
    return result

def arm():
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_master import PROGRAM
    from scripts.legal_mission_execution import process_alive,process_identity,save
    directory=runtime_directory()
    require(read(directory/'registration.json')['status']=='COMMITTED'
        and read(directory/'installed-verification.json')['verdict']=='PASS',
        'Closure deployment is not installed and verified')
    program=read(ROOT/PROGRAM);require(program.get(KEY),'Closure not registered')
    handover=read(directory/'handover.json')
    require(not process_alive(handover['supervisor']),'Predecessor still active')
    with (directory/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=directory/'armed.json'
        if path.exists():
            saved=read(path);require(process_alive(saved['process']),
                'Closure worker ended; inspect result before reviewed restart')
            return saved
        provider().check()
        with (directory/'worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),
                str(ROOT/'scripts/legal_product_closure.py'),'worker'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        identity=process_identity(process.pid);require(identity,'Closure worker exited at startup')
        result=dict(process=identity,at_utc=datetime.now(timezone.utc).isoformat(),
            attempts_added_by_handover=0,predecessor=handover['supervisor'])
        save(path,result);return result

def drain_independent():
    from scripts.legal_mission_execution import save
    from scripts.legal_review_repair import live as drain
    try:
        corpus()
    except Exception as exc:
        # Record this branch's failure, then let the existing scheduler validate
        # shared authority/integrity before admitting any independent work.
        # KeyboardInterrupt and SystemExit still stop the supervisor.
        import traceback
        save(runtime_directory()/'corpus-handler-error.json',dict(error=type(exc).__name__,
            reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc(),
            at_utc=datetime.now(timezone.utc).isoformat(),legal_acceptance=False))
    return drain()

def worker():
    from scripts.legal_mission_execution import save,process_identity
    directory=runtime_directory()
    with (directory/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(directory/'worker.json',dict(process=process_identity(os.getpid()),
            at_utc=datetime.now(timezone.utc).isoformat()))
        try:
            save(directory/'live-result.json',drain_independent())
        except BaseException as exc:
            import traceback
            save(directory/'worker-error.json',dict(error=type(exc).__name__,
                reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc(),
                at_utc=datetime.now(timezone.utc).isoformat()))
            raise
        finally:
            with (directory/'final-refresh.stdout').open('w') as out,(directory/'final-refresh.stderr').open('w') as err:
                code=subprocess.call([str(ROOT/'.venv/bin/python'),'scripts/legal_mission_control.py','refresh'],
                    cwd=ROOT,stdout=out,stderr=err)
            save(directory/'finished.json',dict(refresh_exit=code,
                at_utc=datetime.now(timezone.utc).isoformat(),integration_complete=False))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['arm','worker','corpus'])
    print(json.dumps(globals()[parser.parse_args().action](),indent=2))
