"""Separate verifier using the retained 008 reading, not production row/parser code."""
from copy import deepcopy
import hashlib
import json


def fingerprint(value):
    raw = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def source(unit):
    require(unit['visible'] is True, 'Original occurrence unavailable')
    return {'unit': unit['id'], 'document': unit['document'], 'source_sha256': unit['source_sha256'],
            'start': 0, 'end': len(unit['raw']), 'quote': unit['raw']}


def signed_integer(text, language):
    """Independent character/group checks; no production parser or regex."""
    text = text.strip()
    if text == '-':
        return None
    negative = text[:1] == '(' and text[-1:] == ')'
    body = text[1:-1].strip() if negative else text
    groups = body.split(',' if language == 'en' else ' ')
    require(bool(groups) and all(g and all('0' <= c <= '9' for c in g) for g in groups),
            'Invalid independent source numeral')
    require(len(groups) == 1 or (1 <= len(groups[0]) <= 3 and all(len(g) == 3 for g in groups[1:])),
            'Invalid independent digit grouping')
    digits = ''.join(groups)
    require(digits == '0' or not digits.startswith('0'), 'Invalid independent leading zero')
    value = int(digits)
    return -value if negative else value


def verify_review(actual, profile, graph, original_reading, original_units, root=None):
    """Check complete structured result against a second, immutable source map."""
    old = {u['id']: u for u in original_units}
    current = {u['id']: u for u in graph['units']}
    require(len(current) == len(graph['units']), 'Duplicate graph source identity')
    require(profile['graph_sha256'] == fingerprint(graph), 'Graph/profile mismatch')
    require(actual['profile_sha256'] == fingerprint(profile), 'Result/profile mismatch')
    names = ('buy_investments', 'sell_investments', 'dividend', 'buy_AFS', 'sell_AFS',
             'HTM', 'buy_fixed', 'sell_fixed', 'investing', 'operating', 'financing',
             'merger_leasing', 'merger_BESSA', 'net_change')
    editions = []
    def checked(anchor):
        u = old[anchor['unit']]
        require(fingerprint(current.get(u['id'])) == fingerprint(u), 'Original extraction occurrence changed')
        require(fingerprint(anchor) == fingerprint(source(u)), 'Complete original source occurrence required')
        return {**anchor, 'page': u['page'], 'bbox': u.get('bbox')}
    for language in ('en', 'pt'):
        supplied, = [e for e in profile['editions'] if e['language'] == language]
        table = original_reading['tables'][language]['cash_flow']['rows']
        document = 'bes-2008-' + language
        context = {}
        for key, page, line in (('individual', 165, 1), ('title', 170, 0), ('unit', 170, 1)):
            expected = source(old[f'{document}:p{page}:l{line}'])
            require(fingerprint(supplied['context'][key]) == fingerprint(expected), 'Source context changed')
            context[key] = checked(expected)
        context['years'] = [checked(source(old[f'{document}:p170:l{line}'])) for line in (4, 5)]
        require(fingerprint(supplied['context']['years']) == fingerprint([
            source(old[f'{document}:p170:l{line}']) for line in (4, 5)]), 'Year order changed')
        rows = {}
        for name in names:
            original = table[name]
            label = source(old[original['labels'][0]['id']])
            anchors = [source(old[c['source_unit']]) for c in original['cells']]
            require(fingerprint(supplied['rows'][name]) == fingerprint({'label': label, 'cells': anchors}),
                    'Original row mapping changed')
            cells = {}
            for year, cell, a in zip(('2008', '2007'), original['cells'], anchors):
                number = signed_integer(a['quote'], language)
                require(type(number) is int if cell['value'] is not None else number is None,
                        'Boolean/non-integer source amount')
                require(fingerprint(number) == fingerprint(cell['value']), 'Original reading/independent parse disagree')
                cells[year] = {'literal': a['quote'], 'value': number, 'unit': 'EUR thousands',
                               'status': 'DASH_UNKNOWN' if number is None else 'SOURCE_NUMBER', 'source': checked(a)}
            rows[name] = {'label': checked(label), 'cells': cells}
        require(set(supplied['rows']) == set(names), 'Row inventory changed')
        capital = ({'status': 'SUPPLIED_VISUAL_BLANKS',
                    'label': checked(source(old[table['capital_increase']['labels'][0]['id']])),
                    'cells': {y: {'status': 'VISIBLE_BLANK_UNKNOWN', 'value': None,
                                  'unit': 'EUR thousands', 'source': None} for y in ('2008', '2007')}}
                   if language == 'en' else {'status': 'ABSENT_IN_SUPPLIED_READING', 'cells': None})
        require(fingerprint(supplied['capital_increase']) == fingerprint(
            {'status': capital['status'], **({'label': source(old[table['capital_increase']['labels'][0]['id']])}
                                            if language == 'en' else {})}), 'Blank/absence observation changed')
        relations = []
        for year in ('2008', '2007'):
            for identifier, target, parts in (
                    ('investing', 'investing', names[:8]),
                    ('net-change', 'net_change', ('operating', 'investing', 'financing', 'merger_leasing', 'merger_BESSA'))):
                values = [rows[k]['cells'][year]['value'] for k in (target, *parts)]
                missing = [{'row': k, 'coefficient': 1 if i == 0 else -1}
                           for i, (k, v) in enumerate(zip((target, *parts), values)) if v is None]
                left = values[0] if values[0] is not None else 0
                right = sum(v for v in values[1:] if v is not None)
                difference = left - right
                relations.append({'id': identifier + ':' + year, 'year': year, 'unit': 'EUR thousands',
                    'target': target, 'components': list(parts),
                    'status': 'INCOMPLETE_UNKNOWN' if missing else 'COMPLETE_EQUALITY' if difference == 0 else 'PRINTED_ARITHMETIC_DISCREPANCY',
                    'known_residual_part': difference, 'unknown_terms': missing,
                    'residual': None if missing else difference, 'component_sum': None if missing else right,
                    'official_correction_established': False})
        image = deepcopy(supplied['image'])
        if root is not None:
            path = (root / image['path']).resolve()
            require(path.is_relative_to(root.resolve()) and fingerprint(path.read_bytes()) == image['sha256'],
                    'Original image identity changed')
        editions.append({'language': language, 'document': document, 'source_sha256': supplied['source_sha256'],
            'context': context, 'image': image, 'rows': rows, 'capital_increase': capital, 'relations': relations})
    require(fingerprint(actual['editions']) == fingerprint(editions), 'Independent source/arithmetic check failed')
    comparisons = []
    for name in names:
        for year in ('2008', '2007'):
            a, b = [e['rows'][name]['cells'][year]['value'] for e in editions]
            difference = None if a is None or b is None else a - b
            comparisons.append({'row': name, 'year': year, 'unit': 'EUR thousands', 'en': a, 'pt': b,
                'difference_en_minus_pt': difference,
                'status': 'INCOMPLETE_UNKNOWN' if difference is None else 'AGREE' if difference == 0 else 'UNRESOLVED_SOURCE_DISCREPANCY'})
    require(fingerprint(actual['bilingual_comparisons']) == fingerprint(comparisons), 'Bilingual comparison changed')
    for flag in ('automatic_discovery', 'source_authenticity_established', 'official_correction_established',
                 'financial_calculation_authorized', 'independent_legal_acceptance', 'may_execute_transaction'):
        require(actual[flag] is False, 'Unsupported promotion: ' + flag)
    for field in ('resolved_amount', 'controlling_edition', 'accounting_cause'):
        require(actual[field] is None, 'Unresolved interpretation selected')
    require(actual['version'] == 'bes2008-individual-cash-flow.v1'
            and actual['graph_sha256'] == fingerprint(graph)
            and fingerprint(actual['review']) == fingerprint(profile['review'])
            and actual['scope'] == 'BES Bank individual cash-flow statements; supplied page170 rows,2008/2007; not consolidated or BES Finance Ltd standalone',
            'Evidence scope changed')
    # Checked against the finite original numbers, independently of the production prose builder.
    sentences = []
    for e in editions:
        for r in e['relations']:
            outcome = (f'incomplete, with known-part residual {r["known_residual_part"]} and {len(r["unknown_terms"])} unknown term(s)'
                       if r['unknown_terms'] else f'complete, with printed-minus-component residual {r["residual"]}')
            sentences.append(f'{e["language"]} {r["id"]}: {outcome} thousand euros.')
    expected_prose = ('The supplied 2008 individual cash-flow statements are in thousands of euros. '
        'The eight printed investing components sum to -4041798 in English and -4041798 in Portuguese. '
        'The printed subtotals are -4041758 and -4041798, respectively. '
        'The English printed-minus-component residual is 40 thousand euros; the Portuguese residual is 0. '
        + ' '.join(sentences) + ' A known-part residual with unknown terms is not a complete arithmetic discrepancy. '
        'The English blank capital-increase cells and the row absent from the supplied Portuguese reading remain distinct. '
        'Both editions are preserved. No controlling edition, official corrected amount, accounting cause or financial authorization is established.')
    require(actual['explanation'] == expected_prose, 'Source-linked explanation changed')
    require(set(actual) == {'version', 'profile_sha256', 'graph_sha256', 'review', 'editions', 'bilingual_comparisons',
            'scope', 'automatic_discovery', 'source_authenticity_established', 'resolved_amount', 'controlling_edition',
            'accounting_cause', 'official_correction_established', 'financial_calculation_authorized',
            'independent_legal_acceptance', 'may_execute_transaction', 'explanation'}, 'Unexpected result field')
    return {'version': 'bes-cash-flow-independent.v1', 'source_rows': 28, 'source_cells': 56,
            'relations': 8, 'complete_relations': 4, 'incomplete_relations': 4,
            'en_2008_investing_residual_thousand_EUR': 40, 'pt_2008_investing_residual_thousand_EUR': 0,
            'official_correction_established': False, 'original_task_complete': False}
