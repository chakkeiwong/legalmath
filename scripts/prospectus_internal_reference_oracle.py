"""Original-page interval transcription and independent complete-closure oracle.

Expected intervals below are transcribed from the retained original reading.
No production validator, target list, occurrence lookup or closure is used.
"""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH, ROOT, read, sha
from scripts.prospectus_financial_references import retained
from scripts.prospectus_typed_delta import equal
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/internal-closure-279'
KEY = 'basf-base-september-2022-exchange'
IDS = ('temporary-global-self-scope', 'payment-additional-amounts', 'tax-call-additional-amounts',
       'holder-option-tax-exception', 'holder-option-self-scope', 'tax-call-reverse-conditions',
       'substitution-whole-scope', 'additional-amounts-backward-scope',
       'substitution-affiliate-definition', 'depository-proof-scope')
GROUPS = ('temporary', 'tax', 'tax', 'tax-call', 'holder', 'tax-call',
          'substitution', 'tax-body', 'affiliate', 'proof')


def originals(p):
    raw = {u['id']: u for u in p['P1']['payload']['graph']['units']}
    selected = {u['unit']: u for u in p['P2']['payload']['assembly']['units']}

    def key(page, line):
        return f'{KEY}:p{page}:l{line}'

    def source(identity, left=0, right=None):
        u = raw[identity]
        right = len(u['raw']) if right is None else right
        return {'unit': identity, 'document': u['document'], 'source_sha256': u['source_sha256'],
                'start': left, 'end': right, 'quote': u['raw'][left:right]}

    places = {
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
    ends = {key(page, line): (left, right) for page, line, left, right in (
        (108, 81, 0, 75), (125, 10, 1, 81), (125, 50, 0, 31),
        (118, 31, 1, 79), (118, 58, 0, 32), (119, 24, 1, 78), (120, 8, 0, 57),
        (128, 56, 1, 88), (128, 61, 0, 33), (129, 12, 1, 86), (129, 22, 0, 62))}
    targets, destinations = {}, {}
    for group, locations in places.items():
        targets[group], destinations[group] = [], []
        for page, line in locations:
            use = key(page, line)
            left, right = ends.get(use, (0, len(raw[use]['raw'])))
            a = source(use, left, right)
            cm = [{'start': 0, 'end': len(a['quote']), 'operation': 'Text', 'source': a}]
            equal(selected[use]['character_map'], cm, 'Original internal character map differs')
            equal(selected[use]['text'], a['quote'], 'Original internal text differs')
            equal(selected[use]['role'], 'UNKNOWN' if (page, line) in ((125, 1), (125, 2)) else 'OPERATIVE',
                  'Original internal role differs')
            equal(selected[use]['questions'], ['Q1', 'Q2'], 'Original internal questions differ')
            equal(raw[use]['language'], 'de/en', 'Original bilingual source tag differs')
            targets[group].append({'source': a, 'use': use, 'language': 'de/en'})
            destinations[group].append({'unit': use, 'start': 0, 'end': len(a['quote']), 'source': a})
    rows = []
    citations = (
        (108, 79, 0, 39, 'diesem Absatz (b) dieses § 1 Absatz (3)', 25),
        (115, 11, 64, 67, '§ 7', 64),
        (118, 50, 17, 39, '§ 7 dieser Bedingungen', 17),
        (119, 29, 5, 19, '§ 5 Absatz (2)', 5),
        (119, 60, 44, 65, 'diesem § 5 Absatz (3)', 51),
        (123, 35, 64, 76, 'Absatzes (2)', None),
        (129, 37, 15, 26, 'dieses § 10', 22),
        (125, 49, 21, 43, 'im oben genannten Sinn', None),
        (128, 58, 42, 76, 'verbundenes Unternehmen (wie unten', None),
        (133, 4, 19, 50, 'Für die Zwecke des Vorstehenden', None))
    for identity, group, (page, line, left, right, phrase, offset) in zip(IDS, GROUPS, citations):
        a = source(key(page, line), left, right)
        equal(a['quote'], phrase, 'Original citation differs')
        rows.append({'id': identity, 'form': 'relative', 'source': a, 'from_use': a['unit'],
            'language': 'de/en', 'targets': targets[group], 'authority': a, 'questions': ['Q1', 'Q2'],
            'discovery_ids': [key(page, line) + ':ref:' + str(offset)] if offset is not None else [],
            'reason': 'Complete selected original internal scope; cyclic support, statutory application and actual events remain unresolved.'})
    # Original issuer alternatives and adjacent UNKNOWN headings stay excluded
    # or uncertain; no truncated target is used to hide a source cycle.
    excluded = [(119, n) for n in range(1, 9)] + [(118, n) for n in range(66, 78)]
    excluded += [(128, n) for n in range(69, 75)] + [(129, n) for n in range(30, 33)]
    assert all(selected[key(page, line)]['role'] == 'EXCLUDED' for page, line in excluded)
    assert all(selected[key(118, n)]['role'] == 'INSTRUCTION' for n in range(59, 66))
    assert all(selected[key(129, n)]['role'] == 'UNKNOWN' for n in (51, 52))
    review = read(PREP / 'source-review.json')
    equal(review['references'], rows, 'Internal specification differs from independent original intervals')
    for s in review['sources']:
        assert sha(ROOT / s['path']) == s['sha256']
    for path, checksum in review['images'].items():
        assert sha(ROOT / path) == checksum
    return rows, destinations, review


def expected(p, missing):
    rows, targets, review = originals(p)
    packet = p['P3']['payload']['interpretation_input']['reference_admission']
    deps = []
    for row, group in zip(rows, GROUPS):
        if row['id'] in missing:
            deps.append({'id': 'internal-reference:' + row['id'], 'questions': ['Q1', 'Q2'],
                'status': 'UNRESOLVED', 'reason': 'The complete selected internal scope has no reviewed source link'})
            continue
        a = row['source']
        unknown = [KEY + ':p125:l1', KEY + ':p125:l2'] if group == 'tax' else []
        deps.append({'id': 'reviewed-reference:' + row['id'], 'questions': ['Q1', 'Q2'],
            'status': 'UNRESOLVED' if unknown else 'RESOLVED',
            'source_use': {'unit': a['unit'], 'start': a['start'], 'end': a['end'], 'source': a},
            'targets': targets[group], 'form': 'relative', 'discovery_ids': row['discovery_ids'],
            'authority': a, 'review': packet['review'], 'automatic_discovery': False,
            **({'source_binding': 'RESOLVED', 'unknown_target_uses': unknown} if unknown else {})})
    return deps, rows, review


def independent_closures(p, deps):
    """Rebuild every raw/reviewed edge and deterministic DFS without production code."""
    graph = p['P1']['payload']['graph']
    request = {**p['P1']['payload']['request'], **p['P3']['payload']['interpretation_input']}
    assert not request.get('reference_dispositions'), 'This oracle does not assume dispositions are references'
    assembly = p['P2']['payload']['assembly']
    units = {u['unit']: u for u in assembly['units'] if u['role'] in ('OPERATIVE', 'UNKNOWN')}
    raw = {u['id']: u for u in graph['units']}
    indexed = {}
    for use, u in units.items():
        maps = u.get('character_map')
        if maps is None:
            original = raw.get(use)
            maps = []
            if original and original.get('visible') and original['raw'] == u['text']:
                a = {k: original[k] for k in ('document', 'source_sha256')}
                a.update(unit=use, start=0, end=len(original['raw']), quote=original['raw'])
                maps = [{'start': 0, 'end': len(u['text']), 'operation': 'Text', 'source': a}]
        for cm in maps:
            if cm.get('operation') not in ('Text', 'Field'):
                continue
            cm = deepcopy(cm)
            if cm.get('source') is None:
                r = raw[cm['unit']]
                cm['source'] = {'unit': r['id'], 'document': r['document'],
                    'source_sha256': r['source_sha256'], 'start': cm['source_start'],
                    'end': cm['source_end'], 'quote': r['raw'][cm['source_start']:cm['source_end']]}
            s = cm['source']
            if s['start'] == s['end']:
                continue
            if use.startswith('ast:') and len(maps) == 1:
                cm['start'], cm['end'] = 0, cm['end'] - cm['start']
            assert u['text'][cm['start']:cm['end']] == s['quote']
            indexed.setdefault(cm['source']['unit'], []).append((use, cm))
    reviewed = [d for d in deps if d['id'].startswith('reviewed-reference:')]
    claims = {(identity, d['source_use']['unit'], q) for d in reviewed
              for identity in d['discovery_ids'] for q in d['questions']}
    edges = {q: [] for q in ('Q1', 'Q2')}
    for d in reviewed:
        for q in d['questions']:
            edges[q].extend((d['source_use']['unit'], t['unit'], d['id'], d['status'] == 'RESOLVED')
                            for t in d['targets'])
    actual_raw = {d['id']: d for d in deps if '@' in d['id'] and d.get('source_use') is not None}
    expected_raw = {}
    for ref in graph['references']:
        original = raw[ref['unit']]
        if not original.get('visible', False):
            continue
        candidates = {}
        for use, cm in indexed.get(ref['unit'], []):
            s = cm['source']
            left, right = max(s['start'], ref['start']), min(s['end'], ref['end'])
            if left < right:
                mapping = candidates.setdefault(use, {})
                for position in range(left, right):
                    assert position not in mapping, 'Ambiguous independent character mapping'
                    mapping[position] = cm['start'] + position - s['start']
        matches = []
        for use, mapping in candidates.items():
            if sorted(mapping) != list(range(ref['start'], ref['end'])):
                continue
            output = [mapping[n] for n in range(ref['start'], ref['end'])]
            if output != list(range(output[0], output[0] + len(output))):
                continue
            a = {'unit': ref['unit'], 'document': original['document'],
                 'source_sha256': original['source_sha256'], 'start': ref['start'],
                 'end': ref['end'], 'quote': original['raw'][ref['start']:ref['end']]}
            matches.append({'unit': use, 'start': output[0], 'end': output[-1] + 1, 'source': a})
        for match in matches:
            questions = sorted(q for q in units[match['unit']]['questions']
                               if (ref['id'], match['unit'], q) not in claims)
            if not questions:
                continue
            identity = ref['id'] + '@' + match['unit']
            assert identity not in expected_raw
            expected_raw[identity] = {'id': identity, 'questions': questions, 'status': 'UNRESOLVED',
                                      'source_use': match, 'targets': []}
            for q in questions:
                edges[q].append((match['unit'], None, identity, False))
    equal(actual_raw, expected_raw, 'Independent discovered occurrence reconstruction differs')
    result = []
    for q in ('Q1', 'Q2'):
        roots = sorted(k for k, u in units.items() if q in u['questions'])
        outgoing = {}
        for left, right, identity, resolved in edges[q]:
            outgoing.setdefault(left, []).append((right, identity, resolved))
        for values in outgoing.values():
            values.sort(key=lambda e: (str(e[0]), e[1], e[2]))
        reached, active, failures = set(), set(), set()

        def walk(k):
            if k in active:
                failures.add('Unsupported reference cycle: ' + k)
                return
            if k in reached:
                return
            if k not in units:
                failures.add('Missing reference target: ' + k)
                return
            reached.add(k)
            active.add(k)
            for target, identity, resolved in outgoing.get(k, ()):
                if not resolved:
                    failures.add('Unresolved reference: ' + identity)
                if target is not None:
                    walk(target)
            active.remove(k)

        for root in roots:
            walk(root)
        if failures:
            result.append({'id': 'reference-closure:' + q, 'questions': [q], 'status': 'UNRESOLVED',
                'roots': roots, 'reachable': sorted(reached), 'unresolved': sorted(failures)})
    return result


def questions(original, extra, replaced):
    result = deepcopy(original)
    required = {d['id'] for d in extra if d['status'] == 'UNRESOLVED'}
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
        equal(p[stage], before[stage], 'Protected source/construction changed')
    old, got = before['P3']['payload'], p['P3']['payload']
    extra, rows, review = expected(p, missing)
    replaced = {identity + '@' + r['from_use'] for r in rows if r['id'] not in missing
                for identity in r['discovery_ids']}
    wanted = deepcopy([d for d in old['dependencies'] if d['id'] not in replaced
                       and not d['id'].startswith('reference-closure:')]) + extra
    closures = independent_closures(p, wanted)
    wanted += closures
    equal(sorted(got['dependencies'], key=lambda d: d['id']), sorted(wanted, key=lambda d: d['id']),
          'Complete original-source dependencies differ')
    equal(got['questions'], questions(old['questions'], extra, replaced), 'Unexpected semantic question change')
    value = deepcopy(old['interpretation_input'])
    value['reference_admission']['references'].extend(r for r in rows if r['id'] not in missing)
    equal(got['interpretation_input'], value, 'Unexpected internal interpretation input')
    omit = {'dependencies', 'questions', 'interpretation_input'}
    equal({k: v for k, v in got.items() if k not in omit}, {k: v for k, v in old.items() if k not in omit},
          'Unrelated existing meaning changed')
    old_closures = {d['id']: d for d in old['dependencies'] if d['id'].startswith('reference-closure:')}
    closure_delta = {d['id']: {
        'removed': sorted(set(old_closures[d['id']]['unresolved']) - set(d['unresolved'])),
        'added': sorted(set(d['unresolved']) - set(old_closures[d['id']]['unresolved']))} for d in closures}
    for d in closures:
        for field in ('roots', 'reachable'):
            equal(d[field], old_closures[d['id']][field], 'Source roots/reachability changed')
        for entry in closure_delta[d['id']]['removed']:
            assert entry.startswith('Unsupported reference cycle:') or entry in {
                'Unresolved reference: ' + key for key in replaced}
        for entry in closure_delta[d['id']]['added']:
            assert entry.startswith('Unsupported reference cycle:') or entry in {
                'Unresolved reference: ' + d['id'] for d in extra if d['status'] == 'UNRESOLVED'}
    if answer is not None:
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], before[stage]['payload'], 'Legal/financial content changed')
        equal(answer['questions'], questions(old_answer['questions'], extra, replaced), 'Unexpected ordinary questions')
        omit = {'questions', 'dependencies', 'consumed_products', 'report_sha256', 'internal_references'}
        equal({k: v for k, v in answer.items() if k not in omit},
              {k: v for k, v in old_answer.items() if k not in omit}, 'Unrelated whole answer changed')
        equal(answer['dependencies'], got['dependencies'], 'Ordinary dependencies changed')
        equal(answer['internal_references'], {
            'status': 'UNREVIEWED' if missing else 'REVIEWED', 'references': rows, 'missing': list(missing),
            'source_documents': review['sources'], 'source_images': review['images'],
            'specification_sha256': digest(review), 'automatic_discovery': False,
            'conservative_cycle_policy': True, 'actual_tax_and_event_application': 'UNKNOWN',
            'complete_reference_graph': False,
            'unknown_target_uses': [KEY + ':p125:l1', KEY + ':p125:l2']}, 'Internal report differs from originals')
        equal(answer['consumed_products'], {k: v['sha256'] for k, v in p.items()}, 'Wrong consumed products')
    return {'status': 'PASS', 'independent_links': 10,
        'target_intervals': [23, 43, 43, 32, 66, 32, 46, 41, 2, 30],
        'closure_diagnostic_delta': closure_delta, 'unknown_target_uses': 2,
        'missing': list(missing), 'complete_answer_checked': answer is not None, 'original_task_complete': False}
