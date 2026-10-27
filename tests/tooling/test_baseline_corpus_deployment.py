from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts import legal_baseline_corpus_deployment as deploy
from scripts.legal_mission_execution import save, ref, Refused
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance

def transaction(root):
    (root / 'old.py').write_text('old')
    (root / 'replacement.py').write_text('new')
    journal = dict(profile='baseline-corpus-deployment-transaction.v1', status='PREPARED', writes=[
        dict(path='old.py', before=ref(root, 'old.py'), replacement=ref(root, 'replacement.py')),
        dict(path='new.py', before=None, replacement=ref(root, 'replacement.py'))])
    save(root / 'journal.json', journal)
    return journal

def test_transaction_installs_existing_and_new_targets_and_resumes(tmp_path):
    transaction(tmp_path)
    deploy.finish_transaction(tmp_path, Path('journal.json'))
    deploy.finish_transaction(tmp_path, Path('journal.json'))
    assert (tmp_path / 'old.py').read_text() == (tmp_path / 'new.py').read_text() == 'new'
    assert json.loads((tmp_path / 'journal.json').read_text())['status'] == 'COMMITTED'

@pytest.mark.parametrize('mutation', ['old', 'new', 'candidate', 'duplicate', 'escape'])
def test_transaction_refuses_foreign_changes_before_any_write(tmp_path, mutation):
    journal = transaction(tmp_path)
    if mutation == 'old':
        (tmp_path / 'old.py').write_text('user change')
    elif mutation == 'new':
        (tmp_path / 'new.py').write_text('user addition')
    elif mutation == 'candidate':
        (tmp_path / 'replacement.py').write_text('corrupt')
    elif mutation == 'duplicate':
        journal['writes'].append(journal['writes'][0])
    else:
        journal['writes'][1]['path'] = '../outside.py'
    save(tmp_path / 'journal.json', journal)
    before = (tmp_path / 'old.py').read_bytes()
    with pytest.raises(Refused):
        deploy.finish_transaction(tmp_path, Path('journal.json'))
    assert (tmp_path / 'old.py').read_bytes() == before

def test_transaction_rolls_forward_after_partial_install(tmp_path):
    transaction(tmp_path)
    (tmp_path / 'old.py').write_text('new')
    deploy.finish_transaction(tmp_path, Path('journal.json'))
    assert (tmp_path / 'new.py').read_text() == 'new'

def state_fixture(root):
    before = dict(tasks={
        'failed': dict(status='FAILED', attempts=[dict(number=1, result={'path': 'failure'})]),
        'done': dict(status='SUCCEEDED', attempts=[dict(number=1)]),
        'paused': dict(status='RUNNING', attempts=[dict(number=2)], service_checkpoint={'path': 'checkpoint'}),
        'pending': dict(status='PENDING', attempts=[])},
        events=[{'action': 'prior'}], continuation_vetoes=[{'code': 'E_RESOURCE_LIMIT'}])
    save(root / 'before.json', before)
    program = {deploy.KEY: dict(prior_state=ref(root, 'before.json'), review={'path': 'review'})}
    return before, program

def test_state_projection_preserves_all_attempts_and_checkpoints(tmp_path, monkeypatch):
    from scripts import legal_window_continuation
    monkeypatch.setattr(legal_window_continuation, 'validate_state_history', lambda *args: None)
    before, program = state_fixture(tmp_path)
    after = deploy.project_state(before, program, 'now')
    deploy.validate_history(program, after, tmp_path)
    assert after['tasks'] == before['tasks']
    assert after['continuation_vetoes'] == before['continuation_vetoes']

@pytest.mark.parametrize('mutation', ['attempt', 'reopen', 'checkpoint', 'events', 'veto'])
def test_history_rejects_reset_or_false_completion(tmp_path, monkeypatch, mutation):
    from scripts import legal_window_continuation
    monkeypatch.setattr(legal_window_continuation, 'validate_state_history', lambda *args: None)
    before, program = state_fixture(tmp_path)
    after = deploy.project_state(before, program, 'now')
    if mutation == 'attempt': after['tasks']['failed']['attempts'] = []
    elif mutation == 'reopen': after['tasks']['failed']['status'] = 'PENDING'
    elif mutation == 'checkpoint': after['tasks']['paused']['service_checkpoint'] = {'path': 'different'}
    elif mutation == 'events': after['events'].pop(0)
    else: after['continuation_vetoes'] = []
    with pytest.raises(Refused): deploy.validate_history(program, after, tmp_path)

def test_installed_hold_refuses_reservation_before_ledger_charge(tmp_path, monkeypatch):
    allowance = CampaignAllowance(tmp_path, {}, root=tmp_path)
    save(tmp_path / 'live-calls.json', dict(calls=[], maximum=8100))
    save(tmp_path / 'current-binding.json', dict(baseline_corpus_repair_hold=True))
    before = (tmp_path / 'live-calls.json').read_bytes()
    monkeypatch.setattr(allowance, 'check', lambda: dict(calls=[], maximum=8100))
    allowance.expected = 'request'
    with pytest.raises(LegalMathError) as caught: allowance.reserve('request')
    assert caught.value.code == 'E_AUTHORITY'
    assert 'reviewed live continuation' in str(caught.value.details)
    assert (tmp_path / 'live-calls.json').read_bytes() == before

def test_new_profiles_use_fresh_runtime():
    from scripts.legal_integration_phased_live import active_live
    program = {'window_continuation': {'runtime': 'historical'},
        deploy.KEY: {'runtime': str(deploy.WORK / 'live')}}
    assert active_live(program) == deploy.WORK / 'live'
