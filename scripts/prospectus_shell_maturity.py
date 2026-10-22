"""Bounded, restartable source-to-answer evidence for scheduled Shell redemption."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_coupon_premises as common

ROOT, AUTH = common.ROOT, common.AUTH
PREP = AUTH / 'reviews/shell-maturity-361'
HERE = AUTH / 'attempts/finance-conventions/attempt-012'
PLAN = 'docs/plans/prospectus-shell-maturity-2026-10-20.md'
WORKER = 'scripts/prospectus_shell_maturity_worker.py'
TARGET = 'src/legalmath/prospectus/successor/contract_terms.py'
MODULE = 'src/legalmath/prospectus/successor/fixed_maturity.py'
PROFILE = 'src/legalmath/prospectus/successor/shell_maturity_spec.json'
TEST = 'tests/prospectus_successor/test_fixed_maturity.py'
BOUNDS = {'combined_command_seconds': 1800, 'combined_bytes': 512*1024**2,
          'reserve_bytes': 4*1024**2, 'stage_seconds': 90, 'render_seconds': 25}
DEPENDENCIES = {'freeze': (), 'tests': ('freeze',), 'ordinary': ('freeze',),
                'package': ('freeze',), 'installed': ('ordinary', 'package'),
                'seal': ('tests', 'ordinary', 'package', 'installed')}
read, save, sha, rel = common.read, common.save, common.sha, common.rel


def command(name, argv, folder=HERE, timeout=90, cwd=ROOT):
    common.command(name, argv, folder=folder, timeout=timeout, cwd=cwd)


def costs(extra=0):
    old = read(PREP/'prior-costs.json') if (PREP/'prior-costs.json').exists() else {}
    elapsed = old.get('combined_measured_seconds', 0) + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            elapsed += sum(read(p).get('wall_seconds', 0) for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN, WORKER, TARGET, MODULE, PROFILE, TEST, rel(Path(__file__))))
    paths.update((AUTH/'revisions/0361.json', AUTH/'program.json'))
    size = old.get('combined_bytes_conservative', 0) + sum(p.stat().st_size for p in paths if p.exists())
    if elapsed >= BOUNDS['combined_command_seconds'] or size >= BOUNDS['combined_bytes']-BOUNDS['reserve_bytes']:
        raise ValueError('Cumulative maturity continuation bound exhausted')
    return {'combined_measured_seconds': elapsed, 'combined_bytes_conservative': size,
            'bounds': BOUNDS, 'historical_costs_reset': False,
            'older_unmeasured_runtime': 'UNKNOWN', 'authoring_wall_time': 'Separate preparation-to-freeze timestamps'}


def sources():
    from scripts import prospectus_shell_coupons as prior
    from legalmath.prospectus.successor.occurrences import anchor
    save(PREP/'prior-costs.json', prior.costs())
    source = AUTH/'attempts/finance-conventions/attempt-001'
    path = source/'source-P1.json.gz'
    assert sha(path) == read(source/'outputs.json')[path.name]
    graph = read(path)['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    ranges = {
        'currency': [('shell-2030-final', 2, 12, 12)],
        'maturity': [('shell-2030-final', 2, 23, 24)],
        'denominations_and_unit': [('shell-2030-final', 2, 35, 42)],
        'final_amount': [('shell-2030-final', 3, 23, 26)],
        'payment_overrides': [('shell-2030-final', 3, 32, 43)],
        'scheduled_redemption': [('shell-2020-base', 47, 7, 11)],
        'interest_cessation': [('shell-2020-base', 42, 46, 49)],
        'cancellation': [('shell-2020-base', 49, 13, 18)],
        'payment_method': [('shell-2020-base', 49, 21, 44)],
        'presentation': [('shell-2020-base', 49, 45, 54), ('shell-2020-base', 50, 1, 7)],
        'global_recipient': [('shell-2020-base', 50, 8, 18)],
        'coupon_presentation': [('shell-2020-base', 50, 28, 50), ('shell-2020-base', 51, 1, 3)],
        'payment_day': [('shell-2020-base', 51, 4, 27)],
        'principal_scope': [('shell-2020-base', 51, 28, 47)],
    }
    groups = {key: [anchor(units[f'{doc}:p{page}:l{line}'])
                    for doc, page, lo, hi in spans for line in range(lo, hi+1)]
              for key, spans in ranges.items()}
    profile = {'version': 'shell-2030-maturity-source.v1', 'groups': groups,
               'instrument_id': graph['instrument_id'],
               'scope': 'SUPPLIED_SHELL_2030_GBP_SCHEDULED_REDEMPTION_ONLY'}
    save(PREP/'source-profile.json', profile)
    bindings = {rel(path): sha(path), rel(source/'outputs.json'): sha(source/'outputs.json')}
    documents = read(path)['payload']['request']['bundle']['documents']
    for doc in documents:
        if doc['id'] != 'hypotheses':
            assert sha(ROOT/doc['path']) == doc['sha256']
            bindings[doc['path']] = doc['sha256']
    for name in ('final-2.png', 'final-3.png'):
        path = source/'images'/name
        assert sha(path) == read(source/'outputs.json')['images/'+name]
        bindings[rel(path)] = sha(path)
    pdf = ROOT/next(d['path'] for d in documents if d['id']=='shell-2020-base')
    (PREP/'images').mkdir()
    for page in (42, 47, 49, 50, 51):
        command(f'render-{page}', ['pdftoppm', '-f', str(page), '-l', str(page), '-scale-to', '1400',
                '-png', '-singlefile', str(pdf), str(PREP/'images'/f'base-{page}')], folder=PREP, timeout=25)
    save(PREP/'source-bindings.json', bindings)
    return {'status': 'PASS', 'source_groups': len(groups), 'rendered_pages': 5, 'new_extraction': False}


def prepare():
    from legalmath.prospectus.execution_authority import Authority, digest, write
    authority = Authority(ROOT)
    old, _, _ = authority.spec()
    assert old['revision'] == 360
    assert read(PREP/'stages/sources/result.json')['status'] == 'PASS'
    assert (PREP/'SOURCE-REVIEW.md').exists()
    attempts = [e['attempt'] for e in authority.events()
                if e['kind']=='ADMIT' and e['budget_key']=='finance-conventions']
    assert len(attempts) == old['budgets']['finance-conventions']['maximum_new_attempts'] == 11
    for path in (ROOT/TARGET, ROOT/'src/legalmath/prospectus/successor/fixed_term.py'):
        dest = PREP/'baseline'/path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(path.read_bytes())
    command('prepare', [str(ROOT/'.venv/bin/python'), '-B', str(ROOT/WORKER), str(ROOT), str(PREP), 'prepare'], folder=PREP)
    frozen = {rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    frozen.update(read(PREP/'source-bindings.json'))
    frozen.update({n: sha(ROOT/n) for n in (PLAN, WORKER, rel(Path(__file__)),
        'scripts/prospectus_coupon_premises.py', 'scripts/prospectus_shell_maturity_checks.py')})
    # Preparation's own result is written after this function returns.
    save(PREP/'freeze.json', {'bindings': frozen, 'skeptical_audit':
        'PASS: original011 full comparator; complete selected redemption/qualification source groups; separate principal entitlement; independent arithmetic; explicit dependency and failure semantics'})
    new = deepcopy(old); new['revision'] = 361
    task = next(t for t in new['tasks'] if t['id']=='finance-conventions')
    task.update(dossier=PLAN, reason='Complete source-bound conditional Shell maturity principal and coupon cash flows; preserve separate entitlements and payment qualifications', build_criteria_scope=[])
    task['scheduled_maturity'] = {'version': 'shell-maturity.v1', 'review': rel(PREP), 'bounds': BOUNDS,
        'retained_admissions': attempts, 'automatic_retry': False, 'whole_task_acceptance': False,
        'stage_dependencies': DEPENDENCIES}
    mutable = {TARGET, MODULE, PROFILE, TEST}
    task['inputs'] = sorted((set(task['inputs'])-mutable)|set(frozen)|{rel(PREP/'freeze.json')})
    new['budgets']['finance-conventions']['maximum_new_attempts'] = 12
    routes = read(ROOT/old['continuation_review']['routes']); routes['baseline_revision'] = 361
    route = next(r for r in routes['tasks'] if r['task']=='finance-conventions')
    route.update(task_sha256=digest(task), dossier=PLAN,
        remaining='011 full coupons recorded; scheduled principal not calculated. Original wider finance acceptance remains open.',
        next_action='Execute reviewed maturity calculation and independent checks; persist/refresh after each result; reconcile original finance obligations and continue ready source work.',
        stop_condition=json.dumps(BOUNDS, sort_keys=True))
    # Refresh the completed097 description without changing its frozen task or allowance.
    route = next(r for r in routes['tasks'] if r['task']=='basf-references')
    route.update(remaining='097 printed-scope guard and complete ordinary/installed preservation recorded. Original references, law and meaning scope remain open.',
        next_action='Preserve097; return to remaining source interpretation and applicability requirements, without another identical scope or package run.')
    save(PREP/'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP/'routes.json'))
    for name in mutable:
        new['continuation_review']['bindings'].pop(name, None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (PLAN, rel(PREP/'routes.json'), rel(PREP/'freeze.json'))})
    review = {'baseline': digest(old), 'changes': [
        'Preserve all original obligations/tasks,11 finance admissions and cumulative resource history',
        'Add distinct optional maturity cash flows with selected source profile and separate principal entitlement',
        'Explicit success/completion dependencies and finite changed-repair rule; stale097 route refreshed'],
        'skeptical_audit': read(PREP/'freeze.json')['skeptical_audit'],
        'evidence_contract': {'question':'Can actual P5/final answers calculate source-selected scheduled principal with every declared payment condition?',
            'baseline':'Sealed011 complete answers and fresh same-input coupon-only comparators',
            'primary':'Exact independent principal/coupon flows, selected source identity, legacy preservation and ordinary/installed equality',
            'veto':['Wrong amount/source/recipient/date','Lost qualifications','Changed legacy answer','Accepted input/output forgery','Wrong imports'],
            'continuation_veto':['Invalid authority','Corrupt common evidence','Cumulative bound exhausted'],
            'explanatory':['Test count','Time','Storage'],
            'not_concluded':['Actual entitlement/payment','Full settlement','Arbitrary source interpretation','Whole task/build completion']},
        'scope_unchanged':True, 'budget_unchanged':False, 'original_obligations_preserved':True,
        'budget_revision':{'budget_key':'finance-conventions','previous_maximum':11,'new_maximum':12,
            'retained_attempts':attempts,'reason':'Original G14/G15 scheduled redemption missing after full coupons',
            'next_discriminating_check':'Complete selected source groups and separate principal cash flows through P5/consumer',
            'stop_condition':BOUNDS,'same_scope_authorization':'User recover and continue general build'}}
    assert new['obligations'] == old['obligations'] and new['build_contract'] == old['build_contract']
    forecast = costs()['combined_bytes_conservative']+3*len(json.dumps(new,sort_keys=True,indent=2).encode())+64*1024**2
    assert forecast < BOUNDS['combined_bytes']-BOUNDS['reserve_bytes']
    save(PREP/'preflight.json', {'forecast_combined_bytes':forecast,'resources':costs(),'dependency_audit':'PASS'})
    write(PREP/'proposal.json',new,exclusive=True);write(PREP/'review.json',review,exclusive=True)
    return {'status':'PASS','revision':361,'cases':read(PREP/'prepare-summary.json')['cases'],'forecast_bytes':forecast}


def frozen():
    for file in (PREP/'freeze.json', HERE/'methods.json'):
        if file.exists():
            for name, expected in read(file)['bindings'].items():
                assert sha(ROOT/name) == expected, 'Frozen evidence changed: '+name


def admitted():
    from legalmath.prospectus.execution_authority import Authority,digest
    authority=Authority(ROOT);program,tasks,_=authority.spec();a=read(HERE/'admission.json')
    assert program['revision']==361 and a['program_sha256']==digest(program)
    assert a['binding']==authority.binding(tasks['finance-conventions'])


def freeze():
    production=[p for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    paths=[ROOT/PLAN,Path(__file__),ROOT/WORKER,ROOT/'scripts/prospectus_shell_maturity_checks.py',ROOT/TEST,HERE/'METHOD-REVIEW.md']
    save(HERE/'methods.json', {'bindings':{rel(p):sha(p) for p in paths+production},
        'production_map':{str(p.relative_to(ROOT/'src/legalmath')):sha(p) for p in production},
        'authoring_started_utc':read(PREP/'stages/sources/started.json')['utc'],
        'frozen_utc':datetime.now(timezone.utc).isoformat()})
    return {'status':'PASS','files':len(paths+production)}


def tests():
    command('tests',[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',TEST,
        'tests/prospectus_successor/test_fixed_term.py','tests/prospectus_successor/test_initial_coupon.py',
        'tests/prospectus_successor/test_coupon_premises.py','--junitxml='+str(HERE/'tests.xml')])
    suites=ET.parse(HERE/'tests.xml').getroot().findall('testsuite')
    assert suites and all(int(s.get(k,'0'))==0 for s in suites for k in ('failures','errors','skipped'))
    return {'status':'PASS','tests':sum(int(s.get('tests')) for s in suites)}


def ordinary():
    command('ordinary',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/WORKER),str(ROOT),str(HERE),'ordinary'])
    result=read(HERE/'ordinary-summary.json')
    return {'status':result['status'],'cases':len(result['cases']),'legacy_equal':result['legacy_complete_answers_equal']}


def package():
    from scripts import prospectus_reference_mentions_run as packaging
    packaging.ROOT,packaging.AUTH,packaging.HERE=ROOT,AUTH,HERE
    packaging.execute=lambda name,argv,timeout=90,cwd=ROOT:command(name,argv,timeout=min(timeout,90),cwd=cwd)
    return packaging.package()


def installed():
    command('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),'installed'],cwd=HERE)
    result=read(HERE/'installed-summary.json')
    return {'status':result['status'],'cases':len(result['cases']),'ordinary_equal':result['installed_ordinary_equal']}


def seal():
    assert (HERE/'RESULT.md').exists(), 'Substantive result analysis required'
    save(HERE/'result.json', {'status':'PASS','task':'finance-conventions','whole_task_complete':False,
        'build_criteria_claimed':[],'classification':'CONDITIONAL_SCHEDULED_PRINCIPAL_AND_COUPONS',
        'ordinary':read(HERE/'ordinary-summary.json'),'installed':read(HERE/'installed-summary.json'),'resources':costs()})
    save(HERE/'run-manifest.json', {'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':sorted(rel(p) for folder in (PREP,HERE) for p in (folder/'commands').glob('*.json')),
        'environment':str(ROOT/'.venv/bin/python'),'installed_environment':read(HERE/'package.json')['python'],
        'CPU_GPU':'CPU; GPU deliberately hidden','data_version':sha(PREP/'source-bindings.json'),
        'seeds':'N/A deterministic','wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    return {'status':'PASS','whole_task_complete':False,'resources':costs()}


def frontier():
    states={}
    for stage in DEPENDENCIES:
        folder=HERE/'stages'/stage
        states[stage]=read(folder/'result.json')['status'] if (folder/'result.json').exists() else (
            'FAIL' if (folder/'failure.json').exists() else 'INTERRUPTED_OR_RUNNING' if folder.exists() else 'PENDING')
    ready=[s for s,deps in DEPENDENCIES.items() if states[s]=='PENDING' and all(states[d]=='PASS' for d in deps)]
    return {'stage_states':states,'ready':ready,'independent_review':'Original finance acceptance reconciliation remains available',
            'whole_program_complete':False}


def main():
    stage=sys.argv[1]
    if stage=='status':
        print(json.dumps(frontier()));return
    assert stage in {'sources','prepare'}|set(DEPENDENCIES)
    folder=(PREP if stage in {'sources','prepare'} else HERE)/'stages'/stage
    assert not folder.exists(),'Unchanged retry refused; inspect retained stage first'
    if stage in DEPENDENCIES:
        frozen();admitted();assert stage in frontier()['ready'],'Stage prerequisites have not succeeded'
    costs();start=time.monotonic();save(folder/'started.json',{'command':sys.argv,'utc':datetime.now(timezone.utc).isoformat()})
    try:
        result=globals()[stage]();elapsed=time.monotonic()-start;costs(elapsed)
        if stage in DEPENDENCIES:frozen()
        result.update(wall_seconds=elapsed);save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps({'result':result,'frontier':frontier()}))
    except Exception as exc:
        save(folder/'failure.json',{'status':'FAIL','type':type(exc).__name__,'reason':str(exc),'wall_seconds':time.monotonic()-start})
        raise


if __name__=='__main__':main()
