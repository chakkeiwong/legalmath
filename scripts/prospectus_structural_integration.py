"""Admitted structural-context integration with cumulative retained evidence."""
from copy import deepcopy
from datetime import datetime,timezone
import ast
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import zipfile

os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_structural_candidate as c
from scripts import prospectus_structural_oracle as oracle
from scripts.prospectus_typed_delta import changes,apply,equal
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH,PREP,HERE,BASE,PLAN=c.AUTH,c.PREP,c.HERE,c.BASE,c.PLAN
read,save,sha,rel=c.read,c.save,c.sha,c.rel
METHOD='scripts/prospectus_structural_integration.py'
WORKER='scripts/prospectus_structural_installed.py'
TEST='tests/prospectus_successor/test_structural_context.py'
ROOT_FILES=[METHOD,WORKER,TEST,'scripts/prospectus_structural_candidate.py',
            'scripts/prospectus_structural_oracle.py',PLAN,
            'docs/plans/prospectus-structural-reference-context-2026-10-18.md']
STAGES=('install','tests','legacy','construction','interpretation','downstream','consume',
        'controls-role','controls-question','controls-reference','package','installed','seal')


def package_files(folder):
    return {str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_035_measured_seconds']+extra
    seconds+=sum(read(PREP/n)['wall_seconds'] for n in ('preparation-result.json','prediction-result.json'))
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in ROOT_FILES)
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0295.json')
    size=start['prior_resources']['cumulative026_035_bytes']+start['prior_extra_bytes']
    size+=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    for row in read(PREP/'candidate-manifest.json')['files']:
        target=ROOT/row['target'];before=PREP/'baseline'/target.name
        if target.exists():size+=max(0,target.stat().st_size-(before.stat().st_size if before.exists() else 0))
    assert seconds<5400 and size<508*1024**2,'Cumulative structural integration bound'
    return {'cumulative026_036_measured_seconds':seconds,'cumulative026_036_bytes':size,
        'seconds_bound':5400,'bytes_bound_including_4MiB_reserve':512*1024**2,
        'prior_costs_reset':False,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==294
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==35 and any(e['kind']=='RECORD' and e.get('attempt')==rel(c.prior.HERE) for e in events)
    for name,value in read(c.prior.HERE/'outputs.json').items():assert sha(c.prior.HERE/name)==value,name
    extras=read(c.prior.HERE/'accounting-addendum.json')['extra_root_files']
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in extras)
    manifest=read(PREP/'candidate-manifest.json')
    for row in manifest['files']:
        target=ROOT/row['target'];assert (sha(target) if target.exists() else None)==row['before_sha256']
        row['after_sha256']=sha(ROOT/row['candidate'])
        if target.suffix=='.py':ast.parse((ROOT/row['candidate']).read_text())
    (PREP/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save(PREP/'accounting-start.json',{'prior_resources':c.prior.costs(),
        'prior_extra_bytes':sum(r['bytes'] for r in extras),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    targets={r['target'] for r in manifest['files']}
    bindings={n:sha(ROOT/n) for n in (*CODE,*ROOT_FILES,'pyproject.toml')}
    for path in (ROOT/'src/legalmath').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc' and rel(path) not in targets:
            bindings[rel(path)]=sha(path)
    for n in ('complete-products.json.gz','complete-expected-answer.json.gz','complete-inputs.json','outputs.json'):bindings[rel(BASE/n)]=sha(BASE/n)
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings[rel(c.prior.HERE/'outputs.json')]=sha(c.prior.HERE/'outputs.json')
    save(PREP/'freeze.json',{'bindings':bindings,'targets':manifest['files']})
    proposal=deepcopy(program);proposal['revision']=295
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=[n for n in task['inputs'] if n not in targets]
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Integrate exact structural roles without truncating complete reference context; retain substantive uncertainty',
        structural_context_integration={'review':rel(PREP),'baseline':rel(BASE),'original_task_complete':False,
            'seconds_bound_cumulative026':5400,'bytes_bound_including_4MiB_reserve':512*1024**2,
            'stages':list(STAGES),'external_adviser_prerequisite':False})
    proposal['budgets']['basf-references']['maximum_new_attempts']=36
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=295
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Complete source/context role integration and installed validation, then remaining conditional meanings and historical-law applications',
            stop_condition='36 admissions;180s stages;5400s cumulative026 onward;512MiB including4MiB reserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in targets:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    package_bytes=sum(p.stat().st_size for p in (ROOT/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    resource=costs();forecast={'measured_seconds':resource['cumulative026_036_measured_seconds']+1400,
        'bytes':resource['cumulative026_036_bytes']+3*(AUTH/'program.json').stat().st_size+3*package_bytes+16*1024**2,
        'basis':'Complete consumer03495s; migrated checks and installation with bounded correction reserve','estimate_only':True}
    assert forecast['measured_seconds']<5400 and forecast['bytes']<508*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Same original task with exact full reference-context contract','Preserve all prior costs;3600 to5400seconds;384 to512MiB;35 to36 admissions'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast,
            'predictions_retained_before_candidate':read(PREP/'prediction-result.json')},
        'evidence_contract':{'primary':'Full independently predicted products/answer equality, unchanged legacy consumer, resealed refusal and isolated installed replay',
            'promotion_veto':['Lost complete target context','Altered substantive source or uncertainty','Changed financial/law payload','Accepted forgery'],
            'continuation_veto':['Corrupt source','Frozen-method drift','Unexplained delta','Exhausted cumulative bound'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Legal completeness','Automatic source classification','General build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':35,'new_maximum':36,'retained_attempts':attempts,
            'reason':'Source-reviewed headings require a coordinated complete-reference migration, not target truncation',
            'next_discriminating_check':'Exact predicted full consumer delta and refusal of altered complete reference context',
            'stop_condition':'180s stages;5400s cumulative;512MiB with4MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued internally supported general build'}}
    save(PREP/'resource-forecast.json',forecast);save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':295,'forecast':forecast,'candidate_evaluated':False}


def frozen(installed):
    admission=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    freeze=read(PREP/'freeze.json')
    for name,value in freeze['bindings'].items():assert sha(ROOT/name)==value,name
    for row in freeze['targets']:
        path=ROOT/row['target'];assert (sha(path) if path.exists() else None)==row['after_sha256' if installed else 'before_sha256'],row['target']


def retain(name,p,answer=None):
    base,old=oracle.baseline();value={'products_delta':changes(base,p),'products_sha256':digest(p)}
    if answer is not None:value.update(answer_delta=changes(old,answer),answer_sha256=digest(answer))
    save(HERE/(name+'.json.gz'),value)


def retained(name):
    base,old=oracle.baseline();value=read(HERE/(name+'.json.gz'));p=apply(base,value['products_delta'])
    assert digest(p)==value['products_sha256']
    a=apply(old,value['answer_delta']) if 'answer_delta' in value else None
    assert a is None or digest(a)==value['answer_sha256']
    return p,a


def execute(label,command,seconds=150,cwd=None):
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1',
         'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)}
    save(HERE/('commands/'+label+'.json'),{'command':command,'cwd':str(cwd or ROOT),'seconds_bound':seconds,
        'cpu_gpu':'CPU; GPU intentionally hidden'})
    with (HERE/'commands'/(label+'.log')).open('x') as f:
        r=subprocess.run(command,cwd=cwd or ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=seconds)
    assert r.returncode==0,'Inspect retained '+label+' log'


def install():
    for row in read(PREP/'candidate-manifest.json')['files']:
        (ROOT/row['target']).write_bytes((ROOT/row['candidate']).read_bytes())
    return {'status':'PASS','installed_candidate_files':10}


def tests():
    names=[TEST,'tests/prospectus_successor/test_reference_unknown_targets.py',
        'tests/prospectus_successor/test_question_consumer_integrity.py',
        'tests/prospectus_successor/test_reference_consumer_integrity.py',
        'tests/prospectus_successor/test_basf_substitution_references.py',
        'tests/prospectus_successor/test_basf_financial_references.py',
        'tests/prospectus_successor/test_basf_internal_references.py',
        'tests/prospectus_successor/test_closure_consumers.py']
    execute('tests',[sys.executable,'-m','pytest','-q',*names],150)
    return {'status':'PASS','focused_regressions':True,'log':rel(HERE/'commands/tests.log')}


def legacy():
    from legalmath.prospectus.successor import service
    p,a=oracle.baseline();actual=service.consume(p,ROOT,mode='frozen');equal(actual,a,'Legacy complete answer changed')
    save(HERE/'legacy.json',{'status':'PASS','answer_sha256':digest(actual),'complete_answer_equal031':True})
    return {'status':'PASS','complete_legacy_answer_unchanged':True}


def construction():
    from legalmath.prospectus.successor import service
    expected,_=oracle.retained();base,_=oracle.baseline();p=dict(base);p['P1']=expected['P1']
    p['P2']=service.construction_product(p['P1'],ROOT)
    equal(p['P2'],expected['P2'],'Actual construction differs from independent role prediction')
    retain('construction',p)
    return {'status':'PASS','actual_construction_equal':True}


def interpretation():
    from legalmath.prospectus.successor import service
    expected,_=oracle.retained();p,_=retained('construction')
    p['P3']=service.interpretation_product(p['P1'],p['P2'],expected['P3']['payload']['interpretation_input'])
    retain('interpretation',p)
    equal(p['P3'],expected['P3'],'Actual complete interpretation differs from independent prediction')
    return {'status':'PASS','actual_complete_interpretation_equal':True}


def downstream():
    from legalmath.prospectus.successor import service
    expected,_=oracle.retained();p,_=retained('interpretation');law,finance=p['P4']['payload'],p['P5']['payload']
    p['P4']=service.law_product(p['P1'],p['P3'],law['cases'],law['law_input'])
    p['P5']=service.financial_product(p['P1'],p['P2'],p['P3'],finance['cases'],finance['scenario_input'])
    retain('products',p);equal(p,expected,'Complete predicted products differ')
    return {'status':'PASS','complete_products_equal':True,'protected_law_finance_unchanged':True}


def consume():
    from legalmath.prospectus.successor import service
    p,_=retained('products');_,expected=oracle.retained();actual=service.consume(p,ROOT,mode='frozen')
    retain('answer',p,actual);equal(actual,expected,'Complete ordinary answer differs from prediction')
    return {'status':'PASS','complete_answer_equal_prediction':True,'answer_sha256':digest(actual)}


def controls(kind):
    from legalmath.prospectus.successor import service
    p,_=retained('products');p=deepcopy(p);identity='basf-base-september-2022-exchange:p127:l12'
    if kind=='role':
        unit=next(u for u in p['P2']['payload']['assembly']['units'] if u['unit']==identity);unit['role']='HEADER'
    elif kind=='question':
        q=p['P3']['payload']['questions'];q['Q1']['unresolved'].remove(identity);q['Q3']['value']['Q1']['unresolved']=deepcopy(q['Q1']['unresolved'])
    elif kind=='reference':
        ref=next(d for d in p['P3']['payload']['dependencies'] if d.get('structural_targets'));ref['structural_targets']=[]
    else:raise ValueError(kind)
    bundle=p['P1']['payload']['request']['bundle']
    p['P2']=service.seal('P2',bundle,{'P1':p['P1']['sha256']},p['P2']['payload'])
    p['P3']=service.seal('P3',bundle,{'P1':p['P1']['sha256'],'P2':p['P2']['sha256']},p['P3']['payload'])
    for key,parents in [('P4',('P1','P3')),('P5',('P2','P3'))]:p[key]=service.seal(key,bundle,{k:p[k]['sha256'] for k in parents},p[key]['payload'])
    for key in p:service.verify(p[key],key)
    try:service.consume(p,ROOT,mode='frozen')
    except ValueError as exc:
        expected={'role':'Structural role review or complete selected assembly changed',
            'question':'Consumed question results differ from declared inference',
            'reference':'Consumed BASF substitution dependencies differ from source review'}
        assert str(exc)==expected[kind],str(exc)
        save(HERE/('control-'+kind+'.json'),{'status':'PASS','all_phase_hashes_valid':True,'error':str(exc),'products_sha256':digest(p)})
    else:raise AssertionError('Resealed forgery accepted: '+kind)
    return {'status':'PASS','actual_complete_consumer_refused':kind}


def package():
    from scripts.prospectus_component_revalidation import runtime
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=package_files(folder/'src/legalmath');assert expected==package_files(ROOT/'src/legalmath')
    python=str(runtime()/'bin/python')
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60,HERE)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    import hashlib
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected,'Wheel differs from reviewed package source'
    execute('package-install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60,HERE)
    assert package_files(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'package':expected,'wheel_sha256':sha(wheels[0]),'python':python,'isolated_target':rel(HERE/'installed')})
    return {'status':'PASS','wheel_and_installed_bytes_equal':True,'files':len(expected)}


def installed():
    execute('installed-consume',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],165,HERE)
    result=read(HERE/'installed-result.json');assert result['status']=='PASS'
    return result


def seal_result():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_STRUCTURAL_CONTEXT_INTEGRATION','prediction':read(PREP/'prediction.json'),
        'complete_legacy_equal':True,'complete_candidate_equal':True,'complete_installed_equal':True,
        'controls':[read(HERE/('control-'+k+'.json')) for k in ('role','question','reference')],
        'resources':costs(),'attribution':'Local role/context representation gap; not evidence of an external package defect',
        'next_action':'Continue retained substantive meanings and conditional historical statutory applications',
        'legal_completeness':False,'automatic_heading_recognition':False}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden','random_seeds':'N/A deterministic',
        'data_version':sha(BASE/'complete-products.json.gz'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    with (HERE/'RESULT.md').open('x') as f:f.write('''# Exact structural context reaches the ordinary consumer

The finite44-role correction preserves all selected text and every complete
reference target. Four links retain18 structural targets separately from their
substantive destinations. Twelve section-number discovery dependencies and14
wholly structural clauses leave operative inference. Five mixed-node residuals
remain UNKNOWN. The independently predicted74 uncertainty-ID reduction is an
accounting consequence, not legal completeness. Default(f), calculation-agent,
financial, statutory and other substantive uncertainties remain protected.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain exact optional source-role integration | Full predicted product/answer equality; legacy and isolated installed replay; resealed refusal | No unexplained delta or declared accepted forgery | Supplied source reading and uncompleted substantive law/meaning | Continue substantive source analysis | General heading recognition or completed build |

The strongest alternative explanation is a shared source-reading mistake. This
implementation proves exact propagation and conditional consistency; it does
not establish every supplied legal meaning or exhaust the original obligations.
''')
    return {'status':'PASS','original_task_complete':False,'resources':costs()}


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_structural_integration',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':180})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Structural integration stage bound')));signal.alarm(180)
    try:
        if stage!='prepare':frozen(stage!='install')
        if stage.startswith('controls-'):result=controls(stage.removeprefix('controls-'))
        elif stage=='seal':result=seal_result()
        else:result=globals()[stage]()
        if stage!='prepare':frozen(True)
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
