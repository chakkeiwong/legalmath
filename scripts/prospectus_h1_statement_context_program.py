"""Bounded source-context repair, delivery and current unit revalidation."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from scripts import prospectus_h1_current_acceptance as oldcheck
from scripts import prospectus_h1_statement_context_mapping as mapping
read,sha,require=oldcheck.read,oldcheck.sha,oldcheck.require
AUTH=ROOT/oldcheck.AUTH
BASE=ROOT/oldcheck.BASE
WORK=ROOT/'.localresources/prospectus-preparation/h1-statement-context'
PREP=AUTH/'reviews/h1-statement-context-432'
HERE=BASE/'attempt-069'
DONOR=BASE/'attempt-067'
SELF='scripts/prospectus_h1_statement_context_program.py'
MAPPING='scripts/prospectus_h1_statement_context_mapping.py'
PLAN='docs/plans/prospectus-h1-statement-context-2026-10-22.md'
CHANGED=['prospectus/h1_statement_context.py','prospectus/h1_incorporation_scope.py','prospectus/build_contract.py']
LIMITS={'new_bytes':256*1024**2,'measured_seconds':600,'control_seconds':60,'worker_seconds':120,'unchanged_retries':0}
STAGES=('ordinary','package','installed')


def rel(p): return str(Path(p).relative_to(ROOT))


def save(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    if path.suffix=='.gz': raw=gzip.compress(raw,mtime=0)
    require(len(raw)<32*1024**2,'Bounded file ceiling')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream: stream.write(raw)


def authority():
    sys.path.insert(0,str(ROOT/'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs():
    start=read(PREP/'accounting-start.json')
    paths={p for folder in (WORK,PREP,HERE) if folder.exists() for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (SELF,MAPPING,PLAN))
    paths.update(ROOT/'src/legalmath'/n for n in CHANGED)
    paths.add(AUTH/'revisions/0432.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    records=[read(p) for folder in (PREP,HERE,WORK) for p in folder.glob('commands/*.json')]
    seconds=sum(r['seconds'] for r in records if r.get('accounting_role') not in {'NESTED','UPPER_BOUND'})
    booked=sum(r['seconds'] for r in records if r.get('accounting_role')=='UPPER_BOUND')
    return {'new_bytes':size,'new_measured_seconds':seconds,'control_reservation_seconds':60,
        'prior_known_bytes':start['prior']['known_cumulative_bytes'],
        'prior_booked_seconds':start['prior']['booked_cumulative_seconds'],
        'known_cumulative_bytes':start['prior']['known_cumulative_bytes']+size,
        'booked_unmeasured_upper_bound_seconds':booked,
        'booked_cumulative_seconds':start['prior']['booked_cumulative_seconds']+seconds+booked+60,
        'manual_unmeasured_seconds':'UNKNOWN','allowed':size<254*1024**2 and seconds+booked<600}


def command(name,argv,folder,*,nested=False,timeout=120):
    require(costs()['allowed'] and costs()['new_measured_seconds']+costs()['booked_unmeasured_upper_bound_seconds']+timeout<600,'Resource bound exhausted')
    folder.mkdir(exist_ok=True,parents=True)
    tick=time.monotonic()
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONNOUSERSITE':'1','PYTHONPATH':'','PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_CACHE_DIR':'1'}
    with (folder/(name+'.log')).open('x') as log:
        process=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        # Retain a process identity before polling so restart never blindly repeats it.
        sys.path.insert(0,str(ROOT/'src'))
        from legalmath.prospectus.execution_authority import process_identity
        save(folder/(name+'-started.json'),{'argv':argv,'identity':process_identity(process.pid),
            'at':datetime.now(timezone.utc).isoformat(),'seconds':0})
        try: code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill();process.wait();code=-1
    save(folder/(name+'.json'),{'argv':argv,'exit_code':code,'seconds':time.monotonic()-tick,
        'accounting_role':'NESTED' if nested else 'MEASURED',
        'environment':{k:env[k] for k in ('CUDA_VISIBLE_DEVICES','PYTHONPATH','PIP_NO_INDEX')}})
    require(code==0,'Inspect retained '+str(folder/(name+'.log')))
    require(costs()['allowed'],'Post-command resource bound')


def prepare(recovery=False):
    tick=time.monotonic();a=authority();old,_,_=a.spec()
    require(old['revision']==431 and not HERE.exists(),'Current431required')
    require((not PREP.exists()) if not recovery else ((PREP/'commands/preparation-failed.json').exists()
        and not (PREP/'candidate.json').exists() and not (PREP/'commands/recovery-started.json').exists()),'One changed preparation recovery only')
    state=a.status()
    require(not state['running'] and state['next_task'] is None,'Finish current authority work first')
    if recovery:
        save(PREP/'commands/recovery-started.json',{'seconds':0,'change':'Check management printed_unit versus consolidated unit; original failure retained'})
    else:
        from scripts.prospectus_h1_original_requirements import resources
        save(PREP/'accounting-start.json',{'prior':resources(),
            'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
            'program_bytes':(AUTH/'program.json').stat().st_size})
    require(read(BASE/'attempt-068/result.json')['status']=='PASS','068review required')
    baseline=oldcheck.inventory(ROOT/'src/legalmath')
    require(baseline==read(DONOR/'package.json')['files'],'Current production differs from067')
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    prior=read(DONOR/'ordinary-answer.json.gz')
    require(prior==read(DONOR/'installed-answer.json.gz'),'Baseline answers differ')
    value=mapping.profile(ROOT,graph,prior)
    save(PREP/'profile.json',value)
    module=(WORK/'module-template.py').read_text()
    for token,replacement in {'__MAP__':mapping.compact(value['associations']),
        '__GRAPH__':value['graph_sha256'],'__PRIOR__':value['prior_sha256']}.items():
        require(module.count(token)==1,'Template placeholder changed');module=module.replace(token,replacement)
    wrapper=(ROOT/'src/legalmath/prospectus/h1_incorporation_scope.py').read_text()
    before='            expected_reference_profile_sha256=None):'
    after='            expected_reference_profile_sha256=None, context_profile=None,\n            expected_context_profile_sha256=None):'
    require(wrapper.count(before)==1,'Wrapper signature changed');wrapper=wrapper.replace(before,after)
    before='    prior = h1_risk_tables.consume(products, cash_profile, risk_profile, root,'
    after=("    if context_profile is None and expected_context_profile_sha256 is not None:\n"
        "        raise ValueError('Statement context profile missing for supplied identity')\n"
        "    if context_profile is not None and any(v is None for v in\n"
        "            (unit_profile, relationship_profile, reference_profile, expected_context_profile_sha256)):\n"
        "        raise ValueError('Current unit, relationship and reference profiles required for statement context')\n"+before)
    require(wrapper.count(before)==1,'Wrapper entry changed');wrapper=wrapper.replace(before,after)
    before="    return {**answer, 'h1_reference_availability_review': references,\n            'h1_reference_availability_explanation': h1_reference_availability.explain(references)}"
    after=("    answer = {**answer, 'h1_reference_availability_review': references,\n"
        "              'h1_reference_availability_explanation': h1_reference_availability.explain(references)}\n"
        "    if context_profile is None:\n        return answer\n"
        "    from . import h1_statement_context\n"
        "    context = h1_statement_context.evaluate(products['P1']['payload']['graph'], answer, context_profile,\n"
        "        expected_profile_sha256=expected_context_profile_sha256)\n"
        "    return {**answer, 'h1_statement_context_review': context,\n"
        "            'h1_statement_context_explanation': h1_statement_context.explain(context)}")
    require(wrapper.count(before)==1,'Wrapper result changed');wrapper=wrapper.replace(before,after)
    dispatch=(ROOT/'src/legalmath/prospectus/build_contract.py').read_text()
    before="        if row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_current_unit_acceptance'):"
    after=("        if row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_statement_context_acceptance'):\n"
        "            from scripts.prospectus_h1_statement_context_program import validate_submission as validate\n"
        "        elif row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_current_unit_acceptance'):")
    require(dispatch.count(before)==1,'Unit dispatch changed');dispatch=dispatch.replace(before,after)
    candidate=WORK/'candidate/src/legalmath'
    shutil.copytree(ROOT/'src/legalmath',candidate,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name,text in zip(CHANGED,(module,wrapper,dispatch)):
        (candidate/name).write_text(text)
    actual=oldcheck.inventory(candidate)
    require({n for n in set(baseline)|set(actual) if baseline.get(n)!=actual.get(n)}==set(CHANGED),'Unexpected candidate change')
    save(PREP/'candidate.json',{'baseline_production':baseline,'candidate_production':actual,
        'source_oracle':mapping.source_oracle(graph,prior,value['associations'])})
    save(PREP/'commands/preparation.json',{'seconds':time.monotonic()-tick,'argv':[SELF,'recover' if recovery else 'prepare']})
    return {'status':'CANDIDATE_PREPARED','resources':costs()}


def recover(): return prepare(recovery=True)


def trial():
    command('candidate',[str(ROOT/'.venv/bin/python'),'-I','-B',str(ROOT/SELF),'worker','--kind','candidate'],WORK/'commands')
    return {'status':'CANDIDATE_CHECKED','resources':costs()}


def candidate_worker():
    sys.path.insert(0,str(WORK/'candidate/src'))
    from legalmath.prospectus import h1_statement_context as context
    from legalmath.prospectus import h1_incorporation_scope as public
    from legalmath.prospectus.successor.contracts import digest
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    baseline=read(DONOR/'ordinary-answer.json.gz');value=read(PREP/'profile.json')
    review=context.evaluate(graph,baseline,value,expected_profile_sha256=digest(value))
    answer={**baseline,'h1_statement_context_review':review,'h1_statement_context_explanation':context.explain(review)}
    verification=mapping.verify(ROOT,graph,baseline,answer,value)
    controls=mapping.adverse(graph,baseline,value)
    # These failures occur at the public entry, before any expensive source replay.
    for case,kwargs in [('missing-profile',{'expected_context_profile_sha256':digest(value)}),
        ('missing-prerequisites',{'context_profile':value,'expected_context_profile_sha256':digest(value)})]:
        try: public.consume({},None,None,None,ROOT,expected_cash_profile_sha256=None,
            expected_risk_profile_sha256=None,expected_profile_sha256=None,**kwargs)
        except ValueError as exc: controls.append({'case':case,'refused':True,'reason':str(exc)})
        else: raise ValueError('Public consumer silently dropped context')
    save(WORK/'candidate-check.json',{'status':'PASS','verification':verification,'controls':controls,
        'imports':oldcheck.imported(WORK/'candidate/src')})
    return {'status':'PASS','controls':len(controls)}


def freeze():
    tick=time.monotonic();a=authority();old,tasks,_=a.spec()
    require(old['revision']==431 and not a.status()['running'],'Current431required')
    require(read(WORK/'candidate-check.json')['status']=='PASS','Source candidate must pass')
    require(read(WORK/'commands/regression.json')['exit_code']==0,'Existing build/criterion checks must pass')
    candidate=read(PREP/'candidate.json')
    require(oldcheck.inventory(ROOT/'src/legalmath')==candidate['baseline_production'],'Baseline changed')
    require(oldcheck.inventory(WORK/'candidate/src/legalmath')==candidate['candidate_production'],'Candidate changed')
    inherited=read(AUTH/'reviews/h1-acceptance-lineage-430/freeze.json')
    evidence=dict(inherited['evidence'])
    evidence.update({'src/legalmath/'+n:h for n,h in candidate['candidate_production'].items()})
    for folder in (DONOR,BASE/'attempt-068'):
        evidence.update({rel(folder/n):h for n,h in read(folder/'outputs.json').items()})
        evidence[rel(folder/'outputs.json')]=sha(folder/'outputs.json')
    for n in (SELF,MAPPING,PLAN,rel(PREP/'profile.json'),rel(PREP/'candidate.json'),rel(WORK/'module-template.py'),
        rel(WORK/'candidate-check.json'),rel(WORK/'commands/candidate.json'),rel(WORK/'commands/candidate.log')):
        evidence[n]=sha(ROOT/n)
    for n,h in candidate['candidate_production'].items(): evidence[rel(WORK/'candidate/src/legalmath'/n)]=h
    for p in (WORK/'failed-preparation').glob('*'):evidence[rel(p)]=sha(p)
    for p in (WORK/'commands').glob('*'):evidence[rel(p)]=sha(p)
    evidence[rel(WORK/'regression.xml')]=sha(WORK/'regression.xml')
    evidence[rel(PREP/'commands/preparation-failed.json')]=sha(PREP/'commands/preparation-failed.json')
    require(all(sha(ROOT/n)==h for n,h in evidence.items() if not n.startswith('src/legalmath/')),'Inherited evidence changed')
    save(PREP/'freeze.json',{'baseline_production':candidate['baseline_production'],
        'candidate_production':candidate['candidate_production'],'evidence':evidence,
        'runtime':inherited['runtime'],'limits':LIMITS})
    from legalmath.prospectus.execution_authority import digest
    program=deepcopy(old);program['revision']=432
    task=next(t for t in program['tasks'] if t['id']=='source-bes-dep-05')
    files=sorted(set(evidence)|{rel(PREP/'freeze.json')})
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[oldcheck.CRITERION],
        reason='Deliver exact statement context and groups; revalidate preserved current unit evidence',
        h1_statement_context_acceptance={'version':mapping.VERSION,'freeze':rel(PREP/'freeze.json'),'donor':rel(DONOR)},
        build_criterion_lineage={oldcheck.CRITERION:{'version':'criterion-evidence.v1','files':files,'trees':['src/legalmath']}})
    task['inputs']=sorted(set(task['inputs'])|set(files))
    attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
    require(len(attempts)==old['budgets'][task['budget_key']]['maximum_new_attempts']==68,'Preserve68admissions')
    program['budgets'][task['budget_key']]['maximum_new_attempts']=69
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=432
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=digest(task),dossier=PLAN,phase=0,
                remaining='64context passages and five groups need explicit delivery; source truths and global interpretation remain unresolved.',
                next_action='Deliver reviewed context, revalidate current unit criterion, then return to original source/interpretation frontier.',
                stop_condition='Attempt069;256MiB;600+60seconds; no unchanged retry or external action; finite supplied context only.')
    save(PREP/'routes.json',routes)
    program['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in CHANGED:
        key='src/legalmath/'+n
        if key in program['continuation_review']['bindings']:program['continuation_review']['bindings'][key]=candidate['candidate_production'][n]
    program['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (SELF,MAPPING,PLAN,rel(PREP/'freeze.json'),rel(PREP/'routes.json'))})
    require(program['obligations']==old['obligations'] and program['build_contract']==old['build_contract'],'Original scope changed')
    save(PREP/'proposal.json',program)
    save(PREP/'review.json',{'baseline':digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Exact64source associations and five group memberships','Fresh ordinary/installed current unit proof after production changes'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'candidate_check':rel(WORK/'candidate-check.json'),
            'external_opinion_required':False,'source_counts_not_semantics':True},
        'evidence_contract':{'question':'Do exact statement contexts reach the full current public answer without changing its meanings?',
            'baseline':rel(DONOR),'primary':'Exact source/target/groups and complete baseline preservation in both environments with unit oracle',
            'promotion_veto':['Wrong source/group/unit','Changed previous answer','Accepted corruption','Wrong imports'],
            'continuation_veto':['Invalid authority','Corrupt shared evidence','Exhausted bound'],
            'explanatory':['Counts','Runtime'],'not_concluded':['Source truth','Intended unit','Global meaning','Whole source completion']},
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':68,'new_maximum':69,'retained_attempts':attempts,
            'reason':'Repair concrete068context omissions under original source task',
            'next_discriminating_check':'Actual public metadata/group delivery with preserved independent unit proof',
            'stop_condition':LIMITS,'same_scope_authorization':'Recover and continue original prospectus build'}})
    save(PREP/'commands/freeze.json',{'seconds':time.monotonic()-tick,'argv':[SELF,'freeze']})
    forecast=costs()['new_bytes']+3*sum((ROOT/'src/legalmath'/n).stat().st_size for n in candidate['baseline_production'])
    forecast+=3*(PREP/'proposal.json').stat().st_size+4*(DONOR/'ordinary-answer.json.gz').stat().st_size
    require(forecast<254*1024**2,'Forecast exceeds reservation')
    return {'status':'FROZEN_REVIEWED','revision':432,'forecast_bytes':forecast,'resources':costs()}


def cutover():
    a=authority();from legalmath.prospectus.execution_authority import digest
    frozen=read(PREP/'freeze.json')
    require(digest(a.spec()[0])==read(PREP/'review.json')['baseline'] and not a.status()['running'],'Cutover baseline changed')
    require(oldcheck.inventory(ROOT/'src/legalmath')==frozen['baseline_production'],'Production changed')
    for n in CHANGED:shutil.copyfile(WORK/'candidate/src/legalmath'/n,ROOT/'src/legalmath'/n)
    require(oldcheck.inventory(ROOT/'src/legalmath')==frozen['candidate_production'],'Cutover differs')
    save(PREP/'cutover.json',{'status':'PASS','changed':CHANGED,'revision_to_commit':432})
    return {'status':'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def consume(products,profiles,value):
    from legalmath.prospectus import h1_incorporation_scope
    from legalmath.prospectus.successor.contracts import digest
    return h1_incorporation_scope.consume(products,profiles['cash'],profiles['risk'],profiles['scope'],ROOT,
        expected_cash_profile_sha256=digest(profiles['cash']),expected_risk_profile_sha256=digest(profiles['risk']),
        expected_profile_sha256=digest(profiles['scope']),unit_profile=profiles['unit'],expected_unit_profile_sha256=digest(profiles['unit']),
        relationship_profile=profiles['relationships'],expected_relationship_profile_sha256=digest(profiles['relationships']),
        reference_profile=profiles['references'],expected_reference_profile_sha256=digest(profiles['references']),
        context_profile=value,expected_context_profile_sha256=digest(value))


def stage(kind):
    a=authority();program,tasks,_=a.spec();task=tasks['source-bes-dep-05']
    require(program['revision']==432 and read(HERE/'admission.json')['binding']==a.binding(task),'Current432admission required')
    require(next(e for e in reversed(a.events()) if e.get('task')==task['id'])['kind']=='ADMIT','Attempt already terminal')
    if kind=='installed':require(read(HERE/'package.json')['status']=='PASS','Package required')
    runtime=read(PREP/'freeze.json')['runtime']
    python=runtime['package_python' if kind=='installed' else 'ordinary_python']
    command(kind,[python,'-I','-B',str(ROOT/SELF),'worker','--kind',kind],HERE/'commands')
    return {'status':'PASS','stage':kind,'resources':costs()}


def worker(kind):
    if kind=='candidate':return candidate_worker()
    frozen=read(PREP/'freeze.json')
    if kind=='package':
        source=HERE/'package-source';source.mkdir()
        shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
        shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        python=frozen['runtime']['package_python']
        command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
            '--wheel-dir',str(HERE/'wheel'),str(source)],HERE/'commands',nested=True,timeout=60)
        wheels=list((HERE/'wheel').glob('*.whl'));require(len(wheels)==1,'One wheel required')
        command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
            '--target',str(HERE/'installed'),str(wheels[0])],HERE/'commands',nested=True,timeout=60)
        require(oldcheck.inventory(HERE/'installed/legalmath')==frozen['candidate_production'],'Installed package differs')
        save(HERE/'package.json',{'status':'PASS','files':frozen['candidate_production'],'wheel':{'path':rel(wheels[0]),'sha256':sha(wheels[0])}})
    else:
        target=ROOT/'src' if kind=='ordinary' else HERE/'installed'
        sys.path.insert(0,str(target))
        products,profiles=oldcheck.inputs(ROOT);value=read(PREP/'profile.json')
        answer=consume(products,profiles,value)
        baseline=read(DONOR/'ordinary-answer.json.gz')
        if kind=='ordinary':
            require(oldcheck.consume(ROOT,products,profiles)==baseline,'Existing public call changed without context profile')
        verification=mapping.verify(ROOT,products['P1']['payload']['graph'],baseline,answer,value)
        projection={k:answer[k] for k in baseline}
        proof=oldcheck.proof(ROOT,projection,adverse=True)
        path=HERE/(kind+'-answer.json.gz');save(path,answer)
        save(HERE/(kind+'.json'),{'status':'PASS','answer_sha256':sha(path),'verification':verification,
            'unit_proof':proof,'imports':oldcheck.imported(target),'isolated':sys.flags.isolated==1,
            'executable':str(Path(sys.executable).resolve())})
    return {'status':'PASS','worker':kind}


def validate_submission(root,attempt,task):
    root,attempt=Path(root).resolve(),Path(attempt).resolve()
    selector=task['h1_statement_context_acceptance']
    require(root==ROOT and selector=={'version':mapping.VERSION,'freeze':rel(PREP/'freeze.json'),'donor':rel(DONOR)}
        and task['build_criteria_scope']==[oldcheck.CRITERION],'Wrong current context submission')
    frozen=read(root/selector['freeze'])
    files=sorted(set(frozen['evidence'])|{selector['freeze']})
    require(task['build_criterion_lineage']=={oldcheck.CRITERION:{'version':'criterion-evidence.v1','files':files,'trees':['src/legalmath']}},'Incomplete criterion evidence closure')
    require(all(sha(root/n)==h for n,h in frozen['evidence'].items()),'Changed source or method')
    production=oldcheck.inventory(root/'src/legalmath')
    require(production==frozen['candidate_production'],'Changed production')
    package=read(attempt/'package.json');wheel=root/package['wheel']['path']
    require(package['status']=='PASS' and package['files']==production and sha(wheel)==package['wheel']['sha256']
        and oldcheck.inventory(attempt/'installed/legalmath')==production,'Installed package differs')
    with zipfile.ZipFile(wheel) as archive:
        actual={n.removeprefix('legalmath/'):hashlib.sha256(archive.read(n)).hexdigest()
            for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(actual==production,'Wheel differs from reviewed source')
    products,_=oldcheck.inputs(root);value=read(PREP/'profile.json')
    baseline=read(DONOR/'ordinary-answer.json.gz')
    require(baseline==read(DONOR/'installed-answer.json.gz'),'Donor answers differ')
    answers=[]
    for kind in ('ordinary','installed'):
        path=attempt/(kind+'-answer.json.gz');answer=read(path);receipt=read(attempt/(kind+'.json'))
        require(receipt['status']=='PASS' and sha(path)==receipt['answer_sha256'],'Changed actual result')
        require(receipt['verification']==mapping.verify(root,products['P1']['payload']['graph'],baseline,answer,value),'Changed context verification')
        require(receipt['unit_proof']==oldcheck.proof(root,{k:answer[k] for k in baseline},adverse=True),'Independent unit proof failed')
        target=root/'src' if kind=='ordinary' else attempt/'installed'
        require(receipt['isolated'] is True and 'legalmath.prospectus.h1_statement_context' in receipt['imports'],'Missing actual isolated context import')
        for item in receipt['imports'].values():
            p=Path(item['path']).resolve()
            require(p.is_relative_to(target/'legalmath') and sha(p)==item['sha256'],'Wrong import origin')
        cmd=read(attempt/'commands'/(kind+'.json'))
        python=frozen['runtime']['package_python' if kind=='installed' else 'ordinary_python']
        require(cmd['exit_code']==0 and cmd['argv']==[python,'-I','-B',str(root/SELF),'worker','--kind',kind]
            and receipt['executable']==str(Path(python).resolve()),'Wrong actual invocation')
        require(cmd['environment']['CUDA_VISIBLE_DEVICES']=='-1' and cmd['environment']['PIP_NO_INDEX']=='1','Unexpected execution environment')
        answers.append(answer)
    require(answers[0]==answers[1],'Ordinary and installed answers differ')
    return True


def seal():
    a=authority();_,tasks,_=a.spec()
    for kind in STAGES:require(read(HERE/'commands'/(kind+'.json'))['exit_code']==0,'Missing required stage')
    require(validate_submission(ROOT,HERE,tasks['source-bes-dep-05']),'Current unit submission invalid')
    save(HERE/'result.json',{'status':'PASS','task':'source-bes-dep-05','candidate_passed':True,
        'criteria_submitted':[oldcheck.CRITERION],'source_associations':64,'explicit_groups':5,
        'original_task_complete':False,'whole_program_complete':False,'resources':costs()})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],'plan':PLAN,
        'command':SELF+' stage --kind ordinary|package|installed; seal; authority record/refresh',
        'commands':{n:read(HERE/'commands'/(n+'.json')) for n in STAGES},
        'environment':read(PREP/'freeze.json')['runtime'],'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'data_version':rel(DONOR),'random_seeds':'N/A; deterministic source interpretation',
        'wall_seconds':costs()['new_measured_seconds'],'artifacts':rel(HERE),'resources':costs()})
    require((HERE/'RESULT.md').exists(),'Substantive result note required')
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.name!='outputs.json'})
    require(costs()['allowed'],'Final resource bound')
    return {'status':'SEALED','resources':costs()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','recover','trial','freeze','cutover','stage','worker','seal','costs'])
    parser.add_argument('--kind',choices=[*STAGES,'candidate'])
    args=parser.parse_args()
    result=stage(args.kind) if args.action=='stage' else worker(args.kind) if args.action=='worker' else globals()[args.action]()
    print(json.dumps(result),flush=True)
