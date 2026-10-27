from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance, SERVICE_CONTINUATION_POLICY
from legalmath.interpretation.assurance.phased.admission import admit
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save


def setup(tmp_path):
    base, live = 'master', 'live'
    grant = {'maximum_calls': 1000, 'deadline_utc': (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()}
    save(tmp_path / base / 'live-grant.json', grant)
    review = {'path':'review.md','sha256':'0'*64}
    scope = {'grant_hash':digest(grant),'review':review}
    save(tmp_path / live / 'service/scope.json', scope)
    binding = {'service_recovery_policy':SERVICE_CONTINUATION_POLICY,
        'phase_service_scope':evidence_file(tmp_path / live / 'service/scope.json', tmp_path), 'review':review}
    save(tmp_path / base / 'current-binding.json', binding)
    save(tmp_path / base / 'live-calls.json', {'grant_hash':digest(grant),'maximum':1000,'calls':[]})
    allowance = CampaignAllowance(tmp_path / base, {}, root=tmp_path)
    allowance.check = lambda: json.loads(allowance.path.read_text())
    return base, live, allowance


def test_interleaved_phases_charge_only_their_own_calls(tmp_path):
    base, live, allowance = setup(tmp_path)
    first = admit(tmp_path, base, live, 'first', 1, owner='p14')
    allowance.expected = 'a'
    allowance.reserve('a')
    admit(tmp_path, base, live, 'other', 10, owner='p10')
    for i in range(5):
        allowance.expected = str(i)
        allowance.reserve(str(i))
    assert admit(tmp_path, base, live, 'first', 1, owner='p14') == first
    for i in range(3):
        allowance.expected = 'remaining' + str(i)
        allowance.reserve(allowance.expected)
    with pytest.raises(LegalMathError):
        allowance.reserve(allowance.expected)
    ledger = json.loads(allowance.path.read_text())
    assert len(ledger['calls']) == 9
    assert sum(r['stage_hash'] == first['sha256'] for r in ledger['calls']) == 4


def test_sibling_phase_cannot_reset_open_shared_circuit(tmp_path):
    base, live, allowance = setup(tmp_path)
    admit(tmp_path, base, live, 'first', 1, owner='p14')
    from types import SimpleNamespace
    for n in range(1, 9):
        try:
            allowance.service_circuit(failure=SimpleNamespace(allowance_slot=n))
        except LegalMathError:
            assert n == 8
    admit(tmp_path, base, live, 'other', 1, owner='p10')
    with pytest.raises(LegalMathError):
        allowance.service_circuit()
    allowance.expected = 'undispatched'
    with pytest.raises(LegalMathError):
        allowance.reserve(allowance.expected)
    assert not json.loads(allowance.path.read_text())['calls']


@pytest.mark.parametrize('version', ['v6','v7'])
def test_reviewed_successor_preserves_progressive_window_admission(tmp_path, version):
    from legalmath.interpretation.assurance.bounded_provider import (
        SERVICE_REVIEW_REPAIR_POLICY, SERVICE_REVIEW_DEPLOYMENT_POLICY)
    base,live,allowance=setup(tmp_path)
    grant=json.loads((tmp_path/base/'live-grant.json').read_text())
    grant['deadline_utc']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    save(tmp_path/base/'live-grant.json',grant)
    binding=json.loads((tmp_path/base/'current-binding.json').read_text())
    binding['service_recovery_policy']=(SERVICE_REVIEW_REPAIR_POLICY if version=='v6'
        else SERVICE_REVIEW_DEPLOYMENT_POLICY)
    save(tmp_path/base/'current-binding.json',binding)
    pointer=admit(tmp_path,base,live,'one-exact-recovery',1,owner='service-requalification')
    stage=json.loads((tmp_path/pointer['path']).read_text())
    assert stage['logical_calls']==1 and stage['maximum_calls']==25
    assert stage['deadline_utc']==grant['deadline_utc']
    assert not json.loads(allowance.path.read_text())['calls']
    with pytest.raises(LegalMathError) as caught:
        admit(tmp_path,base,live,'too-long',12,owner='p14')
    assert caught.value.details=='Phase exceeds original global window'
