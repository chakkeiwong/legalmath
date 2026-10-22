"""Authority preparation and bounded execution of the complete fixed coupon term."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET
from scripts import prospectus_coupon_premises as previous

ROOT,AUTH=previous.ROOT,previous.AUTH
PREP=AUTH/'reviews/shell-full-coupons-360'
HERE=AUTH/'attempts/finance-conventions/attempt-011'
PLAN='docs/plans/prospectus-shell-full-coupons-2026-10-20.md'
WORKER='scripts/prospectus_shell_coupons_worker.py'
TARGET='src/legalmath/prospectus/successor/contract_terms.py'
MODULE='src/legalmath/prospectus/successor/fixed_term.py'
TEST='tests/prospectus_successor/test_fixed_term.py'
BOUNDS={'combined_command_seconds':900,'stage_seconds':90,'combined_bytes':320*1024**2,
        'reserve_bytes':4*1024**2,'conservative_authoring_seconds':300}
STAGES=('freeze','tests','ordinary','quantlib','package','installed','seal')
read,save,sha,rel=previous.read,previous.save,previous.sha,previous.rel

def costs(extra=0):
    old=previous.costs()
    elapsed=old['new_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            elapsed+=sum(read(p).get('wall_seconds',0) for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,WORKER,TARGET,MODULE,TEST,rel(Path(__file__))))
    paths.add(AUTH/'revisions/0360.json')
    size=old['new_retained_bytes_conservative']+sum(p.stat().st_size for p in paths if p.exists())
    assert elapsed<BOUNDS['combined_command_seconds'],'Cumulative command time exhausted'
    assert size<BOUNDS['combined_bytes']-BOUNDS['reserve_bytes'],'Cumulative storage reserve reached'
    return {'combined_measured_seconds':elapsed,'combined_bytes_conservative':size,'bounds':BOUNDS,
            'authoring_charge_seconds':300,'historical_costs_reset':False,'older_unmeasured_runtime':'UNKNOWN'}

def command(name,argv,folder=HERE,timeout=90,cwd=ROOT):
    return previous.command(name,argv,folder=folder,timeout=timeout,cwd=cwd)

def prepare():
    from legalmath.prospectus.execution_authority import Authority,digest,write
    authority=Authority(ROOT);old,_,_=authority.spec();assert old['revision']==359
    attempts=[e['attempt'] for e in authority.events() if e['kind']=='ADMIT' and e['budget_key']=='finance-conventions']
    assert len(attempts)==old['budgets']['finance-conventions']['maximum_new_attempts']==10
    paths=[ROOT/TARGET,ROOT/'src/legalmath/prospectus/successor/fixed_coupon.py']
    for path in paths:
        target=PREP/'baseline'/path.name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(path.read_bytes())
    bindings={}
    for path in (AUTH/'attempts/finance-conventions/attempt-002').glob('selected-*-products.json.gz'):
        manifest=path.parent/'outputs.json';assert sha(path)==read(manifest)[path.name]
        bindings[rel(path)]=sha(path);bindings[rel(manifest)]=sha(manifest)
    for path in (AUTH/'attempts/finance-conventions/attempt-010').glob('ordinary/shell-selected-*-answer.json.gz'):
        manifest=path.parent.parent/'outputs.json';assert sha(path)==read(manifest)[str(path.relative_to(path.parent.parent))]
        bindings[rel(path)]=sha(path);bindings[rel(manifest)]=sha(manifest)
    for name in ('source-review.json','source-bindings.json','independent-calendar.json','quantlib-input.json'):
        path=AUTH/'attempts/finance-conventions/attempt-001'/name;bindings[rel(path)]=sha(path)
    save(PREP/'source-bindings.json',bindings)
    command('prepare-consumers',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/WORKER),str(ROOT),str(PREP),'prepare'],folder=PREP)
    # No local actualactual.cpp was found. Do not convert a fraction-only
    # package cross-check into a source-code or package-wide verification claim.
    save(PREP/'package-scope.json',{'version':'1.38','adapter':'scripts/prospectus_adoption_sidecar.py',
        'official_daycount_code_locally_available':False,'comparison':'EXECUTED_EXPLICIT_REFERENCE_FRACTIONS_ONLY',
        'historical_comparator':'finance001; no new package source-code conclusion', 'new_network':False})
    frozen={rel(p):sha(p) for p in PREP.rglob('*') if p.is_file()}
    frozen.update(bindings)
    for name in (PLAN,WORKER,rel(Path(__file__)),'scripts/prospectus_coupon_premises.py','scripts/prospectus_adoption_sidecar.py'):
        frozen[name]=sha(ROOT/name)
    save(PREP/'freeze.json',{'bindings':frozen,'skeptical_audit':'PASS: printed annual term and form-specific rules; independent ten-row arithmetic; hypothetical event inputs; preserved first/legacy answers; no unproved settlement or package claim'})
    new=deepcopy(old);new['revision']=360
    task=next(t for t in new['tasks'] if t['id']=='finance-conventions')
    task.update(dossier=PLAN,reason='Calculate all ten source-bound Shell coupons through real selected-term consumer; retain form-specific aggregation and explicit hypothetical events')
    task['full_coupon_term']={'version':'shell-full-coupons.v1','review':rel(PREP),'bounds':BOUNDS,'retained_admissions':attempts,'automatic_retry':False,'whole_task_acceptance':False}
    task['inputs']=sorted((set(task['inputs'])-{TARGET,MODULE,TEST})|set(frozen)|{rel(PREP/'freeze.json')})
    new['budgets']['finance-conventions']['maximum_new_attempts']=11
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=360
    route=next(r for r in routes['tasks'] if r['task']=='finance-conventions')
    route.update(task_sha256=digest(task),dossier=PLAN,remaining='Ten dates currently expose first coupon only; complete conditional coupon term and original finance coverage still open',
        next_action='Execute reviewed complete fixed-term consumer, exact independent arithmetic, ordinary/installed verification and preserved legacy answers; seal/record/refresh then original acceptance review',stop_condition=json.dumps(BOUNDS,sort_keys=True))
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for name in (TARGET,MODULE,TEST):new['continuation_review']['bindings'].pop(name,None)
    new['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':digest(old),'changes':['Same original finance task and scope, all ten admissions/costs retained','Distinct optional complete coupon term with conditional form-specific calculations','One admission10-to11 with cumulative359/360 bounds'],
        'skeptical_audit':read(PREP/'freeze.json')['skeptical_audit'],
        'evidence_contract':{'question':'Do all ten printed annual coupon periods reach the real consumer with correct conditional form-specific amounts?',
            'baseline':'Source-bound Shell002, current010 legacy answers, independently frozen ten-row integer/date oracle',
            'primary':'Ten exact periods/fractions/amounts, input retention, first-coupon and legacy preservation, ordinary/installed equality',
            'veto':['Wrong rounding basis','Omitted period','Changed unrelated question','Assumption or input drift','Wrong imports'],
            'continuation_veto':['Corrupted evidence','Frozen method drift','Cumulative bounds exhausted'],
            'explanatory':['Counts','Time','Storage'],
            'not_concluded':['Actual ownership or payment','Redemption principal','Settlement','Package-wide correctness','Whole task/build completion']},
        'scope_unchanged':True,'budget_unchanged':False,'original_obligations_preserved':True,
        'budget_revision':{'budget_key':'finance-conventions','previous_maximum':10,'new_maximum':11,'retained_attempts':attempts,
            'reason':'Complete missing nine coupon calculations in original G14/G15 domain',
            'next_discriminating_check':'Source dates and form-specific integer oracle through actual P5/full consumer',
            'stop_condition':BOUNDS,'same_scope_authorization':'User refresh master program and continue general build'}}
    assert new['obligations']==old['obligations'] and new['build_contract']==old['build_contract']
    forecast=costs()['combined_bytes_conservative']+3*len(json.dumps(new,sort_keys=True,indent=2).encode())+56*1024**2
    assert forecast<BOUNDS['combined_bytes']-BOUNDS['reserve_bytes']
    save(PREP/'preflight.json',{'forecast_combined_bytes':forecast,'prior':previous.costs(),'bounds':BOUNDS,'historical_costs_reset':False})
    write(PREP/'proposal.json',new,exclusive=True);write(PREP/'review.json',review,exclusive=True)
    return {'status':'PASS','revision':360,'prepared':read(PREP/'prepare-summary.json'),'forecast_bytes':forecast}

def frozen():
    for name,h in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/name)==h,'Frozen preparation changed: '+name
    if (HERE/'methods.json').exists():
        for name,h in read(HERE/'methods.json')['bindings'].items():assert sha(ROOT/name)==h,'Frozen method changed: '+name

def admitted():
    from legalmath.prospectus.execution_authority import Authority,digest
    authority=Authority(ROOT);p,ts,_=authority.spec();a=read(HERE/'admission.json')
    assert p['revision']==360 and a['program_sha256']==digest(p) and a['binding']==authority.binding(ts['finance-conventions'])

def freeze():
    paths=[ROOT/PLAN,Path(__file__),ROOT/WORKER,ROOT/TEST,HERE/'METHOD-REVIEW.md']
    production=[p for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    save(HERE/'methods.json',{'bindings':{rel(p):sha(p) for p in paths+production},'production_map':{str(p.relative_to(ROOT/'src/legalmath')):sha(p) for p in production}})
    return {'status':'PASS','frozen_files':len(paths+production)}

def tests():
    command('tests',[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',TEST,'tests/prospectus_successor/test_initial_coupon.py',
        'tests/prospectus_successor/test_fixed_phase.py','tests/prospectus_successor/test_coupon_premises.py',
        'tests/prospectus_successor/test_closure_finance.py','--junitxml='+str(HERE/'tests.xml')])
    suites=ET.parse(HERE/'tests.xml').getroot().findall('testsuite');assert suites
    assert all(int(s.get(k,'0'))==0 for s in suites for k in ('failures','errors','skipped'))
    return {'status':'PASS','tests':sum(int(s.get('tests')) for s in suites)}

def ordinary():
    command('ordinary',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/WORKER),str(ROOT),str(HERE),'ordinary'])
    value=read(HERE/'ordinary-summary.json');return {'status':value['status'],'cases':len(value['cases']),'legacy_equal':value['legacy_complete_answers_equal']}

def quantlib():
    folder=HERE/'quantlib';folder.mkdir()
    command('quantlib',['/tmp/prospectus-adoption-tools/bin/python','-B','-m','scripts.prospectus_adoption_sidecar','coupon','--input',str(PREP/'package-input.json'),'--output',str(folder)])
    result=read(folder/'result.json');assert result['version']=='1.38' and len(result['fractions'])==10
    from fractions import Fraction
    expected=[Fraction(457,366)]+[Fraction(1)]*9
    assert [r['id'] for r in result['fractions']]==[str(i) for i in range(10)]
    assert all(abs(r['year_fraction']-float(e))<1e-12 for r,e in zip(result['fractions'],expected))
    assert result['evaluation_date_used'] is False and result['missing_reference_fallback_used'] is False
    save(HERE/'package-comparison.json',{'status':'PASS','fractions':10,'absolute_tolerance':1e-12,'scope':'Explicit reference fractions only; no legal/form/rounding/event capability claim'})
    return {'status':'PASS','matched_fractions':10}

def package():
    from scripts import prospectus_reference_mentions_run as packaging
    packaging.ROOT,packaging.AUTH,packaging.HERE=ROOT,AUTH,HERE
    packaging.execute=lambda name,argv,timeout=90,cwd=ROOT:command(name,argv,timeout=min(timeout,90),cwd=cwd)
    return packaging.package()

def installed():
    command('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),'installed'],cwd=HERE)
    value=read(HERE/'installed-summary.json');return {'status':value['status'],'cases':len(value['cases']),'ordinary_equal':value['installed_ordinary_equal']}

def seal():
    result={'status':'PASS','task':'finance-conventions','whole_task_complete':False,'build_criteria_claimed':[],
        'classification':'CONDITIONAL_FULL_FIXED_COUPON_TERM','ordinary':read(HERE/'ordinary-summary.json'),
        'installed':read(HERE/'installed-summary.json'),'quantlib':read(HERE/'package-comparison.json'),'resources':costs()}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],'commands':sorted(rel(p) for p in (HERE/'commands').glob('*.json')),
        'environment':str(ROOT/'.venv/bin/python'),'installed_environment':read(HERE/'package.json')['python'],
        'package_environment':'/tmp/prospectus-adoption-tools/bin/python','CPU_GPU':'CPU;GPU deliberately hidden',
        'data_version':sha(PREP/'source-bindings.json'),'seeds':'N/A deterministic','wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    return {'status':'PASS','whole_task_complete':False,'resources':costs()}

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not folder.exists(),'Unchanged retry refused'
    if stage!='prepare':
        frozen();admitted()
        for old in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/old/'result.json')['status']=='PASS'
    costs();start=time.monotonic();save(folder/'started.json',{'command':sys.argv,'utc':datetime.now(timezone.utc).isoformat()})
    try:
        result=globals()[stage]();elapsed=time.monotonic()-start;costs(elapsed)
        if stage!='prepare':frozen()
        result.update(wall_seconds=elapsed);save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except Exception as exc:
        save(folder/'failure.json',{'status':'FAIL','type':type(exc).__name__,'reason':str(exc),'wall_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
