"""Inspect exact retained context delivery; no provider or scheduler access."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/chakwong/python/legalmath')
HERE = ROOT/'artifacts/legal-mission-control/2026-10-23/p14-corrected-context'
RUNTIME = ROOT/'artifacts/legal-mission-control/2026-10-23/p14-deployment/context-isolated-live/arms/p14/baseline'
TARGETS = {
    'product_fn2': ['source:d996fc27b2d2e.u41.7404:0'],
    'product_fn3': ['source:d996fc27b2d2e.u42.7511:0'],
    'product_fn4': ['source:d996fc27b2d2e.u43.7658:0'],
    'handbook_legal_status_with_continuation': [
        'source:handbook.oct2024.page7:0',
        'source:handbook.oct2024.page8:0',
        'source:handbook.oct2024.page9:0'],
    'retained_appendix_text': [
        'source:d4b586a37635c.u0.0:0',
        'source:d4b586a37635c.u0.0:1',
        'source:d4b586a37635c.u0.0:2'],
    'intermediary_network_discussion': ['source:dfdc3eb665b8e.u0.0:3'],
}


def read(path):
    return json.loads(path.read_text())


def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def coverage(ids):
    present = set(ids)
    return {name: dict(delivered=[rid for rid in target if rid in present],
                       not_delivered=[rid for rid in target if rid not in present],
                       all_delivered=set(target) <= present)
            for name, target in TARGETS.items()}


def report():
    source = RUNTIME/'source-store.json'
    store = read(source)
    assert all(rid in store for target in TARGETS.values() for rid in target)
    census_path = ROOT/'artifacts/legal-mission-control/2026-10-23/p14-decisions/decisions.json'
    census = {r['id']: r for r in read(census_path) if r['verdict'] == 'UNRESOLVED'}
    planned_path = ROOT/'artifacts/legal-mission-control/2026-10-23/p14-deployment/context-preflight-population.json'
    planned = read(planned_path)
    assert len(planned) == 672 and {r['assignment_id'] for r in planned} == set(census)
    planned_rows = [dict(assignment=r['assignment_id'],
                         coverage=coverage(r['delivered_record_ids'])) for r in planned]
    observed = []
    for path in sorted(RUNTIME.glob('context-review-*.json')):
        item = read(path)
        result = item['result']
        value = result.get('value', {})
        observed.append(dict(assignment=item['item']['id'], receipt=ref(path),
            status=result['status'], verdict=value.get('verdict'),
            coverage=coverage(item['delivered_ids']), issues=value.get('issues', []),
            context_needs=value.get('context_needs', []),
            source_gaps=value.get('source_gaps', []), reason=value.get('reason', result.get('reason'))))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = HERE/'context-coverage'
    folder.mkdir(exist_ok=True)
    result = dict(at_utc=datetime.now(timezone.utc).isoformat(),
        question='Which specifically identified retained source passages are delivered in planned and observed P14 continuations?',
        baseline=ref(census_path), planned_population=ref(planned_path), source_store=ref(source),
        target_records={name: [store[rid] for rid in ids] for name, ids in TARGETS.items()},
        planned_count=len(planned_rows), observed_count=len(observed),
        planned_full_delivery_counts={name: sum(r['coverage'][name]['all_delivered'] for r in planned_rows)
                                     for name in TARGETS},
        observed_full_delivery_counts={name: sum(r['coverage'][name]['all_delivered'] for r in observed)
                                      for name in TARGETS},
        observed_verdicts=dict(Counter(r['verdict'] for r in observed if r['verdict'])),
        planned_rows=planned_rows, observed_rows=observed,
        provider_calls=0, legal_acceptance=False,
        limits='Source presence establishes delivery only. These targets are not presumed necessary for every assignment. Missing from a request does not mean absent from the corpus. No original verdict is changed.')
    path = folder/(stamp+'.json')
    with path.open('x') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in
        ('target_records', 'planned_rows', 'observed_rows')} | {'report':str(path.relative_to(ROOT))}, indent=2))


if __name__ == '__main__':
    report()
