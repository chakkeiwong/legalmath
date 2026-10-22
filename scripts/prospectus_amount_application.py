"""Admitted exact cross-default amount integration and complete delivery."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_statutory_test_scope as prior
from scripts import prospectus_bgb_timing as base
from scripts import prospectus_amount_oracle as oracle
from scripts.prospectus_typed_delta import changes,apply
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=base.AUTH;PREP=AUTH/'reviews/cross-default-amount-304';HERE=AUTH/'attempts/basf-references/attempt-045'
PLAN='docs/plans/prospectus-cross-default-amount-2026-10-19.md';METHOD='scripts/prospectus_amount_application.py'
WORKER='scripts/prospectus_amount_installed.py';ORACLE='scripts/prospectus_amount_oracle.py'
TEST='tests/prospectus_successor/test_cross_default_amount.py';FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/cross_default_amount.py','src/legalmath/prospectus/successor/service.py')
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=base.read,base.save,base.sha,base.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_044_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0304.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_044_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<8400 and size<892*1024**2,'Amount cumulative026 resource bound'
    return {'cumulative026_045_measured_seconds':seconds,'cumulative026_045_bytes':size,'prior_costs_reset':False,
        'seconds_bound':8400,'bytes_bound_with_4MiB_reserve':896*1024**2,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':'UNKNOWN;retained lineage never treats manual time as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==303
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==44 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for attempt in (prior.HERE,base.HERE):
        for n,v in read(attempt/'outputs.json').items():assert sha(attempt/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    text=(ROOT/TARGETS[1]).read_text();old='            majority_profile=None, expected_majority_profile_sha256=None):'
    new='            majority_profile=None, expected_majority_profile_sha256=None,\n            amount_profile=None, expected_amount_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,new)
    old='    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new='''    if amount_profile is not None:
        from ..cross_default_amount import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['cross_default_amount_review'] = evaluate(products, baseline, amount_profile, root,
            expected_profile_sha256=expected_amount_profile_sha256)
    elif expected_amount_profile_sha256 is not None:
        raise ValueError('Amount profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(old)==1;text=text.replace(old,new);(PREP/'candidate/service.py').write_text(text)
    (PREP/'baseline').mkdir(exist_ok=True);installation=[]
    for target in TARGETS:
        candidate=PREP/'candidate'/Path(target).name;ast.parse(candidate.read_text());exists=(ROOT/target).exists()
        if exists:shutil.copyfile(ROOT/target,PREP/'baseline'/Path(target).name)
        installation.append({'target':target,'before':sha(ROOT/target) if exists else None,
            'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    products,ordinary=base.retained('answer');node=next(n for n in products['P3']['payload']['clauses']['nodes'] if n['id']=='basf-default:c')
    assert 'mehr als EUR 200.000.000' in node['quote'];instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    rows=oracle.scenarios(instrument);profile={'version':'basf-cross-default-amount.v1','products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':node,'scenarios':rows,'actual_event_established':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{'scenarios':{r['id']:oracle.classify(r) for r in rows},'candidate_invoked':False})
    (PREP/'METHOD-REVIEW.md').write_text('''# Exact amount source application audit

PASS for the declared conditional adapter after reading complete selected
default(c),its source mappings,legal reading and composite overdue definition.
Threshold applies only to the payment alternative. Exact source formula remains
unchanged;amount arithmetic derives only its overdue premise. Explicit currency
direction,eligibility,time and one-obligation scope remain hypotheses. Existing
notice,dispute,cure,quorum,representative and other branches remain. Independent
integer oracle and expected scenarios precede candidate calls. Ordinary and
installed complete answers must retain all prior fields and decisions exactly.
No network,actual event,rate-date inference or historical-law promotion.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',base.METHOD,prior.METHOD,
        'scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',base.HERE/'outputs.json',base.HERE/'answer.json.gz',base.HERE/'default-profile.json',base.HERE/'majority-profile.json'):bindings[rel(p)]=sha(p)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=304
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Derive exact conditional EUR200m payment threshold without changing other default branches',
        cross_default_amount={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':8400,'cumulative026_bytes':896*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=45
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=304
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Integrate exact amount/FX hypotheses through complete default(c),then time/causality adapters',
            stop_condition='45 admissions;210s stages;8400s cumulative026;896MiB with reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_045_measured_seconds']+850,'bytes':costs()['cumulative026_045_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<8400 and forecast['bytes']<892*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Substantive amount/FX conditional adapter','Admission44 to45;7200 to8400s and768 to896MiB cumulative026;no reset'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent amount/full-formula oracle;baseline equality;actual and installed answer',
            'promotion_veto':['Wrong comparison','Branch leakage','Lost qualifier','Unexpected delta','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual default','Historical applicability','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':44,'new_maximum':45,'retained_attempts':attempts,
            'reason':'Existing composite Boolean lacks source-specific amount derivation',
            'next_discriminating_check':'Exact200m false,above true,other branches unaffected in complete consumer',
            'stop_condition':'210s stages;8400s cumulative026;896MiB with reserve;no GETs',
            'same_scope_authorization':'User requested continued internally supported complete build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review);return {'status':'PASS','revision':304,'scenarios':len(rows),'forecast':forecast}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['after' if installed else 'before'],row['target']


def install():
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['before'];shutil.copyfile(ROOT/row['candidate'],p)
    return {'status':'PASS','production_files':2}


def execute(name,command,seconds):
    folder=HERE/'commands';folder.mkdir(exist_ok=True);save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',str(ROOT/TEST),
        str(ROOT/base.prior.TEST),str(ROOT/base.TEST),str(ROOT/prior.TARGETS[0]),'-q','--junitxml='+str(HERE/'pytest.xml')],60)
    from legalmath.prospectus import cross_default_amount as module
    profile=read(PREP/'profile.json');instrument=profile['scenarios'][0]['payment']['instrument_id']
    for row in profile['scenarios']:assert oracle.projection(module.analyze(row,profile['context'],instrument))==oracle.classify(row)
    return {'status':'PASS','independent_formula_cases':1042,'actual_source_node_cases':len(profile['scenarios'])}


def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import cross_default_amount as module
    p,ordinary=base.retained('answer');profile=read(PREP/'profile.json');default=read(base.HERE/'default-profile.json');majority=read(base.HERE/'majority-profile.json')
    actual=service.consume(p,ROOT,mode='frozen',default_f_profile=default,expected_default_f_profile_sha256=digest(default),
        majority_profile=majority,expected_majority_profile_sha256=digest(majority),
        amount_profile=profile,expected_amount_profile_sha256=digest(profile))
    verification=module.verify_answer(actual,ordinary,profile,p,ROOT,expected_profile_sha256=digest(profile))
    outcomes={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']};assert outcomes==read(PREP/'expected.json')['scenarios']
    save(HERE/'answer-delta.json.gz',{'delta':changes(ordinary,actual),'sha256':digest(actual)})
    save(HERE/'outcomes.json',outcomes);save(HERE/'verification.json',verification)
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(outcomes),'answer_sha256':digest(actual)}


def retained():
    p,ordinary=base.retained('answer');delta=read(HERE/'answer-delta.json.gz');answer=apply(ordinary,delta['delta'])
    assert digest(answer)==delta['sha256'];return p,ordinary,answer


def controls():
    from legalmath.prospectus import cross_default_amount as module
    p,ordinary,actual=retained();profile=read(PREP/'profile.json');refused={}
    for kind in ('source','products','baseline','promotion','computed-override','forged-answer','lost-baseline'):
        bad=deepcopy(profile);answer=deepcopy(actual)
        if kind=='source':bad['context']['quote']+=' changed'
        elif kind=='products':bad['products_sha256']='0'*64
        elif kind=='baseline':bad['ordinary_answer_sha256']='0'*64
        elif kind=='promotion':bad['actual_event_established']=True
        elif kind=='computed-override':bad['scenarios'][1]['other_facts']['default.c.overdue']=True
        elif kind=='forged-answer':answer[module.KEY]['scenarios'][2]['amount_above_threshold']=True
        else:answer['questions']['Q1']['status']='YES'
        answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
        try:
            if kind in ('forged-answer','lost-baseline'):module.verify_answer(answer,ordinary,bad,p,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(p,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=base.prior.prior.base.package_files(ROOT/'src/legalmath');python=read(base.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert base.prior.prior.base.package_files(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])});return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    return read(HERE/'installed-result.json')


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'EXACT_CONDITIONAL_DEFAULT_AMOUNT',
        'scenarios':len(read(PREP/'profile.json')['scenarios']),'formula_cases':1042,'baseline_unchanged':True,'installed_complete_equal':True,
        'resources':costs(),'actual_default':'NOT_ESTABLISHED','rate_date':'NOT_ESTABLISHED','next_action':'Source-specific30-day,45-day cutoff and causal-rating adapters'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(base.HERE/'answer.json.gz'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Exact conditional payment amounts reach the full default(c) answer

The optional amount adapter distinguishes below,exactly and aboveEUR200m and
uses explicit EUR-per-source-unit FX hypotheses. It derives the composite
overdue-payment premise while preserving accelerated-debt/security alternatives,
notice,dispute,cure,quorum and representative restrictions. Independent integer
and source-formula checks match. All previous answer fields and conditional
decisions remain unchanged;the complete installed answer is identical.

| Decision | Criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain conditional amount adapter | Exact independent arithmetic and actual/installed answer | Malformed and forged controls refused | Debt scope,time,FX choice,actual events | Time/cutoff/causal adapters | Actual default,automatic classification,whole build |

This was a local source-specific derivation gap. No external package defect
was established. The strongest alternative explanation for a wrong actual
conclusion is an incorrect supplied debt/FX/event premise. The adapter exposes
those hypotheses and never authenticates them or infers aggregation.
''');return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES;folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_amount_application',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Amount stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
