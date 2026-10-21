"""Integrity controls for missing pre-dispatch roots and completed receipts."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_recovery, account_output
from tests.assurance.test_bounded_product import Scripted, envelope, limits


def lineage(tmp_path, receipt=False):
    options = dict(limits=replace(limits(), input_tokens=12000, output_tokens=3000),
        requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE)
    prior = BoundedProduct(tmp_path, tmp_path/'prior', Scripted(fail_at=2), envelope(), list, **options)
    question = envelope()['original_questions'][0]
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    good = prior.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {'assignment': 'First'}, ['o1'])
    bad = prior.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {'assignment': 'Second'}, ['o2'])
    details = [{'id': 'o1', 'result': good}, {'id': 'o2', 'result': bad}]
    (prior.directory/'requirement-details.json').write_text(json.dumps(details))
    old = account_recovery.build(tmp_path, prior.directory/'calls', details)
    if receipt:
        old['completed_account_receipts'] = {'detail-1': {
            'originals': deepcopy(old['account_recovery']['originals']['detail-1']),
            'dispatch': deepcopy(old['dispatch']), 'allowance_slot': 7}}
    pointer = put(tmp_path, 'prior-recovery.json', old)
    latest = BoundedProduct(tmp_path, tmp_path/'latest', Scripted(), envelope(), list,
        requirement_account_recovery=pointer, **options)
    assert latest.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {'assignment': 'First'}, ['o1']) == good
    # detail-1 is absent from this journal: refused before any dispatch reservation.
    (latest.directory/'requirement-details.json').write_text(json.dumps(details))
    composite = account_recovery.build(tmp_path, latest.directory/'calls', details, predecessor=pointer)
    return composite, options, records, question, good


def put(root, name, value):
    path = root/name; path.write_text(json.dumps(value))
    return evidence_file(path, root)


def test_missing_latest_root_keeps_authenticated_origin_and_exact_success(tmp_path):
    manifest, options, records, question, good = lineage(tmp_path)
    pointer = put(tmp_path, 'composite.json', manifest)
    assert account_recovery.load(tmp_path, pointer, manifest['input_hash']) == manifest
    assert set(manifest['account_recovery']['originals']) == {'detail-0', 'detail-1'}
    assert manifest['original_dispatches']['detail-1']['path'] == 'prior/calls/dispatch.json'
    provider = Scripted()
    fresh = BoundedProduct(tmp_path, tmp_path/'fresh', provider, envelope(), list,
        requirement_account_output_profile=account_output.PROFILE,
        requirement_account_recovery=pointer, **options)
    assert fresh.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {'assignment': 'First'}, ['o1']) == good
    assert not provider.requests
    assert fresh.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {'assignment': 'Second'}, ['o2'])['status'] == 'VALIDATED'
    assert len(provider.requests) == 1


@pytest.mark.parametrize('mutation', ['omit', 'origin', 'success', 'population', 'input', 'predecessor'])
def test_composite_rejects_lost_or_changed_lineage(tmp_path, mutation):
    manifest, *_ = lineage(tmp_path)
    if mutation == 'omit': manifest['account_recovery']['originals'].pop('detail-1')
    elif mutation == 'origin': manifest['original_dispatches']['detail-1'] = manifest['dispatch']
    elif mutation == 'success': manifest['calls']['detail-0'] = manifest['account_recovery']['originals']['detail-1']
    elif mutation == 'population':
        path = tmp_path/'latest/requirement-details.json'
        path.write_text(json.dumps(json.loads(path.read_text())[:1]))
        manifest['account_recovery']['details'] = evidence_file(path, tmp_path)
    elif mutation == 'input': manifest['input_hash'] = 'foreign'
    else: manifest.pop('predecessor_recovery')
    pointer = put(tmp_path, 'tampered.json', manifest)
    with pytest.raises(LegalMathError): account_recovery.load(tmp_path, pointer, manifest['input_hash'])


@pytest.mark.parametrize('mutation', [None, 'omit', 'charge', 'origin'])
def test_successor_preserves_completed_receipt_or_rejects_mutation(tmp_path, monkeypatch, mutation):
    from legalmath.interpretation.assurance.phased import account_receipt
    # Isolate lineage checks; actual receipt bytes are checked in the test below.
    monkeypatch.setattr(account_receipt, 'checked', lambda *args: None)
    manifest, *_ = lineage(tmp_path, receipt=True)
    assert manifest['completed_account_receipts']['detail-1']['allowance_slot'] == 7
    if mutation == 'omit': manifest.pop('completed_account_receipts')
    elif mutation == 'charge': manifest['completed_account_receipts']['detail-1']['allowance_slot'] = 8
    elif mutation == 'origin': manifest['completed_account_receipts']['detail-1']['dispatch'] = manifest['dispatch']
    pointer = put(tmp_path, 'receipt-composite.json', manifest)
    if mutation:
        with pytest.raises(LegalMathError):
            account_recovery.load(tmp_path, pointer, manifest['input_hash'])
    else:
        assert account_recovery.load(tmp_path, pointer, manifest['input_hash']) == manifest


def test_real_receipt_authenticates_original_composite_dispatch():
    from scripts.legal_integration_master import ROOT
    from scripts.legal_mission_execution import read
    from legalmath.interpretation.assurance.phased import account_receipt
    checkpoint = read(ROOT / 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-1/recovery-p10.json')
    entry = checkpoint['completed_account_receipts']['detail-10']
    checkpoint['original_dispatches'] = {'detail-10': deepcopy(checkpoint['dispatch'])}
    checkpoint['dispatch'] = {'path': 'later/composite-dispatch.json', 'sha256': 'later'}
    _, _, value, measurement = account_receipt.checked(ROOT, checkpoint, 'detail-10', entry)
    assert value and measurement['wire_tokens'] > 2048
    entry['dispatch'] = checkpoint['dispatch']
    with pytest.raises(LegalMathError):
        account_receipt.checked(ROOT, checkpoint, 'detail-10', entry)


@pytest.mark.parametrize('mutation', [None, 'result', 'provenance', 'failed'])
def test_receipt_can_only_be_promoted_by_exact_authenticated_reuse(tmp_path, mutation):
    from scripts.legal_integration_master import ROOT
    from scripts.legal_mission_execution import read
    from legalmath.canonical import digest
    from legalmath.interpretation.assurance.phased import account_receipt
    path = ROOT / 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-1/recovery-p10.json'
    inherited = read(path)
    pointer = evidence_file(path, ROOT)
    entry = inherited['completed_account_receipts']['detail-10']
    request, schema, _, _ = account_receipt.checked(ROOT, inherited, 'detail-10', entry)
    request['account_output_profile'] = account_output.PROFILE
    result, provenance = account_receipt.retained(ROOT, inherited, pointer, 'detail-10', request, schema)
    row = {'status':'VALIDATED', 'result_hash':digest(result), 'retained_initial':deepcopy(provenance)}
    if mutation == 'result': result['request_hash'] = 'changed'
    elif mutation == 'provenance': row['retained_initial']['allowance_slot'] = 999
    elif mutation == 'failed': row['status'] = 'FAILED'
    refs = {name:put(tmp_path,name+'.json',value) for name,value in
        (('request',request),('schema',schema),('result',result))}
    refs = {name:{**p,'path':str(tmp_path/p['path'])} for name,p in refs.items()}
    # Store successor bytes under the actual root, as required by evidence paths.
    from unittest.mock import patch
    original = account_recovery.read_evidence
    def evidence(p, root):
        if p in refs.values(): return json.loads(__import__('pathlib').Path(p['path']).read_text())
        return original(p, root)
    with patch.object(account_recovery, 'read_evidence', evidence):
        args = (ROOT, inherited, pointer, {'calls':{'detail-10':row}}, {'detail-10':refs}, {})
        if mutation:
            with pytest.raises(LegalMathError): account_recovery.inherited_receipts(*args)
        else:
            assert account_recovery.inherited_receipts(*args) == {}
