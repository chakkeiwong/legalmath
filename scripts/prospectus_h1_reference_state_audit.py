"""Finite current-reference audit; original text presence is not semantic closure."""
from collections import Counter
from copy import deepcopy
import json
import re
import sys
import time
from pathlib import Path

from scripts import prospectus_h1_relationship_runner_repair as repair
from scripts import prospectus_h1_association_audit as association

common = repair.common
ROOT, BASE, AUTH = repair.ROOT, repair.BASE, repair.AUTH
read, save, require, sha, rel = common.read, common.save, common.require, common.sha, common.rel
PLAN = 'docs/plans/prospectus-h1-reference-state-audit-2026-10-22.md'
TEMP = ROOT / '.localresources/prospectus-preparation/h1-reference-state-audit'
PREFIX = '/answer/source_statement_cells/'
DOCUMENT = 'bes-interim-h1-2010'
at = association.at

# These five relationships were inspected against the original prose and the
# original mappers. Targets identify available supplied readings, not legal truth.
SPECS = [
    {'id': 'note21-note42', 'flag': 'cross_note_evidence/securitised_loans/note42_resolved',
     'sources': [(124, 3), (124, 5)], 'note': '42',
     'targets': ['securitisation_evidence/transactions', 'securitisation_evidence/reported_treatment',
                 'securitisation_evidence/consolidation_impact', 'securitisation_evidence/note21_comparison'],
     'current_availability': 'Relevant Note 42 transactions, treatment and reported amounts are delivered.',
     'remaining': 'Displayed loan precision is not financial accuracy; loan assets and debt liabilities differ.'},
    {'id': 'note21-policy2.2', 'flag': 'cross_note_evidence/securitised_loans/policy2_2_resolved',
     'sources': [(124, 4)], 'note': '2.2',
     'targets': ['securitisation_evidence/policy2_2', 'securitisation_evidence/reported_treatment'],
     'current_availability': 'The referenced historical consolidation policy and reported treatment are delivered.',
     'remaining': 'Reading a reported policy does not verify current standards, ownership or derecognition.'},
    {'id': 'note35-note10', 'flag': 'debt_context/buyback_gains/note10_reference_resolved',
     'sources': [(145, 194)], 'note': '10',
     'targets': ['cross_note_evidence/other_operating/rows/1', 'cross_note_evidence/buyback_comparison'],
     'current_availability': 'The referenced income row and explicit comparison are delivered.',
     'remaining': 'Amounts and comparator periods are not reconciled; no typo or rounding policy is established.'},
    {'id': 'note32-note21', 'flag': 'debt_securities/covered_bonds/reported_collateral/note21_resolved',
     'sources': [(138, 71), (138, 72)], 'note': '21',
     'targets': ['cross_note_evidence/collateral_comparison', 'debt_securities/covered_bonds/reported_collateral'],
     'current_availability': 'Both dated reported collateral disclosures and their comparison are delivered.',
     'remaining': 'Agreement of reported figures does not establish legal eligibility or a holder privilege.'},
    {'id': 'note41-note1', 'flag': 'related_parties_evidence/dependency_resolution/note1_group_structure_resolved',
     'sources': [(154, 2), (154, 3)], 'note': '1',
     'targets': ['group_structure_evidence/directory', 'group_structure_evidence/clauses',
                 'group_structure_evidence/reported_interpretation', 'group_structure_evidence/dependency_resolution'],
     'current_availability': 'The referenced Note 1 group directory and its qualifications are delivered.',
     'remaining': 'Related parties, subsidiaries, votes, control and entity identity remain distinct.'},
]


def source(units, page, order):
    u = units[f'{DOCUMENT}:p{page}:l{order}']
    return {k: u[k] for k in ('id', 'document', 'source_sha256', 'page', 'order', 'bbox')} | {'quote': u['raw']}


def state_rows(answer, units):
    rows = []
    for spec in SPECS:
        require(at(answer, PREFIX + spec['flag']) is False, 'Historical unresolved flag changed')
        sources = [source(units, *loc) for loc in spec['sources']]
        text = ' '.join(s['quote'] for s in sources)
        require(re.search(r'\bNotes?\s+(?:32 and )?' + re.escape(spec['note']) + r'\b', text),
                'Expected original note reference missing')
        targets = []
        for suffix in spec['targets']:
            path = PREFIX + suffix
            value = at(answer, path)
            require(value is not None and value != [] and value != {}, 'Empty current target')
            targets.append({'path': path, 'sha256': common.compact_digest(value)})
        rows.append({**{k: v for k, v in spec.items() if k not in ('sources', 'targets', 'flag')},
            'historical_flag': {'path': PREFIX + spec['flag'], 'value': False},
            'sources': sources, 'targets': targets, 'target_available': True,
            'historical_flag_retained': True, 'financial_reconciliation_established': False,
            'legal_effect_established': False})
    return rows


def check_states(answer, units, proposed=None):
    expected = state_rows(answer, units)
    require(proposed is None or proposed == expected, 'Current reference relationship changed')
    s = answer['answer']['source_statement_cells']
    sec = s['securitisation_evidence']
    compare = sec['note21_comparison']
    require(compare['reference_read'] is True and compare['financial_accuracy_proved'] is False
        and compare['loan_asset_equals_debt_liability'] is False
        and sec['reported_treatment']['consolidation_equals_derecognition'] is False
        and sec['reported_treatment']['actual_legal_ownership_established'] is False,
        'Securitisation limitation lost')
    buyback = s['cross_note_evidence']['buyback_comparison']
    require(buyback['reference_read'] is True and all(buyback[k] is False
        for k in ('amounts_and_periods_reconciled', 'typo_established', 'rounding_policy_established')),
        'Buyback reconciliation invented')
    collateral = s['cross_note_evidence']['collateral_comparison']
    require(collateral['source_reference_read'] is True and collateral['reported_amounts_agree'] is True
        and collateral['legal_eligibility_established'] is False
        and collateral['particular_holder_privilege_established'] is False, 'Collateral legal effect invented')
    group = s['group_structure_evidence']
    require(group['dependency_resolution']['note1_source_delivered'] is True
        and group['dependency_resolution']['note41_original_unresolved_flag_retained'] is True
        and group['dependency_resolution']['all_group_relationships_legally_proven'] is False
        and group['dependency_resolution']['source_authority_or_incorporation_resolved'] is False
        and all(group['distinctions'][k] is False for k in
            ('economic_interest_equals_direct_voting_power', 'identical_names_establish_identity', 'consolidation_proves_guarantee'))
        and s['related_parties_evidence']['distinctions']['related_means_consolidated'] is False,
        'Related-party distinction lost')
    return expected


def refusal_checks(answer, units):
    # Copy only the branches mutated, keeping the large prior answer shared.
    def changed(section, path, value):
        inner = answer['answer']
        cells = inner['source_statement_cells']
        branch = deepcopy(cells[section])
        target = branch
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return {**answer, 'answer': {**inner, 'source_statement_cells': {**cells, section: branch}}}
    wrong = deepcopy(state_rows(answer, units))
    wrong[0]['targets'] = wrong[2]['targets']
    cases = [('wrong-note-target', answer, wrong, 'Current reference relationship changed'),
        ('flipped-history', changed('cross_note_evidence', ['securitised_loans', 'note42_resolved'], True),
         None, 'Historical unresolved flag changed'),
        ('loan-debt-equality', changed('securitisation_evidence', ['note21_comparison', 'loan_asset_equals_debt_liability'], True),
         None, 'Securitisation limitation lost'),
        ('invented-buyback-reconciliation', changed('cross_note_evidence', ['buyback_comparison', 'amounts_and_periods_reconciled'], True),
         None, 'Buyback reconciliation invented'),
        ('collateral-eligibility', changed('cross_note_evidence', ['collateral_comparison', 'legal_eligibility_established'], True),
         None, 'Collateral legal effect invented'),
        ('related-is-consolidated', changed('related_parties_evidence', ['distinctions', 'related_means_consolidated'], True),
         None, 'Related-party distinction lost')]
    refused = []
    for name, candidate, rows, message in cases:
        try:
            check_states(candidate, units, rows)
        except ValueError as exc:
            require(str(exc) == message, 'Unexpected reference-state refusal')
            refused.append({'case': name, 'reason': str(exc)})
        else:
            raise ValueError('Audit accepted ' + name)
    return refused


NOTE_WORD = re.compile(r'\bnotes?\b', re.I)
NOTE_NUMBER = re.compile(r'\bnotes?\s+(\d+(?:\.\d+)?)', re.I)
SPLIT_NEXT = {(95, 19): (95, 20), (121, 118): (121, 119), (161, 1): (161, 2)}
HISTORICAL_LABELS = {
    'afs_disclosures_evidence/dependency_resolution/note18': 'PARTIAL_CONTEXT_ONLY',
    'afs_disclosures_evidence/dependency_resolution/note41': 'UNRESOLVED',
    'critical_judgments_evidence/dependency_resolution/tax_and_pension_full_notes': 'UNRESOLVED_OR_RETAINED_SUPPLEMENT_ONLY',
    'financial_policies_evidence/source_dependencies/Note23': 'ORIGINAL_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED',
    'investment_hedges_evidence/source_dependencies/Note39': 'FULL_INTERPRETATION_NOT_ESTABLISHED',
    'investment_hedges_evidence/source_dependencies/Note7': 'FULL_INTERPRETATION_NOT_ESTABLISHED',
}


def prose_inventory(units):
    rows = []
    for u in sorted(units.values(), key=lambda u: (u['page'], u['order'], u['id'])):
        if u['document'] != DOCUMENT or not 51 <= u['page'] <= 173 or not NOTE_WORD.search(u['raw']):
            continue
        raw = u['raw']
        sources = [{k: u[k] for k in ('id', 'document', 'source_sha256', 'page', 'order', 'bbox')} | {'quote': raw}]
        if re.match(r'^NOTE\s+\d', raw):
            category = 'NOTE_HEADING'
        elif (u['page'], u['order']) in SPLIT_NEXT:
            sources.append(source(units, *SPLIT_NEXT[u['page'], u['order']]))
            category = 'REVIEWED_SPLIT_REFERENCE'
        elif NOTE_NUMBER.search(raw):
            category = 'INLINE_NUMBERED_REFERENCE_REQUIRES_TARGET_REVIEW'
        elif re.search(r'\bMedium Term Notes\b', raw, re.I):
            category = 'INSTRUMENT_NAME'
        else:
            category = 'GENERIC_OR_UNCLASSIFIED_MENTION'
        rows.append({'category': category, 'sources': sources,
            'numbers_not_automatically_normalized': True, 'target_meaning_resolved': False})
    return rows


def statement_inventory(answer, units):
    rows = []
    sections = answer['answer']['source_statement_cells']
    tables = [(PREFIX + 'tables/' + name, table['rows']) for name, table in sections['tables'].items()]
    tables.append(('/cash_flow_review', answer['cash_flow_review']['rows']))
    for path, table in tables:
        for index, row in enumerate(table):
            for note_index, note in enumerate(row.get('notes', [])):
                # Statement notes use either id/quote or exact span anchors.
                uid = note.get('id', note.get('unit'))
                require(uid in units, 'Unknown statement note occurrence')
                original = units[uid]
                start, end = note.get('start', 0), note.get('end', len(original['raw']))
                require(type(start) is int and type(end) is int and 0 <= start < end <= len(original['raw']) and
                    original['raw'][start:end] == note['quote'], 'Changed statement note quote')
                if 'unit' in note:
                    require(note['document'] == original['document'] and note['source_sha256'] == original['source_sha256']
                        and note.get('bbox', original['bbox']) == original['bbox'], 'Changed statement note edition or geometry')
                rows.append({'path': path + f'/rows/{index}/notes/{note_index}',
                    'source': note, 'row_label': row.get('label'),
                    'category': 'STATEMENT_NOTE_COLUMN', 'target_meaning_resolved': False})
    return rows


def main():
    tick = time.monotonic()
    target = TEMP / 'reference-state-065.json'
    require(not target.exists(), 'Preserve the first diagnostic; no unchanged retry')
    auth = common.authority()
    require(read(AUTH / 'program.json')['revision'] == 428, 'Expected revision 428')
    require(read(repair.HERE / 'result.json')['status'] == 'PASS', 'Successful 065 required')
    require(any(e.get('attempt') == rel(repair.HERE) and
        e.get('outputs_sha256') == sha(repair.HERE / 'outputs.json') for e in auth.events()), 'Recorded 065 required')
    for location in (repair.OLD_HERE, repair.HERE):
        require(all(sha(location / name) == value for name, value in read(location / 'outputs.json').items()),
            'Changed sealed actual trial')
    production = common.production()
    freeze = read(repair.PREP / 'freeze.json')
    require(production == freeze['production'], 'Current production changed')
    require(all(sha(ROOT / name) == value for name, value in freeze['bindings'].items()), 'Changed retained source or method')
    answer = repair.checked_answer('ordinary')
    require(answer == repair.checked_answer('installed'), 'Current installed answer differs')
    graph = read(BASE / 'attempt-007/products.json.gz')['P1']['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    require(len(units) == len(graph['units']), 'Duplicate original source identity')
    states = check_states(answer, units)
    controls = refusal_checks(answer, units)
    historical_labels = []
    for suffix, expected in HISTORICAL_LABELS.items():
        path = PREFIX + suffix
        require(at(answer, path) == expected, 'Historical pending label changed')
        historical_labels.append({'path': path, 'value': expected, 'current_relationship': 'PENDING_SOURCE_REVIEW'})
    prose, columns = prose_inventory(units), statement_inventory(answer, units)
    require(sum(row['category'] == 'REVIEWED_SPLIT_REFERENCE' for row in prose) == 3,
        'Reviewed split references missing')
    require(any(row['source'].get('id', row['source'].get('unit', '')).startswith(DOCUMENT + ':p58:')
        for row in columns), 'Statement schema omitted')
    require(common.production() == production, 'Diagnostic changed production')
    result = {'status': 'FIVE_CURRENT_REFERENCE_STATES_CHECKED_WIDER_INVENTORY_UNRESOLVED',
        'plan': PLAN, 'method': common.ref(Path(__file__)), 'source_review': common.ref(TEMP / 'SOURCE-REVIEW.md'),
        'original_graph': common.ref(BASE / 'attempt-007/products.json.gz'),
        'actual_ordinary': common.ref(repair.OLD_HERE / 'ordinary-answer.json.gz'),
        'actual_installed': common.ref(repair.HERE / 'installed-answer.json.gz'),
        'states': states, 'adverse_controls': controls,
        'further_historical_labels': historical_labels,
        'prose_note_mentions': prose, 'prose_categories': dict(Counter(row['category'] for row in prose)),
        'statement_note_columns': columns,
        'inventory_scope': 'All literal note/notes units on pages51-173 plus delivered statement/cash note fields; not all implicit references',
        'remaining': ['Current explanation relating the five historical flags to later target availability',
            'Six additional historical dependency labels need substantive current association review',
            'Review inline and statement references against relevant target clauses',
            'No exhaustive semantic coverage, implicit-reference or source-authority conclusion'],
        'production_changed': False, 'original_task_complete': False, 'seconds': time.monotonic() - tick}
    save(target, result)
    return {'status': result['status'], 'checked_states': len(states), 'adverse_controls': len(controls),
        'prose_categories': result['prose_categories'], 'statement_note_columns': len(columns),
        'seconds': result['seconds'], 'bytes': target.stat().st_size, 'output': rel(target)}


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    print(json.dumps(main()), flush=True)
