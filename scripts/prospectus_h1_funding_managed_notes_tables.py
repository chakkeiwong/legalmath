"""Image-bound original funding and managed-asset tables."""
import re
from scripts import prospectus_h1_funding_managed_notes_mapping as mapping


def require(ok, message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def number(raw):
    token = normal(raw)
    require(bool(re.fullmatch(r'[0-9]+', token)), 'Unreviewed positive integer form')
    return int(token)


def tables(units):
    lookup = {(u['page'], u['order']): u for u in units}

    def ref(page, order):
        u = lookup[page, order]
        return {'id': u['id'], 'quote': u['raw']}

    result = []
    for spec in mapping.TABLES:
        page = spec['page']
        rows = []
        for key, label, left, right in spec['rows']:
            refs = [ref(page, n) for n in (left, right)]
            rows.append({'key': key,
                'label_source': None if label is None else ref(page, label),
                'label_role': 'INTERPRETIVE_UNLABELLED_ROW' if label is None else 'PRINTED_ROW_LABEL',
                'cells': [{'source': q, 'value': number(q['quote']), 'status': 'REPORTED_INTEGER'} for q in refs]})
        result.append({'key': spec['key'], 'page': page, 'unit': 'EUR_THOUSANDS',
            'dates': ['2010-06-30', '2009-12-31'], 'period_months': None,
            'unit_source': ref(page, spec['unit_order']),
            'date_sources': [ref(page, n) for n in spec['date_orders']],
            'section_sources': [ref(page, n) for n in spec['section_orders']],
            'rows': rows})
    return result


def validate(actual, units, manual):
    lookup = {u['id']: u for u in units}
    require(len(lookup) == len(units), 'Duplicate original occurrence')
    require(actual == tables(units), 'Reviewed table association changed')
    require({t['key'] for t in actual} == set(manual['tables']), 'Missing image table')
    numeric_ids, residuals = [], []
    row_count, maximum_offset = 0, 0
    specs = {s['key']: s for s in mapping.TABLES}
    for table in actual:
        typed = manual['tables'][table['key']]
        require(table['dates'] == typed['dates'] == ['2010-06-30', '2009-12-31'] and
                table['period_months'] == typed['period_months'] is None and
                table['unit'] == typed['unit'] == 'EUR_THOUSANDS', 'Image date/unit scope mismatch')
        values = [[r['key'], *[c['value'] for c in r['cells']]] for r in table['rows']]
        require(values == typed['rows'], 'Image row/value mismatch')
        require(normal(table['unit_source']['quote']) == '(inthousandsofeuro)', 'Wrong printed unit')
        require([normal(q['quote']) for q in table['date_sources']] == ['30.06.2010', '31.12.2009'],
                'Wrong printed dates')
        headers = [lookup[q['id']]['bbox'] for q in table['date_sources']]
        require(headers[0][2] < headers[1][0] and abs(headers[0][1] - headers[1][1]) <= 1,
                'Date alignment changed')
        middle = (headers[0][2] + headers[1][0]) / 2
        previous_y = None
        keys = [r['key'] for r in table['rows']]
        require(len(keys) == len(set(keys)), 'Duplicate table row')
        for row in table['rows']:
            row_count += 1
            require(len(row['cells']) == 2, 'Missing numeric column')
            boxes = [lookup[c['source']['id']]['bbox'] for c in row['cells']]
            maximum_offset = max(maximum_offset, abs(boxes[0][1] - boxes[1][1]))
            require(abs(boxes[0][1] - boxes[1][1]) <= 1, 'Date values on different rows')
            require(boxes[0][2] < middle < boxes[1][0], 'Wrong value/date column')
            require(all(b[1] > h[3] for b, h in zip(boxes, headers)), 'Value above header')
            require(previous_y is None or boxes[0][1] > previous_y, 'Wrong row sequence')
            previous_y = boxes[0][1]
            if row['label_source'] is not None:
                label = lookup[row['label_source']['id']]
                offset = abs(label['bbox'][1] - boxes[0][1])
                maximum_offset = max(maximum_offset, offset)
                require(label['page'] == table['page'] and offset <= 1 and
                        label['bbox'][2] < boxes[0][0], 'Wrong label/value row')
            for cell in row['cells']:
                source = lookup[cell['source']['id']]
                require(source['page'] == table['page'] and source['raw'] == cell['source']['quote'],
                        'Wrong source reference')
                numeric_ids.append(source['id'])
        by_key = {r['key']: [c['value'] for c in r['cells']] for r in table['rows']}
        for parts, total in specs[table['key']]['subtotals']:
            residuals.append({'table': table['key'], 'total_row': total,
                'residuals': [sum(by_key[k][c] for k in parts) - by_key[total][c] for c in range(2)]})
        if table['key'] == 'central-funding':
            distinctions = manual['distinctions']
            require(distinctions['collateral_sentence_unit'] == 'EUR_MILLIONS',
                    'Wrong prose amount units')
            residuals.append({'table': table['key'], 'prose_row': 'escb-other',
                'million_to_thousand_factor': 1000,
                'residuals': [distinctions['escb_other_funds_eur_millions'][date] * 1000 -
                              by_key['escb-other'][c] for c, date in enumerate(table['dates'])]})
    require(row_count == 37 and len(numeric_ids) == len(set(numeric_ids)) == 74,
            'Missing or duplicate numeric position')
    return {'table_rows': row_count, 'numeric_positions': len(numeric_ids),
        'maximum_row_offset_points': maximum_offset, 'geometry_tolerance_points': 1,
        'arithmetic_role': 'EXPLANATORY_ONLY', 'arithmetic': residuals}
