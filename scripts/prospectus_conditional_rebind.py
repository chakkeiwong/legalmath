"""Use existing default(f) alternatives on the current exact source groups."""
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_structural_integration as prior
from scripts.prospectus_typed_delta import changes,apply,equal
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;BASE=prior.HERE
PREP=AUTH/'reviews/current-conditional-296'
HERE=AUTH/'attempts/basf-references/attempt-037'
PLAN='docs/plans/prospectus-current-conditional-rebind-2026-10-19.md'
METHOD='scripts/prospectus_conditional_rebind.py'
WORKER='scripts/prospectus_conditional_installed.py'
OLD=AUTH/'reviews/current-default-alternatives-257/profile.json'
OLD_ANSWER=AUTH/'attempts/basf-meanings/attempt-020/current-answer.json.gz'
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
STAGES=('source-check','consume','control-old','control-group','control-selection','installed','trigger-inventory','seal')


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior_resources']['cumulative026_036_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,METHOD,WORKER))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0296.json')
    size=start['prior_resources']['cumulative026_036_bytes']+start['prior_extra_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<5400 and size<508*1024**2,'Cumulative conditional continuation bound'
    return {'cumulative026_037_measured_seconds':seconds,'cumulative026_037_bytes':size,
        'seconds_bound':5400,'bytes_bound_including_4MiB_reserve':512*1024**2,
        'prior_costs_reset':False,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==295
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==36 and any(e['kind']=='RECORD' and e.get('attempt')==rel(BASE) for e in events)
    for name,value in read(BASE/'outputs.json').items():assert sha(BASE/name)==value,name
    extras=read(BASE/'accounting-addendum.json')['extra_root_files'];assert all(sha(ROOT/r['path'])==r['sha256'] for r in extras)
    save(PREP/'accounting-start.json',{'prior_resources':prior.costs(),'prior_extra_bytes':sum(r['bytes'] for r in extras),
        'program_bytes':(AUTH/'program.json').stat().st_size,'history_names':[p.name for p in (AUTH/'history').glob('*.json')]})
    from legalmath.prospectus import basf_default_f as source
    p,answer=prior.retained('answer');profile=read(OLD);groups=source.source_groups(p)
    equal(groups,profile['groups'],'Current exact default source groups changed')
    original=deepcopy(profile);profile.update(products_sha256=digest(p),ordinary_answer_sha256=digest(answer))
    assert {tuple(d['path']) for d in changes(original,profile)}=={('products_sha256',),('ordinary_answer_sha256',)}
    save(PREP/'profile.json',profile)
    save(PREP/'source-equivalence.json',{'status':'PASS','groups_sha256':digest(groups),'groups':list(groups),
        'current_products_sha256':digest(p),'current_answer_sha256':digest(answer),'old_profile_sha256':digest(original),
        'changed_fields':['products_sha256','ordinary_answer_sha256'],'scenarios':len(profile['scenarios']),
        'scenario_outcomes_sha256':digest(read(OLD_ANSWER)['default_f_review']['scenarios'])})
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,WORKER,'pyproject.toml')}
    bindings.update({rel(path):sha(path) for path in (ROOT/'src/legalmath').rglob('*') if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc'})
    bindings.update({rel(path):sha(path) for path in PREP.rglob('*') if path.is_file()})
    for path in (BASE/'outputs.json',BASE/'answer.json.gz',BASE/'package.json',OLD,OLD_ANSWER,
                 prior.BASE/'complete-products.json.gz',prior.BASE/'complete-expected-answer.json.gz',
                 ROOT/'scripts/prospectus_structural_integration.py',ROOT/'scripts/prospectus_structural_oracle.py',
                 AUTH/'attempts/basf-references/attempt-033/exceptional-source-readings.json.gz'):
        bindings[rel(path)]=sha(path)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=296
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Enable existing conditional default alternatives on verified source-equivalent complete output; preserve open meanings and prepare12 source predicates',
        conditional_rebind={'review':rel(PREP),'baseline':rel(BASE),'original_task_complete':False,
            'production_changes':False,'cumulative026_seconds':5400,'cumulative026_bytes_with_reserve':512*1024**2})
    proposal['budgets']['basf-references']['maximum_new_attempts']=37
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=296
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify current default(f) conditional supplement, then source-supported open predicates and historical statutory applications',
            stop_condition='37 admissions;180s stages;5400s cumulative026;512MiB including4MiB reserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    resource=costs();forecast={'seconds':resource['cumulative026_037_measured_seconds']+900,
        'bytes':resource['cumulative026_037_bytes']+3*(AUTH/'program.json').stat().st_size+12*1024**2,
        'basis':'Five complete consumers at150s each plus preparation/verification reserve;existing installed tree reused','estimate_only':True}
    assert forecast['seconds']<5400 and forecast['bytes']<508*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Same task returns to existing conditional source meaning after structural repair','Admission36 to37; cumulative time/storage ceilings unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast,'exact_source_groups_equal':True},
        'evidence_contract':{'primary':'Identical source groups; complete ordinary fields preserved;192 old conditional decisions identical;actual controls refused;installed consumer equal',
            'promotion_veto':['Lost uncertainty','Changed source or scenarios','Wrong temporal/causal scope','Selected unproved governing meaning'],
            'continuation_veto':['Source corruption','Frozen-method drift','Unexpected full answer','Exhausted limits'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Exhaustive legal meaning','Actual default','Whole task completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':36,'new_maximum':37,'retained_attempts':attempts,
            'reason':'Return to source-equivalent conditional behavior after exact structural integration',
            'next_discriminating_check':'Current ordinary answer plus identical conditional outcomes through source and installed consumers',
            'stop_condition':'180s stages;5400s cumulative;512MiB including4MiB reserve',
            'same_scope_authorization':'User requested refreshed master and continued internally supported general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review);save(PREP/'resource-forecast.json',forecast)
    return {'status':'PASS','revision':296,'source_groups_equal':True,'forecast':forecast}


def frozen():
    admission=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/name)==value,name


def source_check():
    from legalmath.prospectus import basf_default_f as source
    p,a=prior.retained('answer');profile=read(PREP/'profile.json')
    equal(source.source_groups(p),profile['groups'],'Bound source groups changed')
    assert digest(p)==profile['products_sha256'] and digest(a)==profile['ordinary_answer_sha256']
    return {'status':'PASS','exact_source_groups_equal':True,'profile_sha256':digest(profile)}


def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import basf_default_f_current as current
    p,ordinary=prior.retained('answer');profile=read(PREP/'profile.json')
    actual=service.consume(p,ROOT,mode='frozen',default_f_profile=profile,expected_default_f_profile_sha256=digest(profile))
    verification=current.verify_answer(actual,ordinary,profile,expected_profile_sha256=digest(profile))
    assert verification['checked_answers']==192
    equal(actual['default_f_review']['scenarios'],read(OLD_ANSWER)['default_f_review']['scenarios'],'Conditional source-equivalent outcomes changed')
    save(HERE/'answer-delta.json.gz',{'base':rel(BASE/'answer.json.gz'),'answer_delta':changes(ordinary,actual),
        'answer_sha256':digest(actual),'ordinary_sha256':digest(ordinary),'verification':verification})
    return {'status':'PASS','ordinary_fields_unchanged':True,'source_equivalent_decisions':192,'answer_sha256':digest(actual)}


def control(kind):
    from legalmath.prospectus.successor import service
    p,_=prior.retained('answer');profile=read(PREP/'profile.json')
    if kind=='old':profile=read(OLD)
    elif kind=='group':profile['groups']['german_f'][0]['selected_text']+=' altered'
    elif kind=='selection':profile['selected_reading']='both_conducts'
    else:raise ValueError(kind)
    try:service.consume(p,ROOT,mode='frozen',default_f_profile=profile,expected_default_f_profile_sha256=digest(profile))
    except ValueError as exc:
        expected={'old':'Complete pre-option ordinary answer changed','group':'Complete original/selected default(f) source groups changed',
                  'selection':'Unresolved German construction and hypothetical scope must remain'}
        assert str(exc)==expected[kind],str(exc)
        save(HERE/('control-'+kind+'.json'),{'status':'PASS','actual_complete_consumer_refused':True,'error':str(exc),
            'profile_sha256':digest(profile),'phase_products_unchanged':True,'profile_pin_matches_mutation':True})
    else:raise AssertionError('Invalid conditional profile accepted')
    return {'status':'PASS','actual_consumer_refusal':kind}


def installed():
    command=[read(BASE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)]
    save(HERE/'installed-command.json',{'command':command,'timeout_seconds':165,'cpu_gpu':'CPU; GPU intentionally hidden'})
    with (HERE/'installed.log').open('x') as stream:
        r=subprocess.run(command,cwd=HERE,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},stdout=stream,stderr=subprocess.STDOUT,timeout=165)
    assert r.returncode==0,'Inspect installed.log'
    result=read(HERE/'installed-result.json');assert result['status']=='PASS'
    return {k:v for k,v in result.items() if k!='production_imports'}


def trigger_inventory():
    p,_=prior.retained('answer');nodes={n['id']:n for n in p['P3']['payload']['clauses']['nodes']}
    source=read(AUTH/'attempts/basf-references/attempt-033/exceptional-source-readings.json.gz')
    rows=[]
    for item in source['unmatched_resolved_to_sources']:
        if item['kind']!='CONDITIONAL_TRIGGER_OR_EXCEPTION':continue
        for row in item['nodes']:
            equal(nodes[row['node']['id']],row['node'],'Conditional source node changed')
            n=row['node'];rows.append({'diagnostic':item['id'],'node':n,'sources':row['sources'],
                'next_cases':['open premises','sufficient hypothetical premises','required premise absent',
                              'exception or cure applies','relevant explicit conflict'],
                'actual_activation':False,'case_matrix_executed':False})
    assert len(rows)==12
    save(HERE/'open-condition-source-packet.json.gz',{'clauses':rows,'actual_client_facts_supplied':False,
        'source_nodes_unchanged':True,'legal_meaning_proved':False,'next_action':'Reviewed source-specific conditional case matrix, then historical statutory applications'})
    return {'status':'PASS','source_predicates_retained':12,'next_case_matrix_executed':False}


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'CURRENT_SOURCE_EQUIVALENT_CONDITIONAL_DEFAULT','ordinary_fields_unchanged':True,
        'source_groups_equal':True,'retained_decisions':192,'installed_complete_equal':True,
        'controls':[read(HERE/('control-'+k+'.json')) for k in ('old','group','selection')],
        'open_condition_sources':12,'open_condition_case_matrix_executed':False,
        'resources':costs(),'production_changes':False,'governing_reading_selected':False,
        'next_action':'Source-supported conditional cases for12 predicates, then historical statutory applications',
        'attribution':'Existing package capability required exact current profile invocation; no fundamental package defect established'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden','random_seeds':'N/A deterministic',
        'data_version':sha(BASE/'answer.json.gz'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    with (HERE/'RESULT.md').open('x') as f:f.write('''# Existing conditional default analysis reaches the current answer

All original and selected default(f) source groups equal the earlier reviewed
profile. Only the complete products and ordinary-answer identities change.
The normal and isolated installed consumers preserve every ordinary field and
reproduce all192 earlier conditional decisions. Actual consumer calls reject
stale input binding, altered source groups and an asserted governing reading.
This is a profile-invocation repair, not a new semantic engine or package defect.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain current conditional supplement | Exact sources, ordinary-field preservation,192 matched decisions,installed equality | Declared adverse controls refused | Governing reading and further source-supported cases | Twelve open predicates and historical statutory applications | Actual default,exhaustive meanings or completed build |

The strongest alternative explanation remains a shared inadequacy in the finite
interpretation set. Reproducing earlier scenarios proves compatibility only.
Twelve additional source predicates are retained as a next-case inventory; that
inventory is not implemented conditional analysis and removes no uncertainty.
''')
    return {'status':'PASS','original_task_complete':False,'resources':costs()}


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_conditional_rebind',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':180})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Conditional stage bound')));signal.alarm(180)
    try:
        if stage!='prepare':frozen()
        if stage.startswith('control-'):result=control(stage.removeprefix('control-'))
        else:result=globals()[stage.replace('-','_')]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
