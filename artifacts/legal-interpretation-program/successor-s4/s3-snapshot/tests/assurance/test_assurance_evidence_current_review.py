from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_evidence_core as c
import assurance_evidence_extension as ex
import assurance_evidence_current_review as packets
import assurance_evidence_review_runtime as runtime
import assurance_evidence_protocol as protocol
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_assurance_evidence_extension import root, reserve, code_error


def task(i=0, role='structure-reader'):
    value = protocol.make_task('final', role, ['final.dispositions.'+role], {
        'kind': 'review', 'source_packet': {'units': [{'unit_id': 'source', 'text': 'Complete source.'}]},
        'questions': [{'id': 'question', 'missing': 'What remains unresolved?'}]})
    value.update(id='current-review.test.'+str(i), counted_repair=True,
        predecessors=['retained.previous.'+str(i)], review_phase='engineering' if i < 2 else 'dispositions')
    return value


@pytest.fixture
def prepared(root, request):
    grant_path = root/ex.RUN/'authorization.json'
    grant = c.read(grant_path)
    grant['allowed_issues'].append('final.dispositions.exception-challenger')
    c.save(grant_path, grant)
    for i in range(46):
        reserve(root, i, i < 20)
    base = ex.Allowance(root)
    folder = root/runtime.RUN/'packages/test'
    tasks = [task(i, c.ROLES[i % 2]) for i in range(getattr(request, 'param', 6))]
    for name, value in [('task-definitions.json', tasks), ('coverage.json', []),
            ('preflight.json', packets.preflight(tasks, base.verify())), ('run-manifest.json', {'frozen_root': str(Path(runtime.__file__).resolve().parents[1])})]:
        c.save(folder/name, value)
    proposal = {'status': 'PROPOSED_NOT_APPROVED', 'requested_window_hours': 48, 'maximum': 100, 'repair_maximum': 50,
        'final_disposition_limit': 50, 'other_final_issue_limit': 50, 'attempts_per_task': 2,
        'ends_at': base.grant['ends_at'], 'baseline': base.verify(), 'baseline_calls': base.ledger(),
        'old_unused_calls_carried': 0, 'count_all_current_review_calls_as_repairs': True,
        'tasks': c.receipt(folder/'task-definitions.json', root),
        'preflight': c.receipt(folder/'preflight.json', root)}
    c.save(folder/'proposed-amendment.json', proposal)
    c.save(folder/'completion-receipt.json', {'inputs': [c.receipt(root/ex.RUN/'allowance.json', root)],
        'files': ex.master.files_in(folder, root, ('completion-receipt.json',))})
    c.save(root/runtime.RUN/'prepared.json', {'receipt': c.receipt(folder/'completion-receipt.json', root)})
    return root, folder, tasks


def approve(prepared):
    root, folder, _ = prepared
    timestamp = c.now()
    proposal = c.read(folder/'proposed-amendment.json')
    c.save(root/runtime.AUTHORIZATION, {**{k: proposal[k] for k in ('requested_window_hours', 'maximum', 'repair_maximum', 'final_disposition_limit', 'other_final_issue_limit', 'attempts_per_task', 'old_unused_calls_carried', 'count_all_current_review_calls_as_repairs')}, 'status': 'APPROVED_BY_USER',
        'window_renewal': True, 'ends_at': (datetime.fromisoformat(timestamp)+timedelta(hours=48)).isoformat(),
        'approval_text': 'TEST FIXTURE ONLY: grouped amendment and 48-hour renewal approved.', 'approved_at': timestamp,
        'proposal': c.receipt(folder/'proposed-amendment.json', root),
        'prepared': c.receipt(folder/'completion-receipt.json', root)})


def charged(root, value):
    return runtime.Allowance(root, value).reserve(digest(protocol.transport(value)[0]))


def test_case_compression_preserves_unknown_removals_and_complete_results():
    base = {'fact': {'value': True, 'status': 'known'}, 'a': [1, 2]}
    other = {'fact': {'status': 'unknown'}, 'a': [2, 1], 'new': False}
    assert packets.restore(base, packets.delta(base, other)) == other
    row = {'checks': [{'case_id': 'base', 'case': base, 'expected': [1], 'result': {'value': True}},
        {'case_id': 'unknown', 'case': other, 'expected': [None], 'result': {'unknown': True}}]}
    packed = packets.case_packet(row)
    for before, after in zip(row['checks'], packed['checks']):
        assert packets.restore(packed['case_base'], after['changes']) == before['case']
        assert packets.restore(packed['result_base'], after['result_changes']) == before['result']


def test_pending_approval_does_not_reserve_or_dispatch(prepared):
    root, _, _ = prepared
    assert runtime.run(root) is None
    assert not runtime.summary(root)['dispatch_authorized']
    with code_error('E_AUTHORITY'):
        runtime.Allowance(root)
    assert ex.Allowance(root).verify()['used'] == 46


def test_amendment_preserves_old_grant_and_counts_every_review_as_repair(prepared):
    root, _, tasks = prepared
    before = ex.Allowance(root).verify()
    approve(prepared)
    assert charged(root, tasks[0]) == 142
    state = runtime.Allowance(root).verify()
    assert (state['used'], state['repair_calls'], state['remaining']) == (47, 21, 53)
    assert ex.Allowance(root).verify() == before
    with code_error('E_AUTHORITY'):
        reserve(root, 60)


def test_task_cap_duplicate_and_changed_payload(prepared):
    root, _, tasks = prepared
    approve(prepared)
    charged(root, tasks[0])
    with code_error('E_INTEGRITY'):
        charged(root, tasks[0])
    modified = deepcopy(tasks[0]); modified['request']['correction'] = {'details': 'Exact validator error'}
    modified = packets.rebind(modified)
    charged(root, modified)
    modified['request']['correction']['details'] = 'Third attempt'
    modified = packets.rebind(modified)
    with code_error('E_RESOURCE_LIMIT'):
        charged(root, modified)
    modified = deepcopy(tasks[1]); modified['request']['questions'][0]['missing'] = 'Different work'
    with code_error('E_AUTHORITY'):
        charged(root, packets.rebind(modified))


def test_expiry_and_authorization_tampering(prepared, monkeypatch):
    root, _, tasks = prepared
    approve(prepared)
    monkeypatch.setattr(c, 'now', lambda: '2100-01-01T00:00:00+00:00')
    with code_error('E_RESOURCE_LIMIT'):
        charged(root, tasks[0])
    grant = c.read(root/runtime.AUTHORIZATION); grant['approval_text'] = ''
    c.save(root/runtime.AUTHORIZATION, grant)
    with code_error('E_AUTHORITY'):
        runtime.Allowance(root)


def test_old_checkpoint_and_packet_tampering_fail_closed(prepared):
    root, folder, tasks = prepared
    approve(prepared)
    c.save(folder/'task-definitions.json', tasks[:-1])
    with code_error('E_INTEGRITY'):
        runtime.Allowance(root)


def test_interrupted_counted_request_is_not_replayed(prepared):
    root, _, tasks = prepared
    approve(prepared)
    charged(root, tasks[0])
    row = runtime.engine().attempt(root, tasks[0], provider_factory=lambda **kw: pytest.fail('No blind replay'))
    assert row['status'] == 'FAILED' and row['error'] == 'E_DEPENDENCY'
    assert runtime.Allowance(root).verify()['used'] == 47


def test_saved_provider_output_restarts_without_spending(prepared):
    root, _, tasks = prepared
    approve(prepared)
    selected = tasks[0]
    wire, schema, _ = protocol.transport(selected)
    slot = charged(root, selected)
    folder = root/runtime.RUN/'provider-evidence'/f'{slot:04}-{digest(wire)[:16]}'
    output = {'binding_hash': wire['binding_hash'], 'legal_correctness': 'NOT_ESTABLISHED',
        'findings': [{'question_id': wire['questions'][0]['id'], 'status': 'UNRESOLVED',
            'answer': 'Actual facts are missing.', 'evidence': [], 'qualifications': ['Conditional only.'],
            'needed_evidence': ['Actual facts.'], 'original_question_answered': False}]}
    for name, value in [('request.json', wire), ('schema.json', schema), ('result.json', output)]:
        c.save(folder/name, value)
    c.save(folder/'manifest.json', {'allowance_slot': slot, 'request_hash': digest(wire),
        'files': {name: {'retained_sha256': raw_digest((folder/name).read_bytes())}
            for name in ('request.json', 'schema.json', 'result.json')}})
    for _ in range(2):
        result = runtime.engine().attempt(root, selected, provider_factory=lambda **kw: pytest.fail('No new provider call'))
        assert result['status'] == 'VALIDATED'
    assert runtime.summary(root)['unaccounted_slots'] == []
    assert runtime.Allowance(root).verify()['used'] == 47


def test_two_provider_failures_stop_later_dispatch(prepared, monkeypatch):
    from legalmath.interpretation.search.providers import CodexProvider
    root, _, _ = prepared
    approve(prepared)
    monkeypatch.setattr(ex, 'verify', lambda root: {'frozen_root': str(Path(runtime.__file__).resolve().parents[1])})
    def fail_provider(self, wire, schema, settings):
        self.allowance.reserve(digest(wire))
        raise LegalMathError('E_DEPENDENCY', details='Synthetic unavailable provider')
    monkeypatch.setattr(CodexProvider, 'complete', fail_provider)
    result = runtime.run(root)
    assert result['status'] == 'HALTED' and result['allowance']['review_calls'] == 2
    assert result['state']['halt']['error'] == 'E_DEPENDENCY'
    assert runtime.run(root)['allowance']['review_calls'] == 2


def test_preflight_keeps_issue_and_total_limits_separate():
    tasks = [task(i) for i in range(13)]
    result = packets.preflight(tasks, {'remaining': 54, 'repair_calls': 20, 'new_issue_spending': {'final.dispositions.structure-reader': 40}})
    assert result['status'] == 'PREFLIGHT_BLOCKED' and len(result['violations']) == 1
    result = packets.preflight(tasks, {'remaining': 14, 'repair_calls': 20, 'new_issue_spending': {}})
    assert result['status'] == 'PREFLIGHT_BLOCKED' and len(result['violations']) == 1


def test_actual_current_packets_have_complete_sources_and_coverage():
    root = Path('/home/chakwong/python/legalmath')
    frozen = Path(__file__).resolve().parents[2]
    tasks, coverage = packets.build(root, ex, {'frozen_root': str(frozen)})
    assert len(coverage) == 70 and sum(row['guarded'] for row in coverage) == 20
    assert packets.preflight(tasks, ex.Allowance(root).verify())['status'] == 'PREFLIGHT_PASSED'
    assert all(t['counted_repair'] and t['predecessors'] for t in tasks)


def test_removed_authorization_cannot_reset_charged_history(prepared):
    root, _, tasks = prepared
    approve(prepared)
    charged(root, tasks[0])
    (root/runtime.AUTHORIZATION).unlink()
    with code_error('E_INTEGRITY'):
        runtime.run(root)
    with code_error('E_AUTHORITY'):
        reserve(root, 60)


def test_question_grouping_preserves_all_distinct_dispositions_and_order():
    rows = [{'question_id': 'q1', 'status': 'open', 'reason': 'Facts'},
        {'question_id': 'q2', 'status': 'open', 'reason': 'Dates'},
        {'question_id': 'q3', 'status': 'open', 'reason': 'Facts'}]
    packed = packets.group_questions(rows)
    assert len(packed['groups']) == 2
    assert [{**packed['groups'][i]['shared_disposition'],
        'question_id': packed['groups'][i]['question_ids'][j]}
        for i, j in packed['original_order']] == rows


@pytest.mark.parametrize('prepared', [26], indirect=True)
def test_four_shared_corrections_preserve_all_initial_reviews(prepared):
    root, folder, tasks = prepared
    approve(prepared)
    original = ex.Allowance(root).verify()
    pre = c.read(folder/'preflight.json')
    assert pre['unconstrained_two_attempt_calls'] == 52
    assert pre['worst_case_calls'] == 30 and pre['shared_correction_maximum'] == 4
    for i, selected in enumerate(tasks):
        charged(root, selected)
        if i <= 4:
            correction = deepcopy(selected)
            correction['request']['correction'] = {'details': 'Synthetic validator correction'}
            if i < 4:
                charged(root, packets.rebind(correction))
            else:
                with code_error('E_RESOURCE_LIMIT'):
                    charged(root, packets.rebind(correction))
    state = runtime.Allowance(root).verify()
    assert (state['used'], state['repair_calls'], state['remaining']) == (76, 50, 24)
    assert len(state['task_spending']) == 26 and state['correction_remaining'] == 0
    with code_error('E_RESOURCE_LIMIT'):
        charged(root, tasks[-1])
    assert ex.Allowance(root).verify() == original


def test_expired_original_window_requires_explicit_renewal(prepared, monkeypatch):
    root, _, tasks = prepared
    old_end = ex.Allowance(root).grant['ends_at']
    later = (datetime.fromisoformat(old_end)+timedelta(hours=1)).isoformat()
    monkeypatch.setattr(c, 'now', lambda: later)
    approve(prepared)
    assert charged(root, tasks[0]) == 142
    grant = c.read(root/runtime.AUTHORIZATION)
    grant['window_renewal'] = False
    c.save(root/runtime.AUTHORIZATION, grant)
    with code_error('E_AUTHORITY'):
        runtime.Allowance(root)


def test_expired_renewed_window_blocks_dispatch(prepared, monkeypatch):
    root, _, tasks = prepared
    approve(prepared)
    end = c.read(root/runtime.AUTHORIZATION)['ends_at']
    monkeypatch.setattr(c, 'now', lambda: end)
    with code_error('E_RESOURCE_LIMIT'):
        charged(root, tasks[0])


def test_approval_cannot_silently_raise_limits(prepared):
    root, _, _ = prepared
    approve(prepared)
    grant = c.read(root/runtime.AUTHORIZATION)
    grant['repair_maximum'] = 74
    c.save(root/runtime.AUTHORIZATION, grant)
    with code_error('E_AUTHORITY'):
        runtime.Allowance(root)


def test_insufficient_repairs_blocks_complete_coverage():
    tasks = [task(i) for i in range(26)]
    result = packets.preflight(tasks, {'remaining': 54, 'repair_calls': 25, 'new_issue_spending': {}})
    assert result['status'] == 'PREFLIGHT_BLOCKED'

def test_current_review_note_reports_the_active_authorization():
    note = ex.current_review_note({'current_review': {'status': 'AUTHORIZED',
        'packet_count': 26, 'worst_case_calls': 30, 'preflight': 'preflight.json',
        'prior_ends_at': '2026-10-04', 'prior_window_expired': True,
        'allowance': {'ends_at': '2026-10-06'}}})
    assert '100 total and 50 repairs' in note and '2026-10-06' in note
