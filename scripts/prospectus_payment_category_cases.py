"""Source-first hypothetical decisions, frozen before the new implementation."""
from copy import deepcopy
from datetime import datetime, timezone
import time
from scripts import prospectus_unicode_labels as prior

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/payment-categories-323'
PLAN = 'docs/plans/prospectus-payment-categories-2026-10-19.md'
METHOD = 'scripts/prospectus_payment_category_cases.py'
SOURCE = 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-026/selected-text.txt'
ORACLE = 'scripts/prospectus_payment_category_oracle.py'
TAX_POSITIVE = ('source_application_supported', 'specified_german_tax',
                'legally_required_withholding', 'additional_net_preservation_needed')
TAX_NEGATIVE = ('exception_a', 'exception_b', 'exception_c', 'exception_d',
                'exception_e', 'flat_tax_or_solidarity')
CONDITIONS = ('classification_supported', 'terms_reference_applies', 'where_applicable')
PRINCIPAL = ('redemption_amount', 'early_redemption_amount', 'call_redemption_amount',
             'premium', 'other_amount_payable_in_respect_notes')


def case(identity, component='section7_additional_amount'):
    return {'id': identity, 'kind': 'HYPOTHETICAL_DEVELOPMENT',
        'identity': {'instrument_id': 'BASF-SOURCE-BOUND-PLACEHOLDER', 'obligation_id': identity,
                     'tax_id': identity + ':single-tax' if component == 'section7_additional_amount' else None},
        'component': component, 'conditions': dict.fromkeys(CONDITIONS, True),
        'component_payable': None if component == 'section7_additional_amount' else True,
        'tax': {**dict.fromkeys(TAX_POSITIVE, True), **dict.fromkeys(TAX_NEGATIVE, False)}
               if component == 'section7_additional_amount' else None,
        'other_qualifying_note_payment': False,
        'payment': {'id': identity, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'route': 'a',
            'trigger_kind': 'DUE_DATE',
            'clock': {'instrument_id': 'BASF-SOURCE-BOUND-PLACEHOLDER', 'event_id': identity,
                'convention': 'ELAPSED_30_DAYS_INCLUSIVE', 'utc_offset': None,
                'trigger': {'value': '2024-01-01T00:00:00Z', 'role': 'DUE_DATE'},
                'assessment': {'value': '2024-02-02T00:00:00Z', 'role': 'ASSESSMENT'}, 'payment': None},
            'payment_state': 'UNPAID_THROUGH_ASSESSMENT', 'source_trigger_supported': True,
            'counting_convention_supported': True, 'payment_state_supported': True,
            'other_facts': {'default.notice': True, 'default.a.cured': False,
                'representative.a.entrusted': False, 'representative.a.express_permission': False},
            'amount_scenario': None}}


def expected(section7='YES', inclusion='YES', qualification='YES', premise='YES', complete='YES'):
    return {'section7': section7, 'inclusion': inclusion, 'qualification': qualification,
            'payment_premise': premise, 'complete_default': complete}


def authored():
    rows = []
    def add(row, result, reason):
        rows.append({'scenario': row, 'expected': result, 'reason': reason,
                     'origin': 'CONSTRUCTED_FACTS_ORIGINAL_SOURCE_READING'})
    row = case('all-open')
    row['conditions'] = dict.fromkeys(CONDITIONS)
    row['tax'] = dict.fromkeys((*TAX_POSITIVE, *TAX_NEGATIVE))
    row['other_qualifying_note_payment'] = None
    for k in ('source_trigger_supported', 'counting_convention_supported', 'payment_state_supported'):
        row['payment'][k] = None
    row['payment'].update(payment_state='UNKNOWN', other_facts={})
    row['payment']['clock'].update(trigger=None, assessment=None, payment=None, convention=None)
    add(row, expected(*(['UNKNOWN'] * 5)), 'Missing facts support neither a payment category nor actual default.')
    add(case('section7-inclusion'), expected(), 'All necessary gross-up premises stipulated; clock and notice separately supplied.')
    for field in (*TAX_POSITIVE, *TAX_NEGATIVE):
        excluded = field in TAX_NEGATIVE
        for suffix, value, status in [('veto', excluded, 'NO'), ('unknown', None, 'UNKNOWN'),
                                       ('conflict', 'conflict', 'CONFLICT')]:
            row = case('tax-' + field + '-' + suffix)
            row['tax'][field] = value
            add(row, expected(*([status] * 5)), 'Each whole-source qualification is retained, including unresolved application.')
    for component in PRINCIPAL:
        add(case(component, component), expected(section7=None), 'An expressly included payable principal component.')
        for suffix, value, status in [('unpayable', False, 'NO'), ('unknown', None, 'UNKNOWN'),
                                      ('conflict', 'conflict', 'CONFLICT')]:
            row = case(component + '-' + suffix, component)
            row['component_payable'] = value
            add(row, expected(None, status, status, status, status), 'A name cannot create the component payment obligation.')
    for field in CONDITIONS:
        for suffix, value, status in [('false', False, 'NO'), ('unknown', None, 'UNKNOWN'),
                                      ('conflict', 'conflict', 'CONFLICT')]:
            row = case(field + '-' + suffix)
            row['conditions'][field] = value
            add(row, expected('YES', status, status, status, status), 'Scope and applicability cannot be inferred from the label.')
    for suffix, other, status in [('unknown', None, 'UNKNOWN'), ('yes', True, 'YES'),
                                  ('conflict', 'conflict', 'CONFLICT')]:
        row = case('excluded-but-other-' + suffix)
        row['tax']['exception_b'] = True
        row['other_qualifying_note_payment'] = other
        add(row, expected('NO', 'NO', status, status, status), 'A failed inclusion route is not an exhaustive negative.')
    row = case('overlapping-qualifying-routes')
    row['other_qualifying_note_payment'] = True
    add(row, expected(), 'Two qualifying routes do not create two payments or a doubled amount.')
    row = case('unknown-inclusion-known-other')
    row['tax']['exception_b'] = None
    row['other_qualifying_note_payment'] = True
    add(row, expected('UNKNOWN', 'UNKNOWN', 'YES', 'YES', 'YES'), 'A supported independent route can establish qualification.')
    row = case('conflicting-inclusion-known-other')
    row['tax']['exception_b'] = 'conflict'
    row['other_qualifying_note_payment'] = True
    add(row, expected('CONFLICT', 'CONFLICT', 'CONFLICT', 'CONFLICT', 'CONFLICT'),
        'A relevant explicit conflict must not disappear behind a true alternative.')
    for name, key, value, premise, complete in [
        ('missing-clock-convention-support', 'counting_convention_supported', None, 'UNKNOWN', 'UNKNOWN'),
        ('payment-state-unknown', 'payment_state', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN')]:
        row = case(name)
        row['payment'][key] = value
        add(row, expected(premise=premise, complete=complete), 'A qualifying category cannot establish missing timing/performance facts.')
    row = case('exact-thirty-day-boundary')
    row['payment']['clock']['assessment']['value'] = '2024-01-31T00:00:00Z'
    add(row, expected(premise='NO', complete='NO'), 'The retained elapsed convention includes the exact thirty-day limit.')
    row = case('timely-payment')
    row['payment'].update(payment_state='FULL_PAYMENT')
    row['payment']['clock']['payment'] = {'value': '2024-01-31T00:00:00Z', 'role': 'FULL_PAYMENT'}
    add(row, expected(premise='NO', complete='NO'), 'Qualifying amounts paid within the stipulated window do not trigger that condition.')
    for name, facts, complete in [
        ('cured', {'default.a.cured': True}, 'NO'),
        ('no-notice', {'default.notice': False}, 'NO'),
        ('representative-restricted', {'representative.a.entrusted': True}, 'NO'),
        ('representative-permitted', {'representative.a.entrusted': True,
                                      'representative.a.express_permission': True}, 'YES')]:
        row = case(name)
        row['payment']['other_facts'].update(facts)
        add(row, expected(complete=complete), 'The complete source condition retains notice, cure and representative restrictions.')
    return rows


def main():
    from legalmath.prospectus.execution_authority import Authority
    assert not (PREP / 'cases.json').exists() and not (PREP / 'candidate.py').exists()
    began = time.monotonic()
    assert prior.read(AUTH / 'program.json')['revision'] == 322
    events = [e for e in Authority(ROOT).events() if e.get('attempt') == prior.rel(prior.HERE)]
    assert events[-1]['kind'] == 'RECORD'
    prior.save(PREP / 'accounting-start.json', {'prior': prior.costs(),
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    text = (ROOT / SOURCE).read_text()
    assert 'schließen, soweit\nanwendbar' in text and 'sämtliche gemäß § 7 zahlbaren' in text
    excerpts = [
        text[text.index('[(5)] Bezugnahmen'):text.index('[(6)] Hinterlegung')],
        text[text.index('Sämtliche auf die Schuldverschreibungen zu zahlenden Beträge'):text.index('§ 8\nVORLEGUNGSFRIST')],
        text[text.index('(a) die Emittentin Kapital oder Zinsen nicht'):text.index('(b) die Emittentin die ordnungsgemäße Erfüllung')]]
    rows = authored()
    prior.save(PREP / 'cases.json', {'version': 'payment-category-cases.v1', 'cases': rows,
                                   'actual_client_facts': False, 'source_excerpts': excerpts})
    prior.save(PREP / 'cases-freeze.json', {'cases_sha256': prior.sha(PREP / 'cases.json'),
        'authoring_method': METHOD, 'authoring_method_sha256': prior.sha(ROOT / METHOD),
        'plan': PLAN, 'plan_sha256': prior.sha(ROOT / PLAN),
        'source_files': {SOURCE: prior.sha(ROOT / SOURCE)},
        'independent_oracle': ORACLE, 'oracle_sha256': prior.sha(ROOT / ORACLE),
        'candidate_exists': False, 'frozen_at': datetime.now(timezone.utc).isoformat(),
        'temporal_separation': 'Same agent, separately authored cases before candidate; not blind annotation'})
    elapsed = time.monotonic() - began
    assert elapsed < 30 and sum(p.stat().st_size for p in PREP.rglob('*') if p.is_file()) < 1024**2
    prior.save(PREP / 'case-preparation.json', {'status': 'PASS', 'cases': len(rows),
        'wall_seconds': elapsed, 'command': ['.venv/bin/python', '-m', 'scripts.prospectus_payment_category_cases']})
    print({'status': 'PASS', 'cases': len(rows), 'wall_seconds': elapsed})


if __name__ == '__main__':
    main()
