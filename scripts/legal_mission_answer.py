#!/usr/bin/env python3
"""Closed offline preparation/qualification for the admitted answer consumer.

No provider construction, source download, tool installation or live dispatch.
The scripted proposal below checks a boundary; it is never a legal answer trial.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import investigation_answer as answer
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.sources import acquire_context, audit_packet, packet_from_context
from legalmath.interpretation.search.providers import Completion

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation'
PLAN = ROOT / 'docs/plans/legal-mission-answer-preparation.md'
MISSION = ROOT / 'docs/implementation/legal-mission-control/mission.json'
CORPUS = ROOT / 'artifacts/legal-interpretation-program/successor-s4/attempt-1/development-inputs.json'
CORPUS_SHA = '01e973c1b1eb59f69bf44fed02c91767ea1452a819e514d328c15af94f2cbd4a'
AUTHORITY = ROOT / 'artifacts/assurance-gap-continuation/2026-10-01/authority-context.json'
CONTEXT = ROOT / 'artifacts/authority-source-revision/2026-09-29/attempt-01/context.json'
FIXTURE = ROOT / 'artifacts/legal-integration-repair/2026-10-08/R2/final/dossier.json'
FIXTURE_DIRECTORY = FIXTURE.parent / 'controlled-product'
END = datetime(2026, 10, 9, 9, 33, tzinfo=timezone.utc)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value))


def require(condition, message):
    if not condition:
        raise LegalMathError('E_INTEGRITY', details=message)


def admitted():
    if datetime.now(timezone.utc) >= END:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Reviewed local window expired; no reset')
    from scripts.legal_mission_control import admit
    mission = json.loads(MISSION.read_text())
    tools = json.loads((MISSION.parent / 'tools.json').read_text())
    admit(mission, tools, 'answer-consumer-preparation', ROOT)
    return mission


def manifest(command, started, files):
    return {'command': command, 'git_commit': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'environment': str(ROOT / '.venv/bin/python'),
            'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 set before package imports',
            'random_seeds': 'N/A: deterministic local preparation/receipt provider',
            'live_calls': 0, 'elapsed_milliseconds': int((time.monotonic() - started) * 1000),
            'finished_utc': datetime.now(timezone.utc).isoformat(),
            'plan': evidence_file(PLAN, ROOT), 'data': evidence_file(CORPUS, ROOT),
            'implementation': [evidence_file(Path(__file__), ROOT), evidence_file(Path(answer.__file__), ROOT)],
            'output_artifacts': [evidence_file(p, ROOT) for p in files],
            'legal_quality_evaluated': False}


def prepare():
    started = time.monotonic()
    mission = admitted()
    out = BASE / 'source'
    out.mkdir(parents=True, exist_ok=False)
    require(raw_digest(CORPUS.read_bytes()) == CORPUS_SHA, 'Frozen corpus changed')
    corpus = loads(CORPUS.read_bytes())['packet']
    units = corpus['units']
    require(len(units) == 54 and sum(len(u['text']) for u in units) == 54910, 'Corpus denominator changed')
    authority = loads(AUTHORITY.read_bytes())
    metadata = {u['unit_id']: {k: v for k, v in u.items() if k != 'text'} for u in authority['units']}
    historical_context = loads(CONTEXT.read_bytes())
    acquisition = loads((AUTHORITY.parent / 'authority-sources/acquisition-02.json').read_bytes())
    ut = next(row for row in acquisition if row['path'].endswith('/ut-current.pdf'))
    groups = [
        ('26ec22', 'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=26EC22', units[:50],
         ROOT / 'docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json'),
        ('ut', ut['url'], units[50:52], ROOT / ut['path']),
        ('23ec52', metadata[units[52]['unit_id']]['metadata']['url'], units[52:53],
         ROOT / 'artifacts/authority-source-revision/2026-09-29/attempt-01/sources/23ec52.json'),
        ('appendix', metadata[units[53]['unit_id']]['metadata']['url'], units[53:54],
         ROOT / 'artifacts/authority-source-revision/2026-09-29/attempt-01/sources/23ec52-appendix.pdf'),
    ]
    questions = [{'question_id': q['id'], 'text': q['question']}
                 for q in mission['questions'] if q['id'] in ('p10', 'evidence')]
    require([q['question_id'] for q in questions] == ['p10', 'evidence'], 'Question order changed')
    roots, mapping, provenance, references = [], [], [], [evidence_file(CORPUS, ROOT),
        evidence_file(AUTHORITY, ROOT), evidence_file(CONTEXT, ROOT)]
    for name, url, selected, original in groups:
        # The official URL identifies the originating document; the bytes are
        # explicitly local derived text. They are not represented as HTTP bytes.
        text = '\n'.join(u['text'] for u in selected)
        raw = text.encode('utf-8')
        path = out / (name + '.derived.txt')
        with path.open('xb') as stream:
            stream.write(raw)
        cursor, regions = 0, []
        for u in selected:
            a, b = cursor, cursor + len(u['text'])
            require(text[a:b] == u['text'], 'Source reconstruction lost characters')
            mapping.append({'original_unit_id': u['unit_id'], 'original_text_hash': digest(u['text']),
                            'url': url, 'start': a, 'end': b, 'qualification': u.get('qualification'),
                            'retained_metadata': metadata.get(u['unit_id'])})
            regions.append({'anchor': {'start': a, 'end': b, 'quote': u['text']}})
            cursor = b + 1
        # Separate ranges preserve source-unit boundaries, including both UT
        # selections. The parser can still split an oversized unit losslessly.
        selection = {'raw_sha256': raw_digest(raw), 'text_sha256': raw_digest(raw),
                     'ranges': [[r['anchor']['start'], r['anchor']['end']] for r in regions],
                     'regions': regions}
        original_ref = evidence_file(original, ROOT)
        if name == '26ec22':
            require(original_ref['sha256'] == 'b2e07418f147060531d01e743925f8b732414f90d3d66c7c0ae99e9c5d823828',
                    'Retained 26EC22 source changed')
        if name == 'ut':
            require(original_ref['sha256'] == ut['sha256'], 'UT retained PDF changed')
        if name in ('23ec52', 'appendix'):
            require(original_ref['sha256'] == metadata[selected[0]['unit_id']]['metadata']['raw_sha256'],
                    'Retained circular/Appendix raw bytes changed')
        roots.append({'url': url, 'media_type': 'text/plain', 'data': raw, 'selection': selection,
                      'local_reconstruction': True, 'original_evidence': original_ref})
        provenance.append({'name': name, 'url': url, 'original': original_ref,
                           'derived_text': evidence_file(path, ROOT), 'http_bytes': False,
                           'reconstruction': 'Exact retained unit text joined by one LF; original order preserved'})
        references.extend([original_ref, evidence_file(path, ROOT)])
    def no_network(_):
        raise AssertionError('Offline source preparation attempted network acquisition')
    context = acquire_context(roots, fetcher=no_network, max_documents=4, max_depth=0)
    require(len(context['documents']) == 4, 'Offline retained document missing')
    packet = packet_from_context(context, answer.question_text(questions))
    findings = audit_packet(packet, context)
    require(all(f['kind'] == 'SELECTED_AUTHORITY_CONTEXT' for f in findings), 'Packet source coverage failed')
    for row in mapping:
        prefix = 'd' + digest(row['url'])[:12]
        pieces = [u for u in packet['units'] if u['span']['source_id'] == prefix
                  and row['start'] <= u['span']['start'] < row['end']]
        pieces.sort(key=lambda u: u['span']['start'])
        original = next(u['text'] for u in units if u['unit_id'] == row['original_unit_id'])
        require(''.join(u['text'] for u in pieces) == original,
                'Packet splitting lost original characters in ' + row['original_unit_id'])
        row['packet_units'] = [u['unit_id'] for u in pieces]
        row['exact_character_preservation'] = True
    retained_context = {**context, 'documents': [{k: v for k, v in d.items() if k != 'data'}
                                                for d in context['documents']]}
    qualification = {
        'profile': 'investigation-answer-source-qualification.v1', 'source_packet_hash': digest(packet),
        'evidence': references,
        'limitations': [
            'Locally reconstructed retained selection, not HTTP source bytes or complete current law.',
            'The 26EC22 selection includes page titles and navigation; metadata is not an operative legal rule.',
            'UT Chapter 6 and first five pages are selected, whitespace-normalized historical extraction; '
            'edition/applicability remain unresolved and the full PDF is retained.',
            'The 23EC52 Appendix has retained extraction disagreement and unsupported visual content on pages 1–3.',
            'All parser units have normative=True by inherited parser default; this is not a reviewed legal classification.',
            'Exact character preservation of this derived corpus does not establish PDF extraction fidelity, '
            'source completeness, legal applicability or correctness.',
        ],
        'details': {'documents': provenance, 'unit_mapping': mapping,
                    'retained_extraction_findings': historical_context['findings'],
                    'applicable_assessment_interval': 'UNKNOWN'},
    }
    source_request = {'task': 'SOURCE_CAPACITY_ONLY', 'source_packet': packet,
                      'source_qualification': qualification, 'original_questions': questions}
    wire = compact_request(source_request, profile='v2')
    capacity = {'source_only_wire_bytes': len(canonical(wire)), 'maximum_input_bytes': 200000,
                'fits': len(canonical(wire)) <= 200000,
                'full_dossier_capacity_established': False}
    for name, value in [('packet.json', packet), ('context.json', retained_context),
                        ('qualification.json', qualification), ('mapping.json', mapping),
                        ('questions.json', questions), ('source-capacity-wire.json', wire)]:
        write(out / name, value)
    result = {'status': 'SOURCE_PREPARED' if capacity['fits'] else 'CAPACITY_BLOCKED',
              'original_units': len(units), 'original_characters': 54910,
              'packet_units': len(packet['units']), 'exact_character_preservation': True,
              'packet_audit': findings, 'capacity': capacity,
              'questions': questions, 'source': evidence_file(out / 'packet.json', ROOT),
              'context': evidence_file(out / 'context.json', ROOT),
              'qualification': evidence_file(out / 'qualification.json', ROOT),
              'legal_quality_evaluated': False, 'live_calls': 0}
    write(out / 'result.json', result)
    write(out / 'run-manifest.json', manifest('.venv/bin/python scripts/legal_mission_answer.py prepare',
          started, sorted(out.glob('*.json')) + sorted(out.glob('*.txt'))))
    print(json.dumps({k: v for k, v in result.items() if k not in ('packet_audit', 'questions')}, indent=2))


def receipt_proposal(request):
    """Deliberately non-substantive: a transport fixture, not an expert answer."""
    qids = list(request['question_hashes'])
    unit = request['source_packet']['units'][0]
    return {'binding_hash': request['binding_hash'],
            'answers': [{'question_id': q['question_id'], 'question_hash': digest(q['text']),
                         'answer': 'Scripted engineering receipt only. No legal conclusion evaluated.',
                         'claims': [{'claim_id': 'fixture.quote', 'conclusion': 'This supplied text is retained.',
                                     'inference': 'Exact quotation check only.',
                                     'support': [{'unit_id': unit['unit_id'], 'quote': unit['text']}],
                                     'contrary': [], 'assumptions': ['Controlled fixture.'],
                                     'unresolved': ['Legal sufficiency is not assessed.']}],
                         'conditional_alternatives': [], 'qualifications': ['Scripted receipt only.'],
                         'unresolved_dependencies': ['Source-grounded answer review remains required.']}
                        for q in request['original_questions']],
            'reading_account': [{'candidate_id': cid, 'reading_hash': digest(r), 'disposition': 'UNRESOLVED',
                                 'question_ids': qids, 'explanation': 'Retained without evaluating legal meaning.'}
                                for cid, r in request['candidates'].items()],
            'tool_account': [{'key': t['key'], 'result_hash': t.get('result_hash'), 'disposition': 'UNRESOLVED',
                              'question_ids': qids, 'explanation': 'Tool result delivered; consideration untested.',
                              'limitation': 'Engine execution does not prove a legal premise.'}
                             for t in request['investigation'].get('optional_tools', {}).get('checks', [])],
            'legal_correctness_established': False, 'release_eligible': False}


class ReceiptProvider:
    provider_id = 'offline.investigation-answer.receipt'
    live = False

    def __init__(self):
        self.requests = []

    def complete(self, request, schema, settings):
        require(len(canonical(request)) <= settings.max_input_bytes, 'Receipt input exceeds provider capacity')
        self.requests.append(request)
        return Completion(receipt_proposal(request), {'provider': self.provider_id, 'live': False,
                                                      'synthetic_receipt_only': True})


def qualify():
    started = time.monotonic()
    admitted()
    source_result = loads((BASE / 'source/result.json').read_bytes())
    require(source_result['status'] == 'SOURCE_PREPARED', 'Source prerequisite failed; stop this attempt')
    out = BASE / 'qualification'
    out.mkdir(parents=True, exist_ok=False)
    dossier = loads(FIXTURE.read_bytes())
    packet = read_evidence(dossier['packet'], ROOT)
    q = {'profile': 'investigation-answer-source-qualification.v1', 'source_packet_hash': digest(packet),
         'limitations': ['Synthetic gift-control fixture; not the P10/evidence questions or corpus.'],
         'evidence': [evidence_file(FIXTURE, ROOT)], 'details': {'synthetic_fixture': True}}
    write(out / 'fixture-qualification.json', q)
    provider = ReceiptProvider()
    result = answer.propose(ROOT, evidence_file(FIXTURE, ROOT), provider, out / 'consumer',
        investigation_directory=FIXTURE_DIRECTORY, expected_revision=dossier['revision'],
        questions=[{'question_id': 'gift', 'text': dossier['binding']['question']}],
        qualification_ref=evidence_file(out / 'fixture-qualification.json', ROOT))
    require(result['status'] == 'STRUCTURALLY_VALID_PROPOSAL', 'Fixture consumer qualification failed')
    # This is a source-material lower bound, explicitly NOT a fabricated full
    # investigation and never dispatched. All generated findings would add bytes.
    full_packet = read_evidence(source_result['source'], ROOT)
    minimum = {'task': 'FULL_SOURCE_ANSWER_LOWER_BOUND',
               'source_packet': full_packet,
               'source_context': answer.source_context_view(read_evidence(source_result['context'], ROOT), full_packet),
               'source_qualification': read_evidence(source_result['qualification'], ROOT),
               'original_questions': source_result['questions']}
    minimum_wire = compact_request(minimum, profile='v2')
    write(out / 'full-source-minimum-wire.json', minimum_wire)
    size = len(canonical(minimum_wire))
    result = {'status': 'CAPACITY_BLOCKED' if size > 200000 else 'FULL_DOSSIER_NOT_YET_QUALIFIED',
              'controlled_consumer': result, 'scripted_provider_calls': len(provider.requests), 'live_calls': 0,
              'full_source_lower_bound_bytes': size, 'maximum_input_bytes': 200000,
              'lower_bound_components': list(minimum), 'full_target_dossier_available': False,
              'matched_live_invocation_ready': False, 'legal_quality_evaluated': False,
              'limitations': ['The fixture answer proves no legal progress or tool benefit.',
                             'The full original-question investigation has not run; candidate/claim counts '
                             'and complete payload cannot be inferred from the small fixture.']}
    write(out / 'result.json', result)
    write(out / 'run-manifest.json', manifest('.venv/bin/python scripts/legal_mission_answer.py qualify',
          started, sorted(out.rglob('*.json'))))
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'qualify'))
    args = parser.parse_args()
    {'prepare': prepare, 'qualify': qualify}[args.action]()


if __name__ == '__main__':
    main()
