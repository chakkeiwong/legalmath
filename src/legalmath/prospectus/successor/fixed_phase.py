"""Conditional fixed-rate phase ending at a reset, with no maturity inference."""
from copy import deepcopy
from .anchors import fields, bind
from .contracts import digest
from .coupon_dates import anchored_date, iso_date, lattice_index
from .fixed_coupon import calculate as coupon
from ..semantics import exact


def schedule(terms):
    """The supported domain is annual BondBasis with an explicit short first period."""
    fields(terms['rounding'], {'quantum', 'rule', 'aggregation'}, {'quantum', 'rule', 'aggregation'})
    expected = {'day_count': 'THIRTY_360_BOND_BASIS', 'stub': 'SHORT_FIRST',
                'fixed_phase_boundary': 'FIRST_RESET_DATE', 'note_form': 'VP_SYSTEMS',
                'adjustment': 'FOLLOWING', 'references': []}
    if (any(terms[k] != v for k, v in expected.items()) or type(terms['frequency']) is not int
            or terms['frequency'] != 1 or terms['eom'] is not False
            or terms['rounding'].get('aggregation') != 'PER_LEGAL_HOLDER'):
        raise ValueError('Unsupported fixed-phase convention, form or rounding basis')
    start, first, end = (iso_date(terms[k]) for k in ('accrual_start', 'accrual_end', 'fixed_phase_end'))
    anchor = terms['coupon_anchor']
    first_index = lattice_index(first.isoformat(), anchor, 1, False)
    end_index = lattice_index(end.isoformat(), anchor, 1, False)
    if (terms['due_date'] != first.isoformat() or first.isoformat() != anchor
            or not anchored_date(anchor, -12, False) < start < first):
        raise ValueError('Fixed phase requires a short first coupon ending on its declared anchor')
    count = end_index - first_index + 1
    if not 1 <= count <= 600:
        raise ValueError('Fixed phase requires 1 to 600 coupons through its reset boundary')
    result, left = [], start.isoformat()
    for i in range(count):
        right = anchored_date(anchor, (first_index + i) * 12, False).isoformat()
        result.append({'accrual_start': left, 'accrual_end': right, 'due_date': right,
                       'stub': 'SHORT_FIRST' if i == 0 else 'REGULAR'})
        left = right
    return result


def calculate(admitted, calculation, graph, assembly):
    from .contract_terms import FIXED_PHASE
    fields(calculation, {'version', 'terms_sha256', 'premises', 'periods'},
           {'version', 'terms_sha256', 'premises', 'periods'})
    if (admitted.get('version') != 'admitted-coupon-terms.v4' or set(admitted['terms']) != FIXED_PHASE
            or calculation['version'] != 'selected-fixed-phase-calculation.v1'
            or calculation['terms_sha256'] != digest(admitted)
            or admitted['assembly_sha256'] != digest(assembly) or admitted['graph_sha256'] != digest(graph)):
        raise ValueError('Selected fixed-phase terms or calculation binding changed')
    common = calculation['premises']
    fields(common, {'profile', 'issue_id', 'source_sha256', 'premise_kind', 'calendar', 'holdings',
                    'event_scope', 'phase_assumptions', 'evidence'},
                   {'profile', 'issue_id', 'source_sha256', 'premise_kind', 'calendar', 'holdings',
                    'event_scope', 'phase_assumptions', 'evidence'})
    if common['profile'] != 'fixed-phase.v1' or common['premise_kind'] != 'HYPOTHETICAL':
        raise ValueError('Only explicitly hypothetical fixed-phase premises supported')
    assumptions = {'no_call', 'no_cancellation', 'no_conversion', 'no_principal_reduction', 'no_tax'}
    fields(common['phase_assumptions'], assumptions, assumptions)
    if any(value is not True for value in common['phase_assumptions'].values()):
        raise ValueError('Every fixed-phase absence assumption must be explicitly true')
    fields(common['evidence'], {'calendar', 'holdings', 'event_scope', 'phase_assumptions'},
           {'calendar', 'holdings', 'event_scope', 'phase_assumptions'})
    for row in common['evidence'].values():
        fields(row, {'source', 'reason'}, {'source', 'reason'})
        if not isinstance(row['reason'], str) or not row['reason'].strip():
            raise ValueError('Fixed-phase premise requires a reason')
        bind(graph, row['source'])
    terms = {k: row['value'] for k, row in admitted['terms'].items()}
    periods = schedule(terms)
    if not isinstance(calculation['periods'], list) or len(calculation['periods']) != len(periods):
        raise ValueError('Exactly one separately evidenced premise packet per coupon period required')
    if not isinstance(common['holdings'], list) or not common['holdings']:
        raise ValueError('Explicit hypothetical holdings required')
    for holding in common['holdings']:
        fields(holding, {'legal_holder_id', 'account_id', 'principal', 'entitled'},
               {'legal_holder_id', 'account_id', 'principal', 'entitled'})
    issue_principal = exact(terms['issue_principal'])
    principals = [exact(h['principal']) for h in common['holdings']]
    if issue_principal <= 0 or any(p < 0 for p in principals) or sum(principals) > issue_principal:
        raise ValueError('Holdings exceed admitted issue principal or contain negative principal')
    calculations = []
    kernel_terms = {'currency', 'annual_rate', 'day_count', 'frequency', 'eom', 'adjustment', 'rounding', 'references'}
    for i, (period, premise) in enumerate(zip(periods, calculation['periods'])):
        fields(premise, {'payment_date', 'events', 'evidence'}, {'payment_date', 'events', 'evidence'})
        fields(premise['evidence'], {'payment_date', 'events'}, {'payment_date', 'events'})
        value = {k: deepcopy(common[k]) for k in ('issue_id', 'source_sha256', 'premise_kind', 'calendar', 'holdings', 'event_scope')}
        value.update(profile='fixed-coupon.v1', **period,
                     payment_date=premise['payment_date'], events=deepcopy(premise['events']))
        value.update({k: deepcopy(terms[k]) for k in kernel_terms})
        value['evidence'] = {k: deepcopy(common['evidence'][k]) for k in ('calendar', 'holdings', 'event_scope')}
        value['evidence'].update(deepcopy(premise['evidence']))
        for key in kernel_terms | set(period):
            source_key = key if i == 0 or key in kernel_terms else 'coupon_anchor'
            row = admitted['terms'][source_key]
            value['evidence'][key] = {'source': deepcopy(row['source']),
                                      'reason': row['reason'] if i == 0 or key in kernel_terms else
                                      'Derived from selected annual non-EOM lattice through the first reset'}
        calculations.append(coupon(value, graph))
    return {'version': 'conditional-fixed-phase.v1', 'selected_terms_sha256': digest(admitted),
            'contract_terms': admitted, 'coupon_schedule': periods, 'calculations': calculations,
            'schedule_scope': 'UNADJUSTED_ACCRUAL_AND_DUE_DATES_THROUGH_FIRST_RESET',
            'fixed_phase_end': terms['fixed_phase_end'], 'accrual_end_exclusive': True,
            'phase_assumptions': deepcopy(common['phase_assumptions']),
            'phase_assumption_evidence': deepcopy(common['evidence']['phase_assumptions']),
            'note_form': 'VP_SYSTEMS', 'floating_phase': 'NOT_MODELLED', 'redemption_inferred': False,
            'fact_scope': 'HYPOTHETICAL_ENTITLEMENT_CALENDAR_AND_EVENTS',
            'actual_event': 'NOT_ESTABLISHED', 'full_settlement_supported': False}
