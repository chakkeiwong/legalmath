"""Source context reaches actual requests and invalidates outer completed caches."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import source_context as qualified
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.assurance.workflow import CachedEvidenceProvider
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import source, settings
from .test_successor_workflow import complete_responder

ROOT = Path(__file__).resolve().parents[2]
JDK = ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1'
QUESTION = 'Selected gift control'


def preparation(root, directory, roots, limitation='Synthetic source; applicability unresolved.'):
    packet = packet_from_context(acquire_context(roots, max_depth=0), QUESTION)
    save(directory / 'packet.json', packet)
    qualification = {'profile': 'investigation-answer-source-qualification.v1',
        'source_packet_hash': digest(packet), 'limitations': [limitation],
        'evidence': [evidence_file(directory / 'packet.json', root)],
        'details': {'normative_classification': 'Inherited flag is unreviewed.'}}
    return qualified.prepare(root, roots, packet, qualification), packet


def test_qualification_precedes_compaction_cache_and_actual_inventory_dispatch(tmp_path):
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    sink = FunctionProvider(lambda _: {'seen': True})
    wrapped = qualified.ContextProvider(sink, context, tmp_path)
    cache = CachedEvidenceProvider(wrapped, tmp_path / 'cache', {'case': 'fixture'})
    provider = CompactProvider(cache, tmp_path / 'transport')
    request = {'task': 'SOURCE_INVENTORY', 'source_packet': packet, 'role': 'atomic-reader'}
    provider.complete(request, {}, Settings())
    provider.complete(request, {}, Settings())
    assert len(sink.requests) == 1
    received = sink.requests[0]
    assert received['source_qualification'] == context['qualification']
    assert received['source_context_binding'] == digest(context)
    action = cache.journal.report()['actions'][0]
    assert action['spec']['inputs']['request']['source_qualification'] == context['qualification']
    original = loads((tmp_path / 'transport/call-000/original-request.json').read_bytes())
    assert original['source_packet'] == packet and original['source_qualification'] == context['qualification']


@pytest.mark.parametrize('fault', ['packet', 'qualification', 'sources', 'piece'])
def test_wrong_context_or_packet_is_refused_before_dispatch(tmp_path, fault):
    roots = [source()]
    context, packet = preparation(tmp_path, tmp_path / 'source', roots)
    sink = FunctionProvider(lambda _: pytest.fail('Invalid input dispatched'))
    if fault == 'sources':
        roots[0]['data'] += b'changed'
        with pytest.raises(LegalMathError): qualified.validate(tmp_path, context, roots)
        return
    provider = CompactProvider(qualified.ContextProvider(sink, context, tmp_path), tmp_path / 'transport')
    request = {'task': 'SOURCE_INVENTORY', 'source_packet': deepcopy(packet)}
    if fault == 'packet': request['source_packet']['selected_slice'] = 'Other target'
    if fault == 'qualification': request['source_qualification'] = {'incorrect': True}
    if fault == 'piece':
        request['source_packet']['units'][0]['text'] += ' altered'
        request['piece'] = {'full_source_packet_hash': context['qualification']['source_packet_hash']}
    with pytest.raises(LegalMathError): provider.complete(request, {}, Settings())
    assert not sink.requests


def test_final_encoded_size_is_checked_even_for_a_nonchecking_provider(tmp_path):
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    sink = FunctionProvider(lambda _: pytest.fail('Overflow dispatched'))
    provider = CompactProvider(qualified.ContextProvider(sink, context, tmp_path), tmp_path / 'transport')
    with pytest.raises(LegalMathError) as exc:
        provider.complete({'task': 'SOURCE_INVENTORY', 'source_packet': packet}, {}, Settings(max_input_bytes=1000))
    assert exc.value.code == 'E_RESOURCE_LIMIT' and not sink.requests


def test_direct_cached_dispatch_also_binds_qualification(tmp_path):
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    sink = FunctionProvider(lambda _: {'seen': True})
    cache = CachedEvidenceProvider(qualified.ContextProvider(sink, context, tmp_path), tmp_path / 'cache', {})
    cache.complete({'task': 'SOURCE_INVENTORY', 'source_packet': packet}, {}, Settings())
    assert sink.requests[0]['source_qualification'] == context['qualification']
    assert cache.journal.report()['actions'][0]['spec']['inputs']['request']['source_context_binding'] == digest(context)


def test_cached_result_cannot_hide_changed_qualification_evidence(tmp_path):
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    sink = FunctionProvider(lambda _: {'seen': True})
    cache = CachedEvidenceProvider(qualified.ContextProvider(sink, context, tmp_path), tmp_path / 'cache', {})
    request = {'task': 'SOURCE_INVENTORY', 'source_packet': packet}
    cache.complete(request, {}, Settings())
    (tmp_path / 'source/packet.json').write_text('changed')
    with pytest.raises(LegalMathError): cache.complete(request, {}, Settings())
    assert len(sink.requests) == 1


def test_copied_context_marker_does_not_approve_a_changed_encoded_packet(tmp_path):
    from legalmath.interpretation.assurance.decomposition import compact_request
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    request = compact_request(qualified.augment({'task': 'SOURCE_INVENTORY', 'source_packet': packet}, context), profile='v2')
    request['source_packet']['units'][0]['text'] += 'wrong'
    with pytest.raises(LegalMathError): qualified.before_cache(request, context)


@pytest.mark.parametrize('fault', ['changed', 'missing'])
def test_compact_source_document_locators_remain_bound(tmp_path, fault):
    from legalmath.interpretation.assurance.decomposition import compact_request
    context, packet = preparation(tmp_path, tmp_path / 'source', [source()])
    request = compact_request(qualified.augment({'task': 'SOURCE_INVENTORY', 'source_packet': packet}, context), profile='v2')
    assert request['source_packet_document_locators']
    if fault == 'missing': del request['source_packet_document_locators']
    else:
        key = next(iter(request['source_packet_document_locators']))
        request['source_packet_document_locators'][key] = ['https://example.org/different-origin']
    with pytest.raises(LegalMathError): qualified.before_cache(request, context)


def test_inventory_pieces_keep_full_qualification_and_reject_changed_piece(tmp_path):
    from legalmath.interpretation.assurance.decomposition import partition, piece_request, compact_request
    roots = [source()]
    roots[0]['data'] += b'\nAdditional context.'
    context, packet = preparation(tmp_path, tmp_path / 'source', roots)
    pieces = partition(packet, 20000, 1)
    assert len(pieces) == 2
    req = piece_request(pieces[0], 'atomic-reader', 0, 2, digest(packet))
    wire = compact_request(qualified.augment(req, context), profile='v2')
    assert qualified.before_cache(wire, context)['source_qualification'] == context['qualification']
    wire['source_packet']['units'][0]['normative'] = False
    with pytest.raises(LegalMathError): qualified.before_cache(wire, context)


def test_actual_inventory_repair_receives_qualification(tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from .test_integration import responder
    roots = [source()]; context, _ = preparation(tmp_path, tmp_path / 'source', roots)
    normal = responder()
    def respond(request):
        if request['task'] == 'REPAIR_SOURCE_INVENTORY': return normal({**request, 'task': 'SOURCE_INVENTORY'})
        value = normal(request)
        if request['task'] == 'SOURCE_INVENTORY': value['claims'][0]['exceptions'] = []
        return value
    provider = FunctionProvider(respond)
    engine = Assurance(tmp_path / 'product', provider, JDK, AT, settings(1),
        source_context=context, source_context_root=tmp_path)
    result = engine.drive(roots, QUESTION)
    requests = [r for r in provider.requests if r['task'] == 'REPAIR_SOURCE_INVENTORY']
    assert len(requests) == 2, result
    assert all(r['source_qualification'] == context['qualification'] for r in provider.requests)


def test_qualified_challenge_and_reference_paths_use_same_original_method():
    from .test_challenge_integration import responder
    from legalmath.interpretation.assurance import source_references
    with TemporaryDirectory(prefix='qualified-challenge-test-', dir=ROOT / 'artifacts') as td:
        directory = Path(td); roots = [source()]
        context, _ = preparation(ROOT, directory / 'source', roots)
        provider = FunctionProvider(responder)
        runner = CompleteInvestigation(ROOT, directory / 'product', provider, JDK, AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
            reference_protocol=source_references.PROTOCOL, input_profile='readable-tables.v1',
            challenge_options={'batch_size': 4, 'rounds': 1, 'maximum_actions': 12})
        result = runner.run(roots, QUESTION, source_context=context)
        assert result['execution_complete']
        assert any(r['task'] == 'INTERPRETATION_CHALLENGES' for r in provider.requests)
        assert all(r['source_qualification'] == context['qualification'] for r in provider.requests)
        assert verify(ROOT, result)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        next_provider = FunctionProvider(responder)
        continuation = CompleteInvestigation(ROOT, directory / 'continuation', next_provider, JDK, AT,
            settings=settings(), reference_protocol=source_references.PROTOCOL,
            input_profile='readable-tables.v1', challenge_options={'batch_size': 4, 'rounds': 1,
                'maximum_actions': 12, 'input_profile': 'readable-challenges.v1'})
        ref = runner.directory / 'revisions' / result['revision'] / 'dossier.json'
        continued = continuation.continue_challenges(ref)
        assert next_provider.requests and all(r['source_qualification'] == context['qualification']
                                              for r in next_provider.requests)
        assert verify(ROOT, continued)['status'] == 'FILE_BOUND_CHALLENGE_CONTINUATION_VERIFIED'


def test_selection_only_changes_create_outer_revisions_and_keep_raw_source_identity():
    with TemporaryDirectory(prefix='source-selection-test-', dir=ROOT / 'artifacts') as td:
        directory = Path(td)
        provider = FunctionProvider(complete_responder)
        runner = CompleteInvestigation(ROOT, directory / 'product', provider, JDK, AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1)
        original = source()
        old = runner.run([original], QUESTION)
        count = len(provider.requests)
        text = original['data'].decode()
        changed = deepcopy(original)
        changed['selection'] = {'raw_sha256': raw_digest(original['data']),
            'text_sha256': raw_digest(text.encode()), 'ranges': [[0, len(text)]],
            'regions': [{'anchor': {'start': 0, 'end': len(text), 'quote': text}}]}
        new = runner.run([changed], QUESTION)
        assert new['revision'] != old['revision']
        assert new['binding']['sources'] == old['binding']['sources']
        assert len(provider.requests) > count
        assert verify(ROOT, old)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        assert verify(ROOT, new)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        count = len(provider.requests)
        assert runner.run([changed], QUESTION) == new and len(provider.requests) == count


def test_challenge_checks_qualification_evidence_between_direct_dispatches():
    from .test_challenge_integration import responder
    with TemporaryDirectory(prefix='qualified-challenge-evidence-test-', dir=ROOT / 'artifacts') as td:
        directory = Path(td); roots = [source()]
        context, _ = preparation(ROOT, directory / 'source', roots)
        seen = []
        def respond(request):
            value = responder(request)
            if request['task'] == 'INTERPRETATION_CHALLENGES':
                seen.append(request)
                (directory / 'source/packet.json').write_text('Changed qualification evidence')
            return value
        provider = FunctionProvider(respond)
        runner = CompleteInvestigation(ROOT, directory / 'product', provider, JDK, AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
            reference_protocol='legalmath.source-spans.v1', input_profile='readable-tables.v1',
            challenge_options={'batch_size': 4, 'rounds': 1, 'maximum_actions': 12})
        with pytest.raises(LegalMathError): runner.run(roots, QUESTION, source_context=context)
        assert len(seen) == 1


def test_qualification_only_change_invalidates_outer_and_core_completed_results():
    with TemporaryDirectory(prefix='source-qualification-test-', dir=ROOT / 'artifacts') as td:
        directory = Path(td)
        roots = [source()]
        context, _ = preparation(ROOT, directory / 'source', roots)
        provider = FunctionProvider(complete_responder)
        runner = CompleteInvestigation(ROOT, directory / 'product', provider, JDK, AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1)
        old = runner.run(roots, QUESTION, source_context=context)
        assert old['execution_complete'], old['core']['interpretation']['report']
        tasks = {r['task'] for r in provider.requests}
        assert {'SOURCE_INVENTORY', 'GENERATE', 'DEFINE_EXACT_QUESTIONS', 'SCOPED_SOURCE_FIDELITY'} <= tasks
        assert {r['role'] for r in provider.requests if r['task'] == 'SOURCE_INVENTORY'} == {'atomic-reader', 'qualification-reader'}
        assert all(r['source_qualification'] == context['qualification'] for r in provider.requests)
        count = len(provider.requests)
        assert runner.run(roots, QUESTION, source_context=context) == old
        assert len(provider.requests) == count
        changed = deepcopy(context)
        changed['qualification']['limitations'].append('New retained edition uncertainty.')
        new = runner.run(roots, QUESTION, source_context=changed)
        assert new['revision'] != old['revision'] and len(provider.requests) > count
        assert new['binding']['sources'] == old['binding']['sources']
        assert all(r['source_qualification'] == changed['qualification'] for r in provider.requests[count:])
        assert verify(ROOT, old)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        assert new['core']['interpretation']['directory'] != old['core']['interpretation']['directory']
