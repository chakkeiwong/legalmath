"""Changed serializer continuation; original failed attempt and methods stay frozen."""
from copy import deepcopy
import ast,json,shutil,sys
from scripts import prospectus_fresh_preparation as failed
from scripts import prospectus_residual_coverage as coverage
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
ROOT,AUTH=failed.ROOT,failed.AUTH
PREP=AUTH/'reviews/fresh-compact-315';HERE=AUTH/'attempts/basf-references/attempt-056'
PLAN='docs/plans/prospectus-fresh-serialization-repair-2026-10-19.md'
METHOD='scripts/prospectus_fresh_compact.py';WORKER='scripts/prospectus_fresh_compact_installed.py'
TEST='tests/prospectus_successor/test_preparation_compact.py'
FILES=(PLAN,METHOD,WORKER,TEST,'scripts/prospectus_fresh_failure.py')
TARGETS=('src/legalmath/prospectus/successor/preparation.py',)
read,save,sha,rel=failed.read,failed.save,failed.sha,failed.rel
STAGES=failed.STAGES;PHASES=failed.PHASES


def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior'];seconds=base['cumulative026_055_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0315.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['cumulative026_055_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=max(0,(ROOT/TARGETS[0]).stat().st_size-start['production_bytes'])
    assert seconds<12600 and size<2044*1024**2,'Fresh compact cumulative026 bound'
    return {'cumulative026_056_measured_seconds':seconds,'cumulative026_056_bytes':size,
        'prior_costs_reset':False,'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def testfiles():return [TEST,*failed.testfiles()]


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==314
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==55 and any(e['kind']=='REJECT' and e.get('attempt')==rel(failed.HERE) for e in events)
    for n,v in read(failed.HERE/'outputs.json').items():assert sha(failed.HERE/n)==v,n
    assert read(failed.HERE/'source-failure-diagnosis.json')['complete_P1_equal'] is True
    save(PREP/'accounting-start.json',{'prior':failed.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],'production_bytes':(ROOT/TARGETS[0]).stat().st_size})
    text=(ROOT/TARGETS[0]).read_text();text=text.replace('from pathlib import Path','from pathlib import Path\nimport json\nimport os',1)
    old='        write(path, product)'
    new="""        temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(product, stream, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)"""
    assert text.count(old)==1;text=text.replace(old,new);ast.parse(text)
    path=PREP/'candidate/preparation.py';path.parent.mkdir(exist_ok=True);path.write_text(text)
    (PREP/'baseline').mkdir();shutil.copyfile(ROOT/TARGETS[0],PREP/'baseline/preparation.py')
    save(PREP/'installation.json',[{'target':TARGETS[0],'before':sha(ROOT/TARGETS[0]),'candidate':rel(path),'after':sha(path)}])
    shutil.copyfile(failed.PREP/'recipe.json',PREP/'recipe.json')
    assert sha(PREP/'recipe.json')==sha(failed.PREP/'recipe.json')
    (PREP/'METHOD-REVIEW.md').write_text('''# Serialization correction audit

PASS:complete freshly extractedP1equals baseline;only indented bytes exceeded
the cap. Candidate changes product serialization to compactUTF-8JSONwith
flush/fsync/replace. Original recipe,semantic content,hashes and128MiBcap remain.
Regression makes compact JSON fit while pretty JSON would fail. Preserve all
failed055bytes,costs and methods;no unchanged retry. Finish actual installed
P1-P5and full answer equality. Counts do not prove legal completeness.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,failed.METHOD,failed.WORKER,*failed.FILES,'pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (failed.HERE/'outputs.json',failed.HERE/'source-failure-diagnosis.json',failed.PREP/'recipe.json',failed.PREP/'freeze.json',coverage.HERE/'ordinary-answer.json.gz',coverage.PREP/'profiles.json'):
        bindings[rel(p)]=sha(p)
    for row in read(failed.PREP/'recipe.json')['inputs'].values():bindings[row['path']]=row['sha256']
    for row in read(failed.PREP/'source-files.json'):bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=315
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair reproduced prettyJSONsize mismatch and finish unchanged source regeneration criteria',
        fresh_compact_repair={'failed_attempt':rel(failed.HERE),'review':rel(PREP),'original_task_complete':False,
            'cumulative026_seconds':12600,'cumulative026_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=56
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=315
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify changed compact serialization,then installed originalP1-P5and complete answer;continue substantive source gaps',
            stop_condition='56 admissions;210s stages;12600s cumulative026;2048MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].pop(TARGETS[0],None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_056_measured_seconds']+1100,'bytes':costs()['cumulative026_056_bytes']+300*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Compact lossless product serialization only','Add realistic size regression','Admission55to56;retain cumulative bounds and all failed bytes'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Compact size regression and unchanged full installedP1-P5and answer comparisons',
            'promotion_veto':['Semantic change','Lost evidence','Profile rehash','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Package failure','Legal completeness','Automatic unseen-source interpretation']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':55,'new_maximum':56,'retained_attempts':attempts,
            'reason':'Reproduced indented serialization exceeds cap;source extraction itself matches exactly',
            'next_discriminating_check':'Compact encoding fits same cap with identical product and full installed source replay',
            'stop_condition':'210s stages;12600s cumulative026;2048MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested repair and continued bounded general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':315,'forecast':forecast,'failed_evidence_preserved':True}


def bind_runner():
    # Execute the already reviewed stage code with explicit new destinations.
    # Frozen files on disk are never rewritten.
    failed.PREP=PREP;failed.HERE=HERE;failed.PLAN=PLAN;failed.METHOD=METHOD;failed.WORKER=WORKER
    failed.TARGETS=TARGETS;failed.costs=costs
    failed.testfiles=lambda:[TEST,'tests/prospectus_successor/test_successor.py',*coverage.testfiles()]
    original_install=failed.install
    def install():
        result=original_install();result['production_files']=1;return result
    failed.install=install


if __name__=='__main__':
    if sys.argv[1]=='prepare':
        import signal,time
        folder=PREP/'stages/prepare';assert not (folder/'started.json').exists()
        save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_fresh_compact','prepare']})
        started=time.monotonic()
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Compact preparation bound')));signal.alarm(210)
        try:
            result=prepare();result['wall_seconds']=time.monotonic()-started;costs(result['wall_seconds'])
            save(folder/'result.json',result);print(json.dumps(result))
        except BaseException as error:
            save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-started});raise
        finally:signal.alarm(0)
    else:
        bind_runner();failed.main()
