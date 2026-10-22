"""Type-exact current fixed-finance evidence, with no general legal acceptance."""
from datetime import date
from fractions import Fraction
import json
import math
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from scripts.prospectus_default_holder import ROOT, AUTH, read, sha, rel, digest, Authority
from scripts import prospectus_shell_maturity_checks as checks

PREP = AUTH / 'reviews/fixed-finance-377'
BASE = AUTH / 'attempts/finance-conventions/attempt-012'
LEGACY = AUTH / 'attempts/finance-conventions/attempt-011'
QUANTLIB = AUTH / 'attempts/finance-conventions/attempt-009'
ORIGINAL = AUTH / 'reviews/shell-maturity-361'
OLD = AUTH / 'reviews/shell-full-coupons-360'
SCOPE = 'SOURCE_BOUND_CONDITIONAL_FIXED_RATE_ONLY'
CASES = tuple(f'{form}-{kind}' for form in ('global','definitive')
              for kind in ('plain','maturity-holiday','coupon-only','principal-only','excluded')) + ('definitive-two-recipients',)
LEGACY_CASES = tuple(f'{form}-{kind}' for form in ('global','definitive') for kind in ('plain','holiday','excluded'))
REQUIRED_TESTS = {'test_rehashed_corruption_refused', 'test_p5_mutation_refused',
                 'test_missing_case_or_control_refused', 'test_failed_stage_cannot_be_pass',
                 'test_missing_source_refused', 'test_package_drift_refused',
                 'test_fixed_finance_validator_is_bound_to_the_assisted_task',
                 'test_reconcile_waits_for_completion_and_failure_blocks_dependents'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def same(actual, expected, label):
    require(encoded(actual) == encoded(expected), 'Exact JSON mismatch: ' + label)


def _exact_product(path):
    value = read(path)
    require(isinstance(value, dict) and value.get('report_sha256') ==
            digest({k:v for k,v in value.items() if k != 'report_sha256'}), 'answer report digest is invalid')
    return value


def verify_files(root, bindings):
    root = Path(root).resolve()
    require(isinstance(bindings, dict) and bool(bindings), 'Missing file bindings')
    for name, checksum in bindings.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and path.is_file() and sha(path) == checksum,
                'Missing or changed bound file: ' + name)


def originals():
    events = Authority(ROOT).events()
    folders = [AUTH / 'attempts/finance-conventions' / f'attempt-{i:03d}' for i in (1,8,9,10,11,12)]
    folders.append(AUTH / 'attempts/entitlement/attempt-011')
    for folder in folders:
        recorded = [e for e in events if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
        require(bool(recorded) and sha(folder / 'outputs.json') == recorded[-1]['outputs_sha256'],
                'Original evidence manifest differs from authority: ' + rel(folder))
        verify_files(folder, read(folder / 'outputs.json'))
    verify_files(ROOT, read(PREP / 'source-bindings.json'))
    from scripts.prospectus_fixed_finance_acceptance import method_equivalence
    method = method_equivalence()
    same(method, read(PREP / 'comparison-methods.json'), 'current numerical method proof')
    same(list(CASES), read(ORIGINAL / 'cases.json'), 'original eleven-case denominator')
    same(list(LEGACY_CASES), read(OLD / 'cases.json'), 'original six legacy cases')
    return method


def check_answer(answer, packet, baseline):
    """Recompute independent integer/date result, then compare every field."""
    oracle = checks.expected(packet)
    same(packet['expected'], oracle, 'packet integer/date expectations')
    checks.validate(answer, {**packet, 'expected': oracle})
    value = answer['questions']['Q5']['value']
    same(value['cash_flows'], oracle['cash_flows'], 'all dated cash flows')
    same(value['totals'], oracle['totals'], 'all recipient totals')
    same(value['calculation_inputs'], packet['request']['contract_calculation'], 'all retained input premises')
    same(value['coupons'], packet['baseline_answer']['questions']['Q5']['value'], 'complete nested coupon result')
    require(value['full_settlement_supported'] is False and value['legal_entitlement_established'] is False
            and answer['may_execute_transaction'] is False and answer['independent_legal_acceptance'] is False,
            'False legal/settlement/transaction claim')
    require(value['redemption']['source_applicability'] == 'CONDITIONAL_ON_SUPPLIED_PROFILE'
            and value['redemption']['source_applicability_established'] is False, 'Lost source applicability limit')
    same(answer, baseline, 'entire authenticated original answer')
    return {'cash_flows':len(oracle['cash_flows']), 'answer_sha256':digest(answer)}


def check_p5(p5, baseline, answer):
    same(p5, baseline, 'entire authenticated original P5')
    require(p5['sha256'] == digest({k:v for k,v in p5.items() if k != 'sha256'})
            and answer['consumed_products']['P5'] == p5['sha256'], 'P5/report binding differs')


def summary_check(summary, mode):
    baseline = read(BASE / (mode + '-summary.json'))
    same({k:v for k,v in summary.items() if k != 'import_count'},
         {k:v for k,v in baseline.items() if k != 'import_count'}, 'complete original ' + mode + ' summary')
    same([r['id'] for r in summary['cases']], list(CASES), 'scenario denominator')
    require(sum(len(r['input_refusals']) for r in summary['cases']) == 506 and
            sum(len(r['corrupt_answer_refusals']) for r in summary['cases']) == 66, 'Control denominator incomplete')


def checked_stages(attempt, names, exact=False):
    stages = Path(attempt) / 'stages'
    if exact:
        require({p.parent.name for p in stages.glob('*/started.json')} == set(names)
                == {p.parent.name for p in stages.glob('*/result.json')}, 'Missing or extra completed stage')
    for name in names:
        folder = stages / name
        require((folder / 'started.json').is_file() and (folder / 'result.json').is_file(), 'Missing stage: ' + name)
        require(not (folder / 'failure.json').exists() and read(folder / 'result.json').get('status') == 'PASS',
                'Failed stage cannot be PASS: ' + name)


def _check_package(attempt, production=None):
    attempt = Path(attempt)
    if production is None:
        production = {str(Path(n).relative_to('src/legalmath')): h
                      for n,h in read(PREP / 'freeze-379.json')['production'].items()}
    package = read(attempt / 'package.json')
    same(package['files'], production, 'package against frozen production')
    wheels = list((attempt / 'wheel').glob('*.whl'))
    require(len(wheels) == 1 and sha(wheels[0]) == package['wheel_sha256'], 'Wheel identity changed')
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist()
                  if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual, production, 'complete wheel file set')
    installed = attempt / 'installed/legalmath'
    same({str(p.relative_to(installed)):sha(p) for p in installed.rglob('*') if p.is_file()},
         production, 'complete installed file set')
    origins = {}
    for mode in ('ordinary','installed'):
        imports = read(attempt / (mode + '-imports.json'))
        require(bool(imports) and 'legalmath.prospectus.successor.service' in imports, 'Missing real consumer origins')
        package_root = (ROOT / 'src/legalmath' if mode == 'ordinary' else installed).resolve()
        for module, location in imports.items():
            path = Path(location).resolve()
            require(path.is_relative_to(package_root), 'Wrong module origin: ' + module)
            key = str(path.relative_to(package_root))
            require(key in production and sha(path) == production[key], 'Imported module bytes changed: ' + module)
        require(type(read(attempt/(mode+'-summary.json'))['import_count']) is int
                and len(imports) == read(attempt/(mode+'-summary.json'))['import_count'], 'Incomplete origin accounting')
        origins[mode] = len(imports)
    return {'source_files':len(production), 'wheel_sha256':sha(wheels[0]), 'module_origins':origins}


def quantlib_evidence():
    """Inspect real retained package inputs/outputs, not only PASS labels."""
    from scripts import prospectus_fixed_phase_package as package
    from scripts import prospectus_fixed_phase_oracle as oracle
    comparisons = {}
    for name in ('selected','holiday'):
        data = read(package.PREP / (name + '-package-input.json'))
        same(data, package.package_input(name, package.requests()[name]), 'QuantLib independently selected inputs')
        result = read(QUANTLIB / 'package' / name / 'result.json')
        same(result['input'], data, 'complete QuantLib echoed input')
        require(read(QUANTLIB / 'package' / name / 'exit.json')['returncode'] == 0, 'QuantLib did not execute')
        comparisons[name] = package.check_package(result, data, name == 'holiday')
    adverse = []
    for name, bad in package.bad_inputs(read(package.PREP / 'selected-package-input.json')):
        folder = QUANTLIB / 'package-adverse' / name
        same(read(folder / 'input.json'), bad, 'QuantLib adverse input ' + name)
        result = read(folder / 'result.json')
        require(read(folder / 'exit.json')['returncode'] == 1 and result['execution'] == 'FAILED'
                and 'ValueError' in result['traceback'], 'Missing actual QuantLib refusal')
        adverse.append({'name':name, 'error':result['error']})
    same(read(QUANTLIB/'package-comparison.json'), {'valid':comparisons,'input_refusals':adverse,
        'legal_scope':{k:False for k in package.SCOPE_FLAGS}}, 'complete matched QuantLib comparison')
    rows = read(QUANTLIB/'consumer-comparison.json')['cases']
    same([r['name'] for r in rows], ['selected','holiday','excluded'], 'three prior Danske consumers')
    for row in rows:
        for binding in [row['answer'], *row['products'].values()]:
            path = ROOT / binding['path']
            require(sha(path) == binding['sha256'] and digest(read(path)) == binding['semantic_sha256'], 'Changed original package consumer')
        answer = read(ROOT / row['answer']['path'])
        same(row['independent_integer_proof'], oracle.check_value(answer['questions']['Q5']['value'],
            holiday=row['name']=='holiday', excluded=row['name']=='excluded'), 'original integer source proof')
    source = oracle.source_check(AUTH/'attempts/finance-conventions/attempt-003')
    data = read(OLD/'package-input.json')
    require(data['calendar_dates'] == [] and len(data['cases']) == 10, 'Shell fraction input coverage')
    fractions = []
    for i, row in enumerate(data['cases']):
        left = '2020-09-10' if i == 0 else f'{2020+i}-12-10'
        right = f'{2021+i}-12-10'
        refs = [{'start':'2019-12-10','end':'2020-12-10'}, {'start':'2020-12-10','end':'2021-12-10'}] if i == 0 else [{'start':left,'end':right}]
        same(row, {'convention':'ACT_ACT_ICMA','end':right,'eom':False,'frequency':1,
            'id':str(i),'references':refs,'start':left}, 'explicit source reference periods')
        total = Fraction()
        for ref in refs:
            lo=max(date.fromisoformat(left),date.fromisoformat(ref['start']))
            hi=min(date.fromisoformat(right),date.fromisoformat(ref['end']))
            total += Fraction(max(0,(hi-lo).days),(date.fromisoformat(ref['end'])-date.fromisoformat(ref['start'])).days)
        fractions.append(total)
    output = read(LEGACY/'quantlib/result.json')
    require(output['version']=='1.38' and output['execution']=='EXECUTED'
        and output['evaluation_date_used'] is False and output['missing_reference_fallback_used'] is False
        and output['calendar']==[], 'Shell QuantLib scope changed')
    require(read(LEGACY/'commands/quantlib.json')['returncode']==0, 'Shell package command failed')
    same([r['id'] for r in output['fractions']], [str(i) for i in range(10)], 'ten QuantLib fractions')
    for row, expected in zip(output['fractions'],fractions):
        require(type(row['year_fraction']) in (float,int) and math.isfinite(row['year_fraction'])
            and abs(row['year_fraction']-float(expected))<1e-12, 'Wrong retained QuantLib fraction')
    return {'matched_Danske_cases':comparisons, 'actual_adverse_inputs':len(adverse),
        'Shell_fractions':[str(v) for v in fractions], 'source_reading':source,
        'execution':'RETAINED_ACTUAL_EXECUTION_WITH_CURRENT_NUMERICAL_METHOD_IDENTITY', 'new_QuantLib_call':False}


def verify(root, attempt, task=None, final=False):
    require(Path(root).resolve()==ROOT.resolve(), 'Wrong acceptance root')
    attempt=Path(attempt).resolve()
    require(attempt.is_relative_to(AUTH/'attempts/finance-conventions'), 'Wrong finance attempt')
    names=('tests','ordinary','package','installed')
    checked_stages(attempt, names+('verify','reconcile','seal') if final else names, exact=final)
    freeze=read(PREP/'freeze-379.json')
    verify_files(ROOT,freeze['bindings'])
    methods=originals()
    suites=list(ET.parse(attempt/'tests.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    require(counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped')), 'Failed or missing tests')
    names={r.get('name','').split('[')[0] for r in ET.parse(attempt/'tests.xml').getroot().iter('testcase')}
    require(REQUIRED_TESTS <= names, 'Required acceptance refusal tests missing')
    identities={}
    for mode in ('ordinary','installed'):
        summary_check(read(attempt/(mode+'-summary.json')),mode)
        identities[mode]={}
        for case in CASES:
            packet=read(ORIGINAL/(case+'-packet.json.gz'))
            answer=_exact_product(attempt/mode/(case+'-answer.json.gz'))
            detail=check_answer(answer,packet,read(BASE/'ordinary'/(case+'-answer.json.gz')))
            p5=read(attempt/mode/(case+'-P5.json.gz'))
            check_p5(p5,read(BASE/'ordinary'/(case+'-P5.json.gz')),answer)
            identities[mode][case]={**detail,'P5_sha256':digest(p5)}
        for case in LEGACY_CASES:
            for kind in ('answer','P5'):
                same(read(attempt/'legacy'/mode/(case+'-'+kind+'.json.gz')),
                     read(LEGACY/'ordinary'/(case+'-'+kind+'.json.gz')), 'complete legacy '+mode+'/'+case+'/'+kind)
        from scripts.prospectus_fixed_phase_oracle import check_value
        for case in ('selected','holiday','excluded'):
            for kind in ('answer','P5'):
                current=read(attempt/'danske'/mode/(case+'-'+kind+'.json.gz'))
                same(current,read(AUTH/'attempts/finance-conventions/attempt-010/ordinary'/('danske-'+case+'-'+kind+'.json.gz')),
                     'current complete Danske '+mode+'/'+case+'/'+kind)
                if kind=='answer':check_value(current['questions']['Q5']['value'],holiday=case=='holiday',excluded=case=='excluded')
        command=read(attempt/'commands'/(mode+'.json'))
        require(command['exit_code']==0 and command['failure'] is None, 'Failed consumer command')
    same(identities['ordinary'],identities['installed'],'complete current runtime equality')
    return {'version':'conditional-fixed-finance.v1','status':'PASS','scope':SCOPE,
        'maturity_cases':len(CASES),'legacy_cases':len(LEGACY_CASES),'current_Danske_cases':3,
        'input_refusals_per_runtime':506,'corrupt_answer_refusals_per_runtime':66,
        'identities':identities,'package':_check_package(attempt),'tests':counts,
        'numerical_methods':methods,'QuantLib':quantlib_evidence(),
        'source_applicability_established':False,'actual_entitlement_established':False,
        'full_settlement_supported':False,'whole_program_complete':False}


def validate_submission(root, attempt, task):
    require(task.get('id')=='finance-conventions' and task.get('validator')=='conditional-fixed-finance.v1', 'Wrong finance task')
    expected=verify(root,attempt,task,final=True)
    same(read(Path(attempt)/'verification.json'),expected,'recorded complete verification')
    result=read(Path(attempt)/'result.json')
    require(result['status']=='PASS' and result['scope']==SCOPE and result['whole_task_complete'] is False
            and result['whole_program_complete'] is False and result['build_criteria_claimed']==[], 'Invalid finance result scope')
    # The original task includes unresolved source applicability. Conditional
    # evidence cannot manufacture acceptance of that whole task.
    return False


if __name__=='__main__':
    import sys
    from scripts.prospectus_default_holder import save
    target=Path(sys.argv[1])
    result=verify(ROOT,target)
    save(target/'verification.json',result)
    print(json.dumps({'status':result['status'],'maturity_cases':result['maturity_cases'],'legacy_cases':result['legacy_cases'],'current_Danske_cases':3}))
