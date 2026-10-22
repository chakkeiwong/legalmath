"""Bounded source preparation; preserve heterogeneous historical provenance."""
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
from scripts.prospectus_relative_notices import retained
from legalmath.prospectus.successor.anchors import bind
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, segments, _DependencyLookup

PREP = AUTH / 'reviews/basf-payment-references-273'
SPEC = ROOT / 'src/legalmath/prospectus/successor/basf_payment_references_spec.json'
KEY = 'basf-base-september-2022-exchange'
IDS = ('principal-payment-method', 'interest-payment-method', 'temporary-payment-method')


def reconcile(p, new_rows=()):
    """Reconcile every original record; no marker count is a recall denominator."""
    original = read(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json')
    raw = {u['id']: u for u in p['P1']['payload']['graph']['units']}
    selected = {u['unit']: u for u in p['P2']['payload']['assembly']['units']}
    refs = p['P3']['payload']['interpretation_input']['reference_admission']['references']
    current = {r['id']: r for r in [*refs, *new_rows]}
    records = []
    for family, field in (('historical_candidate_lines', 'source_pieces'),
                           ('additional_explicit_review_findings', 'sources')):
        for i, row in enumerate(original[family]):
            pieces = []
            for piece in row[field]:
                if set(piece) == {'substitution_basis'}:
                    basis = piece['substitution_basis']
                    if 'unit' in basis:
                        bind({'units': [raw[basis['unit']]]}, basis)
                        evidence = {'kind': 'SCALAR_ANCHOR', 'source_checked': True}
                    else:
                        assert sha(ROOT / basis['original']) == basis['source_sha256']
                        assert sha(ROOT / basis['text']) == basis['text_sha256']
                        evidence = {'kind': 'SCALAR_EXTRACTION_PROVENANCE', 'source_checked': True,
                            'original_and_extraction_hashes_verified': True,
                            'legacy_excerpt_offsets_reinterpreted': False}
                    pieces.append({'original': deepcopy(piece), **evidence})
                else:
                    bind({'units': [raw[piece['unit']]]}, piece)
                    pieces.append({'original': deepcopy(piece), 'kind': 'RAW_ANCHOR',
                        'source_checked': True, 'current_selection': deepcopy(selected.get(piece['unit']))})
            identity = row.get('reviewed_reference')
            if family == 'historical_candidate_lines' and i in (19, 21):
                identity = {19: 'par-call-notice', 21: 'early-call-notice'}[i]
            if family == 'historical_candidate_lines' and i in (5, 6, 7) and IDS[i - 5] in current:
                identity = IDS[i - 5]
            if family == 'additional_explicit_review_findings' and row['id'] == 'holding-proof-information':
                identity = 'holding-proof-information'
            current_row = current.get(identity)
            # A matched edge is evidence of mapping, not proof that all words in
            # a mixed statutory/contractual record have been interpreted.
            status = 'CURRENT_REVIEWED_LINK' if current_row else row['status']
            if row['status'] == 'MIXED_ADDED_AND_EXTERNAL_MISSING':
                status = 'CURRENT_LINK_AND_EXTERNAL_SOURCE_MISSING'
            records.append({'family': family, 'index': i, 'original': deepcopy(row),
                'source_pieces': pieces, 'current_status': status,
                'current_reference': deepcopy(current_row),
                'original_target_unchanged': (row['exact_targets'] == current_row['targets']
                    if current_row and 'exact_targets' in row else None),
                'complete_legal_interpretation': False})
    assert len(records) == 60
    for family in ('historical_candidate_lines', 'additional_explicit_review_findings'):
        assert [r['original'] for r in records if r['family'] == family] == original[family]
    assert sum(s['kind'].startswith('SCALAR_') for r in records for s in r['source_pieces']) == 2
    return {'version': 'basf-reference-reconciliation.v1', 'records': records,
        'original_inventory_sha256': sha(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json'),
        'historical_records': 47, 'additional_records': 13, 'scalar_provenance_records': 2,
        'all_original_records_preserved': True, 'counts_are_not_recall': True,
        'remaining': original['remaining'], 'complete_reference_graph': False}


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH / 'program.json')['revision'] == 272
    p, answer = retained('candidate-answer')
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {u['id']: u for u in graph['units']}
    selected = {u['unit']: u for u in assembly['units']}
    targets, selection = [], []
    for n in range(29, 40):
        u = raw[f'{KEY}:p114:l{n}']
        s = selected[u['id']]
        parts = segments(graph, s, _raw=raw)
        selection.append({'raw_source': anchor(u), 'use': u['id'], 'role': s['role'],
            'questions': s['questions'], 'text': s['text'], 'segments': parts})
        if n in (36, 37):
            assert s['role'] == 'EXCLUDED' and s['text'] == '' and not parts
            continue
        assert s['role'] == 'OPERATIVE' and len(parts) == 1
        start, end = 0, len(u['raw'])
        if n == 35:
            end = u['raw'].index('[Im Fall')
        elif n == 38:
            start = u['raw'].index(']') + 1
        want = anchor(u, start, end)
        assert parts == [{'source': want, 'start': 0, 'end': len(want['quote'])}]
        assert s['text'] == want['quote']
        targets.append({'source': want, 'use': u['id'], 'language': u['language']})
    assert len(targets) == 9
    rows = []
    for identity, line, phrase in zip(IDS, (78, 82, 90), ('Absatzes (2)', 'Absatz (2)', 'Absatz (2)')):
        u = raw[f'{KEY}:p113:l{line}']
        assert u['raw'].count(phrase) == 1
        start = u['raw'].index(phrase)
        source = anchor(u, start, start + len(phrase))
        rows.append({'id': identity, 'form': 'relative', 'source': source,
            'from_use': u['id'], 'language': u['language'], 'targets': deepcopy(targets),
            'authority': source, 'questions': ['Q1', 'Q2'], 'discovery_ids': [],
            'reason': 'Original section4(2): complete selected payment paragraph including tax qualifications; renminbi branch excluded by the supplied final terms. Actual payment and external tax-law application remain unknown.'})
        assert not any(r['unit'] == u['id'] and start <= r['start'] < r['end'] <= source['end']
                       for r in graph['references'])
    packet = {'version': 'reviewed-references.v2', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'Codex original pages113-114', 'kind': 'DEVELOPMENT',
            'reason': 'Three exact payment-method references under supplied final terms'}, 'references': rows}
    malformed = deepcopy(packet)
    wrong = raw[f'{KEY}:p114:l39']
    malformed['references'][0]['targets'] = [{'source': anchor(wrong), 'use': wrong['id'], 'language': wrong['language']}]
    dependencies, _ = admit(graph, assembly, malformed, _lookup=_DependencyLookup(graph, assembly))
    assert all(d['status'] == 'RESOLVED' for d in dependencies)
    printed = read(ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    images = {k: v for k, v in printed['images'].items() if k.endswith(('base-113.png', 'base-114.png'))}
    assert len(images) == 2
    for name, value in images.items():
        assert sha(ROOT / name) == value
    sources = [{k: d[k] for k in ('id', 'path', 'sha256')}
               for d in p['P1']['payload']['request']['bundle']['documents'] if d['id'] in (KEY, 'basf-2032-final')]
    for s in sources:
        assert sha(ROOT / s['path']) == s['sha256']
    spec = {'version': 'basf-payment-references.v1', 'sources': sources, 'references': rows,
        'target_selection': selection, 'images': images,
        'boundary_review': 'Original4(2) spans114:29-39; excluded RMB text splits35/38 and excludes36/37',
        'automatic_discovery': False}
    save(PREP / 'source-review.json', spec)
    save(SPEC, spec)
    save(PREP / 'packet.json', packet)
    save(PREP / 'reconciliation-before.json.gz', reconcile(p))
    save(PREP / 'reconciliation-proposed.json.gz', reconcile(p, rows))
    save(PREP / 'pre-repair.json', {'missing_links': list(IDS),
        'generic_truncated_target_status': dependencies[0]['status'],
        'lost_qualifications': 'All of section4(2) except the last currency sentence',
        'raw_whole_paragraph_wrong': True, 'selected_target_intervals': 9,
        'baseline_products_sha256': digest(p), 'baseline_answer_sha256': digest(answer)})
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py',
                 'src/legalmath/prospectus/successor/service.py'):
        dst = PREP / 'pre-edit' / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT / name).read_bytes())
    return {'status': 'PASS', 'reconciled_original_records': 60, 'scalar_records_preserved': 2,
        'new_links': 3, 'target_intervals': 9, 'pre_repair_truncation_accepted': True}


def main():
    began = time.monotonic()
    save(PREP / 'preparation-started.json', {'command': sys.argv, 'stage_bound_seconds': 90,
        'started_at': datetime.now(timezone.utc).isoformat(), 'cpu': 'GPU deliberately hidden'})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Source preparation90s')))
    signal.alarm(90)
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
