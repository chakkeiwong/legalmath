"""Reviewed definition referents under the original prospectus master."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import ast,json,os,shutil,signal,sys,time
import xml.etree.ElementTree as ET
from scripts import prospectus_definition_context as prior
from scripts import prospectus_definition_referent_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/definition-referents-333'
HERE=AUTH/'attempts/basf-references/attempt-072'
PLAN='docs/plans/prospectus-definition-referents-2026-10-19.md'
METHOD='scripts/prospectus_definition_referent.py'
WORKER='scripts/prospectus_definition_referent_installed.py'
ORACLE='scripts/prospectus_definition_referent_oracle.py'
TEST='tests/prospectus_successor/test_definition_referents.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_definition_referent_cases.py')
TARGETS=tuple('src/legalmath/prospectus/successor/'+n for n in
    ('definition_referents.py','definition_referents_spec.json','service.py','conditional_profiles.py'))
STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
PRODUCTS=prior.prior.PRODUCTS

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
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0333.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert measured+charged<18000 and size<2684*1024**2,'Cumulative referent resource bound'
    return {'combined_measured_seconds':measured,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':measured+charged,'combined_bytes':size,'seconds_bound':18000,
        'bytes_bound_with_4MiB_reserve':2688*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}

def testfiles():return [TEST,*prior.testfiles()]

def install():
    for row in read(PREP/'installation.json'):
        path=ROOT/row['target'];assert (sha(path) if path.exists() else None)==row['before']
        shutil.copyfile(ROOT/row['candidate'],path)
    return {'status':'PASS','production_files':len(TARGETS)}

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==332
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==71 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
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
    save(PREP/'candidate/definition_referents_spec.json',spec)
    module=PREP/'candidate/definition_referents.py';body=module.read_text()
    assert body.count('SPEC_SHA256 = None')==1
    module.write_text(body.replace('SPEC_SHA256 = None','SPEC_SHA256 = '+repr(digest(spec))))
    profile={'version':oracle.VERSION,'products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],'specification_sha256':digest(spec),
        'whole_task_complete':False,'legal_truth_established':False}
    save(PREP/'profile.json',profile)
    manifest=read(prior.PREP/'profiles.json')
    manifest['profiles'].append({'name':'definition_referents','path':rel(PREP/'profile.json'),
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
    proposal=deepcopy(program);proposal['revision']=333
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Preserve276note/issuer/holder occurrence referents including generic debt, other creditors and conditional succession',
        definition_referent_review={'review':rel(PREP),'original_task_complete':False,
            'accounted_seconds_bound':18000,'bytes_bound_with_4MiB_reserve':2688*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=72
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=333
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify276source referents through whole ordinary/installed answers; continue231other associations and original acceptance',
            stop_condition='72admissions;900s/128MiBforecast;18000accounted seconds/2688MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+900,
        'bytes':snapshot['combined_bytes']+128*1024**2,'estimate_only':True}
    assert forecast['seconds']<18000 and forecast['bytes']<2684*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Exact276referent decisions retain complete612associations and prior answer',
                   'No new external prerequisite and no cumulative bound reset'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent complete source-referent answer and fresh installed equality',
            'promotion_veto':['Wrong referent','Lost qualification','Heading promoted','Lost use','Wrong import'],
            'continuation_veto':['Corrupt baseline','Frozen drift','Cumulative bound'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Other231uses','Actual facts','Historical law','Legal truth','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':71,'new_maximum':72,
            'retained_attempts':attempts,'reason':'071leaves507associations;276inspected note/issuer/holder uses give source-specific continuation',
            'next_discriminating_check':'Generic debt, other creditors, heading and named/original/successor distinctions with612retention',
            'stop_condition':'900s/128MiBforecast;18000accounted seconds/2688MiBwith4MiBreserve;no unchanged retry',
            'same_scope_authorization':'User requested continued general build and internally supported correctness'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':333,'candidate_evaluated':False,'forecast':forecast}

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
    from legalmath.prospectus.successor import definition_referents as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],330)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    result=oracle.verify(actual,ordinary,products,profile,read(PREP/'expected-content.json'))
    save(HERE/'independent-verification.json',result)
    save(HERE/'verification.json',module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile)))
    return {**result,'actual_cli':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}

def controls():
    from legalmath.prospectus.successor import definition_referents as module
    products,ordinary=baseline();profile=read(PREP/'profile.json');content=read(PREP/'expected-content.json')
    actual=read(HERE/'ordinary-answer.json.gz');refused={}
    for kind in ('missing-use','generic-as-series','other-creditor-as-holder','successor-as-fact',
                 'heading-as-operative','lost-qualification','lost-question','false-completion'):
        bad=deepcopy(actual);uses=bad[module.KEY]['uses']
        if kind=='missing-use':uses.pop()
        elif kind=='generic-as-series':next(u for u in uses if u['record']=='D01-notes' and u['start']==6200)['referent_binding']['referent']='DEFINED_SERIES'
        elif kind=='other-creditor-as-holder':next(u for u in uses if u['record']=='D12-holder' and u['start']==30233)['referent_binding']['referent']='CONTRACTUAL_COOWNER_OR_COMPARABLE_RIGHT_HOLDER'
        elif kind=='successor-as-fact':next(u for u in uses if u['record']=='D01-notes' and u['start']==33710)['referent_binding']['qualification']='Substitution completed'
        elif kind=='heading-as-operative':next(u for u in uses if u['record']=='D02-issuer' and u['start']==34215)['disposition']='BOUND_REFERENT'
        elif kind=='lost-qualification':next(u for u in uses if u['referent_binding'] is not None)['referent_binding']['meaning']['reading']['qualification']=''
        elif kind=='lost-question':bad['questions']['Q1']['unresolved']=[]
        else:bad[module.KEY]['all_governing_uses_established']=True
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
    answer=read(HERE/'ordinary-answer.json.gz');counts=dict(Counter(u['disposition'] for u in answer[oracle.KEY]['uses']))
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'EXACT_SOURCE_DEFINITION_REFERENTS','associations':counts,
        'independent_whole_answer_equal':True,'installed_answer_equal':True,'resources':costs(),
        'next_action':'Continue231other associations, typed agency classification and original-task acceptance without erasing ambiguity'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Notes, issuer and holder referents

The normal and fresh installed answers preserve the complete prior answer and
276 additional source decisions:260 ordinary referents,2 conditional referents,
10 heading mentions,2 name components,1 generic security class and1 reference to
other creditors. All612 associations remain. Existing issuer and successor
obligations, further notes, actual facts and source uncertainty remain distinct.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite referent correspondence|Frozen whole answer and installed equality|Source, identity, qualification and forgery controls refused|231 other associations and unproved factual/historical premises|Continue original source and acceptance work|Legal truth, general recall, whole task or whole build|

Comparison is exact equality of complete parsed JSON values. Serialized file
hashes can differ. The strongest alternative explanation is a shared error in
the supplied source interpretation. A contrary source referent or missing
condition would overturn that decision. Internal checks establish software
correspondence to an inspected conditional interpretation, not an external legal
opinion or future-proof interpretation of every source.
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
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_referent',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Referent stage bound')));signal.alarm(bound)
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
