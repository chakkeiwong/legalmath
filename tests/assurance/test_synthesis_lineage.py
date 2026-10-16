from copy import deepcopy
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import read_evidence, evidence_file
from legalmath.interpretation.assurance.phased import synthesis_recovery as recovery
from tests.assurance.test_synthesis_successor import fixture


def reused(root):
    f = fixture(root)
    old, phase, dispatch, ledger, outcomes = recovery.metadata(root, f.pointer, 'source')
    stage = f.put('stage-2.json', {'grant_hash': 'grant', 'sequence': 2})
    key = 'reduce-q-0-0'
    dispatch = deepcopy(dispatch)
    dispatch['calls'][key]['retained_initial'] = {'manifest': f.pointer,
        'result': old['rows'][key]['result'],
        'evidence_class': 'RETAINED_EXACT_SYNTHESIS; NOT_A_NEW_MODEL_SAMPLE'}
    for name, row in old['rows'].items():
        for kind, filename in (('request', 'request'), ('schema', 'schema'), ('result', 'result')):
            f.put('second/calls/' + name + '/' + filename + '.json', read_evidence(row[kind], root))
        if name != key:
            f.put('second/calls/' + name + '/reference-binding.json', read_evidence(row['reference_binding'], root))
    ledger = deepcopy(ledger)
    charge = {**ledger['calls'][1], 'stage_hash': stage['sha256']}
    ledger['calls'].append(charge)
    old_receipt = old['rows']['reduce-q-0-1']['receipt']
    receipt = read_evidence(old_receipt, root)
    directory = 'provider/0003-' + charge['request_hash'][:16]
    for name in receipt['files']:
        (root / directory).mkdir(parents=True, exist_ok=True)
        (root / directory / name).write_bytes((root / old_receipt['path']).with_name(name).read_bytes())
    f.put(directory + '/manifest.json', {**receipt, 'allowance_slot': 3})
    journal = f.put('second/calls/dispatch.json', dispatch)
    current_phase = f.put('phase-2.json', {**phase, 'admission': stage})
    current_ledger = f.put('ledger-2.json', ledger)
    manifest = recovery.build(root, current_phase, journal, current_ledger, f.dispatch.provider_binding, 'provider')
    pointer = f.put('synthesis-2.json', manifest)
    return f, manifest, pointer


def test_second_generation_reuses_original_receipt_without_a_new_charge(tmp_path):
    f, manifest, pointer = reused(tmp_path)
    value = recovery.load(tmp_path, pointer, 'source', provider_binding=f.dispatch.provider_binding)
    row = value['rows']['reduce-q-0-0']
    assert row['slot'] is None and row['receipt'] is None and row['predecessor'] == f.pointer
    assert not (tmp_path / 'second/calls/reduce-q-0-0/reference-binding.json').exists()
    result, provenance = recovery.retained(tmp_path, pointer, 'reduce-q-0-0', f.requests[0], f.schema,
        f.dispatch.request_identity(f.requests[0], f.schema), 'source')
    assert result['provenance']['allowance_slot'] == 1
    assert provenance['manifest'] == pointer and not f.provider.calls


@pytest.mark.parametrize('change', ['lost_predecessor', 'unknown_charge', 'changed_result',
    'lost_historical_charge', 'changed_provenance', 'changed_binding', 'unknown_instruction'])
def test_reused_success_requires_exact_lineage_and_zero_current_charge(tmp_path, change):
    f, value, pointer = reused(tmp_path)
    if change == 'lost_predecessor': value['rows']['reduce-q-0-0'].pop('predecessor')
    elif change in ('unknown_charge', 'lost_historical_charge'):
        ledger = read_evidence(value['ledger'], tmp_path)
        if change == 'unknown_charge':
            phase = read_evidence(value['phase'], tmp_path)
            ledger['calls'].append({**ledger['calls'][0], 'stage_hash': phase['admission']['sha256']})
        else: ledger['calls'][0]['request_hash'] = 'changed'
        value['ledger'] = f.put('changed-ledger.json', ledger)
    elif change == 'changed_result':
        value['rows']['reduce-q-0-0']['result'] = f.put('changed-result.json', {'status': 'VALIDATED', 'value': {}})
    elif change == 'changed_provenance':
        dispatch = read_evidence(value['dispatch'], tmp_path)
        dispatch['calls']['reduce-q-0-0']['retained_initial']['evidence_class'] = 'new sample'
        value['dispatch'] = f.put('changed-dispatch.json', dispatch)
    elif change == 'changed_binding':
        value['rows']['reduce-q-0-0']['reference_binding'] = value['rows']['reduce-q-0-1']['reference_binding']
    else: value['instruction_profile'] = 'unreviewed'
    with pytest.raises(LegalMathError):
        recovery.load(tmp_path, f.put('changed.json', value), 'source')
    assert not f.provider.calls
