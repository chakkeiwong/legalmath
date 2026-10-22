"""Same-task source route composition; prior methods and evidence stay frozen."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_agent_notice_integration as prior
from scripts import prospectus_notice_delivery_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/notice-delivery-composition-317'
HERE=AUTH/'attempts/basf-office/attempt-005'
PLAN='docs/plans/prospectus-notice-delivery-composition-2026-10-19.md'
METHOD='scripts/prospectus_notice_delivery.py';WORKER='scripts/prospectus_notice_delivery_installed.py'
ORACLE='scripts/prospectus_notice_delivery_oracle.py';TEST='tests/prospectus_successor/test_notice_delivery.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/notice_delivery.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    products,_=prior.baseline();answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='f8d63818df3ba9a1a27b026487c0c6a84f9efbf4c41834f5e91ac61a1079edcb'
    return products,answer


def testfiles():return [TEST,*prior.testfiles()]


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0317.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<12600 and size<2044*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==316
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-office']
    assert len(attempts)==4 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    candidate=PREP/'candidate/notice_delivery.py';spec=importlib.util.spec_from_file_location('legalmath.prospectus._delivery_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();source=module.context(products,ordinary)
    rows=oracle.scenarios(products['P1']['payload']['request']['bundle']['instrument_id'])
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'context':source,'scenarios':rows,'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{r['id']:oracle.expected(r) for r in rows})
    text=(ROOT/TARGETS[1]).read_text();old='            agent_notice_profile=None, expected_agent_notice_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,'            agent_notice_profile=None, expected_agent_notice_profile_sha256=None,'+chr(10)+'            notice_delivery_profile=None, expected_notice_delivery_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new='''    if notice_delivery_profile is not None:
        from ..notice_delivery import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['notice_delivery_review'] = evaluate(products, baseline, notice_delivery_profile, root,
            expected_profile_sha256=expected_notice_delivery_profile_sha256)
    elif expected_notice_delivery_profile_sha256 is not None:
        raise ValueError('Notice delivery profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'coverage', 'agent_notice')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'coverage', 'agent_notice', 'notice_delivery')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'notice_delivery','path':rel(PREP/'profile.json'),'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text('''# Delivery composition skeptical audit

PASS: original third/seventh-day source rules and route conditions preserved.
Hypothetical issuer notice dates derive arithmetic candidates only. Listing,
valid event,exchange permission and substitution election remain explicit.
Holder-to-agent notices are refused. The existing notice evaluator receives
the derived date and finite route status; negative intervals receive explicit
insufficient-notice treatment without misusing its nonnegative domain.
Independent Gregorian addition and exhaustive truth checks precede execution.
Full prior answer and isolated installed equality are primary checks. Source
interpretation,actual events and historical law remain unproved. All prior
attempts,costs and unknown time remain; no additional external calls.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,'scripts/prospectus_calendar_oracle.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=317
    task=next(t for t in proposal['tasks'] if t['id']=='basf-office')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Compose section13 conditional deemed dates with complete agent-notice answer',
        notice_delivery_composition={'review':rel(PREP),'original_task_complete':False,'combined_seconds':12600,'combined_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-office']['maximum_new_attempts']=5
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=317
    for row in routes['tasks']:
        if row['task']=='basf-office':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify conditional delivery date composition then continue original office/source authority',
            stop_condition='5 admissions;210s stages;combined12600s and2048MiB;no external calls')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+900,'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Source-bound delivery dates reach agent-notice answer','Preserve route conditions and uncertainty','Same-task admission4to5;retain combined costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent Gregorian addition and route truth;complete prior answer;ordinary and installedCLI equality',
            'promotion_veto':['Wrong delay','Wrong notice direction','Lost conditions','False actual notice','Source drift','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Full legal validity','Actual change','Office authority','General interpretation']},
        'budget_revision':{'budget_key':'basf-office','previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
            'reason':'The previous integration accepted holders-informed dates but did not derive source route delays',
            'next_discriminating_check':'Route-dependent dates reverse naive30/46day answers and preserve unknowns in full installed answer',
            'stop_condition':'210s stages;combined12600s and2048MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested continued internally established general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':317,'scenarios':len(rows),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus import notice_delivery as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    expected=read(PREP/'expected.json')
    for r in actual[module.KEY]['scenarios']:
        want=expected[r['scenario']['id']]
        assert r['arithmetic_candidate_date']==want['date'] and r['route_preconditions']['status']==want['route']
        assert r['notice']['notice_precondition']['status']==want['notice']
        assert r['notice']['conditional_notice_precondition']['status']==want['conditional']
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import notice_delivery as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source-delay','source-target','actual-promoted','missing-open','duplicate','wrong-direction','wrong-agent','wrong-notice','candidate-date','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='source-delay':bad['context']['agent_and_notice_context']['notice_clauses'][0]['procedural_reading']['deemed_effective_days_after_publication']=0
        elif kind=='source-target':bad['context']['agent_and_notice_context']['notice_reference']['targets'].pop()
        elif kind=='actual-promoted':bad['actual_event_established']=True
        elif kind=='missing-open':bad['scenarios'].pop(0)
        elif kind=='duplicate':bad['scenarios'].append(deepcopy(bad['scenarios'][0]))
        elif kind=='wrong-direction':bad['scenarios'][1]['event']['role']='HOLDER_TO_AGENT'
        elif kind=='wrong-agent':bad['scenarios'][1]['event']['agent_id']='other'
        elif kind=='wrong-notice':bad['scenarios'][1]['event']['notice_id']='other'
        elif kind=='candidate-date':actual[module.KEY]['scenarios'][1]['arithmetic_candidate_date']='2024-01-01'
        else:actual['agent_notice_review']['complete_legal_test']=True
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('candidate-date','lost-prior'):module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def seal():
    result={'status':'PASS','task':'basf-office','original_task_complete':False,'result_kind':'CONDITIONAL_NOTICE_DELIVERY_COMPOSITION',
        'baseline_unchanged':True,'installed_cli_equal':True,'resources':costs(),
        'next_action':'Continue original office authority,historical/source completeness and general preparation gaps'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Notice route dates reach the complete answer

Conditional publication and clearing notices now apply their three/seven-day
source delays before the 30/45-day agent notice test. Listing,valid event,
exchange permission and substitution election remain explicit finite premises.
Holder notices use neither issuer route. Boundary examples reverse the naive
answer that wrongly treats publication or delivery as immediate holder notice.
Unknowns,conflicts,source context and every prior answer field are preserved.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite composition|Independent date/truth and full ordinary/installed checks|Wrong direction,identity,source and actual promotion refused|Reading applicability,office and original source completeness|Original substantive gaps|Actual notice,legal completeness or whole build|

This repairs our missing composition. No package incapability follows. A shared
error in the source reading remains the strongest alternative explanation;
independent arithmetic does not resolve historical law or all legal premises.
Wrong route conditions or a changed complete prior answer invalidate the result.
''')
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
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_notice_delivery',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Delivery stage bound')));signal.alarm(210)
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
