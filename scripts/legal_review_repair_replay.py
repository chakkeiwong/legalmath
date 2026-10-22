"""Current production-entry replay, with missing model work explicitly offline."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import time
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save, require
from scripts import legal_integration_phased_live as live
from scripts.legal_review_repair import WORK, QUESTIONS
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import group_review, review_repair
from legalmath.interpretation.assurance.phased.source_review import assignments


def main():
    began = time.monotonic()
    before = ref(ROOT, live.BASE/'live-calls.json')
    original = read(ROOT/live.PROGRAM)
    candidate = deepcopy(original)
    candidate['review_repair'] = dict(work=str(WORK/'production-replay'), review_profile=review_repair.PROFILE,
        checkpoints={q:ref(ROOT, WORK/'checkpoints'/(q+'.json')) for q in QUESTIONS},
        arm_checkpoints={q:{p.stem:ref(ROOT,p) for p in (ROOT/WORK/'checkpoints/arms'/q).glob('*.json')} for q in QUESTIONS})
    service = live.configure().provider()
    original_read = live.read
    def read_candidate(path):
        return deepcopy(candidate) if path == ROOT/live.PROGRAM else original_read(path)
    admitted, missing = [], []
    def admission(owner):
        def phase(name, count):
            admitted.append(dict(owner=owner, name=name, count=count))
            return dict(owner=owner, name=name, count=count, offline=True)
        return phase
    class NoCalls:
        live = False
        reference_transport = True
        acquisition_workers = 1
        measure = service.measure
        def complete(self, request, schema, settings):
            missing.append(dict(task=request['task'], request_hash=digest(request)))
            raise LegalMathError('E_DEPENDENCY', details='Offline replay: missing model work; no external call')
    original_plan = group_review.plan
    def saved_membership(product, qid, question, answer, dependencies, *, prefix='', exclude_ids=(), **kwargs):
        if qid not in ('p14','gatecoin') or prefix:
            return original_plan(product, qid, question, answer, dependencies, prefix=prefix, exclude_ids=exclude_ids, **kwargs)
        # The census already performed greedy packing of these exact inputs.
        # Rebuild and measure every saved group, preserving every assignment.
        membership = read(ROOT/WORK/'packing'/(qid+'-membership.json'))
        rows = [r for r in assignments(product, qid, dependencies) if r['id'] not in exclude_ids]
        table = {r['id']:r for r in rows}
        flattened = [i for ids in membership.values() for i in ids]
        require(len(flattened) == len(set(flattened)) and set(flattened) == set(table), 'Replay membership changed')
        census = read(ROOT/WORK/'packing-census.json')['questions'][qid]
        verify_answer = read(ROOT/census['answer']['path'])['answers'][qid]['answer']['value']
        require(answer == verify_answer, 'Replay answer differs from measured census')
        calls = []
        for key, ids in membership.items():
            request, schema = group_review.build(product, qid, question, answer, [table[i] for i in ids])
            product.dispatch.measure(request, schema)
            calls.append(dict(key=key, request=request, schema=schema,
                validate=lambda value, ids=ids, records=request['records']:
                    group_review.validate(product,qid,value,ids,records)))
        return calls, membership, [], rows
    results = {}
    with patch.object(live, 'read', read_candidate), patch.object(live, 'phase_admit', admission), \
            patch.object(group_review, 'plan', saved_membership):
        for q in QUESTIONS:
            start_missing = len(missing)
            try:
                # Actual wrapper -> run_product -> PhasedProduct -> retained
                # acquisition, preparation and answer paths. No staged imports.
                prepared = live.product_route(q, None, NoCalls(), preparation_only=True)
                outcome = live.product_route(q, None, NoCalls())
                folder = ROOT/WORK/'production-replay/live/arms'/q/'baseline'
                current = read(folder/'result.json')
                if q in ('p14','gatecoin'):
                    old = read(ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface/live/arms'/q/'baseline/result.json')
                    require(current['answers'][q]['answer']['value'] == old['answers'][q]['answer']['value'],
                        'Successful original answer was changed')
                results[q] = dict(route_completed=True, original_answer_unchanged=q in ('p14','gatecoin'),
                    result=ref(ROOT,folder/'result.json'))
            except Exception as exc:
                # A missing preparation is expected for P10/evidence; preserve
                # its exact cause, never classify a changed identity as a pass.
                reason = str(getattr(exc,'details',None) or exc)
                results[q] = dict(route_completed=False, error=type(exc).__name__, code=getattr(exc,'code',None), reason=reason)
                require(q in ('p10','evidence') and len(missing) > start_missing
                    and getattr(exc,'code',None) == 'E_DEPENDENCY', 'Unexpected production replay failure: '+q+' '+reason)
            results[q]['missing_model_requests'] = deepcopy(missing[start_missing:])
            save(ROOT/WORK/'production-replay-progress.json', results)
            print(json.dumps(dict(question=q, **results[q])), flush=True)
    require(ref(ROOT, live.BASE/'live-calls.json') == before, 'Offline replay charged a provider call')
    result = dict(verdict='PASS', provider_calls=0, ledger_unchanged=True, legal_acceptance=False,
        current_production_entry=True, actual_live_admission=False, questions=results, admissions=admitted,
        membership_optimization='Exact measured census; every request rebuilt and measured, no assignments removed',
        wall_seconds=time.monotonic()-began)
    save(ROOT/WORK/'production-replay.json', result)
    print(json.dumps(dict(verdict='PASS', wall_seconds=result['wall_seconds'], provider_calls=0)))


if __name__ == '__main__':
    main()
