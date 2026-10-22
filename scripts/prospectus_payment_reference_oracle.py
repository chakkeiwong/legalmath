"""Independent source-interval and full-answer checks; no production checker."""
from copy import deepcopy

from scripts.prospectus_margin_preparation import AUTH, ROOT, read, sha
from scripts.prospectus_relative_notices import retained
from scripts.prospectus_typed_delta import equal

PREP = AUTH / 'reviews/basf-payment-references-273'
KEY = 'basf-base-september-2022-exchange'
IDS = ('principal-payment-method', 'interest-payment-method', 'temporary-payment-method')


def expected(p, missing):
    raw = {r['id']: r for r in p['P1']['payload']['graph']['units']}
    selected = {r['unit']: r for r in p['P2']['payload']['assembly']['units']}
    packet = p['P3']['payload']['interpretation_input']['reference_admission']
    review = read(PREP / 'source-review.json')
    for s in review['sources']:
        assert sha(ROOT / s['path']) == s['sha256']
    for name, checksum in review['images'].items():
        assert sha(ROOT / name) == checksum
    # Independently transcribed page114 bounds.35/38 are partial around RMB.
    targets, target_rows = [], []
    for line in (29, 30, 31, 32, 33, 34, 35, 38, 39):
        u = raw[f'{KEY}:p114:l{line}']
        left, right = (0, 46) if line == 35 else (61, 83) if line == 38 else (0, len(u['raw']))
        a = {'unit': u['id'], 'document': u['document'], 'source_sha256': u['source_sha256'],
             'start': left, 'end': right, 'quote': u['raw'][left:right]}
        s = selected[u['id']]
        assert s['role'] == 'OPERATIVE' and s['text'] == a['quote']
        target_rows.append({'source': a, 'use': u['id'], 'language': u['language']})
        targets.append({'unit': u['id'], 'start': 0, 'end': right - left, 'source': a})
    assert selected[f'{KEY}:p114:l36']['role'] == selected[f'{KEY}:p114:l37']['role'] == 'EXCLUDED'
    assert raw[f'{KEY}:p114:l35']['raw'][46:].startswith('[Im Fall')
    assert raw[f'{KEY}:p114:l38']['raw'][60] == ']'
    text = ' '.join(t['source']['quote'] for t in targets)
    assert 'Section 1471' in text and 'Regierungszusammenarbeit' in text
    assert 'Renminbi' not in text and 'USD' not in text
    deps = []
    for identity, line, phrase in zip(IDS, (78, 82, 90), ('Absatzes (2)', 'Absatz (2)', 'Absatz (2)')):
        u = raw[f'{KEY}:p113:l{line}']
        assert u['raw'].count(phrase) == 1 and selected[u['id']]['text'] == u['raw']
        start = u['raw'].index(phrase)
        source = {'unit': u['id'], 'document': u['document'], 'source_sha256': u['source_sha256'],
            'start': start, 'end': start + len(phrase), 'quote': phrase}
        reviewed = next(r for r in review['references'] if r['id'] == identity)
        equal(reviewed['source'], source, 'Independent referring source differs')
        equal(reviewed['targets'], target_rows, 'Independent selected paragraph differs')
        if identity in missing:
            deps.append({'id': 'payment-reference:' + identity, 'questions': ['Q1', 'Q2'],
                'status': 'UNRESOLVED', 'reason': 'The complete selected payment paragraph has no reviewed source link'})
        else:
            deps.append({'id': 'reviewed-reference:' + identity, 'questions': ['Q1', 'Q2'],
                'status': 'RESOLVED', 'source_use': {'unit': u['id'], 'start': start,
                    'end': start + len(phrase), 'source': source}, 'targets': targets,
                'form': 'relative', 'discovery_ids': [], 'authority': source,
                'review': packet['review'], 'automatic_discovery': False})
    return deps


def question_effect(original, missing):
    result = deepcopy(original)
    for q in ('Q1', 'Q2'):
        nodes = [result[q], *result[q].get('subquestions', {}).values()]
        if 'Q3' in result and q in result['Q3'].get('value', {}):
            nodes.append(result['Q3']['value'][q])
        for node in nodes:
            node['unresolved'] = sorted(set(node['unresolved']) | {'payment-reference:' + k for k in missing})
    return result


def verify(p, answer=None, *, missing=()):
    original, baseline_answer = retained('candidate-answer')
    for stage in ('P1', 'P2'):
        equal(p[stage], original[stage], 'Source or construction changed')
    baseline, semantic = original['P3']['payload'], p['P3']['payload']
    owned = {prefix + key for key in IDS for prefix in ('payment-reference:', 'reviewed-reference:')}
    actual = [d for d in semantic['dependencies'] if d['id'] in owned]
    equal(sorted(actual, key=lambda d: d['id']), sorted(expected(p, missing), key=lambda d: d['id']),
          'Independent full payment dependency mismatch')
    equal([d for d in semantic['dependencies'] if d['id'] not in owned], baseline['dependencies'],
          'Existing dependency changed')
    equal(semantic['questions'], question_effect(baseline['questions'], missing), 'Unexpected question effect')
    allowed = {'dependencies', 'questions', 'interpretation_input'}
    equal({k: v for k, v in semantic.items() if k not in allowed},
          {k: v for k, v in baseline.items() if k not in allowed}, 'Existing meaning or scope changed')
    overlay = deepcopy(baseline['interpretation_input'])
    overlay['reference_admission']['references'].extend(
        r for r in read(PREP / 'packet.json')['references'] if r['id'] not in missing)
    equal(semantic['interpretation_input'], overlay, 'Unexpected interpretation input')
    if answer is not None:
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], original[stage]['payload'], 'Law or finance content changed')
        equal(answer['questions'], question_effect(baseline_answer['questions'], missing), 'Ordinary question effect differs')
        allowed = {'questions', 'consumed_products', 'report_sha256', 'payment_method_references'}
        equal({k: v for k, v in answer.items() if k not in allowed},
              {k: v for k, v in baseline_answer.items() if k not in allowed}, 'Unrelated complete answer changed')
        review = read(PREP / 'source-review.json')
        report = answer['payment_method_references']
        equal(report['references'], review['references'], 'Ordinary answer lost complete target')
        equal(report['missing'], list(missing), 'Missing payment report differs')
        equal(report['source_documents'], review['sources'], 'Source identity differs')
        equal(report['source_images'], review['images'], 'Image identity differs')
        assert report['status'] == ('UNREVIEWED' if missing else 'REVIEWED')
        assert report['external_tax_law_application'] == report['actual_payment_compliance'] == 'UNKNOWN'
        assert report['complete_reference_graph'] is False and report['automatic_discovery'] is False
        equal(answer['consumed_products'], {k: v['sha256'] for k, v in p.items()}, 'Wrong consumed products')
    return {'status': 'PASS', 'independent_links': 3, 'target_intervals_each': 9,
        'missing_links': list(missing), 'whole_answer_checked': answer is not None,
        'existing_meanings_unchanged': True, 'complete_reference_graph': False}
