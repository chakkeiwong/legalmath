"""Bounded, matched QuantLib comparison of the original conditional fixed phase."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone, date
from fractions import Fraction
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, digest as authority_digest
from legalmath.prospectus.successor.contracts import digest
from scripts import prospectus_fixed_phase_oracle as oracle

AUTH = ROOT / REL
PREP = AUTH / 'reviews/fixed-phase-package-259'
HERE = AUTH / 'attempts/finance-conventions/attempt-009'
PRIOR = AUTH / 'attempts/finance-conventions/attempt-008'
OLD = AUTH / 'attempts/finance-conventions/attempt-003'
INPUTS = AUTH / 'reviews/fixed-phase-256'
PLAN = 'docs/plans/prospectus-fixed-phase-package-2026-10-18.md'
ROUTES = REL + '/closure-routes-2026-10-18-fixed-phase-package-259.json'
PROPOSAL = AUTH / 'proposals/fixed-phase-package-259.json'
REVIEW = AUTH / 'proposals/fixed-phase-package-259-review.json'
SIDECAR = ROOT / 'scripts/prospectus_adoption_sidecar.py'
PYTHON = '/tmp/prospectus-adoption-tools/bin/python'
BOUNDS = dict(new_seconds=300, stage_seconds=90, new_bytes=48*1024**2,
              reserve_bytes=1024**2, source_retrievals=4,
              new_installs_native_OCR_model_GPU_subagents_messages=0)
DOWNLOADS = [
    ('time/schedule.cpp', 0.605638709),
    ('cashflows/fixedratecoupon.cpp', 0.494719112),
    ('time/calendar.cpp', 0.511675797),
    ('time/calendars/bespokecalendar.cpp', 0.466226441),
]
STAGES = {'prepare': (), 'api_repair': (), 'freeze': ('api_repair',), 'propose': ('freeze',),
          'package': ('propose',), 'consumers': ('package',),
          'verify': ('consumers',), 'seal': ('verify',)}
PREPARATION = {'prepare', 'api_repair', 'freeze', 'propose'}
SCOPE_FLAGS = ('legal_entitlement_evaluated', 'holder_aggregation_evaluated',
               'event_precedence_evaluated', 'legal_rounding_evaluated',
               'actual_VP_calendar_established', 'redemption_inferred', 'evaluation_date_used')


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def encoded(value, pretty=False):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2 if pretty else None,
                       separators=None if pretty else (',', ':')) + '\n').encode()


def save(path, value, pretty=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value, pretty))


def text_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(value)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def identity(path):
    return {'path': rel(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def costs(enforce=True):
    elapsed = sum(seconds for _, seconds in DOWNLOADS)
    elapsed += sum(read(p)['wall_seconds'] for base in (PREP, HERE)
                   for p in base.glob('stages/*/result.json'))
    size = sum(p.stat().st_size for base in (PREP, HERE) for p in base.rglob('*') if p.is_file())
    for path in (Path(__file__), SIDECAR, ROOT / PLAN, PROPOSAL, REVIEW,
                 AUTH / 'revisions/0259.json', ROOT / ROUTES):
        if path.is_file():
            size += path.stat().st_size
    if read(AUTH / 'program.json')['revision'] >= 259:
        size += (AUTH / 'program.json').stat().st_size
    if enforce:
        assert elapsed < BOUNDS['new_seconds'], 'Reviewed total execution time exhausted'
        assert size + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Reviewed storage reserve exhausted'
    return {'new_measured_seconds': elapsed, 'new_bytes': size, 'earlier_timing': 'UNKNOWN'}


def methods():
    return sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py')) + [
        Path(__file__), SIDECAR, ROOT / PLAN,
        ROOT / 'scripts/prospectus_fixed_phase_oracle.py', ROOT / 'scripts/prospectus_control.py']


def original_integrity():
    events = Authority(ROOT).events()
    for folder in (PRIOR, OLD):
        admissions = [e for e in events if e['kind'] == 'ADMIT' and e['attempt'] == rel(folder)]
        assert len(admissions) == 1 and sha(folder / 'admission.json') == admissions[0]['admission_sha256']
        recorded = [e for e in events if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
        assert recorded and sha(folder / 'outputs.json') == recorded[-1]['outputs_sha256']
        for name, expected in read(folder / 'outputs.json').items():
            assert sha(folder / name) == expected, 'Sealed original output drift: ' + name
    admission = read(PRIOR / 'admission.json')
    request_path = INPUTS / 'phase-request.json'
    assert sha(request_path) == admission['binding'][rel(request_path)], 'Original request drift'
    for name, expected in read(OLD / 'source-bindings.json').items():
        assert sha(ROOT / name) == expected, 'Original source drift: ' + name
    oracle.source_check(OLD)


def requests():
    return {'selected': read(INPUTS / 'phase-request.json'),
            'holiday': read(PRIOR / 'holiday-request.json.gz'),
            'excluded': read(PRIOR / 'excluded-request.json.gz')}


def package_input(name, request):
    terms = {k: v['value'] for k, v in request['term_interpretations']['terms'].items()}
    premises = request['contract_calculation']['premises']
    holding, = premises['holdings']
    assert holding['entitled'] is True, 'Entitlement preprocessing is not a package comparison'
    assert terms['fixed_phase_boundary'] == 'FIRST_RESET_DATE'
    assert terms['coupon_anchor'] == terms['accrual_end'] == terms['due_date']
    assert terms['stub'] == 'SHORT_FIRST'
    source = INPUTS / 'phase-request.json' if name == 'selected' else PRIOR / (name + '-request.json.gz')
    return {'version': 'quantlib-fixed-phase.v1', 'request_sha256': sha(source),
        **{k: terms[k] for k in ('currency', 'annual_rate', 'accrual_start', 'fixed_phase_end',
                                'frequency', 'eom', 'day_count', 'adjustment')},
        'principal': holding['principal'], 'first_coupon': terms['coupon_anchor'],
        'calendar': deepcopy(premises['calendar']), 'termination_role': 'FIXED_PHASE_RESET_BOUNDARY',
        'premise_kind': premises['premise_kind']}


def command(argv, folder, timeout=30):
    folder.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    save(folder / 'command.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout,
                                 'environment_overrides': {k: env[k] for k in
                                  ('CUDA_VISIBLE_DEVICES', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPATH',
                                   'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')}})
    started = time.monotonic()
    with (folder / 'stdout.txt').open('xb') as stream:
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    save(folder / 'exit.json', {'returncode': result.returncode,
                              'wall_seconds': time.monotonic()-started})
    return result.returncode


def prepare():
    original_integrity()
    rows = []
    for suffix, seconds in DOWNLOADS:
        url = 'https://raw.githubusercontent.com/lballabio/QuantLib/v1.38/ql/' + suffix
        target = PREP / 'official' / Path(suffix).name
        assert target.is_file() and target.stat().st_size > 500
        rows.append({**identity(target), 'url': url, 'actual_argv': ['curl', '--fail', '--location',
            '--max-time', '20', '--silent', '--show-error', '--output', rel(target), url],
            'wall_seconds': seconds, 'returncode': 0,
            'receipt_basis': 'Actual successful calls recovered from preceding session summary; no new retrieval'})
    save(PREP / 'official-source-commands.json', rows)
    text_file(PREP / 'SOURCE-AUDIT.md', '''# Official QuantLib1.38 method inspection

The retained source is the upstream v1.38 tag. schedule.cpp94–135 requires the
explicit effective/first dates; the evaluation-date fallback at103 applies only
to a missing effective date with backward generation. Forward generation at
268–342 starts from the explicit first date and records irregular-first and
regular subsequent intervals. NullCalendar and Unadjusted keep accrual endpoints.

fixedratecoupon.cpp62–65 computes nominal times the compound factor minus one
on accrualStartDate_/accrualEndDate_. FixedRateLeg174–257 separately adjusts each
payment from the period end using paymentCalendar_ and paymentLag_; the binding
must accept explicit Simple compounding and zero lag. No interest is added on a
FOLLOWING payment delay. calendar.cpp84–104 advances through holidays; its
advance implementation with zero days delegates to adjust. BespokeCalendar45–58
creates a fresh implementation; explicit weekends and addHoliday avoid market
calendar substitution. The comparator checks adjusted dates remain in coverage.

The already retained quantlib-v1.38-thirty360.cpp45–46 maps BondBasis to ISMA_Impl;
72–82 implements the same two31-day endpoint adjustments as Base71(v). The
separate integer oracle encodes the source numerator, rather than importing the
engine or package. The calendar, principal, entitlement and rounding premises
are hypothetical. No package API inspected here establishes legal entitlement,
holder aggregation, event precedence, actual VP calendar or legal rounding.

The adapter's finite domain is annual non-EOM anchors on days1–28, a genuinely
short first interval, aligned end anchor, bounded rational inputs and covered
Sat/Sun calendar. This trial asserts only the original six source-bound coupons.
The first reset is a phase boundary. No bond/redemption/maturity object is used.
''')
    sources = read(OLD / 'source-bindings.json')
    originals = [INPUTS / 'phase-request.json', INPUTS / 'hypotheses.txt',
                 PRIOR / 'admission.json', PRIOR / 'outputs.json', OLD / 'admission.json',
                 OLD / 'outputs.json', OLD / 'source-bindings.json',
                 OLD / 'quantlib-v1.38-thirty360.cpp']
    for name in requests():
        originals += [PRIOR / (name + '-answer.json.gz')]
        originals += [PRIOR / (name + '-' + p + '.json.gz') for p in ('P1', 'P2', 'P3', 'P4', 'P5')]
        if name != 'selected':
            originals += [PRIOR / (name + '-request.json.gz')]
    save(PREP / 'original-inputs.json', {rel(p): sha(p) for p in originals} | sources)
    for name, request in requests().items():
        if name != 'excluded':
            save(PREP / (name + '-package-input.json'), package_input(name, request))
    probe = '''import os, json, sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import QuantLib as ql
doc = ql.FixedRateLeg.__doc__
print(json.dumps({'version':ql.__version__, 'module':ql.__file__,
 'interpreter':sys.executable, 'fixed_rate_leg_signature':doc,
 'schedule_signature':ql.Schedule.__init__.__doc__,
 'as_coupon_signature':ql.as_coupon.__doc__, 'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}))
assert ql.__version__ == '1.38'
for name in ('paymentCalendar', 'paymentLag', 'compounding', 'notionals', 'couponRates'):
    assert name in doc, name
'''
    text_file(PREP / 'api-probe.py', probe)
    assert command([PYTHON, '-B', str(PREP / 'api-probe.py')], PREP / 'api-probe') == 0, 'API probe failed; retain before repair'
    probe_result = read(PREP / 'api-probe/stdout.txt')
    save(PREP / 'api.json', probe_result)
    gap = read(ROOT / 'docs/implementation/prospectus-integration-closure/gap-status.json')
    save(PREP / 'requirement.json', {'original_G15': 'Declared fixed-rate schedule, stub, calendar, entitlement, aggregation, event-order and rounding cases match independent calculations and QuantLib on identical premises.',
        'gap_status_sha256': digest(gap), 'covered_here': ['Schedule', 'Stub flags', 'Hypothetical payment adjustment', 'Day fractions', 'Unrounded amounts'],
        'not_package_capabilities': ['Entitlement', 'Legal-holder aggregation', 'Event precedence', 'Legal rounding'],
        '003': 'Eleven endpoint inputs; no calendar rows', '008': 'Actual six-period consumer and independent integer check; no matched full QuantLib schedule/leg',
        'original_obligations_preserved': ['G14', 'G15', 'E03', 'RESIDUAL-04', 'PACKAGE-03']})
    return {'originals_verified': len(originals), 'official_files': len(rows), 'version': probe_result['version']}


def frozen():
    freeze_data = read(PREP / 'freeze.json')
    assert set(freeze_data['methods']) == {rel(p) for p in methods()}
    for name, expected in freeze_data['methods'].items():
        assert sha(ROOT / name) == expected, 'Frozen method drift: ' + name
    for name, expected in freeze_data['inputs'].items():
        assert sha(ROOT / name) == expected, 'Frozen input drift: ' + name
    return freeze_data


def api_repair():
    failure = read(PREP / 'stages/prepare/result.json')
    assert failure['status'] == 'FAIL' and 'API probe failed' in failure['error']
    original = (PREP / 'api-probe/stdout.txt').read_text()
    observed = json.loads(original.splitlines()[0])
    assert 'AssertionError: notionals' in original
    assert 'DoubleVector nominals' in observed['fixed_rate_leg_signature']
    assert 'nominals=[float(principal)]' in SIDECAR.read_text()
    probe = (PREP / 'api-probe.py').read_text().replace("'notionals'", "'nominals'")
    text_file(PREP / 'api-repair.py', probe)
    assert command([PYTHON, '-B', str(PREP / 'api-repair.py')], PREP / 'api-repair') == 0
    save(PREP / 'api.json', read(PREP / 'api-repair/stdout.txt'))
    save(PREP / 'api-repair.json', {'classification': 'LOCAL_BINDING_KEYWORD_ERROR',
        'failed_probe': 'api-probe', 'expected_by_draft': 'notionals', 'actual1.38_binding': 'nominals',
        'repair': 'Use the actual documented keyword; retain failed probe and its measured cost',
        'new_admission_required': False, 'reason': 'No method has been frozen or admitted',
        'fundamental_package_defect_established': False})
    gap = read(ROOT / 'docs/implementation/prospectus-integration-closure/gap-status.json')
    save(PREP / 'requirement.json', {'original_G15': 'Declared fixed-rate schedule, stub, calendar, entitlement, aggregation, event-order and rounding cases match independent calculations and QuantLib on identical premises.',
        'gap_status_sha256': digest(gap), 'covered_here': ['Schedule', 'Stub flags', 'Hypothetical payment adjustment', 'Day fractions', 'Unrounded amounts'],
        'not_package_capabilities': ['Entitlement', 'Legal-holder aggregation', 'Event precedence', 'Legal rounding'],
        '003': 'Eleven endpoint inputs; no calendar rows', '008': 'Six-period consumer; no matched full QuantLib schedule/leg',
        'original_obligations_preserved': ['G14', 'G15', 'E03', 'RESIDUAL-04', 'PACKAGE-03']})
    return {'status': 'PASS', 'classification': 'LOCAL_BINDING_KEYWORD_ERROR', 'actual_keyword': 'nominals'}


def freeze():
    original_integrity()
    for path in methods():
        if path.suffix == '.py':
            compile(path.read_text(), rel(path), 'exec')
    inputs = read(PREP / 'original-inputs.json')
    inputs.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()
                   and 'stages' not in p.relative_to(PREP).parts})
    save(PREP / 'freeze.json', {'methods': {rel(p): sha(p) for p in methods()}, 'inputs': inputs,
        'no_method_edits_after_admission': True,
        'skeptical_audit': {'verdict': 'PASS', 'question': 'Original G15 full schedule/leg comparison',
            'baseline': 'Authenticated003/008 original evidence, complete answers and independent source-integer oracle',
            'api': 'Actual1.38 binding documents explicit paymentCalendar, zero paymentLag and Simple compounding',
            'fixed': ['Strict annual short-first domain, no365-day proxy', 'Adjusted payment coverage checked',
                      'Whole answer/product equality, not numeric-only promotion', 'Independent package date generation'],
            'limits': ['Hypothetical premises', 'No legal entitlement or market-calendar claim',
                       'Original task and whole-build closure not claimed', 'All earlier admissions/costs retained']}})
    return {'methods': len(methods()), 'inputs': len(inputs), 'audit': 'PASS'}


def propose():
    from legalmath.prospectus.execution_authority import write
    frozen()
    auth = Authority(ROOT)
    old, _, _ = auth.spec()
    assert old['revision'] == 258
    attempts = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == 'finance-conventions']
    assert len(attempts) == old['budgets']['finance-conventions']['maximum_new_attempts'] == 8
    new = deepcopy(old)
    new['revision'] = 259
    task = next(t for t in new['tasks'] if t['id'] == 'finance-conventions')
    task.update(dossier=PLAN, build_criteria_scope=[],
                reason='Close original G15 missing matched QuantLib full six-period schedule/leg; original finance requirements remain open')
    task['fixed_phase_package_validation'] = {'version': 'matched-quantlib-fixed-phase.v1',
        'review': rel(PREP), 'bounds': BOUNDS, 'retained_admissions': attempts,
        'whole_task_acceptance': False, 'automatic_retry': False}
    extra = {rel(p) for p in methods()} | set(read(PREP / 'freeze.json')['inputs'])
    extra |= {rel(p) for p in PREP.rglob('*') if p.is_file()}
    extra |= {rel(PREP / 'preflight.json'), rel(PREP / 'stages/propose/result.json')}
    task['inputs'] = sorted(set(task['inputs']) | extra)
    new['budgets']['finance-conventions']['maximum_new_attempts'] = 9
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 259
    route = next(r for r in routes['tasks'] if r['task'] == task['id'])
    route.update(task_sha256=authority_digest(task), dossier=PLAN,
        remaining='Original G15 matched full schedule/leg comparison pending. Entitlement, aggregation, events, rounding and original scope remain separate.',
        next_action='Run frozen009 package, current selected/holiday/excluded full consumers, independent checks and adverse controls; seal, record, refresh, continue next original gap.',
        stop_condition=json.dumps(BOUNDS, sort_keys=True))
    new['continuation_review'].update(plan=PLAN, routes=ROUTES)
    new['continuation_review']['bindings'][ROUTES] = hashlib.sha256(encoded(routes, True)).hexdigest()
    for name in (PLAN, rel(Path(__file__)), rel(SIDECAR), rel(PREP / 'freeze.json')):
        new['continuation_review']['bindings'][name] = sha(ROOT / name)
    review = {'baseline': authority_digest(old),
        'changes': ['Same original finance task; matched full QuantLib comparison missing from003/008',
                    'Frozen optional comparator; no financial-engine change',
                    'One changed admission8-to9; original requirements, evidence and all prior costs retained'],
        'skeptical_audit': read(PREP / 'freeze.json')['skeptical_audit'],
        'evidence_contract': {'question': 'Do actual QuantLib and current consumer agree with independent source-integer calculation on the identical six-period premises?',
            'baseline': 'Authenticated008 complete products/answers and independent oracle; official1.38 methods/API',
            'primary': 'All schedule dates, flags, fractions and unrounded amounts match; full current answers/products equal008',
            'veto': ['Input/method/source drift', 'Bad checker control accepted', 'Different or overstated package scope'],
            'continuation_veto': ['Corrupt evidence', 'Exceeded execution/storage bound', 'Unexpected external activity'],
            'explanatory': ['Counts', 'Time', 'Storage below bounds'],
            'not_concluded': ['Actual holdings or VP calendar', 'Legal entitlement/aggregation/events/rounding by package',
                              'Floating coupons/redemption', 'Automatic legal interpretation', 'Whole task/build completion']},
        'scope_unchanged': True, 'budget_unchanged': False,
        'budget_revision': {'budget_key': 'finance-conventions', 'previous_maximum': 8, 'new_maximum': 9,
            'retained_attempts': attempts, 'reason': 'A distinct original G15 comparison gap, not unchanged retry',
            'next_discriminating_check': 'Actual1.38 six-period schedule/leg versus independent integer oracle and current complete consumers',
            'stop_condition': BOUNDS, 'same_scope_authorization': 'User refresh master program and continue general build'},
        'original_obligations_preserved': True, 'external_opinion_required': False}
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    historical = []
    for name in attempts:
        folder = ROOT / name
        manifest = read(folder / 'run-manifest.json') if (folder / 'run-manifest.json').exists() else {}
        historical.append({'attempt': name, 'bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
            'retained_timing_fields': {k: v for k, v in manifest.items() if 'seconds' in k or 'time' in k},
            'total_historical_runtime': 'UNKNOWN unless explicitly complete in original manifest'})
    # Exact serializer used by Authority.revise for proposal, revision and active copy.
    raw_size = len(encoded(new, True))
    forecast = costs()['new_bytes'] + 3*raw_size + len(encoded(review, True)) + len(encoded(routes, True)) + 3*1024**2 + BOUNDS['reserve_bytes']
    assert forecast < BOUNDS['new_bytes'], 'Full proposal/revision/replacement/output forecast exceeds48MiB'
    save(PREP / 'preflight.json', {'forecast_bytes': forecast, 'new_program_bytes_each': raw_size,
        'program_copies': 3, 'output_and_metadata_forecast_bytes': 3*1024**2,
        'reserve_bytes': BOUNDS['reserve_bytes'], 'bounds': BOUNDS,
        'historical': historical, 'earlier_timing': 'UNKNOWN; no cumulative historical runtime claim'})
    save(ROOT / ROUTES, routes, True)
    write(PROPOSAL, new, exclusive=True)
    write(REVIEW, review, exclusive=True)
    assert PROPOSAL.stat().st_size == raw_size
    return {'revision': 259, 'retained_admissions': len(attempts), 'forecast_bytes': forecast, 'criteria_claimed': []}


def admitted():
    frozen()
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    admission = read(HERE / 'admission.json')
    task = tasks['finance-conventions']
    assert program['revision'] == 259 and task['build_criteria_scope'] == []
    assert admission['program_sha256'] == authority_digest(program)
    assert admission['task_sha256'] == authority_digest(task) and admission['binding'] == auth.binding(task)
    event = next(e for e in auth.events() if e['kind'] == 'ADMIT' and e['attempt'] == rel(HERE))
    assert event['admission_sha256'] == sha(HERE / 'admission.json')


def check_package(output, expected_input, holiday=False):
    assert output['execution'] == 'EXECUTED' and output['engine_executed'] is True
    assert output['version'] == '1.38' and output['input'] == expected_input
    assert output['comparison_scope'] == 'UNADJUSTED_SCHEDULE_AND_HYPOTHETICAL_PAYMENT_CALENDAR_AND_UNROUNDED_LEG'
    assert all(output[k] is False for k in SCOPE_FLAGS)
    assert output['cpu_gpu'] == 'CPU; CUDA_VISIBLE_DEVICES=-1'
    rows = oracle.expected(holiday=holiday)
    assert output['schedule'] == [rows[0]['start'], *[r['end'] for r in rows]]
    assert len(output['coupons']) == len(rows) == 6
    errors = []
    for index, (coupon, expected) in enumerate(zip(output['coupons'], rows)):
        assert coupon['accrual_start'] == expected['start'] and coupon['accrual_end'] == expected['end']
        assert coupon['payment_date'] == expected['payment'] and coupon['regular'] is (index > 0)
        for key in ('day_fraction', 'unrounded_amount', 'nominal'):
            assert type(coupon[key]) in (int, float) and math.isfinite(coupon[key]), key
        assert coupon['nominal'] == 1000000
        fraction_error = abs(coupon['day_fraction'] - float(Fraction(expected['fraction'])))
        amount_error = abs(coupon['unrounded_amount'] - float(Fraction(expected['unrounded'])))
        assert fraction_error <= 1e-12 and amount_error <= 1e-7
        errors.append({'period': index, 'fraction_absolute_error': fraction_error, 'DKK_absolute_error': amount_error})
    return {'periods': len(rows), 'absolute_tolerances': {'fraction': 1e-12, 'DKK': 1e-7}, 'observed_errors': errors}


def bad_inputs(data):
    rows = []
    def put(name, path, value):
        changed = deepcopy(data)
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        rows.append((name, changed))
    for name, path, value in [
        ('actual-premise', ['premise_kind'], 'ACTUAL'),
        ('maturity', ['termination_role'], 'MATURITY'),
        ('wrong-counter', ['day_count'], 'THIRTY_360_USA'),
        ('nonboolean-eom', ['eom'], 0),
        ('boolean-frequency', ['frequency'], True),
        ('zero-principal', ['principal'], '0'),
        ('nonfinite-rate', ['annual_rate'], 'NaN'),
        ('regular-first', ['accrual_start'], '2025-11-25'),
        ('long-first', ['accrual_start'], '2025-08-25'),
        ('unaligned-end', ['fixed_phase_end'], '2031-11-26'),
        ('eom-first', ['first_coupon'], '2026-11-30'),
        ('missing-identity', ['request_sha256'], ''),
        ('missing-coverage', ['calendar', 'valid_until'], '2031-12-01'),
        ('different-weekends', ['calendar', 'weekend'], [4, 5]),
        ('unknown-field', ['unrecognized'], True),
    ]:
        put(name, path, value)
    # Forty covered holidays can push the last payment past otherwise adequate
    # coverage. A pre-adjustment31-day check alone would incorrectly accept it.
    late = deepcopy(data)
    late['calendar']['valid_until'] = '2031-12-26'
    day = date(2031, 11, 25)
    late['calendar']['holidays'] = [(day+timedelta(days=i)).isoformat() for i in range(32)]
    rows.append(('adjusted-payment-outside-coverage', late))
    return rows


def package():
    results = {}
    for name in ('selected', 'holiday'):
        input_path = PREP / (name + '-package-input.json')
        folder = HERE / 'package' / name
        argv = [PYTHON, '-B', '-m', 'scripts.prospectus_adoption_sidecar', 'fixed_phase',
                '--input', str(input_path), '--output', str(folder)]
        assert command(argv, folder) == 0, 'Package/API execution failed: ' + name
        results[name] = check_package(read(folder / 'result.json'), read(input_path), name == 'holiday')
    refusals = []
    for name, data in bad_inputs(read(PREP / 'selected-package-input.json')):
        folder = HERE / 'package-adverse' / name
        save(folder / 'input.json', data)
        code = command([PYTHON, '-B', '-m', 'scripts.prospectus_adoption_sidecar', 'fixed_phase',
                        '--input', str(folder / 'input.json'), '--output', str(folder)], folder)
        output = read(folder / 'result.json')
        assert code == 1 and output['execution'] == 'FAILED', 'Permissive comparator input: ' + name
        assert 'ValueError' in output['traceback'] and 'Traceback' in output['traceback']
        refusals.append({'name': name, 'error': output['error']})
    save(HERE / 'package-comparison.json', {'valid': results, 'input_refusals': refusals,
        'legal_scope': {k: False for k in SCOPE_FLAGS}})
    return {'calendar_cases': len(results), 'periods_each': 6, 'input_refusals': len(refusals)}


def consumers():
    from legalmath.prospectus.successor import service
    records = []
    for name, request in requests().items():
        products = {'P1': service.source_product(request, ROOT)}
        products['P2'] = service.construction_product(products['P1'], ROOT)
        products['P3'] = service.interpretation_product(products['P1'], products['P2'])
        products['P4'] = service.law_product(products['P1'], products['P3'])
        products['P5'] = service.financial_product(products['P1'], products['P2'], products['P3'])
        answer = service.consume(products, ROOT)
        assert answer == read(PRIOR / (name + '-answer.json.gz')), 'Complete answer changed: ' + name
        refs = {}
        for product, value in products.items():
            path = PRIOR / (name + '-' + product + '.json.gz')
            assert value == read(path), 'Complete product changed: ' + name + '/' + product
            refs[product] = {**identity(path), 'semantic_sha256': digest(value)}
        assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']
        proof = oracle.check_value(answer['questions']['Q5']['value'], holiday=name == 'holiday', excluded=name == 'excluded')
        records.append({'name': name, 'actual_full_consumer_executed': True, 'complete_answer_equal008': True,
            'products': refs, 'answer': {**identity(PRIOR / (name + '-answer.json.gz')), 'semantic_sha256': digest(answer)},
            'independent_integer_proof': proof})
    save(HERE / 'consumer-comparison.json', {'status': 'PASS', 'cases': records,
        'retention': 'Identical complete observed values retained by authenticated immutable008 references; no new copies'})
    return {'actual_P1_to_P5_and_final_cases': 3, 'whole_answer_and_products_equal008': True, 'excluded_total': '0'}


def verify():
    original_integrity()
    rows = []
    for name in ('selected', 'holiday'):
        data = read(PREP / (name + '-package-input.json'))
        assert data == package_input(name, requests()[name])
        output = read(HERE / 'package' / name / 'result.json')
        check_package(output, data, name == 'holiday')
        for defect in ('omitted-final-coupon', 'delayed-date-accrual', 'wrong-rate', 'wrong-principal',
                       'wrong-stub', 'false-entitlement-claim', 'not-executed', 'nonfinite-amount'):
            changed = deepcopy(output)
            if defect == 'omitted-final-coupon':
                changed['coupons'].pop()
                changed['schedule'].pop()
            elif defect == 'delayed-date-accrual':
                changed['coupons'][2]['day_fraction'] = 362/360
                changed['coupons'][2]['unrounded_amount'] = 1000000*.051*362/360
            elif defect == 'wrong-rate':
                changed['coupons'][0]['unrounded_amount'] *= 2
            elif defect == 'wrong-principal':
                changed['coupons'][0]['nominal'] *= 2
            elif defect == 'wrong-stub':
                changed['coupons'][0]['regular'] = True
            elif defect == 'false-entitlement-claim':
                changed['legal_entitlement_evaluated'] = True
            elif defect == 'not-executed':
                changed['engine_executed'] = False
            else:
                changed['coupons'][0]['unrounded_amount'] = float('nan')
            try:
                check_package(changed, data, name == 'holiday')
            except AssertionError:
                rows.append({'case': name, 'defect': defect, 'verdict': 'REFUSED'})
            else:
                raise AssertionError('Permissive package-output check: ' + defect)
    # Both package outputs and the current complete financial answer separately
    # match the same independent source-integer oracle. No engine output is fed
    # to QuantLib to obtain agreement by construction.
    assert read(HERE / 'consumer-comparison.json')['status'] == 'PASS'
    save(HERE / 'verification.json', {'status': 'PASS', 'output_adverse': rows,
        'package': read(HERE / 'package-comparison.json'), 'original_source_oracle': oracle.source_check(OLD),
        'source_bound_claim': 'IDENTICAL_SIX_PERIOD_PREMISES_ONLY', 'whole_task_complete': False})
    return {'output_adverse_refusals': len(rows), 'independent_same_premise_comparison': True, 'whole_task_complete': False}


def seal():
    manifest = {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': 'stages/*/started.json and package*/**/command.json',
        'environment': sys.executable, 'python': sys.version, 'package_environment': PYTHON,
        'package_version': read(PREP / 'api.json')['version'], 'module_origins': read(PREP / 'api.json'),
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1 before imports', 'random_seeds': 'N/A deterministic',
        'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'data': read(PREP / 'original-inputs.json'),
        'frozen_methods': frozen()['methods'], 'historical_resources': read(PREP / 'preflight.json')['historical'],
        'resources_before_seal': costs(), 'bounds': BOUNDS, 'earlier_timing': 'UNKNOWN',
        'official_retrieval_commands': rel(PREP / 'official-source-commands.json'),
        'new_installs_native_OCR_model_GPU_subagents_messages': 0}
    save(HERE / 'run-manifest.json', manifest)
    text_file(HERE / 'RESULT.md', '''# Matched six-period QuantLib integration

Actual QuantLib1.38 independently generates the same six accrual periods and
short-first/regular flags as the source-bound local consumer. On the identical
declared Sat/Sun calendar and first-coupon holiday variant, its payment dates,
BondBasis fractions and unrounded amounts agree with a separate source-integer
calculation within the predeclared1e-12 fraction and1e-7 DKK tolerances. Each
local amount is exact:12,750 then five51,000 coupons, total267,750 DKK.

The pre-freeze actual API probe found that our draft used notionals while the
installed1.38 Python binding requires nominals. The failed probe and cost are
retained. Correcting that local keyword before freezing resolves the usage
error; it is not evidence of a fundamental package defect.

The actual current P1–P5 and final consumers for selected, holiday and excluded
requests equal the complete sealed008 products and answers. The excluded case
produces no transfers. Identical full values are preserved by authenticated
immutable references. Invalid adapter inputs and deliberately wrong package
outputs are refused. A full answer comparison prevents numerical agreement from
hiding a changed source qualification, unknown or transaction restriction.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain optional full schedule/leg comparator | Actual dates, flags, fractions and amounts match source-integer oracle; complete current consumers equal008 | No observed source/method drift or permissive adverse control | Reviewed source interpretation and hypothetical premises | Record partial G15 evidence, refresh authority and return to original finance or source gap | No whole-task/build completion |
| Attribute missing comparison to local integration coverage |003 had endpoint inputs only and no calendar rows;008 had no matched full package leg | Actual1.38 API executes with explicit calendar/lag/compounding | Only this finite trial evaluated | Keep package capabilities and legal analysis separate | No fundamental QuantLib defect established |

QuantLib here establishes arithmetic under declared inputs. It does not supply
legal entitlement, holder aggregation, event precedence, applicable rounding or
an actual VP calendar. The first reset bounds this fixed phase; no maturity,
redemption, floating coupon or actual payment is inferred. Original requirements
and all earlier evidence and costs remain retained. External adviser opinion is
not a correctness prerequisite.

The strongest alternative explanation is a shared mistaken source reading or
hypothesis. The retained original anchors and separate integer derivation
constrain this interpretation; a conflicting governing source or real event
would require a new scenario. The weakest evidence is legal exhaustiveness,
which this finite arithmetic trial does not establish. Accepted wrong output,
input drift or disagreement on identical premises would overturn this result.
''')
    save(HERE / 'result.json', {'status': 'PASS', 'task': 'finance-conventions',
        'whole_task_complete': False, 'build_criteria_claimed': [], 'classification': 'MATCHED_QUANTLIB_FIXED_PHASE_COMPARISON',
        'package': read(HERE / 'package-comparison.json'), 'consumers': read(HERE / 'consumer-comparison.json'),
        'verification': read(HERE / 'verification.json'), 'resources_before_seal': costs()})
    return {'status': 'SEALED_PARTIAL', 'whole_task_complete': False}


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in STAGES
    stage = sys.argv[1]
    base = PREP if stage in PREPARATION else HERE
    for predecessor in STAGES[stage]:
        folder = PREP if predecessor in PREPARATION else HERE
        assert read(folder / 'stages' / predecessor / 'result.json')['status'] == 'PASS'
    if stage not in PREPARATION:
        admitted()
    before = costs()
    limit = min(BOUNDS['stage_seconds'], math.floor(BOUNDS['new_seconds'] - before['new_measured_seconds']))
    assert limit > 5
    save(base / 'stages' / stage / 'started.json', {'command': ['.venv/bin/python', '-B', '-m',
        'scripts.prospectus_fixed_phase_package', stage], 'utc': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': limit, 'resources_before': before})
    def alarm(*args):
        raise TimeoutError('Reviewed fixed-phase package stage ceiling')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(limit)
    started = time.monotonic()
    try:
        detail = globals()[stage]()
        receipt = {'status': 'PASS', 'detail': detail, 'wall_seconds': time.monotonic()-started}
    except Exception as error:
        receipt = {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic()-started}
        save(base / 'stages' / stage / 'result.json', receipt)
        if base == HERE:
            if not (HERE / 'result.json').exists():
                save(HERE / 'result.json', {'status': 'FAIL', 'whole_task_complete': False,
                     'failed_stage': stage, 'error': repr(error)})
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        raise
    finally:
        signal.alarm(0)
    save(base / 'stages' / stage / 'result.json', receipt)
    if stage == 'seal':
        save(HERE / 'final-resources.json', costs())
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
    after = costs()
    print(json.dumps({'stage': stage, **receipt, 'resources': after}), flush=True)


if __name__ == '__main__':
    main()
