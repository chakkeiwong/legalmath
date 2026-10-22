"""Reviewed coordinator repair; original product/source checks remain unchanged."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import signal
import sys
import time

from scripts import prospectus_margin_execution as execution
from scripts.prospectus_margin_preparation import ROOT, AUTH, MARGINS, read, save, sha, relative
from scripts import prospectus_margin_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest

OLD_PREP = AUTH / 'reviews/basf-margin-production-268'
PREP = AUTH / 'reviews/basf-margin-receipt-269'
OLD = MARGINS / 'attempt-004'
HERE = MARGINS / 'attempt-005'
PLAN = 'docs/plans/prospectus-basf-margin-receipt-repair-2026-10-18.md'
ORIGINAL_CASE = execution.save_case


def successful_scope_receipt(result):
    scope = result.get('status')
    if scope not in ('COMPLETE_REVIEWED_SCOPE', 'PARTIAL', 'UNREVIEWED'):
        raise ValueError('Unknown or failed scope classification cannot become PASS')
    return {**result, 'scope_status': scope, 'status': 'PASS'}


def save_case(*args):
    return successful_scope_receipt(ORIGINAL_CASE(*args))


def costs():
    prior = read(OLD / 'result.json')['resources']
    receipts = list(HERE.glob('stages/*/result.json')) if HERE.exists() else []
    measured = prior['new_measured_seconds'] + sum(read(p)['wall_seconds'] for p in receipts)
    # Original counted bytes include268 preparations, products, proposals and code.
    size = prior['new_counted_bytes']
    size += sum(p.stat().st_size for base in (PREP, HERE) if base.exists()
                for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    size += sum(p.stat().st_size for p in (Path(__file__), ROOT / PLAN,
        ROOT / 'tests/prospectus/test_margin_stage_receipts.py', AUTH / 'program.json', AUTH / 'revisions/0269.json') if p.exists())
    if measured >= 1400 or size >= 126 * 1024**2:
        raise ValueError('Cumulative printed-scope repair bound exhausted')
    return {'new_measured_seconds': measured, 'new_counted_bytes': size,
        'carried268_seconds': prior['new_measured_seconds'],
        'historical_measured_fields': prior['historical_measured_fields'],
        'unmeasured_authoring_controller_and_smoke_time': 'UNKNOWN',
        'previous_new_seconds_bound': 900, 'new_seconds_bound': 1400,
        'new_bytes_bound': 128 * 1024**2, 'reserved_bytes': 2 * 1024**2,
        'reason_for_bound_revision': 'Measured115s full baseline informs all remaining consumers and validation; no reset'}


def reuse_baseline():
    manifest = read(OLD / 'outputs.json')
    for name, expected in manifest.items():
        assert sha(OLD / name) == expected, 'Retained004 evidence changed'
    # All product and independent-oracle methods remain identical. Only registry
    # dispatch changes, from the original coordinator to this reviewed repair.
    for name, expected in read(OLD_PREP / 'freeze.json')['methods'].items():
        if name != 'src/legalmath/prospectus/execution_acceptance.py':
            assert sha(ROOT / name) == expected, 'Product/source/oracle changed since passing baseline'
    shutil.copyfile(OLD / 'baseline.json.gz', HERE / 'baseline.json.gz')
    p, answer = execution.retained('baseline')
    summary = oracle.verify(p, answer)
    execution.compare_ordinary(read(execution.DONOR / 'installed-answer/ordinary-answer.json.gz'), answer)
    save(HERE / 'baseline-reuse.json', {'source_attempt': relative(OLD),
        'source_outputs_sha256': sha(OLD / 'outputs.json'), 'source_baseline_sha256': manifest['baseline.json.gz'],
        'original_wall_seconds': read(OLD / 'stages/baseline/result.json')['wall_seconds'],
        'fresh_product_run': False, 'complete_reconstruction_and_independent_check': True,
        'product_and_oracle_methods_unchanged': True})
    return {**successful_scope_receipt(summary), 'baseline_reused': True}


def tests():
    import pytest
    paths = ['tests/prospectus/test_basf_printed_scope.py', 'tests/prospectus/test_margin_stage_receipts.py',
        'tests/prospectus/test_execution_acceptance.py', 'tests/prospectus/test_execution_authority.py',
        'tests/prospectus_successor/test_governing_interpretation.py',
        'tests/prospectus_successor/test_occurrence_lookup.py']
    if pytest.main(['-q', *paths, '--junitxml=' + str(HERE / 'tests.xml')]) != 0:
        raise ValueError('Reviewed receipt/scope/authority tests failed')
    return {'status': 'PASS'}


def configure():
    execution.PREP, execution.HERE, execution.PLAN = PREP, HERE, PLAN
    execution.costs, execution.save_case = costs, save_case
    execution.baseline, execution.tests = reuse_baseline, tests


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 268
    methods = dict(read(OLD_PREP / 'freeze.json')['methods'])
    methods['src/legalmath/prospectus/execution_acceptance.py'] = sha(ROOT / 'src/legalmath/prospectus/execution_acceptance.py')
    for path in (Path(__file__), ROOT / PLAN, ROOT / 'tests/prospectus/test_margin_stage_receipts.py'):
        methods[relative(path)] = sha(path)
    inputs = dict(read(OLD_PREP / 'freeze.json')['inputs'])
    for name in read(OLD / 'outputs.json'):
        inputs[relative(OLD / name)] = sha(OLD / name)
    inputs[relative(OLD / 'outputs.json')] = sha(OLD / 'outputs.json')
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs,
        'reused_baseline': relative(OLD / 'baseline.json.gz'),
        'production_methods_changed': False, 'receipt_repair_only': True})
    proposal = deepcopy(program)
    proposal['revision'] = 269
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-margins')
    task['dossier'] = PLAN
    task['reason'] = 'Preserve failed004 receipt and verified baseline; correct stage status and execute remaining actual consumers under cumulative original-task limits'
    task['printed_scope_acceptance'].update(review=relative(PREP),
        bounds={'stage_seconds': 180, 'new_seconds': 1400, 'new_bytes': 128 * 1024**2},
        receipt_repair={'previous_attempt': relative(OLD), 'baseline_reused': True, 'further_harness_retry_allowed': False})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-margins']['maximum_new_attempts'] = 5
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 269
    row = next(r for r in routes['tasks'] if r['task'] == 'basf-margins')
    row.update(remaining='004 complete source/product baseline passed but stage status was overwritten; receipt defect is retained.',
        next_action='Reuse verified004 baseline and execute the remaining source/consumer controls with corrected receipts.',
        dossier=PLAN, task_sha256=authority_digest(task))
    save(PREP / 'routes.json', routes)
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = relative(PREP / 'routes.json')
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'), relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-margins']
    review = {'baseline': authority_digest(program), 'changes': ['Repair stage receipt; preserve original coordinator and product methods',
        'Verify and reuse004 full baseline; continue all original controls', 'Explicitly carry costs forward and revise measured cumulative ceiling before admission'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'cause': 'Successful scope label overwrote worker PASS',
            'production_and_oracle_unchanged': True, 'known_previous_seconds': costs()['new_measured_seconds']},
        'evidence_contract': {'question': 'Does the original complete scope reach ordinary answers with required refusals?',
            'primary': 'Unchanged original54-group/522-occurrence full answer comparison and independent source checks',
            'veto': ['Source/product/oracle drift', 'Failed actual consumer/control', 'New harness failure', 'Bounds exceeded'],
            'not_concluded': ['Whole legal contract', 'Automatic discovery', 'Source authenticity', 'Whole build']},
        'scope_unchanged': True, 'budget_unchanged': False,
        'budget_revision': {'budget_key': 'basf-margins', 'previous_maximum': 4, 'new_maximum': 5,
            'retained_attempts': attempts, 'reason': 'Diagnosed receipt defect; changed repair and verified reuse, not an unchanged rerun',
            'next_discriminating_check': 'Missing-family and malformed/resealed scope consumers',
            'stop_condition': '180s stages;1400s cumulative from original268 preparation;128MiB; no further harness retry',
            'same_scope_authorization': 'User directed refreshed program and continuing execution'},
        'original_obligations_preserved': True}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    print(json.dumps({'status': 'PASS', 'revision': 269, 'methods': len(methods), 'resources': costs()}))


def validate_submission(root, attempt, task):
    configure()
    return execution.validate_submission(root, attempt, task)


def main():
    label = sys.argv[1]
    configure()
    if label == 'prepare':
        prepare()
        return
    if label not in execution.STAGES:
        raise ValueError('Unknown reviewed scope stage')
    execution.frozen()
    assert (HERE / 'admission.json').is_file()
    index = execution.STAGES.index(label)
    if index:
        assert read(HERE / 'stages' / execution.STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    costs()
    began = time.monotonic()
    folder = HERE / 'stages' / label
    save(folder / 'started.json', {'command': [str(ROOT / '.venv/bin/python'), '-m',
        'scripts.prospectus_margin_receipt_repair', label], 'started_at': datetime.now(timezone.utc).isoformat(),
        'stage_seconds_bound': 180, 'freeze_sha256': sha(PREP / 'freeze.json')})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Scope repair180s stage bound')))
    signal.alarm(180)
    try:
        result = execution.omission(label) if label.startswith('omit-') else getattr(execution, label.replace('-', '_'))()
        if result.get('status') != 'PASS':
            raise ValueError('Successful worker must return PASS independently of scope classification')
        execution.frozen()
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
