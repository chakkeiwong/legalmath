from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, AUDIT, WARRANT
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.integration_contract import read_evidence, evidence_file
from legalmath.interpretation.assurance.phased import downstream_input, downstream_instructions as guidance
from legalmath.interpretation.assurance.phased import synthesis_recovery as recovery
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from tests.assurance.test_downstream_capacity import product
from tests.assurance.test_synthesis_successor import fixture


@pytest.mark.parametrize('schema,task', [(NOTE, 'SYNTHESIZE_FINDINGS'),
    (AUDIT, 'AUDIT_ANSWER_AND_DETAILED_ACCOUNT'), (WARRANT, 'ASSESS_REVIEW_WARRANT')])
def test_schema_guidance_preserves_actual_wire_sources_selectors_and_shapes(tmp_path, schema, task):
    p = product(tmp_path, downstream_input_profile=downstream_input.PROFILE)
    records = [r for r in p.route.records.values() if r['kind'] == 'source']
    request = p.request(task, p.route.envelope['original_questions'][0], records,
        payload={'whole': records}, expected=['obligation'])
    old = prepare(request, schema)
    new = prepare(guidance.annotate(request), schema)
    assert new['schema'] == old['schema']
    stripped = {k: v for k, v in new['request'].items() if k not in
        ('downstream_instruction_profile', 'instructions', 'response_reference_instructions')}
    assert stripped == {k: v for k, v in old['request'].items() if k not in
        ('instructions', 'response_reference_instructions')}
    assert 'including assumptions, unresolved items' in new['request']['response_reference_instructions']
    assert ('Put verdict, issues and support inside review.' in new['request']['response_reference_instructions']) == (schema == AUDIT)
    assert prepare(request, schema) == old  # Ordinary historical bytes unchanged.


def correctable(root):
    f = fixture(root)
    manifest, phase, dispatch, ledger, outcomes = recovery.metadata(root, f.pointer, 'source')
    dispatch, ledger, phase = deepcopy(dispatch), deepcopy(ledger), deepcopy(phase)
    for i in (1, 2):
        key = 'reduce-q-0-' + str(i)
        request = deepcopy(f.requests[i])
        request['downstream_input_profile'] = downstream_input.PROFILE
        f.requests[i] = request
        prepared = prepare(request, f.schema)
        identity = f.dispatch.request_identity(request, f.schema)
        f.put('old/calls/' + key + '/request.json', request)
        f.put('old/calls/' + key + '/reference-binding.json', prepared)
        dispatch['calls'][key]['identity'] = identity
        next(c for c in phase['contract']['calls'] if c['key'] == key)['identity'] = identity
        if i == 1:
            raw = {'value': {'conclusion': 'Paragraph 14 is not verified in these extracts.'},
                'provenance': {'allowance_slot': 2, 'request_hash': digest(prepared['request'])}}
            result = {'status': 'FAILED', 'error': 'E_INTEGRITY',
                'reason': 'Numbered assertion has no document/proposition binding'}
            f.put('old/calls/' + key + '/raw.json', raw)
            f.put('old/calls/' + key + '/result.json', result)
            dispatch['calls'][key].update(status='FAILED', result_hash=digest(result))
            outcomes[key] = {'key': key, 'result': result, 'dispatch_result_hash': digest(result)}
            ledger['calls'][1]['request_hash'] = digest(prepared['request'])
            directory = 'provider/0002-' + digest(prepared['request'])[:16]
            files = {}
            for name, value in (('request.json', prepared['request']), ('schema.json', prepared['schema']),
                    ('result.json', raw['value'])):
                pointer = f.put(directory + '/' + name, value)
                files[name] = {'bytes': (root / pointer['path']).stat().st_size, 'retained_sha256': pointer['sha256']}
            events = root / directory / 'events.jsonl'
            events.write_text(json.dumps({'type': 'turn.completed'}) + '\n')
            files['events.jsonl'] = {'bytes': events.stat().st_size, 'retained_sha256': evidence_file(events, root)['sha256']}
            f.put(directory + '/manifest.json', {'allowance_slot': 2, 'request_hash': digest(prepared['request']),
                'complete_output_present': True, 'files': files})
    phase['outcome'] = f.put('new-outcome.json', {'results': list(outcomes.values())})
    pointer = f.put('correctable.json', recovery.build(root, f.put('new-phase.json', phase),
        f.put('old/calls/dispatch.json', dispatch), f.put('new-ledger.json', ledger),
        f.dispatch.provider_binding, 'provider', instruction_profile=guidance.PROFILE))
    f.pointer = pointer
    f.combined = f.put('new-combined.json', {'profile': recovery.PROFILE, 'input_hash': 'source',
        'account': f.account, 'synthesis': pointer})
    return f


def test_completed_rejection_is_bound_correction_not_transport_retry(tmp_path):
    f = correctable(tmp_path)
    value = recovery.load(tmp_path, f.pointer, 'source')
    assert value['rows']['reduce-q-0-1']['disposition'] == 'COMPLETED_RESPONSE_REJECTED'
    request = recovery.rewrite(tmp_path, f.pointer, 'reduce-q-0-1', f.requests[1], f.schema, 'source')
    assert guidance.base_request(request) == f.requests[1]
    correction = request['downstream_response_correction']
    assert correction['prior_candidate']['conclusion'].startswith('Paragraph 14')
    assert correction['failure_paths'][0]['path'] == '/conclusion'
    with pytest.raises(LegalMathError):
        BoundedProduct.citations(SimpleNamespace(route=SimpleNamespace(envelope={}), root=tmp_path),
            correction['prior_candidate'], [])
    assert recovery.retained(tmp_path, f.pointer, 'reduce-q-0-1', request, f.schema,
        f.dispatch.request_identity(request, f.schema), 'source') is None
    with pytest.raises(LegalMathError): guidance.annotate(request, correction=correction)
    assert not f.provider.calls


@pytest.mark.parametrize('field', ['support', 'contrary', 'considered', 'source_gaps', 'assertion_bindings'])
def test_format_correction_cannot_drop_evidence_or_uncertainty(field):
    prior = {field: ['retained'], 'conclusion': 'Missing provision.'}
    request = {'downstream_response_correction': {'prior_candidate': prior, 'failure_paths': []}}
    guidance.validate_correction(request, prior)
    with pytest.raises(LegalMathError): guidance.validate_correction(request, {**prior, field: []})


def test_correction_preserves_unaffected_qualifications_and_order():
    prior = {'conclusion': 'Paragraph 14 is not delivered.',
        'unresolved': ['Client facts remain unknown.'], 'source_gaps': []}
    request = {'downstream_response_correction': {'prior_candidate': prior,
        'failure_paths': [{'path': '/conclusion'}]}}
    revised = {**prior, 'conclusion': 'The applicable confirmation standard is not delivered.'}
    guidance.validate_correction(request, revised)
    for change in ({**revised, 'unresolved': []}, {**revised, 'unresolved': ['No problem.']}):
        with pytest.raises(LegalMathError): guidance.validate_correction(request, change)


def test_phase_adapter_leaves_success_exact_and_changes_only_reviewed_missing_requests(tmp_path):
    f = correctable(tmp_path)
    f.dispatch.retained_initial = (tmp_path, f.combined)
    p = SimpleNamespace(root=tmp_path, dispatch=f.dispatch, route=f.route,
        downstream_instruction_profile=guidance.PROFILE)
    calls = [{'key': 'reduce-q-0-' + str(i), 'request': request, 'schema': f.schema,
        'validate': lambda value: None} for i, request in enumerate(f.requests)]
    rewritten = PhasedProduct.prepare_calls(p, calls)
    assert rewritten[0]['request'] == f.requests[0]
    assert 'downstream_response_correction' in rewritten[1]['request']
    assert rewritten[2]['request'] == guidance.annotate(f.requests[2])
    changed = deepcopy(f.requests[1]); changed['payload'] = {'case': 'different evidence'}
    with pytest.raises(LegalMathError): recovery.rewrite(tmp_path, f.pointer, 'reduce-q-0-1', changed, f.schema, 'source')
    assert not f.provider.calls


@pytest.mark.parametrize('change', ['raw', 'unreviewed_rejection', 'lost_profile', 'source', 'provider'])
def test_complete_rejection_cannot_be_reclassified_or_rewritten_arbitrarily(tmp_path, change):
    f = correctable(tmp_path)
    value = read_evidence(f.pointer, tmp_path)
    if change == 'raw':
        raw = read_evidence(value['rows']['reduce-q-0-1']['raw'], tmp_path)
        raw['value']['conclusion'] = 'Nothing is missing.'
        value['rows']['reduce-q-0-1']['raw'] = f.put('wrong-raw.json', raw)
    elif change == 'unreviewed_rejection':
        value['rows']['reduce-q-0-1']['disposition'] = 'CHARGED_NO_OUTPUT_FAILURE'
    elif change == 'lost_profile': value.pop('instruction_profile')
    elif change == 'source':
        request = {**f.requests[1], 'payload': {'new': 'authority'}}
        with pytest.raises(LegalMathError):
            recovery.retained(tmp_path, f.pointer, 'reduce-q-0-1', request, f.schema,
                f.dispatch.request_identity(request, f.schema), 'source')
        return
    else: value['provider_binding']['routing'] = {'model': 'different'}
    with pytest.raises(LegalMathError):
        recovery.load(tmp_path, f.put('changed-correctable.json', value), 'source')
    assert not f.provider.calls
