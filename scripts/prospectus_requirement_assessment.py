"""Execute a reviewed original-requirements assessment under the prospectus authority."""
from copy import deepcopy
from datetime import datetime, timezone
import ast,json,os,shutil,signal,sys,time
import xml.etree.ElementTree as ET
from scripts import prospectus_cycle_disposition as prior
from scripts import prospectus_requirement_inventory as inventory
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest

ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/original-acceptance-338'
HERE=AUTH/'attempts/basf-references/attempt-077'
PLAN='docs/plans/prospectus-original-acceptance-2026-10-19.md'
METHOD='scripts/prospectus_requirement_assessment.py'
WORKER='scripts/prospectus_requirement_installed.py'
TEST='tests/prospectus_successor/test_reference_requirements.py'
FILES=(PLAN,METHOD,WORKER,TEST,'scripts/prospectus_requirement_inventory.py')
TARGETS=('src/legalmath/prospectus/reference_requirements.py',)
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel

def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior']
    seconds=base['combined_measured_seconds']+read(PREP/'inventory-freeze.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0338.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum((ROOT/n).stat().st_size for n in TARGETS if (ROOT/n).exists())
    charged=base['conservative_extra_seconds']
    assert seconds+charged<21600 and size<3196*1024**2,'Cumulative resource bound'
    return {'combined_measured_seconds':seconds,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':seconds+charged,'combined_bytes':size,'seconds_bound':21600,
        'bytes_bound_with_4MiB_reserve':3200*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==337
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==76 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v
    for n,v in read(prior.PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(prior.PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after']
    frozen=read(PREP/'inventory-freeze.json')
    assert frozen['candidate_absent'] and sha(PREP/'expected.json')==frozen['expected_sha256']
    assert sha(PREP/'evidence.json')==frozen['evidence_sha256']
    for n,v in read(PREP/'evidence.json')['bindings'].items():assert sha(ROOT/n)==v,n
    candidate=PREP/'candidate/reference_requirements.py';text=candidate.read_text()
    assert text.count('EVIDENCE_SHA256 = None')==1
    candidate.write_text(text.replace('EVIDENCE_SHA256 = None','EVIDENCE_SHA256 = '+repr(sha(PREP/'evidence.json'))))
    ast.parse(candidate.read_text());assert not (ROOT/TARGETS[0]).exists()
    save(PREP/'installation.json',[{'target':TARGETS[0],'before':None,'candidate':rel(candidate),'after':sha(candidate)}])
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.WORKER,'scripts/prospectus_residual_coverage.py')}
    bindings.update(read(PREP/'evidence.json')['bindings'])
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=338
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Reconcile original requirement identities against retained actual source-to-answer evidence and preserve incomplete acceptance',
        original_requirement_assessment={'review':rel(PREP),'original_task_complete':False,'accounted_seconds_bound':21600,
            'bytes_bound_with_4MiB_reserve':3200*1024**2,'next_action':'Repair the first concrete original-source discovery gap exposed by the assessor'})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=77
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=338
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify original49/47/14/60/612 identities and current evidence,then repair concrete reference or definition discovery gaps',
            stop_condition='77 cumulative admissions;360s/64MiBforecast;21600accounted seconds/3200MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+360,
        'bytes':snapshot['combined_bytes']+64*1024**2,'estimate_only':True}
    assert forecast['seconds']<21600 and forecast['bytes']<3196*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Add original-source evidence assessor without an automatic completion shortcut',
            'Refresh historical ledger statuses from actual current answer while preserving sealed evidence',
            'Retain all prior costs and76admissions;admit one bounded original-requirements package'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Exact original identities,source slices,complete reference projections,definition dependencies and explicit gaps',
            'promotion_veto':['Source or target lost','Definition association lost','Uncertainty erased','False completion','Wrong installed import'],
            'continuation_veto':['Frozen corruption','Method drift','Cumulative bound'],
            'explanatory_only':['Test totals','Counts','Runtime'],
            'not_concluded':['General discovery','Historical law','Actual events','New full-answer execution','Original task completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':76,'new_maximum':77,'retained_attempts':attempts,
            'reason':'Original acceptance requirements lack one exact current evidence reconciliation',
            'next_discriminating_check':'Missing original identities,target truncation and false completeness must be refused',
            'stop_condition':'360s/64MiBforecast;21600accounted seconds/3200MiB;no unchanged retry',
            'same_scope_authorization':'User requested internally supported general build and continuous execution'},
        'resource_accounting':{'retained_costs':snapshot,'seconds_bound':21600,'bytes_with_reserve':3200*1024**2,
            'limits_extended':False,'forecast_correction':'32MiB in initial plan was inadequate for retained package-source plus installed tree;64MiB replaces that estimate before execution'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':338,'candidate_evaluated':False,'forecast':forecast}

def install():
    row=read(PREP/'installation.json')[0];assert not (ROOT/row['target']).exists()
    shutil.copyfile(ROOT/row['candidate'],ROOT/row['target'])
    return {'status':'PASS','production_files':1}

def tests():
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',str(ROOT/TEST),'-q','--junitxml='+str(HERE/'pytest.xml')],120)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS',**counts}

def consume():
    command=[str(ROOT/'.venv/bin/python'),'-m','legalmath.prospectus.reference_requirements',
        '--repository',str(ROOT),'--evidence',str(PREP/'evidence.json'),'--output',str(HERE/'assessment.json')]
    engine.execute('assessment-cli',command,60)
    actual=read(HERE/'assessment.json');expected=read(PREP/'expected.json')
    assert all(actual[k]==v for k,v in expected.items())
    assert actual['task_ready'] is False and actual['whole_build_complete'] is False
    save(HERE/'verification.json',{'status':'PASS','exact_expected_inventory_equal':True,
        'actual_assessor_cli':True,'new_full_consumer_execution':False,'report_sha256':actual['report_sha256']})
    return read(HERE/'verification.json')

def controls():
    cases=list(ET.parse(HERE/'pytest.xml').getroot().iter('testcase'))
    names=[r.attrib['name'] for r in cases if 'refused' in r.attrib['name']]
    assert len(names)==20 and all(not list(r) or all(x.tag not in ('failure','error','skipped') for x in r) for r in cases)
    save(HERE/'controls.json',{'status':'PASS','refused_cases':names,'executed_in':'tests stage; no duplicate test run'})
    return {'status':'PASS','refused':len(names)}

def installed():
    engine.execute('installed-assessor',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),str(PREP)],60)
    return read(HERE/'installed-result.json')

def seal():
    report=read(HERE/'assessment.json')
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'ORIGINAL_REQUIREMENT_EVIDENCE_ASSESSMENT','resources':costs(),
        'report_sha256':report['report_sha256'],'task_ready':False,
        'next_action':'Trace original selected prose through current reference discovery; freeze exact unsupported forms and repair the first source-supported miss'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PREP/'evidence.json'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Original requirements now have a current evidence assessment

The actual assessor and isolated installed package agree on every original
identity:49 headings,47 reference lines,14 preserved numbering markers,60 reference
records and612 associations across62 definitions. Exact source slices,complete
P3 references and answer projections remain checked; the finite inventories do
not establish exhaustive discovery. Historical statutory and H43 statuses are
read from the current answer without rewriting the old ledger.

|Decision|Primary criterion|Veto status|Uncertainty|Next justified action|Not concluded|
|---|---|---|---|---|---|
|Retain conservative evidence assessor|Exact frozen requirement inventory and installed equality|Missing/changed evidence and false completeness refused|General discovery,historical law,scope and missing source facts|Trace selected prose through discovery and repair exact unsupported forms|Original task or whole-build completion|

Seven substantive requirements remain explicit in assessment.json. The strongest
alternative explanation is omitted linguistic content outside the finite
inventory. That possibility prevents acceptance and directs the next discovery
repair. No actual client holdings or external adviser is made a prerequisite.
This package runs a new assessor over a previously executed complete consumer
answer; it does not claim a new full consumer run.
''')
    return result

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':
        save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
            'program_bytes':(AUTH/'program.json').stat().st_size})
    else:
        for s in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/s/'result.json')['status']=='PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    engine.PREP,engine.HERE,engine.PLAN,engine.METHOD,engine.WORKER,engine.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
    engine.costs=costs
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_requirement_assessment',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':150})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Requirement assessment stage bound')));signal.alarm(150)
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
