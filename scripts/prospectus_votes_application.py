"""Reviewed voting-threshold integration through complete source-bound answers."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_rating_application as prior
from scripts import prospectus_votes_oracle as oracle
from scripts.prospectus_typed_delta import changes,apply
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/control-votes-309';HERE=AUTH/'attempts/basf-references/attempt-050'
PLAN='docs/plans/prospectus-control-votes-2026-10-19.md';METHOD='scripts/prospectus_votes_application.py'
WORKER='scripts/prospectus_votes_installed.py';ORACLE='scripts/prospectus_votes_oracle.py'
TEST='tests/prospectus_successor/test_control_votes.py';FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/control_votes.py',
         'src/legalmath/prospectus/successor/service.py')
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_049_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0309.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_049_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<9600 and size<1148*1024**2,'Rating cumulative026 resource bound'
    return {'cumulative026_050_measured_seconds':seconds,'cumulative026_050_bytes':size,
        'prior_costs_reset':False,'seconds_bound':9600,'bytes_bound_with_4MiB_reserve':1152*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==308
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==49 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    text=(ROOT/TARGETS[1]).read_text()
    old='            rating_profile=None, expected_rating_profile_sha256=None):'
    new='            rating_profile=None, expected_rating_profile_sha256=None,\n            votes_profile=None, expected_votes_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,new)
    old='    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new="""    if votes_profile is not None:
        from ..control_votes import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['control_votes_review'] = evaluate(products, baseline, votes_profile, root,
            expected_profile_sha256=expected_votes_profile_sha256)
    elif expected_votes_profile_sha256 is not None:
        raise ValueError('Voting profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;text=text.replace(old,new);(PREP/'candidate/service.py').write_text(text)
    (PREP/'baseline').mkdir(exist_ok=True);installation=[]
    for target in TARGETS:
        candidate=PREP/'candidate'/Path(target).name;ast.parse(candidate.read_text())
        exists=(ROOT/target).exists()
        if exists:shutil.copyfile(ROOT/target,PREP/'baseline'/Path(target).name)
        installation.append({'target':target,'before':sha(ROOT/target) if exists else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    p,_,ordinary=prior.retained();node=next(n for n in p['P3']['payload']['clauses']['nodes'] if n['id']=='basf-redemption:control_put')
    assert all(s in node['quote'] for s in ('mehr als 50% der Stimmrechte','§ 30 Absatz 2','mittelbar oder unmittelbar','Aktien der BASF'))
    assert node['exceptions']=='control_put.earlier_tax_notice'
    instrument=p['P1']['payload']['request']['bundle']['instrument_id'];rows=oracle.scenarios(instrument)
    profile={'version':'basf-control-votes.v1','products_sha256':digest(p),'ordinary_answer_sha256':digest(ordinary),
        'context':node,'scenarios':rows,'actual_event_established':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{'scenarios':{r['id']:oracle.classify(r) for r in rows},'candidate_invoked':False})
    evidence=[]
    for n,capability in ((41,'Numbered SchVG1-8 source repair'),(42,'Conditional qualified/simple majority'),
        (43,'BGB presentation/limitation source relations'),(45,'Exact EUR200m overdue amount'),
        (46,'Strict default(b) duration'),(47,'Frankfurt exercise cutoff'),(48,'Default(a)/(c) payment timing'),
        (49,'Rating alternatives,120days,causal premise and cutoff composition')):
        folder=AUTH/'attempts/basf-references'/('attempt-%03d'%n)
        result=read(folder/'result.json');assert result['status']=='PASS' and result['original_task_complete'] is False
        evidence.append({'attempt':rel(folder),'capability':capability,'result_sha256':sha(folder/'result.json'),
            'outputs_sha256':sha(folder/'outputs.json'),'classification':'VERIFIED_PARTIAL_CONDITIONAL_WORK'})
    old=read(AUTH/'attempts/basf-references/attempt-025/original-ledger-reconciliation.json.gz')
    definitions=read(AUTH/'attempts/basf-references/attempt-030/reconciliation.json.gz')
    spec=read(ROOT/'src/legalmath/prospectus/successor/statutory_references_spec.json')
    reconciliation={'version':'remaining-reference-reconciliation.v1','baseline':rel(prior.HERE),
        'completed_partial_capabilities':evidence,'original_reference_records':len(old['records']),
        'original_definition_records':definitions['original_records'],
        'original_use_associations':definitions['original_use_associations'],'denominator_replaced':False,
        'current_numeric_gap':'control_put.control is still a supplied Boolean before this candidate',
        'statutory_records':[{'id':r['id'],'historical_validity':r['historical_validity'],'onward_scope':r['onward_scope']} for r in spec['records']],
        'remaining':[{'scope':'Reference and definition completeness','action':'Occurrence-level reconciliation of implicit uses and priority/self-scope;finite inventory is not recall'},
            {'scope':'H16 control eligibility','action':'Derive contract ratio now;coordinated-person qualification,indirect ownership and nonoverlapping attribution remain separate conditional applications'},
            {'scope':'H28 timing','action':'Source relations repaired;actual calendar application and suspension/onward conditions remain'},
            {'scope':'H35 affiliate categories','action':'Preserve distinct statutory alternatives and substitution prerequisites'},
            {'scope':'H39 H40 A7 A8 governance','action':'Preserve open statutory scope,ballot/meeting alternatives,notice override,mandate and proceedings'},
            {'scope':'A2 A3 A12 taxation','action':'Purpose-specific and event-date-specific conditional applications;historical chain and executed IGA remain unresolved'},
            {'scope':'A11 priorities','action':'Conditional examples cannot exhaust unspecified mandatory law'},
            {'scope':'Historical source editions','action':'No repeated GETs on exhausted SchVG route;missing editions remain visible'},
            {'scope':'Original wider source tasks','action':'Margins,office,incorporation,meaning and remaining BASF/BES tasks retain their original acceptance'}],
        'real_client_facts':'AFTER_BUILD','external_adviser_required':False,'cdm_receiver':'DEFERRED',
        'portability':'DEFERRED','actus_missing_source':'BLOCKS_ACTUS_TRIAL_ONLY',
        'complete_reference_graph':False,'original_task_complete':False,'counts_are_not_recall':True}
    save(PREP/'reconciliation.json',reconciliation)
    (PREP/'METHOD-REVIEW.md').write_text("""# Voting threshold skeptical audit

PASS for conditional calculation on explicitly qualified totals.049 is the full
baseline. Contract threshold is >50%,not statutory>=30%,not>=50%. Voting rights
are not shares,note principal or meeting participation. Exact quantities have
subject,event,unit and basis bindings;unknown/zero totals stay unknown. Ownership,
concert,nonoverlap and common snapshot are explicit hypothetical qualifications.
Composition shares the same control event and preserves rating,causation,cutoff,
tax,notice,delivery,payment and representative conditions. Independent integer
oracle expectations precede candidate;complete baseline/installed equality and
adverse controls remain mandatory. No actual eligibility or historical validity.
Coverage reconciliation preserves originals and separates verified finite work
from historical-source,statutory-application and wider completeness gaps.
""")
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.WORKER,prior.ORACLE,
        'scripts/prospectus_calendar_oracle.py','scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'answer-delta.json.gz',prior.PREP/'profile.json'):
        bindings[rel(p)]=sha(p)
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=309
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Derive strict control voting ratio and same-event rating/cutoff composition;retain eligibility and source gaps',
        control_votes={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':9600,'cumulative026_bytes':1152*1024**2},
        remaining_coverage_reconciliation=rel(PREP/'reconciliation.json'))
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=50
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=309
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Integrate exact control voting ratio;continue retained statutory eligibility and wider source applications',
            stop_condition='50 admissions;210s stages;9600s cumulative026;1152MiB with reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_050_measured_seconds']+750,'bytes':costs()['cumulative026_050_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<9600 and forecast['bytes']<1148*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Substantive conditional control threshold and composition','Reconcile delivered capabilities against original scope','Admission49 to50;retain cumulative time/storage and all prior costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent exact threshold/full-formula oracle,baseline equality,ordinary and installed answer',
            'promotion_veto':['Wrong denominator or threshold','Eligibility inferred','Event mismatch','Lost qualifier','Unexpected delta','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual control','Concert eligibility','Historical applicability','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':49,'new_maximum':50,'retained_attempts':attempts,
            'reason':'Current control premise has no source-specific exact voting threshold derivation',
            'next_discriminating_check':'Exact50% false;positive ratio with unknown scope unknown;composed rating/cutoff preserved',
            'stop_condition':'210s stages;9600s cumulative026;1152MiB with reserve;no GETs',
            'same_scope_authorization':'User requested continued internally supported complete build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':309,'scenarios':len(rows),'forecast':forecast,'original_reference_records':len(old['records'])}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['after' if installed else 'before'],row['target']


def install():
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['before'];shutil.copyfile(ROOT/row['candidate'],p)
    return {'status':'PASS','production_files':len(TARGETS)}


def execute(name,command,seconds):
    folder=HERE/'commands';folder.mkdir(exist_ok=True);save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def testfiles():
    return [TEST,*prior.testfiles()]


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],90)
    from legalmath.prospectus import control_votes as module
    profile=read(PREP/'profile.json');instrument=profile['scenarios'][0]['events']['instrument_id']
    for row in profile['scenarios']:assert oracle.projection(module.analyze(row,profile['context'],instrument))==oracle.classify(row)
    return {'status':'PASS','independent_formula_cases':560,'actual_source_node_cases':len(profile['scenarios'])}


def profiles():
    options=prior.profiles();profile=read(PREP/'profile.json')
    return {**options,'votes_profile':profile,'expected_votes_profile_sha256':digest(profile)}


def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import control_votes as module
    p,_,ordinary=prior.retained();profile=read(PREP/'profile.json')
    actual=service.consume(p,ROOT,mode='frozen',**profiles())
    verification=module.verify_answer(actual,ordinary,profile,p,ROOT,expected_profile_sha256=digest(profile))
    outcomes={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']}
    assert outcomes==read(PREP/'expected.json')['scenarios']
    save(HERE/'answer-delta.json.gz',{'delta':changes(ordinary,actual),'sha256':digest(actual)})
    save(HERE/'outcomes.json',outcomes);save(HERE/'verification.json',verification)
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(outcomes),'answer_sha256':digest(actual)}


def retained():
    p,_,ordinary=prior.retained();delta=read(HERE/'answer-delta.json.gz');answer=apply(ordinary,delta['delta'])
    assert digest(answer)==delta['sha256'];return p,ordinary,answer


def controls():
    from legalmath.prospectus import control_votes as module
    p,ordinary,actual=retained();profile=read(PREP/'profile.json');refused={}
    for kind in ('source','products','baseline','promotion','computed-override','denominator','operand-event','composition-event','forged-answer','lost-baseline'):
        bad=deepcopy(profile);answer=deepcopy(actual)
        if kind=='source':bad['context']['quote']+=' changed'
        elif kind=='products':bad['products_sha256']='0'*64
        elif kind=='baseline':bad['ordinary_answer_sha256']='0'*64
        elif kind=='promotion':bad['actual_event_established']=True
        elif kind=='computed-override':bad['scenarios'][1]['other_facts']['control_put.control']=True
        elif kind=='denominator':bad['scenarios'][1]['votes']['total']['basis']='PARTICIPATING_VOTING_RIGHTS'
        elif kind=='operand-event':bad['scenarios'][1]['votes']['eligible']['control_event_id']='other'
        elif kind=='composition-event':next(r for r in bad['scenarios'] if r['id']=='composed-timely')['rating_scenario']['events']['control_event_id']='other'
        elif kind=='forged-answer':answer[module.KEY]['scenarios'][1]['voting_rights_above_half']=True
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
    filemap=prior.prior.prior.prior.prior.base.prior.prior.base.package_files;expected=filemap(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert filemap(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])});return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    return read(HERE/'installed-result.json')


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'CONDITIONAL_CONTROL_VOTING_RIGHTS',
        'scenarios':len(read(PREP/'profile.json')['scenarios']),'formula_cases':560,'baseline_unchanged':True,'installed_complete_equal':True,
        'resources':costs(),'actual_control':'NOT_ESTABLISHED','eligible_ownership_and_concert':'NOT_DERIVED',
        'next_action':'Continue retained statutory eligibility and source-specific applications;preserve wider original coverage'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(prior.HERE/'answer-delta.json.gz'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    shutil.copyfile(PREP/'reconciliation.json',HERE/'reconciliation.json')
    (HERE/'RESULT.md').write_text("""# Strict contract voting threshold reaches the full answer

The adapter derives >50% from exact eligible/all voting rights and composes the
same control event with rating and Frankfurt exercise conditions. Exactly50%
and statutory30% do not trigger this contract threshold. Numeric majority does
not establish eligible ownership,coordinated persons,nonoverlap or snapshot truth.
Unknown qualifications stay visible. All prior complete-answer fields and the
isolated installed answer are preserved.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain conditional ratio and composition|Integer oracle,complete formula,ordinary/installed equality|Wrong basis,event,override,source and forged controls refused|Eligible ownership,concert,historical application|Source-specific statutory applications|Actual control or whole build|

This was a local missing source-specific derivation,not evidence of a package
defect. The strongest alternative explanation for an actual positive result is
an incorrect supplied eligible total; explicit qualification premises expose
that dependence. Independent ownership attribution remains unevaluated. The
coverage reconciliation retains original denominators and each historical or
broader source gap; finite test counts do not establish complete reference recall.
""");return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES;folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_votes_application',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Rating stage bound')));signal.alarm(210)
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
