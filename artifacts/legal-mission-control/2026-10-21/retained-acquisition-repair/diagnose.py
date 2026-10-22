"""Offline diagnostic of the actual master product entry; never dispatch."""
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_integration_phased_live as live
from scripts.legal_mission_execution import read, ref, save
from scripts import legal_product_completion as entry
from legalmath.canonical import digest
from legalmath.interpretation.assurance.integration_contract import read_evidence
from legalmath.interpretation.assurance.phased import retained_acquisition
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider

WORK = Path(__file__).resolve().parent


def duties(packet):
    request = packet['request']
    context = {k: v for k, v in request.items() if k != 'records'}
    if request['task'] not in ('READ_SOURCE', 'REVIEW_REQUIREMENTS'):
        return Counter({'joint:' + packet['packet_hash']: 1})
    return Counter(digest(dict(context=context, record=record)) for record in request['records'])


def main():
    begin = time.monotonic()
    run_product = entry.run_product
    original_load = retained_acquisition.load
    reports = {}
    active = None

    def never(*args, **kwargs):
        raise AssertionError('Offline diagnostic attempted provider dispatch')

    def capture(product, reference):
        value = read_evidence(reference, ROOT)
        originals = [r for r in value['outputs'] if 'recovery_of' not in r]
        packets, blocked = product.reading_packets()
        selected = [p for p in packets if any(set(product.active_questions) &
            product.acquisition_questions(r) for r in p['request']['records'])]
        retained = {p['packet_hash'] for p in originals}
        missing = [p for p in selected if p['packet_hash'] not in retained]
        required_duties = sum((duties(p) for p in selected), Counter())
        retained_duties = sum((duties(p) for p in originals), Counter())
        manager = product.dispatch.capacity_manager
        try:
            product.dispatch.capacity_manager = None
            legacy, legacy_blocked = product.reading_packets()
        finally:
            product.dispatch.capacity_manager = manager
        legacy_selected = [p for p in legacy if any(set(product.active_questions) &
            product.acquisition_questions(r) for r in p['request']['records'])]
        rebuilt = []
        for output in originals:
            r = output['request']
            p = product.route.make_packet(r['task'], [s['id'] for s in r['records']],
                reader=r['reader'], question_ids=[q['question_id'] for q in r['original_questions']],
                dependency=r.get('dependency'))
            rebuilt.append(p['packet_hash'] == output['packet_hash'] and p['request'] == r)
        report = dict(question=active, reference=reference, input_hash=product.route.input_hash,
            retained_originals=len(originals), retained_recoveries=len(value['outputs'])-len(originals),
            current_planned=len(selected), missing_current_packet_hashes=len(missing),
            missing_current_by_task=dict(Counter(p['request']['task'] for p in missing)),
            legacy_planned=len(legacy_selected), legacy_missing=sum(p['packet_hash'] not in retained for p in legacy_selected),
            current_blocked=len(blocked), legacy_blocked=len(legacy_blocked),
            missing_exact_observation_or_joint_duties=dict(required_duties-retained_duties),
            all_original_requests_reconstruct=all(rebuilt),
            reported_complete=value['question_acquisition_complete'][active],
            current_batch_sizes=dict(Counter(len(p['request']['records']) for p in selected)),
            legacy_batch_sizes=dict(Counter(len(p['request']['records']) for p in legacy_selected)))
        reports[active] = report
        save(WORK/'diagnosis.json', dict(provider_calls=0, questions=reports, complete=False))
        try:
            result = original_load(product, reference)
            report['entry_result'] = 'VALIDATED'
            return result
        except Exception as exc:
            report['entry_result'] = dict(code=getattr(exc, 'code', type(exc).__name__),
                reason=str(getattr(exc, 'details', None) or exc))
            raise
        finally:
            save(WORK/'diagnosis.json', dict(provider_calls=0, questions=reports, complete=False))

    def isolated(root, directory, provider, jdk, at, **kwargs):
        kwargs.update(bounded_phase='acquire', shared_prefix=None)
        return run_product(root, WORK/'entry'/active, provider, jdk, at, **kwargs)

    service = live.configure().provider()
    for active in ('p10', 'p14', 'evidence', 'gatecoin'):
        try:
            with patch.object(entry, 'run_product', isolated), \
                    patch.object(retained_acquisition, 'load', capture), \
                    patch.object(BoundedCodexProvider, 'complete', never), \
                    patch.object(live, 'phase_admit', lambda owner: never):
                live.product_route(active, None, service)
        except Exception as exc:
            if active not in reports:
                reports[active] = dict(entry_result=dict(code=getattr(exc, 'code', type(exc).__name__),
                    reason=str(getattr(exc, 'details', None) or exc)))
        print(active, json.dumps(reports[active], sort_keys=True), flush=True)
    result = dict(provider_calls=0, complete=True, questions=reports,
        wall_seconds=time.monotonic()-begin, cpu_mode='GPU deliberately hidden',
        command='.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)),
        script=ref(ROOT, Path(__file__)), plan=ref(ROOT,
            'docs/plans/legal-retained-acquisition-capacity-repair-2026-10-21.md'))
    save(WORK/'diagnosis.json', result)


if __name__ == '__main__':
    main()
