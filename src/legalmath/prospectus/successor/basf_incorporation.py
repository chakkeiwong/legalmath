"""Two unresolved BASF incorporation readings with exact source identities."""
from copy import deepcopy

from . import basf
from .admissions import review
from .anchors import bind, fields
from .contracts import digest
from .occurrences import anchor

VERSION = 'basf-incorporation-review.v1'
ANNUAL = 'basf-annual-2022-exchange'
SUPPLEMENT = 'basf-supplement-february-2023-exchange'
DEPENDENCY = 'incorporation:basf-2022-financial-statements-scope'
RANGES = [[197, 202], [203, 203], [205, 206], [207, 207], [209, 290]]
DISCREPANCY = ('Overall heading ends at 209; explicit Notes range ends at 290. '
               'Both preserved. Only enumerated detailed ranges admitted; full incorporation interpretation remains unresolved.')


def expected(graph, construction):
    if not construction or construction.get('annual_range_discrepancy') != DISCREPANCY:
        raise ValueError('Protected BASF incorporation discrepancy changed')
    raw = {u['id']: u for u in graph['units']}

    def sources(document, page, numbers):
        return [anchor(raw[f'{document}:p{page}:l{i}']) for i in numbers]

    groups = {
        'general_incorporation': sources(SUPPLEMENT, 12, [3, 4, 5, 7, 8]),
        'table_instruction': sources(SUPPLEMENT, 12, [9, 10]),
        'printed_heading': sources(SUPPLEMENT, 12, [19, 20]),
        'enumeration': sources(SUPPLEMENT, 12, range(21, 26)),
        'unlisted_portions_limit': sources(basf.KEY, 191, range(48, 51)),
        'annual_contents': sources(ANNUAL, 195, range(6, 21)),
        'disputed_statement_headings': sources(ANNUAL, 204, [3]) + sources(ANNUAL, 208, [3]),
        'audited_statement_description': sources(ANNUAL, 197, range(9, 19)),
        'auditor_language_priority': sources(ANNUAL, 197, [32]),
    }
    if ([s['quote'] for s in groups['enumeration']] != [
            'Consolidated balance sheet (p. 205 – p. 206)',
            'Consolidated statement of income (p. 203)',
            'Consolidated statement of cash flows (p. 207)',
            'Notes (p. 209 – p. 290)', "Auditors' report (p. 197 – p. 202)"] or
            groups['printed_heading'][1]['quote'] != '(p. 195 – p. 209 )' or
            'Solely the original text in German language is authoritative.' not in groups['auditor_language_priority'][0]['quote']):
        raise ValueError('Reviewed BASF source wording or source extent changed')
    detailed = sorted({p for a, b in RANGES for p in range(a, b + 1)})
    full = list(range(197, 291))
    pages = []
    for page in full:
        units = [u for u in graph['units'] if u['document'] == ANNUAL and u['page'] == page]
        if not units or len({u['source_sha256'] for u in units}) != 1:
            raise ValueError('Required annual source page missing or mixed')
        pages.append({'document': ANNUAL, 'source_sha256': units[0]['source_sha256'], 'page': page,
                      'units_sha256': digest(units), 'role': 'SOURCE_IDENTITY_ONLY'})
    return {'source_groups': groups, 'target_pages': pages, 'detailed_ranges': RANGES,
        'readings': [
            {'id': 'detailed-enumeration', 'candidate_pages': detailed,
             'condition': 'The express cross-reference list and exclusion of unlisted portions control scope.'},
            {'id': 'full-financial-statements', 'candidate_pages': full,
             'condition': 'The general incorporation of audited financial statements includes the two statements omitted from the detailed list.'}],
        'disputed_pages': [204, 208], 'literal_heading_pages': list(range(195, 210)),
        'front_matter_scope': {'pages': [195, 196], 'status': 'UNRESOLVED'},
        'status': 'UNRESOLVED', 'selected_reading': None,
        'independent_legal_acceptance': False, 'financial_values_validated': False}


def admit(graph, construction, admission):
    data = expected(graph, construction)
    required = set(data) | {'version', 'graph_sha256', 'construction_sha256', 'review'}
    fields(admission, required, required)
    if (admission['version'] != VERSION or admission['graph_sha256'] != digest(graph) or
            admission['construction_sha256'] != digest(construction)):
        raise ValueError('BASF incorporation source or construction changed')
    review(admission['review'])
    for name, value in data.items():
        if admission[name] != value:
            raise ValueError('BASF unresolved incorporation review changed: ' + name)
    for sources in admission['source_groups'].values():
        for source in sources:
            bind(graph, source)
    return {'version': 'admitted-basf-incorporation.v1', 'input_sha256': digest(admission),
            'review': deepcopy(admission['review']), **deepcopy(data)}


def dependency(admitted):
    return {'id': DEPENDENCY, 'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED',
            'reason': 'The supplement and base limitation support competing incorporation readings; no reading is adjudicated.',
            'review_sha256': digest(admitted)}


def explain(admitted):
    return {**deepcopy(admitted),
        'explanation': 'The detailed list covers 92 annual-report pages. A reading of the general incorporation sentence as covering all financial statements would add pages 204 and 208. The printed heading says 195–209, while its Notes entry says 209–290. Legal scope remains unresolved.',
        'restriction': 'The base prospectus expressly excludes information not listed in its cross-reference list; the broader reading needs an interpretation of the supplement that addresses this restriction.',
        'language': 'The incorporated report is English, but its auditor report says the German original alone is authoritative.',
        'effect': 'The page lists identify competing source scopes. They add no operative debt clause, verified financial amount or actual event.'}
