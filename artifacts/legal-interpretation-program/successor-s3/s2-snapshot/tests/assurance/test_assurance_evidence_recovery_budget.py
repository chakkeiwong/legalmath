from copy import deepcopy
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import assurance_evidence_core as c
import assurance_evidence_extension as ex
import assurance_evidence_next_phase as n
import assurance_evidence_review_runtime as current
import assurance_evidence_current_review as packets
from test_assurance_evidence_current_review import prepared, approve, charged
from test_assurance_evidence_extension import root, code_error
from test_assurance_evidence_next_phase import inputs


def review_report():
    return {'state': {'halt': None, 'phases': {p: {'status': 'COMPLETED'} for p in ('engineering', 'dispositions')}},
        'status': 'COMPLETED_WITH_OPEN_EVIDENCE', 'structurally_validated_tasks': 26,
        'findings': [{'answer': 'Still unresolved.'}]*74, 'unaccounted_slots': [],
        'packet_count': 26, 'attempted_tasks': 26}


def test_combined_allowance_retains_historical_task_spending(prepared):
    root, _, tasks = prepared
    old = ex.Allowance(root).verify()
    approve(prepared)
    charged(root, tasks[0])
    combined, run = n.current_allowance(root, ex)
    assert (combined['used'], combined['repair_calls'], combined['repair_remaining']) == (47, 21, 29)
    assert combined['final_issue_limit'] == 50 and run == current.RUN
    assert all(combined['task_spending'][k] == v for k, v in old['task_spending'].items())
    assert combined['task_spending'][tasks[0]['id']] == 1
    assert ex.Allowance(root).verify() == old
    assert len(n.reservation_refs(root, ex, run)) == 47
    (root/current.AUTHORIZATION).unlink()
    with code_error('E_AUTHORITY'):
        n.current_allowance(root, ex)


def test_stale_recovery_summary_is_explicit_and_does_not_rewrite(root, monkeypatch):
    folder = root/ex.RUN/'local-recovery'/'test'
    old = ex.Allowance(root).verify()
    for name in n.REQUIRED:
        c.save(folder/name, {})
    c.save(folder/'allowance-checkpoint.json', old)
    work = {'status': 'PREPARED_WITH_BLOCKED_DEPENDENCIES', 'counts': {}, 'budget': {'remaining_total_calls': 100}}
    c.save(folder/'work-items.json', work)
    c.save(folder/'completion-receipt.json', {'inputs': [],
        'files': ex.master.files_in(folder, root, ('completion-receipt.json',))})
    ref = c.receipt(folder/'completion-receipt.json', root)
    c.save(root/ex.RUN/'current-local-recovery.json', {'receipt': ref})
    monkeypatch.setattr(n, 'current_allowance', lambda root, ex: ({**old, 'used': 1, 'remaining': 99}, ex.RUN))
    result = n.summary(root, ex)
    assert result['status'] == 'STALE_BUDGET_CHECKPOINT' and result['current_allowance']['used'] == 1
    assert c.read(folder/'allowance-checkpoint.json') == old and c.receipt(folder/'completion-receipt.json', root) == ref


def test_completed_round_is_not_a_fresh_26_call_deficit():
    args = list(inputs())
    args[-1].update(remaining=28, repair_remaining=4, final_issue_limit=50,
        new_issue_spending={'final.dispositions.'+role: 23 for role in c.ROLES})
    work = n.assemble(*args, now='2026-10-04')
    assert all(a['canonical_calls_remaining'][a['issues'][0]] in (27, 50) for a in work['final_audits'])
    n.attach_current_review(work, review_report(), [], None)
    assert work['budget']['current_evidence_review_calls_without_retries'] == 0
    assert work['budget']['current_evidence_review_repair_shortfall'] == 0
    assert work['budget']['hypothetical_full_repeat_repair_shortfall'] == 22
    assert not work['budget']['provider_dispatch_planned']
    assert work['counts']['failed_final_audits'] == 11
    assert all(a['remaining_task_attempts'] == 1 for a in work['final_audits'])
    assert 'Pending initial calls in the current round: 0' in n.plan_text(work)
    assert work['current_review']['accepted_substantive_repairs'] == 0


def actual_map():
    root = Path('/home/chakwong/python/legalmath')
    workdir = root/ex.RUN
    ref = c.read(workdir/'current-post-review-repairs.json')['receipt']
    derived = c.read((root/ref['path']).parent/'dispositions.json')
    work = {'inventory': c.read(workdir/'checks-current-v3/program-inventory.json'),
        'evidence_requests': c.read(root/c.OLD/'remaining-obligations.json'), 'final_audits': [],
        'budget': {'current_evidence_review_calls_without_retries': 26,
            'current_evidence_review_repair_shortfall': 22, 'remaining_repair_calls': 4,
            'current_evidence_review_issue_shortfalls': {}}}
    return work, derived, ref


def test_actual_corrected_map_preserves_all_original_obligations():
    work, derived, ref = actual_map()
    originals = deepcopy(work['evidence_requests'])
    n.attach_current_review(work, review_report(), derived, ref)
    mapping = work['obligation_evidence_map']
    assert len(mapping) == 46
    rows = [r for o in mapping for r in o['derived_requests']]
    assert len(rows) == 178 and sum(r['direct_subject'] for r in rows) == 92
    assert all(not r['request']['original_question_answered'] for r in rows)
    assert work['evidence_requests'] == originals
    text = n.evidence_text(work)
    assert 'independently established assessment period' in text


@pytest.mark.parametrize('damage', ['omit', 'duplicate', 'close', 'foreign', 'rename'])
def test_evidence_map_rejects_incomplete_or_changed_originals(damage):
    work, derived, ref = actual_map()
    row = next(e for e in derived if e['operative']['obligations'])
    if damage == 'omit':
        row['operative']['obligations'].pop()
    elif damage == 'duplicate':
        row['operative']['obligations'].append(deepcopy(row['operative']['obligations'][0]))
    elif damage == 'close':
        row['operative']['obligations'][0]['original_question_answered'] = True
    elif damage == 'foreign':
        row['operative']['obligations'][0]['question_id'] = 'foreign'
    else:
        row['reading_id'] = 'foreign'
    with code_error('E_INTEGRITY'):
        n.attach_current_review(work, review_report(), derived, ref)


def test_completed_review_keeps_approved_package_when_active_revision_changes(prepared, monkeypatch):
    root, folder, _ = prepared
    approve(prepared)
    before = c.receipt(folder/'completion-receipt.json', root)
    monkeypatch.setattr(ex, 'verify', lambda root: {'frozen_root': str(Path(packets.__file__).resolve().parents[1])})
    monkeypatch.setattr(packets, 'build', lambda *a: pytest.fail('Do not rebuild the approved review'))
    summary = packets.prepare(root, ex)
    assert summary['authorization_recorded'] and summary['package'] == before
