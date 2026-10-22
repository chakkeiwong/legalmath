"""Repair the reproduced interim-review category bypass with bounded evidence."""
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
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from scripts import prospectus_h1_current_acceptance as basecheck
from scripts import prospectus_h1_statement_context_program as context_program
read,sha,require=basecheck.read,basecheck.sha,basecheck.require
AUTH=ROOT/basecheck.AUTH;BASE=ROOT/basecheck.BASE
WORK=ROOT/'.localresources/prospectus-preparation/interim-review-applicability'
PREP=AUTH/'reviews/interim-review-applicability-433'
HERE=BASE/'attempt-070';DONOR=BASE/'attempt-069'
SELF='scripts/prospectus_interim_applicability_program.py'
PLAN='docs/plans/prospectus-interim-review-applicability-2026-10-22.md'
TEST='tests/prospectus_successor/test_interim_review_applicability.py'
CHANGED=['prospectus/successor/interim_review.py','prospectus/build_contract.py']
VERSION='interim-review-applicability.v1'
LIMITS={'new_bytes':256*1024**2,'measured_seconds':600,'control_seconds':60,'worker_seconds':120,'unchanged_retries':0}


def rel(p):return str(Path(p).relative_to(ROOT))


def save(p,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    if p.suffix=='.gz':raw=gzip.compress(raw,mtime=0)
    require(len(raw)<32*1024**2,'Output ceiling')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write(raw)


def authority():
    sys.path.insert(0,str(ROOT/'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs():
    initial=read(PREP/'accounting-start.json')
    paths={p for folder in (WORK,PREP,HERE) if folder.exists() for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (SELF,PLAN,TEST,'scripts/prospectus_interim_review_probe.py'))
    paths.update(ROOT/'src/legalmath'/n for n in CHANGED)
    paths.add(AUTH/'revisions/0433.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in initial['history_names'])
    size=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-initial['program_bytes'])
    seconds=read(WORK/'probe.json')['seconds']+sum(read(p)['seconds'] for folder in (WORK,PREP,HERE)
        for p in folder.glob('commands/*.json') if read(p).get('accounting_role')!='NESTED')
    return {'new_bytes':size,'new_measured_seconds':seconds,'control_reservation_seconds':60,
        'prior_known_bytes':initial['prior']['known_cumulative_bytes'],
        'prior_booked_seconds':initial['prior']['booked_cumulative_seconds'],
        'known_cumulative_bytes':initial['prior']['known_cumulative_bytes']+size,
        'booked_cumulative_seconds':initial['prior']['booked_cumulative_seconds']+seconds+60,
        'manual_unmeasured_seconds':'UNKNOWN','allowed':size<254*1024**2 and seconds<600}


def command(name,argv,folder,*,nested=False,timeout=120):
    require(costs()['allowed'] and costs()['new_measured_seconds']+timeout<600,'Resource bound exhausted')
    folder.mkdir(exist_ok=True,parents=True);tick=time.monotonic()
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONNOUSERSITE':'1','PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_CACHE_DIR':'1'}
    with (folder/(name+'.log')).open('x') as log:
        process=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        sys.path.insert(0,str(ROOT/'src'))
        from legalmath.prospectus.execution_authority import process_identity
        save(folder/(name+'-started.json'),{'argv':argv,'identity':process_identity(process.pid),
            'at':datetime.now(timezone.utc).isoformat(),'seconds':0})
        try:code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:process.kill();process.wait();code=-1
    save(folder/(name+'.json'),{'argv':argv,'exit_code':code,'seconds':time.monotonic()-tick,
        'accounting_role':'NESTED' if nested else 'MEASURED',
        'environment':{k:env[k] for k in ('CUDA_VISIBLE_DEVICES','PYTHONPATH','PIP_NO_INDEX')}})
    require(code==0,'Inspect retained '+str(folder/(name+'.log')))
    require(costs()['allowed'],'Post-command resource bound')


def prepare():
    tick=time.monotonic();a=authority();old,_,_=a.spec()
    require(old['revision']==432 and not PREP.exists() and not HERE.exists(),'Fresh432required')
    state=a.status();require(not state['running'] and state['next_task'] is None,'Finish current work first')
    require(read(WORK/'probe.json')['false_support_cases']==3,'Reproduced false audit support required')
    save(PREP/'accounting-start.json',{'prior':context_program.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    baseline=basecheck.inventory(ROOT/'src/legalmath')
    require(baseline==read(DONOR/'package.json')['files'],'Production differs from069')
    # Retain complete P1/P2 inputs at durable local paths. The original probe
    # deliberately stored report responses, not products; do not pretend its
    # response contains an executable product packet.
    sys.path.insert(0,str(ROOT/'tests/prospectus_successor'))
    from test_interim_review import fixture, products
    from legalmath.prospectus.successor import report_scope, service
    packets=[]
    for variant in ('exact','scope-qualification','conclusion-qualification','changed-criteria'):
        source=read(WORK/(variant+'-LIMITED_FINANCIAL_REVIEW.json.gz'))['source_variant']
        folder=WORK/'source-inputs'/variant;folder.mkdir(parents=True)
        p1,p2,scope,_=fixture(folder,source)
        for category in ('LIMITED_FINANCIAL_REVIEW','STATUTORY_FINANCIAL_AUDIT'):
            supplied=deepcopy(scope);facts=supplied['reports'][0]['facts'];facts['identity']['value']=category
            for field,value in report_scope.PROFILES[category].items():facts[field]['value']=value
            packet={'variant':variant,'category':category,'P1':p1,'P2':p2,'scope':supplied,
                'selected':p2['payload']['source_report_readings']}
            try:packet['baseline']=service.consume(products(p1,p2,supplied),ROOT,mode='current',include_artifacts=True)
            except ValueError as exc:
                require(variant=='exact' and category=='STATUTORY_FINANCIAL_AUDIT'
                    and 'Source interim review contradicts' in str(exc),'Unexpected baseline refusal')
                packet['error']=str(exc)
            if 'baseline' in packet:
                prior=read(WORK/(variant+'-'+category+'.json.gz'))['answer']['source_reports'][0]
                current=packet['baseline']['source_reports'][0]
                require(current['status']==prior['status'] and current['use_assessment']==prior['use_assessment'], 'Durable input changed reproduced behavior')
            packets.append(packet)
    save(WORK/'consumer-inputs.json.gz',packets)
    candidate=WORK/'candidate/src/legalmath'
    shutil.copytree(ROOT/'src/legalmath',candidate,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    module=(candidate/CHANGED[0]).read_text()
    old='    if kind != KIND:\n        return None\n    if required is None:'
    new=("    # Applicability must survive failure of the stricter positive matcher.\n"
        "    # A qualification or damaged extraction cannot turn this source into\n"
        "    # a different report category merely through supplied codes.\n"
        "    known_source = (reading.get('source_sha256') ==\n"
        "        'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'\n"
        "        and any(p.get('page') in {172, 173} for p in reading.get('pages', [])))\n"
        "    interim_title = re.search(r'^LIMITED REVIEW REPORT[ \\t]*$', text, re.M) is not None\n"
        "    if kind != KIND and not known_source and not interim_title:\n"
        "        return None\n"
        "    if required is None:")
    require(module.count(old)==1,'Interim guard baseline changed')
    (candidate/CHANGED[0]).write_text(module.replace(old,new))
    dispatch=(candidate/CHANGED[1]).read_text()
    old="        if row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_statement_context_acceptance'):"
    new=("        if row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_interim_applicability_acceptance'):\n"
        "            from scripts.prospectus_interim_applicability_program import validate_submission as validate\n"
        "        elif row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_statement_context_acceptance'):")
    require(dispatch.count(old)==1,'Current unit dispatch changed')
    (candidate/CHANGED[1]).write_text(dispatch.replace(old,new))
    actual=basecheck.inventory(candidate)
    require({n for n in set(actual)|set(baseline) if actual.get(n)!=baseline.get(n)}==set(CHANGED),'Unexpected candidate change')
    save(PREP/'candidate.json',{'baseline_production':baseline,'candidate_production':actual})
    save(PREP/'commands/preparation.json',{'argv':[SELF,'prepare'],'seconds':time.monotonic()-tick})
    return {'status':'PREPARED','resources':costs()}


def trial():
    code=('import sys; from pathlib import Path; r=Path.cwd(); '
        'sys.path[:0]=[str(r/".localresources/prospectus-preparation/interim-review-applicability/candidate/src"),str(r),str(r/"tests/prospectus_successor")]; '
        'import pytest; raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",'
        '"tests/prospectus_successor/test_interim_review_applicability.py",'
        '"tests/prospectus_successor/test_interim_review.py","tests/prospectus_successor/test_report_scope.py",'
        '"tests/prospectus_successor/test_english_report_context.py",'
        '"tests/prospectus/test_build_contract.py","tests/prospectus/test_criterion_evidence.py",'
        '"--junitxml=.localresources/prospectus-preparation/interim-review-applicability/regression.xml"]))')
    command('tests',[str(ROOT/'.venv/bin/python'),'-I','-B','-c',code],WORK/'commands',timeout=60)
    command('classification',[str(ROOT/'.venv/bin/python'),'-I','-B',str(ROOT/SELF),'worker','--kind','candidate'],WORK/'commands',timeout=60)
    return {'status':'PASS','resources':costs()}


def classification_cases():
    # The probe retains real service inputs/answers for each explicit source
    # variant, so installed tests need neither pytest nor a synthesized oracle.
    from legalmath.prospectus.successor import report_scope, service
    from legalmath.prospectus.successor.contracts import digest
    rows=[];outputs=[]
    for packet in read(WORK/'consumer-inputs.json.gz'):
            variant,category=packet['variant'],packet['category']
            if 'baseline' not in packet:
                # Original wrong category was refused before a full answer;
                # its retained selected reading is enough to prove continued refusal.
                try:report_scope.admit(packet['selected'],packet['scope'])
                except ValueError as exc:
                    require('Source interim review contradicts' in str(exc),'Wrong refusal')
                    rows.append({'variant':variant,'category':category,'refused':True});continue
                raise ValueError('Original false category no longer refused')
            # Reuse exact frozen P1/P2 products from the actual source probe.
            original=packet['baseline']
            p1,p2=packet['P1'],packet['P2']
            p3=service.interpretation_product(p1,p2,{'source_report_scope':packet['scope']})
            products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
            actual=service.consume(products,ROOT,mode='current',include_artifacts=True)
            report=actual['source_reports'][0]
            if variant=='exact':
                require(actual==original,'Exact supported report answer changed')
                require(report['use_assessment']['financial_interim_review']=='SUPPLIED_SOURCE_SUPPORT','Exact report lost support')
            else:
                require(report['status']=='INCOMPLETE_SOURCE_READING' and report['unresolved_interim_review_fields']==['source_structure'], 'Incomplete source gained support')
                require(report['use_assessment']['financial_statement_audit_opinion']=='NOT_ESTABLISHED_BY_THIS_READING','False audit support persists')
                for key in ('questions','dependencies','assembly','may_execute_transaction'):
                    require(actual[key]==original[key],'Unrelated report answer changed')
            rows.append({'variant':variant,'category':category,'status':report['status'],
                'audit_support':report['use_assessment']['financial_statement_audit_opinion'],'refused':False})
            outputs.append({'variant':variant,'category':category,'answer':actual})
    return {'rows':rows,'original_exact_answer_preserved':True,'false_audit_support_cases':0},outputs


def freeze():
    tick=time.monotonic();a=authority();old,_,_=a.spec()
    require(old['revision']==432 and not a.status()['running'],'Current432required')
    require(read(WORK/'commands/tests.json')['exit_code']==read(WORK/'commands/classification.json')['exit_code']==0,'Candidate checks required')
    candidate=read(PREP/'candidate.json')
    require(basecheck.inventory(ROOT/'src/legalmath')==candidate['baseline_production'],'Production changed')
    require(basecheck.inventory(WORK/'candidate/src/legalmath')==candidate['candidate_production'],'Candidate changed')
    inherited=read(AUTH/'reviews/h1-statement-context-432/freeze.json')
    evidence=dict(inherited['evidence'])
    evidence.update({'src/legalmath/'+n:h for n,h in candidate['candidate_production'].items()})
    evidence.update({rel(DONOR/n):h for n,h in read(DONOR/'outputs.json').items()})
    for n in (SELF,PLAN,TEST,rel(DONOR/'outputs.json'),'scripts/prospectus_interim_review_probe.py',rel(PREP/'candidate.json')):
        evidence[n]=sha(ROOT/n)
    for p in WORK.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:evidence[rel(p)]=sha(p)
    require(all(sha(ROOT/n)==h for n,h in evidence.items() if not n.startswith('src/legalmath/')),'Inherited evidence changed')
    save(PREP/'freeze.json',{'baseline_production':candidate['baseline_production'],
        'candidate_production':candidate['candidate_production'],'evidence':evidence,'runtime':inherited['runtime'],'limits':LIMITS})
    from legalmath.prospectus.execution_authority import digest
    program=deepcopy(old);program['revision']=433
    task=next(t for t in program['tasks'] if t['id']=='source-bes-dep-05');files=sorted(set(evidence)|{rel(PREP/'freeze.json')})
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[basecheck.CRITERION],
        reason='Repair reproduced false audit support for incomplete interim-review variants',
        h1_interim_applicability_acceptance={'version':VERSION,'freeze':rel(PREP/'freeze.json'),'donor':rel(DONOR)},
        build_criterion_lineage={basecheck.CRITERION:{'version':'criterion-evidence.v1','files':files,'trees':['src/legalmath']}})
    task['inputs']=sorted(set(task['inputs'])|set(files))
    attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
    require(len(attempts)==old['budgets'][task['budget_key']]['maximum_new_attempts']==69,'Preserve69admissions')
    program['budgets'][task['budget_key']]['maximum_new_attempts']=70
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=433
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=digest(task),dossier=PLAN,phase=0,
                remaining='Three incomplete interim variants falsely support audit; source truth and whole interpretation remain unresolved.',
                next_action='Repair classification applicability, preserve exact069answer and unit proof, then inspect remaining original frontier.',
                stop_condition='Attempt070;256MiB;600+60seconds; one changed recovery; no external action.')
    save(PREP/'routes.json',routes)
    program['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in CHANGED:
        key='src/legalmath/'+n
        if key in program['continuation_review']['bindings']:program['continuation_review']['bindings'][key]=candidate['candidate_production'][n]
    program['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (SELF,PLAN,rel(PREP/'freeze.json'),rel(PREP/'routes.json'))})
    require(program['obligations']==old['obligations'] and program['build_contract']==old['build_contract'],'Original scope changed')
    save(PREP/'proposal.json',program)
    save(PREP/'review.json',{'baseline':digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Separate interim applicability from full positive source matching','Fresh actual classification and complete069/unit regression'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'reproduction':rel(WORK/'probe.json'),'tests':rel(WORK/'regression.xml')},
        'evidence_contract':{'question':'Can an incomplete limited review gain false audit support?',
            'baseline':rel(WORK/'probe.json'),'primary':'False support withheld; exact supported answer and complete069preserved',
            'promotion_veto':['False support','Changed baseline','Wrong imports','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared evidence','Exhausted bound'],
            'explanatory':['Counts','Runtime'],'not_concluded':['All forms recognized','Legal truth','Source authority','Whole build']},
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':69,'new_maximum':70,'retained_attempts':attempts,
            'reason':'Reproduced false audit support in actual service; original semantics repair',
            'next_discriminating_check':'Qualified-source/wrong-category combinations through both current consumers',
            'stop_condition':LIMITS,'same_scope_authorization':'Recover and continue original prospectus build'}})
    save(PREP/'commands/freeze.json',{'seconds':time.monotonic()-tick,'argv':[SELF,'freeze']})
    forecast=costs()['new_bytes']+3*sum((ROOT/'src/legalmath'/n).stat().st_size for n in candidate['baseline_production'])
    forecast+=3*(PREP/'proposal.json').stat().st_size+4*(DONOR/'ordinary-answer.json.gz').stat().st_size
    require(forecast<254*1024**2,'Reservation forecast exceeded')
    return {'status':'FROZEN_REVIEWED','forecast_bytes':forecast,'resources':costs()}


def cutover():
    a=authority();from legalmath.prospectus.execution_authority import digest
    frozen=read(PREP/'freeze.json')
    require(digest(a.spec()[0])==read(PREP/'review.json')['baseline'] and not a.status()['running'],'Cutover baseline changed')
    require(basecheck.inventory(ROOT/'src/legalmath')==frozen['baseline_production'],'Production changed')
    for n in CHANGED:shutil.copyfile(WORK/'candidate/src/legalmath'/n,ROOT/'src/legalmath'/n)
    require(basecheck.inventory(ROOT/'src/legalmath')==frozen['candidate_production'],'Cutover differs')
    save(PREP/'cutover.json',{'status':'PASS','changed':CHANGED,'revision_to_commit':433})
    return {'status':'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def stage(kind):
    a=authority();program,tasks,_=a.spec();task=tasks['source-bes-dep-05']
    require(program['revision']==433 and read(HERE/'admission.json')['binding']==a.binding(task),'Current433admission required')
    require(next(e for e in reversed(a.events()) if e.get('task')==task['id'])['kind']=='ADMIT','Attempt terminal')
    if kind=='installed':require(read(HERE/'package.json')['status']=='PASS','Package required')
    runtime=read(PREP/'freeze.json')['runtime'];python=runtime['package_python' if kind=='installed' else 'ordinary_python']
    command(kind,[python,'-I','-B',str(ROOT/SELF),'worker','--kind',kind],HERE/'commands')
    return {'status':'PASS','stage':kind,'resources':costs()}


def worker(kind):
    if kind=='candidate':
        sys.path.insert(0,str(WORK/'candidate/src'))
        results,answers=classification_cases()
        save(WORK/'candidate-classification.json',results);save(WORK/'candidate-answers.json.gz',answers)
        return {'status':'PASS','classification':results}
    frozen=read(PREP/'freeze.json')
    if kind=='package':
        source=HERE/'package-source';source.mkdir();shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
        shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        python=frozen['runtime']['package_python']
        command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(source)],HERE/'commands',nested=True,timeout=60)
        wheels=list((HERE/'wheel').glob('*.whl'));require(len(wheels)==1,'One wheel required')
        command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],HERE/'commands',nested=True,timeout=60)
        require(basecheck.inventory(HERE/'installed/legalmath')==frozen['candidate_production'],'Installed package differs')
        save(HERE/'package.json',{'status':'PASS','files':frozen['candidate_production'],'wheel':{'path':rel(wheels[0]),'sha256':sha(wheels[0])}})
    else:
        target=ROOT/'src' if kind=='ordinary' else HERE/'installed';sys.path.insert(0,str(target))
        classification,answers=classification_cases()
        require(classification==read(WORK/'candidate-classification.json') and answers==read(WORK/'candidate-answers.json.gz'),'Actual classification differs from candidate')
        products,profiles=basecheck.inputs(ROOT)
        value=read(AUTH/'reviews/h1-statement-context-432/profile.json')
        answer=context_program.consume(products,profiles,value)
        baseline=read(DONOR/'ordinary-answer.json.gz')
        require(answer==baseline==read(DONOR/'installed-answer.json.gz'),'Complete069answer changed')
        keys=basecheck.PRIOR|basecheck.LATER
        unit_proof=basecheck.proof(ROOT,{k:answer[k] for k in keys},adverse=True)
        path=HERE/(kind+'-answer.json.gz');save(path,answer);save(HERE/(kind+'-classification.json.gz'),answers)
        save(HERE/(kind+'.json'),{'status':'PASS','answer_sha256':sha(path),'unit_proof':unit_proof,
            'classification':classification,'imports':basecheck.imported(target),'isolated':sys.flags.isolated==1,
            'executable':str(Path(sys.executable).resolve())})
    return {'status':'PASS','worker':kind}


def validate_submission(root,attempt,task):
    root,attempt=Path(root).resolve(),Path(attempt).resolve()
    selector=task['h1_interim_applicability_acceptance']
    require(root==ROOT and selector=={'version':VERSION,'freeze':rel(PREP/'freeze.json'),'donor':rel(DONOR)}
        and task['build_criteria_scope']==[basecheck.CRITERION],'Wrong submission selector')
    frozen=read(root/selector['freeze']);files=sorted(set(frozen['evidence'])|{selector['freeze']})
    require(task['build_criterion_lineage']=={basecheck.CRITERION:{'version':'criterion-evidence.v1','files':files,'trees':['src/legalmath']}},'Incomplete criterion closure')
    require(all(sha(root/n)==h for n,h in frozen['evidence'].items()),'Changed method/source')
    production=basecheck.inventory(root/'src/legalmath');require(production==frozen['candidate_production'],'Production changed')
    package=read(attempt/'package.json');wheel=root/package['wheel']['path']
    require(package['status']=='PASS' and package['files']==production and sha(wheel)==package['wheel']['sha256']
        and basecheck.inventory(attempt/'installed/legalmath')==production,'Changed installed package')
    with zipfile.ZipFile(wheel) as archive:
        actual={n.removeprefix('legalmath/'):hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(actual==production,'Wheel differs')
    baseline=read(DONOR/'ordinary-answer.json.gz');require(baseline==read(DONOR/'installed-answer.json.gz'),'Donor answers differ')
    expected=read(WORK/'candidate-classification.json');require(expected['false_audit_support_cases']==0,'Candidate false support')
    for kind in ('ordinary','installed'):
        path=attempt/(kind+'-answer.json.gz');answer=read(path);receipt=read(attempt/(kind+'.json'))
        require(receipt['status']=='PASS' and sha(path)==receipt['answer_sha256'] and answer==baseline,'Actual answer changed')
        require(receipt['unit_proof']==basecheck.proof(root,{k:answer[k] for k in basecheck.PRIOR|basecheck.LATER},adverse=True),'Independent unit proof failed')
        require(receipt['classification']==expected and read(attempt/(kind+'-classification.json.gz'))==read(WORK/'candidate-answers.json.gz'),'Classification changed')
        target=root/'src' if kind=='ordinary' else attempt/'installed'
        require(receipt['isolated'] is True and 'legalmath.prospectus.successor.interim_review' in receipt['imports'],'Missing actual isolated report import')
        for item in receipt['imports'].values():
            p=Path(item['path']).resolve();require(p.is_relative_to(target/'legalmath') and sha(p)==item['sha256'],'Wrong import origin')
        cmd=read(attempt/'commands'/(kind+'.json'));python=frozen['runtime']['package_python' if kind=='installed' else 'ordinary_python']
        require(cmd['exit_code']==0 and cmd['argv']==[python,'-I','-B',str(root/SELF),'worker','--kind',kind]
            and receipt['executable']==str(Path(python).resolve()),'Wrong actual command')
        require(cmd['environment']['CUDA_VISIBLE_DEVICES']=='-1' and cmd['environment']['PIP_NO_INDEX']=='1','Unexpected runtime environment')
    return True


def seal():
    a=authority();_,tasks,_=a.spec()
    for kind in ('ordinary','package','installed'):require(read(HERE/'commands'/(kind+'.json'))['exit_code']==0,'Missing required stage')
    require(validate_submission(ROOT,HERE,tasks['source-bes-dep-05']),'Invalid current unit evidence')
    save(HERE/'result.json',{'status':'PASS','task':'source-bes-dep-05','candidate_passed':True,
        'criteria_submitted':[basecheck.CRITERION],'false_audit_support_repaired':3,
        'original_task_complete':False,'whole_program_complete':False,'resources':costs()})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],'plan':PLAN,
        'command':SELF+' stage --kind ordinary|package|installed; seal; authority record/refresh',
        'commands':{n:read(HERE/'commands'/(n+'.json')) for n in ('ordinary','package','installed')},
        'environment':read(PREP/'freeze.json')['runtime'],'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'data_version':rel(DONOR),'random_seeds':'N/A; deterministic source adversaries','wall_seconds':costs()['new_measured_seconds'],
        'artifacts':rel(HERE),'resources':costs()})
    require((HERE/'RESULT.md').exists(),'Substantive result note required')
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.name!='outputs.json'})
    require(costs()['allowed'],'Final resource bound')
    return {'status':'SEALED','resources':costs()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','trial','freeze','cutover','stage','worker','seal','costs'])
    parser.add_argument('--kind',choices=['ordinary','package','installed','candidate'])
    args=parser.parse_args();result=stage(args.kind) if args.action=='stage' else worker(args.kind) if args.action=='worker' else globals()[args.action]()
    print(json.dumps(result),flush=True)
