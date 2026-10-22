"""Bounded source-to-purpose discovery under the original prospectus authority."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import os
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_unquoted_verifier_repair as prior
from scripts import prospectus_purpose_uses_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/purpose-use-discovery-351'
HERE = AUTH / 'attempts/basf-references/attempt-090'
PLAN = 'docs/plans/prospectus-purpose-use-discovery-2026-10-19.md'
METHOD = 'scripts/prospectus_purpose_uses.py'
WORKER = 'scripts/prospectus_purpose_uses_installed.py'
TEST = 'tests/prospectus_successor/test_purpose_uses.py'
FILES = (PLAN, METHOD, WORKER, TEST, 'scripts/prospectus_purpose_uses_oracle.py',
    'scripts/prospectus_purpose_uses_cases.py',
    'docs/implementation/prospectus-execution-authority/reviews/purpose-use-discovery-351/METHOD-REVIEW.md')
TARGETS = tuple('src/legalmath/prospectus/successor/' + name for name in
    ('purpose_uses.py', 'purpose_uses_spec.json', 'service.py', 'conditional_profiles.py'))
STAGES = ('install', 'tests', 'consume', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.PRODUCTS
SECONDS_BOUND, BYTES_BOUND = 25200, 3712 * 1024**2


def baseline():
    products = {k: read(ROOT / row['path']) for k, row in read(PRODUCTS)['products'].items()}
    old = read(prior.prior.HERE / 'ordinary-answer.json.gz')
    frozen = read(PREP / 'source-freeze.json')
    assert digest(products) == frozen['products_sha256'] and digest(old) == frozen['ordinary_answer_sha256']
    assert read(prior.HERE / 'result.json')['status'] == 'PASS'
    return products, old


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    seconds = base['combined_measured_seconds'] + read(PREP / 'source-freeze.json')['wall_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0351.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / name).stat().st_size - start['production_bytes'][name])
                for name in TARGETS if (ROOT / name).exists())
    charge = base['conservative_extra_seconds']
    assert seconds + charge < SECONDS_BOUND and size < BYTES_BOUND - 4 * 1024**2, 'Cumulative purpose-use bound'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
        'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
        'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
        'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [TEST, 'tests/prospectus_successor/test_unquoted_definitions.py',
        'tests/prospectus_successor/test_unquoted_verifier_repair.py',
        'tests/prospectus_successor/test_standalone_sections.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py']


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 350
    events = Authority(ROOT).events()
    attempts = [event['attempt'] for event in events
        if event['kind'] == 'ADMIT' and event.get('budget_key') == 'basf-references']
    assert len(attempts) == 89
    assert any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for name, value in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == value, name
    prior.verify_lineage()
    frozen = read(PREP / 'source-freeze.json')
    assert frozen['candidate_absent'] is True
    assert sha(PREP / 'expected.json') == frozen['expected_sha256'] and sha(ROOT / PLAN) == frozen['plan_sha256']
    baseline()
    spec = {'version': 'purpose-use-discovery.v1', 'products_sha256': frozen['products_sha256'],
        'ordinary_answer_sha256': frozen['ordinary_answer_sha256'],
        'target_claim': 'Finite source-discovered adjective/noun uses and proposed printed-purpose connections',
        'legal_truth_established': False}
    save(PREP / 'candidate/purpose_uses_spec.json', spec)
    path = PREP / 'candidate/purpose_uses.py'
    candidate = path.read_text()
    assert candidate.count('SPEC_SHA256 = None') == 1
    path.write_text(candidate.replace('SPEC_SHA256 = None', 'SPEC_SHA256 = ' + repr(digest(spec))))
    service = (ROOT / TARGETS[2]).read_text()
    signature = 'unquoted_definitions_profile=None, expected_unquoted_definitions_profile_sha256=None):'
    assert service.count(signature) == 1
    service = service.replace(signature,
        'unquoted_definitions_profile=None, expected_unquoted_definitions_profile_sha256=None,\n'
        '            purpose_uses_profile=None, expected_purpose_uses_profile_sha256=None):')
    marker = '    return {**result, "report_sha256": digest(result)}\n'
    assert service.count(marker) == 1
    block = """    if purpose_uses_profile is not None:
        from .purpose_uses import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, purpose_uses_profile, root,
            expected_profile_sha256=expected_purpose_uses_profile_sha256))
    elif expected_purpose_uses_profile_sha256 is not None:
        raise ValueError('Purpose-use profile pin supplied without a profile')
"""
    (PREP / 'candidate/service.py').write_text(service.replace(marker, block + marker))
    loader = (ROOT / TARGETS[3]).read_text()
    marker = "'standalone_sections', 'unquoted_definitions')"
    assert loader.count(marker) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(loader.replace(marker,
        "'standalone_sections', 'unquoted_definitions', 'purpose_uses')"))
    profile = {key: spec[key] for key in ('version', 'products_sha256', 'ordinary_answer_sha256')}
    profile.update(specification_sha256=digest(spec), whole_task_complete=False, legal_truth_established=False)
    save(PREP / 'profile.json', profile)
    manifest = read(prior.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'purpose_uses', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    (PREP / 'baseline').mkdir()
    installation = []
    for target in TARGETS:
        path = ROOT / target
        candidate = PREP / 'candidate' / path.name
        if candidate.suffix == '.py': ast.parse(candidate.read_text())
        if path.exists(): shutil.copyfile(path, PREP / 'baseline' / path.name)
        installation.append({'target': target, 'before': sha(path) if path.exists() else None,
            'candidate': rel(candidate), 'after': sha(candidate)})
    save(PREP / 'installation.json', installation)
    bindings = {name: sha(ROOT / name) for name in (*CODE, *FILES, *testfiles(), 'pyproject.toml',
        prior.METHOD, 'scripts/prospectus_residual_coverage.py')}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in (prior.HERE / 'outputs.json', prior.prior.HERE / 'ordinary-answer.json.gz', PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(PRODUCTS)['products'].values(): bindings[row['path']] = row['sha256']
    for row in manifest['profiles']: bindings[row['path']] = row['file_sha256']
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False})
    proposal = deepcopy(program)
    proposal['revision'] = 351
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Discover inflected uses and distinct printed purposes from source declarations; preserve conditional meanings and uncertainty',
        purpose_use_review={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]
        + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 90
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 351
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify source-discovered use/purpose connections,then reassess all seven original gap classes',
                stop_condition='90 admissions;25200 accounted seconds;3712 MiB including4 MiB reserve;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS: proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 1100,
        'bytes': snapshot['combined_bytes'] + 96 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < SECONDS_BOUND and forecast['bytes'] < BYTES_BOUND - 4 * 1024**2, 'Forecast does not fit'
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Source-discovered inflected uses and explicit unresolved/title roles',
            'Reconcile printed-purpose proposals with existing conditional meanings without regenerating them',
            'Preserve user deferrals,original obligations and all89 previous admissions'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Six independent exact source readings,two distinct printed purposes,renamed/adverse cases,and complete ordinary/installed equality',
            'promotion_veto': ['Wrong use/role/purpose/source', 'False legal admission', 'Changed old answer', 'Accepted tampering', 'Wrong installed import'],
            'continuation_veto': ['Corrupt frozen baseline', 'Method drift', 'Cumulative resource bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General linguistic recall', 'Complete governing scope', 'Entitlement', 'Historical law', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 89, 'new_maximum': 90,
            'retained_attempts': attempts, 'reason': 'Distinct declarations and reviewed semantics do not yet discover inflected uses or propose printed-purpose connections',
            'next_discriminating_check': 'Exact source roles and purposes with broad reference/title unselected plus isolated complete installed equality',
            'stop_condition': '25200seconds/3712MiB cumulative including4MiB reserve;no unchanged retry',
            'same_scope_authorization': 'User requested continued reviewed internal evidence for the whole general build'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': True,
            'previous_seconds_bound': 24000, 'previous_bytes_bound': 3584 * 1024**2,
            'seconds_bound': SECONDS_BOUND, 'bytes_with_reserve': BYTES_BOUND,
            'reason': 'Bounded source-to-purpose experiment;all previous costs retained;older unmeasured time stays UNKNOWN'}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 351, 'candidate_evaluated': False, 'forecast': forecast}


def tests():
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', **counts}


def cli_arguments(output):
    return ['prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
        '--output', str(HERE / output), '--mode', 'frozen', '--conditional-profiles', rel(PREP / 'profiles.json'),
        '--conditional-profiles-sha256', sha(PREP / 'profiles.json')]


def consume():
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli',
        *cli_arguments('ordinary-answer.json')], 360)
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json')
    result = oracle.verify(actual, old, products, read(PREP / 'expected.json'), read(PREP / 'profile.json'))
    save(HERE / 'independent-verification.json', result)
    return {**result, 'actual_cli': True, 'answer_sha256': digest(actual), **engine.compress_output('ordinary-answer.json')}


def controls():
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json.gz')
    refused = {}
    for kind in ('omit-use', 'wrong-term', 'swap-purpose', 'drop-restriction', 'wrong-value',
        'invent-destination', 'source-map-delete', 'wrong-declaration-source', 'heading-operative',
        'broad-reference-selected', 'false-meaning', 'false-completion', 'prior-answer',
        'profile-identity', 'source-identity', 'false-reconciliation', 'malformed-occurrence',
        'malformed-declaration', 'malformed-target', 'malformed-reconciliation'):
        bad = deepcopy(actual)
        report = bad[oracle.KEY]
        row, declaration = report['occurrences'][0], report['declarations'][0]
        if kind == 'omit-use': report['occurrences'].pop()
        elif kind == 'wrong-term': row['start'] += 1
        elif kind == 'swap-purpose': declaration['targets'] = deepcopy(report['declarations'][1]['targets'])
        elif kind == 'drop-restriction': declaration['restriction'] = None
        elif kind == 'wrong-value': declaration['value'] = deepcopy(report['declarations'][1]['value'])
        elif kind == 'invent-destination': declaration['targets'][0]['path'] = ['10', 'a']
        elif kind == 'source-map-delete': row['source_projection'].pop()
        elif kind == 'wrong-declaration-source': declaration['source_projection'].pop()
        elif kind == 'heading-operative': report['occurrences'][3]['role'] = 'USE_CANDIDATE'
        elif kind == 'broad-reference-selected': row['selected_declaration_starts'] = [21343]
        elif kind == 'false-meaning': row['meaning'] = 'Legal meaning established'
        elif kind == 'false-completion': report['whole_task_complete'] = True
        elif kind == 'prior-answer': bad['questions']['Q1']['status'] = 'YES'
        elif kind == 'profile-identity': report['profile_sha256'] = '0' * 64
        elif kind == 'source-identity': report['text_sha256'] = '0' * 64
        elif kind == 'false-reconciliation': report['reviewed_binding_reconciliation']['occurrences'][1]['reviewed_rule'] = 'makewhole'
        elif kind == 'malformed-occurrence': report['occurrences'][0] = None
        elif kind == 'malformed-declaration': report['declarations'][0] = None
        elif kind == 'malformed-target': declaration['targets'] = [None]
        else: report['reviewed_binding_reconciliation'] = None
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try:
            oracle.verify(bad, old, products, read(PREP / 'expected.json'), read(PREP / 'profile.json'))
        except AssertionError as error:
            refused[kind] = {'reason': str(error), 'exception': 'AssertionError', 'outer_digest_recomputed': True}
        else: raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused, 'unexpected_exceptions_accepted': False})
    return {'status': 'PASS', 'refused': len(refused), 'unexpected_exceptions_accepted': False}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
        str(ROOT), str(HERE), str(PREP)], 360)
    return {**read(HERE / 'installed-result.json'), **engine.compress_output('installed-answer.json')}


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'SOURCE_PURPOSE_USE_DISCOVERY', **read(HERE / 'independent-verification.json'),
        'ordinary_installed_equal': True, 'controls': read(HERE / 'stages/controls/result.json'),
        'resources': costs(), 'next_action': 'Reassess seven open source classes and continue historical/onward law and scope evidence'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / stage / 'started.json')['command'] for stage in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PRODUCTS), 'wall_time': costs(),
        'plan': PLAN, 'result': rel(HERE / 'result.json')})
    with (HERE / 'RESULT.md').open('x') as stream: stream.write(RESULT_NOTE)
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {name: (ROOT / name).stat().st_size if (ROOT / name).exists() else 0 for name in TARGETS}})
    else:
        for preceding in STAGES[:STAGES.index(stage)]: assert read(HERE / 'stages' / preceding / 'result.json')['status'] == 'PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    engine.PREP, engine.HERE, engine.PLAN, engine.METHOD, engine.WORKER, engine.TARGETS = PREP, HERE, PLAN, METHOD, WORKER, TARGETS
    engine.costs, engine.testfiles = costs, testfiles
    bound = 90 if stage == 'prepare' else 420
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_purpose_uses', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Purpose-use stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': engine.frozen(installed=stage != 'install')
        function = globals().get(stage.replace('-', '_')) or getattr(engine, stage)
        result = function()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(folder / 'result.json', result)
        if stage == 'seal': save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - started})
        raise
    finally: signal.alarm(0)


RESULT_NOTE = '''# Source-discovered terms retain their distinct printed purposes

Six exact occurrences include two inflected operative-use candidates, two
declaration terms, one broad reference and one title. Printed purpose addresses
propose the tax and issuer-option connections separately. The broad reference
and title select no declaration. Exact source projections and a separately frozen
oracle check these findings; reconciliation agrees with the existing conditional
binding matrix without deriving new legal meanings. The complete previous answer
is preserved, and fresh normal and isolated installed CLI answers agree.

|Decision|Primary criterion|Veto status|Main uncertainty|Next justified action|Not concluded|
|---|---|---|---|---|---|
|Retain bounded source discovery|Exact six readings,two purposes,renamed grammar cases and complete consumer equality pass|No source,baseline,tampering or import veto observed|Finite morphology and printed containment do not establish governing legal scope|Reassess seven original gap classes and return to law/scope evidence|General recall,actual entitlement,historical-law applicability or whole build|

The strongest alternative explanation is that finite morphology succeeds only
on the declared grammar; renamed terms and adverse boundaries discriminate
lookup from discovery but cannot prove general recall. A source disagreement or
accepted semantic promotion would overturn this result. No new external package
is under test; an implementation failure would concern our code or harness.
All cumulative costs and original obligations remain retained. Real holdings and
reader acceptance follow the general build; external opinions are not required.
'''


if __name__ == '__main__': main()
