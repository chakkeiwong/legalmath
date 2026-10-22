"""Inspect current source links without treating retained context as interpretation."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import time

from scripts import prospectus_h1_current_coverage as census

ROOT, BASE = census.ROOT, census.BASE
TEMP = ROOT / '.localresources/prospectus-preparation/h1-current-source-audit'
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
HERE = BASE / 'attempt-063'
read, ref, require = census.read, census.ref, census.require
PREFIX = '/source_statement_cells/'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':')).encode()).hexdigest()


def at(value, pointer):
    require(pointer.startswith('/'), 'Absolute JSON pointer required')
    for item in pointer[1:].split('/'):
        key = item.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            require(key.isdigit() and int(key) < len(value), 'Missing list target: ' + pointer)
            value = value[int(key)]
        else:
            require(isinstance(value, dict) and key in value, 'Missing field target: ' + pointer)
            value = value[key]
    return value


# Each source occurrence appears once. Targets express this review's association,
# not an assertion that the existing product already exposes that explicit link.
GROUPS = [
    (61, [0, 1], 'REPORT_IDENTITY_CONTEXT', ['group_structure_evidence']),
    (61, [2], 'CONSOLIDATED_NOTE_TITLE_CONTEXT', ['group_structure_evidence']),
    (61, [3], 'QUALIFIED_GLOBAL_UNIT_CONTEXT', ['group_structure_evidence']),
    (61, [4], 'NOTE_HEADING', ['group_structure_evidence']),
    (62, [1], 'DIRECT_BANK_DIRECTORY_INTRODUCTION', ['group_structure_evidence/directory/0']),
    (63, [1], 'SUBGROUP_DIRECTORY_INTRODUCTION', ['group_structure_evidence/directory/1', 'group_structure_evidence/directory/2']),
    (107, [1, 2], 'NOTE10_HEADING_AND_BALANCE_INTRODUCTION', ['cross_note_evidence/other_operating']),
    (123, [1], 'NOTE21_HEADING', ['cross_note_evidence/loans', 'cross_note_evidence/impairment_movements', 'cross_note_evidence/impairment_detail']),
    (124, [8, 9], 'IMPAIRMENT_MOVEMENT_INTRODUCTION', ['cross_note_evidence/impairment_movements']),
    (125, [1], 'IMPAIRMENT_DATED_TABLE_INTRODUCTION', ['cross_note_evidence/impairment_detail']),
    (125, [105], 'DECEMBER_TOTAL_COLUMN_GROUP', ['cross_note_evidence/impairment_detail/2009-12-31', 'cross_note_evidence/impairment_detail/columns']),
    (126, [1], 'NOTE22_HEADING', ['investment_hedges_evidence/tables/0', 'investment_hedges_evidence/tables/1']),
    (126, [2], 'HTM_BALANCE_INTRODUCTION', ['investment_hedges_evidence/tables/0']),
    (133, [1], 'NOTE27_HEADING', ['associates_evidence']),
    (138, [1, 2], 'NOTE32_HEADING_AND_BALANCE_INTRODUCTION', ['debt_securities/summary']),
    (138, [73, 74], 'DEBT_MOVEMENT_INTRODUCTION', ['debt_securities/movements']),
    (139, [6], 'OTHER_MOVEMENTS_FOOTNOTE_LABEL', ['debt_securities/movements/footnote_sources/0', 'debt_securities/movements/other_movements']),
    (139, [7], 'CD_NET_PRESENTATION_FOOTNOTE_LABEL', ['debt_securities/movements/footnote_sources/1', 'debt_securities/movements/certificates_of_deposit']),
    (144, [73, 74], 'NOTE35_HEADING_AND_BALANCE_INTRODUCTION', ['debt_context/summary']),
    (145, [1], 'SUBORDINATED_ISSUE_INTRODUCTION', ['debt_context/issues']),
    (145, [148, 149], 'SUBORDINATED_MOVEMENT_INTRODUCTION', ['debt_context/movements']),
    (154, [1], 'NOTE41_HEADING', ['related_parties_evidence']),
    (154, [5], 'ASSOCIATES_COMPANY_COLUMN', ['related_parties_evidence/directory/0']),
    (154, [62], 'ESFG_COMPANY_COLUMN', ['related_parties_evidence/directory/1']),
    (154, [103], 'ESFG_COMPANY_COLUMN', ['related_parties_evidence/directory/2']),
    (155, [3, 4], 'ESFG_CONTINUATION_COMPANY_COLUMNS', ['related_parties_evidence/directory/3']),
    (155, [134], 'ASSOCIATES_TABLE_HEADING', ['related_parties_evidence/tables/0']),
    (156, [13], 'JUNE_ASSET_COLUMN_GROUP', ['related_parties_evidence/tables/1/columns']),
    (156, [207], 'DECEMBER_ASSET_COLUMN_GROUP', ['related_parties_evidence/tables/2/columns']),
    (171, [1], 'NOTE46_HEADING', ['events_evidence/events']),
]

NOTES = {
    12: ('employee_benefits_notes_evidence', ['siba-rights', 'siba-share-movement', 'siba-costs', 'siba-recognition']),
    37: ('capital_preference_notes_evidence', ['treasury-allocation', 'treasury-table', 'treasury-sales-footnote']),
    38: ('reserves_nci_notes_evidence', ['nci-introduction', 'nci-movement-periods', 'nci-movement']),
}
EQUITY = [(13, 19, 37), (14, 20, 12), (15, 21, 38),
          (23, 352, 37), (24, 353, 12), (25, 354, 38),
          (35, 375, 37), (36, 376, 12), (37, 377, 38)]


def uid(page, order):
    return f'{census.DOCUMENT}:p{page}:l{order}'


def source(units, page, order):
    item = units[uid(page, order)]
    return {k: item[k] for k in ('id', 'document', 'source_sha256', 'page', 'order', 'bbox')} | {'quote': item['raw']}


def targets(sections, paths):
    require(bool(paths), 'Missing association targets')
    result = []
    for path in paths:
        absolute = PREFIX + path
        value = at(sections, absolute)
        require(value is not None and value != [] and value != {}, 'Empty association target')
        result.append({'path': absolute, 'sha256': digest(value)})
    return result


def check_layout(reading, units):
    def u(page, line):
        return units[uid(page, line)]
    imp = reading['cross_note_evidence']['impairment_detail']
    require(imp['columns'][4:] == ['total_gross', 'total_impairment', 'net_loans'], 'Wrong total column group')
    heading, row = u(125, 105), u(125, 104)
    require(heading['raw'] == row['raw'] == 'Total' and heading['bbox'][0] > 400
        and row['bbox'][0] < 150 and heading['bbox'][1] < u(125, 68)['bbox'][1] < row['bbox'][1],
        'Column heading confused with total row')
    require(imp['2009-12-31']['rows'][-1]['label']['id'] == row['id'], 'Wrong December total row')
    movements = reading['debt_securities']['movements']
    for marker, text, index in ((6, 54, 0), (7, 55, 1)):
        require(abs(u(139, marker)['bbox'][1] - u(139, text)['bbox'][1]) < 3
            and movements['footnote_sources'][index] == {'id': uid(139, text), 'quote': u(139, text)['raw']},
            'Wrong debt footnote association')
    require('a)' in u(139, 14)['raw'] and movements['certificates_of_deposit']['marker']['id'] == uid(139, 28)
        and movements['certificates_of_deposit']['row_index'] == 1
        and movements['certificates_of_deposit']['column'] == 'repayments', 'Wrong debt footnote referent')
    require([x['section'] for x in reading['group_structure_evidence']['directory']] ==
        ['DIRECT_BANK_TABLE', 'SUBGROUP_TABLE', 'SUBGROUP_TABLE'], 'Wrong consolidation directory scopes')
    categories = [x['category'] for x in reading['related_parties_evidence']['directory']]
    require(categories[0] == 'Associates' and len(set(categories[1:])) == 1
        and 'ESFG' in categories[1], 'Wrong related-party directory scopes')
    for index, period in ((1, '2010-06-30'), (2, '2009-12-31')):
        columns = reading['related_parties_evidence']['tables'][index]['columns']
        require(columns == [period + '/' + label for label in ('Loans and advances to banks', 'Loans',
            'Securities', 'Other', 'Total assets', 'Guarantees', 'Liabilities', 'Income', 'Expenses')],
            'Guarantees incorrectly included in asset column group')
    return {'status': 'PASS', 'column_heading_not_total_row': True,
            'separate_footnotes': True, 'directory_scopes_preserved': True,
            'guarantees_outside_asset_group': True}


def note_target(reading, note, field, keys):
    require(reading[field].get('notes') == [note], 'Wrong referenced note target')
    clauses = reading[field]['clauses']
    paths = []
    for key in keys:
        indices = [i for i, clause in enumerate(clauses) if clause['key'] == key]
        require(len(indices) == 1, 'Missing or duplicate referenced-note clause')
        paths.append(field + '/clauses/' + str(indices[0]))
    return paths


def association_rows(sections, units, inventory):
    residual = {row['id']: row for row in inventory['residual_context_items']}
    rows = []
    for page, orders, role, paths in GROUPS:
        linked = targets(sections, paths)
        for order in orders:
            item = source(units, page, order)
            current = residual[item['id']]
            require(current['quote'] == item['quote'] and not current['current_direct']
                and current['current_context'], 'Residual population or current delivery changed')
            for context in current['current_context']:
                at(sections, context['path'])
            rows.append({'source': item, 'reviewed_role': role,
                'current_context_paths': [r['path'] for r in current['current_context']],
                'reviewed_targets': linked,
                'existing_delivery': 'RETAINED_CONTEXT_WITH_RELEVANT_SEMANTIC_FIELDS',
                'explicit_source_to_target_link_in_existing_answer': False,
                'meaning_independently_proved': False})
    require(len(rows) == len(residual) == 38 and {r['source']['id'] for r in rows} == set(residual),
            'Original 38 residual source occurrences not exactly accounted for')
    return rows


def equity_rows(reading, units, sections):
    equity = reading['equity_statement_evidence']
    rows = []
    for index, order, note in EQUITY:
        row = equity['rows'][index]
        item = source(units, 59, order)
        require(row['label_source'] == {'id': item['id'], 'quote': item['quote']}, 'Wrong equity source row')
        require('seeNote' + str(note) in ''.join(item['quote'].split()), 'Wrong source-specific equity note reference')
        field, keys = NOTES[note]
        linked = targets(sections, note_target(reading, note, field, keys))
        rows.append({'source': item, 'current_reference_path': PREFIX + f'equity_statement_evidence/rows/{index}/label_source',
            'note': note, 'period': row['period'], 'reviewed_targets': linked,
            'target_available': True, 'financial_reconciliation_established': False,
            'existing_resolution_status': equity['distinctions']['note_reference_resolution']})
    metadata = [i for i, value in enumerate(equity['metadata_sources']) if value['id'] == uid(59, 460)]
    require(len(metadata) == 1, 'Missing preference dividend note reference')
    item = source(units, 59, 460)
    require('5.58%' in ''.join(item['quote'].split()) and 'seeNote37' in ''.join(item['quote'].split()),
            'Wrong preference dividend footnote')
    field = NOTES[37][0]
    linked = targets(sections, note_target(reading, 37, field,
        ['preference-fixed-dividend', 'reported-dividend', 'preference-guarantee']))
    rows.append({'source': item, 'current_reference_path': PREFIX + 'equity_statement_evidence/metadata_sources/' + str(metadata[0]),
        'note': 37, 'reviewed_targets': linked, 'target_available': True,
        'relationship': 'PREFERENCE_SHARE_DIVIDEND_FOOTNOTE_NOT_PROSPECTUS_NOTE_COUPON',
        'financial_reconciliation_established': False,
        'existing_resolution_status': equity['distinctions']['note_reference_resolution']})
    return rows


def adverse_checks(reading, units, sections):
    refused = []
    def attempt(name, action, expected):
        try:
            action()
        except ValueError as exc:
            require(str(exc) == expected, 'Unexpected diagnostic failure for ' + name)
            refused.append({'case': name, 'reason': str(exc)})
        else:
            raise ValueError('Association diagnostic accepted ' + name)
    changed_units = dict(units)
    changed_units[uid(125, 105)] = {**units[uid(125, 105)], 'bbox': units[uid(125, 104)]['bbox']}
    attempt('heading-as-data-row', lambda: check_layout(reading, changed_units), 'Column heading confused with total row')
    bad = deepcopy(reading)
    bad['debt_securities']['movements']['footnote_sources'].reverse()
    attempt('swapped-debt-footnotes', lambda: check_layout(bad, units), 'Wrong debt footnote association')
    bad_columns = deepcopy(reading)
    bad_columns['related_parties_evidence']['tables'][1]['columns'][4:6] = list(reversed(
        bad_columns['related_parties_evidence']['tables'][1]['columns'][4:6]))
    attempt('guarantees-as-assets', lambda: check_layout(bad_columns, units),
            'Guarantees incorrectly included in asset column group')
    attempt('wrong-note-target', lambda: note_target(reading, 12, NOTES[37][0], NOTES[37][1]), 'Wrong referenced note target')
    attempt('missing-target', lambda: targets(sections, ['missing_note_evidence']),
            'Missing field target: ' + PREFIX + 'missing_note_evidence')
    return {'status': 'PASS', 'refused': refused}


def run():
    tick = time.monotonic()
    target = TEMP / 'associations-063.json'
    require(not target.exists(), 'Preserve prior association diagnostic; no unchanged retry')
    outcome = {'status': 'FAIL', 'plan': census.PLAN}
    try:
        def production():
            return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / 'src/legalmath').rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
        expected_production = read(AUTH / 'reviews/h1-combined-consumer-426/freeze.json')['production']
        require(production() == expected_production, 'Current production differs from recorded delivery')
        # Authenticate the final snapshot and authority record, not just file names.
        inventory = read(TEMP / 'snapshot-063.json')
        require(inventory['status'] == 'REFERENCE_INVENTORY_COMPLETE_WITH_MEANING_UNCHECKED'
            and not inventory['provisional'], 'Final current reference inventory required')
        require(ref(ROOT / inventory['method']['path']) == inventory['method'], 'Census method changed')
        require(ref(HERE / 'ordinary-answer.json.gz') == inventory['actual_answer'], 'Current answer changed')
        manifest = read(HERE / 'outputs.json')
        require(ref(HERE / 'ordinary-answer.json.gz')['sha256'] == manifest['ordinary-answer.json.gz']
            and ref(HERE / 'result.json')['sha256'] == manifest['result.json'], 'Sealed result changed')
        require(read(HERE / 'result.json')['status'] == 'PASS', 'Sealed current PASS required')
        events = [read(p) for p in (AUTH / 'history').glob('*.json')]
        recorded = [e for e in events if e.get('attempt') == str(HERE.relative_to(ROOT)) and 'outputs_sha256' in e]
        require(recorded and any(e['outputs_sha256'] == ref(HERE / 'outputs.json')['sha256'] for e in recorded),
            'Authority-recorded current result required')
        graph_path = BASE / 'attempt-007/products.json.gz'
        require(ref(graph_path) == inventory['original_graph'], 'Original graph changed')
        graph = read(graph_path)['P1']['payload']['graph']
        units = {u['id']: u for u in graph['units']}
        require(len(units) == len(graph['units']), 'Duplicate original source identity')
        answer = read(HERE / 'ordinary-answer.json.gz')
        reading = answer['answer']['source_statement_cells']
        sections = {'source_statement_cells': reading} | {name: answer[name] for name in
            ('cash_flow_review', 'risk_table_review', 'h1_scope_review', 'h1_individual_unit_review')}
        # Validate source intervals and identities with the already reviewed scanner.
        checked = list(census.references(sections, units))
        layout = check_layout(reading, units)
        residual = association_rows(sections, units, inventory)
        equity = equity_rows(reading, units, sections)
        adverse = adverse_checks(reading, units, sections)
        require(production() == expected_production, 'Production changed during association diagnostic')
        outcome.update(status='SUPPLIED_ASSOCIATIONS_CHECKED_CURRENT_LINK_GAPS_RETAINED',
            original_graph=ref(graph_path), actual_answer=ref(HERE / 'ordinary-answer.json.gz'),
            inventory=ref(TEMP / 'snapshot-063.json'), source_review=ref(TEMP / 'SOURCE-ASSOCIATIONS.md'),
            reviewed_equity_image=ref(ROOT / '.localresources/prospectus-preparation/h1-equity-consumer-061/source-preparation/page-59.png'),
            residual_associations=residual, equity_references=equity, layout_checks=layout,
            adverse_controls=adverse, checked_reference_occurrences=len(checked),
            finding='Source text and relevant meanings are delivered; explicit current links and note-availability status remain to be delivered.',
            source_only_context_is_not_interpretation=True, production_changed=False,
            production_sha256=digest(expected_production),
            scope={'source_specific_supplied_review': True, 'financial_reconciliation_established': False,
                'source_authenticity_established': False, 'legal_incorporation_selected': False,
                'automatic_interpretation_proved': False, 'original_task_complete': False})
    except Exception as exc:
        outcome['error'] = {'type': type(exc).__name__, 'reason': str(exc)}
    outcome['seconds'] = time.monotonic() - tick
    outcome['method'] = ref(Path(__file__))
    raw = (json.dumps(outcome, ensure_ascii=False, indent=2) + '\n').encode()
    require(len(raw) < 4 * 1024**2, 'Association diagnostic exceeds reservation')
    with target.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': outcome['status'], 'seconds': outcome['seconds'],
        'bytes': len(raw), 'error': outcome.get('error'), 'output': str(target.relative_to(ROOT))}))


if __name__ == '__main__':
    require(len(sys.argv) == 1, 'No unreviewed arguments')
    run()
