"""Source citation context with exact projections and preserved original answers."""
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,shutil,signal,sys,time
import xml.etree.ElementTree as ET
from scripts import prospectus_reference_scope as prior
baseline_run = prior.baseline_run
from scripts import prospectus_reference_scope_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/reference-scope-headers-344';HERE=AUTH/'attempts/basf-references/attempt-083'
PLAN='docs/plans/prospectus-reference-scope-header-repair-2026-10-19.md'
METHOD='scripts/prospectus_reference_scope_header_repair.py';WORKER='scripts/prospectus_reference_scope_installed.py'
TEST='tests/prospectus_successor/test_reference_scope.py';ORACLE='scripts/prospectus_reference_scope_oracle.py'
EXTRA_TEST='tests/prospectus_successor/test_reference_scope_headers.py'
FILES=(PLAN,METHOD,WORKER,TEST,ORACLE,EXTRA_TEST,'scripts/prospectus_reference_scope_cases.py',
    'tests/prospectus_successor/conftest.py')
TARGETS=('src/legalmath/prospectus/successor/reference_scope.py',)
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
PRODUCTS=baseline_run.PRODUCTS

def baseline():
    manifest=read(PRODUCTS);products={k:read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=read(baseline_run.HERE/'ordinary-answer.json.gz');freeze=read(PREP/'source-freeze.json')
    assert digest(products)==freeze['products_sha256'] and digest(answer)==freeze['ordinary_answer_sha256']
    return products,answer

def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior']
    seconds=base['combined_measured_seconds']+read(PREP/'source-freeze.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0344.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-start['production_bytes'][n]) for n in TARGETS if (ROOT/n).exists())
    charged=base['conservative_extra_seconds']
    assert seconds+charged<21600 and size<3196*1024**2,'Cumulative reference-context resource bound'
    return {'combined_measured_seconds':seconds,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':seconds+charged,'combined_bytes':size,'seconds_bound':21600,
        'bytes_bound_with_4MiB_reserve':3200*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN;never treated as zero'}

def testfiles():return [TEST,EXTRA_TEST,'tests/prospectus_successor/test_paragraph_references.py',
    'tests/prospectus_successor/test_conditional_profiles_cli.py',
    'tests/prospectus_successor/test_reference_requirements.py',
    'tests/prospectus_successor/test_reference_requirement_raw_copies.py',
    'tests/prospectus_successor/test_reference_requirement_order.py']

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==343
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==82 and any(e['kind']=='REJECT' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    for n,v in read(prior.PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for r in read(prior.PREP/'installation.json'):assert sha(ROOT/r['target'])==r['after']
    frozen=read(PREP/'source-freeze.json');assert frozen['candidate_absent'] is True
    assert sha(PREP/'expected.json')==frozen['expected_sha256'] and sha(ROOT/prior.PLAN)==frozen['plan_sha256']
    assert sha(PREP/'expected.json')==sha(prior.PREP/'expected.json')
    spec=read(PREP/'candidate/reference_scope_spec.json')
    profile=read(prior.PREP/'profile.json');save(PREP/'profile.json',profile)
    manifest=read(prior.PREP/'profiles.json')
    save(PREP/'profiles.json',manifest);(PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name
        if candidate.suffix=='.py':ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,*testfiles(),'pyproject.toml',prior.METHOD,baseline_run.METHOD,'scripts/prospectus_residual_coverage.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',baseline_run.HERE/'outputs.json',baseline_run.HERE/'ordinary-answer.json.gz',PRODUCTS):bindings[rel(p)]=sha(p)
    for r in read(PRODUCTS)['products'].values():bindings[r['path']]=r['sha256']
    for r in manifest['profiles']:bindings[r['path']]=r['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=344;task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair reproduced stale auxiliary header lookup using exact current-P2 source bindings; retain original context expectations and unresolved legal targets',
        reference_scope_header_review={'review':rel(PREP),'original_task_complete':False,'accounted_seconds_bound':21600,'bytes_bound_with_4MiB_reserve':3200*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=83
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=344
    for r in routes['tasks']:
        if r['task']=='basf-references':r.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify unchanged30contexts using current source headers; retain failed082 and return to remaining target/definition work',
            stop_condition='83admissions;800s/68MiBforecast;21600accounted seconds/3200MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+800,'bytes':snapshot['combined_bytes']+68*1024**2,'estimate_only':True}
    assert forecast['seconds']<21600 and forecast['bytes']<3196*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Repair stale auxiliary heading lookup with exact current P2 role and source bindings','Preserve all original sources,answers and unresolved target/semantic requirements'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Frozen literal source/grammar expectations,independent source mapping,complete ordinary/installed equality',
            'promotion_veto':['Source offset/token differs','Incomplete syntax promoted','Target invented','Prior answer changed','Installed mismatch'],
            'continuation_veto':['Corruption','Frozen drift','Cumulative bound'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['General recall','Target resolution','Legal interpretation','Actual facts','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':82,'new_maximum':83,'retained_attempts':attempts,
            'reason':'082real-source test rejects eleven wrong enclosing sections because auxiliary definition-source heading associations are stale',
            'next_discriminating_check':'Unchanged30contexts,positive missing-auxiliary regression,source/map refusals and complete fresh installed equality',
            'stop_condition':'800s/68MiBforecast;21600seconds/3200MiB cumulative;no unchanged retry',
            'same_scope_authorization':'User requested complete internally supported build and continued source-specific repairs'},
        'resource_accounting':{'retained_costs':snapshot,'seconds_bound':21600,'bytes_with_reserve':3200*1024**2,'limits_extended':False}}
    with (PREP/'proposal.json').open('x') as stream:json.dump(proposal,stream,ensure_ascii=False,separators=(',',':'))
    assert read(PREP/'proposal.json')==proposal
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':344,'candidate_evaluated':False,'forecast':forecast}

def install():
    for r in read(PREP/'installation.json'):
        p=ROOT/r['target'];assert (sha(p) if p.exists() else None)==r['before'];shutil.copyfile(ROOT/r['candidate'],p)
    return {'status':'PASS','production_files':len(TARGETS)}

def tests():
    prior_collection=(prior.HERE/'commands/collection.log').read_text()
    assert 'test_reference_requirement_copies.py::' not in prior_collection
    assert 'test_reference_requirement_raw_copies.py::test_production_direct_copy_passes' in prior_collection
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],120)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS',**counts}

def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]

def consume():
    from legalmath.prospectus.successor import reference_scope as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],330)
    p,old=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    independent=oracle.verify(actual,old,p,read(PREP/'expected.json'));save(HERE/'independent-verification.json',independent)
    save(HERE/'verification.json',module.verify_answer(actual,old,profile,p,ROOT,expected_profile_sha256=digest(profile)))
    return {**independent,'actual_cli':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}

def controls():
    p,old=baseline();actual=read(HERE/'ordinary-answer.json.gz');expected=read(PREP/'expected.json');refused={}
    for kind in ('context-delete','section-change','statute-change','scope-change','source-shift',
                 'projection-delete','separator-invention','false-target','false-completion','prior-answer'):
        bad=deepcopy(actual);report=bad[oracle.KEY];row=report['contexts'][0]
        if kind=='context-delete':report['contexts'].pop()
        elif kind=='section-change':row['explicit_section']='99'
        elif kind=='statute-change':report['contexts'][11]['statute']='BGB'
        elif kind=='scope-change':row['enclosing_section']='99'
        elif kind=='source-shift':row['start']+=1
        elif kind=='projection-delete':row['source_projection'].pop()
        elif kind=='separator-invention':
            split=next(r for r in report['contexts'] if r['paragraph_start']==8571)
            next(v for v in split['source_projection'] if v['source'] is None)['text']=' '
        elif kind=='false-target':row['target']='approved-target'
        elif kind=='false-completion':report['whole_task_complete']=True
        else:bad['questions']['Q1']['status']='YES'
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,old,p,expected)
        except AssertionError:refused[kind]=True
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}

def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),str(PREP)],330)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result

def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_CITATION_CONTEXT_CURRENT_HEADERS','source_contexts':30,
        'target_resolution_established':False,'ordinary_installed_equal':True,'resources':costs(),
        'obsolete_fixture_retained':True,'active_replacement_verified':True,
        'next_action':'Assess remaining target/definition discovery work against cumulative resources; continue independent authorized tasks'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PRODUCTS),'wall_time':costs(),
        'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Complete citation context reaches the normal answer

Thirty source expressions retain full adjacent section qualifiers and their
original source projections. Four explicitly named statutes remain distinguished
from unqualified section numbers. The cross-page section1/paragraph3(b)
expression now preserves both source lines and the generated separator. Its
overlap with a retained source reference is evidence of lexical correspondence,
not proof of a legal target. Enclosing headings provide source context only.

The current header lookup verifies P2 role,document,page,raw hash and character map.
The failed082auxiliary-list lookup remains retained with unchanged expectations.

The exact obsolete339fixture remains unchanged. Normal collection excludes only
those frozen bytes; the active constructor-based replacement and its adverse
hash cases pass. This repairs test selection, not source-hash semantics.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional citation context|Exact source/grammar expectations and complete installed equality|Changed sources,scope,targets and old answers refused|Unseen grammar,legal targets,historical application|Bounded target/definition work or independent ready task|General recall,legal meaning or whole build|

The strongest alternative explanation is an unsupported qualifier form outside
the finite grammar. Unknown forms and target meaning remain explicit. All prior
answers,admissions,failures and resource costs remain retained.
""")
    return result

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage;assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    else:
        for s in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/s/'result.json')['status']=='PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    engine.PREP,engine.HERE,engine.PLAN,engine.METHOD,engine.WORKER,engine.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
    engine.costs,engine.testfiles,engine.cli_arguments=costs,testfiles,cli_arguments
    bound=90 if stage=='prepare' else 360
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_reference_scope_header_repair',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Reference scope stage bound')));signal.alarm(bound)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(engine,stage))()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as e:
        save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
