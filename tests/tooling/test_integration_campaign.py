from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save


def approved(tmp_path):
    route = {'model': 'fixture', 'provider': 'fixture', 'fields': {}}
    (tmp_path/'bound.py').write_text('# frozen implementation\n')
    save(tmp_path/'proposal.json', {'dispatch_ready': True, 'maximum_calls': 3,
        'routing_hash': digest(route), 'window_seconds': 3600,
        'bindings': [evidence_file(tmp_path/'bound.py', tmp_path)]})
    now = datetime.now(timezone.utc)
    save(tmp_path/'live-grant.json', {'profile': 'integration-master-live-grant.v1', 'approved': True,
        'approval_text': 'Synthetic test approval', 'proposal': evidence_file(tmp_path/'proposal.json', tmp_path),
        'maximum_calls': 3, 'routing_hash': digest(route), 'started_utc': now.isoformat(),
        'deadline_utc': (now+timedelta(seconds=3600)).isoformat()})
    return route


def test_grant_binds_raw_implementation_and_route(tmp_path):
    route = approved(tmp_path)
    allowance = CampaignAllowance(tmp_path, route, root=tmp_path)
    assert allowance.check()['calls'] == []
    wrong = CampaignAllowance(tmp_path, {**route, 'model': 'different'}, root=tmp_path)
    with pytest.raises(LegalMathError): wrong.check()
    (tmp_path/'bound.py').write_text('# changed\n')
    with pytest.raises(LegalMathError): allowance.check()


def test_declared_campaign_caps_cover_every_planned_phase():
    from scripts.legal_integration_campaign import MAXIMUM_CALLS, WINDOW_SECONDS, CALL_TIMEOUT
    source_chunks, requirements = 151, (85, 4, 86, 4)
    full = 159 + 8 + 4*320 + 7*sum(r+source_chunks+32 for r in requirements) + 24*6 + 7*6
    assert full <= MAXIMUM_CALLS
    # Shared acquisition runs serially, remaining ready branches use two workers.
    assert (159+8)*CALL_TIMEOUT + (full-167)*CALL_TIMEOUT/2 + 3600 < WINDOW_SECONDS


def test_recovery_preserves_original_grant_charges_and_archived_code(tmp_path):
    route = approved(tmp_path)
    allowance = CampaignAllowance(tmp_path, route, root=tmp_path)
    allowance.expected = 'original'
    allowance.reserve('original')
    grant = __import__('json').loads((tmp_path/'live-grant.json').read_text())
    original = evidence_file(tmp_path/'bound.py', tmp_path)
    (tmp_path/'archived.py').write_bytes((tmp_path/'bound.py').read_bytes())
    (tmp_path/'bound.py').write_text('# reviewed repair\n')
    before = __import__('json').loads((tmp_path/'live-calls.json').read_text())
    save(tmp_path/'before.json', before)
    migration = {'grant_hash':digest(grant),'global_ceiling':3,'deadline_utc':grant['deadline_utc'],
        'replacements':[{'previous':original,'archive':evidence_file(tmp_path/'archived.py',tmp_path),
                         'current':evidence_file(tmp_path/'bound.py',tmp_path)}],
        'bindings':[], 'ledger_before':evidence_file(tmp_path/'before.json',tmp_path)}
    save(tmp_path/'recovery-proposal.json',migration)
    with pytest.raises(LegalMathError): allowance.check()
    save(tmp_path/'recovery-approval.json',{'profile':'integration-master-recovery-approval.v1',
        'approved':True,'approval_text':'Synthetic explicit recovery approval',
        'grant_hash':digest(grant),'proposal':evidence_file(tmp_path/'recovery-proposal.json',tmp_path)})
    allowance.expected = 'repair'
    assert allowance.reserve('repair') == 2
    current = allowance.check()
    current['calls'][0]['request_hash'] = 'changed'
    save(tmp_path/'live-calls.json',current)
    with pytest.raises(LegalMathError): allowance.check()
    current['calls'][0] = before['calls'][0]
    save(tmp_path/'live-calls.json',current)
    (tmp_path/'archived.py').write_text('# changed historical implementation\n')
    with pytest.raises(LegalMathError): allowance.check()


def test_reviewed_reopening_binds_new_code_and_retains_old_charge(tmp_path):
    import json
    route=approved(tmp_path)
    allowance=CampaignAllowance(tmp_path,route,root=tmp_path)
    allowance.expected='spent'; allowance.reserve('spent')
    grant=json.loads((tmp_path/'live-grant.json').read_text())
    original=evidence_file(tmp_path/'bound.py',tmp_path)
    (tmp_path/'original.py').write_bytes((tmp_path/'bound.py').read_bytes())
    before=json.loads((tmp_path/'live-calls.json').read_text())
    save(tmp_path/'before.json',before)
    save(tmp_path/'recovery-proposal.json',{'grant_hash':digest(grant),'global_ceiling':3,
        'deadline_utc':grant['deadline_utc'],'replacements':[],'bindings':[],
        'ledger_before':evidence_file(tmp_path/'before.json',tmp_path)})
    save(tmp_path/'recovery-approval.json',{'profile':'integration-master-recovery-approval.v1',
        'approved':True,'approval_text':'Synthetic authority','grant_hash':digest(grant),
        'proposal':evidence_file(tmp_path/'recovery-proposal.json',tmp_path)})
    (tmp_path/'bound.py').write_text('# reviewed new implementation\n')
    save(tmp_path/'reopening.json',{'grant_hash':digest(grant),'global_ceiling':3,
        'deadline_utc':grant['deadline_utc'],'prior_recovery':evidence_file(tmp_path/'recovery-approval.json',tmp_path),
        'ledger_before':evidence_file(tmp_path/'before.json',tmp_path),
        'historical_bindings':[{'previous':original,'archive':evidence_file(tmp_path/'original.py',tmp_path)}],
        'bindings':[evidence_file(tmp_path/'bound.py',tmp_path)]})
    save(tmp_path/'reopening-binding.json',{'profile':'integration-master-reopening-binding.v1',
        'grant_hash':digest(grant),'user_instruction':'Synthetic reviewed continuation',
        'proposal':evidence_file(tmp_path/'reopening.json',tmp_path)})
    assert allowance.check()['calls']==before['calls']
    (tmp_path/'bound.py').write_text('# unauthorized change\n')
    with pytest.raises(LegalMathError): allowance.check()
