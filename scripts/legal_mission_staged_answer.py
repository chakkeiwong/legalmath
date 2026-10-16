#!/usr/bin/env python3
"""Closed offline qualification for the one-time staged answer attempt."""
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import investigation_answer as answer
from legalmath.interpretation.assurance import staged_investigation_answer as staged
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.decomposition import compact_request
from scripts.legal_mission_control import admit, read, BASE as MISSION_BASE
from scripts.legal_mission_answer import receipt_proposal

OUT = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-staging'
PLAN = ROOT / 'docs/implementation/legal-mission-control/answer-staging-admission.md'


def admission():
    admit(read(ROOT / MISSION_BASE / 'mission.json'), read(ROOT / MISSION_BASE / 'tools.json'),
          'answer-staging-preparation', ROOT)


def receipt(request):
    """Intentionally legally empty; a structural pass is not a legal answer."""
    if request['task'] == 'REVIEW_SCOPED_EVIDENCE':
        ids = [r['record_id'] for r in request['records']]
        return {'review_binding': request['review_binding'],
                'accounts': [{'record_ids': ids, 'disposition': 'UNRESOLVED',
                              'explanation': 'Synthetic receipt; no legal assessment.'}],
                'findings': [{'record_ids': ids, 'question_ids': [q['question_id'] for q in request['original_questions']],
                              'conclusion': 'No legal conclusion has been evaluated.',
                              'inference': 'Record transport only.', 'support': [], 'contrary': [],
                              'assumptions': ['Scripted provider.'], 'unresolved': ['Every legal inference.'],
                              'cross_record_dependencies': []}], 'legal_correctness_established': False}
    result = receipt_proposal(request)
    result.update(stage_binding=request['stage_binding'], review_account=[
        {'review_binding': k, 'review_hash': v, 'explanation': 'Synthetic receipt only.'}
        for k, v in request['review_hashes'].items()])
    return result


def qualify(work):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source, settings
    from tests.search.test_formal import AT
    from scripts.legal_integration_tools import ProductToolBackend
    provider = FunctionProvider(complete_responder)
    runner = CompleteInvestigation(ROOT, work / 'product', provider,
        ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
        settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
        optional_tool_backend=ProductToolBackend())
    dossier = runner.run([source()], 'Selected gift control')
    ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', ROOT)
    qualification = {'profile': 'investigation-answer-source-qualification.v1',
        'source_packet_hash': digest(loads((ROOT / dossier['packet']['path']).read_bytes())),
        'limitations': ['Synthetic fixture; legal accuracy and full target capacity not evaluated.'],
        'evidence': [dossier['packet']], 'details': {'fixture': True}}
    save(work / 'qualification.json', qualification)
    arguments = {'investigation_directory': runner.directory, 'expected_revision': dossier['revision'],
        'questions': [{'question_id': 'gift', 'text': 'Selected gift control'}],
        'qualification_ref': evidence_file(work / 'qualification.json', ROOT)}
    response = staged.propose(ROOT, ref, FunctionProvider(receipt), work / 'consumer', **arguments)
    checks = dossier['optional_tools']['checks']
    return {'status': response['status'], 'dossier': ref, 'consumer': response,
            'tool_kinds': sorted({c['kind'] for c in checks}),
            'tool_names': sorted({c.get('tool', '') for c in checks}),
            'investigation_execution_complete': dossier['execution_complete'],
            'fresh_current_dossier': True, 'new_live_calls': 0, 'legal_quality_evaluated': False,
            'limit': 'Actual installed backend and dossier consumer; legally empty scripted responses.'}


def capacity(work):
    """Retained stress content, never an allegedly current investigation dossier."""
    qualified = read(OUT / 'qualify/result.json')
    staged.require(qualified['status'] == 'STRUCTURALLY_VALID_PROPOSAL', 'Fresh qualification incomplete')
    original = read(OUT / 'qualify/consumer/original-request.json')
    source_dir = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
    retained_path = ROOT / 'artifacts/legal-candidate-response-product/2026-10-09/replay/scoped/result.json'
    staged.require(raw_digest(retained_path.read_bytes()) ==
        'e42087a31f20d0d11024b775882b0caedcf17c3ed370dbe2ed4bcfed0028a609', 'Stress evidence changed')
    inputs_path = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/inputs.json'
    staged.require(raw_digest(inputs_path.read_bytes()) ==
        '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf', 'Stress input changed')
    inputs = read(inputs_path)
    # These are deliberately labelled separately: old judgments refer to a
    # 12-unit packet, while additional full-source overhead is measured too.
    original['source_packet'] = inputs['packet']
    original['candidates'] = inputs['candidates']
    original['source_claims'] = inputs['claims']
    original['investigation']['scoped'] = read(retained_path)
    original['capacity_stress_only'] = {
        'historical_judgment_packet': '12 units, preserved with original identifiers',
        'full_target_packet': read(source_dir / 'packet.json'),
        'full_target_qualification': read(source_dir / 'qualification.json'),
        'original_target_questions': read(source_dir / 'questions.json'),
        'limit': 'Composite size stress case, not legally coherent input or a verified current dossier. '
                 'Non-scoped core/criticism is synthetic; full target common context remains unknown.'}
    save(work / 'stress-request.json', original)
    try:
        prepared = staged.partition(original)
        save(work / 'partition.json', prepared)
        reviews = [receipt(staged.review_request(prepared['common'], prepared['registry'], b))
                   for b in prepared['batches']]
        request = staged.synthesis_request(original, prepared, reviews)
        save(work / 'synthetic-synthesis-request.json', request)
        synthesis_bytes = len(canonical(compact_request(request, profile='v2')))
        return {'status': 'CAPACITY_SCREEN_PASSED' if synthesis_bytes <= 200000 else 'CAPACITY_BLOCKED',
            'batches': len(reviews), 'maximum_review_wire_bytes': max(prepared['wire_bytes']),
            'synthetic_synthesis_bytes': synthesis_bytes,
            'unique_records': len(prepared['registry']['records']),
            'raw_reconstruction_equal': staged.restore(prepared['registry']) == original['investigation']['scoped'],
            'source': evidence_file(retained_path, ROOT), 'new_live_calls': 0,
            'full_target_feasibility_established': False, 'legal_quality_evaluated': False,
            'limit': 'Synthetic summaries are short and legally empty; real summaries/core may overflow.'}
    except LegalMathError as exc:
        return {'status': 'CAPACITY_BLOCKED' if exc.code == 'E_RESOURCE_LIMIT' else 'REJECTED',
                'error': exc.code, 'details': exc.details, 'new_live_calls': 0,
                'source': evidence_file(retained_path, ROOT), 'full_target_feasibility_established': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('qualify', 'capacity'))
    args = parser.parse_args()
    admission()
    work = OUT / args.action
    work.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        result = {'qualify': qualify, 'capacity': capacity}[args.action](work)
    except Exception as exc:
        result = {'status': 'FAILED', 'error': type(exc).__name__,
                  'details': str(exc), 'new_live_calls': 0}
        save(work / 'result.json', result)
        raise
    finally:
        save(work / 'run-manifest.json', {
            'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'command': '.venv/bin/python scripts/legal_mission_staged_answer.py ' + args.action,
            'environment': str(ROOT / '.venv/bin/python'),
            'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally set before imports',
            'seeds': 'N/A: synthetic deterministic responses / retained file measurements',
            'wall_milliseconds': int((time.monotonic() - started) * 1000),
            'finished_utc': datetime.now(timezone.utc).isoformat(), 'plan': evidence_file(PLAN, ROOT),
            'source': [evidence_file(Path(__file__), ROOT), evidence_file(Path(staged.__file__), ROOT)]})
    save(work / 'result.json', result)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] in ('STRUCTURALLY_VALID_PROPOSAL', 'CAPACITY_SCREEN_PASSED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
