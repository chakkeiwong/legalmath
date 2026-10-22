"""Exact conditional control threshold; eligible ownership remains a premise."""
from copy import deepcopy
from . import causal_rating
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch, names
from .successor.ratio_facts import number

VERSION = 'basf-control-votes.v1'
KEY = 'control_votes_review'
COMPUTED = 'control_put.control'
QUALIFICATIONS = ('eligible_scope_supported', 'total_basis_supported',
                  'no_double_counting_supported', 'common_snapshot_supported')
VALUE = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}


def context(products):
    node = causal_rating.context(products)
    if not all(s in node['quote'] for s in ('mehr als 50% der Stimmrechte',
            '§ 30 Absatz 2', 'mittelbar oder unmittelbar', 'Aktien der BASF')):
        raise ValueError('Exact contract control threshold and subject required')
    return node


def analyze(row, node, instrument):
    keys = {'id', 'kind', 'votes', 'other_facts', 'rating_scenario', *QUALIFICATIONS}
    fields(row, keys, keys)
    if not isinstance(row['id'], str) or not row['id'] or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical voting scenario required')
    for key in QUALIFICATIONS:
        causal_rating.boolean(row[key])
    votes = row['votes']
    keys = {'instrument_id', 'control_event_id', 'issuer', 'eligible', 'total'}
    fields(votes, keys, keys)
    if votes['instrument_id'] != instrument or votes['issuer'] != 'BASF_SE':
        raise ValueError('Voting instrument or issuer mismatch')
    event = votes['control_event_id']
    if not isinstance(event, str) or not event:
        raise ValueError('Explicit control event identity required')
    values, unresolved = {}, []
    for label in ('eligible', 'total'):
        operand = votes[label]
        if operand is None:
            unresolved.append('Missing ' + label + ' voting rights')
            continue
        keys = {'instrument_id', 'control_event_id', 'issuer', 'unit', 'basis', 'value'}
        fields(operand, keys, keys)
        if any(operand[k] != votes[k] for k in ('instrument_id', 'control_event_id', 'issuer')):
            raise ValueError('Voting operand subject or control event mismatch')
        basis = 'ELIGIBLE_UNIQUE_BASF_VOTING_RIGHTS' if label == 'eligible' else 'ALL_BASF_VOTING_RIGHTS'
        if operand['unit'] != 'VOTING_RIGHTS' or operand['basis'] != basis:
            raise ValueError('Voting rights require the exact eligible/all-votes basis')
        values[label] = number(operand['value'])
    above, exact = None, None
    if len(values) == 2:
        numerator, denominator = values['eligible'], values['total']
        if numerator > denominator:
            raise ValueError('Eligible voting rights exceed all voting rights')
        if denominator == 0:
            unresolved.append('Zero total; voting-rights ratio undefined')
        else:
            above = 2 * numerator > denominator
            exact = {'numerator': str(numerator), 'denominator': str(denominator),
                     'left': str(2 * numerator), 'right': str(denominator),
                     'operator': 'GT', 'threshold': '1/2',
                     'method': 'exact rational cross multiplication'}
    premises = {'voting_rights_above_half': above, **{k: row[k] for k in QUALIFICATIONS}}
    derived = dispatch({'all': list(premises)}, premises)
    expression = {'all': [node['conditions'], {'not': node['exceptions']}]}
    facts = row['other_facts']
    fields(facts, names(expression) - {COMPUTED})
    for value in facts.values():
        causal_rating.boolean(value)
    observations = {**facts, COMPUTED: VALUE[derived['status']]}
    rating_review = None
    if row['rating_scenario'] is not None:
        rating = deepcopy(row['rating_scenario'])
        if (not isinstance(rating, dict) or rating.get('id') != row['id']
                or rating.get('other_facts') is not None):
            raise ValueError('Rating composition requires shared scenario and no nested overrides')
        events = rating.get('events')
        if (not isinstance(events, dict) or events.get('instrument_id') != instrument
                or events.get('control_event_id') != event):
            raise ValueError('Rating composition requires the exact same control event')
        if causal_rating.COMPUTED in facts:
            raise ValueError('Computed rating cannot also be supplied')
        rating['other_facts'] = observations
        rating_review = causal_rating.analyze(rating, node, instrument)
        observations = rating_review['derived_observations']
        complete = rating_review['complete_control_put']
    else:
        complete = dispatch(expression, observations)
    return {'scenario': deepcopy(row), 'voting_rights_above_half': above,
            'exact_ratio': exact, 'unresolved_votes': unresolved, 'control_premises': premises,
            'derived_control': derived, 'rating_review': rating_review,
            'derived_observations': observations, 'complete_control_put': complete,
            'actual_control_change': 'NOT_ESTABLISHED',
            'eligible_ownership_and_concert': 'HYPOTHETICAL_PREMISE_NOT_DERIVED',
            'historical_application': 'NOT_ESTABLISHED',
            'meaning': 'Strict contractual threshold on declared eligible unique voting rights; no ownership or concert inference'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios', 'actual_event_established'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['products_sha256'] != digest(products)
            or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned voting profile or complete baseline changed')
    if profile['actual_event_established'] is not False:
        raise ValueError('Conditional votes cannot establish actual control')
    node = context(products)
    if profile['context'] != node:
        raise ValueError('Complete control source changed')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not rows or len(rows) > 128 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Bounded voting scenarios required')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Distinct voting scenario identities required')
    first = rows[0]
    if (first['id'] != 'all-open' or first['other_facts'] or first['rating_scenario'] is not None
            or any(first[k] is not None for k in QUALIFICATIONS)
            or any(first['votes'][k] is not None for k in ('eligible', 'total'))):
        raise ValueError('Explicit all-open voting baseline required')
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
            'ordinary_answer_sha256': digest(ordinary), 'context': node,
            'scenarios': [analyze(r, node, instrument) for r in rows],
            'actual_event_established': False, 'classification': 'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            or {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
            != {k: v for k, v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Complete voting answer changed baseline or digest')
    expected = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY) != expected:
        raise ValueError('Computed voting answer differs from full reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'scenarios': len(expected['scenarios'])}
