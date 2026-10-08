"""Candidate ownership, retained roles, new authorization and bounded restart."""
from copy import deepcopy
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2 as fidelity
from legalmath.interpretation.assurance import executable_references_v2 as expressions
from legalmath.interpretation.assurance import source_references as sources
from scripts import legal_coverage_candidates as codec
from scripts import legal_coverage_aliases as aliases
from scripts import legal_coverage_resume as resume
from .test_coverage_aliases import fixture


@pytest.mark.parametrize('status', ['PRESERVES', 'UNAVAILABLE', 'BLOCKED'])
def test_candidate_constraints_preserve_valid_proposals_and_original_validation(status):
    wire, schema, original, inputs, context = fixture(status)
    revised, output_schema, binding = codec.prepare(wire, schema)
    encoded = aliases.encode_response(original, wire, schema)
    decoded = codec.resolve(encoded, wire, schema, binding)
    assert decoded == original
    assert revised['source_packet'] == wire['source_packet']
    assert revised['candidates'] == wire['candidates']
    assert revised['pair_targets'][0]['question'] == wire['candidates'][0]['question']['question']
    p, claims, candidates, questions = inputs
    request, original_schema, executable_schema, erefs, srefs = context
    sourced = sources.resolve_response(decoded, executable_schema, schema, srefs, p, srefs['request_hash'])
    resolved = expressions.resolve(sourced, request, original_schema, erefs, readings=candidates, questions=questions)
    assert fidelity.validate(resolved, p, claims, candidates, questions)


def mixed_fixture():
    _, _, _, inputs, _ = fixture('PRESERVES')
    packet, claims, candidates, questions = inputs
    other = deepcopy(candidates['candidate']); other['formalization'] = None
    candidates['unformalized'] = other
    questions['unformalized'] = deepcopy(questions['candidate'])
    questions['unformalized']['control_id'] = 'unformalized-control'
    request = fidelity.request(packet, claims, candidates, questions)
    schema = fidelity.FidelityV2.model_json_schema()
    ew, es, erefs = expressions.prepare(request, schema, readings=candidates, questions=questions)
    wire, ws, srefs = sources.prepare(ew, es)
    return wire, ws


@pytest.mark.parametrize('fault', ['foreign_executable', 'unavailable_comparison', 'changed_question', 'changed_binding'])
def test_mixed_candidate_faults_rejected_before_internal_correspondence_acceptance(fault):
    wire, schema = mixed_fixture()
    _, _, binding = codec.prepare(wire, schema)
    _, _, original, _, _ = fixture('PRESERVES')
    base = original['checks'][0]
    claims = wire['claims']; candidates = wire['candidates']
    source_span = wire['source_references']['spans'][0]['span_id']
    executable_span = wire['executable_references']['spans'][0]['span_id']
    checks = []
    for candidate in candidates:
        row = deepcopy(base)
        row['candidate_id'] = candidate['candidate_id']
        row['claim_id'] = claims[0]['claim_id']
        row['question_relation']['question_hash'] = candidate['question_hash']
        for k in ('source_support', 'question_relation'):
            row[k]['evidence'] = [{'span_ids': [source_span]}]
        row['executable_correspondence']['representation_quotes'] = [executable_span]
        if candidate['candidate_id'] == 'unformalized':
            row['executable_correspondence'].update(status='UNAVAILABLE', representation_quotes=[])
            row['followup_questions'] = ['What formalization expresses the original meaning?']
        checks.append(row)
    value = aliases.encode_response({'checks': checks, 'additional_concerns': []}, wire, schema)
    assert codec.resolve(value, wire, schema, binding)
    target = next(r for r in value['checks'] if binding['base_alias_references']['pairs'][r['pair']][1] == 1)
    if fault == 'foreign_executable': target['executable_correspondence']['representation_quotes'] = ['e0']
    elif fault == 'unavailable_comparison': target['executable_correspondence']['status'] = 'OMITS'
    elif fault == 'changed_question': wire['candidates'][1]['question_hash'] = '0' * 64
    else: binding['base_alias_references']['pairs'][target['pair']][1] = 0
    with pytest.raises(LegalMathError): codec.resolve(value, wire, schema, binding)


@pytest.mark.parametrize('status', ['UNCERTAIN', 'UNASSESSED', 'NOT_APPLICABLE_TO_THIS_QUESTION'])
def test_candidate_schema_retains_uncertainty_and_not_applicable(status):
    wire, schema, original, _, _ = fixture()
    row = original['checks'][0]
    row['question_relation']['status'] = status
    row['executable_correspondence']['status'] = 'NOT_APPLICABLE' if status.startswith('NOT_APPLICABLE') else 'UNASSESSED'
    _, _, binding = codec.prepare(wire, schema)
    value = aliases.encode_response(original, wire, schema)
    assert codec.resolve(value, wire, schema, binding) == original


def grant(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'ROOT', tmp_path)
    monkeypatch.setattr(resume.time, 'time', lambda: resume.DEADLINE - 1000)
    old = tmp_path / 'prior.json'
    old.write_text(json.dumps({'maximum': 100, 'calls': [{'retained': i} for i in range(54)]}))
    path = tmp_path / 'authorization.json'
    path.write_text(json.dumps({'schema': 'legalmath.coverage-resumption-grant.v1',
        'authorization': resume.AUTHORIZATION, 'maximum': 200, 'repair_maximum': 100,
        'deadline_epoch': resume.DEADLINE, 'predecessor': [resume.ref(old)]}))
    return path


def test_additional_grant_caps_calls_without_resetting_nonexhausted_history(tmp_path, monkeypatch):
    path = grant(tmp_path, monkeypatch)
    previous = (tmp_path / 'prior.json').read_bytes()
    allowance = resume.ResumeAllowance(17, 'qualification-first', 'repair', path)
    for _ in range(200): allowance.reserve('a' * 64)
    with pytest.raises(LegalMathError): allowance.reserve('b' * 64)
    assert allowance.verify()['used'] == 200
    assert (tmp_path / 'prior.json').read_bytes() == previous


@pytest.mark.parametrize('fault', ['history', 'authorization', 'expiry', 'hash', 'role', 'batch'])
def test_grant_rejects_changes_and_expiry_before_dispatch(tmp_path, monkeypatch, fault):
    path = grant(tmp_path, monkeypatch)
    allowance = resume.ResumeAllowance(17, 'qualification-first', grant_path=path)
    if fault == 'history': (tmp_path / 'prior.json').write_text('{}')
    elif fault == 'authorization': path.write_text('{}')
    elif fault == 'expiry': monkeypatch.setattr(resume.time, 'time', lambda: resume.DEADLINE)
    elif fault == 'role': allowance.role = 'peer-copy'
    elif fault == 'batch': allowance.batch = 16
    with pytest.raises(LegalMathError): allowance.reserve('bad' if fault == 'hash' else 'a' * 64)
    assert not (tmp_path / 'allowance.json').exists()


def test_only_valid_original_roles_are_retained(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'ROOT', tmp_path)
    result = {'batches': [{'proposals': [{'retained': True}], 'attempts': [
        {'role': 'source-first', 'status': 'VALIDATED_PROPOSAL'},
        {'role': 'qualification-first', 'status': 'REJECTED_RESPONSE'}]}]}
    path = tmp_path / 'result.json'; path.write_text(json.dumps(result))
    selected = resume.selected_roles([{'receipt': {'historical': True}, 'value': {
        'arm': 'combined', 'batch': 17, 'result': resume.ref(path)}}])
    assert set(selected) == {(17, 'source-first')}
    assert selected[(17, 'source-first')]['proposal'] == {'retained': True}


def test_interrupted_role_cannot_redispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'OUT', tmp_path)
    monkeypatch.setattr(resume, 'check_review', lambda: {})
    folder = resume.role_directory(17, 'qualification-first'); folder.mkdir(parents=True)
    (folder / 'started.json').write_text('{}')
    monkeypatch.setattr(resume, 'CandidateProvider', lambda *a, **k: pytest.fail('Unexpected dispatch'))
    with pytest.raises(LegalMathError) as exc: resume.run_role(17, 'qualification-first', {}, [])
    assert exc.value.code == 'E_JOB_STATE'


@pytest.mark.parametrize('complete', [True, False])
def test_completed_or_failed_restart_never_schedules_another_call(monkeypatch, complete):
    monkeypatch.setattr(resume, 'check_review', lambda: {})
    monkeypatch.setattr(resume, 'tested', lambda: {})
    monkeypatch.setattr(resume, 'aggregate', lambda: {'execution_complete': complete, 'failed_roles': [] if complete else [1]})
    monkeypatch.setattr(resume, 'verify', lambda: {'execution_complete': True})
    monkeypatch.setattr(resume, 'refresh', lambda: {'failed_roles': [1]})
    monkeypatch.setattr(resume, 'run_role', lambda *a: pytest.fail('Unexpected live role'))
    result = resume.execute()
    assert result.get('execution_complete') if complete else result['status'] == 'REPAIR_REVIEW_REQUIRED'


def service_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'ROOT', tmp_path)
    monkeypatch.setattr(resume, 'OUT', tmp_path)
    from scripts import legal_gap_program
    monkeypatch.setattr(legal_gap_program, 'ROOT', tmp_path)
    def verify(path, *args):
        value = resume.read(path)
        for item in value.get('evidence', []): resume.checked(item)
        return value
    monkeypatch.setattr(resume, 'verify_role', verify)
    folder = resume.role_directory(21, 'qualification-first')
    details = 'unexpected status 502 Bad Gateway: Upstream service temporarily unavailable'
    failure = {'error': 'E_DEPENDENCY', 'details': details}
    resume.save(folder / 'receipt.json', {'complete': False, 'proposal': None, 'calls': 1,
        'batch': 21, 'role': 'qualification-first', 'stopped': failure})
    resume.save(folder / 'model/journal.json', {'value': {'actions': [
        {'status': 'FAILED', **failure}]}})
    resume.save(folder / 'candidate-responses/request/started.json', {'wire_hash': 'a' * 64})
    transport = tmp_path / 'provider-evidence/failed'
    resume.save(transport / 'schema.json', {'schema': 'unchanged'})
    resume.save(transport / 'events.jsonl', {'type': 'turn.failed', 'error': {'message': details}})
    # The transport is JSONL; one canonical record is also a valid single line.
    (transport / 'events.jsonl').write_text(json.dumps({'type': 'turn.failed', 'error': {'message': details}}))
    files = {p.name: {'retained_sha256': resume.ref(p)['sha256'],
                     'original_sha256': resume.ref(p)['sha256']} for p in transport.iterdir()}
    resume.save(transport / 'manifest.json', {'allowance_slot': 1, 'request_hash': 'a' * 64,
        'complete_output_present': False, 'files': files})
    resume.save(tmp_path / 'allowance.json', {'maximum': 200, 'calls': [
        {'batch': 21, 'role': 'qualification-first', 'request_hash': 'a' * 64}]})
    resume.save(tmp_path / 'note.json', {'reviewed': True})
    spec = {'kind': 'returned-http-502-no-output', 'batch': 21, 'role': 'qualification-first',
        'attempt': 1, 'maximum_calls': 1, 'previous': resume.ref(folder / 'receipt.json'),
        'note': resume.ref(tmp_path / 'note.json'), 'transport': resume.ref(transport / 'manifest.json'),
        'dispatch': {'request_hash': 'a' * 64, 'schema_hash': files['schema.json']['original_sha256']}}
    return folder, spec


def test_returned_502_is_eligible_without_refunding_failed_call(tmp_path, monkeypatch):
    folder, spec = service_failure(tmp_path, monkeypatch)
    ledger = (tmp_path / 'allowance.json').read_bytes()
    assert resume.validate_recovery(spec, {}, []) == spec
    assert (tmp_path / 'allowance.json').read_bytes() == ledger


@pytest.mark.parametrize('fault', ['schema', 'auth', 'timeout', 'unknown', 'proposal', 'output',
                                 'journal', 'event', 'request', 'role', 'transport', 'unbounded'])
def test_service_review_rejects_other_failures_and_invalid_evidence(tmp_path, monkeypatch, fault):
    folder, spec = service_failure(tmp_path, monkeypatch)
    receipt = resume.read(folder / 'receipt.json')
    if fault in ('schema', 'auth', 'timeout', 'unknown'):
        receipt['stopped'] = {'error': {'schema': 'E_SCHEMA', 'auth': 'E_AUTHORITY',
            'timeout': 'E_RESOURCE_LIMIT', 'unknown': 'E_DEPENDENCY'}[fault], 'details': fault}
    elif fault == 'proposal': receipt['proposal'] = {'partial': True}
    elif fault == 'output':
        resume.save(resume.checked(spec['transport']).parent / 'result.json', {'unexpected': 'output'})
    elif fault == 'journal': resume.save(folder / 'model/journal.json', {'value': {'actions': []}})
    elif fault in ('event', 'transport'):
        path = resume.checked(spec['transport'])
        (path.parent / 'events.jsonl').write_text(json.dumps({'type': 'turn.completed'}))
        if fault == 'event':
            manifest = resume.read(path)
            manifest['files']['events.jsonl']['retained_sha256'] = resume.ref(path.parent / 'events.jsonl')['sha256']
            resume.save(path, manifest); spec['transport'] = resume.ref(path)
    elif fault == 'request': spec['dispatch']['request_hash'] = 'b' * 64
    elif fault == 'role': spec['role'] = 'source-first'
    elif fault == 'unbounded': spec['maximum_calls'] = 2
    resume.save(folder / 'receipt.json', receipt)
    spec['previous'] = resume.ref(folder / 'receipt.json')
    with pytest.raises(LegalMathError): resume.validate_recovery(spec, {}, [])


def completed_attempt(folder, spec, tmp_path, *, complete=True):
    resume.save(tmp_path / 'recovery.json', spec)
    attempt = folder / 'attempt-01'
    resume.save(attempt / 'started.json', {'recovery': resume.ref(tmp_path / 'recovery.json')})
    resume.save(attempt / 'receipt.json', {'batch': 21, 'role': 'qualification-first',
        'complete': complete, 'proposal': {'valid': True} if complete else None})
    resume.save(folder / 'latest.json', {'receipt': resume.ref(attempt / 'receipt.json')})
    return attempt


def test_latest_role_preserves_prior_failure_and_verifies_it(tmp_path, monkeypatch):
    folder, spec = service_failure(tmp_path, monkeypatch)
    old = (folder / 'receipt.json').read_bytes()
    attempt = completed_attempt(folder, spec, tmp_path)
    value, path = resume.latest_role(folder, {}, [])
    assert value['complete'] and path == attempt / 'receipt.json'
    assert (folder / 'receipt.json').read_bytes() == old
    (folder / 'receipt.json').write_text('{}')
    with pytest.raises((LegalMathError, KeyError)): resume.latest_role(folder, {}, [])


@pytest.mark.parametrize('fault', ['started', 'unselected', 'foreign_pointer', 'changed_receipt', 'skipped_attempt'])
def test_interrupted_or_substituted_successor_blocks_normal_execution(tmp_path, monkeypatch, fault):
    folder, spec = service_failure(tmp_path, monkeypatch)
    attempt = completed_attempt(folder, spec, tmp_path)
    if fault == 'started': (attempt / 'receipt.json').unlink()
    elif fault == 'unselected': (folder / 'latest.json').unlink()
    elif fault == 'foreign_pointer': resume.save(folder / 'latest.json', {'receipt': spec['previous']})
    elif fault == 'changed_receipt': (attempt / 'receipt.json').write_text('{}')
    elif fault == 'skipped_attempt': (folder / 'attempt-03').mkdir()
    monkeypatch.setattr(resume, 'check_review', lambda: {})
    monkeypatch.setattr(resume, 'CandidateProvider', lambda *a, **k: pytest.fail('Unexpected dispatch'))
    with pytest.raises((LegalMathError, KeyError)): resume.run_role(21, 'qualification-first', {}, [])


@pytest.mark.parametrize('complete', [True, False])
def test_repair_restart_never_reissues_consumed_attempt(tmp_path, monkeypatch, complete):
    folder, spec = service_failure(tmp_path, monkeypatch)
    attempt = completed_attempt(folder, spec, tmp_path, complete=complete)
    monkeypatch.setattr(resume, 'check_review', lambda: {'recovery': resume.ref(tmp_path / 'recovery.json')})
    monkeypatch.setattr(resume, 'tested', lambda: {})
    monkeypatch.setattr(resume, 'historical', lambda: ({}, {'batches': {21: []}}, []))
    monkeypatch.setattr(resume, 'refresh', lambda: {})
    monkeypatch.setattr(resume, 'run_role', lambda *a, **kw: pytest.fail('Unexpected redispatch'))
    (folder / 'latest.json').unlink()  # Crash after receipt, before pointer publication.
    result = resume.repair()
    assert result['status'] == ('RECOVERY_VALIDATED' if complete else 'REPAIR_REVIEW_REQUIRED')
    assert resume.checked(resume.read(folder / 'latest.json')['receipt']) == attempt / 'receipt.json'
    assert resume.repair() == result


def test_candidate_provider_rejects_changed_recovery_request_before_reserving(tmp_path, monkeypatch):
    wire, schema, *_ = fixture()
    provider = resume.CandidateProvider(tmp_path, expected_dispatch={'request_hash': 'a' * 64, 'schema_hash': 'b' * 64})
    monkeypatch.setattr(resume.CodexProvider, 'complete', lambda *a, **k: pytest.fail('Unexpected provider call'))
    with pytest.raises(LegalMathError) as exc:
        provider.complete(wire, schema, resume.Settings())
    assert exc.value.code == 'E_INTEGRITY'
    assert not list(tmp_path.rglob('started.json'))


def test_successful_peer_is_reused_without_a_call(tmp_path, monkeypatch):
    folder, spec = service_failure(tmp_path, monkeypatch)
    peer = resume.role_directory(21, 'source-first')
    resume.save(peer / 'receipt.json', {'batch': 21, 'role': 'source-first', 'complete': True,
                                      'proposal': {'retained': 'unchanged'}})
    monkeypatch.setattr(resume, 'check_review', lambda: {})
    monkeypatch.setattr(resume, 'CandidateProvider', lambda *a, **kw: pytest.fail('Unexpected peer call'))
    assert resume.run_role(21, 'source-first', {}, [])['proposal'] == {'retained': 'unchanged'}


def test_recovery_reuses_original_tool_directory_and_cannot_rewind_selection(tmp_path, monkeypatch):
    folder, spec = service_failure(tmp_path, monkeypatch)
    resume.save(folder / 'started.json', {'recovery': None})
    attempt = completed_attempt(folder, spec, tmp_path)
    assert resume.role_tools(attempt) == folder / 'tools'
    monkeypatch.setattr(resume, 'check_review', lambda: {'recovery': resume.ref(tmp_path / 'recovery.json')})
    monkeypatch.setattr(resume, 'tested', lambda: {})
    monkeypatch.setattr(resume, 'historical', lambda: ({}, {'batches': {21: []}}, []))
    (folder / 'attempt-02').mkdir()
    pointer = (folder / 'latest.json').read_bytes()
    with pytest.raises(LegalMathError): resume.repair()
    assert (folder / 'latest.json').read_bytes() == pointer


def timeout_failure(tmp_path, monkeypatch):
    folder, spec = service_failure(tmp_path, monkeypatch)
    failure = {'error': 'E_RESOURCE_LIMIT', 'details': 'Codex call deadline'}
    receipt = resume.read(folder / 'receipt.json')
    receipt.update(stopped=failure, wall_seconds=300.7)
    resume.save(folder / 'receipt.json', receipt)
    resume.save(folder / 'model/journal.json', {'value': {
        'binding': {'inputs': {'settings': {'timeout_seconds': 300}}},
        'actions': [{'status': 'FAILED', **failure}]}})
    transport = resume.checked(spec['transport'])
    (transport.parent / 'events.jsonl').write_text(json.dumps({'type': 'turn.started'}))
    manifest = resume.read(transport)
    manifest['files']['events.jsonl']['retained_sha256'] = resume.ref(transport.parent / 'events.jsonl')['sha256']
    resume.save(transport, manifest)
    source = tmp_path / 'src/legalmath/interpretation/search/providers.py'
    source.parent.mkdir(parents=True); source.write_text('# Termination source fixture\n')
    spec.update(kind='local-deadline-no-output', timeout_seconds=450,
        previous=resume.ref(folder / 'receipt.json'), transport=resume.ref(transport),
        termination_source=resume.ref(source))
    return folder, spec


def test_explicit_timeout_review_qualifies_only_terminated_original_cap(tmp_path, monkeypatch):
    folder, spec = timeout_failure(tmp_path, monkeypatch)
    assert resume.validate_recovery(spec, {}, []) == spec
    spec['kind'] = 'returned-http-502-no-output'; spec.pop('timeout_seconds')
    with pytest.raises(LegalMathError): resume.validate_recovery(spec, {}, [])


@pytest.mark.parametrize('fault', ['cap', 'old_cap', 'partial_output', 'unknown_journal',
                                 'early_failure', 'error_type', 'termination_source'])
def test_timeout_recovery_rejects_uncertain_or_different_failures(tmp_path, monkeypatch, fault):
    folder, spec = timeout_failure(tmp_path, monkeypatch)
    if fault == 'cap': spec['timeout_seconds'] = 900
    elif fault in ('old_cap', 'unknown_journal'):
        path = folder / 'model/journal.json'; journal = resume.read(path)
        if fault == 'old_cap': journal['value']['binding']['inputs']['settings']['timeout_seconds'] = 450
        else: journal['value']['actions'][0]['status'] = 'RESERVED'
        resume.save(path, journal)
    elif fault == 'partial_output':
        path = resume.checked(spec['transport']); manifest = resume.read(path)
        (path.parent / 'events.jsonl').write_text(json.dumps({'type': 'turn.started'}) + '\n' +
            json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}}))
        manifest['files']['events.jsonl']['retained_sha256'] = resume.ref(path.parent / 'events.jsonl')['sha256']
        resume.save(path, manifest); spec['transport'] = resume.ref(path)
    elif fault in ('early_failure', 'error_type'):
        path = folder / 'receipt.json'; receipt = resume.read(path)
        if fault == 'early_failure': receipt['wall_seconds'] = 5
        else: receipt['stopped']['details'] = 'Codex output byte cap'
        resume.save(path, receipt); spec['previous'] = resume.ref(path)
    elif fault == 'termination_source': resume.checked(spec['termination_source']).write_text('# Changed\n')
    with pytest.raises(LegalMathError): resume.validate_recovery(spec, {}, [])


@pytest.mark.parametrize('limit,remaining,expected', [(300, 600, 300), (450, 600, 450), (450, 37, 37)])
def test_provider_normal_cap_recovery_cap_and_original_expiry(tmp_path, monkeypatch, limit, remaining, expected):
    from types import SimpleNamespace
    from scripts import legal_gap_program
    monkeypatch.setattr(legal_gap_program, 'ROOT', tmp_path)
    monkeypatch.setattr(resume.time, 'time', lambda: resume.DEADLINE - remaining)
    wire, schema, *_ = fixture()
    request, output_schema, _ = codec.prepare(wire, schema)
    expectation = {'request_hash': resume.digest(request), 'schema_hash': resume.digest(output_schema)}
    provider = resume.CandidateProvider(tmp_path, expected_dispatch=expectation if limit == 450 else None,
        timeout_limit=limit, allowance=SimpleNamespace(purpose='repair', batch=21, role='source-first',
                                                       verify=lambda: {'used': 39}))
    def capture(self, request, schema, settings):
        assert settings.timeout_seconds == expected
        raise RuntimeError('captured before any live dispatch')
    monkeypatch.setattr(resume.CodexProvider, 'complete', capture)
    with pytest.raises(RuntimeError, match='captured before any live dispatch'):
        provider.complete(wire, schema, resume.Settings(timeout_seconds=450))


def test_extended_cap_requires_bound_recovery(tmp_path):
    with pytest.raises(LegalMathError): resume.CandidateProvider(tmp_path, timeout_limit=450)
