"""Same-task wheel repair with a reproduced negative baseline."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_definition_applications as prior
from scripts import prospectus_component_revalidation as installed
from legalmath.prospectus.execution_authority import Authority,CODE,digest as authority_digest
from legalmath.prospectus.successor.contracts import digest

AUTH=prior.AUTH
PREP=AUTH/'reviews/definition-package-290'
HERE=AUTH/'attempts/basf-references/attempt-031'
METHOD='scripts/prospectus_definition_package.py'
WORKER='scripts/prospectus_definition_package_worker.py'
PLAN='docs/plans/prospectus-definition-package-repair-2026-10-18.md'
STAGES=('snapshot','baseline-build','baseline-install','baseline-check','install-repair',
        'repaired-build','repaired-install','consume','control','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def package_files(folder):
    return {str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_030_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (METHOD,WORKER,PLAN))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0290.json')
    size=start['prior_resources']['cumulative026_030_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=max(0,(ROOT/'pyproject.toml').stat().st_size-start['pyproject_bytes'])
    assert seconds<3600 and size<316*1024**2,'Cumulative definition delivery resources exhausted'
    return {'cumulative026_031_measured_seconds':seconds,'cumulative026_031_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':320*1024**2,
        'prior_costs_reset':False,'historical_manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['expectation_freeze_command_wall_seconds'],
        'prior_snapshot_sha256':sha(PREP/'accounting-start.json')}


def prepare():
    program=read(AUTH/'program.json')
    assert program['revision']==289
    assert read(prior.HERE/'result.json')['status']=='PASS'
    assert (prior.HERE/'outputs.json').exists()
    for name,value in read(prior.HERE/'outputs.json').items():
        assert sha(prior.HERE/name)==value,name
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==30
    assert any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    save(PREP/'accounting-start.json',{'prior_resources':prior.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'pyproject_bytes':(ROOT/'pyproject.toml').stat().st_size})
    source=(ROOT/'pyproject.toml').read_text()
    pattern='"prospectus/successor/*.json"'
    assert source.count(pattern)==1 and 'prospectus/successor/*.json.gz' not in source
    replacement=source.replace(pattern,pattern+', "prospectus/successor/*.json.gz"')
    for name,value in (('baseline-pyproject.toml',source),('candidate-pyproject.toml',replacement)):
        with (PREP/name).open('x') as stream:
            stream.write(value)
    package=package_files(ROOT/'src/legalmath')
    missing={n:v for n,v in package.items() if n.endswith('.json.gz')}
    assert set(missing)=={'prospectus/successor/definition_scopes_spec.json.gz',
                         'prospectus/successor/definition_applications_spec.json.gz'}
    runtime=installed.runtime()
    assert (runtime/'bin/python').is_file()
    runtime_manifest=installed.runtime_files()
    save(PREP/'package-files.json',package)
    save(PREP/'runtime-files.json',{'path':str(runtime),'files':runtime_manifest})
    for path in (ROOT/METHOD,ROOT/WORKER):
        ast.parse(path.read_text())
    bindings={n:sha(ROOT/n) for n in (*CODE,METHOD,WORKER,PLAN)}
    bindings.update({rel(ROOT/'src/legalmath'/n):value for n,value in package.items()})
    bindings.update({rel(p):sha(p) for p in PREP.iterdir() if p.is_file()})
    bindings[rel(prior.HERE/'outputs.json')]=sha(prior.HERE/'outputs.json')
    # bind the current reconstruction helpers without rerunning sealed stages
    for name in (prior.METHOD,prior.ORACLE,'scripts/prospectus_definition_integration.py',
                 'scripts/prospectus_definition_integration_oracle.py','scripts/prospectus_typed_delta.py',
                 'scripts/prospectus_component_revalidation.py'):
        bindings[name]=sha(ROOT/name)
    save(PREP/'freeze.json',{'bindings':bindings,'runtime_sha256':digest(runtime_manifest),
        'source_sha256':digest(package),'candidate_evaluated':False})
    resources=costs()
    # Two package trees, setuptools build copies and installs; immutable controller
    # copies, compressed complete products and an explicit reserve.
    package_bytes=sum((ROOT/'src/legalmath'/n).stat().st_size for n in package)
    projected_bytes=resources['cumulative026_031_bytes']+6*package_bytes+4*(AUTH/'program.json').stat().st_size+24*1024**2
    projected_seconds=resources['cumulative026_031_measured_seconds']+450
    assert projected_bytes<316*1024**2 and projected_seconds<3600
    save(PREP/'resource-forecast.json',{'status':'PASS','projected_bytes':projected_bytes,
        'projected_measured_seconds':projected_seconds,'source_bytes':package_bytes,
        'estimate_only':True,'baseline_missing_profile_names':list(missing)})
    proposal=deepcopy(program)
    proposal['revision']=290
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=[p for p in task['inputs'] if p!='pyproject.toml']
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+
        [rel(PREP/'freeze.json'),rel(PREP/'resource-forecast.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Reproduce omitted compressed profiles in baseline wheel, repair package data and prove isolated ordinary-answer equivalence',
        definition_package_repair={'review':rel(PREP),'baseline':rel(prior.HERE),
            'original_task_complete':False,'cumulative026_031_seconds':3600,
            'cumulative026_031_bytes_including_4MiB_reserve':320*1024**2,
            'external_calls':0,'production_change':'One reviewed package-data pattern'})
    proposal['budgets']['basf-references']['maximum_new_attempts']=31
    routes=read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=290
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                next_action='Compare negative and repaired wheels with isolated actual consumer; then return to missing-source and historical-law analysis',
                stop_condition='31 admissions;180s stages;3600s cumulative026 onward;320MiB with4MiB reserve;no unchanged retries')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    # Preserve the old configuration as an immutable input; the reviewed worker
    # enforces the live before/after hashes across the single permitted edit.
    proposal['continuation_review']['bindings'].pop('pyproject.toml',None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json'),
        rel(PREP/'baseline-pyproject.toml'):sha(PREP/'baseline-pyproject.toml'),
        rel(PREP/'candidate-pyproject.toml'):sha(PREP/'candidate-pyproject.toml')})
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Repair missing compressed profiles in installed package after source trial',
                   'Retain identical source/complete answers across actual negative and corrected wheels',
                   'Replace the live package-configuration binding with immutable before/after inputs;worker checks exact live transition',
                   'Retain cumulative3600s;storage224 to320MiB for actual wheel comparison;4MiB reserve;no prior cost reset'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),
            'actual_method':WORKER,'method_freeze':rel(PREP/'freeze.json'),
            'wrong_baseline_prevented':'Same protected package tree and complete030 answer; fresh source directories without stale egg-info',
            'environment_control':'Read-only existing runtime hash-bound; every production import must resolve to installed target',
            'proxy_metric_not_primary':True,'resource_forecast':rel(PREP/'resource-forecast.json')},
        'evidence_contract':{'primary':'Two reproduced missing-file failures;all package bytes match;installed complete answer equals030 and resealed forgery refused',
            'promotion_veto':['Missing data','Wrong production import origin','Wrong refusal','Different complete answer'],
            'continuation_veto':['Corrupt inputs','Method drift','Missing result','Exhausted cumulative limits'],
            'explanatory_only':['Build exit code','File counts','Runtime'],
            'not_concluded':['General legal correctness','Portability','Package-wide failure','Whole-build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':30,'new_maximum':31,
            'retained_attempts':attempts,'reason':'Production gzip readers and package-data omission expose a new delivery defect',
            'next_discriminating_check':'Actual baseline wheel failure and corrected installed ordinary consumer',
            'stop_condition':'180s stages;3600s cumulative;320MiB including4MiB reserve;no unchanged retries',
            'same_scope_authorization':'User requested complete general build and internal correctness evidence'},
        'resource_revision':{'prior_seconds':3600,'new_seconds':3600,'prior_bytes':224*1024**2,
            'new_bytes':320*1024**2,'prior_costs_retained':True,'reserve_bytes':4*1024**2},
        'original_obligations_preserved':True,'candidate_evaluated':False}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':290,'candidate_evaluated':False,'resources':costs()}


def frozen(repaired=False):
    admission=read(HERE/'admission.json')
    assert authority_digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name)==value,name
    expected='candidate-pyproject.toml' if repaired else 'baseline-pyproject.toml'
    assert sha(ROOT/'pyproject.toml')==sha(PREP/expected),'Unexpected package configuration'
    assert digest(installed.runtime_files())==read(PREP/'freeze.json')['runtime_sha256']
    for name,value in read(prior.HERE/'outputs.json').items():
        assert sha(prior.HERE/name)==value,name


def execute(stage,command,seconds=150):
    environment={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PIP_NO_INDEX':'1',
                 'PIP_DISABLE_PIP_VERSION_CHECK':'1','PYTHONDONTWRITEBYTECODE':'1'}
    save(HERE/('commands/'+stage+'.json'),{'command':command,'timeout_seconds':seconds,
        'cwd':str(HERE),'environment':{k:environment[k] for k in
            ('CUDA_VISIBLE_DEVICES','PIP_NO_INDEX','PIP_DISABLE_PIP_VERSION_CHECK','PYTHONDONTWRITEBYTECODE')}})
    log=HERE/'commands'/(stage+'.log')
    with log.open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Actual command failed; inspect '+rel(log)


def snapshot():
    package=read(PREP/'package-files.json')
    save(HERE/'package-files.json',package)
    p,answer=prior.retained('assisted-answer')
    assert read(prior.HERE/'assisted-comparison.json')['complete_answer_equal']
    save(HERE/'complete-products.json.gz',p)
    save(HERE/'complete-expected-answer.json.gz',answer)
    save(HERE/'complete-inputs.json',{'products_sha256':digest(p),'answer_sha256':digest(answer),
        'source':rel(prior.HERE/'assisted-answer.json.gz'),'source_file_sha256':sha(prior.HERE/'assisted-answer.json.gz')})
    for label in ('baseline','repaired'):
        folder=HERE/(label+'-source')
        folder.mkdir()
        shutil.copyfile(PREP/('baseline-pyproject.toml' if label=='baseline' else 'candidate-pyproject.toml'),folder/'pyproject.toml')
        shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        assert package_files(folder/'src/legalmath')==package
    return {'status':'PASS','source_files':len(package),'complete_trial_inputs_materialized':True}


def build(label):
    runtime=installed.runtime()/'bin/python'
    execute(label+'-build',[str(runtime),'-I','-B','-m','pip','wheel','--no-deps',
        '--no-build-isolation','--no-index','--wheel-dir',str(HERE/(label+'-wheel')),str(HERE/(label+'-source'))],60)
    wheels=list((HERE/(label+'-wheel')).glob('*.whl'))
    assert len(wheels)==1
    expected=read(PREP/'package-files.json')
    with zipfile.ZipFile(wheels[0]) as archive:
        members={n.removeprefix('legalmath/'):prior.old.hashlib.sha256(archive.read(n)).hexdigest()
                 for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    if label=='baseline':
        expected={k:v for k,v in expected.items() if not k.endswith('.json.gz')}
    assert members==expected,'Wheel bytes differ from reviewed source'
    save(HERE/(label+'-wheel.json'),{'path':rel(wheels[0]),'sha256':sha(wheels[0]),'package':members})
    return {'status':'PASS','label':label,'wheel_source_bytes_match':True,
            'deliberately_reproduced_profile_omissions':2 if label=='baseline' else 0}


def install(label):
    wheel=read(HERE/(label+'-wheel.json'))
    assert sha(ROOT/wheel['path'])==wheel['sha256']
    execute(label+'-install',[str(installed.runtime()/'bin/python'),'-I','-B','-m','pip','install',
        '--no-index','--no-deps','--no-compile','--target',str(HERE/(label+'-installed')),str(ROOT/wheel['path'])],60)
    assert package_files(HERE/(label+'-installed/legalmath'))==wheel['package']
    return {'status':'PASS','label':label,'installed_bytes_match_wheel':True}


def worker(stage):
    label='baseline' if stage=='baseline' else 'repaired'
    execute('installed-'+stage,[str(installed.runtime()/'bin/python'),'-I','-B',str(ROOT/WORKER),
        str(ROOT),str(HERE),str(HERE/(label+'-installed')),stage],165)
    result=read(HERE/('installed-'+stage+'-result.json'))
    assert result['status']=='PASS' and result['isolated']
    return {k:v for k,v in result.items() if k in ('status','stage','complete_answer_equal','actual_consumer_refusals')}


def repair():
    assert len(read(HERE/'installed-baseline-result.json')['missing_profile_failures'])==2
    temporary=ROOT/'pyproject.toml.definition-package-install'
    with temporary.open('xb') as stream:
        stream.write((PREP/'candidate-pyproject.toml').read_bytes())
    temporary.replace(ROOT/'pyproject.toml')
    return {'status':'PASS','configuration_change':'Add compressed successor profiles'}


def seal():
    for stage in STAGES[:-1]:
        assert read(HERE/'stages'/stage/'result.json')['status']=='PASS'
    result={'status':'PASS','task':'basf-references','result_kind':'INSTALLED_DEFINITION_PROFILE_REPAIR',
        'original_task_complete':False,'baseline_missing_profile_failures':2,
        'installed_complete_answer_equal':read(HERE/'installed-consume-result.json')['complete_answer_equal'],
        'installed_actual_consumer_refusals':read(HERE/'installed-control-result.json')['actual_consumer_refusals'],
        'resources':costs(),'attribution':'Local package-data omission; no fundamental external-package failure',
        'next_action':'Return to missing-definition, source-provenance and historical-law analysis'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'actual_subprocess_commands':sorted(rel(p) for p in (HERE/'commands').glob('*.json')),
        'environment':str(installed.runtime()),'cpu_gpu':'CPU; GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':sha(prior.HERE/'outputs.json'),
        'wall_time':result['resources'],'plan':PLAN,'result':rel(HERE/'result.json')})
    with (HERE/'RESULT.md').open('x') as stream:
        stream.write("""# Compressed profiles delivered and consumed from an installed wheel

The unmodified wheel omitted both compressed definition profiles and both
installed readers failed with the expected missing-file errors. Adding the
compressed-profile package-data pattern repairs those omissions. All installed
production bytes match the frozen source. The isolated ordinary consumer
matches the complete retained source-application answer and rejects the
validly resealed changed make-whole meaning.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain packaging repair | Actual baseline failures and complete installed answer comparison pass | No delivery veto | Substantive source meaning and dated law remain | Return to source analysis | General legal correctness, portability or whole-build completion |

This was a local packaging omission. Source-checkout success had not proved
installed delivery. The same source tree and protected answer isolate the
configuration correction; a contrary installed result or changed dependency
runtime would require revalidation.
""")
    return {k:v for k,v in result.items() if k in
        ('status','installed_complete_answer_equal','installed_actual_consumer_refusals','resources','original_task_complete')}


def main():
    assert len(sys.argv)==2
    stage=sys.argv[1]
    if stage=='remaining':
        for name in STAGES:
            folder=HERE/'stages'/name
            if (folder/'result.json').exists():
                assert read(folder/'result.json')['status']=='PASS'
                continue
            assert not (folder/'started.json').exists(),'Unchanged package stage retry refused'
            result=subprocess.run([sys.executable,'-m','scripts.prospectus_definition_package',name],cwd=ROOT,timeout=195)
            if result.returncode:
                raise SystemExit(result.returncode)
        return
    assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged package stage retry refused'
    if stage!='prepare':
        for name in STAGES[:STAGES.index(stage)]:
            assert read(HERE/'stages'/name/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_package',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Definition package stage bound')))
    signal.alarm(180)
    try:
        if stage=='prepare':
            result=prepare()
        else:
            repaired=STAGES.index(stage)>STAGES.index('install-repair')
            frozen(repaired=repaired)
            if stage.endswith('-build'):
                result=build(stage.removesuffix('-build'))
            elif stage.endswith('-install'):
                result=install(stage.removesuffix('-install'))
            elif stage=='baseline-check':
                result=worker('baseline')
            elif stage=='install-repair':
                result=repair()
            elif stage in ('consume','control'):
                result=worker(stage)
            else:
                result=globals()[stage]()
            frozen(repaired=repaired or stage=='install-repair')
        costs(time.monotonic()-started)
        result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal':
            save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(prior.old.json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
