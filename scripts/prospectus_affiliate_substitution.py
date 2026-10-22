"""Same-task source route composition; prior methods and evidence stay frozen."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_notice_delivery as prior
from scripts import prospectus_affiliate_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/affiliate-substitution-318'
HERE=AUTH/'attempts/basf-references/attempt-057'
PLAN='docs/plans/prospectus-affiliate-substitution-2026-10-19.md'
METHOD='scripts/prospectus_affiliate_substitution.py';WORKER='scripts/prospectus_affiliate_installed.py'
ORACLE='scripts/prospectus_affiliate_oracle.py';TEST='tests/prospectus_successor/test_affiliate_substitution.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/affiliate_substitution.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    products,_=prior.baseline();answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='256b0462a51df662c50e97d08497c45354bec810ee09ea02bcd4e28a602b8f4f'
    return products,answer


def testfiles():return [TEST,*prior.testfiles()]


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0318.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<12600 and size<2044*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==317
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==56 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    candidate=PREP/'candidate/affiliate_substitution.py';spec=importlib.util.spec_from_file_location('legalmath.prospectus._affiliate_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();source=module.context(products,ordinary)
    rows=oracle.scenarios(products['P1']['payload']['request']['bundle']['instrument_id'])
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'context':source,'scenarios':rows,'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{r['id']:oracle.expected(r) for r in rows})
    text=(ROOT/TARGETS[1]).read_text();old='            notice_delivery_profile=None, expected_notice_delivery_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,'            notice_delivery_profile=None, expected_notice_delivery_profile_sha256=None,'+chr(10)+'            affiliate_profile=None, expected_affiliate_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new="""    if affiliate_profile is not None:
        from ..affiliate_substitution import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['affiliate_substitution_review'] = evaluate(products, baseline, affiliate_profile, root,
            expected_profile_sha256=expected_affiliate_profile_sha256)
    elif expected_affiliate_profile_sha256 is not None:
        raise ValueError('Affiliate profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'agent_notice', 'notice_delivery')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'agent_notice', 'notice_delivery', 'affiliate')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'affiliate','path':rel(PREP/'profile.json'),'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text("""# Affiliate substitution skeptical audit

PASS: exact H35 with full15-19/291/292 excerpts, five qualified alternatives,
legal independence and complete contractual prerequisites retained. Category
facts are hypothetical full relations, never raw stakes or parent labels.
Historical applicability and issuer election remain separate. Required lawyers
confirmations are a contractual receipt premise,not external program approval.
Notice and document duties remain open. Independent truth enumeration and all
missing/false/conflicting prerequisites precede full ordinary/installed checks.
Prior answers, profiles, failed attempts and all costs remain unchanged.
""")
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,'scripts/prospectus_calendar_oracle.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=318
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Compose H35 qualified affiliate alternatives and complete contractual substitution prerequisites',
        affiliate_substitution={'review':rel(PREP),'original_task_complete':False,'combined_seconds':12600,'combined_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=57
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=318
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify H35 alternatives and substitution prerequisites;continue H43 and historical/source gaps',
            stop_condition='57 reference admissions;210s stages;combined12600s and2048MiB;no external calls')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+850,'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Qualified H35 alternatives and substitution prerequisites reach full answer','Preserve all original source gaps','Same reference task admission56to57;retain combined costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent exhaustive categories and prerequisite cases;complete prior answer;ordinary and installedCLI equality',
            'promotion_veto':['Wrong alternatives','Missing contractual condition','Lost unknowns','False substitution','Source drift','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Full legal validity','Actual change','Office authority','General interpretation']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':56,'new_maximum':57,'retained_attempts':attempts,
            'reason':'H35 category alternatives and substitution prerequisites remained prose-only in the complete answer',
            'next_discriminating_check':'Each affiliate alternative and each missing contractual prerequisite affects the full answer without actual-event promotion',
            'stop_condition':'210s stages;combined12600s and2048MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested continued internally established general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':318,'scenarios':len(rows),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus import affiliate_substitution as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    expected=read(PREP/'expected.json')
    for r in actual[module.KEY]['scenarios']:
        want=expected[r['scenario']['id']]
        for key,value in want.items():assert r[key]['status']==value
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import affiliate_substitution as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source-omitted','source-condition','actual-promoted','missing-open','duplicate','same-company','parent-label','missing-confirmation','false-result','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='source-omitted':bad['context']['H35']['legal_sources'][0]['excerpts'].pop()
        elif kind=='source-condition':bad['context']['contract_clauses'][0]['quote']='affiliate only'
        elif kind=='actual-promoted':bad['actual_event_established']=True
        elif kind=='missing-open':bad['scenarios'].pop(0)
        elif kind=='duplicate':bad['scenarios'].append(deepcopy(bad['scenarios'][0]))
        elif kind=='same-company':bad['scenarios'][1]['identity']['successor']=bad['scenarios'][1]['identity']['issuer']
        elif kind=='parent-label':bad['scenarios'][1]['affiliate_categories']['parent_company']=True
        elif kind=='missing-confirmation':bad['scenarios'][1]['prerequisites'].pop('required_lawyer_confirmations_received_by_fiscal_agent')
        elif kind=='false-result':actual[module.KEY]['scenarios'][0]['listed_prerequisites']['status']='YES'
        else:actual['notice_delivery_review']['complete_legal_test']=True
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('false-result','lost-prior'):module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'CONDITIONAL_AFFILIATE_SUBSTITUTION_COMPOSITION',
        'baseline_unchanged':True,'installed_cli_equal':True,'resources':costs(),
        'next_action':'Continue H43,historical source application,ownership attribution and new-source preparation'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Qualified affiliate alternatives reach substitution analysis

The complete ordinary and installed answers now distinguish all five retained
section15 alternatives and legal independence, with separate applicability.
Every modeled contractual substitution prerequisite and issuer election stays
explicit. A parent label or an assumed affiliated-company bit is not accepted.
The express lawyers-confirmation receipt remains a hypothetical contractual
fact,not an external requirement for approval of this program. Actual company
relations,substitution and onward notice/document duties remain unproved.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite composition|Independent truth and complete ordinary/installed answers|Missing conditions,source changes,identity shortcuts and false promotion refused|Historical law,qualified company facts and source completeness|Original reference/source gaps|Actual affiliation,substitution or whole build|

The repair addresses our missing conditional composition,not package failure.
Shared error in supplied source readings remains an alternative explanation;
truth-table agreement alone cannot prove historical applicability or factual
company relations. A missing statutory category or contractual condition would
invalidate this interpretation. Original H43 and all prior fields remain.
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
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_affiliate_substitution',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Affiliate stage bound')));signal.alarm(210)
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
