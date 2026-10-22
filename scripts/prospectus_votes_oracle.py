"""Independent integer-scaled threshold and explicit source formula."""
from copy import deepcopy
from scripts.prospectus_amount_oracle import rational, decision
from scripts import prospectus_rating_oracle as rating_oracle

QUALIFICATIONS = ('eligible_scope_supported', 'total_basis_supported',
                  'no_double_counting_supported', 'common_snapshot_supported')
FACTS = ('control_put.rating', 'control_put.event_notice', 'control_put.timely_exercise',
         'control_put.valid_declaration', 'control_put.delivery', 'control_put.payment_day',
         'control_put.earlier_tax_notice', 'representative.put.entrusted', 'representative.put.express_permission')
VALUE = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}


def classify(row):
    votes = row['votes']; above = None
    if votes['eligible'] is not None and votes['total'] is not None:
        n, d = rational(votes['eligible']['value']); tn, td = rational(votes['total']['value'])
        if tn != 0:
            above = 2 * n * td > tn * d
    derived = decision([above, *[row[k] for k in QUALIFICATIONS]], lambda *v: all(v))
    rating = None
    if row['rating_scenario'] is not None:
        nested = deepcopy(row['rating_scenario'])
        nested['other_facts'] = {**row['other_facts'], 'control_put.control': VALUE[derived]}
        rating = rating_oracle.classify(nested); complete = rating['complete']
    else:
        complete = decision([VALUE[derived], *[row['other_facts'].get(k) for k in FACTS]],
            lambda control, rating, notice, timely, declaration, delivery, payment, tax, entrusted, permission:
            control and rating and notice and timely and declaration and delivery and payment and not tax
            and (not entrusted or permission))
    return {'above': above, 'control': derived, 'complete': complete, 'rating': rating}


def projection(result):
    rating = result['rating_review']
    return {'above': result['voting_rights_above_half'], 'control': result['derived_control']['status'],
            'complete': result['complete_control_put']['status'],
            'rating': None if rating is None else rating_oracle.projection(rating)}


def case(name, instrument='bond', eligible='50.000000000000000000001', total='100'):
    identity = {'instrument_id': instrument, 'control_event_id': name + ':control', 'issuer': 'BASF_SE'}
    def operand(value, basis):
        return None if value is None else {**identity, 'unit': 'VOTING_RIGHTS', 'basis': basis, 'value': value}
    return {'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'votes': {**identity,
        'eligible': operand(eligible, 'ELIGIBLE_UNIQUE_BASF_VOTING_RIGHTS'),
        'total': operand(total, 'ALL_BASF_VOTING_RIGHTS')}, **dict.fromkeys(QUALIFICATIONS, True),
        'rating_scenario': None, 'other_facts': {**dict.fromkeys(FACTS, True),
            'control_put.earlier_tax_notice': False, 'representative.put.entrusted': False,
            'representative.put.express_permission': False}}


def scenarios(instrument):
    rows = [case('all-open', instrument, None, None)]
    rows[0].update(**dict.fromkeys(QUALIFICATIONS, None), other_facts={})
    for name, eligible, total in [('statutory-thirty', '30', '100'), ('below', '49.99999999999999999999', '100'),
        ('exact-half', '50', '100'), ('just-above-half', '50.000000000000000000001', '100'),
        ('all-votes', '100', '100'), ('none', '0', '100'), ('zero-denominator', '0', '0'),
        ('missing-numerator', None, '100'), ('missing-denominator', '51', None),
        ('fractional-exact', '0.125', '0.25'), ('fractional-above', '0.1250000000000000001', '0.25')]:
        rows.append(case(name, instrument, eligible, total))
    for field in QUALIFICATIONS:
        for suffix, value in [('missing', None), ('false', False), ('conflict', 'conflict')]:
            row = case(field + '-' + suffix, instrument); row[field] = value; rows.append(row)
    for name, changes in [('tax-exception', {'control_put.earlier_tax_notice': True}),
        ('rating-unknown', {'control_put.rating': None}), ('notice-unknown', {'control_put.event_notice': None}),
        ('representative-restricted', {'representative.put.entrusted': True}),
        ('representative-permitted', {'representative.put.entrusted': True, 'representative.put.express_permission': True})]:
        row = case(name, instrument); row['other_facts'].update(changes); rows.append(row)
    for name, eligible, causal in [('composed-timely', '51', True), ('composed-late', '51', True),
            ('composed-causal-unknown', '51', None), ('composed-exact-half', '50', True),
            ('composed-ownership-unknown', '51', True)]:
        row = case(name, instrument, eligible)
        rating_name = 'composed-late' if name == 'composed-late' else 'composed-timely'
        rating = next(r for r in rating_oracle.scenarios(instrument) if r['id'] == rating_name)
        rating['id'] = name; rating['events']['control_event_id'] = name + ':control'
        rating['events']['rating_event_id'] = name + ':rating'
        for label in ('control', 'rating'):
            rating['events'][label]['event_id'] = name + ':' + label
        rating['causal_link'].update(control_event_id=name + ':control', rating_event_id=name + ':rating', value=causal)
        rating['cutoff_scenario']['id'] = name
        # Cutoff observations bind its own event identity to the shared scenario.
        rating['cutoff_scenario']['interval']['event_id'] = name
        rating['other_facts'] = None
        row['other_facts'].pop('control_put.rating'); row['other_facts'].pop('control_put.timely_exercise')
        row['rating_scenario'] = rating
        if name == 'composed-ownership-unknown': row['eligible_scope_supported'] = None
        rows.append(row)
    return rows
