"""Run the reviewed source-reference role trial under cumulative accounting."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import shutil
import signal
import sys
import time
from scripts import prospectus_layout_labels as prior
from scripts import prospectus_reference_role_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/reference-role-325'
HERE = AUTH / 'attempts/basf-references/attempt-064'
PLAN = 'docs/plans/prospectus-reference-role-execution-2026-10-19.md'
METHOD = 'scripts/prospectus_reference_roles.py'
WORKER = 'scripts/prospectus_reference_roles_installed.py'
ORACLE = 'scripts/prospectus_reference_role_oracle.py'
TEST = 'tests/prospectus_successor/test_reference_roles.py'
FILES = (PLAN, 'docs/plans/prospectus-reference-role-2026-10-19.md', METHOD, WORKER, ORACLE, TEST, 'scripts/prospectus_reference_role_cases.py',
         'docs/implementation/prospectus-execution-authority/reviews/post-324-gap-analysis.md')
TARGETS = ('src/legalmath/prospectus/successor/reference_roles.py',
           'src/legalmath/prospectus/successor/service.py',
           'src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS, STAGES = prior.PRODUCTS, prior.STAGES
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def baseline():
    manifest = read(PRODUCTS)
    products = {}
    for key, row in manifest['products'].items():
        path = ROOT / row['path']
        assert sha(path) == row['sha256']
        products[key] = read(path)
    answer = read(prior.HERE / 'ordinary-answer.json.gz')
    assert digest(answer) == '3b9a3556cbbf0b87b33401ecffa25eae68140f50dd217fd5346beb40bf5e7fd1'
    return products, answer


def testfiles():
    return [TEST, *prior.testfiles()]


def tests():
    import xml.etree.ElementTree as ET
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', 'independent_graph_oracle': True, **counts}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    seconds = start['prior']['combined_measured_seconds'] + read(PREP / 'case-preparation.json')['wall_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES)
    paths.add(AUTH / 'revisions/0325.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    if (PREP / 'production-bytes.json').exists():
        size += sum(max(0, (ROOT / n).stat().st_size - value) for n, value in read(PREP / 'production-bytes.json').items() if (ROOT / n).exists())
    assert seconds < 16200 and size < 2428 * 1024**2, 'Combined retained resource bound'
    return {'combined_measured_seconds': seconds, 'combined_bytes': size,
        'prior_costs_reset': False, 'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2,
        'previous_seconds_bound': 14400, 'previous_bytes_bound': 2304 * 1024**2,
        'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 324
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 63 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for name, checksum in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == checksum, name
    freeze = read(PREP / 'cases-freeze.json')
    assert sha(PREP / 'cases.json') == freeze['cases_sha256']
    assert sha(PREP / 'source-review.json') == freeze['source_review_sha256']
    assert sha(ROOT / freeze['method']) == freeze['method_sha256']
    assert sha(ROOT / freeze['plan']) == freeze['plan_sha256']
    for path, checksum in freeze['source_files'].items():
        assert sha(ROOT / path) == checksum
    save(PREP / 'production-bytes.json', {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS})
    (PREP / 'candidate').mkdir()
    shutil.copyfile(PREP / 'candidate.py', PREP / 'candidate/reference_roles.py')
    products, ordinary = baseline()
    sources = read(PREP / 'source-review.json')
    assert sources['products_sha256'] == digest(products) and sources['ordinary_answer_sha256'] == digest(ordinary)
    profile = {'version': 'reference-role-review.v1', 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'source_review': sources,
        'scope_references': ['reviewed-reference:holder-option-self-scope', 'reviewed-reference:substitution-whole-scope'],
        'legal_truth_established': False}
    save(PREP / 'profile.json', profile)
    text = (ROOT / TARGETS[1]).read_text()
    old = '            layout_labels_profile=None, expected_layout_labels_profile_sha256=None):'
    assert text.count(old) == 1
    text = text.replace(old, '            layout_labels_profile=None, expected_layout_labels_profile_sha256=None,\n'
        '            reference_roles_profile=None, expected_reference_roles_profile_sha256=None):')
    old = '    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new = '''    if reference_roles_profile is not None:
        from .reference_roles import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['reference_role_review'] = evaluate(products, baseline, reference_roles_profile, root,
            expected_profile_sha256=expected_reference_roles_profile_sha256)
    elif expected_reference_roles_profile_sha256 is not None:
        raise ValueError('Reference-role profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess('''
    assert text.count(old) == 1
    (PREP / 'candidate/service.py').write_text(text.replace(old, new))
    text = (ROOT / TARGETS[2]).read_text()
    old = "'payment_categories', 'layout_labels')"
    assert text.count(old) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(text.replace(old, "'payment_categories', 'layout_labels', 'reference_roles')"))
    (PREP / 'baseline').mkdir()
    installation = []
    for target in TARGETS:
        path = ROOT / target
        candidate = PREP / 'candidate' / path.name
        ast.parse(candidate.read_text())
        if path.exists():
            shutil.copyfile(path, PREP / 'baseline' / path.name)
        installation.append({'target': target, 'before': sha(path) if path.exists() else None,
                             'candidate': rel(candidate), 'after': sha(candidate)})
    save(PREP / 'installation.json', installation)
    manifest = read(prior.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'reference_roles', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    bindings = {n: sha(ROOT / n) for n in (*CODE, *FILES, prior.METHOD, prior.WORKER, prior.ORACLE,
                                         engine.METHOD, engine.WORKER, 'pyproject.toml')}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in (prior.HERE / 'outputs.json', prior.HERE / 'ordinary-answer.json.gz', prior.PREP / 'profiles.json', PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    for name in testfiles():
        bindings[name] = sha(ROOT / name)
    bindings.update(freeze['source_files'])
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 325
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Distinguish two inspected source-scope links from dependency cycles while retaining every original reference and uncertainty',
        reference_roles={'review': rel(PREP), 'original_task_complete': False,
                         'combined_seconds': 16200, 'combined_bytes': 2432 * 1024**2})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 64
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 325
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify source-role graph analysis and complete consumers; then return to remaining original scope and source coverage',
                stop_condition='64 admissions;360s stages;combined16200s/2432MiB;prior14400s/2304MiB retained;no new requests or unchanged retry')
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
        'changes': ['Explicit source-role analysis preserves original conservative answer and complete reference reachability'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Independent graph/source reconstruction and complete ordinary/installed answers',
            'promotion_veto': ['Lost source edge', 'Hidden real cycle', 'Unreviewed classification', 'Lost prior answer'],
            'continuation_veto': ['Corruption', 'Method drift', 'Resource exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Automatic role discovery', 'Recursive legal semantics', 'Historical applicability', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 63, 'new_maximum': 64,
            'retained_attempts': attempts,
            'reason': 'Actual original graph conflates two inspected scope relations with cyclic support; the next discriminating full consumer trial exceeds the remaining old time allowance',
            'next_discriminating_check': 'All original graph reachability and uncertainty preserved with independently checked source/dependency components',
            'stop_condition': '360s stages;16200s/2432MiB combined;no new requests or unchanged retry',
            'same_scope_authorization': 'User requested refreshed master and continued internally established general build'},
        'resource_revision': {'previous_seconds': 14400, 'new_seconds': 16200,
            'previous_bytes': 2304 * 1024**2, 'new_bytes': 2432 * 1024**2,
            'retained_costs': costs(), 'new_forecast': forecast, 'prior_costs_reset': False}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 325, 'cases': len(read(PREP / 'cases.json')['cases']), 'forecast': forecast}


def cli_arguments(output):
    return ['prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
        '--output', str(HERE / output), '--mode', 'frozen', '--conditional-profiles', rel(PREP / 'profiles.json'),
        '--conditional-profiles-sha256', sha(PREP / 'profiles.json')]


def consume():
    from legalmath.prospectus.successor import reference_roles as module
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', *cli_arguments('ordinary-answer.json')], 330)
    products, ordinary = baseline()
    actual, profile = read(HERE / 'ordinary-answer.json'), read(PREP / 'profile.json')
    verification = module.verify_answer(actual, ordinary, profile, products, ROOT, expected_profile_sha256=digest(profile))
    graphs = oracle.source_graphs(products)
    assert module.source_graphs(products) == graphs, 'Independent complete graph reconstruction differs'
    proofs = {}
    for question, graph in graphs.items():
        scopes = [e['id'] for e in graph['edges'] if e['id'].rsplit('#', 1)[0] in profile['scope_references']]
        proofs[question] = oracle.verify(graph, scopes, actual[module.KEY]['questions'][question])
    save(HERE / 'verification.json', verification)
    save(HERE / 'graph-verification.json', proofs)
    return {'status': 'PASS', 'actual_cli': True, 'baseline_unchanged': True,
        'answer_sha256': digest(actual), 'graphs': proofs, **engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import reference_roles as module
    products, ordinary = baseline()
    answer, profile = read(HERE / 'ordinary-answer.json.gz'), read(PREP / 'profile.json')
    refused = {}
    for kind in ('unreviewed-scope', 'missing-scope', 'source-reading', 'source-target', 'source-edition',
                 'legal-truth', 'product-pin', 'false-cycle-result', 'lost-prior'):
        bad, actual = deepcopy(profile), deepcopy(answer)
        if kind == 'unreviewed-scope': bad['scope_references'].append('reviewed-reference:temporary-global-self-scope')
        elif kind == 'missing-scope': bad['scope_references'] = []
        elif kind == 'source-reading': bad['source_review']['readings'][0]['reading']['role'] = 'TRUE_EVENT'
        elif kind == 'source-target': bad['source_review']['readings'][0]['reference']['targets'].pop()
        elif kind == 'source-edition': bad['source_review']['readings'][0]['reference']['source']['source_sha256'] = '0' * 64
        elif kind == 'legal-truth': bad['legal_truth_established'] = True
        elif kind == 'product-pin': bad['products_sha256'] = '0' * 64
        elif kind == 'false-cycle-result': actual[module.KEY]['questions']['Q1']['dependency_cycles'] = []
        else: actual['layout_label_review']['scope_admitted'] = True
        actual['report_sha256'] = digest({k: v for k, v in actual.items() if k != 'report_sha256'})
        try:
            if kind in ('false-cycle-result', 'lost-prior'):
                module.verify_answer(actual, ordinary, bad, products, ROOT, expected_profile_sha256=digest(bad))
            else:
                module.evaluate(products, ordinary, bad, ROOT, expected_profile_sha256=digest(bad))
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
        'result_kind': 'CONDITIONAL_SOURCE_REFERENCE_ROLES', 'baseline_unchanged': True,
        'installed_cli_equal': True, 'legal_truth_established': False,
        'resources': costs(), 'next_action': 'Continue original scope, source authority and generalization obligations'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / stage / 'started.json')['command'] for stage in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PREP / 'cases.json'), 'wall_time': costs(),
        'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Explicit source roles and reference cycles

The normal and installed consumers retain the original answer and add a
conditional graph analysis of two inspected source-scope references. Full
reference reachability, missing targets, unresolved edges and unsupported
priority remain. Real dependency cycles reached through a scope link remain
visible. This distinguishes graph roles without deciding recursive legal rules.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional reviewed-role analysis|Independent graph/source reconstruction and complete ordinary/installed answers|Source/role/result misuse refused|Classification on unreviewed text and remaining semantic cycles|Original scope and source coverage|Automatic interpretation or whole build|

The limitation arose in our uniform reference-edge representation. This result
does not show a defect in an external package. A reference may have mixed scope
and substantive content; that remains the strongest reason not to generalize
these two supplied classifications automatically.
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
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    else:
        for before in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / before / 'result.json')['status'] == 'PASS'
        costs()
        bind_runner()
    bound = 90 if stage == 'prepare' else 360
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reference_roles', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Reference-role stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare':
            engine.frozen(stage != 'install')
        result = (globals().get(stage) or getattr(engine, stage))()
        if stage != 'prepare':
            engine.frozen()
        current = costs(time.monotonic() - start)
        if stage == 'prepare':
            assert current['combined_measured_seconds'] < 14400, 'Preparation exceeds original time allowance'
            assert current['combined_bytes'] - read(PREP / 'accounting-start.json')['prior']['combined_bytes'] < 128 * 1024**2, 'Proposal preparation bytes exceeded'
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
