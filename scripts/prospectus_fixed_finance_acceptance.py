"""Named finite finance acceptance with complete original evidence preserved."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority

PREP = AUTH / 'reviews/fixed-finance-377'
HERE = AUTH / 'attempts/finance-conventions/attempt-013'
BASE = AUTH / 'attempts/finance-conventions/attempt-012'
ORIGINAL = AUTH / 'reviews/shell-maturity-361'
PLAN = 'docs/plans/prospectus-fixed-finance-acceptance-2026-10-20.md'
VALIDATOR = 'conditional-fixed-finance.v1'
SCOPE = 'SOURCE_BOUND_CONDITIONAL_FIXED_RATE_ONLY'
FILES = [PLAN, 'scripts/prospectus_fixed_finance_acceptance.py',
    'scripts/prospectus_fixed_finance_verify.py', 'scripts/prospectus_fixed_finance_worker.py', 'scripts/prospectus_shell_maturity_worker.py',
    'scripts/prospectus_shell_maturity_checks.py', 'scripts/prospectus_office_composition.py',
    'scripts/prospectus_default_holder.py', 'src/legalmath/prospectus/execution_acceptance.py',
    'tests/prospectus/test_fixed_finance_acceptance.py']
TESTS = ['tests/prospectus/' + n for n in ('test_fixed_finance_acceptance.py', 'test_execution_acceptance.py')]
TESTS += ['tests/prospectus_successor/' + n for n in ('test_fixed_maturity.py', 'test_fixed_term.py',
    'test_fixed_phase.py', 'test_coupon_premises.py', 'test_registration_groups.py', 'test_bond_basis.py')]
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'verify': ('tests', 'ordinary', 'package', 'installed'), 'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed', 'verify')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    records = list(PREP.glob('*-execution.json')) + list(PREP.glob('*-failure.json'))
    records += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in records)
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES); paths.update(AUTH / 'revisions' / f'{n:04d}.json' for n in (377,378,379))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 120, start['prior_bytes'] + size
    assert measured < 750 and size < 156 * 1024**2, 'Fixed-finance increment exhausted'
    assert total < 1800 and combined < 508 * 1024**2, 'Retained finance cumulative bound exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def method_equivalence():
    """Permit only the inspected input-retention/deepcopy change, never math drift."""
    old = AUTH / 'reviews/current-default-verifier-258/methods/src/legalmath/prospectus/successor/fixed_coupon.py'
    current = ROOT / 'src/legalmath/prospectus/successor/fixed_coupon.py'
    prior = read(AUTH / 'attempts/finance-conventions/attempt-009/run-manifest.json')['frozen_methods']
    assert sha(old) == prior[rel(current)]
    before, after = ast.parse(old.read_text()), ast.parse(current.read_text())
    imports = [n for n in after.body if isinstance(n, ast.ImportFrom) and n.module == 'copy']
    assert len(imports) == 1 and [n.name for n in imports[0].names] == ['deepcopy']
    after.body.remove(imports[0])
    fn = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'calculate')
    ret = fn.body[-1]; assert isinstance(ret, ast.Return) and isinstance(ret.value, ast.Dict)
    keys = [k.value if isinstance(k, ast.Constant) else None for k in ret.value.keys]
    for key in ('events', 'source_evidence'):
        i = keys.index(key); value = ret.value.values[i]
        assert isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'deepcopy'
        assert len(value.args) == 1 and not value.keywords
        ret.value.values[i] = value.args[0]
    i = keys.index('calculation_inputs'); value = ret.value.values[i]
    assert ast.dump(value) == ast.dump(ast.parse('deepcopy(s)', mode='eval').body)
    del ret.value.keys[i]; del ret.value.values[i]
    assert ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False)
    unchanged = {}
    for name in ('src/legalmath/prospectus/successor/fixed_phase.py',
                 'src/legalmath/prospectus/semantics.py', 'scripts/prospectus_fixed_phase_oracle.py',
                 'scripts/prospectus_fixed_phase_package.py', 'scripts/prospectus_adoption_sidecar.py'):
        assert sha(ROOT / name) == prior[name], name
        unchanged[name] = sha(ROOT / name)
    package = read(AUTH / 'attempts/finance-conventions/attempt-011/package.json')['files']
    for name in ('prospectus/successor/fixed_coupon.py', 'prospectus/successor/fixed_term.py',
                 'prospectus/successor/coupon_dates.py',
                 'prospectus/semantics.py'):
        assert sha(ROOT / 'src/legalmath' / name) == package[name], name
        unchanged['src/legalmath/' + name] = package[name]
    return {'status': 'PASS', 'numerical_methods_unchanged': True,
        'fixed_coupon_difference': 'Only deepcopy of events/evidence and additive complete calculation_inputs',
        'old_fixed_coupon': {'path': rel(old), 'sha256': sha(old)}, 'current_fixed_coupon_sha256': sha(current),
        'unchanged_methods': unchanged, 'new_package_execution_claimed': False}


def prepare(recovery=False, final=False):
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 376 and not HERE.exists()
    assert (PREP / 'preparation-failure.json').exists() if recovery else not PREP.exists()
    assert not (PREP / 'preparation-recovery-execution.json').exists()
    if final:
        assert (PREP / 'preparation-recovery-failure.json').exists()
        assert not (PREP / 'preparation-final-execution.json').exists()
    from scripts.prospectus_shell_maturity import costs as prior_costs
    previous = prior_costs()
    assert previous['combined_measured_seconds'] + 870 < 1800
    assert previous['combined_bytes_conservative'] + 160 * 1024**2 < 512 * 1024**2
    if not recovery:
        save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_measured_seconds'],
            'prior_bytes': previous['combined_bytes_conservative'], 'prior_resources': previous,
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    try:
        events = Authority(ROOT).events(); bindings = {}
        folders = [AUTH / 'attempts/finance-conventions' / f'attempt-{i:03d}' for i in (1, 8, 9, 10, 11, 12)]
        folders.append(AUTH / 'attempts/entitlement/attempt-011')
        for folder in folders:
            recorded = [e for e in events if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
            assert recorded and sha(folder / 'outputs.json') == recorded[-1]['outputs_sha256']
            for name, checksum in read(folder / 'outputs.json').items():
                assert sha(folder / name) == checksum, name
                bindings[rel(folder / name)] = checksum
            bindings[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
        save(PREP / 'comparison-methods.json', method_equivalence())
        old_freeze = read(ORIGINAL / 'freeze.json')['bindings']
        for name, checksum in old_freeze.items():
            if not name.startswith('src/'):
                assert sha(ROOT / name) == checksum, name
                bindings[name] = checksum
        package = read(BASE / 'package.json')
        for name in ('fixed_maturity.py', 'fixed_term.py', 'fixed_phase.py', 'fixed_coupon.py'):
            path = 'prospectus/successor/' + name
            assert sha(ROOT / 'src/legalmath' / path) == package['files'][path]
            bindings['src/legalmath/' + path] = package['files'][path]
        save(PREP / 'source-bindings.json', bindings)
        save(PREP / 'config.json', {'package_python': package['python']})
        current = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
        delta = {name: {'before': checksum, 'current': current.get('src/legalmath/' + name)}
                 for name, checksum in package['files'].items() if current.get('src/legalmath/' + name) != checksum}
        save(PREP / 'consumer-method-delta.json', {'changed': delta,
            'new': sorted(n for n in current if str(Path(n).relative_to('src/legalmath')) not in package['files']),
            'fresh_consumers_required': True})
        save(PREP / ('preparation-final-execution.json' if final else
                     'preparation-recovery-execution.json' if recovery else 'preparation-execution.json'),
             {'status': 'PASS', 'wall_seconds': time.monotonic() - began})
    except Exception as error:
        save(PREP / ('preparation-final-failure.json' if final else
                     'preparation-recovery-failure.json' if recovery else 'preparation-failure.json'),
             {'status': 'FAIL', 'kind': type(error).__name__,
            'error': str(error), 'wall_seconds': time.monotonic() - began}); raise
    return {'status': 'PASS', 'resources': costs(), 'current_consumer_delta': len(delta)}


def proposal():
    """Create the reviewed revision; admission is performed by the authority."""
    program = read(AUTH / 'program.json')
    assert program['revision'] == 376 and not HERE.exists()
    new = deepcopy(program)
    new['revision'] = 377
    task = next(t for t in new['tasks'] if t['id'] == 'finance-conventions')
    task.update({
        'dossier': PLAN,
        'pre_admission_review': rel(PREP),
        'validator': VALIDATOR,
        'reason': 'Close the declared conditional fixed-rate finance acceptance with exact complete answer, source, package and adverse-control validation',
        'acceptance': 'Named conditional-fixed-finance.v1 validates complete current ordinary/installed answers and retained comparison evidence; the wider finance and legal obligations remain open.',
        'fixed_finance_acceptance': {
            'version': VALIDATOR,
            'scope': SCOPE,
            'review': rel(PREP),
            'whole_task_complete': False,
            'build_criteria_scope': [],
            'stage_dependencies': DEPS,
        },
    })
    # The input list is an immutable admission binding. Include the validator,
    # acceptance tests and runner before the revision is admitted.
    inputs = list(task['inputs'])
    for name in FILES + TESTS:
        if name not in inputs:
            inputs.append(name)
    for path in PREP.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            name = rel(path)
            if name not in inputs:
                inputs.append(name)
    task['inputs'] = sorted(inputs)
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 377
    route = next(r for r in routes['tasks'] if r['task'] == 'finance-conventions')
    route.update({'dossier': PLAN, 'task_sha256': adigest(task),
        'remaining': 'Finance012 supplied current consumer evidence is retained; named fixed-rate acceptance has not yet been independently validated.',
        'next_action': 'Admit finance013, execute tests/ordinary/package/installed, validate complete evidence, record and refresh; retain wider finance and legal gaps.',
        'stop_condition': 'No changed retry; 750 measured+120 conservative seconds and 160MiB new; cumulative 1800 seconds/512MiB.'})
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    review = {
        'baseline': adigest(program),
        'changes': ['Add one named validator for the original conditional fixed-rate acceptance',
                    'Add exact current consumer/package/source identity and refusal checks',
                    'Preserve all wider finance, legal applicability and build obligations'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'findings': ['The baseline is authenticated finance012, not a reduced fixture',
                         'Counts and runtime are explanatory; complete products and adverse controls are primary',
                         'False/zero, rehashed amounts, source loss, package drift and failed-stage PASS are explicit vetoes',
                         'QuantLib reuse is permitted only after method identity and complete retained records are checked']},
        'evidence_contract': {'question': 'Does the current source-bound fixed-rate route preserve complete answers and package identity while refusing changed premises?',
            'baseline': 'Authenticated finance012 ordinary/installed summaries and answers',
            'primary': 'Exact complete answer/P5 equality, independent integer/date recomputation, source and module origins, package identity, retained QuantLib evidence',
            'promotion_veto': ['Changed answer or P5', 'Missing/changed scenario', 'False-to-zero or rehashed wrong amount accepted', 'Missing source condition', 'Package or import drift', 'Failed-stage provisional PASS'],
            'continuation_veto': ['Invalid authority', 'Corrupt retained evidence', 'Cumulative bound exhausted'],
            'explanatory_only': ['Counts', 'Wall time', 'Storage'],
            'not_concluded': ['Actual ownership/payment', 'Unreviewed source applicability', 'Floating/callable/FX/tax/settlement', 'Whole finance task or general build']},
        'scope_unchanged': True,
        'budget_unchanged': True,
        'original_obligations_preserved': True,
    }
    save(PREP / 'proposal.json', new)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 377, 'resources': costs()}


def budget_extension():
    """Review the single additional admission required by the retained plan."""
    program = read(AUTH / 'program.json')
    assert program['revision'] == 377 and not HERE.exists()
    new = deepcopy(program)
    new['revision'] = 378
    old_limit = new['budgets']['finance-conventions']['maximum_new_attempts']
    assert old_limit == 12
    new['budgets']['finance-conventions']['maximum_new_attempts'] = 13
    task = next(t for t in new['tasks'] if t['id'] == 'finance-conventions')
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 378
    route = next(r for r in routes['tasks'] if r['task'] == 'finance-conventions')
    route['task_sha256'] = adigest(task)
    route['next_action'] = 'Admit the single reviewed finance013 acceptance attempt; retain all earlier attempts and cumulative bounds.'
    route['stop_condition'] = '13 admissions maximum; no unchanged retry; cumulative 1800 seconds/512MiB.'
    save(PREP / 'routes-378.json', routes)
    new['continuation_review'].update(routes=rel(PREP / 'routes-378.json'))
    review = {
        'baseline': adigest(program),
        'changes': ['Extend only the finance-conventions admission count from 12 to 13',
                    'Retain all twelve historical admissions, their costs and evidence',
                    'Use the already prepared named fixed-finance validator for the one remaining declared gap'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'findings': ['The extension does not reset time, storage, obligations or source bindings',
                         'The requested attempt is a distinct acceptance validator, not an unchanged retry',
                         'Cumulative resource ceilings remain the hard continuation vetoes']},
        'evidence_contract': {'question': 'Can the already reviewed fixed-rate acceptance be admitted once after the exhausted historical attempt budget?',
            'baseline': 'Revision377 and all twelve retained finance admissions',
            'primary': 'Finance013 exact validator result and complete evidence',
            'promotion_veto': ['Changed prior evidence', 'Unbound validator or inputs', 'Cumulative limit exceeded'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', '1800-second or 512MiB cumulative bound exhausted'],
            'explanatory_only': ['Admission count after extension', 'Runtime', 'Storage'],
            'not_concluded': ['Whole finance task', 'Whole build', 'Actual legal applicability']},
        'scope_unchanged': True,
        'budget_unchanged': False,
        'original_obligations_preserved': True,
        'budget_revision': {'budget_key': 'finance-conventions', 'previous_maximum': 12,
            'new_maximum': 13,
            'retained_attempts': [e['attempt'] for e in Authority(ROOT).events()
                                  if e['kind'] == 'ADMIT' and e['budget_key'] == 'finance-conventions'],
            'reason': 'Prepared finance013 is the reviewed finite acceptance needed to validate the declared fixed-rate task; historical admissions are exhausted and none is repeated',
            'next_discriminating_check': 'Exact current ordinary/installed products, source and package validator',
            'stop_condition': 'One additional admission only; cumulative 1800 seconds/512MiB; no unchanged retry',
            'same_scope_authorization': 'User requested recovery and continuation of the reviewed build'}
    }
    save(PREP / 'proposal-378.json', new)
    save(PREP / 'review-378.json', review)
    return {'status': 'PASS', 'revision': 378, 'previous_maximum': old_limit, 'new_maximum': 13}


def repair_proposal():
    program=read(AUTH/'program.json')
    assert program['revision']==378 and not HERE.exists()
    assert read(PREP/'development-review-execution.json')['exit_code']==0
    from scripts.prospectus_fixed_finance_verify import originals, quantlib_evidence
    originals(); quantlib_evidence()
    production={rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
    bindings={n:sha(ROOT/n) for n in FILES+TESTS+['pyproject.toml','scripts/prospectus_control.py',
              'scripts/prospectus_fixed_phase_package.py','scripts/prospectus_fixed_phase_oracle.py',
              'scripts/prospectus_adoption_sidecar.py']}
    bindings.update(production); bindings.update(read(PREP/'source-bindings.json'))
    for path in (AUTH/'reviews/shell-full-coupons-360/freeze.json',
                 AUTH/'attempts/finance-conventions/attempt-009/admission.json',
                 AUTH/'attempts/finance-conventions/attempt-010/admission.json'):
        value=read(path)
        old=value['binding'] if 'binding' in value else value['bindings']
        for name,checksum in old.items():
            if name.startswith(('docs/','.localresources/')):
                assert sha(ROOT/name)==checksum,name
                bindings[name]=checksum
        bindings[rel(path)]=sha(path)
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP/'freeze-379.json',{'bindings':bindings,'production':production})
    new=deepcopy(program); new['revision']=379
    task=next(t for t in new['tasks'] if t['id']=='finance-conventions')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'EXECUTION-REPAIR.md'),
        acceptance=read(AUTH/'revisions/0376.json')['tasks'][[t['id'] for t in program['tasks']].index('finance-conventions')]['acceptance'],
        reason='Validate current conditional fixed-rate evidence and expose remaining original applicability requirements without falsely accepting the whole task')
    task['fixed_finance_acceptance'].update(freeze=rel(PREP/'freeze-379.json'), conditional_only=True,
        bounds={'new_measured_seconds':750,'conservative_seconds':120,'cumulative_seconds':1800,
                'new_bytes':160*1024**2,'cumulative_bytes':512*1024**2,'consumer_seconds':180,'other_child_seconds':90,'validator_seconds':60},
        stage_dependencies=DEPS,completion_dependencies={'reconcile':list(CHECKS)})
    task['inputs']=sorted(set(task['inputs'])|set(bindings)|{rel(PREP/'freeze-379.json')})
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=379
    row=next(r for r in routes['tasks'] if r['task']=='finance-conventions')
    row.update(task_sha256=adigest(task),dossier=PLAN,
        remaining='Named current conditional evidence validation is prepared; original source applicability still open',
        next_action='Execute finance013 once; preserve source limits and original obligations; record partial evidence and inspect next original source work',
        stop_condition='13 admissions;750+120s/160MiB new;1800s/512MiB cumulative;no unchanged retry')
    save(PREP/'routes-379.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes-379.json'))
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (PLAN,rel(PREP/'routes-379.json'),rel(PREP/'freeze-379.json'))})
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':True,
        'changes':['Repair missing continuation bindings, stage self-dependency and completion semantics before admission',
                   'Fresh type-exact full legacy/Danske/Shell products; complete retained QuantLib comparison',
                   'Restore original acceptance wording; conditional validator returns partial disposition while applicability is unresolved',
                   'Retain revisions377/378, earlier developer failures and all cumulative costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'EXECUTION-REPAIR.md'),'tests':rel(PREP/'development-review-execution.json')},
        'evidence_contract':{'question':'Does current supported fixed finance preserve exact source-bound products and refuse false evidence?',
            'baseline':'Complete authenticated finance012,011 and010 answers and P5, actual QuantLib009/011',
            'primary':'Type-exact complete products and independent integer/date results, real package inputs/outputs, frozen source/package/origins',
            'promotion_veto':['Changed result','Missing scenario/control/source','Wrong import','Failed-stage PASS','Lost legal/conditional limit'],
            'continuation_veto':['Invalid authority','Corrupt shared evidence','Exhausted cumulative bound'],
            'explanatory_only':['Counts','Timing','Storage'],
            'not_concluded':['Original finance acceptance','Legal applicability','Actual ownership','Full settlement','Whole build']}}
    save(PREP/'proposal-379.json',new);save(PREP/'review-379.json',review)
    return {'status':'PASS','revision':379,'resources':costs()}


def frozen():
    admission=read(HERE/'admission.json')
    assert adigest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,checksum in read(PREP/'freeze-379.json')['bindings'].items():assert sha(ROOT/name)==checksum,name


def command(name, argv, timeout, folder=HERE):
    target=folder/'commands';target.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();result=None;failure=None
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1',
         'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    try:
        with (target/(name+'.log')).open('x') as stream:
            result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        if result.returncode:raise RuntimeError('Inspect retained '+rel(target/(name+'.log')))
    except Exception as exc:
        failure={'kind':type(exc).__name__,'reason':str(exc)};raise
    finally:
        save(target/(name+'.json'),{'command':argv,'cwd':str(ROOT),'timeout_seconds':timeout,
            'wall_seconds':time.monotonic()-start,'exit_code':result.returncode if result is not None else None,'failure':failure})


def development(label):
    # Every changed diagnostic gets a new record; no preparation rerun.
    start=time.monotonic();code=1
    try:
        command(label,[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',
            'tests/prospectus/test_fixed_finance_acceptance.py','tests/prospectus/test_execution_acceptance.py',
            '--junitxml='+str(PREP/(label+'.xml'))],90,PREP)
        code=0
    finally:save(PREP/(label+'-execution.json'),{'exit_code':code,'wall_seconds':time.monotonic()-start})
    return {'status':'PASS','resources':costs()}


def tests():
    command('tests',[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],90)
    from legalmath.prospectus.execution_acceptance import checked_tests
    return {'status':'PASS','tests':checked_tests(HERE/'tests.xml',1)}


def ordinary():
    command('ordinary',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/'scripts/prospectus_fixed_finance_worker.py'),
            str(ROOT),str(HERE),'ordinary'],180)
    return {'status':'PASS','cases':len(read(HERE/'ordinary-summary.json')['cases'])}


def package():
    source=HERE/'package-source';source.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    python=read(PREP/'config.json')['package_python']
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
                     '--wheel-dir',str(HERE/'wheel'),str(source)],90)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    expected={str(Path(n).relative_to('src/legalmath')):h for n,h in read(PREP/'freeze-379.json')['production'].items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
                       '--target',str(HERE/'installed'),str(wheels[0])],90)
    installed=HERE/'installed/legalmath'
    assert {str(p.relative_to(installed)):sha(p) for p in installed.rglob('*') if p.is_file()}==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','source_matched_files':len(expected)}


def installed():
    command('installed',[read(HERE/'package.json')['python'],'-I','-B',
            str(ROOT/'scripts/prospectus_fixed_finance_worker.py'),str(ROOT),str(HERE),'installed'],180)
    return {'status':'PASS','cases':len(read(HERE/'installed-summary.json')['cases'])}


def verify():
    command('verify',[str(ROOT/'.venv/bin/python'),'-B','-m','scripts.prospectus_fixed_finance_verify',str(HERE)],60)
    value=read(HERE/'verification.json')
    return {'status':'PASS','maturity_cases':value['maturity_cases'],'legacy_cases':value['legacy_cases'],'current_Danske_cases':3}


def status():
    result={}
    for name,deps in DEPS.items():
        folder=HERE/'stages'/name
        if (folder/'failure.json').exists():result[name]='FAIL'
        elif (folder/'result.json').exists():result[name]=read(folder/'result.json')['status']
        elif (folder/'started.json').exists():result[name]='INTERRUPTED_OR_RUNNING'
        elif any(result.get(d) in ('FAIL','BLOCKED') for d in deps):result[name]='BLOCKED'
        else:result[name]='PENDING'
    ready=[name for name,deps in DEPS.items() if result[name]=='PENDING' and all(result[d]=='PASS' for d in deps)]
    if not all(result[s] in ('PASS','FAIL','BLOCKED') for s in CHECKS):
        ready=[s for s in ready if s not in ('reconcile','seal')]
    return {'stages':result,'ready':ready,'whole_build_complete':False}


def reconcile():
    outcomes={s:status()['stages'][s] for s in CHECKS}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'original-requirements.json',{'candidate_passed':passed,'checks':outcomes,'original_task_complete':False,
        'original_obligations':['G14','G15','E03','RESIDUAL-04','PACKAGE-03'],
        'remaining':['Source applicability/UNKNOWN assembly roles','Actual instrument facts deferred until after build',
                     'Unsupported floating/call/FX/tax/full settlement','Separate exact-quantity build criterion'],
        'external_adviser_opinion_required':False})
    text=f"""# Current conditional fixed-finance evidence

The current conditional candidate {'passed' if passed else 'failed'} its required checks:
{outcomes}. Complete results, executed commands and any failure records are
retained beside this note. Original finance evidence001–012 and entitlement011
remain unchanged.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| {'Retain conditional evidence' if passed else 'Retain failed candidate diagnosis'} | Exact complete products and independent integer/date checks: {passed} | See individual recorded stages | Source applicability retains UNKNOWN roles; actual facts remain hypothetical | Record, refresh, inspect source-interpretation frontier | Whole finance task or build |
| Keep original requirements open | G14/G15/E03/RESIDUAL-04/PACKAGE-03 unchanged | Conditional numeric agreement cannot establish legal applicability | Source translation and actual instrument facts | Resolve original source roles with evidence before acceptance | External opinion or package arithmetic as legal proof |

The current trial uses eleven Shell maturity cases, six complete legacy coupon
cases and three Danske fixed-phase cases in each successful runtime. Exact JSON
comparison distinguishes booleans and numbers, and validates complete P5 and
answers. QuantLib1.38 evidence is reused from actual009 and011 input/output
records after numerical method identity is checked; no new QuantLib run is
claimed. This package supplies conditional evidence and deliberately does not
accept the whole original finance task.

Post-run red-team: both implementations could share a mistaken source reading.
The arithmetic comparison therefore preserves supplied-profile applicability
and cannot establish operative source roles, real ownership or payment. A
contrary source, lost qualifier, changed method or in-domain arithmetic
counterexample would overturn the corresponding application. These are the
weakest evidence boundaries. Counts and runtime are explanatory.

Pre-admission failures were local implementation/usage mistakes: a shared
editable interpreter resolved main-worktree imports; the initial registry
mishandled the assisted stream and non-string names; the initial draft had
incorrect package schemas and stage dependencies. Revisions377/378 were retained
and repaired in379 before any finance013 consumer execution. They establish no
fundamental package defect. Conditional evidence remains separate from legal
and actual-fact acceptance.
"""
    with (HERE/'RESULT.md').open('x') as stream:stream.write(text)
    return {'status':'PASS','candidate_passed':passed}


def seal():
    outcome=status()['stages']; passed=all(outcome[s]=='PASS' for s in CHECKS)
    result={'status':'PASS' if passed else 'FAIL','task':'finance-conventions','scope':SCOPE,
        'whole_task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],
        'classification':'CURRENT_CONDITIONAL_FIXED_RATE_EVIDENCE','checks':{s:outcome[s] for s in CHECKS},'resources':costs()}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PREP/'source-bindings.json'),
        'plan':PLAN,'result':rel(HERE/'RESULT.md'),'resources':costs()})
    return {'status':'PASS','candidate_status':result['status'],'resources':costs()}


def stage(name):
    assert name in status()['ready'],'Stage not ready; inspect retained state'
    frozen();costs();start=time.monotonic()
    folder=HERE/'stages'/name
    save(folder/'started.json',{'command':sys.argv,'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat()})
    try:
        result=globals()[name]();frozen();costs(time.monotonic()-start)
        save(folder/'result.json',{**result,'wall_seconds':time.monotonic()-start})
    except Exception as exc:
        save(folder/'failure.json',{'status':'FAIL','type':type(exc).__name__,'reason':str(exc),'wall_seconds':time.monotonic()-start})
        raise
    if name=='seal':
        save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                                 if p.is_file() and '__pycache__' not in p.parts})
    return {'result':result,'frontier':status()}


if __name__=='__main__':
    action=sys.argv[1]
    if action=='status':result=status()
    elif action.startswith('development-'):result=development(action)
    elif action=='repair-proposal':result=repair_proposal()
    elif action in DEPS:result=stage(action)
    else:raise SystemExit('Use retained preparation; unsupported action '+action)
    print(json.dumps(result))
