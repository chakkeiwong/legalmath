"""Source-qualified payment categories; same-task retained accounting."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_unicode_labels as prior
from scripts import prospectus_payment_category_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/payment-categories-323'
HERE=AUTH/'attempts/basf-references/attempt-062'
PLAN='docs/plans/prospectus-payment-categories-2026-10-19.md'
METHOD='scripts/prospectus_payment_categories.py';WORKER='scripts/prospectus_payment_categories_installed.py'
ORACLE='scripts/prospectus_payment_category_oracle.py';TEST='tests/prospectus_successor/test_payment_categories.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_payment_category_cases.py')
TARGETS=('src/legalmath/prospectus/payment_categories.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel



def baseline():
    manifest=read(PRODUCTS);products={}
    for key,row in manifest['products'].items():
        path=ROOT/row['path'];assert sha(path)==row['sha256']
        products[key]=read(path)
    assert digest(products)==read(prior.PREP/'profile.json')['products_sha256']
    answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='fd08d1041c223972e827e29ad20fdb9b8176d338d4bdee5e7270bf645ecc50a1'
    return products,answer

def testfiles():return [TEST,*prior.testfiles()]


def tests():
    import xml.etree.ElementTree as ET
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',
        *[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],150)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS','independent_boolean_world_oracle':True,**counts}


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+read(PREP/'case-preparation.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0323.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in read(PREP/'production-bytes.json').items() if (ROOT/n).exists())
    assert seconds<14400 and size<2300*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':14400,'bytes_bound_with_4MiB_reserve':2304*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}



def prepare():
    program=read(AUTH/'program.json');assert program['revision']==322
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==61 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    freeze=read(PREP/'cases-freeze.json')
    assert sha(PREP/'cases.json')==freeze['cases_sha256']
    assert sha(ROOT/freeze['authoring_method'])==freeze['authoring_method_sha256']
    assert sha(ROOT/freeze['plan'])==freeze['plan_sha256']
    assert sha(ROOT/freeze['independent_oracle'])==freeze['oracle_sha256']
    for path,checksum in freeze['source_files'].items():assert sha(ROOT/path)==checksum
    save(PREP/'production-bytes.json',{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS})
    candidate=PREP/'candidate/payment_categories.py';candidate.parent.mkdir(exist_ok=True)
    shutil.copyfile(PREP/'candidate.py',candidate)
    spec=importlib.util.spec_from_file_location('legalmath.prospectus._payment_categories_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline()
    cases=read(PREP/'cases.json')['cases'];rows=[deepcopy(c['scenario']) for c in cases]
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    for row in rows:
        assert row['identity']['instrument_id']=='BASF-SOURCE-BOUND-PLACEHOLDER'
        row['identity']['instrument_id']=instrument
        row['payment']['clock']['instrument_id']=instrument
    source=module.context(products)
    from legalmath.prospectus import payment_deadline
    baseline_cases={}
    for name,value in (('qualification_missing',None),('qualification_supplied',True)):
        payment=deepcopy(rows[1]['payment']);payment['qualified_note_payment']=value
        baseline_cases[name]=payment_deadline.analyze(payment,source['payment_defaults'],instrument)
    assert baseline_cases['qualification_missing']['complete_default']['status']=='UNKNOWN'
    assert baseline_cases['qualification_supplied']['complete_default']['status']=='YES'
    save(PREP/'baseline-payment-calculation.json',baseline_cases)
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'context':source,'scenarios':rows,'actual_event_established':False,
        'historical_law_established':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile)
    save(PREP/'baseline-gap.json',{'classification':'SOURCE_READING_NOT_COMPOSED_WITH_PAYMENT_QUALIFICATION',
        'source_groups':[r['id'] for r in source['contract_readings']],
        'existing_parameter':'payment_deadline.analyze -> qualified_note_payment',
        'new_default_asserted':False,'candidate_scenarios_evaluated':False})
    text=(ROOT/TARGETS[1]).read_text();old='            labels_profile=None, expected_labels_profile_sha256=None):'
    assert text.count(old)==1
    text=text.replace(old,'            labels_profile=None, expected_labels_profile_sha256=None,'+chr(10)+
        '            payment_categories_profile=None, expected_payment_categories_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new="""    if payment_categories_profile is not None:
        from ..payment_categories import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['payment_category_review'] = evaluate(products, baseline, payment_categories_profile, root,
            expected_profile_sha256=expected_payment_categories_profile_sha256)
    elif expected_payment_categories_profile_sha256 is not None:
        raise ValueError('Payment category profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'publication', 'labels')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'publication', 'labels', 'payment_categories')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json')
    manifest['profiles'].append({'name':'payment_categories','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,
        'scripts/prospectus_payment_oracle.py','scripts/prospectus_amount_oracle.py',
        'scripts/prospectus_calendar_oracle.py','scripts/prospectus_cutoff_oracle.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):
        bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    bindings.update(freeze['source_files'])
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=323
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Connect unquoted principal/interest definitions and all section7 exceptions to the existing payment-default calculation',
        payment_categories={'review':rel(PREP),'original_task_complete':False,
                            'combined_seconds':14400,'combined_bytes':2304*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=62
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=323
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify source-qualified payment categories and full default(a); continue source/scope coverage with all original records retained',
            stop_condition='62 admissions;300s stages;combined14400s/2304MiB;no GETs or unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+900,
              'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<14400 and forecast['bytes']<2300*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Source-qualified payment inclusion before existing clock','Original answer and unresolved definitions retained'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Frozen independent full scenarios, flat-world oracle, full ordinary/installed equality',
            'promotion_veto':['Lost tax exception','False exhaustive negative','Qualification override','Changed source','Lost prior answer'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual payment obligations','Historical tax law','Calculated amounts','General interpretation','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':61,'new_maximum':62,'retained_attempts':attempts,
            'reason':'Unquoted definitions are retained but existing clock still requires an uncomputed payment-qualification premise',
            'next_discriminating_check':'Source-qualified and excluded amounts change the actual complete conditional default while unknown other routes stay open',
            'stop_condition':'300s stages;combined14400s/2304MiB;no GETs or unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued internally established general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':323,'cases':len(rows),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]



def consume():
    from legalmath.prospectus import payment_categories as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],270)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    wanted={r['scenario']['id']:r['expected'] for r in read(PREP/'cases.json')['cases']}
    outcomes={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']}
    assert outcomes==wanted
    save(HERE/'outcomes.json',outcomes);save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,
        'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import payment_categories as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source','actual','law','complete','duplicate','qualification-override','tax-override',
                 'tax-exclusion','event','false-result','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='source':bad['context']['contract_readings'][0]['reading']='Different reading'
        elif kind=='actual':bad['actual_event_established']=True
        elif kind=='law':bad['historical_law_established']=True
        elif kind=='complete':bad['complete_legal_test']=True
        elif kind=='duplicate':bad['scenarios'].append(deepcopy(bad['scenarios'][1]))
        elif kind=='qualification-override':bad['scenarios'][1]['payment']['qualified_note_payment']=True
        elif kind=='tax-override':bad['scenarios'][1]['component_payable']=True
        elif kind=='tax-exclusion':bad['scenarios'][1]['tax'].pop('exception_e')
        elif kind=='event':bad['scenarios'][1]['payment']['clock']['event_id']='unrelated'
        elif kind=='false-result':actual[module.KEY]['scenarios'][1]['actual_default']='ESTABLISHED'
        else:actual['unicode_label_review']['meaning_admitted']=True
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('false-result','lost-prior'):
                module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}

def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],270)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result



def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'UNQUOTED_PAYMENT_CATEGORIES_IN_DEFAULT_ANALYSIS','baseline_unchanged':True,
        'installed_cli_equal':True,'actual_event_established':False,'resources':costs(),
        'next_action':'Continue remaining original source and scope obligations; retain conditional payment limits'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PREP/'cases.json'),'wall_time':costs(),
        'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Unquoted payment definitions reach conditional default analysis

The optional profile derives an express payment-inclusion route from the
principal and interest readings, retains every section7 qualification, and
supplies the result to the existing30-day payment calculation. Unknown other
payment routes remain open. No amounts are added and no actual obligation or
default is asserted. Ordinary and installed complete answers must agree.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain conditional composition|Independent full scenarios and flat-world oracle; complete CLI equality|Actual source/scenario/result misuse refused|Payment classification, source application, historical tax law and actual facts|Remaining original source and scope work|General interpretation, actual default or whole build|

This repairs our missing source-to-payment dependency. It supplies no evidence
of a fundamental external-package defect. The strongest alternative explanation
is an incorrect source classification or a wrong stipulated premise: Boolean
correctness cannot establish either in a real case. The proof applies only to
the declared independent primitive groups. Cross-group factual constraints,
multiple taxes or monetary calculations require a separately justified model.
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
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_payment_categories',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':300})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Payment category stage bound')));signal.alarm(300)
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
