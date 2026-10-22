"""Bounded additive current H1 relationship delivery, with retained prior answer."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_combined_consumer as prior
from scripts import prospectus_h1_current_relationships_mapping as mapping

common = prior.common
read, save, require, sha, digest, rel = common.read, common.save, common.require, common.sha, common.digest, common.rel
AUTH, BASE = prior.AUTH, prior.BASE
HERE = BASE / 'attempt-064'
PREP = AUTH / 'reviews/h1-current-relationships-427'
AUDIT = ROOT / '.localresources/prospectus-preparation/h1-current-source-audit'
SELF = 'scripts/prospectus_h1_current_relationships.py'
MAPPING = 'scripts/prospectus_h1_current_relationships_mapping.py'
PLAN = 'docs/plans/prospectus-h1-current-relationships-2026-10-22.md'
TESTS = ['tests/prospectus/test_h1_incorporation_scope.py', 'tests/prospectus/test_h1_unit_conflict.py']
MUTABLE = {mapping.MODULE, mapping.WRAPPER}
DEPENDENCIES = {'source': [], 'implement': ['source'], 'tests': ['implement'],
    'ordinary': ['tests'], 'compare': ['ordinary'], 'legacy': ['compare'],
    'package': ['legacy'], 'installed': ['package'], 'installed-compare': ['installed'],
    'installed-legacy': ['installed-compare']}
for case in mapping.CASES:
    DEPENDENCIES['control-' + case] = ['compare']
    DEPENDENCIES['installed-control-' + case] = ['installed-compare', 'control-' + case]
DEPENDENCIES['coverage'] = []
ADDED = {'h1_source_relationship_review', 'h1_source_relationship_explanation'}


def costs(reserve=0, seconds_reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE, AUDIT) if folder.exists() for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (SELF, MAPPING, PLAN, mapping.TEMPLATE,
        'scripts/prospectus_h1_association_audit.py', 'scripts/prospectus_h1_current_coverage.py',
        'docs/plans/prospectus-h1-current-source-audit-2026-10-22.md', mapping.MODULE))
    paths.add(AUTH / 'revisions/0427.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (ROOT / mapping.WRAPPER).stat().st_size - start['wrapper_bytes'])
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    receipts = [read(p) for folder in (PREP, HERE) for p in folder.glob('commands/*.json')]
    seconds = sum(p['wall_seconds'] for p in receipts if p.get('accounting_role') != 'NESTED_IN_PARENT')
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes'] + size,
        'known_cumulative_seconds': start['prior_known_seconds'] + seconds + 60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size + reserve < 252 * 1024**2 and seconds + seconds_reserve < 1200}


def prepare():
    tick = time.monotonic()
    auth = common.authority()
    old = read(AUTH / 'program.json')
    require(old['revision'] == 426 and not PREP.exists() and not HERE.exists(), 'Fresh revision 426 required')
    attempts = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-bes-dep-05']
    require(len(attempts) == old['budgets']['source-bes-dep-05']['maximum_new_attempts'] == 63, 'Retain 63 admissions')
    manifest = read(prior.HERE / 'outputs.json')
    require(read(prior.HERE / 'result.json')['status'] == 'PASS', 'Sealed 063 PASS required')
    require(any(e.get('attempt') == rel(prior.HERE) and e.get('outputs_sha256') == sha(prior.HERE / 'outputs.json')
        for e in auth.events()), 'Recorded 063 required')
    require(all(sha(prior.HERE / n) == v for n, v in manifest.items()), 'Changed sealed 063')
    production = common.production()
    require(production == read(prior.PREP / 'freeze.json')['production'], 'Current 063 production changed')
    require(not (ROOT / mapping.MODULE).exists(), 'Relationship module already exists')
    audit = read(AUDIT / 'associations-063.json')
    require(audit['status'] == 'SUPPLIED_ASSOCIATIONS_CHECKED_CURRENT_LINK_GAPS_RETAINED'
        and audit['production_changed'] is False, 'Successful source association diagnostic required')
    for key in ('original_graph', 'actual_answer', 'inventory', 'source_review', 'reviewed_equity_image', 'method'):
        require(sha(ROOT / audit[key]['path']) == audit[key]['sha256'], 'Changed association evidence ' + key)
    previous = prior.costs()
    save(PREP / 'accounting-start.json', {'prior_known_bytes': previous['known_cumulative_bytes'],
        'prior_known_seconds': previous['known_cumulative_seconds'], 'prior_cost_receipt': previous,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'wrapper_bytes': (ROOT / mapping.WRAPPER).stat().st_size})
    for name in ('snapshot-062.json', 'snapshot-063.json', 'associations-063.json'):
        receipt = read(AUDIT / name)
        save(PREP / 'commands' / name, {'wall_seconds': receipt['seconds'],
            'command': ['timeout', '120', '.venv/bin/python', '-B', '-m',
                'scripts.prospectus_h1_association_audit' if name.startswith('associations') else 'scripts.prospectus_h1_current_coverage',
                *([] if name.startswith('associations') else [str(receipt['snapshot_attempt'])])]})
    config = read(prior.PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256']
        and sha(config['ordinary_python']) == config['ordinary_python_sha256'], 'Interpreter changed')
    save(PREP / 'config.json', config)
    products = read(prior.HERE / 'products.json.gz')
    baseline = read(prior.HERE / 'ordinary-answer.json.gz')
    value = mapping.profile(products['P1']['payload']['graph'], baseline, audit)
    save(PREP / 'profile.json', value)
    candidates = mapping.candidates(value)
    candidate_hashes = {}
    for name, text in candidates.items():
        ast.parse(text)
        path = PREP / 'candidate' / Path(name).name
        path.parent.mkdir(exist_ok=True)
        with path.open('x') as stream:
            stream.write(text)
        candidate_hashes[name] = sha(path)
    candidate_production = production | candidate_hashes
    save(PREP / 'candidate-production.json', candidate_production)
    shutil.copyfile(ROOT / mapping.WRAPPER, PREP / 'baseline-wrapper.py')
    # A direct candidate check is preparation; the admitted trial still must
    # invoke the real public consumer and an installed package.
    spec = importlib.util.spec_from_file_location('legalmath.prospectus._candidate_relationships', PREP / 'candidate/h1_source_relationships.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.evaluate(products['P1']['payload']['graph'], baseline, value, expected_profile_sha256=digest(value))
    proof = mapping.verify(baseline | {'h1_source_relationship_review': result,
        'h1_source_relationship_explanation': module.explain(result)}, baseline, value, audit)
    require(common.production() == production, 'Preparation changed production')
    save(PREP / 'preparation-check.json', {'status': 'PASS', 'checks': proof, 'production_changed': False})
    bindings = {n: v for n, v in read(prior.PREP / 'freeze.json')['bindings'].items() if n not in MUTABLE}
    bindings.update({rel(prior.HERE / n): v for n, v in manifest.items()})
    names = [SELF, MAPPING, PLAN, mapping.TEMPLATE, rel(prior.HERE / 'outputs.json'),
        'scripts/prospectus_h1_association_audit.py', 'scripts/prospectus_h1_current_coverage.py',
        'docs/plans/prospectus-h1-current-source-audit-2026-10-22.md', 'pyproject.toml', *TESTS]
    names.extend(rel(p) for p in AUDIT.rglob('*') if p.is_file())
    names.extend(rel(p) for p in PREP.rglob('*') if p.is_file() and 'commands' not in p.parts and p.name != 'accounting-start.json')
    bindings.update({n: sha(ROOT / n) for n in names})
    require(all(sha(ROOT / n) == v for n, v in bindings.items()), 'Stale inherited input')
    save(PREP / 'freeze.json', {'bindings': bindings, 'baseline_production': production,
        'candidate_production': candidate_production, 'mutable_files': sorted(MUTABLE),
        'implementation_window': 'Once in admitted implement stage'})
    new = deepcopy(old)
    new['revision'] = 427
    task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Deliver exact current source and equity-note relationships while preserving complete 063 and unresolved reconciliation')
    task['inputs'] = sorted((set(task['inputs']) - MUTABLE) | set(bindings) | {rel(PREP / 'freeze.json')})
    bounds = {'measured_seconds': 1200, 'control_seconds': 60, 'new_bytes': 256 * 1024**2,
        'failure_reserve': 4 * 1024**2, 'worker_seconds': 120, 'large_file_bytes': 32 * 1024**2,
        'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0}
    task['current_h1_relationships'] = {'version': mapping.VERSION, 'freeze': rel(PREP / 'freeze.json'),
        'bounds': bounds, 'success_dependencies': DEPENDENCIES, 'original_task_acceptance': False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 64
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 427
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=common.compact_digest(task), dossier=PLAN, phase=0,
                remaining='Complete 063 retained; current links, wider source/reference meaning and authority remain.',
                next_action='Execute additive relationship public/installed delivery, retain actual gap report and continue original source review.',
                stop_condition='Retain 63 admissions; attempt64 only; 1200+60 seconds and256MiB; no unchanged retries; source truth not established.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in MUTABLE:
        new['continuation_review']['bindings'].pop(name, None)
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'), rel(PREP / 'baseline-wrapper.py'))})
    require(old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract'], 'Original scope changed')
    raw = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    source_bytes = sum((ROOT / n).stat().st_size for n in production)
    forecast = costs()['new_bytes'] + 2 * len(raw) + 4 * source_bytes + 2 * 32 * 1024**2 + 8 * 1024**2
    require(forecast < 252 * 1024**2, 'Storage forecast exceeds reservation')
    public_seconds = read(prior.HERE / 'commands/ordinary.json')['wall_seconds']
    time_forecast = 20 * (public_seconds + 8) + 180
    require(time_forecast < 1200, 'Time forecast exceeds reservation')
    with (PREP / 'proposal.json').open('xb') as stream:
        stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Optional public source relationship review', 'Exact original 063 preserved',
            '38 residual associations and10 equity-note links; no inferred financial reconciliation'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'forecast_measured_seconds': time_forecast, 'source_specific_whitelist_not_automatic_interpretation': True},
        'evidence_contract': {'question': 'Do reviewed current links reach the actual public answer without changing063?',
            'baseline': rel(prior.HERE / 'ordinary-answer.json.gz'),
            'primary': 'Whole063 preservation, audited relationships, normal/installed equality and matched adverse refusals',
            'promotion_veto': ['Lost prior field', 'Wrong source/target', 'Accepted corruption', 'Wrong import'],
            'continuation_veto': ['Invalid authority', 'Corrupted originals', 'Exhausted resources'],
            'not_concluded': ['Financial reconciliation', 'Source authenticity', 'Legal truth', 'Automatic capability', 'Whole build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 63, 'new_maximum': 64,
            'retained_attempts': attempts, 'reason': 'Diagnosed current source-link representation gap in original obligation',
            'next_discriminating_check': 'Actual optional public relationship review with independent association comparison',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP / 'commands/preparation.json', {'wall_seconds': time.monotonic() - tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_current_relationships', 'prepare']})
    return {'status': 'PREPARED', 'revision': 427, 'forecast_new_bytes': forecast,
        'forecast_measured_seconds': time_forecast, 'resources': costs()}


def frozen():
    auth = common.authority()
    admission = read(HERE / 'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH / 'program.json')) == admission['program_sha256']
        and auth.binding(admission['task_spec']) == admission['binding'], 'Admission changed')
    freeze = read(PREP / 'freeze.json')
    require(all(sha(ROOT / n) == v for n, v in freeze['bindings'].items()), 'Frozen evidence changed')
    candidate = (HERE / 'implemented.json').exists()
    require(common.production() == freeze['candidate_production' if candidate else 'baseline_production'],
        'Production outside implementation window')
    config = read(PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256']
        and sha(config['ordinary_python']) == config['ordinary_python_sha256'], 'Interpreter changed')


def command(name, argv, timeout=120, nested=False):
    require(costs(32 * 1024**2, timeout)['execution_allowed'], 'Reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    tick = time.monotonic()
    folder = HERE / 'commands'
    folder.mkdir(exist_ok=True)
    process, error = None, None
    try:
        with (folder / (name + '.log')).open('x') as stream:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONNOUSERSITE': '1', 'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT),
                    'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
            save(folder / (name + '-started.json'), {'command': argv, 'identity': process_identity(process.pid),
                'at': datetime.now(timezone.utc).isoformat(), 'timeout_seconds': timeout, 'wall_seconds': 0})
            process.wait(timeout=timeout)
        require(process.returncode == 0, 'Inspect ' + name + '.log')
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(folder / (name + '.json'), {'command': argv, 'wall_seconds': time.monotonic() - tick,
        'exit_code': None if process is None else process.returncode, 'error': error,
        'accounting_role': 'NESTED_IN_PARENT' if nested else 'MEASURED_STAGE'})
    require(error is None, 'Command failed: ' + str(error))
    require(costs()['execution_allowed'], 'Post-command limit exceeded')


def load_inputs():
    return (read(prior.HERE / 'products.json.gz'), read(prior.HERE / 'profiles.json.gz'),
        read(PREP / 'profile.json'), read(prior.HERE / 'ordinary-answer.json.gz'),
        read(AUDIT / 'associations-063.json'))


def imports(kind):
    location = HERE / 'installed' if kind.startswith('installed') else ROOT / 'src'
    modules = {n: m.__file__ for n, m in sys.modules.items()
        if n.startswith('legalmath') and getattr(m, '__file__', None)}
    require(modules and all(Path(p).resolve().is_relative_to(location) for p in modules.values()), 'Wrong imported package origin')
    return modules


def source_worker():
    products, _, value, baseline, audit = load_inputs()
    require(value == mapping.profile(products['P1']['payload']['graph'], baseline, audit), 'Reviewed profile changed')
    spec = importlib.util.spec_from_file_location('legalmath.prospectus._candidate_relationships', PREP / 'candidate/h1_source_relationships.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reviewed = module.evaluate(products['P1']['payload']['graph'], baseline, value, expected_profile_sha256=digest(value))
    proof = mapping.verify(baseline | {'h1_source_relationship_review': reviewed,
        'h1_source_relationship_explanation': module.explain(reviewed)}, baseline, value, audit)
    save(HERE / 'source.json', {'status': 'PASS', 'checks': proof, 'audit': common.ref(AUDIT / 'associations-063.json')})


def implement_worker():
    require(common.production() == read(PREP / 'freeze.json')['baseline_production'], 'Baseline changed before implementation')
    require(not (ROOT / mapping.MODULE).exists(), 'New module already present')
    for name in sorted(MUTABLE):
        shutil.copyfile(PREP / 'candidate' / Path(name).name, ROOT / name)
    require(common.production() == read(PREP / 'candidate-production.json'), 'Installed candidate differs')
    save(HERE / 'implemented.json', {'status': 'PASS', 'production': read(PREP / 'candidate-production.json')})


def answer_worker(kind):
    products, profiles, value, baseline, audit = load_inputs()
    answer = mapping.consume(products, profiles, value)
    proof = mapping.verify(answer, baseline, value, audit)
    raw = gzip.compress(common.encoded(answer), compresslevel=1, mtime=0)
    require(len(raw) < 32 * 1024**2, 'Answer exceeds reservation')
    path = HERE / (kind + '-answer.json.gz')
    with path.open('xb') as stream:
        stream.write(raw)
    save(HERE / (kind + '.json'), {'status': 'PASS', 'answer_sha256': digest(answer),
        'answer_file': common.ref(path), 'checks': proof, 'imports': imports(kind), 'actual_public_consumer': True})


def checked_answer(kind):
    receipt = read(HERE / (kind + '.json'))
    path = HERE / (kind + '-answer.json.gz')
    require(sha(path) == receipt['answer_file']['sha256'], 'Saved answer bytes changed')
    answer = read(path)
    require(digest(answer) == receipt['answer_sha256'], 'Saved answer content changed')
    return answer


def compare_worker(kind):
    installed = kind.startswith('installed')
    answer = checked_answer('installed' if installed else 'ordinary')
    _, _, value, baseline, audit = load_inputs()
    proof = mapping.verify(answer, baseline, value, audit)
    if installed:
        require(answer == checked_answer('ordinary'), 'Installed answer differs')
    refusals = []
    for case in ('lost-prior', 'missing-link', 'invented-reconciliation', 'changed-explanation'):
        bad = dict(answer)
        if case == 'lost-prior':
            del bad['h1_individual_unit_review']
        elif case == 'changed-explanation':
            bad['h1_source_relationship_explanation'] = {**answer['h1_source_relationship_explanation'],
                'financial_reconciliation': 'The source values have been reconciled.'}
        else:
            bad['h1_source_relationship_review'] = deepcopy(answer['h1_source_relationship_review'])
            if case == 'missing-link':
                bad['h1_source_relationship_review']['relationships'].pop()
            else:
                bad['h1_source_relationship_review']['limits']['financial_reconciliation_established'] = True
        try:
            mapping.verify(bad, baseline, value, audit)
        except ValueError as exc:
            require(str(exc) in ('Complete 063 answer changed', 'Current source relationship result differs',
                'Required source relationship explanation differs'), 'Unexpected comparator refusal')
            refusals.append({'case': case, 'refused': True, 'reason': str(exc)})
        else:
            raise ValueError('Comparator accepted ' + case)
    save(HERE / (kind + '.json'), {'status': 'PASS', 'checks': proof, 'refusals': refusals, 'imports': imports(kind)})


def legacy_worker(kind):
    products, profiles, _, baseline, _ = load_inputs()
    answer = prior.support.consume(products, profiles)
    require(answer == baseline, 'Existing public call behavior changed')
    save(HERE / (kind + '.json'), {'status': 'PASS', 'complete_063_preserved': True,
        'answer_sha256': digest(answer), 'imports': imports(kind)})


def control_worker(kind):
    case = kind.removeprefix('installed-').removeprefix('control-')
    products, profiles, value, _, _ = load_inputs()
    try:
        mapping.consume(products, profiles, value, case)
    except ValueError as exc:
        require(str(exc) == mapping.REFUSALS[case], 'Unexpected public refusal: ' + str(exc))
        result = {'status': 'PASS', 'case': case, 'refused': True, 'reason': str(exc)}
    else:
        raise ValueError('Public consumer accepted ' + case)
    if kind.startswith('installed'):
        old = read(HERE / ('control-' + case + '.json'))
        require(result == {k: v for k, v in old.items() if k != 'imports'}, 'Installed refusal differs')
    save(HERE / (kind + '.json'), result | {'imports': imports(kind)})


def package_worker():
    source = HERE / 'package-source'
    source.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '*.egg-info'))
    python = read(PREP / 'config.json')['package_python']
    command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
        '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)], 60, nested=True)
    wheels = list((HERE / 'wheel').glob('*.whl'))
    require(len(wheels) == 1, 'Exactly one wheel required')
    expected = {n.removeprefix('src/legalmath/'): v for n, v in read(PREP / 'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): digest(archive.read(n)) for n in archive.namelist()
            if n.startswith('legalmath/') and not n.endswith('/')}
    require(actual == expected, 'Built wheel differs from candidate')
    command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
        '--target', str(HERE / 'installed'), str(wheels[0])], 60, nested=True)
    folder = HERE / 'installed/legalmath'
    require({str(p.relative_to(folder)): sha(p) for p in folder.rglob('*') if p.is_file()} == expected,
        'Installed bytes differ from candidate')
    save(HERE / 'package.json', {'status': 'PASS', 'wheel': common.ref(wheels[0]), 'files': expected})


def coverage_worker():
    rows = deepcopy(read(prior.HERE / 'requirements.json')['rows'])
    for row in rows:
        if row.get('status', '').startswith('THIS_ATTEMPT'):
            row.update(status='RETAINED_FINITE_DELIVERY', evidence=common.ref(prior.HERE / 'result.json'))
    rows.append({'requirement': 'Explicit current source relationships and equity-note targets',
        'status': 'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'})
    save(HERE / 'requirements.json', {'rows': rows, 'original_task_acceptance': False,
        'next_discriminating_work': 'Inspect wider current cross-reference availability and source-meaning obligations; do not treat this48-link supplied map as general interpretation.'})
    save(HERE / 'remaining.json', {'current_relationships': '38 residual associations and10 equity references only',
        'remaining': ['Wider statement and note reference relationships', 'Substantive completeness of supplied source readings',
            'Clipped equity totals/currency', 'Individual unit conflict', 'Source authority and controlling-language priority',
            'Conditional incorporation selection', 'General automatic capability and original acceptance'],
        'external_adviser_opinion_required': False})


def stage(name):
    require(name in DEPENDENCIES and not (HERE / 'stages' / name).exists(), 'Unknown or already-started stage')
    for parent in DEPENDENCIES[name]:
        require(read(HERE / 'stages' / parent / 'result.json')['status'] == 'PASS', 'Failed predecessor: ' + parent)
    frozen()
    require(costs(46 * 1024**2 if name == 'package' else 32 * 1024**2, 120)['execution_allowed'], 'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE / 'stages' / name / 'started.json', {'identity': process_identity(os.getpid()),
        'at': datetime.now(timezone.utc).isoformat(), 'stage': name})
    error = None
    try:
        if name == 'tests':
            command(name, [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', *TESTS,
                '--junitxml=' + str(HERE / 'tests.xml')])
        else:
            python = read(PREP / 'config.json')['package_python'] if name.startswith('installed') else str(ROOT / '.venv/bin/python')
            command(name, [python, '-I', '-B', str(ROOT / SELF), 'worker-' + name])
        frozen()
    except Exception as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(HERE / 'stages' / name / 'result.json', {'status': 'FAIL' if error else 'PASS', 'error': error})
    return {'stage': name, 'status': 'FAIL' if error else 'PASS', 'error': error, 'resources': costs()}


def finalize():
    require(not (HERE / 'outputs.json').exists(), 'Already sealed')
    for started in (HERE / 'stages').glob('*/started.json'):
        require((started.parent / 'result.json').exists(), 'Recover unresolved started worker first')
    outcomes = {name: read(HERE / 'stages' / name / 'result.json')['status']
        if (HERE / 'stages' / name / 'result.json').exists() else 'BLOCKED' for name in DEPENDENCIES}
    passed = all(v == 'PASS' for v in outcomes.values())
    if passed:
        frozen()
    save(HERE / 'result.json', {'task': 'source-bes-dep-05', 'status': 'PASS' if passed else 'FAIL',
        'stages': outcomes, 'task_complete': False, 'whole_program_complete': False,
        'build_criteria_claimed': [], 'resources': costs()})
    (HERE / 'RESULT.md').write_text('# Current H1 source relationships\n\n'
        + ('The optional public consumer delivered all 48 reviewed links in ordinary and installed calls. '
            'Both preserve the complete 063 answer; old calls also return the complete 063 answer unchanged. '
            'Eight adverse public cases in each environment and four comparator corruptions were refused.\n\n'
            if passed else 'The trial did not pass. Actual stage results identify the failure and blocked dependants.\n\n')
        + 'Target availability remains separate from financial reconciliation. The supplied map preserves '
            'all clipped values, unknowns, unit conflicts, historical limitations and conditional legal scope.\n\n'
            '|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|\n'
            '|---|---|---|---|---|---|\n'
        + ('|Retain finite relationship delivery|' if passed else '|Retain diagnosed failure|')
        + 'Whole 063 preservation and exact separately checked links|See actual stages|Shared development interpretation|'
            'Record, refresh and inspect wider original source/reference obligations|Source truth, financial reconciliation, '
            'general automatic capability or whole build|\n\n'
            'Post-run red-team review: the exact-map whitelist can preserve a shared wrong interpretation. '
            'Original source geometry and the separate audit constrain these 48 links; they do not establish all source meaning. '
            'A wrong target, lost prior field or accepted corruption would overturn the finite delivery verdict. '
            'This is a local representation repair and supplies no evidence that a third-party package is fundamentally unsuitable.\n')
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': read(PREP / 'config.json'), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        'random_seeds': 'N/A deterministic', 'data_version': common.ref(PREP / 'freeze.json'),
        'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    return {'status': 'SEALED', 'candidate_passed': passed, 'resources': costs()}


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    action = sys.argv[1]
    if action.startswith('worker-'):
        kind = action.removeprefix('worker-')
        sys.path.insert(0, str(HERE / 'installed') if kind.startswith('installed') else str(ROOT / 'src'))
        if kind != 'package':
            def forbidden(*args, **kwargs):
                raise RuntimeError('No native/network child in relationship worker')
            subprocess.Popen = forbidden
        if kind in ('ordinary', 'installed'):
            answer_worker(kind)
        elif kind in ('compare', 'installed-compare'):
            compare_worker(kind)
        elif kind in ('legacy', 'installed-legacy'):
            legacy_worker(kind)
        elif kind.startswith(('control-', 'installed-control-')):
            control_worker(kind)
        else:
            {'source': source_worker, 'implement': implement_worker, 'package': package_worker,
                'coverage': coverage_worker}[kind]()
        result = {'status': 'PASS', 'worker': kind}
    else:
        result = prepare() if action == 'prepare' else finalize() if action == 'finalize' else stage(action)
    print(json.dumps(result), flush=True)
