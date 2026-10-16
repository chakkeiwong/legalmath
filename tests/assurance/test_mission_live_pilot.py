"""Grant and dispatch invariants for the actual paired-answer pilot; no live API."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Completion
from scripts import legal_mission_live_pilot as pilot


@pytest.fixture
def grant(tmp_path, monkeypatch):
    start = int(datetime.fromisoformat(pilot.START).timestamp()) + 10
    monkeypatch.setattr(pilot.time, 'time', lambda: start)
    monkeypatch.setattr(pilot.time, 'time_ns', lambda: start * 10**9)
    prior = tmp_path / 'prior.json'
    prior.write_text(json.dumps({'maximum': 200, 'calls': [
        {'batch': 17, 'role': 'source-first', 'purpose': 'combined',
         'request_hash': 'a' * 64, 'issued_at_ns': '1'}] * 49}))
    prior_grant = tmp_path / 'old-authorization.json'
    prior_grant.write_text(json.dumps({'schema': 'legalmath.coverage-resumption-grant.v1',
        'maximum': 200, 'deadline_epoch': start - 100, 'predecessor': [pilot.ref(prior, tmp_path)]}))
    marker = tmp_path / 'review.md'; marker.write_text('Synthetic reviewed plan, no service calls.')
    out = tmp_path / 'pilot'; out.mkdir()
    pilot.save(out / 'authorization.json', {'schema': 'legalmath.mission-pilot-grant.v1',
        'authorization': pilot.AUTHORIZATION, 'maximum': 400, 'started_utc': pilot.START,
        'deadline_utc': pilot.END, 'allocations': {a: pilot.STAGES for a in pilot.ARMS},
        'optional_assessment_calls': 1, 'unallocated_calls': 25, 'historical_unused_transfer': False,
        'historical_ledger': pilot.ref(prior, tmp_path), 'historical_authorization': pilot.ref(prior_grant, tmp_path),
        'plan': pilot.ref(marker, tmp_path), 'specification': pilot.ref(marker, tmp_path),
        'protected_allowance': pilot.ref(marker, tmp_path)})
    pilot.save(out / 'allowance.json', {'maximum': 400, 'calls': []})
    return tmp_path, out, prior


def allowance(grant, arm='baseline'):
    root, out, _ = grant
    return pilot.PilotAllowance(arm, root=root, directory=out)


def test_expired_specialized_predecessor_preserved_and_not_transferred(grant):
    a = allowance(grant); before = grant[2].read_bytes()
    assert a.reserve('b' * 64) == 1
    assert a.verify()['expired_unused'] == 151
    assert a.maximum == 400 and a.reservation_ceiling == 374
    assert grant[2].read_bytes() == before


def test_arm_cannot_borrow_other_arm_or_stage_reservations(grant):
    a = allowance(grant); b = allowance(grant, 'candidate')
    a.stage = b.stage = 'synthesis'
    assert a.reserve('b' * 64) == 1
    with pytest.raises(LegalMathError) as caught:
        a.reserve('c' * 64)
    assert caught.value.code == 'E_RESOURCE_LIMIT'
    assert b.reserve('c' * 64) == 2
    assert a.verify()['used'] == 2


def test_concurrent_last_stage_slot_is_not_overspent(grant):
    def reserve(_):
        a = allowance(grant); a.stage = 'interaction'
        try:
            return a.reserve('b' * 64)
        except LegalMathError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(reserve, range(8)))
    assert result.count(1) == 1 and result.count('E_RESOURCE_LIMIT') == 7


@pytest.mark.parametrize('target', ['old', 'grant', 'ledger', 'plan'])
def test_changed_grant_or_history_cannot_dispatch(grant, target):
    a = allowance(grant)
    root, out, prior = grant
    if target == 'old':
        prior.write_text('{}')
    elif target == 'plan':
        (root / 'review.md').write_text('changed')
    elif target == 'grant':
        g = pilot.read(a.grant_path); g['maximum'] = 401; pilot.save(a.grant_path, g)
    else:
        pilot.save(a.path, {'maximum': 401, 'calls': []})
    with pytest.raises(LegalMathError):
        a.reserve('b' * 64)


def test_deadline_has_no_restart_extension(grant, monkeypatch):
    a = allowance(grant)
    monkeypatch.setattr(pilot.time, 'time', lambda: datetime.fromisoformat(pilot.END).timestamp())
    with pytest.raises(LegalMathError) as caught:
        a.reserve('b' * 64)
    assert caught.value.code == 'E_RESOURCE_LIMIT'
    assert allowance(grant).verify()['used'] == 0


@pytest.mark.parametrize('task,stage', [
    ('DEFINE_EXACT_QUESTIONS', 'question_assignment'), ('SCOPED_SOURCE_FIDELITY', 'scoped'),
    ('REVIEW_DOSSIER_EVIDENCE', 'dossier_reviews'), ('REVIEW_DOSSIER_INTERACTIONS', 'interaction'),
    ('SYNTHESIZE_WHOLE_DOSSIER_ANSWER', 'synthesis'), ('GENERATE', 'core')])
def test_output_repairs_remain_in_original_stage(task, stage):
    assert pilot.stage_for({'task': task}) == stage
    assert pilot.stage_for({'task': 'REPAIR_OUTPUT', 'original_task': task}) == stage


def test_provider_clips_global_clock_and_stops_after_transport_failure(grant, monkeypatch):
    a = allowance(grant)
    monkeypatch.setattr(pilot, 'check_frozen', lambda *args: None)
    p = pilot.PilotProvider(allowance=a)
    monkeypatch.setattr(a, 'remaining_seconds', lambda: 7)
    seen = []
    def failed(self, request, schema, settings):
        seen.append(settings.timeout_seconds)
        self.allowance.reserve(digest(request))
        raise LegalMathError('E_DEPENDENCY', details='stream disconnected')
    monkeypatch.setattr(pilot.CodexProvider, 'complete', failed)
    with pytest.raises(LegalMathError):
        p.complete({'task': 'GENERATE'}, {}, Settings(timeout_seconds=300))
    with pytest.raises(LegalMathError):
        p.complete({'task': 'DEFINE_EXACT_QUESTIONS'}, {}, Settings(timeout_seconds=300))
    assert seen == [7] and a.verify()['used'] == 1


def test_pilot_clock_changes_no_ordinary_default():
    assert pilot.AssuranceSettings().deadline_seconds == 3000
    assert pilot.PilotSettings().deadline_seconds == 10800


def test_operational_history_and_existing_tool_symlink_are_retained(tmp_path):
    target = tmp_path / 'environment' / 'python'
    target.parent.mkdir(); target.write_bytes(b'read-only tool identity')
    root = tmp_path / 'worktree'; root.mkdir()
    link = root / 'tool'; link.symlink_to(target)
    assert pilot.checked(pilot.ref(link, root), root).read_bytes() == target.read_bytes()
    history = root / 'history.json'
    pilot.save(history, {'historical_deadline': 1791519402.34676})
    assert pilot.read(history)['historical_deadline'] == 1791519402.34676


def test_execution_does_not_repeat_terminal_or_interrupted_run(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, 'OUT', tmp_path)
    monkeypatch.setattr(pilot, 'check', lambda: None)
    pilot.save(tmp_path / 'result.json', {'status': 'PAIR_UNAVAILABLE', 'used_calls': 1})
    assert pilot.execute()['used_calls'] == 1
    (tmp_path / 'result.json').unlink()
    pilot.save(tmp_path / 'execution-started.json', {'epoch_seconds': 1})
    with pytest.raises(LegalMathError) as caught:
        pilot.execute()
    assert caught.value.code == 'E_JOB_STATE'


def test_source_span_continuation_cannot_spend_withheld_candidate_core_slots(grant):
    from scripts.legal_mission_pilot_source_spans import SpanAllowance
    root, out, _ = grant
    original = allowance(grant)
    for _ in range(4):
        original.reserve('a' * 64)
    before = pilot.read(original.path)['calls'][:]
    for arm in pilot.ARMS:
        a = SpanAllowance(arm, root=root, directory=out)
        for _ in range(32):
            a.reserve('b' * 64)
        with pytest.raises(LegalMathError) as caught:
            a.reserve('c' * 64)
        assert caught.value.code == 'E_RESOURCE_LIMIT'
    assert pilot.read(original.path)['calls'][:4] == before
    assert original.verify()['used'] == 68


def test_actual_reference_failure_remains_rejected_and_nbsp_is_preserved():
    from scripts.legal_mission_pilot_source_spans import qualify
    result = qualify()
    assert result['new_calls'] == 0 and result['nbsp_preserved']
    assert result['foreign_span_rejected'] and result['omission_and_wrong_link_still_rejected']
    assert result['complete_workflow_capacity'] == 'NOT_ESTABLISHED'
    assert all(row['span_readable_bytes'] < 200000 and row['round_trip_exact'] for row in result['rows'])


def test_decomposed_profile_preserves_qualified_full_source_and_equal_remaining_effort(grant):
    from scripts import legal_mission_pilot_source_spans as revision
    root, out, _ = grant
    try:
        revision.select('decomposed')
        a = allowance(grant)
        for _ in range(5): a.reserve('a' * 64)
        for arm in pilot.ARMS:
            scoped = revision.SpanAllowance(arm, root=root, directory=out)
            for _ in range(31): scoped.reserve('b' * 64)
            with pytest.raises(LegalMathError): scoped.reserve('c' * 64)
        result = revision.qualify()
        assert result['minimum_inventory_calls'] == 12 and result['cross_piece_review_required']
        assert result['all_55_units_preserved_in_order']
        assert all(p['wire_bytes'] < 200000 and p['source_qualification_preserved']
                   and p['round_trip_exact'] for p in result['pieces'])
    finally:
        revision.select('source-spans')
