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


def lineage(tmp_path):
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
