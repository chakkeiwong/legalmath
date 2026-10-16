#!/usr/bin/env python3
"""One approved offline qualification and separate retained-evidence capacity screen."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import dossier_answer as consumer
from legalmath.interpretation.assurance import source_context as qualified
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from scripts.legal_mission_control import admit, read, BASE, CONTEXT_TASK

OUT = ROOT / 'artifacts/legal-mission-control/2026-10-10/context-boundary'
PLAN = ROOT / 'docs/plans/legal-mission-context-boundary-repair.md'


def admission():
    return admit(read(ROOT / BASE / 'mission.json'), read(ROOT / BASE / 'tools.json'), CONTEXT_TASK, ROOT)


def finding(request, ids):
    return {'record_ids': ids[:1], 'question_ids': list(request['question_hashes'])[:1],
        'conclusion': 'No legal conclusion evaluated.', 'inference': 'Synthetic receipt only.',
        'support': [], 'contrary': [], 'assumptions': ['Scripted provider.'],
        'unresolved': ['Every legal inference.'], 'cross_record_dependencies': []}


def accounts(request):
    return [{'review_binding': k, 'review_hash': v, 'explanation': 'Synthetic receipt only.'}
            for k, v in request['review_hashes'].items()]


def receipt(request):
    """Deliberately legally empty responses, never a correct answer template."""
    if request['task'] == 'REVIEW_DOSSIER_EVIDENCE':
        ids = list(request['assigned_records'])
        return {'review_binding': request['review_binding'],
            'accounts': [{'record_ids': ids, 'disposition': 'UNRESOLVED', 'explanation': 'Synthetic receipt.'}],
            'findings': [finding(request, ids)], 'legal_correctness_established': False}
    if request['task'] == 'REVIEW_DOSSIER_INTERACTIONS':
        return {'interaction_binding': request['interaction_binding'], 'review_account': accounts(request),
            'findings': [finding(request, request['registry_ids'])],
            'unresolved_interactions': ['No semantic interaction review performed.'],
            'legal_correctness_established': False}
    unit = request['source_packet']['units'][0]
    qids = list(request['question_hashes'])
    return {'binding_hash': request['binding_hash'], 'stage_binding': request['stage_binding'],
        'interaction_hash': request['interaction_hash'], 'review_account': accounts(request),
        'answers': [{'question_id': q, 'question_hash': h, 'answer': 'No legal answer evaluated.',
            'claims': [{'claim_id': 'empty.' + str(i), 'conclusion': 'No conclusion.',
                'inference': 'Synthetic fixture only.', 'support': [{'unit_id': unit['unit_id'], 'quote': unit['text']}],
                'contrary': [], 'assumptions': ['Scripted provider.'], 'unresolved': ['Legal support unassessed.']}],
            'conditional_alternatives': [], 'qualifications': request['source_qualification']['limitations'],
            'unresolved_dependencies': ['All legal questions remain open.']}
            for i, (q, h) in enumerate(request['question_hashes'].items())],
        'reading_account': [{'candidate_id': cid, 'reading_hash': digest(r), 'disposition': 'UNRESOLVED',
            'question_ids': qids, 'explanation': 'Synthetic receipt, not substantive consideration.'}
            for cid, r in request['candidates'].items()],
        'tool_account': [{'key': c['key'], 'result_hash': c['result_hash'], 'disposition': 'UNRESOLVED',
            'question_ids': qids, 'explanation': 'Receipt only.', 'limitation': 'Legal warrant unassessed.'}
            for c in request['tool_check_index']],
        'legal_correctness_established': False, 'release_eligible': False}


def qualify(work):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source, settings
    from tests.search.test_formal import AT
    from scripts.legal_integration_tools import ProductToolBackend
    roots = [source()]; question = 'Selected gift control'
    packet = packet_from_context(acquire_context(roots, max_depth=0), question)
    save(work / 'prepared-packet.json', packet)
    qualification = {'profile': 'investigation-answer-source-qualification.v1',
        'source_packet_hash': digest(packet),
        'limitations': ['Synthetic source; legal accuracy and actual full-target feasibility unassessed.',
                       'Edition/applicability unresolved; inherited normative flag unreviewed.'],
        'evidence': [evidence_file(work / 'prepared-packet.json', ROOT)],
        'details': {'source_status': 'Synthetic local text fixture.'}}
    save(work / 'qualification.json', qualification)
    context = qualified.prepare(ROOT, roots, packet, qualification)
    save(work / 'qualified-source-context.json', context)
    def respond(request):
        admission()
        return complete_responder(request)
    provider = FunctionProvider(respond)
    consumer.require(provider.live is False, 'Offline qualification refuses live provider', 'E_AUTHORITY')
    runner = CompleteInvestigation(ROOT, work / 'product', provider,
        ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
        settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
        optional_tool_backend=ProductToolBackend())
    dossier = runner.run(roots, question, source_context=context)
    ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', ROOT)
    arguments = {'investigation_directory': runner.directory, 'expected_revision': dossier['revision'],
        'questions': [{'question_id': 'gift', 'text': question}],
        'qualification_ref': evidence_file(work / 'qualification.json', ROOT)}
    result = consumer.propose(ROOT, ref, FunctionProvider(receipt), work / 'consumer',
        **arguments, dispatch_guard=admission)
    save(work / 'provider-requests.json', provider.requests)
    delivered = all(r.get('source_qualification') == qualification
                    and r.get('source_context_binding') == digest(context) for r in provider.requests)
    consumer.require(delivered, 'Actual product requests lost qualification', 'E_INTEGRITY')
    consumer.require({r['role'] for r in provider.requests if r['task'] == 'SOURCE_INVENTORY'}
                     == {'atomic-reader', 'qualification-reader'}, 'Initial reader roles missing')
    index = read(work / 'consumer/partition.json')['registry']
    original = read(work / 'consumer/original-request.json')
    return {'status': result['status'], 'consumer': result, 'dossier': ref,
        'investigation_execution_complete': dossier['execution_complete'],
        'early_and_scoped_qualification_delivered': delivered,
        'actual_request_tasks': sorted({r['task'] for r in provider.requests}),
        'raw_reconstruction_equal': consumer.restore(index) == original,
        'registry_records': len(index['records']),
        'tool_kinds': sorted({c['kind'] for c in dossier['optional_tools']['checks']}),
        'tool_names': sorted({c.get('tool', '') for c in dossier['optional_tools']['checks']}),
        'new_live_calls': 0, 'legal_quality_evaluated': False,
        'full_target_feasibility_established': False,
        'limit': 'Fresh actual product and installed backend, synthetic fixture and legally empty responses.'}


def prepared_source_screen(work):
    """Actual offline projection and inventory transport, never a legal dossier."""
    from tests.search.support import FunctionProvider
    from legalmath.interpretation.assurance.semantics import inventory_request
    from legalmath.interpretation.assurance.transport import CompactProvider
    from legalmath.interpretation.search.models import Settings
    source_dir = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
    expected = {'context.json': '39fb905aa542de30abcfbf82ee05a996d78181b2991b4d9bc431c321d1e8af6c',
                'packet.json': '7f7c3b113825f53c5b87d3a3cc9bebc13ab033baea5d9298998cb1df3ae82a62',
                'qualification.json': '94c0df25a3222160dbf023594dab0d8601fe3a78480062a66e23754c0870a906'}
    for name, sha in expected.items():
        consumer.require(raw_digest((source_dir / name).read_bytes()) == sha,
                         'Prepared source changed: ' + name, 'E_INTEGRITY')
    retained = read(source_dir / 'context.json')
    packet = read(source_dir / 'packet.json')
    qualification = read(source_dir / 'qualification.json')
    definitions = {d['url']: d for d in qualification['details']['documents']}
    roots = []
    for document in retained['documents']:
        definition = definitions[document['url']]
        raw = read_evidence(definition['derived_text'], ROOT, json_value=False)
        read_evidence(definition['original'], ROOT, json_value=False)
        consumer.require(raw.decode('utf-8') == document['text'], 'Derived text differs', 'E_INTEGRITY')
        roots.append({k: document[k] for k in ('url', 'media_type', 'selection',
                                             'local_reconstruction', 'original_evidence')} | {'data': raw})
    def no_network(_):
        raise LegalMathError('E_AUTHORITY', details='Prepared source screen forbids network acquisition')
    projected = acquire_context(roots, fetcher=no_network, max_documents=4, max_depth=0)
    view = {**projected, 'documents': [{k: v for k, v in d.items() if k != 'data'}
                                     for d in projected['documents']]}
    consumer.require(view == retained, 'Offline acquired context differs from retained preparation', 'E_INTEGRITY')
    consumer.require(packet_from_context(projected, packet['selected_slice']) == packet,
                     'Offline source packet projection differs', 'E_INTEGRITY')
    context = qualified.prepare(ROOT, roots, packet, qualification)
    save(work / 'prepared-qualified-source-context.json', context)
    sink = FunctionProvider(lambda _: {'synthetic_delivery_receipt': True})
    consumer.require(sink.live is False, 'Prepared source sink must be offline', 'E_AUTHORITY')
    transport = CompactProvider(qualified.ContextProvider(sink, context, ROOT), work / 'prepared-inventory')
    settings = Settings(timeout_seconds=30, max_input_bytes=200000, max_output_bytes=1000)
    for role in ('atomic-reader', 'qualification-reader'):
        admission()
        transport.complete(inventory_request(packet, role), {}, settings)
    consumer.require(len(sink.requests) == 2 and all(
        r['source_qualification'] == qualification and r['source_context_binding'] == digest(context)
        for r in sink.requests), 'Prepared inventory lost semantic qualification', 'E_INTEGRITY')
    save(work / 'prepared-inventory-requests.json', sink.requests)
    return {'status': 'SOURCE_PROJECTION_AND_DELIVERY_PASSED', 'documents': len(roots),
            'packet_units': len(packet['units']), 'retained_context_equal': True,
            'retained_packet_equal': True, 'both_inventory_roles_qualified': True,
            'inventory_wire_bytes': [len(canonical(r)) for r in sink.requests],
            'source_files': [evidence_file(source_dir / name, ROOT) for name in expected],
            'new_live_calls': 0, 'full_target_dossier_capacity_established': False,
            'limit': 'Derived-text source projection and transport only; no inventories or legal answers evaluated.'}


def capacity(work):
    """Separate source-only and historical scoped-stream screens, no mixed dossier."""
    consumer.require(read(OUT / 'qualify/result.json')['status'] == 'STRUCTURALLY_VALID_PROPOSAL',
                     'Fresh qualification failed')
    path = ROOT / 'artifacts/legal-candidate-response-product/2026-10-09/replay/scoped/result.json'
    inputs_path = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/inputs.json'
    consumer.require(raw_digest(path.read_bytes()) ==
        'e42087a31f20d0d11024b775882b0caedcf17c3ed370dbe2ed4bcfed0028a609', 'Retained stream changed')
    consumer.require(raw_digest(inputs_path.read_bytes()) ==
        '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf', 'Retained packet/readings changed')
    inputs = read(inputs_path)
    questions = [{'question_id': 'retained-scope', 'text': inputs['packet']['selected_slice']}]
    original = {'task': 'STATIC_RETAINED_STREAM_CAPACITY', 'binding': {'profile': 'static-only'},
        'binding_hash': digest({'profile': 'static-only'}), 'instructions': 'Static archival stream, not a legal dossier.',
        'source_packet': inputs['packet'], 'original_questions': questions,
        'question_hashes': {q['question_id']: digest(q['text']) for q in questions},
        'source_qualification': {'profile': 'investigation-answer-source-qualification.v1',
            'source_packet_hash': digest(inputs['packet']),
            'limitations': ['Historical 12-unit excerpt stream; not the prepared full target or a current method dossier.',
                           'Static capacity only; source applicability and legal contribution unassessed.'],
            'evidence': [evidence_file(inputs_path, ROOT), evidence_file(path, ROOT)], 'details': {}},
        'candidates': inputs['candidates'], 'source_claims': inputs['claims'],
        'investigation': {'scoped': read(path)}, 'tool_applicability': {}}
    save(work / 'retained-stream-request.json', original)
    source_dir = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
    source_wire = read(source_dir / 'source-capacity-wire.json')
    source_bytes = len(canonical(source_wire))
    consumer.require(source_bytes == 93741, 'Preserved source-only wire changed', 'E_INTEGRITY')
    source_screen = prepared_source_screen(work)
    save(work / 'prepared-source-screen.json', source_screen)
    base = {'source_only_bytes': source_bytes,
        'prepared_source_screen': source_screen,
        'source_only': evidence_file(source_dir / 'source-capacity-wire.json', ROOT),
        'retained_stream': evidence_file(path, ROOT), 'retained_inputs': evidence_file(inputs_path, ROOT),
        'new_live_calls': 0, 'legal_quality_evaluated': False, 'full_target_feasibility_established': False,
        'limit': 'Separate static screens; short scripted reductions do not qualify real summaries or a genuine full-target dossier.'}
    try:
        prepared = consumer.partition(original)
        save(work / 'partition.json', prepared)
        reviews = [receipt(consumer.review_request(prepared['registry'], b)) for b in prepared['batches']]
        consumer.require(all(len(canonical(r)) <= 4000 for r in reviews), 'Synthetic review output ceiling', 'E_RESOURCE_LIMIT')
        request = consumer.interaction_request(original, prepared, reviews)
        interaction_size = consumer.wire_size(request)
        save(work / 'synthetic-interaction-request.json', request)
        consumer.require(interaction_size <= 200000, {'stage': 'INTERACTION', 'bytes': interaction_size}, 'E_RESOURCE_LIMIT')
        request = consumer.synthesis_request(original, prepared, reviews, receipt(request))
        size = consumer.wire_size(request)
        save(work / 'synthetic-synthesis-request.json', request)
        consumer.require(size <= 200000, {'stage': 'SYNTHESIS', 'bytes': size}, 'E_RESOURCE_LIMIT')
        return {**base, 'status': 'DECLARED_STATIC_SCREEN_PASSED', 'groups': len(reviews),
            'maximum_review_wire_bytes': max(prepared['wire_bytes']), 'interaction_bytes': interaction_size,
            'synthetic_synthesis_bytes': size, 'registry_records': len(prepared['registry']['records']),
            'raw_reconstruction_equal': consumer.restore(prepared['registry']) == original}
    except LegalMathError as exc:
        return {**base, 'status': 'CAPACITY_BLOCKED' if exc.code == 'E_RESOURCE_LIMIT' else 'REJECTED',
                'error': exc.code, 'details': exc.details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('qualify', 'capacity'))
    args = parser.parse_args()
    admission()
    work = OUT / args.action
    work.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = None
    try:
        result = {'qualify': qualify, 'capacity': capacity}[args.action](work)
    except Exception as exc:
        result = {'status': 'FAILED', 'error': type(exc).__name__, 'details': str(exc), 'new_live_calls': 0}
    finally:
        save(work / 'result.json', result or {'status': 'INTERRUPTED'})
        save(work / 'run-manifest.json', {
            'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'command': '.venv/bin/python scripts/legal_mission_context_boundary.py ' + args.action,
            'environment': str(ROOT / '.venv/bin/python'),
            'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally set before imports',
            'seeds': 'N/A: deterministic synthetic responses and retained-file screens',
            'wall_milliseconds': int((time.monotonic() - started) * 1000),
            'finished_utc': datetime.now(timezone.utc).isoformat(), 'plan': evidence_file(PLAN, ROOT),
            'result': evidence_file(work / 'result.json', ROOT),
            'implementation': [evidence_file(Path(__file__), ROOT), evidence_file(Path(consumer.__file__), ROOT),
                               evidence_file(Path(qualified.__file__), ROOT)],
            'data_version': result.get('dossier', result.get('retained_stream', 'N/A: failed before input acceptance')),
            'new_live_calls': 0})
    print(json.dumps(result, indent=2))
    return 0 if result['status'] in ('STRUCTURALLY_VALID_PROPOSAL', 'DECLARED_STATIC_SCREEN_PASSED') else 1


if __name__ == '__main__': raise SystemExit(main())
