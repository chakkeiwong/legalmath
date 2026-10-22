"""Bounded test-only correction after sealed source timing integration."""
from copy import deepcopy
from pathlib import Path
import ast,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_bgb_timing as prior
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
AUTH=prior.AUTH;PREP=AUTH/'reviews/statutory-test-scope-303';HERE=AUTH/'attempts/basf-references/attempt-044'
PLAN='docs/plans/prospectus-statutory-regression-scope-2026-10-19.md';METHOD='scripts/prospectus_statutory_test_scope.py'
TARGETS=('tests/prospectus_successor/test_statutory_numbered_measures.py','tests/prospectus_successor/test_bgb_timing_rules.py')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_043_measured_seconds']+extra
    seconds+=sum(read(p)['wall_seconds'] for folder in (PREP,HERE) for p in folder.glob('stages/*/result.json'))
    seconds+=sum(read(p)['wall_seconds'] for folder in (PREP,HERE) for p in folder.glob('stages/*/failure.json'))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,METHOD));paths.add(AUTH/'revisions/0303.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_043_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['target_bytes'].items())
    assert seconds<7200 and size<764*1024**2,'Cumulative026 test repair bounds'
    return {'cumulative026_044_measured_seconds':seconds,'cumulative026_044_bytes':size,
            'prior_costs_reset':False,'seconds_bound':7200,'bytes_bound_with_4MiB_reserve':768*1024**2}


def pytest(label,files,expected):
    folder=(PREP if label=='reproduce' else HERE)/'commands';folder.mkdir(parents=True,exist_ok=True)
    command=[str(ROOT/'.venv/bin/python'),'-m','pytest',*files,'-q','--junitxml='+str(folder/(label+'.xml'))]
    save(folder/(label+'.json'),{'command':command,'timeout_seconds':60})
    with (folder/(label+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=60)
    assert result.returncode==expected,'Unexpected diagnostic exit;inspect '+label+'.log'


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==302
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==43 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'target_bytes':{n:(ROOT/n).stat().st_size for n in TARGETS}})
    pytest('reproduce',[str(ROOT/TARGETS[0])+'::test_repair_preserves_every_other_statutory_field'],1)
    import xml.etree.ElementTree as ET
    suite=ET.parse(PREP/'commands/reproduce.xml').getroot().find('testsuite')
    assert suite is not None and suite.attrib['failures']=='1' and suite.attrib['errors']=='0'
    (PREP/'candidate').mkdir(exist_ok=True);(PREP/'baseline').mkdir(exist_ok=True)
    text=(ROOT/TARGETS[0]).read_text();text=text.replace('def test_repair_preserves_every_other_statutory_field():','def test_repair_preserves_every_other_h38_field():')
    old="    current['profile'] = baseline['profile']\n    assert current == baseline"
    new="    # Other records have independent reviewed migrations and regressions.\n    assert modified == old"
    assert old in text;text=text.replace(old,new);(PREP/'candidate'/Path(TARGETS[0]).name).write_text(text)
    text=(ROOT/TARGETS[1]).read_text()+'''

def test_timing_repair_preserves_every_other_h28_field():
    import json
    path=ROOT/'docs/implementation/prospectus-execution-authority/reviews/bgb-timing-302/baseline/statutory_references_spec.json'
    old=next(r for r in json.loads(path.read_text())['records'] if r['id']=='H28')
    current=next(r for r in module.specification()['records'] if r['id']=='H28')
    del current['timing_rules']
    for key in ('reviewed_reading','unresolved_application'):
        current[key]=old[key]
    assert current==old
'''
    (PREP/'candidate'/Path(TARGETS[1]).name).write_text(text);installation=[]
    for target in TARGETS:
        path=PREP/'candidate'/Path(target).name;ast.parse(path.read_text());shutil.copyfile(ROOT/target,PREP/'baseline'/Path(target).name)
        installation.append({'target':target,'before':sha(ROOT/target),'candidate':rel(path),'after':sha(path)})
    save(PREP/'installation.json',installation)
    (PREP/'METHOD-REVIEW.md').write_text('''# Focused regression-scope audit

PASS after one reproduced assertion failure,not collection/import errors.
H38 compares its complete remaining fields with original v1;H28 compares its
complete remaining fields with v2. Exact-source and adverse controls remain.
No production source or retained answer changes. Preserve baseline failure and
source-comparison assertions rather than deleting their substantive checks.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,prior.METHOD,prior.prior.TEST)}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings[rel(prior.HERE/'outputs.json')]=sha(prior.HERE/'outputs.json');save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=303;task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),reason='Repair overbroad historical test assertion without changing production or answers',
        statutory_test_scope={'review':rel(PREP),'original_task_complete':False})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=44
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=303
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Validate source-specific regression scope,then continue substantive source applications',
            stop_condition='44 admissions;60s commands;7200s cumulative026;768MiB with reserve')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_044_measured_seconds']+120,
        'bytes':costs()['cumulative026_044_bytes']+3*(AUTH/'program.json').stat().st_size+1024**2,'estimate_only':True}
    assert forecast['seconds']<7200 and forecast['bytes']<764*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Reproduced test-only scope correction','Admission43 to44;no cumulative resource increase'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Both source-specific invariants and all adverse cases pass with unchanged production',
            'promotion_veto':['Source drift','Lost invariant','Missing control'],'continuation_veto':['Corruption','Budget exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Legal completeness','New product acceptance']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':43,'new_maximum':44,'retained_attempts':attempts,
            'reason':'One bounded regression conflict caused by independently reviewed source migrations',
            'next_discriminating_check':'Repaired combined suite retains both original-record invariants',
            'stop_condition':'Two60s commands;7200s cumulative026;768MiB with reserve',
            'same_scope_authorization':'User authorized continued repairs and build verification'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review);return {'status':'PASS','revision':303,'reproduced_failure':True,'forecast':forecast}


def execute():
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        assert sha(ROOT/row['target'])==row['before'];shutil.copyfile(ROOT/row['candidate'],ROOT/row['target'])
    pytest('repaired',[str(ROOT/n) for n in (*TARGETS,prior.prior.TEST)],0)
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for row in read(PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after']
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SCOPED_STATUTORY_REGRESSION_REPAIR','production_unchanged':True,
        'complete_prior_answer_preserved':True,'resources':costs(),
        'next_action':'Continue remaining original source/conditional application requirements'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':a['git_commit'],'command':['.venv/bin/python','-m','scripts.prospectus_statutory_test_scope','execute'],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(prior.HERE/'outputs.json'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Independent source corrections retain independent regression invariants

One historical whole-profile assertion failed because H28 was intentionally
corrected after the H38 repair. H38 now compares all its unchanged fields with
its original baseline;H28 independently compares its unchanged fields with its
pre-correction baseline. Exact quotes,offsets and negative controls remain.
The combined suite passes. Production and complete043 evidence are unchanged.

| Decision | Criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain test-only scope repair | Both field invariants and adverse tests pass | No production/evidence drift | Wider source application | Return to substantive requirements | New legal result or whole build |

The failure belonged to an overbroad test assertion,not the corrected sources or
packages. A changed source field outside the approved record transformations
would still fail the scoped regressions. No independent legal claim is added.
''');return result


def main():
    stage=sys.argv[1];assert stage in ('prepare','execute');folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused';save(folder/'started.json',{'stage':stage})
    start=time.monotonic()
    try:
        result=globals()[stage]();costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='execute':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
