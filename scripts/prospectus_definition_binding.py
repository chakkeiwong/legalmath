"""Reviewed repair331; bounded stages with preserved costs and exact answers."""
from collections import Counter
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

from scripts import prospectus_definition_semantics as prior
from scripts import prospectus_definition_binding_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/definition-bindings-repair-331'
DRAFT = AUTH / 'reviews/definition-bindings-331'
HERE = AUTH / 'attempts/basf-references/attempt-070'
BASE = AUTH / 'attempts/basf-references/attempt-067'
PRODUCTS = AUTH / 'reviews/conditional-cli-311/products.json'
PLAN = 'docs/plans/prospectus-definition-bindings-repair-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_binding.py'
WORKER = 'scripts/prospectus_definition_binding_installed.py'
ORACLE = 'scripts/prospectus_definition_binding_oracle.py'
TEST = 'tests/prospectus_successor/test_definition_bindings.py'
FILES = (PLAN, METHOD, WORKER, ORACLE, TEST)
TARGETS = tuple('src/legalmath/prospectus/successor/' + n for n in
                ('definition_bindings.py', 'service.py', 'conditional_profiles.py'))
STAGES = ('install', 'tests', 'consume', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def baseline():
    products = {k: read(ROOT / r['path']) for k, r in read(PRODUCTS)['products'].items()}
    answer = read(BASE / 'ordinary-answer.json.gz')
    freeze = read(DRAFT / 'cases-freeze.json')
    assert digest(products) == freeze['products_sha256'] and digest(answer) == freeze['original_answer_sha256']
    return products, answer


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    measured = start['prior']['combined_measured_seconds'] + extra
    measured += read(DRAFT / 'case-preparation.json')['wall_seconds']
    measured += read(PREP / 'recovery.json')['wall_seconds'] + read(PREP / 'synthetic-freeze.json')['wall_seconds']
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            measured += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged = start['prior']['conservative_extra_seconds'] + 90
    paths = {p for folder in (DRAFT, PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (*FILES, 'scripts/prospectus_definition_binding_prepare.py',
        'scripts/prospectus_definition_binding_cases.py', 'docs/plans/prospectus-definition-use-bindings-2026-10-19.md'))
    paths.add(AUTH / 'revisions/0331.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / n).stat().st_size - value) for n, value in start['production_bytes'].items() if (ROOT / n).exists())
    assert measured + charged < 18000 and size < 2684 * 1024**2, 'Cumulative definition-binding bound'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charged,
        'combined_accounted_seconds': measured + charged, 'combined_bytes': size,
        'seconds_bound': 18000, 'bytes_bound_with_4MiB_reserve': 2688 * 1024**2,
        'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [TEST, 'tests/prospectus_successor/test_definition_roles.py',
            'tests/prospectus_successor/test_conditional_profiles_cli.py',
            'tests/prospectus_successor/test_structural_context.py']


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 330
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 69 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for folder in (prior.HERE, BASE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, name
    freeze = read(DRAFT / 'cases-freeze.json')
    assert freeze['candidate_absent'] is True
    assert sha(DRAFT / 'expected-content.json') == freeze['expected_content_sha256']
    assert sha(prior.HERE / 'coverage.json') == freeze['source_matrix_sha256']
    assert sha(ROOT / ORACLE) == freeze['oracle_sha256']
    assert sha(PREP / 'synthetic-cases.json') == read(PREP / 'synthetic-freeze.json')['sha256']
    for name, value in read(prior.PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == value, 'Prior330 source freeze: ' + name
    products, ordinary = baseline()
    profile = read(DRAFT / 'profile.json')
    profile['expected_content_sha256'] = digest(read(DRAFT / 'expected-content.json'))
    assert profile['products_sha256'] == digest(products) and profile['ordinary_answer_sha256'] == digest(ordinary)
    save(PREP / 'profile.json', profile)
    manifest = read(AUTH / 'reviews/definition-roles-327/profiles.json')
    assert all(r['name'] != 'definition_bindings' for r in manifest['profiles'])
    manifest['profiles'].append({'name': 'definition_bindings', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    save(PREP / 'expected-identities.json', {'raw_file_sha256': sha(DRAFT / 'expected-content.json'),
        'semantic_content_sha256': profile['expected_content_sha256'], 'frozen_before_original_draft': True})
    (PREP / 'baseline').mkdir()
    installation = []
    for target in TARGETS:
        path, candidate = ROOT / target, PREP / 'candidate' / (ROOT / target).name
        ast.parse(candidate.read_text())
        if path.exists():
            shutil.copyfile(path, PREP / 'baseline' / path.name)
        installation.append({'target': target, 'before': sha(path) if path.exists() else None,
            'candidate': rel(candidate), 'after': sha(candidate)})
    save(PREP / 'installation.json', installation)
    bindings = {n: sha(ROOT / n) for n in (*CODE, *FILES, prior.METHOD, prior.LINKS,
        'scripts/prospectus_residual_coverage.py', 'pyproject.toml', *testfiles())}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for folder in (PREP, DRAFT) for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    for path in (prior.HERE / 'coverage.json', prior.HERE / 'outputs.json', BASE / 'ordinary-answer.json.gz',
                 BASE / 'outputs.json', PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    for row in manifest['profiles']:
        assert sha(ROOT / row['path']) == row['file_sha256']
        bindings[row['path']] = row['file_sha256']
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False})
    proposal = deepcopy(program)
    proposal['revision'] = 331
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Bind reviewed rule purposes to original definition/use identities after correcting premature unadmitted draft',
        definition_binding_repair={'review': rel(PREP), 'failed_draft': rel(DRAFT),
            'original_task_complete': False, 'accounted_seconds_bound': 18000,
            'bytes_bound_with_4MiB_reserve': 2688 * 1024**2, 'conservative_seconds': 795})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]
        + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 70
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 331
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify exact definition-use bindings through source and installed consumers; continue remaining original source coverage',
                stop_condition='70admissions;900s/160MiB forecast;18000accounted seconds/2688MiB with4MiB reserve;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS:
        proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 900,
        'bytes': snapshot['combined_bytes'] + 160 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 18000 and forecast['bytes'] < 2684 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Correct and preserve failed draft; admit staged exact definition-use binding repair',
                    'Preserve complete original answer and independently frozen expected content',
                    'Explicit cumulative extension retaining795 conservative seconds and all prior costs'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Frozen full-answer expectation and fresh installed equality',
            'promotion_veto': ['Lost use', 'Wrong purpose', 'Source forgery', 'Lost uncertainty', 'Wrong import'],
            'continuation_veto': ['Corrupt baseline', 'Frozen drift', 'Cumulative exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Other governing uses', 'General recall', 'Legal truth', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 69, 'new_maximum': 70,
            'retained_attempts': attempts, 'reason': '069reproduced missing exact rule-to-record/use links; failed unadmitted draft corrected before trial',
            'next_discriminating_check': 'Independent612association matrix with whole-answer and installed equality',
            'stop_condition': '900s/160MiB forecast;18000accounted seconds/2688MiB with4MiB reserve;no unchanged retry',
            'same_scope_authorization': 'User requested refreshed master and continued internally established general build'},
        'resource_revision': {'prior_accounted_seconds': 16200, 'new_accounted_seconds': 18000,
            'prior_bytes': 2432 * 1024**2, 'new_bytes': 2688 * 1024**2,
            'failure_reserve_bytes': 4 * 1024**2, 'prior_costs_reset': False}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 331, 'candidate_evaluated': False, 'forecast': forecast}


def tests():
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', **counts}


def cli_arguments(output):
    return ['prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
        '--output', str(HERE / output), '--mode', 'frozen', '--conditional-profiles', rel(PREP / 'profiles.json'),
        '--conditional-profiles-sha256', sha(PREP / 'profiles.json')]


def consume():
    from legalmath.prospectus.successor import definition_bindings as module
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', *cli_arguments('ordinary-answer.json')], 330)
    products, ordinary = baseline()
    actual, profile = read(HERE / 'ordinary-answer.json'), read(PREP / 'profile.json')
    result = oracle.verify(actual, ordinary, products, profile, read(DRAFT / 'expected-content.json'))
    save(HERE / 'independent-verification.json', result)
    save(HERE / 'verification.json', module.verify_answer(actual, ordinary, profile, products, ROOT,
         expected_profile_sha256=digest(profile)))
    return {**result, 'actual_cli': True, 'answer_sha256': digest(actual), **engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import definition_bindings as module
    products, ordinary = baseline()
    profile, actual = read(PREP / 'profile.json'), read(HERE / 'ordinary-answer.json.gz')
    expected = read(DRAFT / 'expected-content.json')
    refused = {}
    for kind in ('lost-original-use', 'lost-extra-use', 'wrong-purpose', 'false-completion', 'lost-question', 'lost-other-answer'):
        bad = deepcopy(actual)
        if kind == 'lost-original-use': bad[module.KEY]['uses'].pop(0)
        elif kind == 'lost-extra-use': bad[module.KEY]['uses'] = [u for u in bad[module.KEY]['uses'] if u['origin'] != 'SUPPLEMENTAL']
        elif kind == 'wrong-purpose':
            row = next(u for u in bad[module.KEY]['uses'] if u['record'].startswith('U06-') and u['start'] == 19119)
            row['disposition'], row['binding'] = 'BOUND_CONDITIONALLY', {'rule': 'makewhole'}
        elif kind == 'false-completion': bad[module.KEY]['all_governing_uses_established'] = True
        elif kind == 'lost-question': bad['questions']['Q1']['unresolved'].pop()
        else: bad['definition_role_projection']['changes'] = []
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try:
            oracle.verify(bad, ordinary, products, profile, expected)
        except AssertionError as error:
            refused[kind] = {'route': 'independent-whole-answer', 'reason': str(error)}
        else:
            raise AssertionError('Accepted ' + kind)
    for kind in ('profile-meaning', 'profile-record', 'profile-provenance', 'profile-completion', 'rehashed-answer',
                 'rehashed-source', 'reconstructed-record', 'reconstructed-rule', 'reconstructed-role', 'reconstructed-map'):
        pp, oo, pr = deepcopy(products), deepcopy(ordinary), deepcopy(profile)
        route = 'evaluate-with-rehashed-profile'
        if kind == 'profile-meaning': pr['expected_content_sha256'] = '0' * 64
        elif kind == 'profile-record': pr['record_rules']['U06-tax-early-amount'] = 'makewhole'
        elif kind == 'profile-provenance': pr['semantic_matrix_sha256'] = '0' * 64
        elif kind == 'profile-completion': pr['whole_task_complete'] = True
        elif kind == 'rehashed-answer': oo['questions']['Q1']['status'] = 'YES'
        elif kind == 'rehashed-source': pp['P2']['payload']['assembly']['continuous_text'] += 'x'
        elif kind == 'reconstructed-record': oo['definition_sources']['records'][0]['uses'].pop()
        elif kind == 'reconstructed-rule':
            pp['P3']['payload']['definition_sources']['application_supplement']['rules'][0]['record'] = 'U07-makewhole-early-amount'
        elif kind == 'reconstructed-role': oo['definition_sources']['source_pieces'][0]['assembly_uses'][0]['role'] = 'UNKNOWN'
        else:
            pp['P2']['payload']['assembly']['units'][0]['character_map'] = []
        oo['report_sha256'] = digest({k: v for k, v in oo.items() if k != 'report_sha256'})
        pr['ordinary_answer_sha256'], pr['products_sha256'] = digest(oo), digest(pp)
        try:
            if kind.startswith('reconstructed-'):
                route = 'registered-reconstruction-without-outer-pins'
                module._checked_report(pp, oo)
            else:
                module.evaluate(pp, oo, pr, ROOT, expected_profile_sha256=digest(pr))
        except ValueError as error:
            refused[kind] = {'route': route, 'reason': str(error)}
        else:
            raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused})
    return {'status': 'PASS', 'refused': len(refused)}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B',
        str(ROOT / WORKER), str(ROOT), str(HERE), str(PREP)], 330)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    answer = read(HERE / 'ordinary-answer.json.gz')
    counts = dict(Counter(u['disposition'] for u in answer[oracle.KEY]['uses']))
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'EXACT_PURPOSE_AWARE_DEFINITION_USE_BINDINGS', 'associations': counts,
        'original_associations': 610, 'supplemental_associations': 2,
        'independent_whole_answer_equal': True, 'installed_answer_equal': True, 'resources': costs(),
        'next_action': 'Continue remaining governing-use and original-reference acceptance work; preserve all explicit uncertainty'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'data_version': sha(PRODUCTS), 'seeds': 'N/A deterministic', 'wall_time': costs(),
        'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Exact purpose-aware definition bindings

The ordinary and freshly installed answers retain62definition records,
610original associations and2supplemental associations. Eleven links carry the
exact existing rule, meaning and qualification. The original report and every
other answer field remain unchanged. This is a finite conditional integration.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain additive use bindings|Complete pre-draft expectation and installed equality|Purpose/extent, forgery, omission and import checks passed|582uses still have no reconciled governing link; historical and factual premises remain|Continue original source coverage and acceptance|General legal interpretation, whole task or whole build|

The earlier premature installation and failed preparation were retained and
reversed exactly before admission. Their costs remain charged. The repaired
candidate resolves interval indirection, purpose identity and ordering errors.
The strongest alternative explanation for agreement is a shared error in the
reviewed source meaning. The tests establish correspondence to that source
review, not unrestricted correctness for unseen texts. A source counterexample
or a binding that loses a qualification would overturn this integration verdict.
''')
    return result


def bind_runner():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    engine.PREP, engine.HERE, engine.PLAN = PREP, HERE, PLAN
    engine.METHOD, engine.WORKER, engine.TARGETS = METHOD, WORKER, TARGETS
    engine.costs, engine.testfiles, engine.cli_arguments = costs, testfiles, cli_arguments


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS}})
    else:
        for before in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / before / 'result.json')['status'] == 'PASS'
        costs()
    bind_runner()
    bound = 90 if stage == 'prepare' else 360
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_binding', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition binding stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': engine.frozen(stage != 'install')
        result = (globals().get(stage) or getattr(engine, stage))()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error),
            'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
