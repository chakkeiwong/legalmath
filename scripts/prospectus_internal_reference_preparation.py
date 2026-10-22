"""Bounded original-source preparation and pre-edit ordinary-consumer probes."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, read, save, sha, relative
from scripts.prospectus_financial_references import retained
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, segments, _DependencyLookup

PREP = AUTH / 'reviews/internal-closure-279'
SPEC = ROOT / 'src/legalmath/prospectus/successor/basf_internal_references_spec.json'
KEY = 'basf-base-september-2022-exchange'
IDS = ('temporary-global-self-scope', 'payment-additional-amounts', 'tax-call-additional-amounts',
       'holder-option-tax-exception', 'holder-option-self-scope', 'tax-call-reverse-conditions',
       'substitution-whole-scope', 'additional-amounts-backward-scope',
       'substitution-affiliate-definition', 'depository-proof-scope')
LEDGER = tuple(('historical_candidate_lines', n) for n in (1, 10, 13, 15, 18, 24, 34)) + tuple(
    ('additional_explicit_review_findings', n) for n in (4, 5, 10))
GROUPS = dict(zip(IDS, ('temporary', 'tax', 'tax', 'tax-call', 'holder', 'tax-call',
                        'substitution', 'tax-body', 'affiliate', 'proof')))


def reseal(p, semantic):
    out = dict(p)
    bundle = p['P1']['payload']['request']['bundle']
    out['P3'] = service.seal('P3', bundle, p['P3']['inputs'], semantic)
    for stage in ('P4', 'P5'):
        out[stage] = service.seal(stage, bundle, {**p[stage]['inputs'], 'P3': out['P3']['sha256']}, p[stage]['payload'])
    return out


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH / 'program.json')['revision'] == 278
    for name in ('reference_closure.py', 'reviewed_references.py', 'service.py'):
        original = ROOT / 'src/legalmath/prospectus/successor' / name
        target = PREP / 'pre-edit' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(original.read_bytes())
    p, old_answer = retained('candidate-answer')
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {u['id']: u for u in graph['units']}
    selected = {u['unit']: u for u in assembly['units']}

    def unit(page, line):
        return raw[f'{KEY}:p{page}:l{line}']

    locations = {
        'temporary': [(108, n) for n in range(59, 82)],
        'tax': [(125, n) for n in (1, 2, *range(10, 51))],
        'tax-body': [(125, n) for n in range(10, 51)],
        'tax-call': [(118, n) for n in range(31, 59)] + [(119, n) for n in range(9, 13)],
        'holder': [(119, n) for n in range(24, 82)] + [(120, n) for n in range(1, 9)],
        'substitution': [(128, n) for n in (*range(56, 62), *range(75, 82))] + [
            (129, n) for n in (*range(1, 5), *range(12, 23), *range(33, 51))],
        'affiliate': [(129, n) for n in (37, 38)],
        'proof': [(132, n) for n in range(67, 87)] + [(133, n) for n in range(1, 11)],
    }
    targets = {}
    for group, places in locations.items():
        targets[group] = []
        for page, line in places:
            u = unit(page, line)
            assert selected[u['id']]['role'] in ('OPERATIVE', 'UNKNOWN')
            targets[group].extend({'source': s['source'], 'use': u['id'],
                                   'language': raw[s['source']['unit']]['language']}
                                  for s in segments(graph, selected[u['id']], _raw=raw))
    rows = []
    citations = (
        (108, 79, 'diesem Absatz (b) dieses § 1 Absatz (3)'),
        (115, 11, '§ 7'), (118, 50, '§ 7 dieser Bedingungen'),
        (119, 29, '§ 5 Absatz (2)'), (119, 60, 'diesem § 5 Absatz (3)'),
        (123, 35, 'Absatzes (2)'), (129, 37, 'dieses § 10'),
        (125, 49, 'im oben genannten Sinn'),
        (128, 58, 'verbundenes Unternehmen (wie unten'),
        (133, 4, 'Für die Zwecke des Vorstehenden'),
    )
    contexts = []
    for identity, (page, line, phrase) in zip(IDS, citations):
        u = unit(page, line)
        assert u['raw'].count(phrase) == 1
        left = u['raw'].index(phrase)
        source = anchor(u, left, left + len(phrase))
        discoveries = [r['id'] for r in graph['references'] if r['unit'] == u['id']
                       and left <= r['start'] < r['end'] <= left + len(phrase)]
        rows.append({'id': identity, 'form': 'relative', 'source': source, 'from_use': u['id'],
            'language': u['language'], 'targets': targets[GROUPS[identity]], 'authority': source,
            'questions': ['Q1', 'Q2'], 'discovery_ids': discoveries,
            'reason': 'Complete selected original internal scope; cyclic support, statutory application and actual events remain unresolved.'})
        contexts.append(anchor(u))
    # The printed citation/definition continues on the following line.
    contexts.extend(anchor(unit(page, line)) for page, line in ((123, 36), (128, 59)))
    packet = {'version': 'reviewed-references.v3', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'Codex original internal source pages108,115,118-120,123,125,128-129,132-133',
            'kind': 'DEVELOPMENT', 'reason': 'Full selected internal targets; conservative cycles and unknown headings'},
        'references': rows}
    truncated = deepcopy(packet)
    for row in truncated['references']:
        row['targets'] = row['targets'][-1:]
    generic, _ = admit(graph, assembly, truncated, _lookup=_DependencyLookup(graph, assembly))
    save(PREP / 'generic-truncation.json', {'statuses': [d['status'] for d in generic],
        'complete_original_targets_missing': True, 'actual_generic_admission_accepted': True})
    spans = {'temporary': ((108, 59, 81),), 'tax': ((125, 1, 66),),
        'tax-body': ((125, 10, 50),), 'tax-call': ((118, 31, 77), (119, 1, 12)),
        'holder': ((119, 24, 81), (120, 1, 8)),
        'substitution': ((128, 54, 81), (129, 1, 52)),
        'affiliate': ((128, 56, 61), (129, 37, 38)),
        'proof': ((132, 67, 86), (133, 1, 10))}
    selection = {group: [{'raw_source': anchor(unit(page, line)), 'use': unit(page, line)['id'],
        **{k: selected[unit(page, line)['id']].get(k) for k in ('role', 'questions', 'text', 'character_map')},
        'segments': segments(graph, selected[unit(page, line)['id']], _raw=raw)}
        for page, first, last in ranges for line in range(first, last + 1)] for group, ranges in spans.items()}
    printed = read(ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    pages = (108, 115, 118, 119, 120, 123, 125, 128, 129, 132, 133)
    images = {k: v for k, v in printed['images'].items() if k.endswith(tuple(
        [f'base-{page}.png' for page in pages] + ['final-4.png', 'final-5.png']))}
    assert len(images) == 13
    for path, checksum in images.items():
        assert sha(ROOT / path) == checksum
    for source in printed['sources']:
        assert sha(ROOT / source['path']) == source['sha256']
    spec = {'version': 'basf-internal-references.v1', 'sources': printed['sources'], 'references': rows,
        'groups': GROUPS, 'selection': selection, 'contexts': contexts, 'images': images,
        'automatic_discovery': False, 'conservative_cycle_policy': True}
    save(PREP / 'source-review.json', spec)
    save(PREP / 'packet.json', packet)
    ledger = read(AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
    for (family, index), row in zip(LEDGER, rows):
        record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
        assert record['current_reference'] is None
        record.update(current_reference=row, current_status='CURRENT_LINK_WITH_CONSERVATIVE_CLOSURE',
                      complete_legal_interpretation=False)
    save(PREP / 'reconciliation-proposed.json.gz', ledger)
    save(PREP / 'source-summary.json', {'targets': {k: len(v) for k, v in targets.items()},
        'citations': [{k: r[k] for k in ('id', 'source', 'discovery_ids')} for r in rows],
        'modified_maps': {r['use']: r['character_map'] for rows_ in selection.values() for r in rows_
                          if r['character_map'] != [{'start': 0, 'end': len(r['raw_source']['quote']),
                              'operation': 'Text', 'source': r['raw_source']}]}})
    actual = service.consume(p, ROOT, mode='frozen')
    assert digest(actual) == digest(old_answer)
    save(PREP / 'positive-consumer.json', {'status': 'PASS', 'answer_sha256': digest(actual),
        'products_sha256': digest(p)})
    controls = []
    for case in ('roots', 'reachable', 'unresolved'):
        began = time.monotonic()
        semantic = deepcopy(p['P3']['payload'])
        closure = next(d for d in semantic['dependencies'] if d['id'] == 'reference-closure:Q1')
        if case in ('roots', 'reachable'):
            closure[case] = closure[case][1:]
        else:
            victim = next(s for s in closure[case] if not s.startswith('Unresolved reference: reviewed-reference:'))
            closure[case].remove(victim)
        forged = reseal(p, semantic)
        answer = service.consume(forged, ROOT, mode='frozen')
        save(PREP / ('accepted-' + case + '.json'), {'status': 'ACCEPTED_INCONSISTENT_CLOSURE',
            'case': case, 'before_sha256': digest(p['P3']['payload']), 'after_sha256': digest(semantic),
            'ordinary_answer_sha256': digest(answer), 'changed_closure': closure,
            'wall_seconds': time.monotonic() - began})
        controls.append(case)
    return {'status': 'PASS', 'source_links': len(rows), 'target_intervals': [len(r['targets']) for r in rows],
        'actual_consumer_gap_reproduced': controls, 'original_inventory_records': 60}


def main():
    began = time.monotonic()
    save(PREP / 'preparation-started.json', {'command': sys.argv, 'stage_bound_seconds': 180,
        'started_at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU; GPU deliberately hidden'})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Internal preparation180s')))
    signal.alarm(180)
    try:
        result = {**prepare(), 'wall_seconds': time.monotonic() - began}
        save(PREP / 'preparation-result.json', result)
        print(json.dumps(result))
    except BaseException as exc:
        save(PREP / 'preparation-failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
