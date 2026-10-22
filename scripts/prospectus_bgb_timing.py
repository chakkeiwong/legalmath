"""Exact BGB timing-source repair under the single prospectus authority."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_majority_application as prior
from scripts import prospectus_bgb_timing_rules as rules
from scripts.prospectus_typed_delta import changes,apply,equal
from scripts.prospectus_structural_oracle import seal as predict_seal
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/bgb-timing-302';HERE=AUTH/'attempts/basf-references/attempt-043'
PLAN='docs/plans/prospectus-bgb-presentation-timing-2026-10-19.md'
METHOD='scripts/prospectus_bgb_timing.py';WORKER='scripts/prospectus_bgb_timing_installed.py'
RULES='scripts/prospectus_bgb_timing_rules.py';TEST='tests/prospectus_successor/test_bgb_timing_rules.py'
FILES=(PLAN,METHOD,WORKER,RULES,TEST)
TARGETS=('src/legalmath/prospectus/successor/statutory_references.py','src/legalmath/prospectus/successor/statutory_references_spec.json')
STAGES=('install','tests','interpretation','downstream','ordinary','default','majority','control-stale','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_042_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0302.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_042_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items())
    assert seconds<7200 and size<764*1024**2,'BGB cumulative026 resource bound'
    return {'cumulative026_043_measured_seconds':seconds,'cumulative026_043_bytes':size,
            'prior_costs_reset':False,'seconds_bound':7200,'bytes_bound_with_4MiB_reserve':768*1024**2,
            'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation']}


def baseline():
    return prior.prior.expected()


def candidate():
    spec=read(ROOT/TARGETS[1]);old_hash=digest(spec);record=next(r for r in spec['records'] if r['id']=='H28')
    rows=[]
    for rule in rules.RULES:
        source=record['legal_sources'][rule['source_index']];text=(ROOT/source['text_path']).read_text()
        assert sha(ROOT/source['text_path'])==source['text_sha256'];assert text.count(rule['quote'])==1
        start=text.index(rule['quote']);rows.append({'id':rule['id'],'source_path':source['text_path'],
            'source_sha256':source['text_sha256'],'start':start,'end':start+len(rule['quote']),
            'quote':rule['quote'],'meaning':rule['meaning']})
    record['reviewed_reading']=rules.READING;record['unresolved_application']=rules.READING
    record['timing_rules']=rows;spec['profile']='basf-statutory-reviewed-2026-10-19.v3'
    save(PREP/'candidate/statutory_references_spec.json',spec)
    code=(ROOT/TARGETS[0]).read_text();assert old_hash in code;code=code.replace(old_hash,digest(spec))
    validator='''
TIMING_RULES = RULES_LITERAL

def validate_timing_rules(spec):
    record = next(r for r in spec['records'] if r['id'] == 'H28')
    rows = record.get('timing_rules')
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or [r.get('id') for r in rows] != [r['id'] for r in TIMING_RULES]):
        raise ValueError('H28 complete ordered timing rules required')
    for row, rule in zip(rows, TIMING_RULES):
        source = record['legal_sources'][rule['source_index']]
        matches = [e for e in source['excerpts'] if rule['quote'] in e['quote']]
        if len(matches) != 1 or matches[0]['quote'].count(rule['quote']) != 1:
            raise ValueError('H28 exact timing source missing or ambiguous')
        start = matches[0]['start'] + matches[0]['quote'].index(rule['quote'])
        expected = {'id': rule['id'], 'source_path': source['text_path'],
            'source_sha256': source['text_sha256'], 'start': start,
            'end': start + len(rule['quote']), 'quote': rule['quote'], 'meaning': rule['meaning']}
        if row != expected:
            raise ValueError('H28 timing meaning or exact source changed')
    return rows

'''.replace('RULES_LITERAL',repr(rules.RULES))
    assert code.count('\ndef specification():')==1;code=code.replace('\ndef specification():',validator+'\ndef specification():')
    code=code.replace('    validate_numbered_measures(value)\n','    validate_numbered_measures(value)\n    validate_timing_rules(value)\n',1)
    ast.parse(code);(PREP/'candidate/statutory_references.py').write_text(code)
    (PREP/'baseline').mkdir(exist_ok=True);installation=[]
    for target in TARGETS:
        name=Path(target).name;shutil.copyfile(ROOT/target,PREP/'baseline'/name)
        installation.append({'target':target,'before':sha(ROOT/target),'candidate':rel(PREP/'candidate'/name),'after':sha(PREP/'candidate'/name)})
    save(PREP/'installation.json',installation);return spec


def prediction(spec):
    old,old_answer=baseline();p=deepcopy(old);answer=deepcopy(old_answer)
    semantic=p['P3']['payload'];report=semantic['statutory_references'];old_record=next(r for r in report['records'] if r['id']=='H28')
    new_record=deepcopy(old_record);source=next(r for r in spec['records'] if r['id']=='H28')
    for key in ('reviewed_reading','unresolved_application','timing_rules'):new_record[key]=deepcopy(source[key])
    new_report=deepcopy(report);new_report.update(profile=spec['profile'],profile_sha256=digest(spec))
    new_report['records']=[new_record if r['id']=='H28' else r for r in new_report['records']]
    packet=semantic['interpretation_input']['statutory_references'];new_packet={**deepcopy(packet),'profile':spec['profile'],'records':deepcopy(spec['records'])}
    def replace(value):
        if isinstance(value,dict):
            if value==report:return deepcopy(new_report)
            if value==packet:return deepcopy(new_packet)
            out={k:replace(v) for k,v in value.items()}
            if isinstance(out.get('id'),str) and out['id'].startswith('statutory-reference:'):
                out['profile_sha256']=digest(spec)
                if out['id']=='statutory-reference:H28':out['record_sha256']=digest(new_record)
            return out
        if isinstance(value,list):return [replace(v) for v in value]
        return value
    p=replace(p);answer=replace(answer);bundle=p['P1']['payload']['request']['bundle']
    for key,parents in [('P3',('P1','P2')),('P4',('P1','P3')),('P5',('P2','P3'))]:
        p[key]=predict_seal(key,bundle,{k:p[k]['sha256'] for k in parents},p[key]['payload'])
    answer['consumed_products']={k:v['sha256'] for k,v in p.items()}
    answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
    equal(answer['questions'],old_answer['questions'],'Unexpected question delta')
    save(PREP/'expected.json.gz',{'products_delta':changes(old,p),'answer_delta':changes(old_answer,answer),
        'products_sha256':digest(p),'answer_sha256':digest(answer)})
    return {'candidate_invoked':False,'questions_unchanged':True,'products_sha256':digest(p),'answer_sha256':digest(answer)}


def expected():
    p,a=baseline();v=read(PREP/'expected.json.gz');p=apply(p,v['products_delta']);a=apply(a,v['answer_delta'])
    assert digest(p)==v['products_sha256'] and digest(a)==v['answer_sha256'];return p,a


def retain(label,p,a=None):
    old,ordinary=baseline();value={'products_delta':changes(old,p),'products_sha256':digest(p)}
    if a is not None:value.update(answer_delta=changes(ordinary,a),answer_sha256=digest(a))
    save(HERE/(label+'.json.gz'),value)


def retained(label):
    p,a=baseline();value=read(HERE/(label+'.json.gz'));p=apply(p,value['products_delta'])
    assert digest(p)==value['products_sha256']
    if 'answer_delta' in value:a=apply(a,value['answer_delta']);assert digest(a)==value['answer_sha256']
    return p,a


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==301
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==42 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'production_bytes':{n:(ROOT/n).stat().st_size for n in TARGETS}})
    spec=candidate();predicted=prediction(spec);save(PREP/'prediction.json',predicted)
    (PREP/'METHOD-REVIEW.md').write_text('''# Presentation/limitation correction audit

PASS for exact source correction under the plan.801(1) uses end of presentation
period as the two-year origin,not actual presentation date.802 expressly names
both clocks. Six source-bound relations retain full exception/onward wording.
The independent complete-output prediction precedes candidate execution.
Baseline ordinary041 equals pre-majority042 ordinary;both existing supplements
are rebound and their full decisions preserved. No date expiry or historical
application is inferred. Reuse packaging machinery with current frozen targets;
explicit timing tests plus existing numbering/majority tests guard interaction.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.ORACLE,
        'scripts/prospectus_h38_repair.py','scripts/prospectus_structural_oracle.py','scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'answer-delta.json.gz',prior.PREP/'profile.json',
        prior.prior.HERE/'answer.json.gz',prior.prior.HERE/'conditional-profile.json'):bindings[rel(p)]=sha(p)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=302;task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair H28 limitation origin and suspension coverage before date application',
        bgb_timing={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':7200,'cumulative026_bytes':768*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=43
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=302
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Correct presentation/limitation origins and preserve both conditional supplements,then remaining applications',
            stop_condition='43 admissions;210s stages;7200s cumulative026;768MiB including reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_043_measured_seconds']+950,'bytes':costs()['cumulative026_043_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<7200 and forecast['bytes']<764*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Exact H28 source timing correction','Admission42 to43;unchanged7200s/768MiB cumulative026'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Exact source relations;full predicted answer;both supplements unchanged;installed equality',
            'promotion_veto':['Wrong origin','Lost suspension','Unexpected delta','Conditional drift','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual limitation','Historical applicability','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':42,'new_maximum':43,'retained_attempts':attempts,
            'reason':'Concrete source ambiguity must be repaired before date calculation','next_discriminating_check':'Correct801 origin and802 both-clock relation reach full answer',
            'stop_condition':'210s stages;7200s cumulative026;768MiB including reserve;no GETs',
            'same_scope_authorization':'User requested internally supported complete build and continued root-cause repair'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review);return {'status':'PASS','revision':302,'prediction':predicted,'forecast':forecast}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after' if installed else 'before'],row['target']


def install():
    for row in read(PREP/'installation.json'):
        assert sha(ROOT/row['target'])==row['before'];shutil.copyfile(ROOT/row['candidate'],ROOT/row['target'])
    return {'status':'PASS','production_files':2}


def execute(name,command,seconds):
    folder=HERE/'commands';folder.mkdir(exist_ok=True);save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',str(ROOT/TEST),str(ROOT/prior.TEST),'-q','--junitxml='+str(HERE/'pytest.xml')],60)
    from legalmath.prospectus.successor import statutory_references as module
    assert len(module.validate_numbered_measures(module.specification()))==8
    return {'status':'PASS','timing_source_rules':6,'H38_numbering_preserved':True}


def interpretation():
    from legalmath.prospectus.successor import service
    p,_=baseline();want,_=expected();p['P3']=service.interpretation_product(p['P1'],p['P2'],want['P3']['payload']['interpretation_input'])
    equal(p['P3'],want['P3'],'Unexpected actual P3 delta');retain('interpretation',p);return {'status':'PASS','complete_P3_equal':True}


def downstream():
    from legalmath.prospectus.successor import service
    p,_=retained('interpretation');want,_=expected();law,finance=p['P4']['payload'],p['P5']['payload']
    p['P4']=service.law_product(p['P1'],p['P3'],law['cases'],law['law_input'])
    p['P5']=service.financial_product(p['P1'],p['P2'],p['P3'],finance['cases'],finance['scenario_input'])
    equal(p,want,'Unexpected complete products delta');retain('products',p);return {'status':'PASS','complete_products_equal':True}


def ordinary():
    from legalmath.prospectus.successor import service
    p,_=retained('products');_,want=expected();answer=service.consume(p,ROOT,mode='frozen')
    equal(answer,want,'Unexpected full ordinary delta');retain('ordinary',p,answer);return {'status':'PASS','full_ordinary_equal':True}


def default():
    from legalmath.prospectus import basf_default_f_current as module
    p,ordinary=retained('ordinary');profile=read(prior.prior.HERE/'conditional-profile.json')
    profile.update(products_sha256=digest(p),ordinary_answer_sha256=digest(ordinary));save(HERE/'default-profile.json',profile)
    body={k:v for k,v in ordinary.items() if k!='report_sha256'}
    body.update(module.evaluate(p,ordinary,profile,ROOT,expected_profile_sha256=digest(profile)))
    answer={**body,'report_sha256':digest(body)};verification=module.verify_answer(answer,ordinary,profile,expected_profile_sha256=digest(profile))
    _,old=prior.prior.retained('answer');equal(answer['default_f_review']['scenarios'],old['default_f_review']['scenarios'],'Default decisions changed')
    assert verification['checked_answers']==192;retain('default',p,answer);return {'status':'PASS','conditional_decisions_equal':192}


def majority():
    from legalmath.prospectus import schvg_majority as module
    p,ordinary=retained('default');profile=read(prior.PREP/'profile.json')
    profile.update(products_sha256=digest(p),ordinary_answer_sha256=digest(ordinary),context=module.context(p,ordinary));save(HERE/'majority-profile.json',profile)
    body={k:v for k,v in ordinary.items() if k!='report_sha256'}
    body[module.KEY]=module.evaluate(p,ordinary,profile,ROOT,expected_profile_sha256=digest(profile));answer={**body,'report_sha256':digest(body)}
    module.verify_answer(answer,ordinary,profile,p,ROOT,expected_profile_sha256=digest(profile))
    old=prior.retained()[2];equal(answer[module.KEY]['scenarios'],old[module.KEY]['scenarios'],'Majority scenarios changed')
    retain('answer',p,answer);return {'status':'PASS','majority_scenarios_equal':28,'answer_sha256':digest(answer)}


def control_stale():
    from legalmath.prospectus.successor import service
    p,_=baseline()
    try:service.consume(p,ROOT,mode='frozen')
    except ValueError as error:
        assert str(error)=='Statutory reference requires the exact registered source reading and edition'
        save(HERE/'stale-profile-control.json',{'status':'PASS','reason':str(error)});return {'status':'PASS','stale_profile_refused':True}
    raise AssertionError('Obsolete profile accepted')


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=prior.prior.base.package_files(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert prior.prior.base.package_files(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])});return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    return read(HERE/'installed-result.json')


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'EXACT_BGB_PRESENTATION_TIMING_REPAIR',
        'source_relations':6,'full_predicted_products_and_ordinary':True,'default_decisions_equal':192,'majority_scenarios_equal':28,
        'installed_complete_equal':True,'resources':costs(),'historical_application':'UNKNOWN','actual_expiry':'NOT_COMPUTED',
        'next_action':'Review remaining source-specific applications and completeness without inventing historical or actual facts'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(prior.HERE/'answer-delta.json.gz'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# The presentation and limitation clocks remain distinct

H28 now states the two-year origin as the end of the presentation period and
retains judicial assertion,coupon-year-end timing,deed variation,and802
suspension of both clocks. Six exact source relations reach independently
predicted products and ordinary answers. Default(f)192 decisions and all28
majority scenarios stay identical. Complete installed consumption is equal.

| Decision | Criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain source correction | Exact source timing and full delivery | Adverse timing edits and stale profile refused | Historical text,claim type,actual events,counting law | Remaining source applications | Actual expiry,effective defence,whole build |

The ambiguity was our local reading,not a package limitation. The strongest
alternative source of an erroneous real conclusion is a wrong applicable
edition,claim classification or event history. No actual expiry is computed.
''');return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES;folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_bgb_timing',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('BGB stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage.replace('-','_')]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
