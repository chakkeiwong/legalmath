"""Complete unchanged Note 27 integration in bounded durable consumer steps."""
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
from scripts import prospectus_h1_associates_storage_repair as source
from scripts import prospectus_h1_statement_consumer as common

read,save,sha,digest=source.read,source.save,source.sha,source.digest
same,require,rel=source.same,source.require,source.rel
AUTH=source.AUTH;BASE=source.BASE;PRODUCTION=source.PRODUCTION
HERE=BASE/'attempt-044'
PREP=AUTH/'reviews/h1-bounded-consumer-407'
SELF='scripts/prospectus_h1_bounded_consumer.py'
PLAN='docs/plans/prospectus-h1-bounded-consumer-2026-10-21.md'
KEYS={21:'h1_normal_statement_consumer',22:'h1_debt_context_consumer',23:'h1_debt_securities_consumer',
    24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',
    29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',
    33:'h1_income_collateral_consumer',35:'h1_afs_disclosures_consumer',36:'h1_critical_judgments_consumer',
    37:'h1_trading_balances_consumer',39:'h1_related_parties_consumer',41:'h1_group_structure_consumer'}
DEPENDENCIES={'adopt':[],'baseline':['adopt'],'ordinary':['adopt'],
    'compare':['baseline','ordinary'],'composition':['compare'],'controls':['compare'],
    'package':['composition','controls'],'installed':['package'],
    'installed-compare':['installed','compare'],'installed-composition':['installed-compare','composition'],
    'installed-controls':['installed-compare','controls'],'coverage':[]}


def object_parts(encoded_values):
    """Yield exactly common.encoded's bytes, retaining nested chunk sequences."""
    yield b'{'
    for index,key in enumerate(sorted(encoded_values)):
        if index:yield b', '
        yield common.encoded(key);yield b': '
        value=encoded_values[key]
        if isinstance(value,bytes):yield value
        else:yield from value
    yield b'}'


def parts_digest(parts):
    hasher=hashlib.sha256()
    for part in parts:hasher.update(part)
    return hasher.hexdigest()


def equivalence():
    cases=[{}, {'z':[1,-2,3.25,None,False],'á':'Espírito\nSanto','a':{'é':'\u0000"\\','x':[]}},
           {'source_statement_cells':{'nested':[{'b':2,'a':1}]},'artifacts':{'k':'value'}},
           {'0':-0.0,'max':12345678901234567890}]
    for value in cases:
        encoded={k:common.encoded(v) for k,v in value.items()}
        chunks=tuple(object_parts(encoded))
        require(b''.join(chunks)==common.encoded(value),'Changed JSON representation')
        require(parts_digest(chunks)==digest(value),'Changed dictionary digest')
        nested={'outer':chunks,'unicode':common.encoded('Ó €')}
        whole={'outer':value,'unicode':'Ó €'}
        require(b''.join(object_parts(nested))==common.encoded(whole),'Changed nested representation')
        require(parts_digest(object_parts(nested))==digest(whole),'Changed nested digest')
    return {'status':'PASS','cases':len(cases),'nested_cases':len(cases),'byte_identity':True}


def costs(reserve=0, seconds_reserve=0):
    start=read(PREP/'accounting-start.json')
    paths={p for folder in (PREP,HERE) if folder.exists() for p in folder.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (SELF,PLAN));paths.add(AUTH/'revisions/0407.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds=sum(read(p)['wall_seconds'] for folder in (PREP,HERE) for p in folder.glob('commands/*.json'))
    return {'new_bytes':size,'new_accounted_seconds':seconds,'new_control_seconds':60,
        'prior_known_bytes':start['prior_known_bytes'],'prior_accounted_seconds':start['prior_known_seconds'],
        'known_cumulative_bytes':start['prior_known_bytes']+size,
        'known_cumulative_seconds':start['prior_known_seconds']+seconds+60,
        'timing_caveat':'Prior total includes 043 interrupted 360-second upper bound; earlier manual costs unknown',
        'execution_allowed':size+reserve<252*1024**2 and seconds+seconds_reserve<1200}


def prepare():
    tick=time.monotonic();auth=source.authority();old=read(AUTH/'program.json')
    require(old['revision']==406 and not PREP.exists() and not HERE.exists(),'Fresh406 required')
    events=auth.events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==43,'Retain43attempts')
    require(read(source.HERE/'result.json')['status']=='FAIL' and read(source.HERE/'interruption.json')['tool_exit_code']==143,'Retained043interruption required')
    require(read(source.prior.HERE/'result.json')['status']=='PASS','Successful041 required')
    previous=source.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    checked=equivalence();save(PREP/'encoder-preflight.json',checked)
    protected=dict(read(source.PREP/'freeze.json')['bindings'])
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43):
        folder=BASE/f'attempt-{n:03d}';manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items():require(sha(folder/name)==h,'Changed original '+name)
    production=common.production();protected.update(production)
    same(production,read(source.HERE/'candidate-production.json'),'Candidate production changed')
    names=[SELF,PLAN,source.SELF,rel(PREP/'encoder-preflight.json'),
        rel(source.HERE/source.READING),rel(source.HERE/'source-units.json'),
        rel(source.HERE/'image-transcript.json'),rel(source.HERE/'SOURCE-REVIEW.md'),
        rel(source.HERE/'registry-entry.json'),rel(source.HERE/'source-check.json'),
        rel(source.HERE/'candidate-freeze.json'),rel(source.HERE/'candidate-production.json'),
        rel(source.HERE/'interruption.json'),rel(source.prior.HERE/'ordinary.json.gz')]
    protected.update({n:sha(ROOT/n) for n in names})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale binding')
    save(PREP/'freeze.json',{'bindings':protected,'production':production,'production_mutation_allowed':False})
    config=read(source.PREP/'config.json');require(sha(config['package_python'])==config['python_sha256'],'Interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=407
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Complete unchanged Note27 with bounded durable consumer steps after interrupted043; preserve041 comparator')
    task['inputs']=sorted(set(task['inputs'])|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'accounted_seconds':1200,'control_seconds':60,'new_bytes':256*1024**2,'failure_reserve':4*1024**2,
        'worker_seconds':120,'large_file_bytes':32*1024**2,'unchanged_retries':0,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_accounted_seconds':previous['known_cumulative_seconds']}
    task['bounded_consumer_repair']={'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=44
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=407
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=source.compact_digest(task),dossier=PLAN,phase=0,
                remaining='Note27 source/tests passed but consumer interrupted; source authority and uncovered notes remain.',
                next_action='Run bounded044 consumer stages; retain all prior compositions and failures; continue policy draft using successful delivery.',
                stop_condition='Retain43admissions; permit44;1200+60seconds;256MiB;120second children;no unchanged retry')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (PLAN,rel(PREP/'freeze.json'),rel(PREP/'routes.json'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    forecast=costs()['new_bytes']+2*len(raw)+190*1024**2
    require(forecast<252*1024**2,'Insufficient reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as authority_digest
    save(PREP/'review.json',{'baseline':authority_digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Split actual consumers/comparison/composition/negatives into durable steps','Preserve unchanged043registry/source/tests and successful041answer','Exact sorted JSON hash with shared chunks'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'encoder_preflight':checked,'forecast_new_bytes':forecast},
        'evidence_contract':{'question':'Can unchanged Note27 be delivered with complete041and historical composition preserved?',
            'primary':'Actual ordinary/installed consumers, complete payload/answer/composition equality and adverse refusals',
            'promotion_veto':['Missing stage','Wrong answer/hash/field','Accepted corruption','Wrong import','Changed source'],
            'continuation_veto':['Invalid authority','Corrupt shared evidence','Spent resources'],
            'not_concluded':['Termination cause','Automatic extraction','Financial/legal truth','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':43,'new_maximum':44,
            'retained_attempts':attempts,'reason':'Reproduced interrupted monolithic consumer; bounded durable execution and exact cached serialization',
            'next_discriminating_check':'Actual baseline/candidate consume with timed progress then identical complete historical hashes',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build; short tools and no duplicate workers'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,'command':[sys.executable,'-B','-m','scripts.prospectus_h1_bounded_consumer','prepare']})
    return {'status':'PREPARED','revision':407,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth=source.authority();admission=read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as authority_digest
    require(authority_digest(read(AUTH/'program.json'))==admission['program_sha256'] and
        auth.binding(admission['task_spec'])==admission['binding'],'Unchanged admission required')
    require(all(sha(ROOT/n)==h for n,h in read(PREP/'freeze.json')['bindings'].items()),'Frozen input changed')


def progress(label):
    print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'progress':label}),flush=True)


def large_save(path,value):
    require(path.name in {'baseline-answer.json.gz','ordinary-answer.json.gz','installed-answer.json.gz'},'Unreviewed large output')
    require(not path.exists(),'Output already exists')
    raw=gzip.compress(common.encoded(value),compresslevel=1,mtime=0)
    require(len(raw)<32*1024**2,'Large output cap exceeded')
    with path.open('xb') as stream:stream.write(raw)
    return {'path':rel(path),'sha256':sha(path),'bytes':len(raw)}


def imports(kind):
    location=HERE/'installed' if kind.startswith('installed') else ROOT/'src'
    modules={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    require(modules and all(Path(p).resolve().is_relative_to(location) for p in modules.values()),'Wrong import origin')
    return modules


def checked_answer(kind):
    path=HERE/(kind+'-answer.json.gz');receipt=read(HERE/(kind+'.json'))
    require(sha(path)==receipt['answer_file']['sha256'],'Changed saved answer')
    value=read(path);require(digest(value)==receipt['answer_sha256'],'Changed decoded answer')
    return value


def adopt():
    source.candidate_frozen()
    for name in ('source','implement','tests'):
        require(read(source.HERE/'stages'/name/'result.json')['status']=='PASS','Required043stage absent')
    same(common.production(),read(source.HERE/'candidate-production.json'),'Source-tested production changed')
    checked=source.source_check(read(source.HERE/source.READING),read(source.HERE/'source-units.json'),read(source.HERE/'image-transcript.json'))
    save(HERE/'adopt.json',{'status':'PASS','source_attempt':rel(source.HERE),'source_check':checked,
        'tests':'41 tests passed in 043; exact unchanged production authenticated',
        'new_production_edit':False,'whole_task_complete':False})


def answer_worker(kind):
    from legalmath.prospectus.successor import service
    tick=time.monotonic();progress(kind+':load-original')
    original=read(BASE/'attempt-007/products.json.gz')
    progress(kind+':build-products')
    products=(source.prior if kind=='baseline' else source).build_products(original)
    del original
    phase_hashes={}
    for phase,product in products.items():
        payload=deepcopy(product['payload'])
        if phase=='P1':
            payload['request'].pop('source_statement_cells');phase_hashes['graph']=digest(payload['graph'])
        elif phase=='P2':payload.pop('source_statement_cells')
        elif phase=='P3':payload.pop('source_statement_cells_sha256')
        phase_hashes[phase]=digest(payload)
    progress(kind+':consume')
    answer=service.consume(products,ROOT,include_artifacts=True)
    del products
    progress(kind+':save')
    answer_hash=digest(answer)
    if kind=='baseline':require(answer_hash==read(source.prior.HERE/'ordinary.json.gz')['answer_sha256'],'Complete041baseline changed')
    artifact=large_save(HERE/(kind+'-answer.json.gz'),answer)
    save(HERE/(kind+'.json'),{'status':'PASS','answer_sha256':answer_hash,'answer_file':artifact,
        'phase_hashes_without_statement':phase_hashes,'imports':imports(kind),
        'worker_seconds':time.monotonic()-tick,'actual_service_consumer':True})
    progress(kind+':complete')


def comparison_worker(kind):
    after_kind='installed' if kind.startswith('installed') else 'ordinary'
    before=checked_answer('baseline');after=checked_answer(after_kind)
    same(read(HERE/'baseline.json')['phase_hashes_without_statement'],
         read(HERE/(after_kind+'.json'))['phase_hashes_without_statement'],'Unrelated phase payload changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer changed')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and
        not after['independent_legal_acceptance'],'Original limits changed')
    for key in read(source.prior.HERE/'reading.json'):
        same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost041field '+key)
    reading=read(source.HERE/source.READING);body=after['source_statement_cells']
    for key in reading:same(body[key],reading[key],'Incomplete reading '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    if after_kind=='installed':same(after,checked_answer('ordinary'),'Installed answer differs')
    save(HERE/(kind+'.json.gz'),{'status':'PASS','prior_complete_answer_sha256':digest(before),
        'answer_sha256':digest(after),'reading_sha256':source.compact_digest(reading),
        'replacements':replacements,'addition':body,'whole_task_complete':False})


def composition_worker(kind):
    after_kind='installed' if kind.startswith('installed') else 'ordinary'
    comparison=read(HERE/('installed-compare.json.gz' if after_kind=='installed' else 'compare.json.gz'))
    before=checked_answer('baseline')
    encoded={k:common.encoded(v) for k,v in before.items()};del before
    def answer_parts(receipt):
        changed={**encoded,**{k:common.encoded(v) for k,v in receipt['replacements'].items()},
                 'source_statement_cells':common.encoded(receipt['addition'])}
        return tuple(object_parts(changed))
    supplement=read(BASE/'attempt-016/answer-supplement.json.gz')
    composed={k:common.encoded(v) for k,v in supplement.items()};del supplement
    c17=read(BASE/'attempt-017/composition.json')
    require(parts_digest(object_parts(composed))==c17['previous_content_sha256'],'Original016changed')
    composed.update({k:common.encoded(v) for k,v in read(BASE/'attempt-017/answer-delta.json.gz').items()})
    require(parts_digest(object_parts(composed))==c17['complete_composed_sha256'],'Original017changed')
    rows=[]
    for n,key in KEYS.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz');parts=answer_parts(receipt)
        require(parts_digest(parts)==receipt['answer_sha256'],'Prior answer differs: '+str(n))
        composed[key]=parts;value=parts_digest(object_parts(composed))
        require(value==receipt['full_composed_sha256'],'Prior composition differs: '+str(n))
        rows.append({'attempt':n,'answer_and_complete_composition_matched':True})
        progress(kind+':preserved-'+str(n))
    previous=read(source.prior.HERE/'ordinary.json.gz')
    require(parts_digest(object_parts(composed))==previous['full_composed_sha256'],'Prior full composition changed')
    parts=answer_parts(comparison);require(parts_digest(parts)==comparison['answer_sha256'],'Candidate answer differs')
    composed['h1_associates_consumer']=parts
    receipt={'status':'PASS','prior_full_composed_sha256':previous['full_composed_sha256'],
        'full_composed_sha256':parts_digest(object_parts(composed)),'preserved':rows,
        'exact_sorted_json_encoding':True}
    if after_kind=='installed':same(receipt,read(HERE/'composition.json'),'Installed composition differs')
    save(HERE/(kind+'.json'),receipt)


def controls_worker(kind):
    previous_here=source.HERE
    # The original helper reads the authenticated043source; redirect only its output save.
    previous_save=source.save
    def routed_save(path,value):
        require(path==previous_here/'controls.json','Unexpected delegated write')
        save(HERE/(kind+'.json'),value)
    source.save=routed_save
    try:source.controls_worker()
    finally:source.save=previous_save
    if kind=='installed-controls':same(read(HERE/(kind+'.json')),read(HERE/'controls.json'),'Installed negatives differ')
    cases=source.registry_controls()
    if kind=='installed-controls':same(cases,read(HERE/'controls-registry.json')['cases'],'Installed registry refusals differ')
    save(HERE/(kind+'-registry.json'),{'status':'PASS','cases':cases,'imports':imports(kind)})


def command(name,argv,timeout=120):
    require(costs(32*1024**2,timeout)['execution_allowed'],'Reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    target=HERE/'commands';target.mkdir(exist_ok=True);tick=time.monotonic();process=None;error=None
    try:
        with (target/(name+'.log')).open('x') as stream:
            process=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                     'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'})
            save(target/(name+'-started.json'),{'command':argv,'identity':process_identity(process.pid),
                'at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':timeout,'wall_seconds':0,
                'timing_role':'Identity only; completed command receipt supplies measured wall time'})
            process.wait(timeout=timeout)
        require(process.returncode==0,'Inspect '+name+'.log')
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill();process.wait()
        error={'type':type(exc).__name__,'reason':str(exc)}
    save(target/(name+'.json'),{'command':argv,'wall_seconds':time.monotonic()-tick,
        'exit_code':None if process is None else process.returncode,'error':error})
    require(error is None,'Command failed: '+str(error))
    require(costs()['execution_allowed'],'Post-command resource limit')


def package_worker():
    folder=HERE/'package-source';folder.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    config=read(PREP/'config.json');python=config['package_python'];require(sha(python)==config['python_sha256'],'Interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(PREP/'freeze.json')['production'].items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        same({n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist()
            if n.startswith('legalmath/') and not n.endswith('/')},expected,'Wheel differs')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    installed=HERE/'installed/legalmath'
    same({str(p.relative_to(installed)):sha(p) for p in installed.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'status':'PASS','wheel':common.ref(wheels[0]),'python':python,'files':expected})


def coverage_worker():
    rows=deepcopy(read(source.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='043_SOURCE_TESTS_PASSED_CONSUMER_INTERRUPTED;044_DELIVERY_SUBJECT_TO_RESULTS')
    rows.append({'requirement':'043interrupted ordinary consumer','status':'RETAINED_FAILURE_EXECUTION_CAUSE_UNKNOWN',
        'evidence':common.ref(source.HERE/'result.json')})
    rows.append({'requirement':'Note27normal/installed delivery with complete041preserved','status':'THIS_ATTEMPT_MUST_PASS;see stages'})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Complete policy2.10–2.14draft using successful044;remaining policies/notes/sourceauthority remain'})
    inventory=deepcopy(read(source.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note']==27:row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)


def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage exists or unknown')
    for parent in DEPENDENCIES[name]:require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen();require(costs(46*1024**2 if name=='package' else 32*1024**2)['execution_allowed'],'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='package':package_worker()
        else:
            python=read(PREP/'config.json')['package_python'] if name.startswith('installed') else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name])
        frozen()
    except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    for started in (HERE/'stages').glob('*/started.json'):
        require((started.parent/'result.json').exists(),'Unresolved started stage; recover its recorded processes first')
    stages={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in stages.values())
    if passed:
        receipt=read(HERE/'compare.json.gz');receipt.update(read(HERE/'composition.json'))
        receipt.update(reading=common.ref(source.HERE/source.READING),source_attempt=rel(source.HERE),
            controls=read(HERE/'controls-registry.json')['cases'],source_check=read(source.HERE/'source-check.json'),
            arithmetic=source.arithmetic_diagnostics(read(source.HERE/source.READING)),
            imports=read(HERE/'ordinary.json')['imports'],source_truth_established=False,
            recipe='Reconstruct041from007;preserve016/017and021–041successfulcompositions;add044as h1_associates_consumer')
        save(HERE/'ordinary.json.gz',receipt)
        installed=deepcopy(receipt);installed['imports']=read(HERE/'installed.json')['imports'];save(HERE/'installed.json.gz',installed)
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':stages,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Bounded Note 27 consumer result\n\n'+('Finite delivery passed.' if passed else 'Delivery did not pass.')+
        '\n\nActual stages: '+json.dumps(stages)+'.\n\nThe original041answer and full historical composition are the comparator. '
        '043source/tests and unchanged registry are retained;042storage failure and043interruption remain preserved. '
        'Exact supplied interpretation is assisted source preservation, not automatic extraction or legal/financial truth.\n\n'
        '|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        '|'+('Retain finite delivery' if passed else 'Retain actual failure')+'|Actual consumers and complete comparisons|See stages|Historical source authority and wider coverage|Record/refresh and continue reviewed ready work|Termination cause,package unsuitability,whole build|\n\n'
        'Post-run review: exact JSON chunking must reproduce each historical hash; success does not explain the earlier termination. '
        'Shared source-interpretation error remains possible despite images and corruption refusals.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':common.ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-')
        sys.path.insert(0,str(HERE/'installed') if kind.startswith('installed') else str(ROOT/'src'))
        def forbidden(*args,**kwargs):raise RuntimeError('No native/network child in consumer worker')
        subprocess.Popen=forbidden
        if kind in ('baseline','ordinary','installed'):answer_worker(kind)
        elif kind in ('compare','installed-compare'):comparison_worker(kind)
        elif kind in ('composition','installed-composition'):composition_worker(kind)
        elif kind in ('controls','installed-controls'):controls_worker(kind)
        else:{'adopt':adopt,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare':result=prepare()
    elif action=='finalize':result=finalize()
    elif action=='equivalence':result=equivalence()
    else:result=stage(action)
    print(json.dumps(result))
