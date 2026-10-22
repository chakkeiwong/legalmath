"""Original mixed-period tables; exact-source checks precede explanatory sums."""
from fractions import Fraction
import re

from scripts import prospectus_h1_eps_bank_notes_mapping as mapping


def require(ok, message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def number(raw):
    token = normal(raw)
    if re.fullmatch(r'[0-9]+\.[0-9]{2}', token):
        return token
    if re.fullmatch(r'\([0-9]+\)', token):
        return -int(token[1:-1])
    require(bool(re.fullmatch(r'[0-9]+', token)), 'Unreviewed numeric form')
    return int(token)


def tables(units):
    lookup = {(u['page'], u['order']): u for u in units}

    def ref(page, order):
        unit = lookup[page, order]
        return {'id': unit['id'], 'quote': unit['raw']}

    result = []
    for spec in mapping.TABLES:
        page = spec['page']
        rows = []
        for key, label, positions, unit in spec['rows']:
            cells = []
            for position in positions:
                source = ref(page, position)
                value = number(source['quote'])
                cells.append({'source': source, 'value': value,
                    'status': 'REPORTED_DECIMAL_STRING' if isinstance(value, str)
                    else 'REPORTED_SIGNED_INTEGER'})
            rows.append({'key': key, 'unit': unit,
                'label_source': None if label is None else ref(page, label),
                'label_role': 'INTERPRETIVE_UNLABELLED_ROW' if label is None
                else 'PRINTED_ROW_LABEL', 'cells': cells})
        result.append({'key': spec['key'], 'page': page,
            'dates': spec['dates'], 'period_months': spec['period_months'],
            'period_scope': spec.get('period_scope'),
            'unit_source': ref(page, spec['unit_order']),
            'date_sources': [ref(page, n) for n in spec['date_orders']],
            'period_sources': [ref(page, n) for n in spec['period_orders']],
            'section_sources': [ref(page, n) for n in spec['section_orders']],
            'rows': rows})
    return result


def validate(actual, units, manual):
    lookup = {u['id']: u for u in units}
    require(len(lookup) == len(units), 'Duplicate original occurrence')
    require(actual == tables(units), 'Reviewed table associations changed')
    require({t['key'] for t in actual} == set(manual['tables']), 'Missing image table')
    numeric_ids, arithmetic = [], []
    row_count, max_row_offset = 0, 0
    for table in actual:
        typed = manual['tables'][table['key']]
        require(table['dates'] == typed['dates'] and
                table['period_months'] == typed['period_months'],
                'Image date/period mismatch')
        require([[row['key'], *[cell['value'] for cell in row['cells']]]
                 for row in table['rows']] == typed['rows'], 'Image row/value mismatch')
        units_expected = typed.get('units', [typed.get('unit')] * len(table['rows']))
        require([r['unit'] for r in table['rows']] == units_expected,
                'Image unit mismatch')
        require(normal(table['unit_source']['quote']) == '(inthousandsofeuro)',
                'Wrong printed unit caption')
        dates = ['.'.join(reversed(date.split('-'))) for date in table['dates']]
        require([normal(q['quote']) for q in table['date_sources']] == dates,
                'Wrong printed dates')
        headers = [lookup[q['id']]['bbox'] for q in table['date_sources']]
        require(all(a[2] < b[0] and abs(a[1] - b[1]) <= 1
                    for a, b in zip(headers, headers[1:])), 'Date header alignment changed')
        middles = [(a[2] + b[0]) / 2 for a, b in zip(headers, headers[1:])]
        periods = [normal(q['quote']) for q in table['period_sources']]
        if table['key'] == 'eps':
            require(periods == ['Sixmonth', 'periodended', 'Yearended',
                                'Sixmonth', 'periodended'], 'EPS period captions changed')
            for source, column in zip(table['period_sources'], [0, 0, 1, 2, 2]):
                box = lookup[source['id']]['bbox']
                require(box[3] < headers[column][1], 'EPS period below date')
                require(column == 0 or box[0] > middles[column - 1],
                        'EPS period in wrong column')
                require(column == len(headers) - 1 or box[2] < middles[column],
                        'EPS period in wrong column')
        elif table['key'] == 'bank-impairment':
            require(periods == ['Sixmonthperiodended'] and
                    normal(typed['printed_period_caption']) == periods[0],
                    'Printed impairment caption changed')
            require(table['period_scope'] == typed['period_scope'] ==
                    'PRINTED_CAPTION_RETAINED; DECEMBER_COLUMN_DURATION_NOT_INFERRED'
                    and table['period_months'] is None, 'Impairment duration inferred')
        else:
            require(not periods and table['period_scope'] is None,
                    'Unexpected balance duration')
        previous_y = None
        keys = [r['key'] for r in table['rows']]
        require(len(keys) == len(set(keys)), 'Duplicate table row')
        for row in table['rows']:
            row_count += 1
            require(len(row['cells']) == len(headers), 'Missing numeric column')
            boxes = [lookup[c['source']['id']]['bbox'] for c in row['cells']]
            require(max(b[1] for b in boxes) - min(b[1] for b in boxes) <= 1,
                    'Date values on different rows')
            require(previous_y is None or boxes[0][1] > previous_y, 'Wrong row sequence')
            previous_y = boxes[0][1]
            for column, (cell, box) in enumerate(zip(row['cells'], boxes)):
                source = lookup[cell['source']['id']]
                require(source['page'] == table['page'] and
                        source['raw'] == cell['source']['quote'], 'Wrong source reference')
                require(box[1] > headers[column][3], 'Value above date')
                require(column == 0 or box[0] > middles[column - 1],
                        'Wrong value/date column')
                require(column == len(headers) - 1 or box[2] < middles[column],
                        'Wrong value/date column')
                require(isinstance(cell['value'], str) == (row['unit'] == 'EUR_PER_SHARE'),
                        'Wrong decimal/integer unit')
                numeric_ids.append(source['id'])
            if row['label_source'] is not None:
                label = lookup[row['label_source']['id']]
                offset = abs(label['bbox'][1] - boxes[0][1])
                max_row_offset = max(max_row_offset, offset)
                require(label['page'] == table['page'] and offset <= 1 and
                        label['bbox'][2] < boxes[0][0], 'Wrong label/value row')
        values = {r['key']: [c['value'] for c in r['cells']] for r in table['rows']}

        def residual(parts, total):
            return {'table': table['key'], 'total_row': total,
                    'residuals': [sum(values[k][c] for k in parts) - values[total][c]
                                  for c in range(len(headers))]}

        if table['key'] == 'eps':
            arithmetic.append({'table': 'eps', 'treasury_subtraction_residuals': [
                values['ordinary-shares'][c] - values['treasury-shares'][c] -
                values['outstanding-shares'][c] for c in range(3)]})
            ratios = []
            for c in range(3):
                ratio = Fraction(values['profit'][c], values['outstanding-shares'][c])
                reported = Fraction(values['basic-eps'][c])
                difference = ratio - reported
                ratios.append({'date': table['dates'][c],
                    'ratio': {'numerator': ratio.numerator, 'denominator': ratio.denominator},
                    'reported_eur_per_share': values['basic-eps'][c],
                    'difference': {'numerator': difference.numerator, 'denominator': difference.denominator},
                    'within_closed_half_cent': abs(difference) <= Fraction(1, 200)})
            arithmetic.append({'table': 'eps', 'ratios': ratios,
                'scale_cancellation': 'EUR_THOUSANDS / SHARES_THOUSANDS = EUR_PER_SHARE',
                'tie_rounding_convention_not_inferred': True})
        elif table['key'] == 'central-cash':
            arithmetic.extend([residual(['bank-portugal', 'other-central-banks'], 'central-total'),
                               residual(['cash', 'central-total'], 'total')])
        elif table['key'] in ('bank-deposits', 'bank-advances'):
            for part in ('portugal', 'abroad'):
                arithmetic.append(residual([k for k in keys if k.startswith(part + '-')
                                            and k != part + '-total'], part + '-total'))
            parts = ['portugal-total', 'abroad-total']
            if table['key'] == 'bank-advances':
                parts.append('impairment')
            arithmetic.append(residual(parts, 'total' if table['key'] == 'bank-deposits' else 'net-total'))
        else:
            arithmetic.append(residual(['opening', 'charge', 'write-back', 'exchange-other'], 'closing'))
    require(row_count == 38 and len(numeric_ids) == len(set(numeric_ids)) == 86,
            'Missing or repeated numeric position')
    return {'table_rows': row_count, 'numeric_positions': len(numeric_ids),
            'maximum_label_offset_points': max_row_offset, 'geometry_tolerance_points': 1,
            'arithmetic_role': 'EXPLANATORY_ONLY', 'arithmetic': arithmetic,
            'unknown_duration_not_inferred': True}
