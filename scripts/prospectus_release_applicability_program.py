"""Bounded source08 repair for changed unaudited-release category bypasses."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
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
sys.dont_write_bytecode = True
from scripts import prospectus_h1_current_acceptance as base
from scripts import prospectus_interim_applicability_program as prior
from scripts import prospectus_h1_statement_context_program as context

read, sha, require = base.read, base.sha, base.require
AUTH = ROOT / base.AUTH
WORK = ROOT / '.localresources/prospectus-preparation/release-applicability'
PROBE = WORK / 'recovery'
PREP = AUTH / 'reviews/release-applicability-434'
HERE = AUTH / 'attempts/source-bes-dep-08/attempt-008'
TASK = 'source-bes-dep-08'
SELF = 'scripts/prospectus_release_applicability_program.py'
PLAN = 'docs/plans/prospectus-release-applicability-2026-10-22.md'
TEST = 'tests/prospectus_successor/test_release_applicability.py'
CHANGED = 'prospectus/successor/unaudited_release.py'
LIMITS = {'bytes': 256 * 1024**2, 'measured_and_failed_seconds': 600,
          'control_seconds': 60, 'worker_seconds': 120, 'unchanged_retries': 0,
          'changed_recovery': 'Used by the probe; no further retries'}


def rel(path):
    return str(Path(path).relative_to(ROOT))


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if path.suffix == '.gz':
        raw = gzip.compress(raw, mtime=0)
    require(len(raw) < 32 * 1024**2, 'Output bound')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def authority():
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs():
    initial = read(PREP / 'accounting-start.json')
    paths = {p for folder in (WORK, PREP, HERE) if folder.exists()
             for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (SELF, PLAN, TEST, 'scripts/prospectus_release_applicability_probe.py'))
    paths.add(ROOT / 'src/legalmath' / CHANGED)
    paths.add(AUTH / 'revisions/0434.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in initial['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - initial['program_bytes'])
    measured = read(PROBE / 'probe.json')['seconds'] + sum(
        read(p)['seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json')
        if read(p).get('accounting_role') != 'NESTED')
    failed = read(WORK / 'first-failure.json')['booked_ceiling_seconds']
    return {'new_bytes': size, 'new_measured_seconds': measured,
            'unmeasured_failed_ceiling_seconds': failed, 'control_seconds': 60,
            'known_cumulative_bytes': initial['prior']['known_cumulative_bytes'] + size,
            'booked_cumulative_seconds': initial['prior']['booked_cumulative_seconds'] + measured + failed + 60,
            'manual_unmeasured_seconds': 'UNKNOWN',
            'allowed': size < 254 * 1024**2 and measured + failed < 600}


def command(name, argv, folder, *, nested=False, timeout=120):
    usage = costs()
    require(usage['allowed'] and usage['new_measured_seconds'] + usage['unmeasured_failed_ceiling_seconds'] + timeout < 600,
            'Resource bound')
    folder.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONNOUSERSITE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1'}
    tick = time.monotonic()
    with (folder / (name + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        sys.path.insert(0, str(ROOT / 'src'))
        from legalmath.prospectus.execution_authority import process_identity
        save(folder / (name + '-started.json'), {'argv': argv, 'identity': process_identity(child.pid),
                                              'at': datetime.now(timezone.utc).isoformat(), 'seconds': 0})
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic() - tick,
                                   'accounting_role': 'NESTED' if nested else 'MEASURED',
                                   'environment': {k: env[k] for k in ('CUDA_VISIBLE_DEVICES', 'PYTHONPATH', 'PIP_NO_INDEX')}})
    require(code == 0, 'Inspect retained log: ' + str(folder / (name + '.log')))
    require(costs()['allowed'], 'Post-command resource bound')


def prepare():
    tick = time.monotonic()
    a = authority()
    program, _, _ = a.spec()
    require(program['revision'] == 433 and not PREP.exists() and not HERE.exists(), 'Fresh433required')
    state = a.status()
    require(not state['running'] and state['next_task'] is None, 'Complete active work first')
    require(read(PROBE / 'probe.json')['false_support_cases'] == 24, 'Reproduction required')
    historical = {}
    for task in ('source-bes-dep-08', 'source-bes-dep-11'):
        folder = AUTH / 'attempts' / task
        latest = sorted(folder.glob('attempt-*'))[-1]
        historical[task] = {'retained_bytes': sum(p.stat().st_size for p in folder.rglob('*')
                           if p.is_file() and '__pycache__' not in p.parts),
                           'latest_result': rel(latest / 'result.json'), 'sha256': sha(latest / 'result.json'),
                           'measured_total_seconds': 'UNKNOWN'}
    save(PREP / 'accounting-start.json', {'prior': prior.costs(), 'historical_sources': historical,
         'historical_overlap': 'Historical directory totals are separate observed stocks; not added to the prior campaign ledger',
         'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
         'program_bytes': (AUTH / 'program.json').stat().st_size})
    production = base.inventory(ROOT / 'src/legalmath')
    require(production == read(prior.HERE / 'package.json')['files'], 'Production differs from070')
    candidate = WORK / 'candidate/src/legalmath'
    shutil.copytree(ROOT / 'src/legalmath', candidate, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    module = (candidate / CHANGED).read_text()
    old = '''    if kind != KIND:
        return None
    if facts["conclusion"]["status"] != "UNKNOWN":
        raise ValueError("Issuer-release profile requires unknown independent opinion conclusion")
    if not header:
        return {"profile": PROFILE, "status": "UNRECOGNIZED_OR_INCOMPLETE_SOURCE_HEADER",
                "checks": {}, "unresolved_fields": ["source_header"],
                "general_semantic_truth_established": False}'''
    new = '''    # Incomplete recognized releases must not acquire another report's support.
    known_cover = reading.get("source_sha256") in {
        "b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f",
        "4c7067274ff3eb8f812a8a98d23c4fd2d4b159ed0259f066069b2416ae2e75ec",
    } and any(page.get("page") == 1 for page in reading.get("pages", []))
    release_title = re.search(
        r"^BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN[^\\n]*$",
        text, re.M) is not None
    if kind != KIND and not known_cover and not release_title:
        return None
    if kind == KIND and facts["conclusion"]["status"] != "UNKNOWN":
        raise ValueError("Issuer-release profile requires unknown independent opinion conclusion")
    if not header:
        return {"profile": PROFILE, "status": "UNRECOGNIZED_OR_INCOMPLETE_SOURCE_HEADER",
                "checks": {}, "unresolved_fields": ["source_header"],
                "general_semantic_truth_established": False}'''
    require(module.count(old) == 1, 'Release guard baseline changed')
    module = module.replace(old, new)
    # The existing positive path still requires the exact reviewed header.
    (candidate / CHANGED).write_text(module)
    actual = base.inventory(candidate)
    require({n for n in production if production[n] != actual[n]} == {CHANGED}
            and production.keys() == actual.keys(), 'Unexpected production change')
    save(PREP / 'candidate.json', {'baseline_production': production, 'candidate_production': actual})
    save(PREP / 'commands/preparation.json', {'argv': [SELF, 'prepare'], 'seconds': time.monotonic() - tick})
    return {'status': 'PREPARED', 'resources': costs()}


def cases():
    from legalmath.prospectus.successor import report_scope, service
    rows, answers = [], []
    for binding in read(PROBE / 'consumer-inputs.json.gz'):
        path = ROOT / binding['path']
        require(sha(path) == binding['sha256'], 'Changed retained case')
        packet = read(path)
        p1, p2 = packet['P1'], packet['P2']
        identity = {k: packet[k] for k in ('source', 'variant', 'category')}
        if 'error' in packet:
            try:
                service.interpretation_product(p1, p2, {'source_report_scope': packet['scope']})
            except ValueError as exc:
                require(str(exc) == packet['error'], 'Refusal reason changed')
                rows.append({**identity, 'refused': True})
                continue
            raise ValueError('Original false category no longer refused')
        p3 = service.interpretation_product(p1, p2, {'source_report_scope': packet['scope']})
        products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
                    'P5': service.financial_product(p1, p2, p3)}
        answer = service.consume(products, ROOT, mode='current', include_artifacts=True)
        baseline = packet['answer']
        report = answer['source_reports'][0]
        if packet['variant'] == 'exact':
            require(answer == baseline, 'Complete exact positive answer changed')
            require(report['use_assessment']['unaudited_financial_release'] == 'SUPPLIED_SOURCE_DESCRIPTION', 'Release description lost')
        else:
            require(report['status'] == 'INCOMPLETE_SOURCE_READING'
                    and report['unresolved_unaudited_release_fields'] == ['source_header'], 'Incomplete release gained support')
            require(all(v != 'SUPPLIED_SOURCE_SUPPORT' for v in report['use_assessment'].values()), 'False assurance persists')
            for key in ('questions', 'dependencies', 'assembly', 'source_map', 'may_execute_transaction', 'independent_legal_acceptance'):
                require(answer[key] == baseline[key], 'Unrelated answer changed: ' + key)
        rows.append({**identity, 'refused': False, 'status': report['status'], 'use_assessment': report['use_assessment']})
        answers.append({**identity, 'answer': answer})
    for original in read(PROBE / 'original-inputs.json.gz'):
        require(sha(ROOT / original['reading']['path']) == original['reading']['sha256'], 'Original source changed')
        actual = report_scope.explain(report_scope.admit(original['selected'], original['scope']))
        require(actual == original['answer'], 'Original PDF-bound scope changed')
    return {'status': 'PASS', 'rows': rows, 'false_support_cases': 0,
            'exact_original_answers_preserved': True, 'original_pdf_scopes_preserved': True}, answers


def trial():
    code = ('import sys; from pathlib import Path; r=Path.cwd(); '
            'sys.path[:0]=[str(r/".localresources/prospectus-preparation/release-applicability/candidate/src"),str(r),str(r/"tests/prospectus_successor")]; '
            'import pytest; raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",'
            '"tests/prospectus_successor/test_release_applicability.py","tests/prospectus_successor/test_unaudited_release.py",'
            '"tests/prospectus_successor/test_q1_release.py","tests/prospectus_successor/test_interim_review.py",'
            '"tests/prospectus_successor/test_interim_review_applicability.py","tests/prospectus_successor/test_report_scope.py",'
            '"tests/prospectus_successor/test_english_report_context.py",'
            '"--junitxml=.localresources/prospectus-preparation/release-applicability/regression.xml"]))')
    command('tests', [str(ROOT / '.venv/bin/python'), '-I', '-B', '-c', code], PREP / 'commands', timeout=60)
    command('classification', [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF), 'worker', '--kind', 'candidate'], PREP / 'commands', timeout=60)
    return {'status': 'PASS', 'resources': costs()}


def freeze():
    tick = time.monotonic()
    a = authority()
    old, _, _ = a.spec()
    require(old['revision'] == 433 and not a.status()['running'], 'Current433required')
    require(all(read(PREP / 'commands' / (name + '.json'))['exit_code'] == 0 for name in ('tests', 'classification')), 'Candidate checks required')
    inventory = read(PREP / 'candidate.json')
    require(base.inventory(ROOT / 'src/legalmath') == inventory['baseline_production'], 'Production changed')
    require(base.inventory(WORK / 'candidate/src/legalmath') == inventory['candidate_production'], 'Candidate changed')
    evidence = {'src/legalmath/' + n: h for n, h in inventory['candidate_production'].items()}
    names = [SELF, PLAN, TEST, 'scripts/prospectus_release_applicability_probe.py', rel(PREP / 'candidate.json')]
    evidence.update({n: sha(ROOT / n) for n in names})
    for folder in (WORK,):
        for path in folder.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                evidence[rel(path)] = sha(path)
    for original in read(PROBE / 'original-inputs.json.gz'):
        evidence[original['reading']['path']] = original['reading']['sha256']
    runtime = read(prior.PREP / 'freeze.json')['runtime']
    save(PREP / 'freeze.json', {**inventory, 'evidence': evidence, 'runtime': runtime, 'limits': LIMITS})
    from legalmath.prospectus.execution_authority import digest
    program = deepcopy(old)
    program['revision'] = 434
    task = next(t for t in program['tasks'] if t['id'] == TASK)
    task.update(dossier=PLAN, pre_admission_review=PLAN,
                reason='Repair reproduced false audit/committee/sustainability support on incomplete issuer releases',
                release_applicability_review=rel(PREP / 'freeze.json'))
    task['inputs'] = sorted(set(task['inputs']) | set(evidence) | {rel(PREP / 'freeze.json')})
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == TASK]
    require(len(attempts) == old['budgets'][TASK]['maximum_new_attempts'] == 7, 'Preserve seven source08 admissions')
    program['budgets'][TASK]['maximum_new_attempts'] = 8
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 434
    for route in routes['tasks']:
        if route['task'] == TASK:
            route.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                         remaining='Twenty-four false-support cases reproduced; original source08 scope remains open.',
                         next_action='Complete admitted applicability checks; after recording008 reconcile original source08 obligations and fresh current-component validation.',
                         stop_condition='Admission008;256MiB;600 measured/failed plus60control seconds; recovery already used; no external action.')
        elif route['task'] == 'source-bes-dep-05':
            route.update(phase=1, remaining='070 retained the interim repair; changed shared production requires fresh unit evidence before current criterion credit.',
                         next_action='Use changed shared-production results for a reviewed fresh unit submission; preserve all070 evidence and original source gaps.')
    save(PREP / 'routes.json', routes)
    program['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    key = 'src/legalmath/' + CHANGED
    if key in program['continuation_review']['bindings']:
        program['continuation_review']['bindings'][key] = inventory['candidate_production'][CHANGED]
    program['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (SELF, PLAN, rel(PREP / 'freeze.json'), rel(PREP / 'routes.json'))})
    require(old['obligations'] == program['obligations'] and old['build_contract'] == program['build_contract'], 'Original scope changed')
    save(PREP / 'proposal.json', program)
    save(PREP / 'review.json', {'baseline': digest(old), 'scope_unchanged': True, 'budget_unchanged': False,
         'changes': ['Separate release applicability from positive header matching', 'Preserve exact originals and test real ordinary/installed consumers'],
         'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'probe': rel(PROBE / 'probe.json'), 'tests': rel(WORK / 'regression.xml')},
         'evidence_contract': {'question': 'Can changed recognizable unaudited releases gain false report support?',
              'baseline': rel(PROBE / 'consumer-inputs.json.gz'), 'primary': 'False support withheld; complete original answers unchanged',
              'promotion_veto': ['False support', 'Wrong source/imports', 'Changed exact answer'],
              'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted bound'],
              'explanatory': ['Runtime', 'Test totals'], 'not_concluded': ['General semantics', 'Source authority', 'Original task complete']},
         'budget_revision': {'budget_key': TASK, 'previous_maximum': 7, 'new_maximum': 8, 'retained_attempts': attempts,
              'reason': 'Twenty-four actual source-header/category counterexamples after prior report repair',
              'next_discriminating_check': 'Exact original and altered-source answers from current ordinary and installed consumers',
              'stop_condition': LIMITS, 'same_scope_authorization': 'Recover and continue original prospectus build'}})
    save(PREP / 'commands/freeze.json', {'seconds': time.monotonic() - tick, 'argv': [SELF, 'freeze']})
    forecast = costs()['new_bytes'] + 3 * sum((ROOT / 'src/legalmath' / n).stat().st_size for n in inventory['baseline_production'])
    forecast += 3 * (PREP / 'proposal.json').stat().st_size + 2 * (WORK / 'candidate-answers.json.gz').stat().st_size
    forecast += 2 * (prior.HERE / 'ordinary-answer.json.gz').stat().st_size
    require(forecast < 254 * 1024**2, 'Forecast storage bound')
    return {'status': 'FROZEN_REVIEWED', 'forecast_bytes': forecast, 'resources': costs()}


def cutover():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    frozen = read(PREP / 'freeze.json')
    require(digest(a.spec()[0]) == read(PREP / 'review.json')['baseline'] and not a.status()['running'], 'Cutover baseline changed')
    require(base.inventory(ROOT / 'src/legalmath') == frozen['baseline_production'], 'Production changed')
    shutil.copyfile(WORK / 'candidate/src/legalmath' / CHANGED, ROOT / 'src/legalmath' / CHANGED)
    require(base.inventory(ROOT / 'src/legalmath') == frozen['candidate_production'], 'Cutover differs')
    save(PREP / 'cutover.json', {'status': 'PASS', 'changed': CHANGED, 'revision_required': 434})
    return {'status': 'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def stage(kind):
    a = authority()
    program, tasks, _ = a.spec()
    require(program['revision'] == 434 and read(HERE / 'admission.json')['binding'] == a.binding(tasks[TASK]), 'Current434admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == TASK)['kind'] == 'ADMIT', 'Attempt terminal')
    if kind == 'installed':
        require(read(HERE / 'package.json')['status'] == 'PASS', 'Package required')
    runtime = read(PREP / 'freeze.json')['runtime']
    python = runtime['package_python' if kind == 'installed' else 'ordinary_python']
    command(kind, [python, '-I', '-B', str(ROOT / SELF), 'worker', '--kind', kind], HERE / 'commands')
    return {'status': 'PASS', 'stage': kind, 'resources': costs()}


def worker(kind):
    if kind == 'candidate':
        sys.path.insert(0, str(WORK / 'candidate/src'))
        result, answers = cases()
        save(WORK / 'candidate-classification.json', result)
        save(WORK / 'candidate-answers.json.gz', answers)
        return {'status': 'PASS'}
    frozen = read(PREP / 'freeze.json')
    if kind == 'package':
        source = HERE / 'package-source'
        source.mkdir()
        shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
        shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        python = frozen['runtime']['package_python']
        command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)], HERE / 'commands', nested=True, timeout=60)
        wheels = list((HERE / 'wheel').glob('*.whl'))
        require(len(wheels) == 1, 'One wheel required')
        command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile', '--target', str(HERE / 'installed'), str(wheels[0])], HERE / 'commands', nested=True, timeout=60)
        require(base.inventory(HERE / 'installed/legalmath') == frozen['candidate_production'], 'Installed package differs')
        save(HERE / 'package.json', {'status': 'PASS', 'files': frozen['candidate_production'], 'wheel': {'path': rel(wheels[0]), 'sha256': sha(wheels[0])}})
    else:
        target = ROOT / 'src' if kind == 'ordinary' else HERE / 'installed'
        sys.path.insert(0, str(target))
        result, answers = cases()
        require(result == read(WORK / 'candidate-classification.json') and answers == read(WORK / 'candidate-answers.json.gz'), 'Actual classification differs')
        products, profiles = base.inputs(ROOT)
        answer = context.consume(products, profiles, read(AUTH / 'reviews/h1-statement-context-432/profile.json'))
        require(answer == read(prior.HERE / 'ordinary-answer.json.gz') == read(prior.HERE / 'installed-answer.json.gz'), 'Complete070financial answer changed')
        proof = base.proof(ROOT, {k: answer[k] for k in base.PRIOR | base.LATER}, adverse=True)
        save(HERE / (kind + '-answer.json.gz'), answer)
        save(HERE / (kind + '-classifications.json.gz'), answers)
        save(HERE / (kind + '.json'), {'status': 'PASS', 'classification': result, 'unit_proof': proof,
             'imports': base.imported(target), 'isolated': sys.flags.isolated == 1, 'executable': str(Path(sys.executable).resolve())})
    return {'status': 'PASS', 'worker': kind}


def verify():
    frozen = read(PREP / 'freeze.json')
    require(all(sha(ROOT / n) == h for n, h in frozen['evidence'].items()), 'Changed frozen input/method')
    require(base.inventory(ROOT / 'src/legalmath') == frozen['candidate_production'], 'Changed production')
    package = read(HERE / 'package.json')
    wheel = ROOT / package['wheel']['path']
    require(package['status'] == 'PASS' and package['files'] == frozen['candidate_production']
            and sha(wheel) == package['wheel']['sha256']
            and base.inventory(HERE / 'installed/legalmath') == package['files'], 'Changed package')
    with zipfile.ZipFile(wheel) as archive:
        payload = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                   for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(payload == package['files'], 'Wheel payload differs')
    for kind in ('ordinary', 'installed'):
        receipt = read(HERE / (kind + '.json'))
        require(receipt['status'] == 'PASS' and receipt['isolated'] is True
                and receipt['classification'] == read(WORK / 'candidate-classification.json'), 'Missing actual result')
        require(read(HERE / (kind + '-classifications.json.gz')) == read(WORK / 'candidate-answers.json.gz'), 'Changed full report answer')
        answer = read(HERE / (kind + '-answer.json.gz'))
        require(answer == read(prior.HERE / 'ordinary-answer.json.gz'), 'Changed previous financial answer')
        require(receipt['unit_proof'] == base.proof(ROOT, {k: answer[k] for k in base.PRIOR | base.LATER}, adverse=True), 'Unit proof differs')
        target = ROOT / 'src' if kind == 'ordinary' else HERE / 'installed'
        require('legalmath.prospectus.successor.unaudited_release' in receipt['imports'], 'Release code was not imported')
        for item in receipt['imports'].values():
            path = Path(item['path']).resolve()
            require(path.is_relative_to(target / 'legalmath') and sha(path) == item['sha256'], 'Wrong import')
        python = frozen['runtime']['package_python' if kind == 'installed' else 'ordinary_python']
        cmd = read(HERE / 'commands' / (kind + '.json'))
        require(cmd['exit_code'] == 0 and cmd['argv'] == [python, '-I', '-B', str(ROOT / SELF), 'worker', '--kind', kind]
                and receipt['executable'] == str(Path(python).resolve()), 'Wrong command/interpreter')
        require(cmd['environment']['CUDA_VISIBLE_DEVICES'] == '-1' and cmd['environment']['PIP_NO_INDEX'] == '1', 'Unexpected environment')
    return True


def seal():
    require(verify(), 'Finite result verification failed')
    require((HERE / 'RESULT.md').exists(), 'Substantive result note required')
    save(HERE / 'result.json', {'status': 'PASS', 'task': TASK, 'finite_repair_verified': True,
         'false_support_cases_repaired': 24, 'original_task_complete': False, 'whole_program_complete': False,
         'current_named_unit_criterion_submitted': False, 'resources': costs()})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'], 'plan': PLAN,
         'commands': {n: read(HERE / 'commands' / (n + '.json')) for n in ('ordinary', 'package', 'installed')},
         'environment': read(PREP / 'freeze.json')['runtime'], 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
         'data_version': rel(PROBE / 'original-inputs.json.gz'), 'random_seeds': 'N/A; deterministic source cases',
         'wall_seconds': costs()['new_measured_seconds'], 'failed_unmeasured_ceiling_seconds': 60,
         'artifacts': rel(HERE), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
         if p.is_file() and '__pycache__' not in p.parts and p.name != 'outputs.json'})
    require(costs()['allowed'], 'Final resource bound')
    return {'status': 'SEALED', 'resources': costs()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'trial', 'freeze', 'cutover', 'stage', 'worker', 'seal', 'costs'])
    parser.add_argument('--kind', choices=['ordinary', 'package', 'installed', 'candidate'])
    args = parser.parse_args()
    result = stage(args.kind) if args.action == 'stage' else worker(args.kind) if args.action == 'worker' else globals()[args.action]()
    print(json.dumps(result), flush=True)
