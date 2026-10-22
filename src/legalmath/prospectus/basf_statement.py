"""Optional exposed reading of BASF's disputed comprehensive-income page."""
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import re

from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'basf-comprehensive-income-review.v1'
DOCUMENT = 'basf-annual-2022-exchange'
PAGE = 204
ROWS = {
    'income': 'Income after taxes',
    'pensions': 'Remeasurement of defined benefit plans b',
    'pension_tax': 'Deferred taxes on the remeasurement of defined benefit plans',
    'equity_nonrec': 'Investments accounted for using the equity method – share of nonreclassifiable gains/losses (after taxes)',
    'nonrec': 'Nonreclassifiable gains/losses',
    'hedges': 'Unrealized gains/losses in connection with cash flow hedges',
    'hedge_reclass': 'Reclassification of realized gains/losses recognized in the statement of income in connection with cash flow hedges',
    'currency': 'Unrealized gains/losses from currency translation',
    'currency_reclass': 'Reclassification of realized gains/losses from currency translation recognized in the statement of income',
    'reclass_tax': 'Deferred taxes on reclassifiable gains/losses',
    'equity_rec': 'Investments accounted for using the equity method – share of reclassifiable gains/losses (after taxes)',
    'rec': 'Reclassifiable gains/losses',
    'oci': 'Other comprehensive income after taxes',
    'oci_shareholders': 'of which attributable to shareholders of BASF SE',
    'oci_nci': 'attributable to noncontrolling interests',
    'comprehensive': 'Comprehensive income',
    'ci_shareholders': 'of which attributable to shareholders of BASF SE',
    'ci_nci': 'attributable to noncontrolling interests',
}
SUMS = {
    'nonrec': ['pensions', 'pension_tax', 'equity_nonrec'],
    'rec': ['hedges', 'hedge_reclass', 'currency', 'currency_reclass', 'reclass_tax', 'equity_rec'],
    'oci': ['nonrec', 'rec'],
    'oci_attribution': ['oci_shareholders', 'oci_nci'],
    'comprehensive': ['income', 'oci'],
    'comprehensive_attribution': ['ci_shareholders', 'ci_nci'],
}


def integer_millions(literal):
    """Preserve the standalone printed dash as unknown, never zero."""
    if literal == '–':
        return {'literal': literal, 'status': 'PRINTED_DASH_UNKNOWN', 'integer_millions': None}
    if not isinstance(literal, str) or re.fullmatch(r'[–−-]?(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)', literal) is None:
        raise ValueError('Expected signed integer-million literal or standalone printed dash')
    sign = -1 if literal[0] in '–−-' else 1
    value = int(literal.lstrip('–−-').replace(',', '')) * sign
    return {'literal': literal, 'status': 'PRINTED_INTEGER', 'integer_millions': value}


def arithmetic(rows):
    """Displayed arithmetic is explanatory; it cannot validate financial data."""
    indexed = {r['id']: r for r in rows}
    out = []
    for group, parts in SUMS.items():
        target = 'oci' if group == 'oci_attribution' else 'comprehensive' if group == 'comprehensive_attribution' else group
        for year in ('2022', '2021'):
            values = [indexed[k]['cells'][year]['integer_millions'] for k in parts]
            printed = indexed[target]['cells'][year]['integer_millions']
            computable = printed is not None and all(v is not None for v in values)
            computed = sum(values) if computable else None
            residual = printed - computed if computable else None
            out.append({'group': group, 'year': year, 'target': target, 'constituents': parts,
                'printed_total': printed, 'sum_of_printed_components': computed,
                'printed_minus_sum': residual,
                'status': 'UNKNOWN_COMPONENT' if not computable else 'EQUAL_PRINTED_TOTAL' if residual == 0 else 'PRINTED_RESIDUAL',
                'role': 'EXPLANATORY_ONLY'})
    return out


def evaluate(graph, incorporation, profile, root, *, expected_profile_sha256):
    keys = {'version', 'graph_sha256', 'incorporation_sha256', 'reviewer', 'source',
            'metadata', 'heading', 'entity', 'subtitle', 'unit', 'years', 'rows', 'footnotes',
            'rounding_context', 'selected_reading', 'financial_values_validated'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != digest(graph) or profile['incorporation_sha256'] != digest(incorporation)):
        raise ValueError('Pinned statement review or source/incorporation changed')
    if profile['selected_reading'] is not None or profile['financial_values_validated'] is not False:
        raise ValueError('Statement reading cannot adjudicate incorporation or validate accounts')
    reviewer = profile['reviewer']
    fields(reviewer, {'identity', 'basis', 'independent'}, {'identity', 'basis', 'independent'})
    if (not isinstance(reviewer['identity'], str) or not reviewer['identity'].strip()
            or reviewer['basis'] != 'AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported statement review authority')
    source = profile['source']
    skeys = {'document', 'page', 'path', 'sha256', 'image_path', 'image_sha256'}
    fields(source, skeys, skeys)
    if source['document'] != DOCUMENT or source['page'] != PAGE:
        raise ValueError('This reviewed table is BASF annual2022 page204')
    root = Path(root).resolve()
    for path_key, hash_key in (('path', 'sha256'), ('image_path', 'image_sha256')):
        name = source[path_key]
        path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != source[hash_key]:
            raise ValueError('Original statement PDF or inspected image changed')
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']):
        raise ValueError('Duplicate source occurrence')
    page = [u for u in graph['units'] if u['document'] == DOCUMENT and u['page'] == PAGE and u['visible']]
    if len(page) != 65 or any(u['source_sha256'] != source['sha256'] or u['text_sha256'] != digest(u['raw'].encode()) for u in page):
        raise ValueError('Reviewed complete page source inventory changed')
    used = []
    def full(a, page_number=PAGE):
        bounded = bind(graph, a)
        u = units[a['unit']]
        if (bounded['document'] != DOCUMENT or bounded['page'] != page_number or a['start'] != 0
                or a['end'] != len(u['raw']) or a['source_sha256'] != source['sha256']):
            raise ValueError('Complete original statement occurrence required')
        if page_number == PAGE:
            used.append(u['id'])
        return bounded
    def box(a):
        b = a['bbox']
        if (not isinstance(b, list) or len(b) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in b)
                or b[0] >= b[2] or b[1] >= b[3]):
            raise ValueError('Finite nonempty original geometry required')
        return b
    def overlap(a, b, axis):
        return max(a[axis], b[axis]) < min(a[axis + 2], b[axis + 2])
    if len(profile['metadata']) != 3:
        raise ValueError('Complete page metadata required')
    metadata = [full(a) for a in profile['metadata']]
    for key, literal in (('heading', 'Statement of Income and Expense Recognized in Equity'),
                         ('entity', 'BASF Group'), ('subtitle', 'Statement of comprehensive income a'), ('unit', 'Million €')):
        if full(profile[key])['quote'] != literal:
            raise ValueError('Statement identity or unit changed')
    fields(profile['years'], {'2022', '2021'}, {'2022', '2021'})
    years = {y: full(a) for y, a in profile['years'].items()}
    if any(a['quote'] != y for y, a in years.items()) or box(years['2022'])[2] >= box(years['2021'])[0]:
        raise ValueError('Year headings or column order changed')
    if [r.get('id') for r in profile['rows']] != list(ROWS):
        raise ValueError('Complete ordered statement row inventory required')
    rows, last_bottom = [], max(box(a)[3] for a in years.values())
    for row in profile['rows']:
        fields(row, {'id', 'label', 'cells'}, {'id', 'label', 'cells'})
        label = full(row['label'])
        if label['quote'] != ROWS[row['id']] or box(label)[1] <= last_bottom:
            raise ValueError('Statement row label or vertical order changed')
        last_bottom = box(label)[3]
        fields(row['cells'], {'2022', '2021'}, {'2022', '2021'})
        cells = {}
        for year, a in row['cells'].items():
            cell = full(a)
            if not overlap(box(label), box(cell), 1) or not overlap(box(years[year]), box(cell), 0) or box(label)[2] >= box(cell)[0]:
                raise ValueError('Cell does not align with its original row and year column')
            cells[year] = {**integer_millions(cell['quote']), 'source': cell}
        rows.append({'id': row['id'], 'label': label, 'cells': cells})
    if len(profile['footnotes']) != 2:
        raise ValueError('Both statement footnotes required')
    footnotes = [full(a) for a in profile['footnotes']]
    expected_notes = ['a For more information on other comprehensive income, see Note 20 on page 256 of the Notes',
                      'b For more information on the remeasurement of defined benefit plans, see Note 22 from page 261 onward']
    if [a['quote'] for a in footnotes] != expected_notes or any(box(a)[1] <= last_bottom for a in footnotes):
        raise ValueError('Statement footnote scope changed')
    if Counter(used) != Counter(u['id'] for u in page):
        raise ValueError('Every original page occurrence must be retained exactly once')
    rounding = [full(a, 6) for a in profile['rounding_context']]
    if [a['unit'] for a in rounding] != [DOCUMENT + ':p6:l' + str(i) for i in (8, 9, 10)]:
        raise ValueError('Complete original rounding context required')
    if 'Due to rounding, individual figures may not add up' not in rounding[0]['quote']:
        raise ValueError('Rounding context wording changed')
    if incorporation['status'] != 'UNRESOLVED' or incorporation['selected_reading'] is not None:
        raise ValueError('Existing incorporation uncertainty must be retained')
    alternatives = []
    for reading in incorporation['readings']:
        included = PAGE in reading['candidate_pages']
        alternatives.append({'id': reading['id'], 'condition': reading['condition'],
            'page204_in_candidate_scope': included, 'page204_reading_available': True,
            'status': 'CONDITIONAL_INCLUDED_SOURCE' if included else 'OUTSIDE_DETAILED_SOURCE_SELECTION',
            'legal_incorporation_established': False})
    if [a['page204_in_candidate_scope'] for a in alternatives] != [False, True]:
        raise ValueError('Expected unresolved detailed and broader incorporation alternatives')
    return {'version': VERSION, 'profile_sha256': digest(profile), 'page': PAGE, 'entity': 'BASF Group',
        'unit': 'Million €', 'years': years, 'rows': rows, 'footnotes': footnotes, 'rounding_context': rounding,
        'rounding_context_in_candidate_scopes': False,
        'rounding_interpretation': 'Printed residuals are descriptive; the warning neither proves a rounding model nor authorizes changing figures.',
        'arithmetic': arithmetic(rows), 'incorporation_alternatives': alternatives,
        'original_occurrences_accounted': len(used), 'printed_cells': len(rows) * 2,
        'page208_reviewed': False, 'independent_legal_acceptance': False,
        'financial_values_validated': False, 'selected_reading': None,
        'field_associations': 'SUPPLIED_EXPOSED_REVIEW', 'profile': deepcopy(profile)}


def consume(products, profile, root, *, expected_profile_sha256):
    from .successor import service
    answer = service.consume(products, root)
    result = evaluate(products['P1']['payload']['graph'], answer['incorporation'], profile, root,
                      expected_profile_sha256=expected_profile_sha256)
    return {'answer': answer, 'statement_review': result}
