from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import shutil
import pytest

from scripts.legal_integration_master import ROOT
from scripts.legal_integration_master import PROGRAM, BASE, TOKENIZER
from scripts.legal_mission_execution import read, ref
from legalmath.errors import LegalMathError
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased import account_contract, account_receipt, account_output

WORK = Path('artifacts/legal-mission-control/2026-10-16/execution-refresh')


def test_authentic_completed_receipt_uses_normal_validator_with_no_reservation(monkeypatch):
    from scripts.legal_integration_campaign import provider
    service = provider()
    def forbidden(*a, **kw): raise AssertionError('Receipt reuse dispatched or reserved a call')
    monkeypatch.setattr(service, 'complete', forbidden)
    monkeypatch.setattr(service.allowance, 'reserve', forbidden)
    pointer = ref(ROOT, WORK/'recovery-p10.json')
    checkpoint = read(ROOT/pointer['path'])
    request, schema, value, measurement = account_receipt.checked(ROOT, checkpoint, 'detail-10',
        checkpoint['completed_account_receipts']['detail-10'])
    request['account_output_profile'] = account_output.PROFILE
    ledger = ref(ROOT, BASE/'live-calls.json')
    product = BoundedProduct(ROOT, ROOT/WORK/'receipt-integration', service,
        read(ROOT/read(ROOT/PROGRAM)['prerequisite_repair']['source']['path']), tokenizer(ROOT/TOKENIZER),
        limits=Limits(), maximum_calls=8100, active_questions=['p10'])
    product.dispatch.retained_initial = (ROOT, pointer)
    def check(actual):
        assert actual == value
        account_contract.validate(actual, product, request['records'])
        assert set(actual['considered']) == set(request['required_considered'])
        product.citations(actual, request['records'])
    result = product.dispatch.call('detail-10', request, schema, check)
    assert result['status'] == 'VALIDATED'
    assert result['provenance']['allowance_slot'] == 2190
    assert measurement['wire_tokens'] == 3005
    assert ref(ROOT, BASE/'live-calls.json') == ledger
    assert read(ROOT/checkpoint['account_recovery']['originals']['detail-10']['result']['path'])['status'] == 'FAILED'


def copied_receipt(tmp_path):
    checkpoint = read(ROOT/WORK/'recovery-p10.json')
    # Copy every referenced evidence byte, including tokenizer and provider files.
    def copy(node):
        if isinstance(node, dict):
            if set(node) == {'path', 'sha256'}:
                src, dest = ROOT/node['path'], tmp_path/node['path']
                dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dest)
            else:
                for child in node.values(): copy(child)
        elif isinstance(node, list):
            for child in node: copy(child)
    entry = checkpoint['completed_account_receipts']['detail-10']
    copy(entry)
    directory = Path(entry['provider_manifest']['path']).parent
    for name in read(ROOT/entry['provider_manifest']['path'])['files']:
        shutil.copyfile(ROOT/directory/name, tmp_path/directory/name)
    return checkpoint, entry


@pytest.mark.parametrize('mutation', ['slot', 'review', 'binding', 'redacted', 'incomplete', 'events', 'result'])
def test_receipt_integrity_rejects_rebound_or_changed_evidence(tmp_path, mutation):
    checkpoint, entry = copied_receipt(tmp_path)
    if mutation == 'slot': entry['allowance_slot'] = 2189
    elif mutation == 'review':
        path = tmp_path/entry['amendment']['path']; v = json.loads(path.read_text())
        v['provider_calls_authorized'] = 1; path.write_text(json.dumps(v)); entry['amendment'] = ref(tmp_path, path)
    elif mutation == 'binding': entry['reference_binding'] = entry['originals']['request']
    else:
        path = tmp_path/entry['provider_manifest']['path']; receipt = json.loads(path.read_text())
        if mutation == 'redacted': receipt['files']['result.json']['redacted'] = True
        elif mutation == 'incomplete': receipt['complete_output_present'] = False
        else:
            name = 'events.jsonl' if mutation == 'events' else 'result.json'
            target = path.parent/name
            target.write_bytes(b'{}\n')
        path.write_text(json.dumps(receipt))
        entry['provider_manifest'] = ref(tmp_path, path)
        review_path = tmp_path/entry['amendment']['path']; review = json.loads(review_path.read_text())
        review['approved_receipts']['detail-10'] = entry['provider_manifest']
        review_path.write_text(json.dumps(review)); entry['amendment'] = ref(tmp_path, review_path)
    with pytest.raises(LegalMathError): account_receipt.checked(tmp_path, checkpoint, 'detail-10', entry)
