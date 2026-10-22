"""Reviewed actual-consumer question-consistency reproduction and repair."""
import ast
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_scope_repair as prior
from legalmath.prospectus.execution_authority import Authority,CODE,digest as authority_digest
from legalmath.prospectus.successor.contracts import digest

AUTH=prior.AUTH
PREP=AUTH/'reviews/question-integrity-293'
HERE=AUTH/'attempts/basf-references/attempt-034'
METHOD='scripts/prospectus_question_integrity.py'
TEST='tests/prospectus_successor/test_question_consumer_integrity.py'
PLAN='docs/plans/prospectus-question-integrity-and-source-closure-2026-10-18.md'
SERVICE='src/legalmath/prospectus/successor/service.py'
STAGES=('baseline','reproduce','install','tests','valid','refuse','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
BASE=prior.prior.HERE


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_033_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (METHOD,TEST))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0293.json')
    size=start['prior_resources']['cumulative026_033_bytes']+start['prior_extra_root_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=max(0,(ROOT/SERVICE).stat().st_size-start['service_bytes'])
    assert seconds<3600 and size<380*1024**2,'Cumulative question-integrity resource bound'
    return {'cumulative026_034_measured_seconds':seconds,'cumulative026_034_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':384*1024**2,
        'prior_costs_reset':False,'historical_manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==292
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==33
    assert any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for folder in (BASE,prior.HERE):
        for name,value in read(folder/'outputs.json').items(): assert sha(folder/name)==value,name
    extras=read(prior.HERE/'accounting-addendum.json')['additional_root_files']
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in extras)
    save(PREP/'accounting-start.json',{'prior_resources':prior.costs(),
        'prior_extra_root_bytes':sum(r['bytes'] for r in extras),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'service_bytes':(ROOT/SERVICE).stat().st_size})
    old=(ROOT/SERVICE).read_text()
    anchor='def _bound_report_readings(graph, request, selected):'
    addition='''def _verify_consumed_questions(graph, selected, request, semantic):
    """Check all stored question fields against the declared inference inputs."""
    if digest(semantic['scope']) != digest(request.get('scope', {})):
        raise ValueError('Consumed question scope differs from declared input')
    expected = clause_graph.evaluate(
        semantic['clauses'], selected['assembly'], semantic['scope'],
        semantic['dependencies'], request.get('observations'),
        predicate_engine=request.get('predicate_engine', 'finite'),
        predicate_constraints=request.get('predicate_constraints', ()), source_graph=graph)
    if digest(semantic['questions']) != digest(expected):
        raise ValueError('Consumed question results differ from declared inference')


'''
    assert old.count(anchor)==1 and '_verify_consumed_questions' not in old
    candidate=old.replace(anchor,addition+anchor)
    target="    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}\n"
    assert candidate.count(target)==1
    candidate=candidate.replace(target,target+'    _verify_consumed_questions(graph, selected, interpretation_input, semantic)\n')
    ast.parse(candidate)
    for name,text in (('baseline-service.py',old),('candidate-service.py',candidate)):
        with (PREP/name).open('x') as f:f.write(text)
    bindings={n:sha(ROOT/n) for n in (*CODE,METHOD,TEST,PLAN)}
    for p in (ROOT/'src/legalmath').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p)!=SERVICE:
            bindings[rel(p)]=sha(p)
    for folder in (BASE,prior.HERE):bindings[rel(folder/'outputs.json')]=sha(folder/'outputs.json')
    for name in ('complete-products.json.gz','complete-expected-answer.json.gz','complete-inputs.json'):
        bindings[rel(BASE/name)]=sha(BASE/name)
    bindings.update({rel(p):sha(p) for p in PREP.iterdir() if p.is_file()})
    save(PREP/'freeze.json',{'bindings':bindings,'baseline_service_sha256':sha(PREP/'baseline-service.py'),
        'candidate_service_sha256':sha(PREP/'candidate-service.py'),'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=293
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=[n for n in task['inputs'] if n!=SERVICE]
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Reproduce and repair the frozen complete-question consistency boundary before source-role and historical-law changes',
        question_integrity={'review':rel(PREP),'baseline':rel(BASE),'original_task_complete':False,
            'production_change':'Recompute and compare complete semantic question results; preserve valid answers',
            'cumulative026_onward_seconds':3600,'cumulative026_onward_bytes_with_reserve':384*1024**2})
    proposal['budgets']['basf-references']['maximum_new_attempts']=34
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=293
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=authority_digest(task),
            next_action='Actual full consumer consistency reproduction and repair, then source-role/profile migration and conditional historical-law applications',
            stop_condition='34 admissions;180s stages;3600s cumulative026 onward;384MiB with4MiB reserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].pop(SERVICE,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    resource=costs()
    forecast={'seconds':resource['cumulative026_034_measured_seconds']+330,
        'bytes':resource['cumulative026_034_bytes']+4*(AUTH/'program.json').stat().st_size+8*1024**2,
        'basis':'031 full installed consume82.34s; three full calls and early candidate refusal plus focused tests',
        'estimate_only':True}
    assert forecast['seconds']<3600 and forecast['bytes']<380*1024**2
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Same original task, conditional repair of an actual consumer question-integrity defect',
            'One additional admission33 to34; cumulative time/storage unchanged; all prior evidence retained'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast,
            'repair_conditional_on_actual_reproduction':True,'complete_baseline_not_proxy':True},
        'evidence_contract':{'primary':'Complete031 answer unchanged; actual old consumer accepts altered source uncertainty; repaired consumer refuses it and all declared focused resealed changes',
            'promotion_veto':['Changed complete valid answer','Accepted forged result','Wrong import origin'],
            'continuation_veto':['Corrupt baseline','Method drift','Exhausted limits','Hypothesis not reproduced before install'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Legal semantic correctness','Whole task completion','General build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':33,'new_maximum':34,
            'retained_attempts':attempts,'reason':'Source audit exposed a potentially trusted stored question boundary; reproduce then repair once',
            'next_discriminating_check':'Resealed source-uncertainty omission through actual complete frozen consumer',
            'stop_condition':'180s stages;3600s cumulative;384MiB with4MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continuation of internally supported general build'},
        'original_obligations_preserved':True,'candidate_evaluated':False}
    save(PREP/'resource-forecast.json',forecast);save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':293,'forecast':forecast,'candidate_evaluated':False}


def frozen(repaired=False):
    admission=read(HERE/'admission.json')
    assert authority_digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    freeze=read(PREP/'freeze.json')
    for name,value in freeze['bindings'].items():assert sha(ROOT/name)==value,name
    assert sha(ROOT/SERVICE)==freeze['candidate_service_sha256' if repaired else 'baseline_service_sha256']


def loaded():
    p=read(BASE/'complete-products.json.gz');answer=read(BASE/'complete-expected-answer.json.gz')
    identity=read(BASE/'complete-inputs.json')
    assert digest(p)==identity['products_sha256'] and digest(answer)==identity['answer_sha256']
    return p,answer


def mutate(p):
    from legalmath.prospectus.successor import service
    p=deepcopy(p);bundle=p['P1']['payload']['request']['bundle']
    payload=p['P3']['payload'];q=payload['questions']
    identity='basf-base-september-2022-exchange:p127:l12'
    assert identity in q['Q1']['unresolved']
    q['Q1']['unresolved'].remove(identity)
    q['Q3']['value']['Q1']['unresolved']=deepcopy(q['Q1']['unresolved'])
    p['P3']=service.seal('P3',bundle,p['P3']['inputs'],payload)
    for key in ('P4','P5'):
        p[key]=service.seal(key,bundle,{**p[key]['inputs'],'P3':p['P3']['sha256']},p[key]['payload'])
    for key in p:service.verify(p[key],key)
    return p,identity


def baseline():
    from legalmath.prospectus.successor import service
    p,expected=loaded();observed=service.consume(p,ROOT,mode='frozen')
    assert digest(observed)==digest(expected),'Complete031 baseline mismatch'
    save(HERE/'baseline.json',{'status':'PASS','complete_answer_equal031':True,'answer_sha256':digest(observed)})
    return {'status':'PASS','complete_answer_equal031':True}


def reproduce():
    from legalmath.prospectus.successor import service
    p,expected=loaded();forged,identity=mutate(p)
    observed=service.consume(forged,ROOT,mode='frozen')
    assert identity not in observed['questions']['Q1']['unresolved']
    assert digest(observed)!=digest(expected)
    save(HERE/'reproduction.json',{'status':'PASS','defect_reproduced':True,
        'removed_identifier':identity,'dependent_q3_mirror_adjusted':True,'all_phase_hashes_valid':True,
        'forged_products_sha256':digest(forged),'accepted_answer_sha256':digest(observed),
        'baseline_service_sha256':sha(PREP/'baseline-service.py'),
        'mutation_method':METHOD,'base_products':rel(BASE/'complete-products.json.gz')})
    return {'status':'PASS','actual_old_consumer_accepted_missing_source_uncertainty':True}


def install():
    assert read(HERE/'reproduction.json')['defect_reproduced']
    (ROOT/SERVICE).write_text((PREP/'candidate-service.py').read_text())
    assert sha(ROOT/SERVICE)==sha(PREP/'candidate-service.py')
    return {'status':'PASS','candidate_installed':True}


def tests():
    command=[sys.executable,'-m','pytest','-q',TEST,
        'tests/prospectus_successor/test_closure_consumers.py',
        'tests/prospectus_successor/test_reference_consumer_integrity.py']
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)}
    with (HERE/'regressions.log').open('x') as stream:
        completed=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
    save(HERE/'regressions.json',{'command':command,'returncode':completed.returncode,
        'environment':{'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':env['PYTHONPATH']}})
    assert completed.returncode==0,'Focused regressions failed; retain and review'
    return {'status':'PASS','focused_regressions':True}


def valid():
    from legalmath.prospectus.successor import service
    p,expected=loaded();observed=service.consume(p,ROOT,mode='frozen')
    assert digest(observed)==digest(expected),'Complete valid answer changed'
    save(HERE/'valid.json',{'status':'PASS','complete_answer_equal031':True,'answer_sha256':digest(observed),
        'questions_unchanged':True,'financial_and_law_unchanged':True})
    return {'status':'PASS','complete_answer_equal031':True}


def refuse():
    from legalmath.prospectus.successor import service
    p,_=loaded();forged,identity=mutate(p)
    assert digest(forged)==read(HERE/'reproduction.json')['forged_products_sha256']
    try:service.consume(forged,ROOT,mode='frozen')
    except ValueError as exc:
        assert str(exc)=='Consumed question results differ from declared inference'
        save(HERE/'refusal.json',{'status':'PASS','same_forgery_refused':True,'error':str(exc),
            'removed_identifier':identity,'valid_phase_hashes':True,'forged_products_sha256':digest(forged)})
    else:raise AssertionError('Forged question still accepted')
    return {'status':'PASS','same_actual_consumer_forgery_refused':True}


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'COMPLETE_QUESTION_CONSUMER_CONSISTENCY_REPAIR',
        'reproduction':read(HERE/'reproduction.json'),'valid':read(HERE/'valid.json'),
        'refusal':read(HERE/'refusal.json'),'regressions':read(HERE/'regressions.json'),
        'resources':costs(),'attribution':'Local missing full-question verification; not an external-package limitation',
        'next_action':'Source-role review and explicit profile migration; retain original legal uncertainty and all cumulative bounds',
        'legal_meaning_proved':False,'installed_revalidation_pending':True}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':sha(BASE/'complete-products.json.gz'),
        'wall_time':costs(),'manual_controller_time':'UNKNOWN','plan':PLAN,'result':rel(HERE/'result.json')})
    with (HERE/'RESULT.md').open('x') as f:f.write('''# Frozen question-result consistency repaired

The actual old consumer accepted a missing default(f) source-uncertainty ID after
P3 and dependent phase hashes were regenerated and Q3 was made self-consistent.
The repaired consumer reconstructs every semantic question field from its
declared inference inputs. The complete valid031 answer remains identical and
the identical forgery is refused. Focused real-consumer controls also test
changed uncertainty, reasoning, evidence, scope, subquestions and completeness.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Accept bounded consistency repair | Full valid equality and resealed refusal | No baseline drift or accepted declared forgery | Correctness of supplied legal meanings and broad source scope | Source-role/profile migration, then conditional law; installed revalidation after changes settle | Legal completeness or whole-build completion |

The strongest alternative explanation is a shared error in the evaluator and
its inputs. Equality checks establish internal consistency, not legal truth.
Source analysis and independently stated legal cases remain necessary.
''')
    return {'status':'PASS','original_task_complete':False,'resources':costs()}


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_question_integrity',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Question integrity stage bound')))
    signal.alarm(180)
    try:
        repaired=stage in ('tests','valid','refuse','seal')
        if stage!='prepare':frozen(repaired)
        result=globals()[stage]()
        if stage!='prepare':frozen(repaired or stage=='install')
        costs(time.monotonic()-started)
        result['wall_seconds']=time.monotonic()-started;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
