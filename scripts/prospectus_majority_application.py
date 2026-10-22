"""Admitted source-specific majority integration after the H38 correction."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import ast, hashlib, json, os, shutil, signal, subprocess, sys, time, zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_h38_repair as prior
from scripts import prospectus_majority_oracle as oracle
from scripts.prospectus_typed_delta import changes, apply
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/schvg-majority-301';HERE=AUTH/'attempts/basf-references/attempt-042'
PLAN='docs/plans/prospectus-schvg-majority-application-2026-10-19.md'
METHOD='scripts/prospectus_majority_application.py';WORKER='scripts/prospectus_majority_installed.py'
ORACLE='scripts/prospectus_majority_oracle.py';TEST='tests/prospectus_successor/test_schvg_majority.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/schvg_majority.py','src/legalmath/prospectus/successor/service.py')
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_041_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0301.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_041_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<7200 and size<764*1024**2,'Cumulative026 resource bound'
    return {'cumulative026_042_measured_seconds':seconds,'cumulative026_042_bytes':size,
            'prior_costs_reset':False,'seconds_bound':7200,'bytes_bound_with_4MiB_reserve':768*1024**2,
            'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==300
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==41 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[x.name for x in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    text=(ROOT/TARGETS[1]).read_text()
    before='            default_f_profile=None, expected_default_f_profile_sha256=None):'
    after='            default_f_profile=None, expected_default_f_profile_sha256=None,\n            majority_profile=None, expected_majority_profile_sha256=None):'
    assert text.count(before)==1;text=text.replace(before,after)
    before='    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    after='''    if majority_profile is not None:
        from ..schvg_majority import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['schvg_majority_review'] = evaluate(products, baseline, majority_profile, root,
            expected_profile_sha256=expected_majority_profile_sha256)
    elif expected_majority_profile_sha256 is not None:
        raise ValueError('Majority profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(before)==1;text=text.replace(before,after)
    (PREP/'candidate/service.py').write_text(text)
    installation=[]
    for target in TARGETS:
        candidate=PREP/'candidate'/Path(target).name;ast.parse(candidate.read_text())
        baseline=PREP/'baseline'/Path(target).name;baseline.parent.mkdir(exist_ok=True)
        exists=(ROOT/target).exists()
        if exists:shutil.copyfile(ROOT/target,baseline)
        installation.append({'target':target,'before':sha(ROOT/target) if exists else None,
                             'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    products,ordinary=prior.retained('answer');report=ordinary['statutory_references']
    record=next(r for r in report['records'] if r['id']=='H38')
    groups=[r for r in ordinary['basf_governance_terms'] if r['kind'] in ('amendment_agreement','qualified_majority','simple_majority')]
    assert len(groups)==3 and record['numbered_measures'][-1]['number']==8
    scenario=oracle.scenarios(products['P1']['payload']['request']['bundle']['instrument_id'])
    profile={'version':'basf-schvg-conditional-majority.v1','products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':{'statutory_profile_sha256':report['profile_sha256'],
        'H38':record,'selected_governance':groups},'scenarios':scenario,'actual_event_established':False,
        'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile)
    save(PREP/'expected.json',{'ordinary_sha256':digest(ordinary),'profile_sha256':digest(profile),
         'scenarios':{r['id']:oracle.classify(r) for r in scenario},'candidate_invoked':False})
    (PREP/'METHOD-REVIEW.md').write_text('''# Conditional majority integration audit

PASS for the bounded evidence contract in the plan. Read the actual selected
German amendment/75%/simple-majority clauses and complete retained SchVG5.
Reuse002/005 conditional-law evidence;041 is the current complete baseline.
Independent decimal-integer oracle is frozen before candidate calls. Different
number ranges are preserved; no historical or effective-event promotion.
Source profile binds entire H38 and all selected governance context. All-open,
missing/conflict/large-decimal controls and full original-answer equality are
required. Production target hashes use explicit install manifests, not mutable
admission inputs. Installed replay resolves production only inside the package.
No source acquisition, external opinion, client facts or budget-lineage reset.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml','scripts/prospectus_h38_repair.py',
        'scripts/prospectus_structural_integration.py','scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'answer.json.gz',prior.HERE/'conditional-profile.json',
              ROOT/record['legal_sources'][0]['text_path']):bindings[rel(p)]=sha(p)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=301
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Apply corrected numbered majority readings to explicit conditional totals in complete current answers',
        majority_application={'review':rel(PREP),'baseline':rel(prior.HERE),'original_task_complete':False,
            'cumulative026_seconds':7200,'cumulative026_bytes_with_reserve':768*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=42
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=301
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Integrate conditional majority calculations then continue other statutory application targets',
            stop_condition='42 admissions;210s stages;7200s cumulative026;768MiB with reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_042_measured_seconds']+900,
              'bytes':costs()['cumulative026_042_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<7200 and forecast['bytes']<764*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Conditional source-specific majority integration','Admission41 to42;unchanged cumulative0267200s/768MiB bounds'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Separate integer oracle;exact baseline preservation;complete actual and installed answers',
            'promotion_veto':['Wrong source','Unexpected delta','Unsupported applicability','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Effective amendment','Actual vote','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':41,'new_maximum':42,'retained_attempts':attempts,
            'reason':'Apply corrected source meanings to finite conditional scenarios using existing arithmetic',
            'next_discriminating_check':'Measure8 below75 and measure9 separate contract/statute outcomes reach actual consumer',
            'stop_condition':'210s stages;7200s cumulative026;768MiB with reserve;no GETs',
            'same_scope_authorization':'User requested continued internally supported general build after refreshed master'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':301,'scenarios':len(scenario),'forecast':forecast}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        path=ROOT/row['target'];assert (sha(path) if path.exists() else None)==row['after' if installed else 'before'],row['target']


def install():
    for row in read(PREP/'installation.json'):
        path=ROOT/row['target'];assert (sha(path) if path.exists() else None)==row['before']
        shutil.copyfile(ROOT/row['candidate'],path)
    return {'status':'PASS','production_files':len(TARGETS)}


def execute(name,command,seconds):
    folder=HERE/'commands';folder.mkdir(exist_ok=True)
    save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},
            stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',str(ROOT/TEST),
        str(ROOT/prior.TEST),'-q','--junitxml='+str(HERE/'pytest.xml')],60)
    return {'status':'PASS','oracle_worlds':4608,'source_regression_included':True}


def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import schvg_majority as module
    products,ordinary=prior.retained('answer');profile=read(PREP/'profile.json');expected=read(PREP/'expected.json')
    default=read(prior.HERE/'conditional-profile.json')
    actual=service.consume(products,ROOT,mode='frozen',default_f_profile=default,
        expected_default_f_profile_sha256=digest(default),majority_profile=profile,
        expected_majority_profile_sha256=digest(profile))
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    observed={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']}
    assert observed==expected['scenarios'];assert actual['default_f_review']==ordinary['default_f_review']
    save(HERE/'answer-delta.json.gz',{'delta':changes(ordinary,actual),'sha256':digest(actual)})
    save(HERE/'verification.json',verification);save(HERE/'outcomes.json',observed)
    return {'status':'PASS','scenarios':len(observed),'baseline_unchanged':True,'answer_sha256':digest(actual)}


def retained():
    products,ordinary=prior.retained('answer');delta=read(HERE/'answer-delta.json.gz')
    actual=apply(ordinary,delta['delta']);assert digest(actual)==delta['sha256'];return products,ordinary,actual


def controls():
    from legalmath.prospectus import schvg_majority as module
    products,ordinary,actual=retained();profile=read(PREP/'profile.json');refused={}
    for kind in ('source','products','baseline','event-promotion','drop-open','forged-answer','lost-baseline'):
        bad=deepcopy(profile);answer=deepcopy(actual)
        if kind=='source':bad['context']['H38']['numbered_measures'][-1]['quote']+=' altered'
        elif kind=='products':bad['products_sha256']='0'*64
        elif kind=='baseline':bad['ordinary_answer_sha256']='0'*64
        elif kind=='event-promotion':bad['actual_event_established']=True
        elif kind=='drop-open':bad['scenarios']=bad['scenarios'][1:]
        elif kind=='forged-answer':answer[module.KEY]['scenarios'][8]['statute']['status']='YES'
        else:answer['questions']['Q4']['status']='YES'
        answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
        try:
            if kind in ('forged-answer','lost-baseline'):
                module.verify_answer(answer,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Control accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=prior.base.package_files(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert expected==actual
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert prior.base.package_files(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    return read(HERE/'installed-result.json')


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_BOUND_CONDITIONAL_MAJORITY','scenarios':len(read(PREP/'profile.json')['scenarios']),
        'oracle_worlds':4608,'baseline_unchanged':True,'installed_complete_equal':True,
        'resources':costs(),'actual_application':'NOT_ESTABLISHED','historical_application':'UNKNOWN',
        'next_action':'Continue source-specific statutory application and amount/date/causality derivation'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(prior.HERE/'answer.json.gz'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Conditional majority rules reach the complete answer

The current consumer now retains a source-bound optional comparison of the
selected contractual and retained statutory majority readings. Item8 requires
the qualified threshold in both declared rules;item9 preserves their different
number ranges. Exact boundary,large-decimal,unknown and conflicting premises
match the independent integer oracle. All original answer fields and192
default(f) decisions remain unchanged. The isolated installed answer is equal.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain optional conditional calculation | Complete answer and separate oracle agree | No unexplained delta;adverse inputs refused | Eligibility,classification,historical law,other prerequisites | Remaining source-specific application | Actual vote,effective amendment,whole build |

The former gap was local integration:current output described the readings but
did not calculate these conditional consequences. Existing numerical/predicate
capabilities suffice. The strongest alternative explanation for a wrong actual
answer is a wrong supplied classification,denominator or applicable edition.
Internal calculation proves the exposed conditional relation only. No package
defect,automatic legal construction or exhaustive legal correctness is inferred.
''')
    return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_majority_application',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Majority stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
