"""Same-task source route composition; prior methods and evidence stay frozen."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_publication_routes as prior
from scripts import prospectus_unicode_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/unicode-labels-322'
HERE=AUTH/'attempts/basf-references/attempt-061'
PLAN='docs/plans/prospectus-unicode-label-integration-2026-10-19.md'
METHOD='scripts/prospectus_unicode_labels.py';WORKER='scripts/prospectus_unicode_installed.py'
ORACLE='scripts/prospectus_unicode_oracle.py';TEST='tests/prospectus_successor/test_unicode_labels.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_unicode_cases.py','docs/plans/prospectus-unicode-label-discovery-2026-10-19.md')
TARGETS=('src/legalmath/prospectus/successor/unicode_labels.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    products,_=prior.baseline();answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='cd36e27c126f52ae1b12f86b83a566b815928ae6c79571c55a8321db1fc11a39'
    return products,answer


def testfiles():return [TEST,*prior.testfiles()]


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+read(PREP/'case-preparation.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0322.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in read(PREP/'production-bytes.json').items() if (ROOT/n).exists())
    assert seconds<14400 and size<2300*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':14400,'bytes_bound_with_4MiB_reserve':2304*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==321
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==60 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    freeze=read(PREP/'cases-freeze.json')
    assert sha(PREP/'cases.json')==freeze['cases_sha256']
    assert sha(ROOT/freeze['authoring_method'])==freeze['authoring_method_sha256']
    assert sha(ROOT/freeze['plan'])==freeze['plan_sha256']
    for path,checksum in freeze['source_files'].items():assert sha(ROOT/path)==checksum
    save(PREP/'production-bytes.json',{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS})
    candidate=PREP/'candidate/unicode_labels.py';candidate.parent.mkdir(exist_ok=True)
    shutil.copyfile(PREP/'candidate.py',candidate)
    spec=importlib.util.spec_from_file_location('legalmath.prospectus.successor._unicode_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();cases=read(PREP/'cases.json')['cases'];sources=[]
    for row in cases:
        if row['origin']!='ORIGINAL_RETAINED':continue
        sources.append({'id':row['id'],'path':row['source']['path'],'file_sha256':row['source']['sha256'],
            **{k:row[k] for k in ('text_sha256','language','regions','quotation_convention')}})
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'sources':sources,'scope_admitted':False,'meaning_admitted':False}
    save(PREP/'profile.json',profile)
    text=(ROOT/TARGETS[1]).read_text();old='            publication_profile=None, expected_publication_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,'            publication_profile=None, expected_publication_profile_sha256=None,'+chr(10)+'            labels_profile=None, expected_labels_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new="""    if labels_profile is not None:
        from .unicode_labels import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['unicode_label_review'] = evaluate(products, baseline, labels_profile, root,
            expected_profile_sha256=expected_labels_profile_sha256)
    elif expected_labels_profile_sha256 is not None:
        raise ValueError('Label profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'affiliate', 'publication')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'affiliate', 'publication', 'labels')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'labels','path':rel(PREP/'profile.json'),'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text((ROOT/PLAN).read_text())
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,'scripts/prospectus_calendar_oracle.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    for row in sources:bindings[row['path']]=row['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=322
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair reproduced Unicode label misses through optional grammar and full ordinary/installed source review',
        unicode_labels={'review':rel(PREP),'original_task_complete':False,'combined_seconds':14400,'combined_bytes':2304*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=61
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=322
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify source-bound Unicode proposals and complete answer; continue unquoted definitions and semantic scope',
            stop_condition='61 admissions;240s stages;combined14400s/2304MiB;no GETs or unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+900,'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<14400 and forecast['bytes']<2300*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Optional explicit quotation conventions and source-review integration','Legacy scanner and prior answer unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Frozen independent source intervals and maps; legacy preservation; ordinary/installed complete answer equality',
            'promotion_veto':['Wrong source','Wrong interval','Cross-region pairing','Header deletion','Invented scope','Prior answer loss'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],
            'not_concluded':['General linguistic recall','Definition semantics','Source authority','Legal correctness','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':60,'new_maximum':61,'retained_attempts':attempts,
            'reason':'Actual retained BES names and ordinary quoted phrase are missed by ASCII-only grammar',
            'next_discriminating_check':'Exact proposals with source maps and explicit nonsemantic status reach complete answer',
            'stop_condition':'240s stages;combined14400s/2304MiB;no GETs or unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued internally established general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':322,'cases':len(cases),'original_sources':len(sources),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus.successor import unicode_labels as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],225)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    cases={r['id']:r for r in read(PREP/'cases.json')['cases']}
    for row in actual[module.KEY]['sources']:oracle.verify(cases[row['source']['id']],row['report'])
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import unicode_labels as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source-bytes','source-text','scope-promoted','duplicate','convention','partition','path','false-result','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='source-bytes':bad['sources'][0]['file_sha256']='0'*64
        elif kind=='source-text':bad['sources'][0]['text_sha256']='0'*64
        elif kind=='scope-promoted':bad['scope_admitted']=True
        elif kind=='duplicate':bad['sources'].append(deepcopy(bad['sources'][0]))
        elif kind=='convention':bad['sources'][0]['quotation_convention']='guess'
        elif kind=='partition':bad['sources'][0]['regions'][0]['start']=1
        elif kind=='path':bad['sources'][0]['path']='../outside.txt'
        elif kind=='false-result':actual[module.KEY]['sources'][0]['report']['scope_admitted']=True
        else:actual['publication_routes_review']['historical_application_proved']=True
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('false-result','lost-prior'):module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],225)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'OPTIONAL_UNICODE_SOURCE_LABEL_REVIEW','baseline_unchanged':True,'installed_cli_equal':True,
        'scope_admitted':False,'meaning_admitted':False,'resources':costs(),
        'next_action':'Continue unquoted definitions,source segmentation and supported semantic scope decisions'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PREP/'cases.json'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Unicode source labels reach the complete source review

The optional scanner accepts explicit quotation conventions. Two retained
BES texts now expose their exact quoted labels through the ordinary and
installed answer. The legacy scanner and all previous answer fields remain
unchanged. Raw page-header contamination remains visible. Ordinary quoted
phrases remain candidates, with no admitted definition, scope or authority.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional grammar|Frozen exact spans/maps and complete ordinary/installed answers|Source,partition,scope and answer misuse refused|Unquoted names,morphology,segmentation and meanings|Original source and supported semantic scope work|General recall,legal interpretation or whole build|

The reproduced miss was our deliberately narrow ASCII grammar, not an external
package defect. The strongest alternative explanation for apparent discovery
progress is that a quote contains ordinary speech or contaminated text rather
than a legal name. The result explicitly preserves that distinction. Changed
source regions or different quotation conventions require fresh evidence.
""")
    return result


def bind_runner():
    engine.PREP=PREP;engine.HERE=HERE;engine.PLAN=PLAN;engine.METHOD=METHOD;engine.WORKER=WORKER
    engine.TARGETS=TARGETS;engine.costs=costs;engine.testfiles=testfiles;engine.cli_arguments=cli_arguments


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs();bind_runner()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_unicode_labels',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':240})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Unicode label stage bound')));signal.alarm(240)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(engine,stage))()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
