"""Current delivery scope inside the sole authority; historical verdicts survive."""
from pathlib import Path


DEFERRED = {
    'instrument-facts': 'REAL_CASE_AFTER_BUILD',
    'authoring-export': 'ACTUAL_READER_ACCEPTANCE_AFTER_BUILD',
    'independent-readings': 'EXTERNAL_OPINION_NOT_BUILD_CRITERION',
    'cdm-profile': 'NO_RECEIVING_SYSTEM',
    'cdm-roundtrip': 'NO_RECEIVING_SYSTEM',
    'portability': 'DEFERRED_BY_USER',
}
BUILD_FIRST_DEFERRED = {**DEFERRED,
    'independent-packet': 'EXTERNAL_READER_COHORT_NOT_BUILD_CRITERION'}
VALIDATORS = {'pension-rounding.v1': ('basf-references', 'pension-rounding'),
              'bes-cash-flow.v1': ('source-bes-dep-07', 'individual-cash-flow'),
              'h1-unit-conflict.v1': ('source-bes-dep-05', 'individual-unit-conflict'),
              'bes-comparative-basis.v1': ('source-bes-dep-06', 'comparative-accounting-basis'),
              'exact-quantity-refusal.v1': ('finance-conventions', 'exact-quantity-refusal')}


def check(program, root):
    """An explicit projection, never a waiver of original obligations."""
    from .execution_authority import file_hash
    contract = program.get('build_contract')
    if contract is None:
        return
    keys = {'version', 'authorization', 'required_tasks', 'deferred_tasks',
            'real_case', 'external_opinion_required', 'cdm_receiver', 'portability', 'claim'}
    if contract.get('version') in {'general-build.v2', 'general-build.v3'}:
        keys.add('criteria')
    elif contract.get('version') != 'general-build.v1':
        raise ValueError('Invalid current-build contract')
    if set(contract) != keys:
        raise ValueError('Invalid current-build contract')
    auth = contract['authorization']
    if not isinstance(auth, dict) or set(auth) != {'path', 'sha256'}:
        raise ValueError('Current-build scope requires retained user direction')
    root = Path(root).resolve()
    path = (root / auth['path']).resolve()
    if not path.is_relative_to(root) or file_hash(path) != auth['sha256']:
        raise ValueError('Current-build authorization changed')
    required = contract['required_tasks']
    tasks = {t['id'] for t in program['tasks']}
    deferred = BUILD_FIRST_DEFERRED if contract['version'] == 'general-build.v3' else DEFERRED
    if (contract['deferred_tasks'] != deferred or not isinstance(required, list)
            or len(required) != len(set(required)) or not required
            or set(required) & set(deferred) or set(required) | set(deferred) != tasks):
        raise ValueError('Every historical task needs an explicit current-build disposition')
    if (contract['real_case'] != 'AFTER_GENERAL_BUILD'
            or contract['external_opinion_required'] is not False
            or contract['cdm_receiver'] is not None or contract['portability'] != 'DEFERRED'
            or contract['claim'] != 'CONDITIONAL_CORRECTNESS_IN_DECLARED_SUPPORTED_DOMAIN'):
        raise ValueError('Current-build scope conflicts with retained user direction')
    criteria = contract.get('criteria', {})
    if not isinstance(criteria, dict) or set(criteria) - set(required):
        raise ValueError('Build criteria must refine existing required tasks')
    by_id = {t['id']: t for t in program['tasks']}
    for task in program['tasks']:
        submission_criteria(task, program)
        from .criterion_evidence import contracts
        contracts(task, program)
    for task_id, rows in criteria.items():
        if (not isinstance(rows, list) or not rows or any(not isinstance(r, dict) for r in rows)
                or len({r.get('id') for r in rows}) != len(rows)):
            raise ValueError('Nonempty unique build criteria required')
        for row in rows:
            if (set(row) != {'id', 'basis', 'validator', 'description'}
                    or not isinstance(row['id'], str) or not row['id']
                    or not isinstance(row['description'], str) or not row['description'].strip()):
                raise ValueError('Explicit build criterion and scope required')
            if row['basis'] == 'ORIGINAL_TASK_ACCEPTANCE':
                if row['validator'] is not None:
                    raise ValueError('Original acceptance cannot acquire a conditional validator')
            elif row['basis'] == 'NAMED_CONDITIONAL_CHECK':
                if (VALIDATORS.get(row['validator']) != (task_id, row['id'])
                        or by_id[task_id]['handler'] != 'agent'):
                    raise ValueError('Unknown or misplaced conditional build validator')
            else:
                raise ValueError('Unknown build-criterion basis')
        if not any(r['basis'] == 'ORIGINAL_TASK_ACCEPTANCE' for r in rows):
            raise ValueError('Conditional component cannot omit remaining original acceptance')


def project(program, completed, conditional=None):
    contract = program.get('build_contract')
    if contract is None:
        return None
    conditional = conditional or {}
    criteria = contract.get('criteria', {})
    verified, pending = [], []
    for task_id, rows in criteria.items():
        for row in rows:
            passed = (task_id in completed if row['basis'] == 'ORIGINAL_TASK_ACCEPTANCE' else
                      row['id'] in conditional.get(task_id, ()))
            (verified if passed else pending).append({'task': task_id, **row})
    missing_scoped = {r['task'] for r in pending}
    remaining = [t for t in contract['required_tasks'] if
                 (t in missing_scoped if t in criteria else t not in completed)]
    return {'version': contract['version'], 'complete': not remaining,
            'claim': contract['claim'], 'remaining_tasks': remaining,
            'deferred_tasks': contract['deferred_tasks'],
            'deferred_tasks_accepted': False, 'external_opinion_required': False,
            'verified_criteria': verified, 'pending_criteria': pending,
            'original_tasks_accepted_by_build_criteria': False}


def submission_criteria(task, program):
    """A submission may claim a reviewed subset; it cannot change the criteria."""
    rows = program.get('build_contract', {}).get('criteria', {}).get(task['id'], [])
    if 'build_criteria_scope' not in task:
        return rows
    scope = task['build_criteria_scope']
    eligible = {r['id'] for r in rows if r['basis'] == 'NAMED_CONDITIONAL_CHECK'}
    if (not isinstance(scope, list) or any(not isinstance(x, str) for x in scope)
            or len(scope) != len(set(scope)) or set(scope) - eligible):
        raise ValueError('Submission scope must name unique existing conditional criteria')
    return [r for r in rows if r['id'] in scope]


def validate_submission(root, attempt, task, program):
    """Named local proof, separate from the historical acceptance disposition."""
    criteria = submission_criteria(task, program)
    passed = []
    for row in criteria:
        if row['basis'] != 'NAMED_CONDITIONAL_CHECK':
            continue
        if VALIDATORS.get(row['validator']) != (task['id'], row['id']) or task['handler'] != 'agent':
            raise ValueError('Conditional validator outside admitted scope')
        if row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_interim_applicability_acceptance'):
            from scripts.prospectus_interim_applicability_program import validate_submission as validate
        elif row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_statement_context_acceptance'):
            from scripts.prospectus_h1_statement_context_program import validate_submission as validate
        elif row['validator'] == 'h1-unit-conflict.v1' and task.get('h1_current_unit_acceptance'):
            from scripts.prospectus_h1_current_acceptance import validate_submission as validate
        elif task.get('current_component_validation'):
            from scripts.prospectus_component_revalidation import validate_submission as validate
        elif row['validator'] == 'pension-rounding.v1':
            from scripts.prospectus_pension_reconciliation import validate_submission as validate
        elif row['validator'] == 'bes-cash-flow.v1':
            if task.get('cash_flow_revalidation'):
                from scripts.prospectus_bes_cash_flow_revalidation import validate_submission as validate
            else:
                from scripts.prospectus_bes_cash_flow import validate_submission as validate
        elif row['validator'] == 'h1-unit-conflict.v1':
            from scripts.prospectus_h1_unit_integration import validate_submission as validate
        elif row['validator'] == 'bes-comparative-basis.v1':
            from scripts.prospectus_comparative_production import validate_submission as validate
        elif row['validator'] == 'exact-quantity-refusal.v1':
            from scripts.prospectus_exact_quantity import validate_submission as validate
        else:
            raise ValueError('Conditional validator not implemented')
        if validate(root, attempt, task) is not True:
            raise ValueError('Conditional evidence did not pass its substantive validator')
        passed.append(row['id'])
    return passed


def check_revision(old, new, review):
    """Scope changes cannot masquerade as ordinary same-delivery refinements."""
    before, after = old.get('build_contract'), new.get('build_contract')
    if before == after:
        return
    if (after is None or review.get('delivery_scope_changed') is not True
            or review.get('delivery_authorization') != after.get('authorization')
            or not review.get('original_obligations_preserved')):
        raise ValueError('Delivery scope change needs explicit user-directed review')
