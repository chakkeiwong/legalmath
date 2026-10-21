from pathlib import Path
import json
import shutil
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import account_gap_preservation as gap
from scripts.legal_integration_master import ROOT
from scripts.legal_mission_execution import read, ref

WORK = Path('artifacts/legal-mission-control/2026-10-19/gap-preservation')
KEY = 'detail-77-part-0-part-1-part-1'


def copied_receipt(tmp_path):
    checkpoint = read(ROOT/WORK/'recovery-p10.json')
    entry = checkpoint['completed_account_receipts'][KEY]
    def copy(node):
        if isinstance(node, dict):
            if set(node) == {'path', 'sha256'}:
                src, dst = ROOT/node['path'], tmp_path/node['path']
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            else:
                for child in node.values(): copy(child)
        elif isinstance(node, list):
            for child in node: copy(child)
    copy(entry)
    directory = Path(entry['provider_manifest']['path']).parent
    for name in read(ROOT/entry['provider_manifest']['path'])['files']:
        shutil.copyfile(ROOT/directory/name, tmp_path/directory/name)
    return checkpoint, entry


def test_authentic_gap_receipt_keeps_original_charge_and_all_uncertainty():
    checkpoint = read(ROOT/WORK/'recovery-p10.json')
    entry = checkpoint['completed_account_receipts'][KEY]
    old, schema, value, measurement = gap.checked(ROOT, checkpoint, KEY, entry)
    assert len(old['account_correction']['required_source_gaps']) == 3
    assert len(value['source_gaps']) == 7
    result, provenance = gap.retained(ROOT, checkpoint, ref(ROOT, WORK/'recovery-p10.json'),
        KEY, old, schema)
    assert result['value'] == value and provenance['allowance_slot'] == 3173
    assert read(ROOT/entry['originals']['result']['path'])['status'] == 'FAILED'


@pytest.mark.parametrize('mutation', ['slot','review','binding','redacted','incomplete','events','result','raw'])
def test_gap_receipt_rejects_changed_evidence(tmp_path, mutation):
    checkpoint, entry = copied_receipt(tmp_path)
    if mutation == 'slot': entry['allowance_slot'] = 3172
    elif mutation == 'review':
        path = tmp_path/entry['amendment']['path']; value = read(path)
        value['provider_calls_authorized'] = 1; path.write_text(json.dumps(value))
        entry['amendment'] = ref(tmp_path, path)
    elif mutation == 'binding': entry['reference_binding'] = entry['originals']['request']
    elif mutation == 'raw':
        path = tmp_path/entry['raw']['path']; value = read(path)
        value['value']['source_gaps'].pop(); path.write_text(json.dumps(value))
        entry['raw'] = ref(tmp_path, path)
    else:
        path = tmp_path/entry['provider_manifest']['path']; receipt = read(path)
        if mutation == 'redacted': receipt['files']['result.json']['redacted'] = True
        elif mutation == 'incomplete': receipt['complete_output_present'] = False
        else: (path.parent/('events.jsonl' if mutation == 'events' else 'result.json')).write_bytes(b'{}')
        path.write_text(json.dumps(receipt)); entry['provider_manifest'] = ref(tmp_path, path)
        review_path = tmp_path/entry['amendment']['path']; review = read(review_path)
        review['approved_receipts'][KEY] = entry['provider_manifest']
        review_path.write_text(json.dumps(review)); entry['amendment'] = ref(tmp_path, review_path)
    with pytest.raises(LegalMathError): gap.checked(tmp_path, checkpoint, KEY, entry)
