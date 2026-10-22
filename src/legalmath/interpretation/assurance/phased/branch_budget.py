"""Optional reviewed reserves across original questions under one grant."""
import json
from pathlib import Path
from ..bounded_context import require
from ..integration_contract import read_evidence

PROFILE = 'reviewed-original-question-reserves.v1'


def bucket(owner):
    if owner == 'service-requalification':
        return 'service'
    if owner.startswith('compare-'):
        return 'comparisons'
    for qid in ('p10', 'p14', 'evidence', 'gatecoin'):
        if owner == qid or owner.startswith((qid+'-', 'prepare-'+qid)):
            return qid
    return 'other'


def check(root, binding, ledger, owner, count=1):
    pointer = binding.get('execution_budget')
    if pointer is None:
        return
    budget = read_evidence(pointer, root)
    require(budget['profile'] == PROFILE and budget['launch_authorized'] is True,
        'Unreviewed original-question budget', 'E_AUTHORITY')
    before = read_evidence(budget['ledger_before'], root)
    require(ledger['calls'][:len(before['calls'])] == before['calls'],
        'Budget lost predecessor charges', 'E_INTEGRITY')
    used = {key: 0 for key in budget['protected_calls']}
    for row in ledger['calls'][len(before['calls']):]:
        key = bucket(row.get('owner', 'other'))
        used[key] = used.get(key, 0) + 1
    key = bucket(owner)
    # Shared transport replacements can occur in any question's phase. Their
    # spent reservations release the service contingency without resetting it.
    folder = Path(binding['phase_service_scope']['path']).parent
    recovery_path = Path(root)/folder/'service-recovery.json'
    replacements = json.loads(recovery_path.read_text()) if recovery_path.exists() else {'charges': []}
    used['service'] = max(used.get('service', 0),
        len(replacements['charges']) - budget['prior_service_replacements'])
    protected = sum(max(0, floor-used.get(other, 0))
        for other, floor in budget['protected_calls'].items() if other != key)
    remaining = ledger['maximum'] - len(ledger['calls'])
    require(remaining-count >= protected,
        {'reason': 'Phase would spend protected independent-question or service calls',
         'owner': owner, 'remaining': remaining, 'requested': count,
         'protected_other_calls': protected, 'used_since_revision': used}, 'E_RESOURCE_LIMIT')

