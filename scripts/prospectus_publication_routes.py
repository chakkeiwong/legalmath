"""Same-task source route composition; prior methods and evidence stay frozen."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_affiliate_substitution as prior
from scripts import prospectus_h43_finalize as source
from scripts import prospectus_publication_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/h43-publication-321'
HERE=AUTH/'attempts/basf-references/attempt-060'
PLAN='docs/plans/prospectus-h43-publication-2026-10-19.md'
METHOD='scripts/prospectus_publication_routes.py';WORKER='scripts/prospectus_publication_installed.py'
ORACLE='scripts/prospectus_publication_oracle.py';TEST='tests/prospectus_successor/test_publication_routes.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/publication_routes.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    products,_=prior.baseline();answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='be268f117f375430be7826fe48337d412f26a409ed33141f2824dea532fe8e85'
    return products,answer


def testfiles():return [TEST,*prior.testfiles()]


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0321.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<14400 and size<2300*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':14400,'bytes_bound_with_4MiB_reserve':2304*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==320
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==59 and any(e['kind']=='RECORD' and e.get('attempt')==rel(source.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':source.resources(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    candidate=PREP/'candidate/publication_routes.py';spec=importlib.util.spec_from_file_location('legalmath.prospectus._publication_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();source_context=module.context(products,ordinary,ROOT)
    rows=oracle.scenarios(products['P1']['payload']['request']['bundle']['instrument_id'])
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'context':source_context,'scenarios':rows,'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{r['id']:oracle.expected(r) for r in rows})
    text=(ROOT/TARGETS[1]).read_text();old='            affiliate_profile=None, expected_affiliate_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,'            affiliate_profile=None, expected_affiliate_profile_sha256=None,'+chr(10)+'            publication_profile=None, expected_publication_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new="""    if publication_profile is not None:
        from ..publication_routes import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['publication_routes_review'] = evaluate(products, baseline, publication_profile, root,
            expected_profile_sha256=expected_publication_profile_sha256)
    elif expected_publication_profile_sha256 is not None:
        raise ValueError('Publication profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'notice_delivery', 'affiliate')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'notice_delivery', 'affiliate', 'publication')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'publication','path':rel(PREP/'profile.json'),'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text((ROOT/PLAN).read_text())
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,'scripts/prospectus_calendar_oracle.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    for p in (source.HERE/'outputs.json',source.HERE/'SOURCE-REVIEW.md',
              ROOT/'scripts/prospectus_h43_finalize.py',ROOT/'scripts/prospectus_h43_accounting.py'):
        bindings[rel(p)]=sha(p)
    for n in module.SOURCE_HASHES:bindings[module.SOURCE+n]=sha(ROOT/(module.SOURCE+n))

    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=321
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Integrate current H43 scope and two publication readings without false historical applicability',
        publication_routes={'review':rel(PREP),'original_task_complete':False,'combined_seconds':14400,'combined_bytes':2304*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=60
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=321
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify source-qualified H43 routes; continue source edition, definition and generalization gaps',
            stop_condition='60 admissions;240s stages;combined14400s/2304MiB;no GETs or unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+900,'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<14400 and forecast['bytes']<2300*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Current H43 full source and two conditional readings in complete answer','Keep historical H43 uncertainty and all prior fields'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent four-valued routes and qualified cases; ordinary/installed full answer equality',
            'promotion_veto':['False historical applicability','Omitted duty','Changed source','Selected unproved interpretation','Prior answer lost'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Actual publication','Full legal validity','General interpretation','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':59,'new_maximum':60,'retained_attempts':attempts,
            'reason':'Retained current H43 source needs qualified actual downstream interpretation',
            'next_discriminating_check':'Issuer and information qualifications, reporting duties and diverging section13 readings reach complete answer',
            'stop_condition':'240s stages;combined14400s/2304MiB;no new GETs or unchanged retry',
            'same_scope_authorization':'User requested continued internally established general build'},
        'resource_revision':{'previous_seconds':12600,'new_seconds':14400,
            'previous_bytes':2048*1024**2,'new_bytes':2304*1024**2,'reserve_bytes':4*1024**2,
            'all_prior_costs_retained':True,'reason':'Full ordinary/installed answers plus duplicated authority metadata require explicit headroom'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':321,'scenarios':len(rows),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus import publication_routes as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],225)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    expected=read(PREP/'expected.json')
    for r in actual[module.KEY]['scenarios']:
        want=expected[r['scenario']['id']]
        for key in ('qualified_information','statutory_conditions'):assert r[key]['status']==want[key]
        for key in ('german_seat_routes','conditional_contract_readings'):
            assert {k:v['status'] for k,v in r[key].items()}==want[key]
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import publication_routes as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source-omitted','source-condition','historical-promoted','missing-open','duplicate','share','seat-shortcut','missing-regulator','false-result','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='source-omitted':bad['context']['complete_current_section50']=''
        elif kind=='source-condition':bad['context']['contract_clauses'].pop()
        elif kind=='historical-promoted':bad['historical_application_proved']=True
        elif kind=='missing-open':bad['scenarios'].pop(0)
        elif kind=='duplicate':bad['scenarios'].append(deepcopy(bad['scenarios'][0]))
        elif kind=='share':bad['scenarios'][1]['identity']['security_kind']='SHARE'
        elif kind=='seat-shortcut':bad['scenarios'][1]['premises']['inlandsemittent']=True
        elif kind=='missing-regulator':bad['scenarios'][1]['premises'].pop('simultaneous_bafin_notification')
        elif kind=='false-result':actual[module.KEY]['scenarios'][0]['selected_interpretation']='broad_replacement'
        else:actual['residual_coverage_review']['H43']['status']='RESOLVED'
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
        'result_kind':'CONDITIONAL_H43_PUBLICATION_ROUTES','baseline_unchanged':True,'installed_cli_equal':True,
        'historical_application_proved':False,'resources':costs(),
        'next_action':'Continue historical applicability, original source scope and new-source profile preparation'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# H43 qualified publication routes reach the full answer

The complete current official provision and exact contractual paragraph reach
the ordinary and installed answers. Statutory issuer qualification, covered
information, implementation rules and concurrent reporting stay distinct.
Both section13 interpretations are evaluated; neither is selected. Separate
website duties remain. Prior H43 edition/application uncertainty and every
earlier answer field remain unchanged.

|Decision|Criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain conditional integration|Independent routes and complete ordinary/installed answers|Source,scope,missing-duty and false-promotion controls refused|Historical edition,issuer definition,implementing rules and facts|Original source and generalization work|Actual publication or whole-task acceptance|

The strongest alternative explanation remains a mismatch between current text
and applicable2022 law, or a different scope of the contractual alternative.
Those are explicit open premises and parallel readings. A relevant historical
source or governing interpretation can change the model. The engineering
addition repairs missing downstream source use; it does not prove all legal
readings or indicate a fundamental package limitation.
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
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_publication_routes',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':240})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Publication stage bound')));signal.alarm(240)
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
