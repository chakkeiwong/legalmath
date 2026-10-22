"""Measure every retained baseline assignment with the repaired constructor."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json
import os
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save
from scripts import legal_integration_phased_live as live
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import group_review, review_repair
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
WORK = Path(__file__).resolve().parent
ARMS = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface/live/arms'

def never(*args, **kwargs):
    raise AssertionError('Census may not dispatch')

def main():
    began = time.monotonic()
    program = read(ROOT/live.PROGRAM)
    envelope = read(ROOT/program['prerequisite_repair']['source']['path'])
    acquisition = load_exact(ROOT/live.LIVE/'acquisition/investigation.json')
    encode = tokenizer(ROOT/live.TOKENIZER)
    service = live.configure().provider()
    service.complete = never
    report = dict(provider_calls=0, questions={}, started_at_utc=datetime.now(timezone.utc).isoformat(),
        exact_questions=['p14', 'gatecoin'], unknown_future_answers=['p10', 'evidence'],
        scope='Exact retained baseline packing; future answers need their own measured phase admission.')
    for qid in ('p14', 'gatecoin'):
        original = ARMS/qid/'baseline'
        identity = read(original/'identity.json')
        options = {k:identity[k] for k in ('requirement_account_profile','requirement_account_input_profile',
            'requirement_account_instruction_profile','requirement_account_capacity_profile',
            'requirement_account_output_profile','common_capacity_profile') if k in identity}
        p = PhasedProduct(ROOT, WORK/'packing'/qid, service, envelope, encode, limits=Limits(),
            maximum_calls=8100, maximum_corrections=1, active_questions=[qid],
            downstream_input_profile=program['repair_execution']['downstream_input_profile'],
            downstream_instruction_profile=program['repair_execution']['downstream_instruction_profile'],
            downstream_capacity_profile=program['synthesis_resolution']['downstream_capacity_profile'],
            review_repair_profile=review_repair.PROFILE, phase_admit=never, phase_identity='offline-repair-census', **options)
        question = next(q for q in envelope['original_questions'] if q['question_id'] == qid)
        answer = load_exact(original/'result.json')['answers'][qid]['answer']['value']
        p.capacity_checkpoint = ref(ROOT, WORK/'checkpoints/arms'/qid/'baseline.json')
        retained, _ = review_repair.retained_groups(p, qid, question, answer, acquisition['discovered_dependencies'])
        held_ids = [i for c in retained for i in c['request']['required_considered']]
        calls, members, blocked, items = group_review.plan(p, qid, question, answer,
            acquisition['discovered_dependencies'], exclude_ids=held_ids)
        measurements = [p.dispatch.measure(c['request'], c['schema']) for c in calls]
        row = dict(assignments=len(items)+len(held_ids), retained_assignments=len(held_ids),
            grouped_calls=len(calls), blocked=len(blocked),
            group_sizes=dict(Counter(len(c['request']['required_considered']) for c in calls)),
            maximum_visible_bytes=max(m['bytes'] for m in measurements),
            maximum_visible_tokens=max(m['local_tokens'] for m in measurements),
            blocked_ids=[i['id'] for i in blocked], answer=ref(ROOT, original/'result.json'))
        save(WORK/'packing'/(qid+'-membership.json'), members)
        report['questions'][qid] = row
        save(WORK/'packing-census.json', report)
        print(json.dumps(dict(question=qid, **row)), flush=True)
    report['wall_seconds'] = time.monotonic()-began
    save(WORK/'packing-census.json', report)

if __name__ == '__main__':
    main()
