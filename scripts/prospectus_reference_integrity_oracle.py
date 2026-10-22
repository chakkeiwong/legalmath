"""Independent original-ledger mapping and complete ordinary-answer comparisons."""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH, read
from scripts.prospectus_payment_references import retained
from scripts.prospectus_typed_delta import equal

PREP = AUTH / 'reviews/reference-consumer-integrity-274'
MISSING = ('clearing-publication-25', 'clearing-publication-27', 'holding-proof-information')


def mapped(raw, selected, source, use):
    unit = raw[source['unit']]
    assert (source['document'], source['source_sha256']) == (unit['document'], unit['source_sha256'])
    assert unit['raw'][source['start']:source['end']] == source['quote']
    row = selected[use]
    assert row['role'] == 'OPERATIVE'
    maps = row.get('character_map')
    if maps is None:
        assert row['text'] == unit['raw'] and use == source['unit']
        return {'unit': use, 'start': source['start'], 'end': source['end'], 'source': source}
    hits = []
    for piece in maps:
        if piece.get('operation') not in ('Text', 'Field'):
            continue
        origin = piece.get('source')
        if origin is None:
            u = raw[piece['unit']]
            origin = {'unit': u['id'], 'document': u['document'], 'source_sha256': u['source_sha256'],
                'start': piece['source_start'], 'end': piece['source_end']}
        if (origin['unit'], origin['document'], origin['source_sha256']) != (source['unit'], source['document'], source['source_sha256']):
            continue
        left, right = max(origin['start'], source['start']), min(origin['end'], source['end'])
        if left < right:
            offset = piece['start'] + left - origin['start']
            assert row['text'][offset:offset+right-left] == unit['raw'][left:right]
            hits.append((left, right, offset, offset+right-left))
    hits.sort()
    assert hits and hits[0][0] == source['start'] and hits[-1][1] == source['end']
    assert all(a[1] == b[0] and a[3] == b[2] for a, b in zip(hits, hits[1:]))
    return {'unit': use, 'start': hits[0][2], 'end': hits[-1][3], 'source': source}


def original_dependencies(p):
    raw = {u['id']: u for u in p['P1']['payload']['graph']['units']}
    selected = {u['unit']: u for u in p['P2']['payload']['assembly']['units']}
    ledger = read(AUTH / 'attempts/basf-references/attempt-001/reference-ledger.json')
    originals = ledger['historical_candidate_lines'] + ledger['additional_explicit_review_findings']
    rows = read(PREP / 'source-review.json')['references']
    packet = p['P3']['payload']['interpretation_input']['reference_admission']
    result = []
    for row in rows:
        original = next(r for r in originals if r.get('reviewed_reference', r.get('id')) == row['id'])
        source = original.get('admitted_source')
        if source is None:
            assert original['id'] == 'holding-proof-information'
            full = original['sources'][0]
            quote = 'vorstehend unter (a) und (b)'
            start = full['start'] + full['quote'].index(quote)
            source = {**full, 'start': start, 'end': start + len(quote), 'quote': quote}
        equal(row['source'], source, 'Source differs from original ledger')
        equal(row['targets'], original['exact_targets'], 'Targets differ from original ledger')
        result.append({'id': 'reviewed-reference:' + row['id'], 'questions': ['Q1', 'Q2'],
            'status': 'RESOLVED', 'source_use': mapped(raw, selected, source, row['from_use']),
            'targets': [mapped(raw, selected, t['source'], t['use']) for t in original['exact_targets']],
            'form': row['form'], 'discovery_ids': row['discovery_ids'], 'authority': row['authority'],
            'review': packet['review'], 'automatic_discovery': False})
    return result


def questions(original, missing):
    result = deepcopy(original)
    for q in ('Q1', 'Q2'):
        nodes = [result[q], *result[q].get('subquestions', {}).values()]
        if 'Q3' in result and q in result['Q3'].get('value', {}):
            nodes.append(result['Q3']['value'][q])
        for node in nodes:
            node['unresolved'] = sorted(set(node['unresolved']) | {'legacy-reference:' + k for k in missing})
    return result


def verify(p, answer=None, *, missing=()):
    before, before_answer = retained('candidate-answer')
    for stage in ('P1', 'P2'):
        equal(p[stage], before[stage], 'Original source/construction changed')
    original = original_dependencies(p)
    for dep in original:
        equal(next(d for d in before['P3']['payload']['dependencies'] if d['id'] == dep['id']), dep,
              'Historical dependency fails independent original-ledger reconstruction')
    old, got = before['P3']['payload'], p['P3']['payload']
    expected = [d for d in old['dependencies'] if d['id'] not in {'reviewed-reference:' + k for k in missing}]
    expected.extend({'id': 'legacy-reference:' + k, 'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED',
        'reason': 'An original reviewed reference lacks its complete source-bound target'} for k in missing)
    equal(sorted(got['dependencies'], key=lambda d: d['id']), sorted(expected, key=lambda d: d['id']), 'Complete dependency mismatch')
    equal(got['questions'], questions(old['questions'], missing), 'Unexpected semantic question change')
    expected_input = deepcopy(old['interpretation_input'])
    expected_input['reference_admission']['references'] = [r for r in expected_input['reference_admission']['references'] if r['id'] not in missing]
    equal(got['interpretation_input'], expected_input, 'Unexpected source review input')
    allowed = {'dependencies', 'questions', 'interpretation_input'}
    equal({k:v for k,v in got.items() if k not in allowed}, {k:v for k,v in old.items() if k not in allowed}, 'Existing semantic content changed')
    if answer is not None:
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], before[stage]['payload'], 'Financial/legal content changed')
        equal(answer['questions'], questions(before_answer['questions'], missing), 'Complete ordinary question difference')
        allowed = {'questions', 'consumed_products', 'report_sha256', 'original_reference_review'}
        equal({k:v for k,v in answer.items() if k not in allowed}, {k:v for k,v in before_answer.items() if k not in allowed}, 'Unrelated ordinary answer changed')
        review = answer['original_reference_review']
        equal(review['references'], read(PREP/'source-review.json')['references'], 'Ordinary original source targets changed')
        equal(review['missing'], list(missing), 'Missing original links differ')
        assert review['status'] == ('UNREVIEWED' if missing else 'REVIEWED')
        assert review['actual_compliance'] == 'UNKNOWN' and not review['complete_reference_graph']
        equal(answer['consumed_products'], {k:v['sha256'] for k,v in p.items()}, 'Wrong actual consumed products')
    return {'status': 'PASS', 'original_references_independently_checked': 20,
        'missing': list(missing), 'complete_answer_checked': answer is not None, 'whole_task_complete': False}
