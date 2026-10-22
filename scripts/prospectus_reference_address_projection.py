"""Reviewed repair of paragraph transformation provenance; original084 retained."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, json, os, shutil, signal, sys, time
from scripts import prospectus_reference_addresses as previous
from scripts import prospectus_reference_address_projection_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest

ROOT, AUTH, engine = previous.ROOT, previous.AUTH, previous.engine
OLD_PREP, OLD_HERE = previous.PREP, previous.HERE
PREP = AUTH / 'reviews/reference-address-projection-346'
HERE = AUTH / 'attempts/basf-references/attempt-085'
PLAN = 'docs/plans/prospectus-reference-address-projection-repair-2026-10-19.md'
METHOD = 'scripts/prospectus_reference_address_projection.py'
WORKER = previous.WORKER
TEST = 'tests/prospectus_successor/test_reference_address_projection.py'
TARGETS = ('src/legalmath/prospectus/successor/reference_addresses.py',
           'tests/prospectus_successor/conftest.py')
FILES = (PLAN, METHOD, WORKER, TEST, 'scripts/prospectus_reference_address_projection_oracle.py',
         'scripts/prospectus_reference_address_projection_draft.py', 'scripts/prospectus_reference_addresses_failure.py')
STAGES = previous.STAGES
read, save, sha, rel = previous.read, previous.save, previous.sha, previous.rel

def costs(extra=0):
    start = read(PREP/'accounting-start.json'); base = start['prior']
    seconds = base['combined_measured_seconds'] + extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES); paths.add(AUTH/'revisions/0346.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size += sum(max(0,(ROOT/n).stat().st_size-start['production_bytes'][n]) for n in TARGETS)
    charge=base['conservative_extra_seconds']
    assert seconds+charge<24000 and size<3452*1024**2,'Cumulative structural-reference bound'
    return {'combined_measured_seconds':seconds,'conservative_extra_seconds':charge,
        'combined_accounted_seconds':seconds+charge,'combined_bytes':size,'seconds_bound':24000,
        'bytes_bound_with_4MiB_reserve':3456*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}

def testfiles():
    return [TEST,'tests/prospectus_successor/test_reference_scope.py',
        'tests/prospectus_successor/test_reference_scope_headers.py',
        'tests/prospectus_successor/test_paragraph_references.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py']

def tests():
    engine.execute('collection',[str(ROOT/'.venv/bin/python'),'-m','pytest','--collect-only','-q',
        str(ROOT/'tests/prospectus_successor')],60)
    collection=(HERE/'commands/collection.log').read_text()
    assert 'test_reference_addresses.py::' not in collection
    assert 'test_reference_address_projection.py::test_original_source_targets_before_expensive_consumers' in collection
    assert 'test_reference_requirement_copies.py::' not in collection
    assert 'test_reference_requirement_raw_copies.py::test_production_direct_copy_passes' in collection
    return previous.tests()

def prepare():
    program=read(AUTH/'program.json'); assert program['revision']==345
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==84
    assert any(e['kind']=='REJECT' and e.get('attempt')==rel(OLD_HERE) for e in events)
    for n,v in read(OLD_HERE/'outputs.json').items(): assert sha(OLD_HERE/n)==v,n
    for n,v in read(OLD_PREP/'freeze.json')['bindings'].items(): assert sha(ROOT/n)==v,n
    for r in read(OLD_PREP/'installation.json'): assert sha(ROOT/r['target'])==r['after']
    frozen=read(OLD_PREP/'source-freeze.json'); assert frozen['candidate_absent'] is True
    assert sha(OLD_PREP/'expected.json')==frozen['expected_sha256']
    assert sha(ROOT/'docs/plans/prospectus-reference-addresses-2026-10-19.md')==frozen['plan_sha256']
    for name in ('source-freeze.json','expected.json','profile.json','profiles.json'):
        shutil.copyfile(OLD_PREP/name,PREP/name)
    (PREP/'baseline').mkdir(); installation=[]
    for name in TARGETS:
        path=ROOT/name; candidate=PREP/'candidate'/path.name; ast.parse(candidate.read_text())
        shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':name,'before':sha(path),'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,*testfiles(),'pyproject.toml',
        'scripts/prospectus_reference_addresses.py','scripts/prospectus_residual_coverage.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (OLD_HERE/'outputs.json',previous.prior.HERE/'ordinary-answer.json.gz',previous.PRODUCTS): bindings[rel(p)]=sha(p)
    for r in read(previous.PRODUCTS)['products'].values(): bindings[r['path']]=r['sha256']
    for r in read(PREP/'profiles.json')['profiles']: bindings[r['path']]=r['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program); proposal['revision']=346
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Repair whole-paragraph transformation provenance after reproduced citation-only projection failure',
        reference_address_projection_review={'review':rel(PREP),'original_task_complete':False,
            'failed_attempt':rel(OLD_HERE),'accounted_seconds_bound':24000,'bytes_bound_with_4MiB_reserve':3456*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=85
    routes=read(ROOT/program['continuation_review']['routes']); routes['baseline_revision']=346
    for row in routes['tasks']:
        if row['task']=='basf-references': row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify unchanged structural destinations with exact transformation provenance; retain failed084',
            stop_condition='85 admissions; 24000 accounted seconds/3456MiB with4MiBreserve; no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS: proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs(); forecast={'seconds':snapshot['combined_accounted_seconds']+1150,
        'bytes':snapshot['combined_bytes']+128*1024**2,'estimate_only':True}
    assert forecast['seconds']<24000 and forecast['bytes']<3452*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Preserve current construction provenance for transformed body spans',
            'Retain original destinations,grammar,citation checker and full prior answers'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,'forecast':forecast},
        'evidence_contract':{'primary':'Original destinations,transformation refusals and complete installed equality',
            'promotion_veto':['Wrong source/target','Invented quotation','Changed old answer','Unknown promoted'],
            'continuation_veto':['Frozen drift','Corrupt baseline','Cumulative bound'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['General recall','Legal meaning','Historical applicability','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':84,'new_maximum':85,
            'retained_attempts':attempts,'reason':'084 rejects valid supplied final terms at its citation-only body projector',
            'next_discriminating_check':'Unchanged destination readings,transformation provenance,complete installed answer',
            'stop_condition':'24000seconds/3456MiB cumulative with4MiBreserve; no unchanged retry',
            'same_scope_authorization':'User requested reviewed internally supported build and continued repairs'},
        'resource_accounting':{'retained_costs':snapshot,'limits_extended':False,'seconds_bound':24000,'bytes_with_reserve':3456*1024**2}}
    with (PREP/'proposal.json').open('x') as stream: json.dump(proposal,stream,ensure_ascii=False,separators=(',',':'))
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':346,'candidate_evaluated':False,'forecast':forecast}

def main():
    stage=sys.argv[1]; assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':
        snapshot=previous.costs()
        save(PREP/'accounting-start.json',{'prior':snapshot,
            'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
            'program_bytes':(AUTH/'program.json').stat().st_size,
            'production_bytes':{n:(ROOT/n).stat().st_size for n in TARGETS}})
    else:
        for preceding in STAGES[:STAGES.index(stage)]: assert read(HERE/'stages'/preceding/'result.json')['status']=='PASS'
        costs()
    for module in (previous,engine):
        module.PREP,module.HERE,module.PLAN,module.METHOD,module.WORKER,module.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
        module.costs,module.testfiles=costs,testfiles
    previous.oracle=oracle
    engine.cli_arguments=previous.cli_arguments
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    bound=90 if stage=='prepare' else 420
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_reference_address_projection',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Projection repair stage bound')));signal.alarm(bound)
    try:
        if stage!='prepare': engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(previous,stage,None) or getattr(engine,stage))()
        if stage!='prepare': engine.frozen()
        costs(time.monotonic()-started);result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal': save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-started});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
