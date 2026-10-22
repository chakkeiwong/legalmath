"""Reviewed definition dependencies under the original prospectus master."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import ast,json,os,shutil,signal,sys,time
import xml.etree.ElementTree as ET
from scripts import prospectus_definition_remainder as prior
from scripts import prospectus_definition_dependency_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/definition-dependencies-335'
HERE=AUTH/'attempts/basf-references/attempt-074'
PLAN='docs/plans/prospectus-definition-dependencies-2026-10-19.md'
METHOD='scripts/prospectus_definition_dependency.py'
WORKER='scripts/prospectus_definition_dependency_installed.py'
ORACLE='scripts/prospectus_definition_dependency_oracle.py'
TEST='tests/prospectus_successor/test_definition_dependencies.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_definition_dependency_cases.py')
TARGETS=tuple('src/legalmath/prospectus/successor/'+n for n in
    ('definition_dependencies.py','definition_dependencies_spec.json','service.py','conditional_profiles.py'))
STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
PRODUCTS=prior.PRODUCTS

def baseline():
    products,_=prior.baseline();answer=read(prior.HERE/'ordinary-answer.json.gz')
    freeze=read(PREP/'cases-freeze.json')
    assert digest(products)==freeze['products_sha256'] and digest(answer)==freeze['ordinary_answer_sha256']
    return products,answer

def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior']
    measured=base['combined_measured_seconds']+read(PREP/'case-preparation.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            measured+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged=base['conservative_extra_seconds']
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0335.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert measured+charged<19800 and size<2940*1024**2,'Cumulative referent resource bound'
    return {'combined_measured_seconds':measured,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':measured+charged,'combined_bytes':size,'seconds_bound':19800,
        'bytes_bound_with_4MiB_reserve':2944*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}

def testfiles():return [TEST,*prior.testfiles()]

def install():
    for row in read(PREP/'installation.json'):
        path=ROOT/row['target'];assert (sha(path) if path.exists() else None)==row['before']
        shutil.copyfile(ROOT/row['candidate'],path)
    return {'status':'PASS','production_files':len(TARGETS)}

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==334
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==73 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v
    for n,v in read(prior.PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(prior.PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after']
    frozen=read(PREP/'cases-freeze.json');assert frozen['candidate_absent'] is True
    for name,key in [('source-decisions.json','source_decisions_sha256'),('expected-content.json','expected_file_sha256')]:
        assert sha(PREP/name)==frozen[key]
    assert sha(ROOT/PLAN)==frozen['plan_sha256'] and sha(ROOT/ORACLE)==frozen['oracle_sha256']
    spec={'version':oracle.VERSION,'products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],
        'expected_content_sha256':frozen['expected_content_sha256'],'decisions':read(PREP/'source-decisions.json')}
    save(PREP/'candidate/definition_dependencies_spec.json',spec)
    module=PREP/'candidate/definition_dependencies.py';body=module.read_text()
    assert body.count('SPEC_SHA256 = None')==1
    module.write_text(body.replace('SPEC_SHA256 = None','SPEC_SHA256 = '+repr(digest(spec))))
    profile={'version':oracle.VERSION,'products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],'specification_sha256':digest(spec),
        'whole_task_complete':False,'legal_truth_established':False}
    save(PREP/'profile.json',profile)
    manifest=read(prior.PREP/'profiles.json')
    manifest['profiles'].append({'name':'definition_dependencies','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest);(PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path,candidate=ROOT/target,PREP/'candidate'/(ROOT/target).name
        if candidate.suffix=='.py':ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,
            'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,*testfiles(),prior.METHOD,prior.WORKER,prior.ORACLE,
        'scripts/prospectus_residual_coverage.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',PRODUCTS):bindings[rel(path)]=sha(path)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for row in manifest['profiles']:bindings[row['path']]=row['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=335
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Apply all612reviewed definition occurrences and78remaining premises to actual question dependencies without promoting answers',
        definition_dependency_review={'review':rel(PREP),'original_task_complete':False,
            'accounted_seconds_bound':19800,'bytes_bound_with_4MiB_reserve':2944*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=74
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=335
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify current question dependency projection; continue original acceptance, supported source scope and raw rating classification',
            stop_condition='74admissions;900s/160MiBforecast;19800accounted seconds/2944MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+900,
        'bytes':snapshot['combined_bytes']+160*1024**2,'estimate_only':True}
    assert forecast['seconds']<19800 and forecast['bytes']<2940*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Replace only generic definition blockers with exact remaining premises in five current question paths',
                   'Retain all prior evidence,costs,73admissions and19800second/2944MiBbound'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent complete current-question projection and fresh installed equality',
            'promotion_veto':['Lost premise','Altered nondefinition blocker','Changed answer status','Lost use','Wrong import'],
            'continuation_veto':['Corrupt baseline','Frozen drift','Cumulative bound'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['General discovery','Actual facts','Historical law','Legal truth','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':73,'new_maximum':74,
            'retained_attempts':attempts,'reason':'073reviews every finite use but the current questions still carry generic unreviewed markers',
            'next_discriminating_check':'Exact occurrence-linked remaining reasons in Q1,Q2 and every Q2subquestion; all other answer values preserved',
            'stop_condition':'900s/160MiBforecast;19800accounted seconds/2944MiBwith4MiBreserve;no unchanged retry',
            'same_scope_authorization':'User requested continued general build and internally supported correctness'}}
    review['resource_accounting']={'accounted_seconds_bound':19800,'bytes_with_reserve':2944*1024**2,
        'retained_costs':snapshot,'limits_extended':False}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':335,'candidate_evaluated':False,'forecast':forecast}

def tests():
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],
        '-q','--junitxml='+str(HERE/'pytest.xml')],150)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS',**counts}

def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),
        '--output',str(HERE/output),'--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),
        '--conditional-profiles-sha256',sha(PREP/'profiles.json')]

def consume():
    from legalmath.prospectus.successor import definition_dependencies as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],330)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    result=oracle.verify(actual,ordinary,products,profile,read(PREP/'expected-content.json'))
    save(HERE/'independent-verification.json',result)
    save(HERE/'verification.json',module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile)))
    return {**result,'actual_cli':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}

def controls():
    from legalmath.prospectus.successor import definition_dependencies as module
    products,ordinary=baseline();profile=read(PREP/'profile.json');content=read(PREP/'expected-content.json')
    actual=read(HERE/'ordinary-answer.json.gz');refused={}
    for kind in ('missing-occurrence','lost-premise','lost-question-premise','lost-discovery',
                 'lost-other-blocker','false-answer','changed-witness','forgotten-subquestion',
                 'changed-prior-review','false-completion'):
        bad=deepcopy(actual);report=bad[module.KEY];question=bad['questions']['Q1']
        if kind=='missing-occurrence':report['records'][0]['occurrences'].pop()
        elif kind=='lost-premise':report['records'][0]['remaining_premises'].pop()
        elif kind=='lost-question-premise':
            question['unresolved'].remove(next(v for v in question['unresolved'] if v.startswith('definition-premise:')))
        elif kind=='lost-discovery':question['unresolved'].remove(module.DISCOVERY)
        elif kind=='lost-other-blocker':question['unresolved'].remove(next(v for v in question['unresolved'] if not v.startswith('definition-')))
        elif kind=='false-answer':question.update(status='YES',value=True)
        elif kind=='changed-witness':question['witnesses']=['invented']
        elif kind=='forgotten-subquestion':bad['questions']['Q2']['subquestions']['common_only']=deepcopy(ordinary['questions']['Q2']['subquestions']['common_only'])
        elif kind=='changed-prior-review':bad['definition_remainder_review']['uses'][0]['remaining']=[]
        else:report['whole_task_complete']=True
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,ordinary,products,profile,content)
        except AssertionError as e:refused[kind]=str(e)
        else:raise AssertionError('Accepted '+kind)
    for kind in ('rehashed-answer','rehashed-product','rehashed-spec','legal-truth'):
        oo,pp,pr=deepcopy(ordinary),deepcopy(products),deepcopy(profile)
        if kind=='rehashed-answer':oo['questions']['Q1']['status']='YES'
        elif kind=='rehashed-product':pp['P2']['payload']['assembly']['continuous_text']+='x'
        elif kind=='rehashed-spec':pr['specification_sha256']='0'*64
        else:pr['legal_truth_established']=True
        oo['report_sha256']=digest({k:v for k,v in oo.items() if k!='report_sha256'})
        pr['ordinary_answer_sha256'],pr['products_sha256']=digest(oo),digest(pp)
        try:module.evaluate(pp,oo,pr,ROOT,expected_profile_sha256=digest(pr))
        except ValueError as e:refused[kind]=str(e)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}

def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),str(PREP)],330)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result

def seal():
    answer=read(HERE/'ordinary-answer.json.gz');report=answer[oracle.KEY]
    counts={'records':len(report['records']),'associations':sum(len(r['occurrences']) for r in report['records']),
        'remaining_premises':sum(len(r['remaining_premises']) for r in report['records']),
        'question_paths':len(report['question_links'])}
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_REVIEWED_QUESTION_DEPENDENCIES','coverage':counts,
        'independent_whole_answer_equal':True,'installed_answer_equal':True,'resources':costs(),
        'next_action':'Continue original-task acceptance, supported source scope, unresolved interpretation and raw rating classification'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Reviewed definitions reach the current questions

The normal and fresh installed answers replace62 generic definition markers
with78 exact remaining premises and one finite-discovery limit in Q1,Q2 and
the threeQ2subquestions. All612 occurrence identities, previous source reports,
nondefinition blockers, answer statuses, values and witnesses remain intact.
The current questions now expose the reviewed conditional state without
asserting the missing facts or legal interpretations.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain downstream dependency projection|Frozen complete answer and installed equality|Lost premise, changed answer and forgery controls refused|Supplied interpretations and unproved factual/historical premises|Original acceptance and supported source scope|Legal truth, general recall, whole task or whole build|

Comparison is exact equality of complete parsed JSON values. Serialized file
hashes can differ. The strongest alternative explanation is a shared error in
the supplied source interpretation. A contrary source referent or missing
condition would overturn that decision. Internal checks establish software
correspondence to an inspected conditional interpretation, not an external legal
opinion or future-proof interpretation of every source. Every prior cost and
73earlier admissions remain charged. The cumulative19800second/2944MiBbound,
including4MiB reserve, is unchanged; older unmeasured time remains UNKNOWN.
''')
    return result

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':
        save(PREP/'accounting-start.json',{'prior':prior.costs(),
            'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
            'program_bytes':(AUTH/'program.json').stat().st_size,
            'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    else:
        for s in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/s/'result.json')['status']=='PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    engine.PREP,engine.HERE,engine.PLAN,engine.METHOD,engine.WORKER,engine.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
    engine.costs,engine.testfiles,engine.cli_arguments=costs,testfiles,cli_arguments
    bound=90 if stage=='prepare' else 360
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_dependency',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Dependency stage bound')));signal.alarm(bound)
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
