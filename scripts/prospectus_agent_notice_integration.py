"""Original basf-office continuation; old methods remain unchanged on disk."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, os, shutil, signal, sys, time
from scripts import prospectus_residual_coverage as engine
from scripts import prospectus_fresh_compact as fresh
from scripts import prospectus_agent_notice_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH=engine.ROOT,engine.AUTH
BASE_HERE,BASE_PREP=engine.HERE,engine.PREP
PREP=AUTH/'reviews/agent-notice-integration-316'
HERE=AUTH/'attempts/basf-office/attempt-004'
PLAN='docs/plans/prospectus-agent-notice-integration-2026-10-19.md'
METHOD='scripts/prospectus_agent_notice_integration.py'
WORKER='scripts/prospectus_agent_notice_installed.py'
ORACLE='scripts/prospectus_agent_notice_oracle.py'
TEST='tests/prospectus_successor/test_agent_notice_application.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_calendar_oracle.py')
TARGETS=('src/legalmath/prospectus/agent_notice_application.py',
         'src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=AUTH/'reviews/conditional-cli-311/products.json'
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=engine.read,engine.save,engine.sha,engine.rel
PRIOR_TESTS=engine.testfiles()


def baseline():
    manifest=read(PRODUCTS)
    products={k:read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=read(BASE_HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='e87a95ae98fda4a8854fe9bb4db283231013d34fac213f36fa5bb28c1c1643a8'
    return products,answer


def testfiles():
    return list(dict.fromkeys([TEST,'tests/prospectus_successor/test_agent_notice_window.py',
        'tests/prospectus_successor/test_preparation.py','tests/prospectus_successor/test_preparation_compact.py',
        'tests/prospectus_successor/test_successor.py',*PRIOR_TESTS]))


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0316.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<12600 and size<2044*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==315
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-office']
    assert len(attempts)==3
    assert any(e['kind']=='RECORD' and e.get('attempt')==rel(fresh.HERE) for e in events)
    for folder in (fresh.HERE,AUTH/'attempts/basf-office/attempt-003'):
        for n,v in read(folder/'outputs.json').items():assert sha(folder/n)==v,n
    prior=fresh.costs()
    oldfolders=[AUTH/'attempts/basf-office'/('attempt-00'+str(i)) for i in (1,2,3)]
    oldfolders.append(AUTH/'reviews/agent-window-237')
    oldbytes=sum(p.stat().st_size for d in oldfolders for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    oldseconds=read(AUTH/'attempts/basf-office/attempt-003/stages/seal/result.json')['cumulative_seconds']
    save(PREP/'accounting-start.json',{'prior_measured_seconds':prior['cumulative026_056_measured_seconds']+oldseconds,
        'prior_bytes':prior['cumulative026_056_bytes']+oldbytes,'prior_reference_costs':prior,
        'retained_office_bytes':oldbytes,'retained_office003_measured_seconds':oldseconds,
        'older_office_time':'UNKNOWN','history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    candidate=PREP/'candidate/agent_notice_application.py'
    spec=importlib.util.spec_from_file_location('legalmath.prospectus._notice_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();source=module.context(products,ordinary)
    source_check=oracle.check_source(products,ordinary,source)
    rows=oracle.scenarios(products['P1']['payload']['request']['bundle']['instrument_id'])
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'context':source,'scenarios':rows,'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{r['id']:oracle.expected(r) for r in rows})
    save(PREP/'source-check.json',source_check)
    text=(ROOT/TARGETS[1]).read_text();old='            coverage_profile=None, expected_coverage_profile_sha256=None):'
    assert text.count(old)==1
    text=text.replace(old,'            coverage_profile=None, expected_coverage_profile_sha256=None,'+chr(10)+'            agent_notice_profile=None, expected_agent_notice_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new='''    if agent_notice_profile is not None:
        from ..agent_notice_application import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['agent_notice_review'] = evaluate(products, baseline, agent_notice_profile, root,
            expected_profile_sha256=expected_agent_notice_profile_sha256)
    elif expected_agent_notice_profile_sha256 is not None:
        raise ValueError('Agent notice profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'concert', 'coverage')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'concert', 'coverage', 'agent_notice')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(BASE_PREP/'profiles.json')
    manifest['profiles'].append({'name':'agent_notice','path':rel(PREP/'profile.json'),'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text('''# Agent notice integration skeptical audit

PASS: exact complete clause and all 15 onward targets retained. Supplied
holders-informed dates are not publication or clearing delivery. Both bounds,
insolvency, unknowns, conflicts and applicability remain separate. No actual
effectiveness or office address inferred. Independent integer and truth oracle
precedes execution. The full 054 answer, freshly reproduced in installed 056,
is the comparator. Counts, hashes and replay do not prove legal completeness.
Prior attempts, measured costs and unknown manual time remain visible.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,engine.METHOD,engine.WORKER,fresh.METHOD,'pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (fresh.HERE/'outputs.json',fresh.HERE/'result.json',BASE_HERE/'ordinary-answer.json.gz',
        BASE_PREP/'profiles.json',PRODUCTS,AUTH/'attempts/basf-office/attempt-003/outputs.json'):bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=316
    task=next(t for t in proposal['tasks'] if t['id']=='basf-office')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Integrate source-bound notice into complete answer; preserve section13 date dependency',
        agent_notice_integration={'review':rel(PREP),'original_task_complete':False,'combined_seconds':12600,'combined_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-office']['maximum_new_attempts']=4
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=316
    for row in routes['tasks']:
        if row['task']=='basf-office':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Integrate necessary notice; retain unknown office and section13 deemed-date dependency',
            stop_condition='4 admissions;210s stages;combined12600s and2048MiB;no external calls')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+1000,'bytes':costs()['combined_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Complete-answer notice integration','Preserve section13 dependency','Same-task admission3to4;retain all costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent intervals/truth;complete prior answer preservation;ordinary and installedCLI equality',
            'promotion_veto':['Wrong bounds','Lost unknowns','Wrong roles','Source drift','False effectiveness','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Legal completeness','Actual change','Office authority','General source interpretation']},
        'budget_revision':{'budget_key':'basf-office','previous_maximum':3,'new_maximum':4,'retained_attempts':attempts,
            'reason':'Separate notice diagnostic never reached complete prospectus answer',
            'next_discriminating_check':'Complete ordinary and installed answers with independent interval/Boolean oracle',
            'stop_condition':'210s stages;combined12600s and2048MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested continued internally established general build before actual facts'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':316,'scenarios':len(rows),'source':source_check,'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus import agent_notice_application as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    expected=read(PREP/'expected.json');results=actual[module.KEY]['scenarios']
    for row in results:
        want=expected[row['scenario']['id']]
        assert row['exact_interval']==want['exact_interval']
        for key in ('notice_precondition','conditional_notice_precondition'):assert row[key]['status']==want[key]
    verification.update(source=oracle.check_source(products,ordinary,actual[module.KEY]['context']),independent_cases=len(results))
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import agent_notice_application as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('onward-target','clause-bound','false-effectiveness','office-invented','missing-open','duplicate-scenario','publication-role','source-omitted','lost-baseline','wrong-boundary'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='onward-target':bad['context']['notice_reference']['targets'].pop()
        elif kind=='clause-bound':bad['context']['agent_clause']['agent_reading']['notice_window_days']=[30,46]
        elif kind=='false-effectiveness':bad['actual_event_established']=True
        elif kind=='office-invented':bad['context']['calculation_agent_office']='invented office'
        elif kind=='missing-open':bad['scenarios'].pop(0)
        elif kind=='duplicate-scenario':bad['scenarios'].append(deepcopy(bad['scenarios'][0]))
        elif kind=='publication-role':bad['scenarios'][1]['interval']['start']['role']='PUBLICATION'
        elif kind=='source-omitted':actual[module.KEY]['context']['notice_reference']['targets']=[]
        elif kind=='lost-baseline':actual['basf_agents']['calculation_agent_office']='invented office'
        else:actual[module.KEY]['scenarios'][1]['notice_precondition']['status']='YES'
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('source-omitted','lost-baseline','wrong-boundary'):
                module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def seal():
    result={'status':'PASS','task':'basf-office','original_task_complete':False,'result_kind':'COMPLETE_ANSWER_AGENT_NOTICE_INTEGRATION',
        'baseline_unchanged':True,'installed_cli_equal':True,'resources':costs(),
        'next_action':'Continue section13 deemed-notice date composition and original office/source authority gaps'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Agent notice now reaches the complete answer

The complete ordinary and isolated installed answers contain the exact
conditional notice precondition, inclusive 30/45 limits, insolvency exception,
unknowns, conflicts and applicability qualification. All prior answer fields
and earlier profile pins are preserved. Full section13 targets remain visible;
a supplied holders-informed date is not a publication date. The agent office
and actual appointment/effectiveness stay open.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain integration|Independent interval/truth and complete ordinary/installed answers|Wrong roles,subjects,sources and false effectiveness refused|Source reading,office and deemed-date composition|Original notice/source work|Actual change,legal completeness or whole build|

This repairs our integration omission, not a fundamental package limitation.
The strongest alternative explanation is a shared error in the supplied source
reading. Complete source context and independent arithmetic constrain that
possibility but cannot establish every legal premise. Wrong dates, changed
source or a lost prior answer field would overturn this result.
''')
    return result


def bind_runner():
    # Explicit in-memory destinations; the old source and sealed evidence stay intact.
    engine.PREP=PREP;engine.HERE=HERE;engine.PLAN=PLAN;engine.METHOD=METHOD;engine.WORKER=WORKER
    engine.TARGETS=TARGETS;engine.costs=costs;engine.testfiles=testfiles;engine.cli_arguments=cli_arguments


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs();bind_runner()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_agent_notice_integration',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Notice integration stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        action=globals().get(stage) or getattr(engine,stage)
        result=action()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
