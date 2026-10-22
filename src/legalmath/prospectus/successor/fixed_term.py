"""Conditional annual fixed coupons through maturity, excluding redemption."""
from copy import deepcopy

from .anchors import bind, fields
from .contracts import digest
from .fixed_coupon import calculate as coupon
from ..semantics import exact


ASSUMPTIONS = {'unchanged_holdings', 'unchanged_note_form', 'no_early_redemption',
               'no_default', 'no_principal_reduction', 'no_tax', 'no_currency_change',
               'timely_presentation'}


def calculate(admitted, calculation, graph, assembly):
    from .contract_terms import EXTENDED, REQUIRED, initial_stub_schedule, scenario

    request_fields = {'version', 'terms_sha256', 'premises', 'periods'}
    fields(calculation, request_fields, request_fields)
    term_fields = REQUIRED | EXTENDED | {'coupon_anchor', 'note_form', 'broken_coupon_amount'}
    if (admitted.get('version') != 'admitted-coupon-terms.v3'
            or set(admitted['terms']) != term_fields
            or calculation['version'] != 'selected-fixed-term-calculation.v1'
            or calculation['terms_sha256'] != digest(admitted)
            or admitted['assembly_sha256'] != digest(assembly)
            or admitted['graph_sha256'] != digest(graph)):
        raise ValueError('Selected fixed-term terms or calculation binding changed')

    common = calculation['premises']
    common_fields = {'profile', 'issue_id', 'source_sha256', 'premise_kind', 'calendar',
                     'holdings', 'event_scope', 'term_assumptions', 'evidence'}
    fields(common, common_fields, common_fields)
    if common['profile'] != 'fixed-term.v1' or common['premise_kind'] != 'HYPOTHETICAL':
        raise ValueError('Only explicitly hypothetical fixed-term premises supported')
    fields(common['term_assumptions'], ASSUMPTIONS, ASSUMPTIONS)
    if any(value is not True for value in common['term_assumptions'].values()):
        raise ValueError('Every fixed-term assumption must be explicitly true')
    evidence_fields = {'calendar', 'holdings', 'event_scope', 'term_assumptions'}
    fields(common['evidence'], evidence_fields, evidence_fields)
    for row in common['evidence'].values():
        fields(row, {'source', 'reason'}, {'source', 'reason'})
        if not isinstance(row['reason'], str) or not row['reason'].strip():
            raise ValueError('Fixed-term premise requires a reason')
        bind(graph, row['source'])

    terms = {key: row['value'] for key, row in admitted['terms'].items()}
    if (terms['day_count'] != 'ACT_ACT_ICMA' or type(terms['frequency']) is not int
            or terms['frequency'] != 1 or terms['eom'] is not False
            or terms['adjustment'] != 'FOLLOWING'
            or terms['note_form'] not in {'GLOBAL', 'DEFINITIVE'}
            or terms['due_date'] != terms['accrual_end']):
        raise ValueError('Unsupported fixed-term convention, form or coupon date')
    periods = initial_stub_schedule(terms['accrual_start'], terms['accrual_end'],
                                    terms['maturity_date'], terms['frequency'], terms['eom'],
                                    terms['stub'], coupon_anchor=terms['coupon_anchor'])
    if not isinstance(calculation['periods'], list) or len(calculation['periods']) != len(periods):
        raise ValueError('Exactly one separately evidenced premise packet per coupon period required')
    if not isinstance(common['holdings'], list) or not common['holdings']:
        raise ValueError('Explicit hypothetical holdings required')
    holding_fields = {'legal_holder_id', 'account_id', 'principal', 'entitled'}
    for holding in common['holdings']:
        fields(holding, holding_fields, holding_fields)
    issue_principal = exact(terms['issue_principal'])
    principals = [exact(holding['principal']) for holding in common['holdings']]
    if issue_principal <= 0 or any(p < 0 for p in principals) or sum(principals) > issue_principal:
        raise ValueError('Holdings exceed admitted issue principal or contain negative principal')
    if terms['note_form'] == 'GLOBAL' and len(common['holdings']) != 1:
        raise ValueError('Global coupons require one explicitly declared aggregate holding')

    calculations = []
    for i, (period, premise) in enumerate(zip(periods, calculation['periods'])):
        fields(premise, {'payment_date', 'events', 'evidence'}, {'payment_date', 'events', 'evidence'})
        fields(premise['evidence'], {'payment_date', 'events'}, {'payment_date', 'events'})
        if not isinstance(premise['events'], list):
            raise ValueError('Explicit per-period events required')
        if i == 0:
            value = {key: deepcopy(item) for key, item in common.items() if key != 'term_assumptions'}
            value['profile'] = 'fixed-coupon.v3'
            value['evidence'].pop('term_assumptions')
            value.update(payment_date=premise['payment_date'], events=deepcopy(premise['events']))
            value['evidence'].update(deepcopy(premise['evidence']))
            first = scenario(admitted, {'version': 'selected-coupon-calculation.v1',
                                        'terms_sha256': calculation['terms_sha256'], 'premises': value},
                             graph, assembly)['calculation']
            calculations.append(first)
            continue

        # Preserve the validated common premises and form-specific rounding.
        # The later regular periods use the same anchored ICMA kernel; their
        # references are exactly one successive annual determination interval.
        value = deepcopy(calculations[0]['calculation_inputs'])
        remove = {'note_form', 'broken_coupon_amount'}
        if terms['note_form'] == 'GLOBAL':
            remove |= {'calculation_amount', 'fixed_coupon_amount'}
        for key in remove:
            value.pop(key)
            value['evidence'].pop(key)
        value.update(profile='fixed-coupon.v2', **period,
                     references=[{'start': period['accrual_start'], 'end': period['accrual_end']}],
                     payment_date=premise['payment_date'], events=deepcopy(premise['events']))
        value['evidence'].update(deepcopy(premise['evidence']))
        for key in set(period) | {'references'}:
            value['evidence'][key] = {
                'source': deepcopy(admitted['terms']['coupon_anchor']['source']),
                'reason': 'Derived from the selected annual non-EOM coupon lattice through aligned maturity; '
                          'regular reference interval excludes payment delay',
            }
        calculations.append(coupon(value, graph))

    return {'version': 'conditional-fixed-term.v1', 'selected_terms_sha256': digest(admitted),
            'contract_terms': deepcopy(admitted), 'coupon_schedule': periods, 'calculations': calculations,
            'schedule_scope': 'UNADJUSTED_ACCRUAL_AND_DUE_DATES_THROUGH_MATURITY',
            'accrual_end_exclusive': True, 'note_form': terms['note_form'],
            'term_assumptions': deepcopy(common['term_assumptions']),
            'term_assumption_evidence': deepcopy(common['evidence']['term_assumptions']),
            'fact_scope': 'HYPOTHETICAL_ENTITLEMENT_CALENDAR_AND_EVENTS',
            'redemption_calculated': False, 'actual_event': 'NOT_ESTABLISHED',
            'full_settlement_supported': False}
