"""Named task checks; no generic agent or human acceptance."""
import ast
import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET

VALIDATORS = {'recovery-sequence.v1': 'recovery', 'authority-audit.v1': 'authority-acceptance',
              'native-binding-files.v1': 'native-binding',
              'native-current-files.v2': 'native-binding',
              'native-installed-profile.v1': 'native-confinement',
              'native-retained-current.v3': 'native-binding',
              'native-installed-current.v2': 'native-confinement',
              'finite-reasoning-certificate.v1': 'reasoning-corpus',
              'conditional-reasoning-current.v1': 'reasoning-corpus',
              'basf-printed-scope.v1': 'basf-margins',
              'conditional-fixed-finance.v1': 'finance-conventions'}
STATES = ('baseline', 'environment-changed', 'model-missing', 'model-restored',
          'correction-image-wrong', 'correction-restored', 'correction-map-wrong', 'final-restored')
CLOSURE = 'src/legalmath/prospectus/successor/closure_program.py'


def check_task(task):
    name = task.get('validator')
    if name is None:
        return
    stream = ('assisted' if name in {'basf-printed-scope.v1', 'conditional-fixed-finance.v1'}
              else 'engineering') if isinstance(name, str) else None
    if (not isinstance(name, str) or name not in VALIDATORS or VALIDATORS[name] != task['id']
            or task['handler'] != 'agent' or task['stream'] != stream):
        raise ValueError('Validator is unknown or outside its named task and stream')


def selection_only_change(old, new):
    """The retained recovery worker runs R0 only; R4/R6 selection is separate."""
    def separate(source):
        tree = ast.parse(source)
        assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'JOBS' for t in n.targets)]
        if len(assignments) != 1:
            raise ValueError('Exactly one literal JOBS assignment required')
        jobs = ast.literal_eval(assignments[0].value)
        tree.body.remove(assignments[0])
        return ast.dump(tree, include_attributes=False), jobs
    try:
        before, jobs_before = separate(old)
        after, jobs_after = separate(new)
    except (ValueError, TypeError, SyntaxError):
        return False
    return (before == after and jobs_before.keys() == jobs_after.keys()
            and all(jobs_before[k] == jobs_after[k] for k in jobs_before if k not in {'R4', 'R6'}))


def checked_tests(path, minimum):
    try:
        suites = list(ET.parse(path).getroot().iter('testsuite'))
        counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    except (ET.ParseError, ValueError, TypeError) as exc:
        raise ValueError('Malformed required evidence checks') from exc
    if counts['tests'] < minimum or any(counts[k] for k in ('failures', 'errors', 'skipped')):
        raise ValueError('Missing, failed or skipped required evidence checks')
    return counts['tests']


def retained_attempt(root, task):
    from .execution_authority import Authority, REL, read, file_hash
    authority = Authority(root)
    name = task.get('evidence_attempt')
    if not isinstance(name, str):
        raise ValueError('Named retained evidence attempt required')
    folder = authority.path(name)
    if not folder.is_relative_to(authority.base / 'attempts' / task['id']):
        raise ValueError('Evidence attempt belongs to another task')
    manifest = read(folder / 'outputs.json')
    if not isinstance(manifest, dict) or 'result.json' not in manifest:
        raise ValueError('Complete retained evidence manifest required')
    required = {str((folder / n).relative_to(root)) for n in manifest}
    required.add(str((folder / 'outputs.json').relative_to(root)))
    if not required <= set(task['inputs']):
        raise ValueError('Every retained evidence file must be an admitted input')
    for relative, expected in manifest.items():
        path = authority.path(str((folder / relative).relative_to(root)))
        if not path.is_relative_to(folder) or file_hash(path) != expected:
            raise ValueError('Retained evidence identity changed: ' + relative)
    if read(folder / 'result.json').get('task') != task['id']:
        raise ValueError('Retained result belongs to another task')
    return folder


def recovery_evidence(root, task):
    from .execution_authority import file_hash, read
    root = Path(root).resolve()
    folder = retained_attempt(root, task)
    started = read(folder / 'started.json')
    if started['states'] != list(STATES):
        raise ValueError('Recovery state denominator changed')
    required_methods = {CLOSURE, *['src/legalmath/prospectus/successor/' + name for name in
                        ('service.py', 'native_inputs.py', 'ocr_worker.py', 'extraction.py', 'source_graph.py')]}
    if not required_methods <= started.get('methods', {}).keys():
        raise ValueError('Recovery production method coverage is incomplete')
    for name, expected in {**started['methods'], **started['sources']}.items():
        if name not in task['inputs']:
            raise ValueError('Recovery source/method missing from admission: ' + name)
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Recovery method/source escapes worktree')
        actual = file_hash(path)
        if actual == expected:
            continue
        old = folder / 'method' / name
        if (name != CLOSURE or not old.is_file() or file_hash(old) != expected
                or not selection_only_change(old.read_text(), (root / name).read_text())):
            raise ValueError('Recovery source/method changed: ' + name)
    tests = checked_tests(folder / 'tests.xml', 44)
    hashes, steps = {}, []
    for label in STATES:
        base = folder / 'steps' / label
        row = read(base / 'result.json')
        if (row.get('state') != label or row.get('status') != 'PASS'
                or row.get('invalidated_before_marker') is not True or row.get('actual_equals_clean') is not True):
            raise ValueError('Missing actual recovery control: ' + label)
        receipt = read(base / 'executor-receipt.json')
        if (receipt.get('engineering_checks') != 'PASS' or receipt.get('reused') is not False
                or read(base / 'clean-command.json').get('returncode') != 0):
            raise ValueError('Missing fresh executor/clean evidence: ' + label)
        checked_tests(base / 'phase-tests.xml', 1)
        hashes[label] = file_hash(base / 'actual.json.gz')
        if hashes[label] != file_hash(base / 'clean.json.gz'):
            raise ValueError('Actual and clean products differ: ' + label)
        steps.append({'state': label, 'product_sha256': hashes[label]})
    if hashes['baseline'] != hashes['final-restored']:
        raise ValueError('Full restoration differs from original output')
    if any(hashes[s] != hashes['environment-changed'] for s in ('model-restored', 'correction-restored')):
        raise ValueError('Intermediate restoration differs')
    def product(label):
        with gzip.open(folder / 'steps' / label / 'actual.json.gz', 'rt') as stream:
            return json.load(stream)
    first = product('baseline')
    changed = product('environment-changed')
    if (first['portuguese']['report']['questions'] != changed['portuguese']['report']['questions']
            or first['portuguese']['report']['source_graph_sha256'] == changed['portuguese']['report']['source_graph_sha256']):
        raise ValueError('Environment change did not preserve questions with changed source identity')
    for case in ('portuguese', 'correction'):
        if not first[case].get('report') or not changed[case].get('report'):
            raise ValueError('Successful actual source consumer missing')
    del changed
    source_name = ('docs/implementation/prospectus-integration-closure/bes-original-acquisition/'
                   'portuguese-2010/ocr-consumer-001/source-product.json.gz')
    worker_name = source_name.replace('source-product.json.gz', 'worker.json')
    if source_name not in started['sources'] or worker_name not in started['sources']:
        raise ValueError('Original Portuguese baseline is not bound')
    with gzip.open(root / source_name, 'rt') as stream:
        original = json.load(stream)
    report = first['portuguese']['report']
    if report['source_map']['units'] != original['payload']['graph']['units']:
        raise ValueError('Original Portuguese source units changed')
    pages = report['source_map']['documents'][0]['scan_pages']
    if [p['image_sha256'] for p in pages] != [p['image_sha256'] for p in read(root / worker_name)['pages']]:
        raise ValueError('Original Portuguese page images changed')
    del original, first, report
    for label, case, fragment in [('model-missing', 'portuguese', 'OCR language model missing or changed: por'),
            ('correction-image-wrong', 'correction', 'source-page image identity'),
            ('correction-map-wrong', 'correction', 'cover the raw interval in order')]:
        output = product(label)
        if fragment not in output[case].get('error', ''):
            raise ValueError('Required specific adverse rejection missing: ' + label)
        other = 'correction' if case == 'portuguese' else 'portuguese'
        if not output[other].get('report'):
            raise ValueError('Independent source consumer missing under adverse state')
        del output
    return {'version': 'finite-recovery-acceptance.v1', 'evidence_attempt': task['evidence_attempt'],
            'states': steps, 'focused_tests': tests, 'complete_restoration': True,
            'scope': 'Finite same-host multilingual and synthetic-correction recovery',
            'native_confinement_established': False, 'portability_established': False,
            'independent_legal_acceptance': False}


def authority_evidence(root):
    from .execution_authority import Authority
    from .successor import closure_program
    authority = Authority(root)
    program, tasks, order = authority.spec()
    state = authority.status()
    events = authority.events()
    recovery = next(r for r in state['tasks'] if r['id'] == 'recovery')
    if recovery['state'] != 'COMPLETE':
        raise ValueError('Actual finite recovery acceptance transition required')
    rows = []
    for row in state['tasks']:
        if row['id'] == 'authority-acceptance':
            continue  # The admission is being validated; no self-completion claim.
        event = next((e for e in reversed(events) if e.get('task') == row['id']), None)
        intact = None
        if event and event['kind'] in {'ACCEPT', 'RECORD', 'REJECT'} and event.get('outputs_sha256'):
            intact = authority.retained_evidence_valid(event)
            if not intact:
                raise ValueError('Another retained task evidence changed: ' + row['id'])
        rows.append({'id': row['id'], 'state': row['state'], 'attempt': row['attempt'],
                     'retained_evidence_intact': intact})
    required = {'R4': ['test_governing_interpretation.py', 'test_meaning_coverage.py', 'test_relation_discovery.py'],
                'R6': ['test_native_inputs.py']}
    for phase, names in required.items():
        paths, expression = closure_program.JOBS[phase]
        if any('tests/prospectus_successor/' + name not in paths.split()
               or name.removeprefix('test_').removesuffix('.py') not in expression for name in names):
            raise ValueError('Delegated regression selection omits required module')
    if any(state['completion'].values()) or state['program_complete']:
        raise ValueError('Current source/human/automatic requirements must remain open')
    return {'version': 'finite-authority-acceptance.v1', 'program_sha256': state['program_sha256'],
            'obligations': program['obligations'], 'tasks': rows, 'budget_admissions': state['budget_admissions'],
            'recovery_accepted_attempt': recovery['attempt'], 'completion_before_this_acceptance': state['completion'],
            'validators': VALIDATORS, 'whole_program_complete': False}


def native_binding_evidence(root, task):
    from . import native_binding_acceptance as native
    from .execution_authority import file_hash, read
    root = Path(root).resolve()
    folder = retained_attempt(root, task)
    required = {str(p.relative_to(root)) for p in (root / 'src/legalmath/prospectus/successor').glob('*.py')}
    required |= {'src/legalmath/prospectus/native_binding_acceptance.py',
                 'tests/prospectus/test_native_binding_acceptance.py', 'scripts/prospectus_native_profile.py'}
    if not required <= set(task['inputs']):
        raise ValueError('Native product/acceptance methods missing from admission')
    tests_name = task.get('acceptance_tests')
    if not isinstance(tests_name, str) or tests_name not in task['inputs']:
        raise ValueError('Current native acceptance test report must be admitted')
    tests = native.contained(root, tests_name)
    checked_tests(tests, 20)
    names = {r.get('name', '').split('[')[0] for r in ET.parse(tests).getroot().iter('testcase')}
    if not {'test_missing_matrix_cell_or_consumer_refuses', 'test_forged_pass_without_evidence_refuses',
            'test_missing_control_refuses', 'test_changed_receipt_refuses', 'test_stale_method_refuses',
            'test_rehashed_answer_still_requires_actual_consumer',
            'test_compressed_file_and_internal_product_identities_are_distinct',
            'test_boundary_diagnostic_refuses_false_explanations',
            'test_campaign_preserves_failed_launch_and_allowance'} <= names:
        raise ValueError('Current native acceptance refusal tests missing')
    proof = task.get('acceptance_test_methods')
    if not isinstance(proof, str) or proof not in task['inputs']:
        raise ValueError('Current test method manifest must be admitted')
    methods = read(native.contained(root, proof))
    if not {'src/legalmath/prospectus/native_binding_acceptance.py',
            'src/legalmath/prospectus/execution_acceptance.py',
            'tests/prospectus/test_native_binding_acceptance.py'} <= methods.keys():
        raise ValueError('Test method inventory incomplete')
    native.verify_files(root, methods)
    result = native.evidence(root, folder)
    result.update(acceptance_tests_sha256=file_hash(tests), acceptance_test_methods=methods)
    return result


def native_installed_evidence(root, task):
    from . import native_installed_acceptance as installed
    from . import native_binding_acceptance as native
    from .execution_authority import file_hash, read
    root = Path(root).resolve()
    folder = retained_attempt(root, task)
    required = {str(p.relative_to(root)) for p in (root / 'src/legalmath/prospectus/successor').glob('*.py')}
    required |= {'src/legalmath/prospectus/native_profile.py',
                 'src/legalmath/prospectus/native_installed_acceptance.py',
                 'src/legalmath/prospectus/native_binding_acceptance.py',
                 'scripts/prospectus_native_install.py', 'scripts/prospectus_native_installed_controls.py',
                 'tests/prospectus/test_native_profile.py', 'tests/prospectus/test_native_installed_acceptance.py'}
    if not required <= set(task['inputs']):
        raise ValueError('Installed acceptance method/input inventory incomplete')
    tests_name, proof_name = task.get('acceptance_tests'), task.get('acceptance_test_methods')
    if any(not isinstance(n, str) or n not in task['inputs'] for n in (tests_name, proof_name)):
        raise ValueError('Current installed acceptance tests and methods must be admitted')
    tests = native.contained(root, tests_name)
    checked_tests(tests, 20)
    names = {r.get('name', '').split('[')[0] for r in ET.parse(tests).getroot().iter('testcase')}
    if not {'test_installed_proof_rejects_wrong_location_or_method',
            'test_installed_controls_reject_incomplete_or_false_evidence',
            'test_installed_wheel_requires_actual_method_bytes',
            'test_installed_campaign_refuses_changed_limits_or_launches',
            'test_installed_forged_pass_without_matrix_refuses',
            'test_installed_requirement_mapping_preserves_bytes_and_unrelated_sources',
            'test_rehashed_answer_still_requires_actual_consumer',
            'test_changed_receipt_refuses', 'test_missing_matrix_cell_or_consumer_refuses'} <= names:
        raise ValueError('Required installed acceptance refusal tests missing')
    methods = read(native.contained(root, proof_name))
    if not (required | {'src/legalmath/prospectus/execution_acceptance.py'}) <= methods.keys():
        raise ValueError('Installed test method inventory incomplete')
    native.verify_files(root, methods)
    result = installed.evidence(root, folder)
    result.update(acceptance_tests_sha256=file_hash(tests), acceptance_test_methods=methods)
    return result


def validate(root, attempt, task):
    from .execution_authority import read
    check_task(task)
    name = task.get('validator')
    if name == 'basf-printed-scope.v1':
        if task.get('printed_scope_acceptance', {}).get('indexed_repair') is True:
            from scripts.prospectus_margin_indexed import validate_submission
        else:
            from scripts.prospectus_margin_receipt_repair import validate_submission
        return validate_submission(root, attempt, task)
    if name == 'conditional-reasoning-current.v1':
        from scripts.prospectus_reasoning_acceptance import validate_submission
        return validate_submission(root, attempt, task)
    if name == 'conditional-fixed-finance.v1':
        from scripts.prospectus_fixed_finance_verify import validate_submission
        return validate_submission(root, attempt, task)
    if name == 'finite-reasoning-certificate.v1':
        from scripts.prospectus_reasoning_verification import validate_submission
        return validate_submission(root, attempt, task)
    if name in {'native-retained-current.v3', 'native-installed-current.v2'}:
        from scripts.prospectus_current_acceptance import validate_submission
        return validate_submission(root, attempt, task)
    if name == 'native-current-files.v2':
        from .native_current_acceptance import validate_submission
        return validate_submission(root, attempt, task)
    if name == 'recovery-sequence.v1':
        expected = recovery_evidence(root, task)
    elif name == 'native-binding-files.v1':
        expected = native_binding_evidence(root, task)
    elif name == 'native-installed-profile.v1':
        expected = native_installed_evidence(root, task)
    elif name == 'authority-audit.v1':
        expected = authority_evidence(root)
        checked_tests(attempt / 'tests.xml', 1)
        names = {r.get('name', '').split('[')[0] for r in ET.parse(attempt / 'tests.xml').getroot().iter('testcase')}
        required = {'test_arbitrary_pass_record_does_not_establish_substantive_completion',
                    'test_reviewed_partial_followup_reuses_original_budget',
                    'test_bound_external_files_allow_review_but_not_automatic_acceptance',
                    'test_registered_validator_requires_actual_evidence',
                    'test_recovery_selection_equivalence_rejects_other_behavior_changes'}
        if not required <= names:
            raise ValueError('Required actual authority acceptance checks missing')
    else:
        return False
    if read(attempt / 'verification.json') != expected:
        raise ValueError('Acceptance result differs from actual retained evidence')
    result = read(attempt / 'result.json')
    if result.get('scope') != 'FINITE_ENGINEERING_ONLY' or result.get('whole_program_complete') is not False:
        raise ValueError('Finite acceptance cannot claim whole-program completion')
    return True
