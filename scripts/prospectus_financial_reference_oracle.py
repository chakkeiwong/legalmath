"""Independent original financial targets, scalar maps and whole-answer oracle."""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH, ROOT, read, sha
from scripts.prospectus_substitution_references import retained
from scripts.prospectus_typed_delta import equal
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/financial-references-278'
KEY = 'basf-base-september-2022-exchange'
IDS = ('maturity-section', 'maturity-paragraph', 'coupon-payment-date',
       'day-count-forward-definition', 'tax-call-forward-amount')
REPLACED = {
    IDS[0]: KEY + ':p111:l34:ref:81@' + KEY + ':p111:l34',
    IDS[2]: KEY + ':p118:l49:ref:24@' + KEY + ':p118:l49',
}


def originals(p):
    """Endpoints are transcribed from originals, never from the production spec."""
    raw = {u['id']: u for u in p['P1']['payload']['graph']['units']}
    selected = {u['unit']: u for u in p['P2']['payload']['assembly']['units']}

    def source(key, left=0, right=None):
        u = raw[key]
        right = len(u['raw']) if right is None else right
        return {'unit': key, 'document': u['document'], 'source_sha256': u['source_sha256'],
                'start': left, 'end': right, 'quote': u['raw'][left:right]}

    def key(page, line):
        return f'{KEY}:p{page}:l{line}'

    maps = {
        key(118, 18): [(key(118, 18), 0, 43)],
        key(118, 20): [(key(118, 20), 42, 79)],
        key(118, 21): [(key(118, 21), 0, 28), ('basf-2032-final:p5:l48', 0, 12), (key(118, 21), 44, 82)],
        key(111, 33): [(key(111, 33), 1, 78)],
        key(111, 34): [(key(111, 34), 0, 13), ('basf-2032-final:p4:l58', 0, 12), (key(111, 34), 32, 84)],
        key(111, 35): [(key(111, 35), 0, 52), ('basf-2032-final:p4:l6', 0, 5), (key(111, 35), 62, 80)],
        key(111, 36): [(key(111, 36), 0, 16), ('basf-2032-final:p4:l60', 0, 7), (key(111, 36), 35, 75)],
        key(111, 37): [(key(111, 37), 0, 19)],
        key(111, 58): [(key(111, 58), 0, 33), ('basf-2032-final:p4:l62', 0, 12), (key(111, 58), 57, 58)],
        key(112, 18): [(key(112, 18), 1, 80)],
        key(112, 19): [(key(112, 19), 0, 60)],
        key(123, 35): [(key(123, 35), 0, 77)],
        key(123, 36): [(key(123, 36), 6, 69)],
    }
    scalars = {
        key(111, 35): '61debb0ba17f4abfa28bc42ac760ca9a89c44919d1c4711d73acf368fff9ba93',
        key(111, 58): '4d87e146483d67407493e342a3ae97ee33480861ca5244a2a05beed38f88f39e',
    }
    groups = {
        'maturity': [(118, n) for n in (17, 18, 20, 21, 22, 23)],
        'coupon': [(111, n) for n in (24, 33, 34, 35, 36, 37, 58)],
        'day-count': [(112, n) for n in (1, 2, 3, 18, 19)],
        'tax-amount': [(123, n) for n in (35, 36, 37)],
    }
    targets, destinations = {}, {}
    for group, locations in groups.items():
        targets[group], destinations[group] = [], []
        for page, line in locations:
            use = key(page, line)
            intervals = maps.get(use, [(use, 0, len(raw[use]['raw']))])
            offset, cm, text = 0, [], ''
            for origin, first, last in intervals:
                a = source(origin, first, last)
                item = {'start': offset, 'end': offset + len(a['quote']),
                        'operation': 'Text' if origin == use else 'Field', 'source': a}
                if use in scalars and origin != use:
                    item['scalar_operation_sha256'] = scalars[use]
                cm.append(item)
                destinations[group].append({'unit': use, 'start': offset,
                    'end': offset + len(a['quote']), 'source': a})
                targets[group].append({'source': a, 'use': use, 'language': raw[origin]['language']})
                text += a['quote']
                offset += len(a['quote'])
            equal(selected[use]['character_map'], cm, 'Original scalar character map differs')
            equal(selected[use]['text'], text, 'Original selected financial text differs')
            equal(selected[use]['role'], 'UNKNOWN' if (page, line) == (111, 24) else 'OPERATIVE',
                  'Original target role differs')
            equal(selected[use]['questions'], ['Q1', 'Q2'], 'Original target questions differ')
    rows = []
    for identity, page, line, left, right, phrase, group, discovery in (
        (IDS[0], 111, 34, 81, 84, '§ 5', 'maturity', KEY + ':p111:l34:ref:81'),
        (IDS[1], 111, 35, 0, 10, 'Absatz (1)', 'maturity', None),
        (IDS[2], 118, 49, 24, 38, '§ 3 Absatz (1)', 'coupon', KEY + ':p118:l49:ref:24'),
        (IDS[3], 111, 77, 18, 64, 'Zinstagequotienten (wie nachstehend definiert)', 'day-count', None),
        (IDS[4], 118, 35, 23, 81, 'vorzeitigen Rückzahlungsbetrag (wie nachstehend definiert)', 'tax-amount', None)):
        a = source(key(page, line), left, right)
        assert a['quote'] == phrase
        rows.append({'id': identity, 'form': 'relative', 'source': a, 'from_use': a['unit'],
            'language': raw[a['unit']]['language'], 'targets': targets[group], 'authority': a,
            'questions': ['Q1', 'Q2'], 'discovery_ids': [discovery] if discovery else [],
            'reason': 'Complete original selected financial definition; actual payment and legal application remain unknown.'})
    review = read(PREP / 'source-review.json')
    for s in review['sources']:
        assert sha(ROOT / s['path']) == s['sha256']
    for path, checksum in review['images'].items():
        assert sha(ROOT / path) == checksum
    equal(review['references'], rows, 'Source specification differs from independently read originals')
    # Cross-page exception excludes the complete reference-period/stub branch.
    assert all(selected[key(112, n)]['role'] == 'EXCLUDED' for n in range(69, 78))
    assert all(selected[key(113, n)]['role'] == 'EXCLUDED' for n in range(13, 19))
    assert selected[key(118, 19)]['role'] == 'EXCLUDED'
    assert all(selected[key(111, n)]['role'] == 'EXCLUDED' for n in range(46, 58))
    assert selected[key(111, 61)]['role'] == 'EXCLUDED' and selected[key(111, 61)]['text'] == ' '
    assert 'Soweit nicht zuvor' in selected[key(118, 17)]['text']
    assert 'Nennbetrag' in selected[key(118, 23)]['text']
    return rows, destinations, review


def expected(p, missing):
    rows, targets, review = originals(p)
    packet = p['P3']['payload']['interpretation_input']['reference_admission']
    deps = []
    for row, group in zip(rows, ('maturity', 'maturity', 'coupon', 'day-count', 'tax-amount')):
        identity = row['id']
        if identity in missing:
            deps.append({'id': 'financial-reference:' + identity, 'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED',
                         'reason': 'The complete selected financial definition has no reviewed source link'})
            continue
        # Source-use coordinates include the selected final-term date replacement.
        offsets = (74, 77) if identity == IDS[0] else (row['source']['start'], row['source']['end'])
        unknown = [KEY + ':p111:l24'] if group == 'coupon' else []
        deps.append({'id': 'reviewed-reference:' + identity, 'questions': ['Q1', 'Q2'],
            'status': 'UNRESOLVED' if unknown else 'RESOLVED',
            'source_use': {'unit': row['from_use'], 'start': offsets[0], 'end': offsets[1], 'source': row['source']},
            'targets': targets[group], 'form': 'relative', 'discovery_ids': row['discovery_ids'],
            'authority': row['authority'], 'review': packet['review'], 'automatic_discovery': False,
            **({'source_binding': 'RESOLVED', 'unknown_target_uses': unknown} if unknown else {})})
    return deps, rows, review


def questions(original, extra, missing):
    result = deepcopy(original)
    required = {d['id'] for d in extra if d['status'] == 'UNRESOLVED'}
    replaced = {value for key, value in REPLACED.items() if key not in missing}
    for q in ('Q1', 'Q2'):
        nodes = [result[q], *result[q].get('subquestions', {}).values()]
        if 'Q3' in result and q in result['Q3'].get('value', {}):
            nodes.append(result['Q3']['value'][q])
        for node in nodes:
            node['unresolved'] = sorted((set(node['unresolved']) - replaced) | required)
    return result


def verify(p, answer=None, *, missing=()):
    before, old_answer = retained('candidate-answer')
    for stage in ('P1', 'P2'):
        equal(p[stage], before[stage], 'Source/construction changed')
    old, got = before['P3']['payload'], p['P3']['payload']
    extra, rows, review = expected(p, missing)
    replaced = {value for key, value in REPLACED.items() if key not in missing}
    wanted = deepcopy([d for d in old['dependencies'] if d['id'] not in replaced])
    unknown = {'Unresolved reference: ' + d['id'] for d in extra
               if d['status'] == 'UNRESOLVED' and d.get('source_binding') == 'RESOLVED'}
    for q in ('Q1', 'Q2'):
        closure = next(d for d in wanted if d['id'] == 'reference-closure:' + q)
        closure['unresolved'] = sorted((set(closure['unresolved']) -
            {'Unresolved reference: ' + k for k in replaced}) | unknown)
    wanted += extra
    equal(sorted(got['dependencies'], key=lambda d: d['id']), sorted(wanted, key=lambda d: d['id']),
          'Complete dependencies changed')
    equal(got['questions'], questions(old['questions'], extra, missing), 'Unexpected semantic question change')
    value = deepcopy(old['interpretation_input'])
    value['reference_admission']['version'] = 'reviewed-references.v3'
    value['reference_admission']['references'].extend(r for r in rows if r['id'] not in missing)
    equal(got['interpretation_input'], value, 'Unexpected interpretation input')
    omit = {'dependencies', 'questions', 'interpretation_input'}
    equal({k: v for k, v in got.items() if k not in omit}, {k: v for k, v in old.items() if k not in omit},
          'Existing meaning changed')
    if answer is not None:
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], before[stage]['payload'], 'Legal/financial content changed')
        equal(answer['questions'], questions(old_answer['questions'], extra, missing), 'Unexpected ordinary question change')
        omit = {'questions', 'consumed_products', 'report_sha256', 'financial_references'}
        equal({k: v for k, v in answer.items() if k not in omit},
              {k: v for k, v in old_answer.items() if k not in omit}, 'Unrelated whole answer changed')
        equal(answer['financial_references'], {
            'status': 'UNREVIEWED' if missing else 'REVIEWED', 'references': rows, 'missing': list(missing),
            'source_documents': review['sources'], 'source_images': review['images'],
            'specification_sha256': digest(review), 'automatic_discovery': False,
            'actual_payment_and_tax_call_compliance': 'UNKNOWN', 'complete_reference_graph': False,
            'unknown_target_uses': [KEY + ':p111:l24']}, 'Financial report differs from originals')
        equal(answer['consumed_products'], {k: v['sha256'] for k, v in p.items()}, 'Wrong consumed products')
    return {'status': 'PASS', 'independent_links': 5, 'target_intervals': [8, 8, 15, 5, 3],
            'unknown_target_uses': 1, 'missing': list(missing), 'complete_answer_checked': answer is not None,
            'original_task_complete': False}
