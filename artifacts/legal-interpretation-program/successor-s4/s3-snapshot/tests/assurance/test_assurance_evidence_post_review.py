from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import assurance_evidence_core as c
import assurance_evidence_continuation as old
import assurance_evidence_extension as ex
import assurance_evidence_master as master
import assurance_evidence_guarded as guard
import assurance_evidence_current_review as packets
import assurance_evidence_review_runtime as runtime
import assurance_evidence_post_review as post
from legalmath.canonical import digest
from test_assurance_evidence_continuation import root as legacy_root, task, retained, error
from test_assurance_evidence_extension import root as extension_root, task as ext_task, retained as ext_retained
from test_assurance_evidence_guarded import FORMAL, CID, EVIDENCE


REPO = Path('/home/chakwong/python/legalmath')


def test_actual_dispositions_preserve_sources_formulas_questions_and_provenance():
    folder = packets.verified(REPO, ex)
    tasks = c.read(folder/'task-definitions.json')
    before = digest(tasks)
    entries, counts = post.derive(tasks)
    assert digest(tasks) == before
    assert len(entries) == 70 and counts['question_status'] == 10 and counts['editorial'] == 13
    assert counts['assessment_period'] > 0
    changed_ids = set()
    for entry in entries:
        original, operative = entry['original'], entry['operative']
        assert original['original_reading'] == operative['original_reading']
        for key in ('question_texts', 'prior_program', 'candidate_repair', 'retained_prior_assumptions', 'retained_prior_questions'):
            assert operative[key] == original[key]
        replay = post.expand(original)
        for change in entry['changes']:
            parent = replay
            for key in change['path'][:-1]:
                parent = parent[key]
            assert parent[change['path'][-1]] == change['before']
            parent[change['path'][-1]] = change['after']
            if change['kind'] == 'question_status':
                q = operative['questions'][change['path'][1]]
                changed_ids.add((entry['reading_id'], q['question_id']))
                assert entry['role'] == 'exception-challenger' and q['status'] == 'REMAINS_OPEN'
            if change['kind'] == 'assessment_period':
                assert change['path'][0] == 'obligations' and change['path'][2] == 'needed_evidence'
                assert '20 April 2026' not in change['after']
                assert 'independently established assessment period' in change['after']
        assert replay == operative
        assert all(not o['original_question_answered'] for o in operative['obligations'])
    assert changed_ids == {(cid, q) for cid, questions in post.OPEN_QUESTIONS.items() for q in questions}


@pytest.mark.parametrize('state', ['missing', 'unknown', 'conflict', 'false'])
@pytest.mark.parametrize('applicable', [True, False])
def test_applicability_ownership_dependency_cannot_bypass_inventory(state, applicable):
    case = guard.synthetic_case(FORMAL, CID)
    for judgment in case['facts'].values():
        judgment['depends_on_ownership'] = False
    case['applicability'].update(depends_on_ownership=True, value=applicable)
    if state == 'missing':
        case['ownership_inventory'] = {}
    elif state == 'false':
        case['ownership_inventory']['reconciliation']['value'] = False
    else:
        case['ownership_inventory']['reconciliation'] = {'status': state}
    answer = guard.evaluate(FORMAL, case, role='structure-reader', reading_id=CID,
        evidence=EVIDENCE, check_reference=lambda ref: None)
    assert answer['status'] == 'UNRESOLVED' and answer['value'] is None
    assert answer['reasons'][0].startswith('APPLICABILITY:OWNERSHIP_INVENTORY_')


def test_missing_receipt_recovers_offline_and_preserves_charge(legacy_root, monkeypatch):
    root = legacy_root
    t = task()
    retained(root, t)
    original = old.attempt(root, t)
    receipt = root/original['receipt']['path']
    before = old.Allowance(root).verify()
    receipt.unlink()
    monkeypatch.setattr(old.CodexProvider, 'complete', lambda *a, **kw: pytest.fail('No dispatch'))
    rows = old.task_rows(root)
    assert len(rows) == 1 and rows[0]['value'] == original['value']
    assert rows[0]['receipt'] == original['receipt']
    assert old.Allowance(root).verify() == before


@pytest.mark.parametrize('detach', ['slot', 'provider'])
def test_missing_receipt_cannot_adopt_detached_evidence(legacy_root, detach):
    root = legacy_root
    t = task()
    provider = retained(root, t)
    result = old.attempt(root, t)
    receipt = root/result['receipt']['path']
    receipt.unlink()
    if detach == 'slot':
        path = receipt.with_name('result.json')
        row = c.read(path); row['allowance_slot'] += 1; c.save(path, row)
    else:
        c.save(provider/'result.json', {})
    with error('E_INTEGRITY'):
        old.task_rows(root)
    assert not receipt.exists()
    assert old.Allowance(root).verify()['used'] == 41


def test_invalid_reservations_leave_no_journal(legacy_root, monkeypatch):
    t = task(); t['issues'] *= 2
    with error('E_AUTHORITY'):
        old.Allowance(legacy_root, t).reserve('1'*64)
    monkeypatch.setattr(c, 'now', lambda: '1900-01-01T00:00:00+00:00')
    with error('E_RESOURCE_LIMIT'):
        old.Allowance(legacy_root, task()).reserve('2'*64)
    assert list((legacy_root/old.RUN/'reservations').glob('*.json')) == []
    assert old.Allowance(legacy_root).verify()['used'] == 40


def test_master_failure_streak_includes_corrections_and_formal_repairs(tmp_path, monkeypatch):
    calls = [{'slot': i} for i in range(1, 5)]
    rows = [(4, 'formal-repair', 1, 'E_DEPENDENCY'), (1, 'first', 1, None),
        (2, 'corrected', 1, 'E_SCHEMA'), (3, 'corrected', 2, 'E_DEPENDENCY')]
    for slot, task_id, attempt, err in rows:
        c.save(tmp_path/c.BASE/'tasks'/task_id/f'attempt-{attempt:02}'/'result.json',
            {'allowance_slot': slot, 'error': err})
    monkeypatch.setattr(master, 'check_attempt', lambda root, folder: c.read(folder/'result.json'))
    monkeypatch.setattr(c, 'EvidenceAllowance', lambda root: SimpleNamespace(_load=lambda: {'calls': calls}))
    assert master.charged_failure_streak(tmp_path) == 2
    calls.append({'slot': 5})
    assert master.charged_failure_streak(tmp_path) == 3
    c.save(tmp_path/c.BASE/'tasks'/'successful'/'attempt-01'/'result.json', {'allowance_slot': 5})
    assert master.charged_failure_streak(tmp_path) == 0


def test_saved_extension_success_replays_under_dependency_veto(extension_root, monkeypatch):
    root = extension_root
    t = ext_task()
    ext_retained(root, t)
    rt = ex.engine()
    original = rt.attempt(root, t)
    monkeypatch.setattr(rt, 'consecutive_failures', lambda root: 2)
    monkeypatch.setattr(ex, 'engine', lambda: rt)
    monkeypatch.setattr(old.CodexProvider, 'complete', lambda *a, **kw: pytest.fail('No dispatch'))
    assert ex.run_task(root, t) == original
    assert ex.Allowance(root).verify()['used'] == 1


def test_saved_program_repair_replays_before_issue_cap(legacy_root, monkeypatch):
    root = legacy_root
    t = task()
    c.save(root/old.RUN/'initial-tasks.json', [t])
    repaired = deepcopy(t)
    repaired.update(id=t['id']+'.program-repair', program_repair=True)
    retained(root, repaired)
    saved = old.attempt(root, repaired)
    c.save(root/old.RUN/'program-repairs'/(repaired['id']+'.json'), repaired)
    row = {'task': t['id'], 'phase': 'propagation', 'value': {'reading_updates': []}}
    monkeypatch.setattr(old, 'accepted_rows', lambda root: [row])
    request = deepcopy(repaired); request['request']['selected'] = ['fixture']
    monkeypatch.setattr(old.phases, 'formal_repair_task', lambda *args: request)
    later = deepcopy(t); later['id'] += '.later'
    old.Allowance(root, later, correction=True).reserve('e'*64)
    monkeypatch.setattr(old.CodexProvider, 'complete', lambda *a, **kw: pytest.fail('No dispatch'))
    assert old.execute_program_repairs(root)
    frontier = c.read(root/old.RUN/'program-repair-frontier.json')
    assert frontier[0]['status'] == 'VALIDATED' and frontier[0]['receipt'] == saved['receipt']
    assert old.Allowance(root).verify()['used'] == 42


def test_dispatch_summary_respects_reserve_failure_veto_and_completion():
    tasks = [{'id': 'a', 'issues': ['final.x'], 'review_phase': 'engineering'}]
    state = {'remaining': 8, 'repair_remaining': 4, 'correction_remaining': 4,
        'task_spending': {}, 'new_issue_spending': {}}
    phases = {'halt': None, 'phases': {}}
    eligible = lambda **kw: runtime.dispatchable_tasks(tasks, kw.get('state', state),
        kw.get('latest', {}), kw.get('phases', phases), kw.get('streak', 0), kw.get('active', True))
    assert eligible() == ['a']
    assert not eligible(streak=2) and not eligible(active=False)
    assert not eligible(state={**state, 'remaining': 2})
    assert not eligible(state={**state, 'new_issue_spending': {'final.x': 50}})
    assert not eligible(phases={'halt': None, 'phases': {'engineering': {'status': 'COMPLETED'}}})
    spent = {**state, 'task_spending': {'a': 1}}
    assert not eligible(state=spent, latest={'a': {'status': 'VALIDATED'}})
    failed = {'a': {'status': 'FAILED', 'error': 'E_SCHEMA'}}
    assert eligible(state=spent, latest=failed) == ['a']
    assert not eligible(state={**spent, 'correction_remaining': 0}, latest=failed)


def test_local_receipt_tampering_blocks_summary(tmp_path):
    folder = tmp_path/ex.RUN/post.SUBDIR/'fixture'
    names = ['dispositions.json', 'findings.json', 'result.json', 'run-manifest.json', 'next-phase-plan.json', 'next-phase-plan.md', 'result.md']
    for name in names:
        c.save(folder/name, {'provider_calls': 0})
    c.save(folder/'completion-receipt.json', {'inputs': [], 'files': master.files_in(folder, tmp_path, ('completion-receipt.json',))})
    ref = c.receipt(folder/'completion-receipt.json', tmp_path)
    c.save(tmp_path/ex.RUN/'current-post-review-repairs.json', {'receipt': ref})
    assert post.summary(tmp_path, ex)['provider_calls'] == 0
    c.save(folder/'dispositions.json', {'tampered': True})
    with error('E_INTEGRITY'):
        post.summary(tmp_path, ex)
