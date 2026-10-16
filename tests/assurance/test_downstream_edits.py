"""Fixed prose corrections retain authenticated original evidence and failures."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from jsonschema import ValidationError
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits
from legalmath.interpretation.assurance.bounded_product import BoundDispatch, BoundedProduct
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import downstream_edits as edits
from legalmath.interpretation.assurance.phased import downstream_instructions as guidance
from legalmath.interpretation.assurance.phased import downstream_input, synthesis_recovery as recovery
from tests.assurance.test_synthesis_successor import Provider


SCHEMA = {'type': 'object', 'additionalProperties': False,
    'properties': {'conclusion': {'type': 'string'},
        'unresolved': {'type': 'array', 'items': {'type': 'string'}}},
    'required': ['conclusion', 'unresolved']}


def fixture(root):
    def put(name, value):
        save(root / name, value)
        return evidence_file(root / name, root)
    route = SimpleNamespace(check=lambda: None, input_hash='source', limits=Limits(), encode=list)
    provider = Provider()
    dispatch = BoundDispatch(provider, root / 'next/calls', route)
    key = 'reduce-q-0-0'
    charges = []
    def stage(number, request, value, reason, predecessor=None):
        prefix = 'stage-' + str(number)
        prepared = prepare(request, SCHEMA)
        wire = digest(prepared['request'])
        stage_ref = put(prefix + '/admission.json', {'grant_hash': 'grant', 'number': number})
        charges.append({'stage_hash': stage_ref['sha256'], 'request_hash': wire})
        result = {'status': 'FAILED', 'error': 'E_INTEGRITY', 'reason': reason}
        raw = {'value': value, 'provenance': {'allowance_slot': number, 'request_hash': wire}}
        for name, data in [('request', request), ('schema', SCHEMA), ('reference-binding', prepared),
                ('result', result), ('raw', raw)]:
            put(prefix + '/calls/' + key + '/' + name + '.json', data)
        identity = dispatch.request_identity(request, SCHEMA)
        journal = put(prefix + '/calls/dispatch.json', {'input_hash': 'source', 'calls': {
            key: {'identity': identity, 'status': 'FAILED', 'result_hash': digest(result)}}})
        outcome = put(prefix + '/outcome.json', {'results': [
            {'key': key, 'result': result, 'dispatch_result_hash': digest(result)}]})
        phase = put(prefix + '/phase.json', {'status': 'INCOMPLETE', 'admission': stage_ref,
            'outcome': outcome, 'contract': {'input_hash': 'source', 'calls': [{'key': key, 'identity': identity}]}})
        directory = f'provider/{number:04}-{wire[:16]}'
        files = {}
        for name, data in [('request.json', prepared['request']), ('schema.json', prepared['schema']),
                ('result.json', value)]:
            pointer = put(directory + '/' + name, data)
            files[name] = {'bytes': (root / pointer['path']).stat().st_size,
                'retained_sha256': pointer['sha256']}
        events = root / directory / 'events.jsonl'
        events.write_text(json.dumps({'type': 'turn.completed'}) + '\n')
        files['events.jsonl'] = {'bytes': events.stat().st_size,
            'retained_sha256': evidence_file(events, root)['sha256']}
        put(directory + '/manifest.json', {'allowance_slot': number, 'request_hash': wire,
            'complete_output_present': True, 'files': files})
        ledger = put(prefix + '/ledger.json', {'grant_hash': 'grant', 'calls': charges})
        manifest = recovery.build(root, phase, journal, ledger, dispatch.provider_binding,
            'provider', instruction_profile=guidance.PROFILE,
            edit_corrections={key: predecessor} if predecessor else None)
        return put(prefix + '/synthesis.json', manifest)
    original = {'task': 'SYNTHESIZE_FINDINGS', 'records': [],
        'downstream_input_profile': downstream_input.PROFILE, 'payload': {'unchanged': 'source evidence'}}
    candidate = {'conclusion': 'Paragraph 14 of 26EC22 is not verified.',
        'unresolved': ['Client facts remain unknown.']}
    first = stage(1, original, candidate, 'Numbered assertion has no document/proposition binding')
    recovery.load(root, first, 'source')
    full = recovery.successor_request(root, read_evidence(first, root), key)
    rejected = {'conclusion': 'The statutory regime is not verified.', 'unresolved': ['No facts are missing.']}
    second = stage(2, full, rejected, 'Formatting correction changed unaffected prose or evidence', first)
    return SimpleNamespace(put=put, dispatch=dispatch, provider=provider, key=key,
        original=original, candidate=candidate, full=full, first=first, second=second)


def test_authenticated_failed_correction_changes_only_fixed_original_prose(tmp_path):
    f = fixture(tmp_path)
    manifest = recovery.load(tmp_path, f.second, 'source')
    revised = recovery.rewrite(tmp_path, f.second, f.key, f.original, SCHEMA, 'source')
    assert revised[edits.FIELD]['prior_candidate'] == f.candidate
    assert revised[edits.FIELD]['failed_correction'] == manifest['rows'][f.key]['raw']
    assert guidance.base_request(revised) == f.original
    prepared = prepare(revised, SCHEMA)
    assert set(prepared['schema']['properties']) == {'e0'}
    corrected = resolve({'e0': 'The SFC circular 26EC22 is not fully verified.'}, prepared,
        maximum_bytes=2000000)
    assert corrected['unresolved'] == f.candidate['unresolved']
    guidance.validate_correction(f.full, corrected)
    BoundedProduct.citations(SimpleNamespace(route=SimpleNamespace(envelope={}), root=tmp_path), corrected, [])
    assert recovery.retained(tmp_path, f.second, f.key, revised, SCHEMA,
        f.dispatch.request_identity(revised, SCHEMA), 'source') is None
    assert not f.provider.calls


@pytest.mark.parametrize('change', ['extra', 'missing', 'empty', 'identifier', 'classification',
    'scope', 'nested', 'profile', 'bytes', 'numbered'])
def test_edit_wire_rejects_changed_scope_schema_identifiers_and_bad_prose(tmp_path, change):
    f = fixture(tmp_path)
    revised = recovery.successor_request(tmp_path, read_evidence(f.second, tmp_path), f.key)
    output = {'e0': 'The SFC circular 26EC22 is not fully verified.'}
    maximum = 2000000
    if change == 'extra': output['unresolved'] = ['Changed']
    elif change == 'missing': output = {}
    elif change == 'empty': output['e0'] = ' '
    elif change == 'identifier': output['e0'] = 'The SFC circular is not fully verified.'
    elif change == 'classification': output['e0'] = 'The statutory regime 26EC22 is not fully verified.'
    elif change == 'scope': revised[edits.FIELD]['failure_paths'] = [{'path': '/unresolved/0'}]
    elif change == 'nested': revised['downstream_response_correction'] = revised[edits.FIELD]
    elif change == 'profile': revised[edits.FIELD]['profile'] = 'unknown'
    elif change == 'bytes': maximum = 10
    else: output['e0'] = 'Paragraph 14 of the SFC circular 26EC22 is not verified.'
    with pytest.raises((LegalMathError, ValidationError)):
        value = resolve(output, prepare(revised, SCHEMA), maximum_bytes=maximum)
        BoundedProduct.citations(SimpleNamespace(route=SimpleNamespace(envelope={}), root=tmp_path), value, [])
    assert not f.provider.calls


@pytest.mark.parametrize('change', ['lost_scope', 'wrong_predecessor', 'raw', 'receipt', 'ledger',
    'extra_key', 'wrong_profile', 'original_candidate', 'repeated_edit'])
def test_edit_successor_requires_original_rejection_and_failed_correction_receipts(tmp_path, change):
    f = fixture(tmp_path)
    manifest = read_evidence(f.second, tmp_path)
    row = manifest['rows'][f.key]
    if change == 'lost_scope': manifest.pop('edit_corrections')
    elif change == 'wrong_predecessor': manifest['edit_corrections'][f.key] = f.second
    elif change == 'raw':
        raw = read_evidence(row['raw'], tmp_path)
        raw['value']['unresolved'] = f.candidate['unresolved']
        row['raw'] = f.put('changed-raw.json', raw)
    elif change == 'receipt':
        receipt = read_evidence(row['receipt'], tmp_path)
        receipt['request_hash'] = 'changed'
        row['receipt'] = f.put('changed-receipt.json', receipt)
    elif change == 'ledger':
        ledger = read_evidence(manifest['ledger'], tmp_path)
        ledger['calls'][0]['request_hash'] = 'changed'
        manifest['ledger'] = f.put('changed-ledger.json', ledger)
    elif change == 'extra_key': manifest['edit_corrections']['reduce-q-0-1'] = f.first
    elif change == 'wrong_profile': manifest['edit_profile'] = 'unknown'
    else:
        request = read_evidence(row['request'], tmp_path)
        if change == 'original_candidate':
            request['downstream_response_correction']['prior_candidate']['unresolved'] = ['False original.']
        else: request[edits.FIELD] = request['downstream_response_correction']
        row['request'] = f.put('changed-request.json', request)
    with pytest.raises(LegalMathError):
        recovery.load(tmp_path, f.put('changed-manifest.json', manifest), 'source')
    assert not f.provider.calls


def test_ordinary_requests_remain_identical_and_repeated_edit_is_forbidden(tmp_path):
    f = fixture(tmp_path)
    prepared = prepare(f.original, SCHEMA)
    assert edits.apply(deepcopy(prepared)) == prepared
    revised = recovery.successor_request(tmp_path, read_evidence(f.second, tmp_path), f.key)
    with pytest.raises(LegalMathError): guidance.annotate(revised, correction=revised[edits.FIELD])
