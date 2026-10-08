from copy import deepcopy
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time

import pytest

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.grant_continuation import (
    CarriedSlice, ScopedContinuationProvider, scoped_history, scoped_issue_keys)
from legalmath.interpretation.assurance.issue_limits import IssueLimits
from legalmath.interpretation.assurance import fidelity_v2
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider, Completion
from .test_round16 import scoped_fixture


@contextmanager
def error(code):
    with pytest.raises(LegalMathError) as caught:
        yield
    assert caught.value.code == code


def setup(tmp_path, spent=1):
    prior = tmp_path/'old.json'; prior.write_bytes(canonical({'maximum': 2, 'calls': [
        {'request_hash': digest(i), 'issued_at_ns': str(time.time_ns())} for i in range(2)]}))
    arm = tmp_path/'arm.json'; arm.write_bytes(canonical({'grant_hash': 'a'*64, 'maximum': 2,
        'reservations': [{'request_hash': digest(i), 'global_slot': i+1, 'status': 'GLOBALLY_RESERVED'}
                         for i in range(spent)]}))
    grant = tmp_path/'grant.json'; grant.write_bytes(canonical({'schema': 'legalmath.additional-grant.v1',
        'grant_id': 'test.new', 'authorized_calls': 5, 'authorization': 'Explicit synthetic test',
        'predecessor': {'path': 'old.json', 'sha256': raw_digest(prior.read_bytes())}, 'ledger': 'new.json'}))
    return grant, arm, prior


def wire():
    packet, claims, readings, questions, _ = scoped_fixture()
    request = fidelity_v2.request(packet, claims, readings, questions)
    request['investigation'] = {'perspective': 'source-first'}
    return compact_request(request, profile='v2')


def test_cross_grant_arm_is_not_reset_or_refunded(tmp_path):
    grant, arm, prior = setup(tmp_path)
    untouched = [p.read_bytes() for p in (arm, prior)]
    allowance = CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    assert allowance.reserve(digest('request')) == 1
    with error('E_RESOURCE_LIMIT'):
        CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes())).reserve(digest('retry'))
    assert untouched == [p.read_bytes() for p in (arm, prior)]
    assert len(loads((tmp_path/'new.json').read_bytes())['calls']) == 1


def test_exhausted_old_arm_stays_exhausted(tmp_path):
    grant, arm, _ = setup(tmp_path, spent=2)
    with error('E_RESOURCE_LIMIT'):
        CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    assert not (tmp_path/'new.json').exists()


@pytest.mark.parametrize('which', ['old-arm', 'carry', 'old-ledger'])
def test_history_changes_prevent_dispatch(tmp_path, which):
    grant, arm, prior = setup(tmp_path)
    allowance = CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    target = {'old-arm': arm, 'carry': allowance.carry_path, 'old-ledger': prior}[which]
    target.write_bytes(target.read_bytes()+b' ')
    with error('E_INTEGRITY'):
        allowance.reserve(digest('request'))
    assert not (tmp_path/'new.json').exists()


def test_concurrent_last_carried_slot_is_reserved_once(tmp_path):
    grant, arm, _ = setup(tmp_path)
    allowance = CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    def call(i):
        try: return allowance.reserve(digest(i))
        except LegalMathError as exc: return exc.code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(call, range(8)))
    assert results.count(1) == 1
    assert results.count('E_RESOURCE_LIMIT') == 7


def test_transport_hash_addition_does_not_create_new_issue():
    request = wire(); old = deepcopy(request)
    for candidate in old['candidates']: candidate.pop('reading_hash', None)
    assert scoped_issue_keys(old) == scoped_issue_keys(request)
    for field in ('question', 'representation'):
        changed = deepcopy(request)
        changed['candidates'][0][field] = 'different meaning'
        assert scoped_issue_keys(changed) != scoped_issue_keys(request)
    changed = deepcopy(request); changed['investigation']['perspective'] = 'qualification-first'
    assert scoped_issue_keys(changed) != scoped_issue_keys(request)


def test_spending_history_includes_failed_transport_and_exact_fallback(tmp_path):
    request = wire(); path = tmp_path/'ledger.json'
    path.write_bytes(canonical({'maximum': 2, 'calls': [
        {'request_hash': digest(request), 'issued_at_ns': str(i+1)} for i in range(2)]}))
    h = raw_digest(path.read_bytes())
    with error('E_INTEGRITY'):
        scoped_history(path, tmp_path/'transport', expected_hash=h, fallback_requests={1: request})
    result = scoped_history(path, tmp_path/'transport', expected_hash=h, fallback_requests={1: request, 2: request})
    assert result['scoped_requests'] == 2
    assert result['issues'][scoped_issue_keys(request)[0]]['spent'] == 2
    changed = deepcopy(request); changed['task'] = 'NOT_SCOPED'
    with error('E_INTEGRITY'):
        scoped_history(path, tmp_path/'transport', expected_hash=h, fallback_requests={1: request, 2: changed})


@pytest.mark.parametrize('expired', [False, True])
def test_new_grant_does_not_reset_issue_attempts_or_deadline(tmp_path, monkeypatch, expired):
    grant, arm, _ = setup(tmp_path)
    allowance = CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    request = wire(); key = scoped_issue_keys(request)[0]
    inherited = {key: {'spent': 1 if expired else 6,
                      'started_ms': 1 if expired else time.time_ns()//1000000, 'evidence_hash': 'b'*64}}
    limits = IssueLimits(tmp_path/'issues.json', {'scope': 'test'}, maximum_attempts=6, inherited=inherited)
    provider = ScopedContinuationProvider(allowance=allowance, issue_limits=limits, allowed_issues={key})
    monkeypatch.setattr(CodexProvider, 'complete', lambda *a: pytest.fail('Issue cap bypassed'))
    with error('E_RESOURCE_LIMIT'):
        provider.complete(request, {}, Settings())
    assert not (tmp_path/'new.json').exists()


def test_changed_issue_rejected_before_any_reservation(tmp_path, monkeypatch):
    grant, arm, _ = setup(tmp_path)
    allowance = CarriedSlice(grant, tmp_path/'new-arm.json', arm, raw_digest(arm.read_bytes()))
    request = wire(); key = scoped_issue_keys(request)[0]
    limits = IssueLimits(tmp_path/'issues.json', {'scope': 'test'}, maximum_attempts=6)
    provider = ScopedContinuationProvider(allowance=allowance, issue_limits=limits, allowed_issues={key})
    request['investigation']['perspective'] = 'qualification-first'
    monkeypatch.setattr(CodexProvider, 'complete', lambda *a: pytest.fail('Unreviewed issue dispatched'))
    with error('E_AUTHORITY'):
        provider.complete(request, {}, Settings())
    assert not limits.path.exists()


def test_scoped_predispatch_stop_does_not_require_a_created_ledger(tmp_path):
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    grant, _, _ = setup(tmp_path)
    class Stopped(CodexProvider):
        def __init__(self):
            self.allowance = GrantedAllowance(grant)
            self.routing = {'synthetic': 'deadline guard'}
        def complete(self, *args):
            raise LegalMathError('E_RESOURCE_LIMIT', details='Original issue expired')
    packet, claims, readings, questions, _ = scoped_fixture()
    result = investigate(packet, claims, readings, questions, Stopped(), tmp_path/'stopped', maximum_rounds=1)
    assert result['live_calls'] == 0
    assert result['stopped']['error'] == 'E_RESOURCE_LIMIT'
    assert result['pending_pairs']
    assert not (tmp_path/'new.json').exists()


def test_another_directory_cannot_reset_carried_arm_balance(tmp_path):
    grant, arm, _ = setup(tmp_path)
    prior_hash = raw_digest(arm.read_bytes())
    a = CarriedSlice(grant, tmp_path/'partition-a.json', arm, prior_hash)
    a.reserve(digest('first'))
    with error('E_INTEGRITY'):
        CarriedSlice(grant, tmp_path/'partition-b.json', arm, prior_hash)
