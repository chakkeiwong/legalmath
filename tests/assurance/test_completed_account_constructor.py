"""The real completed receipt must be selected by the request constructor."""
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.legal_integration_master import ROOT
from scripts.legal_mission_execution import read
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import account_recovery, account_receipt, account_output


WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh')


@pytest.fixture
def contracts(monkeypatch):
    checkpoint = read(ROOT / 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-1/recovery-p10.json')
    old, schema, _, _ = account_receipt.checked(ROOT, checkpoint, 'detail-10',
        checkpoint['completed_account_receipts']['detail-10'])
    current = read(ROOT / WORK / 'p10-request-before.json')
    base, typed = account_recovery.baseline_request(current, schema, root=ROOT)
    assert typed and base['records'] != account_recovery.baseline_request(old, schema, root=ROOT)[0]['records']
    # Full recursive checkpoint authentication is exercised by the production
    # replay. Keep these mutation controls focused on the selection boundary;
    # checked() below still authenticates the actual receipt and its charge.
    monkeypatch.setattr(account_recovery, 'load', lambda *args: checkpoint)
    return checkpoint, old, schema, base


def test_production_request_selects_historical_completed_contract(contracts):
    checkpoint, old, schema, base = contracts
    selected, actual_schema, typed = account_recovery.retained_contract(
        ROOT, {}, 'detail-10', base, checkpoint['input_hash'])
    expected = deepcopy(old)
    expected['account_output_profile'] = account_output.PROFILE
    assert selected == expected and actual_schema == schema and typed
    assert selected['records'] != base['records']


@pytest.mark.parametrize('mutation', ['text', 'offset', 'duplicate', 'missing', 'assignment', 'instructions', 'question'])
def test_completed_contract_cannot_hide_semantic_mutations(contracts, mutation):
    checkpoint, _, _, base = contracts
    if mutation == 'text': base['records'][0]['text'] += ' invented authority'
    elif mutation == 'offset': base['records'][0]['start'] += 1
    elif mutation == 'duplicate': base['records'].append(deepcopy(base['records'][0]))
    elif mutation == 'missing': base['records'].pop()
    elif mutation == 'assignment': base['required_considered'] = ['different obligation']
    elif mutation == 'instructions': base['instructions'] += ' Change the answer.'
    else: base['question'][0]['question_id'] = 'different-question'
    with pytest.raises(LegalMathError):
        account_recovery.retained_contract(ROOT, {}, 'detail-10', base, checkpoint['input_hash'])
