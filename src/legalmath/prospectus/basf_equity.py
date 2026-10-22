"""Optional, exposed reading of BASF's two disputed equity movement tables."""
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import re

from . import basf_statement
from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'basf-equity-movement-review.v1'
DOCUMENT = basf_statement.DOCUMENT
PAGE = 208
COLUMNS = {
    'capital': ['Subscribed', 'capital'],
    'reserves': ['Capital', 'reserves'],
    'retained': ['Retained', 'earnings'],
    'pensions': ['Remeasure-', 'ment of', 'defined', 'benefit plans'],
    'currency': ['Currency', 'translation'],
    'securities': ['Measurement', 'of securities', 'at fair value'],
    'hedges': ['Cash flow', 'hedges'],
    'oci': ['Other com-', 'prehensive', 'income b'],
    'shareholders': ['Equity', 'attributable to', 'shareholders', 'of BASF SE'],
    'nci': ['Non-', 'controlling', '\xadinterests'],
    'equity': ['Equity'],
}
MOVEMENTS = {
    'treasury': ['Treasury shares'],
    'dividends': ['Dividends paid'],
    'income': ['Income after taxes'],
    'oci': ['Other comprehensive income after taxes'],
    'hedge_elimination': [
        'Gains and losses on cash flow hedges and hedging costs, eliminated',
        'from other comprehensive income not affecting profit and loss'],
    'other': ['Changes in scope of consolidation and other changes'],
}
ROW_ORDER = {
    '2022': ['opening', 'treasury', 'dividends', 'income', 'oci', 'hedge_elimination', 'other', 'closing'],
    '2021': ['opening', 'dividends', 'income', 'oci', 'other', 'closing'],
}
FOOTNOTES = {
    'a': 'For more information on the items relating to equity, see Notes 19 and 20 from page 254 onward',
    'b': 'Details are provided in the Statement of Income and Expense Recognized in Equity on page 204.',
    'c': 'Including profit and loss transfers',
    'd': 'Valuation adjustment BASF “plus” share program',
}


def amount(literal, expected_marker=None):
    """Keep the full source literal and require an explicitly associated footnote."""
    if not isinstance(literal, str):
        raise ValueError('Expected original amount literal')
    match = re.fullmatch(r'(.+) ([cd])', literal)
    number, marker = (match[1], match[2]) if match else (literal, None)
    if marker != expected_marker:
        raise ValueError('Required numeric footnote marker changed or omitted')
    parsed = basf_statement.integer_millions(number)
    if marker is not None and parsed['integer_millions'] is None:
        raise ValueError('A footnoted amount must be a printed integer')
    return {**parsed, 'literal': literal, 'amount_literal': number, 'footnote_marker': marker}


def comparison(name, left, right):
    """Compare printed integer sums without imputing any missing component."""
    left_values = [x['integer_millions'] for x in left]
    right_values = [x['integer_millions'] for x in right]
    known = all(x is not None for x in left_values + right_values)
    difference = sum(left_values) - sum(right_values) if known else None
    return {'name': name, 'left': deepcopy(left), 'right': deepcopy(right),
            'left_minus_right': difference,
            'status': 'UNKNOWN_COMPONENT' if not known else 'EQUAL_PRINTED_VALUES' if difference == 0 else 'PRINTED_DIFFERENCE',
            'role': 'EXPLANATORY_ONLY'}


def cross_statement(tables, statement):
    source_rows = {r['id']: r for r in statement['rows']}
    by_year = {t['year']: {r['id']: r for r in t['rows']} for t in tables}
    out = []
    for year in ('2022', '2021'):
        rows = by_year[year]
        for row, column, ref in [('income', 'equity', 'income'), ('oci', 'equity', 'oci'),
                                 ('oci', 'shareholders', 'oci_shareholders'), ('oci', 'nci', 'oci_nci')]:
            out.append(comparison(year + ':' + ref, [rows[row]['cells'][column]], [source_rows[ref]['cells'][year]]))
        for column, ref in [('equity', 'comprehensive'), ('shareholders', 'ci_shareholders'), ('nci', 'ci_nci')]:
            out.append(comparison(year + ':' + ref,
                                  [rows['income']['cells'][column], rows['oci']['cells'][column]],
                                  [source_rows[ref]['cells'][year]]))
    for column in COLUMNS:
        out.append(comparison('closing2021-opening2022:' + column,
                              [by_year['2021']['closing']['cells'][column]],
                              [by_year['2022']['opening']['cells'][column]]))
    return out


def evaluate(graph, incorporation, statement, profile, root, *, expected_profile_sha256):
    keys = {'version', 'graph_sha256', 'incorporation_sha256', 'statement_sha256',
            'reviewer', 'source', 'metadata', 'heading', 'entity', 'tables', 'footnotes',
            'selected_reading', 'financial_values_validated'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != digest(graph)
            or profile['incorporation_sha256'] != digest(incorporation)
            or profile['statement_sha256'] != digest(statement)):
        raise ValueError('Pinned equity/source/incorporation/statement reading changed')
    if profile['selected_reading'] is not None or profile['financial_values_validated'] is not False:
        raise ValueError('Equity reading cannot adjudicate incorporation or validate accounts')
    reviewer = profile['reviewer']
    fields(reviewer, {'identity', 'basis', 'independent'}, {'identity', 'basis', 'independent'})
    if (not isinstance(reviewer['identity'], str) or not reviewer['identity'].strip()
            or reviewer['basis'] != 'AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported equity review authority')
    source = profile['source']
    source_keys = {'document', 'page', 'path', 'sha256', 'image_path', 'image_sha256'}
    fields(source, source_keys, source_keys)
    if source['document'] != DOCUMENT or source['page'] != PAGE:
        raise ValueError('This supplied reading is BASF annual2022 page208')
    root = Path(root).resolve()
    for path_key, hash_key in (('path', 'sha256'), ('image_path', 'image_sha256')):
        name = source[path_key]
        path = (root / name).resolve()
        if (Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file()
                or digest(path.read_bytes()) != source[hash_key]):
            raise ValueError('Original equity PDF or inspected image changed')
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']):
        raise ValueError('Duplicate source occurrence')
    page = [u for u in graph['units'] if u['document'] == DOCUMENT and u['page'] == PAGE and u['visible']]
    if len(page) != 242 or any(u['source_sha256'] != source['sha256'] or u['text_sha256'] != digest(u['raw'].encode()) for u in page):
        raise ValueError('Complete original equity page inventory changed')
    used = []

    def full(a):
        bounded = bind(graph, a)
        u = units[a['unit']]
        if (bounded['document'] != DOCUMENT or bounded['page'] != PAGE or a['start'] != 0
                or a['end'] != len(u['raw']) or a['source_sha256'] != source['sha256']):
            raise ValueError('Complete original equity occurrence required')
        b = bounded['bbox']
        if (not isinstance(b, list) or len(b) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in b)
                or b[0] >= b[2] or b[1] >= b[3]):
            raise ValueError('Finite nonempty original geometry required')
        used.append(u['id'])
        return bounded

    def span(anchors):
        boxes = [a['bbox'] for a in anchors]
        return [min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes)]

    def fragments(anchors, expected):
        bound = [full(a) for a in anchors]
        if [a['quote'] for a in bound] != expected:
            raise ValueError('Complete ordered source fragments required')
        if any(a['bbox'][3] >= b['bbox'][1] for a, b in zip(bound, bound[1:])):
            raise ValueError('Source fragment vertical order changed')
        return bound

    def overlap(a, b, axis):
        return max(a[axis], b[axis]) < min(a[axis + 2], b[axis + 2])

    if len(profile['metadata']) != 3:
        raise ValueError('Complete page metadata required')
    metadata = [full(a) for a in profile['metadata']]
    heading, entity = full(profile['heading']), full(profile['entity'])
    if heading['quote'] != 'Statement of Changes in Equity' or entity['quote'] != 'BASF Group':
        raise ValueError('Equity statement identity changed')
    if [t.get('year') for t in profile['tables']] != ['2022', '2021']:
        raise ValueError('Complete ordered date-specific tables required')
    tables, last_bottom = [], entity['bbox'][3]
    for table in profile['tables']:
        fields(table, {'year', 'subtitle', 'unit', 'columns', 'rows'}, {'year', 'subtitle', 'unit', 'columns', 'rows'})
        year = table['year']
        subtitle, unit = full(table['subtitle']), full(table['unit'])
        if (subtitle['quote'] != 'Statement of changes in equity a' or unit['quote'] != 'Million €'
                or subtitle['bbox'][1] <= last_bottom or unit['bbox'][1] <= subtitle['bbox'][3]):
            raise ValueError('Table identity, unit or date-specific order changed')
        if [c.get('id') for c in table['columns']] != list(COLUMNS):
            raise ValueError('Complete ordered equity columns required')
        columns, col_boxes = [], {}
        last_right = unit['bbox'][0]
        for col in table['columns']:
            fields(col, {'id', 'fragments'}, {'id', 'fragments'})
            bound = fragments(col['fragments'], COLUMNS[col['id']])
            b = span(bound)
            if b[0] <= last_right or b[1] <= unit['bbox'][3]:
                raise ValueError('Column geometry or table membership changed')
            col_boxes[col['id']] = b
            columns.append({'id': col['id'], 'fragments': bound, 'footnote_marker': 'b' if col['id'] == 'oci' else None})
            last_right = b[2]
        if [r.get('id') for r in table['rows']] != ROW_ORDER[year]:
            raise ValueError('Complete ordered equity rows required')
        rows, last_bottom = [], max(b[3] for b in col_boxes.values())
        for row in table['rows']:
            fields(row, {'id', 'label', 'cells'}, {'id', 'label', 'cells'})
            name = row['id']
            expected = ([f'As of January 1, {year}'] if name == 'opening' else
                        [f'As of December 31, {year}'] if name == 'closing' else MOVEMENTS[name])
            label = fragments(row['label'], expected)
            b = span(label)
            if b[1] <= last_bottom or b[2] >= min(x[0] for x in col_boxes.values()):
                raise ValueError('Row geometry or year changed')
            fields(row['cells'], COLUMNS, COLUMNS)
            cells = {}
            for column, a in row['cells'].items():
                cell = full(a)
                if (not overlap(b, cell['bbox'], 1) or not overlap(col_boxes[column], cell['bbox'], 0)
                        or b[2] >= cell['bbox'][0]):
                    raise ValueError('Cell does not align with its original row/year/column')
                marker = 'c' if (name, column) == ('dividends', 'nci') else 'd' if (name, column) == ('other', 'reserves') else None
                cells[column] = {**amount(cell['quote'], marker), 'source': cell}
            rows.append({'id': name, 'label': label, 'cells': cells})
            last_bottom = b[3]
        tables.append({'year': year, 'subtitle': subtitle, 'subtitle_footnote': 'a',
                       'unit': unit, 'columns': columns, 'rows': rows})
    fields(profile['footnotes'], FOOTNOTES, FOOTNOTES)
    footnotes = {}
    for marker, text in FOOTNOTES.items():
        note = profile['footnotes'][marker]
        fields(note, {'marker', 'text'}, {'marker', 'text'})
        m, t = full(note['marker']), full(note['text'])
        if (m['quote'] != marker or t['quote'] != text or not overlap(m['bbox'], t['bbox'], 1)
                or m['bbox'][2] >= t['bbox'][0] or min(m['bbox'][1], t['bbox'][1]) <= last_bottom):
            raise ValueError('Footnote marker, text or original scope changed')
        last_bottom = max(m['bbox'][3], t['bbox'][3])
        footnotes[marker] = {'marker': m, 'text': t}
    if Counter(used) != Counter(u['id'] for u in page):
        raise ValueError('Every original equity page occurrence must be retained exactly once')
    if (incorporation['status'] != 'UNRESOLVED' or incorporation['selected_reading'] is not None
            or statement['version'] != basf_statement.VERSION or statement['page'] != 204
            or statement['financial_values_validated'] is not False or statement['selected_reading'] is not None):
        raise ValueError('Current statement and unresolved incorporation required')
    alternatives = []
    for reading in incorporation['readings']:
        included = PAGE in reading['candidate_pages']
        alternatives.append({'id': reading['id'], 'condition': reading['condition'],
            'page208_in_candidate_scope': included, 'page208_reading_available': True,
            'status': 'CONDITIONAL_INCLUDED_SOURCE' if included else 'OUTSIDE_DETAILED_SOURCE_SELECTION',
            'legal_incorporation_established': False})
    if [r['page208_in_candidate_scope'] for r in alternatives] != [False, True]:
        raise ValueError('Expected unresolved detailed and broader incorporation alternatives')
    for table in tables:
        table['subtitle_note'] = deepcopy(footnotes['a'])
        for column in table['columns']:
            if column['footnote_marker']:
                column['footnote'] = deepcopy(footnotes[column['footnote_marker']])
        for row in table['rows']:
            for cell in row['cells'].values():
                if cell['footnote_marker']:
                    cell['footnote'] = deepcopy(footnotes[cell['footnote_marker']])
    return {'version': VERSION, 'profile_sha256': digest(profile), 'page': PAGE,
        'metadata': metadata, 'heading': heading, 'entity': entity, 'tables': tables, 'footnotes': footnotes,
        'cross_statement_comparisons': cross_statement(tables, statement),
        'rounding_context': deepcopy(statement['rounding_context']), 'rounding_context_in_candidate_scopes': False,
        'rounding_interpretation': statement['rounding_interpretation'],
        'incorporation_alternatives': alternatives, 'original_occurrences_accounted': len(used),
        'printed_cells': 154, 'footnoted_amounts': 4, 'financial_values_validated': False,
        'selected_reading': None, 'independent_legal_acceptance': False,
        'field_associations': 'SUPPLIED_EXPOSED_REVIEW', 'profile': deepcopy(profile)}


def consume(products, statement_profile, profile, root, *, expected_statement_profile_sha256, expected_profile_sha256):
    result = basf_statement.consume(products, statement_profile, root,
                                    expected_profile_sha256=expected_statement_profile_sha256)
    review = evaluate(products['P1']['payload']['graph'], result['answer']['incorporation'],
                      result['statement_review'], profile, root, expected_profile_sha256=expected_profile_sha256)
    return {**result, 'equity_review': review}
