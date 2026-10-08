from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_evidence_completion as completion
import assurance_evidence_core as c
import assurance_evidence_extension as ex
import assurance_evidence_next_phase as n
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
from contextlib import contextmanager

@contextmanager
def raises_code(code):
    try:
        yield
    except LegalMathError as exc:
        assert exc.code == code
    else:
        pytest.fail('Expected '+code)



@pytest.fixture
def root(tmp_path):
    now = datetime.now(timezone.utc)
    c.save(tmp_path/ex.RUN/'authorization.json', {'baseline_used': 95, 'maximum': 100,
        'repair_maximum': 20, 'issue_limit': 4, 'final_issue_limit': 20,
        'attempts_per_task': 2, 'old_unused_calls_carried': 0,
        'starts_at': (now-timedelta(minutes=1)).isoformat(),
        'ends_at': (now+timedelta(hours=1)).isoformat(),
        'baseline_issue_spending': {}, 'allowed_issues': ['issue.0', 'issue.1'],
        'protected_checkpoint': []})
    return tmp_path


def reserve(root, number):
    return ex.Allowance(root, {'id': 'task.'+str(number), 'phase': 'propagation',
        'issues': ['issue.'+str(number)]}).reserve(digest(number))


def checkpoint(root):
    reserve(root, 0)
    before = ex.Allowance(root).verify()
    return {'allowance_before': before, 'allowance_after': before,
        'provider_calls': 0, 'repair_calls': 0}, c.receipt(root/ex.RUN/'allowance.json', root)


def test_historical_diagnostic_accepts_legitimate_appended_spending(root):
    report, ref = checkpoint(root)
    reserve(root, 1)
    assert raw_digest((root/ex.RUN/'allowance.json').read_bytes()) != ref['sha256']
    completion.check_historical_allowance(root, ex, report, ref)
    assert ex.Allowance(root).verify()['used'] == 2


def test_historical_diagnostic_rejects_consistent_rewrite_of_prefix(root):
    report, ref = checkpoint(root)
    path = root/ex.RUN/'reservations/0096.json'
    value = c.read(path)
    value['call']['request_hash'] = 'a'*64
    c.save(path, value)
    projection = root/ex.RUN/'allowance.json'
    value = c.read(projection)
    value['calls'][0]['request_hash'] = 'a'*64
    c.save(projection, value)
    ex.Allowance(root).verify()  # Internally consistent journal, different history.
    with raises_code('E_INTEGRITY'):
        completion.check_historical_allowance(root, ex, report, ref)


@pytest.mark.parametrize('damage', ['truncate', 'projection'])
def test_historical_diagnostic_rejects_removed_or_inconsistent_calls(root, damage):
    report, ref = checkpoint(root)
    if damage == 'truncate':
        (root/ex.RUN/'reservations/0096.json').unlink()
        c.save(root/ex.RUN/'allowance.json', {'authorization_hash':
            raw_digest((root/ex.RUN/'authorization.json').read_bytes()), 'calls': []})
    else:
        value = c.read(root/ex.RUN/'allowance.json')
        value['calls'][0]['request_hash'] = 'b'*64
        c.save(root/ex.RUN/'allowance.json', value)
    with raises_code('E_INTEGRITY'):
        completion.check_historical_allowance(root, ex, report, ref)


def inputs():
    inventory = [{'role': role, 'reading_id': 'reading.'+str(i),
        'status': 'CANDIDATE_DIAGNOSTIC_ONLY' if i < 10 else 'UNFORMALIZED_WITH_OPEN_CONDITIONS',
        'baseline_program_present': i < 10, 'required_program_repairs': ['Preserve unknown inputs.']}
        for role in c.ROLES for i in range(35)]
    obligations = [{'obligation': {'obligation_id': 'obligation.'+str(i),
        'dimension': 'authority', 'candidate_ids': ['reading.'+str(i % 35)]},
        'current_responses': {r: {'followup_question': 'Which rules apply on 20 April 2026?',
            'status': 'UNRESOLVED'} for r in c.ROLES}} for i in range(46)]
    definitions = [{'id': 'final.'+role+'.'+str(i), 'role': role,
        'issues': ['final.dispositions.'+role] if i else ['final.engineering.'+role]}
        for role in c.ROLES for i in range(13)]
    rows = [{'task': t['id'], 'role': t['role'], 'phase': 'final', 'issues': t['issues'],
        'attempt': 1, 'allowance_slot': 100+i, 'status': 'FAILED' if i < 11 else 'VALIDATED',
        'details': 'Qualified finding claimed full closure' if i < 9 else
            'Evidence must occur exactly once in its supplied unit' if i < 11 else '',
        'receipt': {'path': 'example.json', 'sha256': '0'*64},
        'value': {'findings': [{'status': 'PARTIALLY_SUPPORTED', 'answer': 'Keep the question open.'}]}}
        for i, t in enumerate(definitions)]
    allowance = {'remaining': 54, 'repair_remaining': 0, 'ends_at': '2099-01-01',
        'task_spending': {t['id']: 1 for t in definitions},
        'new_issue_spending': {'final.dispositions.'+r: 12 for r in c.ROLES}}
    return inventory, obligations, definitions, rows, allowance


def test_queue_preserves_every_identity_finding_and_separate_budget():
    args = inputs()
    work = n.assemble(*args, now='2026-10-03')
    assert work['counts']['program_repairs'] == 20
    assert work['counts']['failed_final_audits'] == 11
    assert work['counts']['failure_classes'] == {
        'CLOSURE_STATUS_CONTRADICTION': 9, 'NON_SOURCE_QUOTATION': 2}
    assert work['budget']['current_evidence_review_repair_shortfall'] == 26
    assert set(work['budget']['current_evidence_review_issue_shortfalls'].values()) == {4}
    assert len(work['evidence_requests']) == 46 and work['assessment_period'] is None
    assert all(a['counted_repair'] and not a['dispatch_authorized'] for a in work['final_audits'])
    assert all(a['validated_findings'] for a in work['final_audits'][11:])
    assert [r['current_responses'] for r in work['evidence_requests']] == [r['current_responses'] for r in args[1]]
    assert work['accepted_program_repairs'] == 0 and not work['release_eligible']


@pytest.mark.parametrize('part', [0, 1, 2, 3])
def test_queue_refuses_incomplete_or_duplicate_coverage(part):
    args = list(inputs())
    args[part] = deepcopy(args[part][1:])
    if part == 0:
        args[part].append(deepcopy(args[part][0]))
    with raises_code('E_INTEGRITY'):
        n.assemble(*args, now='2026-10-03')


def test_local_execution_disables_dispatch_and_restarts_without_spending(root, monkeypatch):
    from legalmath.interpretation.search.providers import CodexProvider
    inventory, obligations, definitions, rows, _ = inputs()
    reserve(root, 0)
    checkdir = root/ex.RUN/'checks-current-v3'
    c.save(checkdir/'result.json', {})
    c.save(checkdir/'program-inventory.json', inventory)
    c.save(root/c.OLD/'remaining-obligations.json', obligations)
    c.save(root/ex.RUN/'final/task-definitions.json', definitions)
    c.save(root/ex.RUN/'final/coverage.json', [{'role': r['role'], 'reading_id': r['reading_id']} for r in inventory])
    for path in (root/n.PLAN, root/n.AUDIT_PLAN, root/ex.POLICY, root/'revision.json', root/'diagnostic.json'):
        c.save(path, {})
    c.save(root/ex.RUN/'active-revision.json', {'receipt': c.receipt(root/'revision.json', root)})
    c.save(root/ex.RUN/'current-diagnostic.json', {'receipt': c.receipt(root/'diagnostic.json', root)})
    for row in rows:
        path = root/'retained'/row['task']
        c.save(path, {})
        row['receipt'] = c.receipt(path, root)
    monkeypatch.setattr(completion, 'adopted_diagnostic', lambda r, e: {'current': c.receipt(checkdir/'result.json', root)})
    monkeypatch.setattr(ex, 'verify', lambda r: {'frozen_root': str(Path(n.__file__).resolve().parents[1]), 'git_commit': 'test'})
    class Engine:
        def task_rows(self, root): return rows
        def state(self, root): return {'phases': {p: {'status': 'COMPLETED'} for p in ex.PHASES}}
    monkeypatch.setattr(ex, 'engine', Engine)
    real_assemble = n.assemble
    def guarded(*args, **kwargs):
        with raises_code('E_AUTHORITY'):
            CodexProvider.complete(None, None, None, None)
        with raises_code('E_AUTHORITY'):
            reserve(root, 1)
        return real_assemble(*args, **kwargs)
    monkeypatch.setattr(n, 'assemble', guarded)
    before = ex.Allowance(root).verify()
    first = n.execute(root, ex)
    assert first == n.execute(root, ex)
    assert ex.Allowance(root).verify() == before
    # A crash after writing outputs but before sealing must also resume safely.
    (root/first['receipt']['path']).unlink()
    assert n.execute(root, ex) == first
    path = root/Path(first['receipt']['path']).parent/'work-items.json'
    c.save(path, {'release_eligible': True})
    with raises_code('E_INTEGRITY'):
        n.execute(root, ex)


def test_prepare_keeps_initial_requests_when_prompt_builder_changes(root, monkeypatch):
    for name in ('baseline-accepted.json', 'initial-tasks.json'):
        c.save(root/ex.RUN/name, [{'original': name}])
    grant = c.read(root/ex.RUN/'authorization.json')
    grant['protected_checkpoint'] = [c.receipt(root/ex.RUN/name, root)
        for name in ('baseline-accepted.json', 'initial-tasks.json')]
    c.save(root/ex.RUN/'authorization.json', grant)
    monkeypatch.setattr(ex.old, 'verify', lambda r: None)
    class OldAllowance:
        def __init__(self, root): pass
        def verify(self): return {'used': 95}
    monkeypatch.setattr(ex.old, 'Allowance', OldAllowance)
    monkeypatch.setattr(ex.old, 'consecutive_failures', lambda r: 0)
    monkeypatch.setattr(ex, 'initial_tasks', lambda r: pytest.fail('Do not rebuild initial requests'))
    monkeypatch.setattr(ex.old, 'accepted_rows', lambda r: pytest.fail('Do not rebuild protected baseline'))
    ex.prepare(root)
    assert c.read(root/ex.RUN/'initial-tasks.json') == [{'original': 'initial-tasks.json'}]
    c.save(root/ex.RUN/'initial-tasks.json', [{'changed': True}])
    with raises_code('E_INTEGRITY'):
        ex.prepare(root)
