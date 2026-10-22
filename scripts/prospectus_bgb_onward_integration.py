"""Integrate sealed current-source readings without rebasing prior legal answers."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import math
import os
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_bgb_onward_sources as sources
from scripts import prospectus_purpose_use_spelling_repair as spelling
from scripts import prospectus_bgb_onward_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = spelling.ROOT, spelling.AUTH, spelling.engine
PREP = AUTH / 'reviews/bgb-onward-integration-354'
HERE = AUTH / 'attempts/basf-references/attempt-093'
PLAN = 'docs/plans/prospectus-bgb-onward-integration-2026-10-20.md'
METHOD = 'scripts/prospectus_bgb_onward_integration.py'
WORKER = 'scripts/prospectus_bgb_onward_installed.py'
REVIEW = str((PREP / 'METHOD-REVIEW.md').relative_to(ROOT))
FILES = (PLAN, METHOD, WORKER, REVIEW, 'scripts/prospectus_bgb_onward_oracle.py',
         'tests/prospectus_successor/test_bgb_onward.py')
TARGETS = tuple('src/legalmath/prospectus/successor/' + name for name in
                ('bgb_onward.py', 'service.py', 'conditional_profiles.py'))
STAGES = ('install', 'tests', 'consume', 'controls', 'package', 'installed', 'seal')
PRODUCTS = spelling.PRODUCTS
SECONDS_BOUND, BYTES_BOUND = spelling.SECONDS_BOUND, spelling.BYTES_BOUND
FORECAST_SECONDS, FORECAST_BYTES = 800, 96 * 1024**2
SCOPE = 'BGB802_PRE_INITIATION_SIX_MONTH_PERIOD'
read, save, sha, rel = spelling.read, spelling.save, spelling.sha, spelling.rel


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    measured = base['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            measured += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0354.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / name).stat().st_size - start['production_bytes'][name])
                for name in TARGETS if (ROOT / name).exists())
    charge = base['conservative_extra_seconds'] + 60
    assert measured + charge < SECONDS_BOUND, 'Cumulative accounted time exhausted'
    assert size < BYTES_BOUND - 4 * 1024**2, 'Cumulative storage reserve reached'
    assert measured - base['combined_measured_seconds'] < FORECAST_SECONDS, 'Integration command allowance exhausted'
    assert size - base['combined_bytes'] < FORECAST_BYTES, 'Integration storage allowance exhausted'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charge,
        'combined_accounted_seconds': measured + charge, 'combined_bytes': size,
        'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
        'prior_costs_reset': False, 'unmeasured_authoring_and_older_time': 'UNKNOWN; conservative charge is not a measurement'}


def testfiles():
    return [FILES[-1], 'tests/prospectus_successor/test_conditional_profiles_cli.py',
        'tests/prospectus_successor/test_bgb_timing_rules.py',
        'tests/prospectus_successor/test_statutory_numbered_measures.py']


def baseline():
    products = {k: read(ROOT / row['path']) for k, row in read(PRODUCTS)['products'].items()}
    old = read(spelling.HERE / 'ordinary-answer.json.gz')
    profile = read(PREP / 'profile.json')
    assert digest(products) == profile['products_sha256']
    assert digest(old) == profile['ordinary_answer_sha256']
    return products, old


def source_profile(products, old):
    """Authored source interpretation; never import/call the candidate for expectations."""
    findings = read(sources.HERE / 'source-findings.json')
    assert findings['production_changed'] is findings['historical_application_proved'] is False
    assert [row['section'] for row in findings['readings']] == ['206', '210', '211']
    h28 = next(r for r in old['statutory_references']['records'] if r['id'] == 'H28')
    save(PREP / 'h28-baseline.json', h28)
    scope_path = findings['antecedent_review']['literal_source']
    scope_text = (ROOT / scope_path).read_text()
    scope_quotes = [
        'falls die Zahlungssperre vor der Einleitung des Verfahrens verfügt worden ist, auch dann, wenn seit der Beseitigung des der Einleitung entgegenstehenden Hindernisses sechs Monate verstrichen sind und nicht vorher die Einleitung beantragt worden ist.',
        'Auf diese Frist finden die Vorschriften der §§ 206, 210, 211 entsprechende Anwendung.']
    excerpts = []
    for quote in scope_quotes:
        assert scope_text.count(quote) == 1
        a = scope_text.index(quote)
        excerpts.append({'start': a, 'end': a + len(quote), 'quote': quote})
    # Independent finite interpretation of the complete retained092 primary readings.
    literal = {
        '206': {'effect': 'SUSPENSION_WHILE_PREVENTED',
            'conditions': ['CREDITOR_PREVENTED_FROM_PURSUING_RIGHT', 'FORCE_MAJEURE',
                           'WITHIN_LAST_SIX_MONTHS_OF_LIMITATION'], 'exceptions': []},
        '210': {'effect': 'PREVENTION_OF_EXPIRY',
            'conditions': ['PERSON_INCAPABLE_OR_LIMITED_LEGAL_CAPACITY', 'NO_LEGAL_REPRESENTATIVE',
                           'LIMITATION_FOR_OR_AGAINST_PERSON'], 'after_event_months': 6,
            'alternative_events': ['UNRESTRICTED_LEGAL_CAPACITY', 'REPRESENTATION_DEFECT_REMEDIED'],
            'exceptions': ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS',
                'PARAGRAPH1_EXCLUDED_INSOFAR_LIMITED_CAPACITY_PERSON_HAS_PROCEDURAL_CAPACITY']},
        '211': {'effect': 'PREVENTION_OF_EXPIRY',
            'conditions': ['CLAIM_BELONGS_TO_OR_IS_DIRECTED_AGAINST_ESTATE'], 'after_event_months': 6,
            'alternative_events': ['INHERITANCE_ACCEPTED_BY_HEIR', 'ESTATE_INSOLVENCY_OPENED',
                'CLAIM_CAN_BE_ASSERTED_BY_OR_AGAINST_REPRESENTATIVE'],
            'exceptions': ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS'],
            'actual_event_priority_established': False}}
    readings = []
    for row in findings['readings']:
        section = row['section']
        folder = sources.HERE / 'requests' / section
        source = {key: deepcopy(row[key]) for key in ('text_path', 'text_sha256', 'excerpts')}
        for name, path in (('raw', folder / 'body'), ('receipt', folder / 'receipt.json')):
            source[name + '_path'], source[name + '_sha256'] = rel(path), sha(path)
        assert sha(ROOT / source['text_path']) == source['text_sha256']
        readings.append({'section': section, 'literal_rule': literal[section], 'source': source,
            'local_corresponding_application': {'target_period': SCOPE, 'application_proved': False,
                'construction': row['local_corresponding_application']},
            'historical_application_proved': False, 'unresolved': deepcopy(row['unresolved'])})
    return {'version': 'bgb802-onward-readings.v1', 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(old), 'h28_record_sha256': digest(h28),
        'scope': {'antecedent': SCOPE, 'status': 'LOCAL_GRAMMATICAL_CONSTRUCTION',
            'application_to_all_clocks_proved': False,
            'source': {'text_path': scope_path, 'text_sha256': sha(ROOT / scope_path), 'excerpts': excerpts}},
        'readings': readings, 'historical_application_proved': False, 'actual_deadline_computed': False,
        'automatic_legal_interpretation': False, 'whole_task_complete': False, 'whole_build_complete': False,
        'unresolved': ['HISTORICAL_WORDING', 'CORRESPONDING_APPLICATION', 'PERSON_AND_CLAIM_FACTS',
                       'EVENT_DATES', 'CIVIL_COUNTING_CONVENTIONS']}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 353
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 92
    assert [e['kind'] for e in events if e.get('attempt') == rel(sources.HERE)][-1] == 'RECORD'
    assert read(sources.HERE / 'result.json')['status'] == 'PASS'
    for folder in (sources.HERE, spelling.HERE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, name
    products = {k: read(ROOT / row['path']) for k, row in read(PRODUCTS)['products'].items()}
    old = read(spelling.HERE / 'ordinary-answer.json.gz')
    profile = source_profile(products, old)
    save(PREP / 'profile.json', profile)
    expected = deepcopy(profile)
    expected.update(profile_sha256=digest(profile), original_h28_preserved=True,
        complete_prior_answer_preserved=True,
        finding='Current literal conditions retained;802 antecedent is a local construction;actual application remains unknown')
    save(PREP / 'expected.json', expected)
    candidate = PREP / 'candidate/bgb_onward.py'
    text = candidate.read_text()
    assert text.count('REGISTERED_PROFILE_SHA256 = None') == 1
    candidate.write_text(text.replace('REGISTERED_PROFILE_SHA256 = None',
                                     'REGISTERED_PROFILE_SHA256 = ' + repr(digest(profile))))
    service = (ROOT / TARGETS[1]).read_text()
    signature = 'purpose_uses_profile=None, expected_purpose_uses_profile_sha256=None):'
    assert service.count(signature) == 1
    service = service.replace(signature, 'purpose_uses_profile=None, expected_purpose_uses_profile_sha256=None,\n'
        '            bgb_onward_profile=None, expected_bgb_onward_profile_sha256=None):')
    marker = '    return {**result, "report_sha256": digest(result)}\n'
    assert service.count(marker) == 1
    block = """    if bgb_onward_profile is not None:
        from .bgb_onward import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, bgb_onward_profile, root,
            expected_profile_sha256=expected_bgb_onward_profile_sha256))
    elif expected_bgb_onward_profile_sha256 is not None:
        raise ValueError('BGB onward profile pin supplied without a profile')
"""
    (PREP / 'candidate/service.py').write_text(service.replace(marker, block + marker))
    loader = (ROOT / TARGETS[2]).read_text()
    marker = "'unquoted_definitions', 'purpose_uses')"
    assert loader.count(marker) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(loader.replace(marker,
        "'unquoted_definitions', 'purpose_uses', 'bgb_onward')"))
    manifest = read(spelling.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'bgb_onward', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    installation = []
    for name in TARGETS:
        path = ROOT / name
        candidate = PREP / 'candidate' / path.name
        ast.parse(candidate.read_text())
        if path.exists():
            (PREP / 'baseline').mkdir(exist_ok=True)
            shutil.copyfile(path, PREP / 'baseline' / path.name)
        installation.append({'target': name, 'before': sha(path) if path.exists() else None,
            'candidate': rel(candidate), 'after': sha(candidate)})
    save(PREP / 'installation.json', installation)
    bindings = {name: value for name, value in read(sources.PREP / 'freeze.json')['bindings'].items()
                if name not in TARGETS}
    bindings.update({name: sha(ROOT / name) for name in (*CODE, *FILES, *testfiles(),
        sources.METHOD, spelling.METHOD, 'scripts/prospectus_residual_coverage.py', 'pyproject.toml')
        if name not in TARGETS})
    production = engine.filemap(ROOT / 'src/legalmath')
    for row in installation:
        production[row['target'].removeprefix('src/legalmath/')] = row['after']
    save(PREP / 'production-map.json', production)
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    for folder in (sources.HERE, spelling.HERE):
        bindings.update({rel(folder / name): checksum for name, checksum in read(folder / 'outputs.json').items()})
        bindings[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
    bindings[rel(PRODUCTS)] = sha(PRODUCTS)
    for row in read(PRODUCTS)['products'].values(): bindings[row['path']] = row['sha256']
    for row in manifest['profiles']: bindings[row['path']] = row['file_sha256']
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False,
        'source_expectations_from': rel(sources.HERE / 'source-findings.json'),
        'source_expectations_from_candidate': False, 'production_changes': list(TARGETS)})
    proposal = deepcopy(program)
    proposal['revision'] = 354
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=REVIEW, timeout_seconds=420,
        reason='Carry retained206/210/211 exceptions and scoped802 reading into the normal answer while preserving all091 content',
        bgb_onward_integration={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]
        + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 93
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 354
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify exact onward readings through complete consumers,then reassess all seven original gaps',
                stop_condition='93 admissions;800new command seconds/96MiB;25200accounted seconds/3712MiB cumulative including4MiB reserve;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS: proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + FORECAST_SECONDS,
        'bytes': snapshot['combined_bytes'] + FORECAST_BYTES, 'estimate_only': True}
    assert forecast['seconds'] < SECONDS_BOUND and forecast['bytes'] < BYTES_BOUND - 4 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Append current-source reading without modifying frozen statutory products',
            'Preserve complete091 answer and all92 admissions;no source acquisitions or old budget resets'],
        'skeptical_audit': {'verdict': 'PASS', 'review': REVIEW, 'forecast': forecast},
        'evidence_contract': {'primary': 'Exact full primary readings,all exceptions,complete prior-answer preservation,and complete ordinary/installed equality',
            'promotion_veto': ['Missing exception/trigger', 'Broadened scope', 'False historical/application claim',
                'Changed source or prior answer', 'Accepted rehashed mutation', 'Wrong installed import'],
            'continuation_veto': ['Corrupt frozen input', 'Method drift', 'Cumulative bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General recall', 'Historical application', 'Actual deadline', 'Entitlement', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 92, 'new_maximum': 93,
            'retained_attempts': attempts, 'reason': 'Sealed092 primary readings still need actual downstream consideration',
            'next_discriminating_check': 'Independent full literal/scope verification and complete isolated installed equality',
            'stop_condition': 'Unchanged25200seconds/3712MiB cumulative including4MiB reserve;800new command seconds/96MiB;no retry',
            'same_scope_authorization': 'User requested refreshed master and continued internally proved general build'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': False,
            'conservative_authoring_charge_seconds': 60, 'older_unmeasured_time': 'UNKNOWN'}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 354, 'candidate_evaluated': False, 'forecast': forecast}


def frozen(installed=True):
    engine.frozen(installed=installed)
    if installed:
        assert engine.filemap(ROOT / 'src/legalmath') == read(PREP / 'production-map.json'), 'Whole production map drift'


def install():
    for row in read(PREP / 'installation.json'):
        path = ROOT / row['target']
        assert (sha(path) if path.exists() else None) == row['before']
        shutil.copyfile(ROOT / row['candidate'], path)
    return {'status': 'PASS', 'production_files': len(TARGETS)}


def tests():
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', **counts}


def consume():
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli',
        'prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
        '--output', str(HERE / 'ordinary-answer.json'), '--mode', 'frozen',
        '--conditional-profiles', rel(PREP / 'profiles.json'),
        '--conditional-profiles-sha256', sha(PREP / 'profiles.json')], 360)
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json')
    result = oracle.verify(actual, old, products, read(PREP / 'expected.json'), read(PREP / 'profile.json'), ROOT)
    save(HERE / 'independent-verification.json', result)
    return {**result, 'actual_cli': True, 'answer_sha256': digest(actual), **engine.compress_output('ordinary-answer.json')}


def controls():
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json.gz')
    profile, expected = read(PREP / 'profile.json'), read(PREP / 'expected.json')
    refused = {}
    for kind in ('210-exclusion', '210-shorter', '211-shorter', '211-trigger', '206-effect', '206-time',
        'scope', 'scope-proved', 'correspondence', 'historical', 'deadline', 'complete', 'source',
        'quote', 'offset', 'prior-answer', 'h28', 'profile'):
        bad = dict(actual)
        report = bad[oracle.KEY] = deepcopy(actual[oracle.KEY])
        a, b, c = report['readings']
        if kind == '210-exclusion': b['literal_rule']['exceptions'].pop()
        elif kind == '210-shorter': b['literal_rule']['exceptions'].pop(0)
        elif kind == '211-shorter': c['literal_rule']['exceptions'] = []
        elif kind == '211-trigger': c['literal_rule']['alternative_events'].pop()
        elif kind == '206-effect': a['literal_rule']['effect'] = 'AUTOMATIC_SIX_MONTH_ADDITION'
        elif kind == '206-time': a['literal_rule']['conditions'].pop()
        elif kind == 'scope': report['scope']['antecedent'] = 'ALL_CLOCKS'
        elif kind == 'scope-proved': report['scope']['application_to_all_clocks_proved'] = True
        elif kind == 'correspondence': a['local_corresponding_application']['application_proved'] = True
        elif kind == 'historical': report['historical_application_proved'] = True
        elif kind == 'deadline': report['actual_deadline_computed'] = True
        elif kind == 'complete': report['whole_build_complete'] = True
        elif kind == 'source': a['source']['text_sha256'] = '0' * 64
        elif kind == 'quote': b['source']['excerpts'][0]['quote'] += ' changed'
        elif kind == 'offset': b['source']['excerpts'][0]['start'] += 1
        elif kind == 'prior-answer':
            bad['questions'] = deepcopy(actual['questions'])
            bad['questions']['Q1']['status'] = 'YES'
        elif kind == 'h28': report['h28_record_sha256'] = '0' * 64
        else: report['profile_sha256'] = '0' * 64
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try:
            oracle.verify(bad, old, products, expected, profile, ROOT)
        except AssertionError as error:
            refused[kind] = {'reason': str(error), 'outer_digest_recomputed': True, 'exception': 'AssertionError'}
        else:
            raise AssertionError('Accepted adverse output ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused, 'unexpected_exceptions_accepted': False})
    return {'status': 'PASS', 'refused': len(refused), 'unexpected_exceptions_accepted': False}


def package():
    result = engine.package()
    assert read(HERE / 'package.json')['files'] == read(PREP / 'production-map.json')
    return result


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
        str(ROOT), str(HERE), str(PREP)], 360)
    return {**read(HERE / 'installed-result.json'), **engine.compress_output('installed-answer.json')}


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'CURRENT_BGB_ONWARD_SOURCE_READING_INTEGRATION',
        **read(HERE / 'independent-verification.json'), 'ordinary_installed_equal': True,
        'tests': read(HERE / 'stages/tests/result.json'), 'controls': read(HERE / 'stages/controls/result.json'),
        'resources': costs(), 'next_action': 'Reassess all seven original gaps;historical wording and corresponding application remain open'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / stage / 'started.json')['command'] for stage in STAGES],
        'subprocess_commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'installed_environment': read(HERE / 'package.json')['python'],
        'cpu_gpu': 'CPU;GPU intentionally hidden', 'seeds': 'N/A deterministic',
        'data_version': sha(PRODUCTS), 'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(RESULT_NOTE)
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': sources.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS}})
    else:
        for previous in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / previous / 'result.json')['status'] == 'PASS'
    for name in ('PREP', 'HERE', 'PLAN', 'METHOD', 'WORKER', 'TARGETS', 'costs', 'testfiles'):
        setattr(engine, name, globals()[name])
    remaining = min(SECONDS_BOUND - costs()['combined_accounted_seconds'],
        FORECAST_SECONDS - (costs()['combined_measured_seconds'] - read(PREP / 'accounting-start.json')['prior']['combined_measured_seconds']))
    bound = min(90 if stage == 'prepare' else 420, math.floor(remaining) - 1)
    assert bound > 0, 'No command allowance remains'
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_bgb_onward_integration', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('BGB integration stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': frozen(installed=stage != 'install')
        result = globals()[stage]()
        if stage != 'prepare': frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error),
            'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


RESULT_NOTE = '''# Current BGB onward readings reach the ordinary answer

The ordinary answer now retains the complete literal206,210 and211 readings,
including210(2),both shorter-period substitutions and all three211 alternatives.
Suspension under206 remains distinct from protection against expiry under210/211.
The immediate802 antecedent is explicitly a local grammatical construction;
corresponding procedural application remains unproved. Every091 answer field,
including the original H28 and all earlier supplements, is preserved unchanged.
The isolated installed CLI produces the same complete answer and imports the
new module from the verified offline package.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite reading integration|Exact independent source expectations and complete consumers agree|Source,semantic,tampering,baseline and import checks pass|Historical wording and procedural correspondence remain open|Reassess all seven original gap classes within retained limits|General recall,deadline,entitlement or build completion|

This is deterministic engineering evidence of faithful representation, not an
independent proof of all legal meaning. The strongest alternative is a broader
reasoned interpretation of802 than its immediate grammatical antecedent. A
historical or contrary authoritative source would require revisiting the local
construction. No external package was newly evaluated; any implementation
failure belongs to our code or harness. All original obligations and costs,
including unmeasured older time recorded as UNKNOWN, remain. Actual holdings
and reader acceptance follow the general build; external opinion is no prerequisite.
'''


if __name__ == '__main__':
    main()
