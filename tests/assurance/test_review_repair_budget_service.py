from copy import deepcopy
from datetime import timedelta
import json
import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import SERVICE_REVIEW_REPAIR_POLICY as POLICY
from legalmath.interpretation.assurance.phased import branch_budget
from legalmath.interpretation.assurance.phased.admission import admit
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from tests.assurance import test_delayed_service_recovery as delayed


def migrated(tmp_path, monkeypatch):
    allowance, clock = delayed.setup(tmp_path, monkeypatch)
    for n in range(1, 25):
        allowance.reserve_service_recovery(delayed.failure(tmp_path, n))
    path = tmp_path/'stage/service-recovery.json'
    prior = json.loads(path.read_text())
    save(tmp_path/'prior.json', prior)
    stage = {'name': 'repaired', 'service_recovery_policy': POLICY,
             'service_recovery_maximum': POLICY['maximum_replacements']}
    save(tmp_path/'stage/stage.json', stage)
    pointer = evidence_file(tmp_path/'stage/stage.json', tmp_path)
    save(tmp_path/'current-stage.json', pointer)
    save(tmp_path/'current-binding.json', {'service_recovery_policy': POLICY,
        'review_repair_service_predecessor': evidence_file(tmp_path/'prior.json', tmp_path)})
    save(path, {**prior, 'profile': POLICY['profile'], 'maximum': 88, 'stage_hash': pointer['sha256']})
    return allowance, clock, prior


def test_migration_preserves_counts_and_five_minute_schedule(tmp_path, monkeypatch):
    allowance, clock, prior = migrated(tmp_path, monkeypatch)
    # The original request has already exhausted all 24 replacements.
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path, 25))
    assert caught.value.details == 'Request replacements exhausted'
    monkeypatch.setattr(delayed, 'REQUEST', {'question': 'another exact request'})
    allowance.expected = digest(delayed.REQUEST)
    ended = delayed.failure(tmp_path, 26)
    allowance.service_circuit(failure=ended)
    assert allowance.reserve_service_recovery(ended) == 300
    state = json.loads((tmp_path/'stage/service-recovery.json').read_text())
    assert state['charges'][:24] == prior['charges'] and len(state['charges']) == 25
    # Restarted waiting uses elapsed time and the saved due time.
    clock.now += timedelta(seconds=120)
    allowance.wait_service_recovery(ended)
    assert sum(clock.sleeps) == 180
    allowance.service_circuit(reserving=True)
    with pytest.raises(LegalMathError): allowance.service_circuit(reserving=True)


def test_migration_rejects_lost_history_and_honors_retry_after(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance.bounded_provider import recovery_delay
    allowance, _, _ = migrated(tmp_path, monkeypatch)
    path = tmp_path/'stage/service-recovery.json'
    state = json.loads(path.read_text())
    state['charges'][0]['failed_slot'] = 999
    save(path, state)
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path, 25))
    assert caught.value.details == 'Lost prior delayed recovery charges'
    assert recovery_delay(POLICY, 24, {'retry_after_seconds': 901}) == 901
    with pytest.raises(LegalMathError): recovery_delay(POLICY, 24, {'unparsed_retry_after': True})


def test_independent_reserves_enforced_at_admission_and_each_charge(tmp_path):
    from tests.assurance.test_phased_admission import setup
    base, live, allowance = setup(tmp_path)
    path = tmp_path/base/'live-calls.json'
    ledger = json.loads(path.read_text())
    # All prior entries remain byte-for-byte identical after the amendment.
    ledger['calls'] = [{'request_hash': str(n)} for n in range(900)]
    save(path, ledger)
    save(tmp_path/'before.json', ledger)
    budget = dict(profile=branch_budget.PROFILE, launch_authorized=True,
        ledger_before=evidence_file(tmp_path/'before.json', tmp_path),
        protected_calls={'p10': 30, 'p14': 30, 'service': 10, 'comparisons': 10}, prior_service_replacements=24)
    save(tmp_path/'budget.json', budget)
    binding_path = tmp_path/base/'current-binding.json'
    binding = json.loads(binding_path.read_text())
    binding['execution_budget'] = evidence_file(tmp_path/'budget.json', tmp_path)
    save(binding_path, binding)
    admit(tmp_path, base, live, 'first', 13, owner='p14-baseline')
    for n in range(20):
        allowance.expected = str(n+1000)
        allowance.reserve(allowance.expected)
    current = json.loads(path.read_text())
    assert current['calls'][:900] == ledger['calls']
    assert all(r['owner'] == 'p14-baseline' for r in current['calls'][900:])
    with pytest.raises(LegalMathError):
        admit(tmp_path, base, live, 'too-large', 31, owner='p14-baseline')
    # Spending exactly the unprotected pool is allowed; another question's
    # floor cannot be spent by a direct dispatcher either.
    for n in range(30):
        allowance.expected = str(n+2000)
        allowance.reserve(allowance.expected)
    with pytest.raises(LegalMathError): allowance.reserve(allowance.expected)
    branch_budget.check(tmp_path, binding, json.loads(path.read_text()), 'prepare-p10', 1)


def test_exact_receipt_recovery_refuses_output_and_auth_failures(tmp_path):
    from scripts.legal_review_repair_service import terminal_receipt
    value = delayed.failure(tmp_path, 1, message='503 Service Unavailable')
    request, schema, failure, _ = terminal_receipt(tmp_path, '', 1, value.request_hash)
    assert request == delayed.REQUEST and schema == delayed.SCHEMA and failure.allowance_slot == 1
    delayed.failure(tmp_path, 2, message='401 unauthorized')
    with pytest.raises(Exception, match='terminal service failure'):
        terminal_receipt(tmp_path, '', 2, value.request_hash)
    delayed.failure(tmp_path, 3, completed=True)
    with pytest.raises(Exception): terminal_receipt(tmp_path, '', 3, value.request_hash)
