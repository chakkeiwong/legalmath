"""Current definition-role repair under the existing prospectus authority."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import shutil
import signal
import sys
import time
from scripts import prospectus_source_coverage as audit
from scripts import prospectus_definition_role_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine, prior = audit.ROOT, audit.AUTH, audit.engine, audit.prior
PREP = AUTH / 'reviews/definition-roles-327'
HERE = AUTH / 'attempts/basf-references/attempt-066'
PLAN = 'docs/plans/prospectus-definition-current-roles-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_roles.py'
WORKER = 'scripts/prospectus_definition_roles_installed.py'
ORACLE = 'scripts/prospectus_definition_role_oracle.py'
TEST = 'tests/prospectus_successor/test_definition_roles.py'
FILES = (PLAN, METHOD, WORKER, ORACLE, TEST, 'scripts/prospectus_definition_role_cases.py')
TARGETS = ('src/legalmath/prospectus/successor/definition_roles.py',
           'src/legalmath/prospectus/successor/service.py',
           'src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS, STAGES = prior.PRODUCTS, prior.STAGES
read, save, sha, rel = audit.read, audit.save, audit.sha, audit.rel
baseline = audit.baseline


def testfiles():
    return [TEST, *prior.testfiles()]


def tests():
    import xml.etree.ElementTree as ET
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', 'independent_mapping_cases': True, **counts}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    seconds = start['prior']['combined_measured_seconds'] + read(PREP / 'case-preparation.json')['wall_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES)
    paths.add(AUTH / 'revisions/0327.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    if (PREP / 'production-bytes.json').exists():
        size += sum(max(0, (ROOT / n).stat().st_size - value) for n, value in read(PREP / 'production-bytes.json').items() if (ROOT / n).exists())
    assert seconds < 16200 and size < 2428 * 1024**2, 'Cumulative definition-role resource bound'
    return {'combined_measured_seconds': seconds, 'combined_bytes': size, 'prior_costs_reset': False,
            'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2,
            'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 326
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 65 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(audit.HERE) for e in events)
    for folder in (audit.HERE, prior.HERE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, name
    freeze = read(PREP / 'cases-freeze.json')
    assert sha(PREP / 'cases.json') == freeze['cases_sha256']
    assert sha(ROOT / freeze['method']) == freeze['method_sha256']
    assert sha(ROOT / freeze['plan']) == freeze['plan_sha256']
    cases = read(PREP / 'cases.json')
    assert sha(ROOT / cases['source_audit']) == cases['source_audit_sha256']
    assert cases['expected_original_changes'] == read(audit.HERE / 'coverage.json')['source_accounting']['retained_vs_current_roles']
    save(PREP / 'production-bytes.json', {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS})
    (PREP / 'candidate').mkdir()
    shutil.copyfile(PREP / 'candidate.py', PREP / 'candidate/definition_roles.py')
    products, ordinary = baseline()
    from legalmath.prospectus.successor.structural_roles import PROFILE_SHA256
    profile = {'version': 'definition-current-roles.v1', 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'structural_profile_sha256': PROFILE_SHA256,
        'legal_truth_established': False}
    save(PREP / 'profile.json', profile)
    text = (ROOT / TARGETS[1]).read_text()
    old = '            reference_roles_profile=None, expected_reference_roles_profile_sha256=None):'
    assert text.count(old) == 1
    text = text.replace(old, '            reference_roles_profile=None, expected_reference_roles_profile_sha256=None,\n'
        '            definition_roles_profile=None, expected_definition_roles_profile_sha256=None):')
    old = '    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new = '''    if definition_roles_profile is not None:
        from .definition_roles import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_roles_profile, root,
            expected_profile_sha256=expected_definition_roles_profile_sha256))
    elif expected_definition_roles_profile_sha256 is not None:
        raise ValueError('Definition-role profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(old) == 1
    (PREP / 'candidate/service.py').write_text(text.replace(old, new))
    text = (ROOT / TARGETS[2]).read_text()
    old = "'layout_labels', 'reference_roles')"
    assert text.count(old) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(text.replace(old, "'layout_labels', 'reference_roles', 'definition_roles')"))
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
    manifest = read(prior.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'definition_roles', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    bindings = {n: sha(ROOT / n) for n in (*CODE, *FILES, audit.METHOD, prior.METHOD, prior.WORKER, prior.ORACLE,
                                         engine.METHOD, engine.WORKER, 'pyproject.toml')}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in (audit.HERE / 'coverage.json', audit.HERE / 'outputs.json', prior.HERE / 'outputs.json',
                 prior.HERE / 'ordinary-answer.json.gz', prior.PREP / 'profiles.json', PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    for name in testfiles():
        bindings[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 327
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Correct 48 stale role labels in current definition provenance with exact prior/current history and no change of meaning',
        definition_roles={'review': rel(PREP), 'original_task_complete': False,
                          'combined_seconds': 16200, 'combined_bytes': 2432 * 1024**2})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 66
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 327
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify current definition provenance, then continue original governing-scope and unquoted-use analysis',
                stop_condition='66 admissions;360s stages;existing16200s/2432MiB;no new requests or unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS:
        proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    forecast = {'seconds': costs()['combined_measured_seconds'] + 900,
                'bytes': costs()['combined_bytes'] + 100 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 16200 and forecast['bytes'] < 2428 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Current role labels corrected with prior definition hash and exact changes; legal meaning retained'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Frozen audit tuples give exact complete-answer delta, actual mapping cases and normal/installed equality',
            'promotion_veto': ['Changed source or meaning', 'Unreviewed role', 'Lost provenance', 'Hidden answer change'],
            'continuation_veto': ['Corrupt source or baseline', 'Frozen drift', 'Resource exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Governing scope', 'Historical law', 'Automatic role discovery', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 65, 'new_maximum': 66,
            'retained_attempts': attempts,
            'reason': 'Complete source audit reproduced 48 stale role labels across44 reviewed current header occurrences',
            'next_discriminating_check': 'Only independently retained 48 role updates in complete normal/installed answer',
            'stop_condition': '360s stages;existing16200s/2432MiB;no requests or unchanged retry',
            'same_scope_authorization': 'User requested refreshed master and continued internally established general build'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 327, 'cases': len(cases['cases']), 'forecast': forecast}


def cli_arguments(output):
    return ['prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
        '--output', str(HERE / output), '--mode', 'frozen', '--conditional-profiles', rel(PREP / 'profiles.json'),
        '--conditional-profiles-sha256', sha(PREP / 'profiles.json')]


def consume():
    from legalmath.prospectus.successor import definition_roles as module
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', *cli_arguments('ordinary-answer.json')], 330)
    products, ordinary = baseline()
    actual, profile = read(HERE / 'ordinary-answer.json'), read(PREP / 'profile.json')
    verification = module.verify_answer(actual, ordinary, profile, products, ROOT, expected_profile_sha256=digest(profile))
    independent = oracle.verify(actual, ordinary, products, profile, read(PREP / 'cases.json')['expected_original_changes'])
    save(HERE / 'verification.json', verification)
    save(HERE / 'independent-verification.json', independent)
    return {'status': 'PASS', 'actual_cli': True, 'only_reviewed_role_delta': True,
        'answer_sha256': digest(actual), 'independent': independent, **engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import definition_roles as module
    products, ordinary = baseline()
    answer, profile = read(HERE / 'ordinary-answer.json.gz'), read(PREP / 'profile.json')
    refused = {}
    for kind in ('unregistered-roles', 'legal-truth', 'product-pin', 'stale-role', 'lost-history',
                 'false-scope', 'changed-quote', 'lost-prior', 'raw-source', 'current-map', 'current-role'):
        bad, actual = deepcopy(profile), deepcopy(answer)
        trial_products = products
        if kind == 'unregistered-roles': bad['structural_profile_sha256'] = '0' * 64
        elif kind == 'legal-truth': bad['legal_truth_established'] = True
        elif kind == 'product-pin': bad['products_sha256'] = '0' * 64
        elif kind == 'stale-role': actual['definition_sources']['source_pieces'][0]['assembly_uses'][0]['role'] = 'UNKNOWN'
        elif kind == 'lost-history': actual[module.KEY]['changes'] = []
        elif kind == 'false-scope': actual['definition_sources']['scope_admitted'] = True
        elif kind == 'changed-quote': actual['definition_sources']['source_pieces'][0]['text'] += 'x'
        elif kind == 'lost-prior': actual['reference_role_review']['legal_truth_established'] = True
        else:
            trial_products = deepcopy(products)
            identity = answer[module.KEY]['changes'][0]['unit']
            if kind == 'raw-source':
                unit = next(u for u in trial_products['P1']['payload']['graph']['units'] if u['id'] == identity)
                unit['raw'] += 'x'
            else:
                unit = next(u for u in trial_products['P2']['payload']['assembly']['units'] if u['unit'] == identity)
                if kind == 'current-map': unit['character_map'][0]['source']['start'] += 1
                else: unit['role'] = 'OPERATIVE'
            bad['products_sha256'] = digest(trial_products)
        actual['report_sha256'] = digest({k: v for k, v in actual.items() if k != 'report_sha256'})
        try:
            module.verify_answer(actual, ordinary, bad, trial_products, ROOT, expected_profile_sha256=digest(bad))
        except ValueError as error:
            refused[kind] = str(error)
        else:
            raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused})
    return {'status': 'PASS', 'refused': len(refused)}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER), str(ROOT), str(HERE)], 330)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'CURRENT_DEFINITION_PROVENANCE_ROLES', 'only_reviewed_role_delta': True,
        'installed_cli_equal': True, 'legal_truth_established': False,
        'resources': costs(), 'next_action': 'Continue original governing scope and unquoted/morphological-use analysis'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / stage / 'started.json')['command'] for stage in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; no GPU use',
        'seeds': 'N/A deterministic', 'data_version': sha(PREP / 'cases.json'), 'wall_time': costs(),
        'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Current definition provenance

The complete normal and installed answers correct the48stale occurrence-role
labels identified independently by audit065. All original text, intervals,
definitions,610use associations, meanings, questions and other conditional
results are retained. The current answer includes the old definition-report
hash, current assembly identity and exact old/new role list.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional current-role projection|Exact complete-answer delta from frozen065tuples; installed equality|Mapping/profile/result misuse refused|Governing scope and unseen sources|Original scope and use analysis|Legal meaning or whole-task acceptance|

Our structural-definition adaptation changed the assembly identity while
retaining old role metadata. This is a local integration defect. It is not
evidence of a limitation of any external package. The strongest alternative
interpretation is that those labels described historical roles; the projection
now explicitly retains that history while showing current roles. Misclassified
source headings would invalidate the role authority and require a separate
source review. This repair does not establish automatic role classification.
''')
    return result


def bind_runner():
    engine.PREP, engine.HERE, engine.PLAN = PREP, HERE, PLAN
    engine.METHOD, engine.WORKER, engine.TARGETS = METHOD, WORKER, TARGETS
    engine.costs, engine.testfiles, engine.cli_arguments = costs, testfiles, cli_arguments


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        assert not (PREP / 'accounting-start.json').exists()
        save(PREP / 'accounting-start.json', {'prior': audit.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    else:
        for before in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / before / 'result.json')['status'] == 'PASS'
        costs()
        bind_runner()
    bound = 90 if stage == 'prepare' else 360
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_roles', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition-role stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare':
            engine.frozen(stage != 'install')
        result = (globals().get(stage) or getattr(engine, stage))()
        if stage != 'prepare':
            engine.frozen()
        current = costs(time.monotonic() - start)
        if stage == 'prepare':
            assert current['combined_bytes'] - read(PREP / 'accounting-start.json')['prior']['combined_bytes'] < 128 * 1024**2
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
