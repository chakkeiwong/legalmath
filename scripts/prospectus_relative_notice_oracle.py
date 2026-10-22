"""Independent original-page and whole-answer checks for the two local links.

This module does not import the production boundary or admission implementation.
"""
from copy import deepcopy

from scripts.prospectus_margin_preparation import AUTH, ROOT, DONOR, read, sha, products
from scripts.prospectus_typed_delta import equal

PREP = AUTH / 'reviews/basf-relative-notices-270'
KEY = 'basf-base-september-2022-exchange'
IDS = ('par-call-notice', 'early-call-notice')


def expected(p, missing):
    graph = p['P1']['payload']['graph']
    raw = {r['id']: r for r in graph['units']}
    selected = {r['unit']: r for r in p['P2']['payload']['assembly']['units']}
    packet = p['P3']['payload']['interpretation_input']['reference_admission']
    review = read(PREP / 'source-review.json')
    for source in review['sources']:
        assert sha(ROOT / source['path']) == source['sha256']
    for name, checksum in review['images'].items():
        assert sha(ROOT / name) == checksum
    result = []
    for identity, line, page, first, last in (
            (IDS[0], 23, 120, 51, 66), (IDS[1], 91, 121, 8, 21)):
        reviewed = next(r for r in review['references'] if r['id'] == identity)
        referring = raw[f'{KEY}:p120:l{line}']
        text = referring['raw']
        assert text.count('Absatz (b)') == 1
        start = text.index('Absatz (b)')
        anchor = {'unit': referring['id'], 'document': referring['document'],
            'source_sha256': referring['source_sha256'], 'start': start,
            'end': start + 10, 'quote': 'Absatz (b)'}
        equal(anchor, reviewed['source'], 'Independent referring span differs')
        assert selected[referring['id']]['text'] == text
        targets, target_rows = [], []
        for n in range(first, last + 1):
            u = raw[f'{KEY}:p{page}:l{n}']
            s = selected[u['id']]
            assert s['text'] == u['raw'] and s['role'] == 'OPERATIVE'
            a = {'unit': u['id'], 'document': u['document'], 'source_sha256': u['source_sha256'],
                 'start': 0, 'end': len(u['raw']), 'quote': u['raw']}
            target_rows.append({'source': a, 'use': u['id'], 'language': u['language']})
            targets.append({'unit': u['id'], 'start': 0, 'end': len(u['raw']), 'source': a})
        equal(target_rows, reviewed['targets'], 'Independent complete (b) differs')
        assert raw[f'{KEY}:p{page}:l{last + 1}']['raw'].startswith('(c)')
        if identity in missing:
            result.append({'id': 'relative-notice:' + identity, 'questions': ['Q1', 'Q2'],
                'status': 'UNRESOLVED', 'reason': 'The complete local notice paragraph has no reviewed source link'})
        else:
            result.append({'id': 'reviewed-reference:' + identity, 'questions': ['Q1', 'Q2'],
                'status': 'RESOLVED', 'source_use': {'unit': referring['id'],
                    'start': start, 'end': start + 10, 'source': anchor},
                'targets': targets, 'form': 'relative', 'discovery_ids': [],
                'authority': anchor, 'review': packet['review'], 'automatic_discovery': False})
    return result


def question_effect(original, missing, *, ordinary=False):
    want = deepcopy(original)
    for q in ('Q1', 'Q2'):
        nodes = [want[q], *want[q].get('subquestions', {}).values()]
        if 'Q3' in want and q in want['Q3'].get('value', {}):
            nodes.append(want['Q3']['value'][q])
        for node in nodes:
            node['unresolved'] = sorted(set(node['unresolved']) | {'relative-notice:' + k for k in missing})
    return want


def verify(p, answer=None, *, missing=()):
    original = products()
    for stage in ('P1', 'P2'):
        equal(p[stage], original[stage], 'Source/construction changed')
    baseline = original['P3']['payload']
    semantic = p['P3']['payload']
    owned = {prefix + key for key in IDS for prefix in ('relative-notice:', 'reviewed-reference:')}
    actual = [d for d in semantic['dependencies'] if d['id'] in owned]
    equal(sorted(actual, key=lambda d: d['id']), sorted(expected(p, missing), key=lambda d: d['id']),
          'Independent full dependency mismatch')
    equal([d for d in semantic['dependencies'] if d['id'] not in owned], baseline['dependencies'],
          'Unrelated reference/governing dependency changed')
    equal(semantic['questions'], question_effect(baseline['questions'], missing), 'Unexpected semantic question change')
    excluded = {'dependencies', 'questions', 'interpretation_input'}
    equal({k: v for k, v in semantic.items() if k not in excluded},
          {k: v for k, v in baseline.items() if k not in excluded}, 'Existing meaning/scope changed')
    overlay = deepcopy(baseline['interpretation_input'])
    packet = deepcopy(original['P1']['payload']['request']['reference_admission'])
    packet['references'].extend(r for r in read(PREP / 'packet.json')['references'] if r['id'] not in missing)
    overlay['reference_admission'] = packet
    equal(semantic['interpretation_input'], overlay, 'Unexpected interpretation input')
    if answer is not None:
        from scripts.prospectus_typed_delta import apply
        before = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
        retained_margin = read(AUTH / 'attempts/basf-margins/attempt-004/baseline.json.gz')
        old = apply(before, retained_margin['answer_delta'])
        equal(answer['questions'], question_effect(old['questions'], missing, ordinary=True),
              'Unexpected complete answer question effect')
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], original[stage]['payload'], 'Law/financial content changed')
        allowed = {'questions', 'consumed_products', 'report_sha256', 'relative_call_notices'}
        equal({k: v for k, v in answer.items() if k not in allowed},
              {k: v for k, v in old.items() if k not in allowed}, 'Unrelated complete answer changed')
        report = answer['relative_call_notices']
        review = read(PREP / 'source-review.json')
        equal(report['references'], review['references'], 'Ordinary answer lost exact reference extent')
        equal(report['missing'], list(missing), 'Ordinary missing-link report differs')
        assert report['status'] == ('UNREVIEWED' if missing else 'REVIEWED')
        assert report['actual_notice_compliance'] == 'UNKNOWN' and not report['complete_reference_graph']
        equal(answer['consumed_products'], {k: v['sha256'] for k, v in p.items()}, 'Consumed wrong products')
    return {'status': 'PASS', 'independently_checked_links': 2, 'target_lines': [16, 14],
            'missing_links': list(missing), 'whole_answer_checked': answer is not None,
            'existing_meanings_unchanged': True, 'complete_reference_graph': False}
