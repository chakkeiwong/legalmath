"""Retain original financial-reference targets before source checks change."""
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
from scripts.prospectus_substitution_references import retained
from legalmath.prospectus.successor.occurrences import anchor, segments, _DependencyLookup
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/financial-references-278'
SPEC = ROOT / 'src/legalmath/prospectus/successor/basf_financial_references_spec.json'
KEY = 'basf-base-september-2022-exchange'
IDS = ('maturity-section', 'maturity-paragraph', 'coupon-payment-date',
       'day-count-forward-definition', 'tax-call-forward-amount')
GROUPS = dict(zip(IDS, ('maturity', 'maturity', 'coupon', 'day-count', 'tax-amount')))
LEDGER = (('historical_candidate_lines', 3), ('historical_candidate_lines', 4),
          ('historical_candidate_lines', 12), ('additional_explicit_review_findings', 0),
          ('additional_explicit_review_findings', 1))


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH / 'program.json')['revision'] == 277
    p, answer = retained('candidate-answer')
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {u['id']: u for u in graph['units']}
    selected = {u['unit']: u for u in assembly['units']}

    def unit(page, line):
        return raw[f'{KEY}:p{page}:l{line}']

    def destinations(locations):
        result = []
        for page, line in locations:
            u = unit(page, line)
            result.extend({'source': s['source'], 'use': u['id'],
                           'language': raw[s['source']['unit']]['language']}
                          for s in segments(graph, selected[u['id']], _raw=raw))
        return result

    targets = {
        'maturity': destinations((118, n) for n in (17, 18, 20, 21, 22, 23)),
        'coupon': destinations((111, n) for n in (24, 33, 34, 35, 36, 37, 58)),
        'day-count': destinations((112, n) for n in (1, 2, 3, 18, 19)),
        'tax-amount': destinations((123, n) for n in (35, 36, 37)),
    }
    rows = []
    for identity, page, line, phrase in (
        (IDS[0], 111, 34, '§ 5'), (IDS[1], 111, 35, 'Absatz (1)'),
        (IDS[2], 118, 49, '§ 3 Absatz (1)'),
        (IDS[3], 111, 77, 'Zinstagequotienten (wie nachstehend definiert)'),
        (IDS[4], 118, 35, 'vorzeitigen Rückzahlungsbetrag (wie nachstehend definiert)')):
        u = unit(page, line)
        assert u['raw'].count(phrase) == 1
        left = u['raw'].index(phrase)
        source = anchor(u, left, left + len(phrase))
        discoveries = [r['id'] for r in graph['references'] if r['unit'] == u['id']
                       and left <= r['start'] < r['end'] <= left + len(phrase)]
        assert len(discoveries) == (1 if identity in (IDS[0], IDS[2]) else 0)
        rows.append({'id': identity, 'form': 'relative', 'source': source,
                     'from_use': u['id'], 'language': u['language'],
                     'targets': targets[GROUPS[identity]], 'authority': source,
                     'questions': ['Q1', 'Q2'], 'discovery_ids': discoveries,
                     'reason': 'Complete original selected financial definition; actual payment and legal application remain unknown.'})
    packet = {'version': 'reviewed-references.v3', 'assembly_sha256': digest(assembly),
              'review': {'reviewer': 'Codex original pages111-113,118,123 and final4-5',
                         'kind': 'DEVELOPMENT', 'reason': 'Complete selected maturity, coupon, day-count and tax-amount targets'},
              'references': rows}
    malformed = deepcopy(packet)
    for row in malformed['references']:
        row['targets'] = [row['targets'][-1]]
    deps, _ = admit(graph, assembly, malformed, _lookup=_DependencyLookup(graph, assembly))
    assert len(deps) == 5 and all(d['status'] == 'RESOLVED' for d in deps)
    pair_only = {**packet, 'references': [rows[0]]}
    pair_deps, _ = admit(graph, assembly, pair_only, _lookup=_DependencyLookup(graph, assembly))
    assert pair_deps[0]['status'] == 'RESOLVED'

    ranges = {'maturity': ((118, 17, 23),), 'coupon': ((111, 24, 70),),
              'day-count': ((112, 1, 87), (113, 1, 48)),
              'tax-amount': ((123, 35, 50),)}
    selection = {}
    for group, spans in ranges.items():
        selection[group] = []
        for page, first, last in spans:
            for line in range(first, last + 1):
                u = unit(page, line)
                s = selected[u['id']]
                selection[group].append({'raw_source': anchor(u), 'use': u['id'],
                    'role': s['role'], 'questions': s['questions'], 'text': s['text'],
                    'character_map': s.get('character_map'),
                    'segments': segments(graph, s, _raw=raw)})
    printed = read(ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    images = {k: v for k, v in printed['images'].items() if k.endswith((
        'base-111.png', 'base-112.png', 'base-113.png', 'base-118.png', 'base-123.png',
        'final-4.png', 'final-5.png'))}
    assert len(images) == 7
    for path, checksum in images.items():
        assert sha(ROOT / path) == checksum
    for source in printed['sources']:
        assert sha(ROOT / source['path']) == source['sha256']
    contexts = [anchor(unit(page, line)) for page, line in (
        (111, 33), (111, 34), (111, 35), (111, 36), (111, 77),
        (118, 34), (118, 35), (118, 49), (123, 35))]
    spec = {'version': 'basf-financial-references.v1', 'sources': printed['sources'],
            'references': rows, 'groups': GROUPS, 'selection': selection,
            'paired_citation': list(IDS[:2]), 'contexts': contexts, 'images': images,
            'automatic_discovery': False}
    save(PREP / 'source-review.json', spec)
    save(SPEC, spec)
    save(PREP / 'packet.json', packet)
    ledger = read(AUTH / 'attempts/basf-references/attempt-018/candidate-answer-reconciliation.json.gz')
    for (family, index), row in zip(LEDGER, rows):
        record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
        assert record['current_reference'] is None
        record['current_reference'] = row
        record['current_status'] = ('CURRENT_LINK_AND_UNRESOLVED_TARGET_MEANING'
                                    if row['id'] == IDS[2] else 'CURRENT_REVIEWED_LINK')
    save(PREP / 'reconciliation-proposed.json.gz', ledger)
    save(PREP / 'pre-repair.json', {'truncated_statuses': [d['status'] for d in deps],
        'unpaired_maturity_status': pair_deps[0]['status'],
        'lost_qualifications_dates_formula_and_amount': True,
        'baseline_products_sha256': digest(p), 'baseline_answer_sha256': digest(answer)})
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py',
                 'src/legalmath/prospectus/successor/service.py'):
        target = PREP / 'pre-edit' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    return {'status': 'PASS', 'new_source_links': 5,
            'target_intervals': [len(r['targets']) for r in rows],
            'generic_truncation_and_unpaired_citation_accepted': True,
            'original_inventory_records': 60}


def main():
    began = time.monotonic()
    save(PREP / 'preparation-started.json', {'command': sys.argv, 'stage_bound_seconds': 90,
        'started_at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU; GPU deliberately hidden'})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Financial preparation90s')))
    signal.alarm(90)
    try:
        result = {**prepare(), 'wall_seconds': time.monotonic() - began}
        save(PREP / 'preparation-result.json', result)
        print(json.dumps(result))
    except BaseException as exc:
        save(PREP / 'preparation-failure.json', {'type': type(exc).__name__,
             'message': str(exc), 'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
