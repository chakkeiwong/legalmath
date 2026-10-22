"""Original-source reconciliation and bounded pre-repair consumer probes."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import sys
import time
import json

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, read, save, sha, relative
from scripts.prospectus_payment_references import retained
from scripts.prospectus_typed_delta import changes, apply, equal
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.anchors import bind
from legalmath.prospectus.successor.occurrences import segments

PREP = AUTH / 'reviews/reference-consumer-integrity-274'
SPEC = ROOT / 'src/legalmath/prospectus/successor/basf_legacy_references_spec.json'


def prepare():
    assert read(AUTH / 'program.json')['revision'] == 273
    p, answer = retained('candidate-answer')
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {r['id']: r for r in graph['units']}
    selected = {r['unit']: r for r in assembly['units']}
    inventory = read(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json')
    historical = inventory['historical_candidate_lines'] + inventory['additional_explicit_review_findings']
    rows = p['P3']['payload']['interpretation_input']['reference_admission']['references'][:20]
    source_checks = []
    for row in rows:
        matches = [r for r in historical if r.get('reviewed_reference', r.get('id')) == row['id']]
        assert matches, row['id']
        for original in matches:
            equal(original['exact_targets'], row['targets'], 'Original source targets differ from current link')
            if 'admitted_source' in original:
                expected_source = original['admitted_source']
            else:
                assert original['id'] == 'holding-proof-information'
                full = original['sources'][0]
                phrase = 'vorstehend unter (a) und (b)'
                assert full['quote'].count(phrase) == 1
                start = full['start'] + full['quote'].index(phrase)
                expected_source = {**full, 'start': start, 'end': start + len(phrase), 'quote': phrase}
            equal(expected_source, row['source'], 'Original source occurrence differs')
        for source in [row['source'], *[t['source'] for t in row['targets']]]:
            bind({'units': [raw[source['unit']]]}, source)
        target_selections = []
        for target in row['targets']:
            unit = selected[target['use']]
            parts = segments(graph, unit, _raw=raw)
            target_selections.append({'use': target['use'], 'role': unit['role'],
                'questions': unit['questions'], 'text': unit['text'], 'segments': parts})
        source_checks.append({'reference': deepcopy(row), 'original_records': deepcopy(matches),
            'source_selection': deepcopy(selected[row['from_use']]), 'target_selections': target_selections})
    contexts = inventory['historical_candidate_lines'][9]['source_pieces']
    printed = read(ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    spec = {'version': 'basf-legacy-references.v1', 'sources': printed['sources'],
        'references': rows, 'source_checks': source_checks, 'split_contexts': contexts,
        'original_inventory': relative(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json'),
        'original_inventory_sha256': sha(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json'),
        'automatic_discovery': False, 'complete_reference_graph': False}
    save(PREP / 'source-review.json', spec)
    save(SPEC, spec)
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py',
                 'src/legalmath/prospectus/successor/service.py'):
        dest = PREP / 'pre-edit' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    value = deepcopy(p['P3']['payload']['interpretation_input'])
    row = next(r for r in value['reference_admission']['references'] if r['id'] == 'prose-notice-118-34')
    row['targets'] = row['targets'][:1]
    began = time.monotonic()
    broken = service.interpretation_product(p['P1'], p['P2'], value)
    dep = next(d for d in broken['payload']['dependencies'] if d['id'] == 'reviewed-reference:prose-notice-118-34')
    assert dep['status'] == 'RESOLVED' and len(dep['targets']) == 1
    save(PREP / 'upstream-truncated.json.gz', {'input_delta': changes(p['P3']['payload']['interpretation_input'], value),
        'P3_delta': changes(p['P3'], broken), 'resolved_dependency': dep,
        'status': 'GAP_REPRODUCED', 'wall_seconds': time.monotonic() - began})
    forged = deepcopy(p)
    payload = deepcopy(p['P3']['payload'])
    dep = next(d for d in payload['dependencies'] if d['id'] == 'reviewed-reference:prose-notice-118-34')
    dep['targets'] = dep['targets'][:1]
    bundle = p['P1']['payload']['request']['bundle']
    forged['P3'] = service.seal('P3', bundle, p['P3']['inputs'], payload)
    for stage in ('P4', 'P5'):
        forged[stage] = service.seal(stage, bundle, {**p[stage]['inputs'], 'P3': forged['P3']['sha256']}, p[stage]['payload'])
    began = time.monotonic()
    consumed = service.consume(forged, ROOT, mode='frozen')
    equal(consumed['questions'], answer['questions'], 'Unexpected pre-repair question difference')
    delta = changes(p, forged)
    equal(apply(p, delta), forged, 'Diagnostic product delta is lossy')
    save(PREP / 'consumer-forged.json.gz', {'products_delta': delta, 'answer_delta': changes(answer, consumed),
        'products_sha256': digest(forged), 'answer_sha256': digest(consumed),
        'status': 'GAP_REPRODUCED', 'wall_seconds': time.monotonic() - began})
    return {'status': 'PASS', 'original_references_checked': 20,
        'truncated_old_reference_accepted_P3': True, 'resealed_changed_dependency_accepted_consumer': True,
        'baseline_products_sha256': digest(p), 'baseline_answer_sha256': digest(answer)}


def main():
    began = time.monotonic()
    folder = PREP / 'preparation-v2'
    save(folder / 'preparation-started.json', {'command': sys.argv, 'stage_bound_seconds': 180,
        'started_at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU; GPU deliberately hidden'})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Reference integrity preparation180s')))
    signal.alarm(180)
    try:
        result = {**prepare(), 'wall_seconds': time.monotonic() - began}
        save(folder / 'preparation-result.json', result)
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / 'preparation-failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
