from copy import deepcopy
from contextlib import contextmanager
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal, CachedEvidenceProvider
from legalmath.interpretation.assurance.regions import reconcile_page, compare_regions, choose_region_action
from legalmath.interpretation.assurance.abstractions import collect, validate_batch
from legalmath.interpretation.assurance.engine import Assurance, coalesce_dependency_records
from tests.search.support import FunctionProvider
from .support import packet, reading
from .test_integration import source, responder, settings
from tests.search.test_formal import AT
from legalmath.interpretation.search.models import Settings


@contextmanager
def raises_code(code):
    with pytest.raises(LegalMathError) as caught:
        yield
    assert caught.value.code == code


def test_completed_evidence_reused_changed_dependency_dispatches_and_preserves_parent(tmp_path):
    journal = EvidenceJournal(tmp_path, {'case': 'a'})
    calls = []
    def execute(work):
        calls.append(str(work)); (work/'binary.jar').write_bytes(b'fixture bytes')
        return {'answer': 'unknown', 'bbox': [1.2, 3.4, 5.6, 7.8]}
    value, first = journal.execute('source', {'edition': 'one'}, execute)
    assert not first['reused']
    assert journal.execute('source', {'edition': 'one'}, execute)[1]['reused']
    _, new = journal.execute('source', {'edition': 'two'}, execute)
    assert len(calls) == 2 and new['key'] != first['key']
    assert journal.report()['actions'][1]['supersedes'] == [0]
    (tmp_path/'action-0000/binary.jar').write_bytes(b'changed')
    with raises_code('E_INTEGRITY'): journal.report()


def test_crash_consumes_budget_restart_retries_with_limit(tmp_path):
    journal = EvidenceJournal(tmp_path, {}, maximum_per_issue=2)
    def crashed(work): raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt): journal.execute('source', {}, crashed)
    resumed = EvidenceJournal(tmp_path, {}, maximum_per_issue=2)
    assert resumed.report()['consumed_actions'] == 1
    resumed.execute('source', {}, lambda p: {'new_evidence': True})
    with raises_code('E_RESOURCE_LIMIT'):
        resumed.execute('source', {'changed': True}, lambda p: {})
    assert resumed.report()['consumed_actions'] == 2


def test_global_budget_and_corrupt_state_cannot_reset(tmp_path):
    journal = EvidenceJournal(tmp_path, {}, maximum_actions=1)
    journal.execute('a', {}, lambda p: {})
    with raises_code('E_RESOURCE_LIMIT'):
        journal.execute('b', {}, lambda p: {})
    with raises_code('E_INTEGRITY'):
        EvidenceJournal(tmp_path, {}, maximum_actions=2).report()
    envelope = json.loads(journal.path.read_text()); envelope['value']['actions'] = []
    journal.path.write_text(json.dumps(envelope))
    with raises_code('E_INTEGRITY'): journal.report()


def test_incomplete_action_retry_preserves_results_and_issue_limit(tmp_path):
    journal = EvidenceJournal(tmp_path, {}, maximum_per_issue=2)
    first, receipt = journal.execute('interpretation', {}, lambda p: {'complete': False})
    original = (tmp_path/'action-0000/result.json').read_bytes()
    retry = lambda v: not v['complete']
    second, receipt = journal.execute('interpretation', {}, lambda p: {'complete': False}, retry_if=retry)
    assert receipt['sequence'] == 1 and not receipt['reused']
    assert (tmp_path/'action-0000/result.json').read_bytes() == original
    with raises_code('E_RESOURCE_LIMIT'):
        journal.execute('interpretation', {}, lambda p: {'complete': True}, retry_if=retry)


@pytest.mark.parametrize('code,details,retry', [
    ('E_DEPENDENCY', 'stream disconnected before completion', True),
    ('E_RESOURCE_LIMIT', 'Codex call deadline', True),
    ('E_DEPENDENCY', 'credential rejected', False),
    ('E_RESOURCE_LIMIT', 'Allowance exhausted', False),
    ('E_INTEGRITY', 'Changed source hash', False),
])
def test_transport_retries_only_transient_errors_and_counts_all_attempts(tmp_path, code, details, retry):
    calls = []
    def answer(request):
        calls.append(request)
        if len(calls) == 1: raise LegalMathError(code, details=details)
        return {'answer': 'retained'}
    cache = CachedEvidenceProvider(FunctionProvider(answer), tmp_path, {'at': AT})
    if retry:
        response = cache.complete({'task': 'test'}, {}, Settings())
        assert response.value['answer'] == 'retained'
        assert [a['status'] for a in cache.journal.report()['actions']] == ['FAILED', 'EXECUTED']
        assert cache.complete({'task': 'test'}, {}, Settings()).provenance['evidence_reused']
        assert len(calls) == 2
    else:
        with raises_code(code): cache.complete({'task': 'test'}, {}, Settings())
        assert len(calls) == cache.journal.report()['consumed_actions'] == 1


def test_repeated_service_failure_cannot_exceed_persistent_request_limit(tmp_path):
    def failed(request): raise LegalMathError('E_DEPENDENCY', details='stream disconnected')
    provider = FunctionProvider(failed)
    cache = CachedEvidenceProvider(provider, tmp_path, {'at': AT})
    with raises_code('E_DEPENDENCY'): cache.complete({'task': 'test'}, {}, Settings())
    with raises_code('E_RESOURCE_LIMIT'): cache.complete({'task': 'test'}, {}, Settings())
    assert len(provider.requests) == cache.journal.report()['consumed_actions'] == 3


def test_orchestration_change_preserves_cache_but_cannot_reset_resource_binding(tmp_path):
    provider = FunctionProvider(lambda request: {'answer': 'same request'})
    first = CachedEvidenceProvider(provider, tmp_path, {'at': AT, 'settings': {'batch': 16}}, maximum_actions=7)
    first.complete({'task': 'test'}, {}, Settings())
    original = first.journal.path.read_bytes()
    resumed = CachedEvidenceProvider(provider, tmp_path, {'at': AT, 'settings': {'batch': 8}}, maximum_actions=7)
    assert resumed.journal.path.read_bytes() == original
    assert resumed.complete({'task': 'test'}, {}, Settings(timeout_seconds=300)).provenance['evidence_reused']
    assert len(provider.requests) == 1
    with raises_code('E_INTEGRITY'):
        CachedEvidenceProvider(provider, tmp_path, {'at': AT}, maximum_actions=8)
    with raises_code('E_INTEGRITY'):
        CachedEvidenceProvider(provider, tmp_path, {'at': 'changed'}, maximum_actions=7)


@pytest.mark.parametrize('other', [
    'Offer gifts.', 'Do not offer gifts below 60 HKD.', 'Do not offer gifts below 6 USD.',
    'Do not offer gifts above 6 HKD.', 'Do not offer gifts below 6 HKD',
])
def test_meaning_changing_region_edits_never_resolve_by_normalisation(other):
    result = reconcile_page('a'*64, 1, {'text': 'Do not offer gifts below 6 HKD.', 'pixels': other}, raster_sha256='b'*64)
    assert result['status'] == 'UNCERTAINTY_RETAINED' and result['issues']
    issue = result['issues'][0]; first = choose_region_action(issue, [])
    assert choose_region_action(issue, [first]) != first


def test_wrapping_resolves_but_common_text_omission_and_layout_do_not():
    assert reconcile_page('a'*64, 1, {'a': 'not\n permitted', 'b': 'not permitted'},
                          raster_sha256='b'*64)['status'] == 'OBSERVED_SOURCE_AGREEMENT'
    report = reconcile_page('a'*64, 1, {'text1': 'Gifts are prohibited.', 'text2': 'Gifts are prohibited.',
                                      'pixels': 'Gifts are prohibited. Except fee discounts.'}, raster_sha256='b'*64)
    assert len(report['issues']) == 1
    assert reconcile_page('a'*64, 1, {'a': 'text', 'b': 'text'})['status'] == 'UNCERTAINTY_RETAINED'


def abstraction(r=None, component='offer'):
    return {'schema_id': 'schema.'+component, 'actors': ['distributor'], 'objects': [component],
            'relationships': [], 'unit_of_assessment': component, 'temporal_basis': 'at assessment',
            'classification_assumptions': [], 'missing_information': [], 'reading': r or reading()}


@pytest.mark.parametrize('field,alternate', [
    ('unit_of_assessment', 'benefit component'), ('actors', ['issuer', 'distributor']),
    ('temporal_basis', 'transaction date'),
])
def test_rival_units_remain_distinct_even_with_identical_formulas(field, alternate):
    responses = {'one': {'proposals': [abstraction()], 'unresolved': []},
                 'two': {'proposals': [abstraction(component='component')], 'unresolved': []}}
    responses['two']['proposals'][0] = deepcopy(responses['one']['proposals'][0])
    responses['two']['proposals'][0][field] = alternate
    result = collect(responses, packet())
    assert len(result['models']) == 2 and result['pairs'][0]['status'] == 'INCOMPARABLE_ABSTRACTIONS'
    carried = deepcopy(responses['one'])
    carried['proposals'][0]['missing_information'] = ['Is the voucher a gift?']
    checked = validate_batch(carried, packet())
    assert 'Is the voucher a gift?' in checked['proposals'][0]['reading']['questions']


def test_abstraction_validator_carries_explicit_uncertainty_into_reading():
    proposal = abstraction()
    proposal['classification_assumptions'] = ['The assessed object is a component.']
    proposal['missing_information'] = ['Which actor supplied the benefit?']
    proposal['reading']['assumptions'] = []
    proposal['reading']['questions'] = []
    checked = validate_batch({'proposals': [proposal], 'unresolved': []}, packet())
    assert 'The assessed object is a component.' in checked['proposals'][0]['reading']['assumptions']
    assert 'Which actor supplied the benefit?' in checked['proposals'][0]['reading']['questions']


def test_carried_uncertainty_cannot_bypass_reading_limits():
    proposal = abstraction()
    proposal['reading']['questions'] = ['Question '+str(i) for i in range(20)]
    proposal['missing_information'] = ['Additional question']
    with raises_code('E_SCHEMA'):
        validate_batch({'proposals': [proposal], 'unresolved': []}, packet())


def test_identical_dependencies_coalesce_but_distinct_bindings_are_rejected():
    source = packet()
    source['dependencies'] = [{'dependency_id': 'same', 'source_hash': None}] * 2
    normalized, evidence = coalesce_dependency_records(source)
    assert len(source['dependencies']) == 2 and len(normalized['dependencies']) == 1
    assert normalized['units'] == source['units'] and evidence['duplicate_records_coalesced'] == 1
    source['dependencies'][1] = {'dependency_id': 'same', 'source_hash': 'a'*64}
    with raises_code('E_INTEGRITY'): coalesce_dependency_records(source)


def test_real_str_duplicate_reference_packet_can_enter_search(root, tmp_path):
    from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
    from legalmath.storage import Database
    from legalmath.interpretation.service import Interpretations
    from legalmath.interpretation.search.engine import create_search
    from legalmath.sources.intake import import_source
    from legalmath.canonical import digest
    doc = {'url': 'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=26EC2',
           'media_type': 'application/json',
           'data': (root/'examples/integrated-assurance/sources/26ec2.json').read_bytes()}
    context = acquire_context([doc], max_depth=0)
    original = packet_from_context(context, 'STR footnote scope')
    normalized, evidence = coalesce_dependency_records(original)
    assert evidence['duplicate_records_coalesced'] == 1
    db = Database(tmp_path/'work'); service = Interpretations(db)
    service.lc.register({'author': {'token': 'local-test-author', 'roles': ['author']}})
    with db.transaction() as con:
        for d in context['documents']:
            import_source(db, con, 'd'+digest(d['url'])[:12], d['data'], d['media_type'], d['url'], AT,
                          retained_text=d['text'], extractor=d['primary_method'],
                          authority='RETAINED_PUBLIC_SOURCE', preserve_retained_text=True)
    run = create_search(service, 'author', 'create', normalized, Settings())
    assert run['run_id']


def test_missing_schema_challenge_enters_actual_search_and_java(root, tmp_path):
    base = responder()
    def respond(request):
        if request['task'] == 'ABSTRACTION_PROPOSALS':
            p = request['source_packet']; r = reading(); uid = p['units'][0]['unit_id']
            r['citations'] = [{'unit_id': uid, 'quote': p['units'][0]['text']}]
            for fact in r['formalization']['facts']: fact['source_unit_ids'] = [uid]
            challenger = request['role'] == 'missing-schema-challenger'
            if challenger:
                assert len(request['prior_models']['origins']) >= 1
                r['assumptions'] = ['The benefit component is assessed separately from the combined offer.']
            return {'proposals': [abstraction(r, 'component' if challenger else 'offer')], 'unresolved': []}
        return base(request)
    config = settings().model_copy(update={'investigate_abstractions': True, 'total_model_calls': 24})
    provider = FunctionProvider(respond)
    result = Assurance(tmp_path/'case', provider, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
                       config).drive([source()], 'Selected gift control')
    assert result['execution_complete'], result
    assert len(result['abstractions']['models']) == 2
    assert any(f['kind'] == 'INCOMPARABLE_ABSTRACTIONS' for f in result['findings'])
    state = json.loads((tmp_path/'case/search-state.json').read_text())
    assert any('benefit component' in ' '.join(n['reading']['assumptions']) for n in state['nodes'])
    assert state['java_checks'] and not result['release_eligible']
