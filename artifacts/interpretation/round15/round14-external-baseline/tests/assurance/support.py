from copy import deepcopy
from tests.search.support import generation, packet as threshold_packet


def packet():
    p = threshold_packet()
    p['units'][0]['text'] = 'A distributor should not offer gifts other than a discount of fees or charges.'
    p['selected_slice'] = 'Gift control including the discount exception'
    return p


def inventory():
    return {'claims': [{'claim_id': 'gift', 'kind': 'PROHIBITION', 'actor': 'distributor',
        'action': 'offer gifts', 'modality': 'SHOULD_NOT', 'conditions': [],
        'exceptions': ['a discount of fees or charges'], 'temporal': [],
        'statement': 'The gift prohibition excludes fee discounts.', 'relevance': 'CONTROL',
        'evidence': [{'unit_id': 'p1', 'quote': packet()['units'][0]['text']}], 'uncertainty': []}],
        'units': [{'unit_id': 'p1', 'disposition': 'CLAIMS', 'claim_ids': ['gift'], 'rationale': 'Selected gift rule'}],
        'authorities': [], 'uncertainties': []}


def reading(omitted=False):
    r = generation()['readings'][0]; r['citations'] = deepcopy(inventory()['claims'][0]['evidence'])
    r['statement'] = '[TRUE_IS_PROHIBITED] Result true means prohibited gift offer, with the fee exception.'
    r['formalization'] = {'facts': [{'name': name, 'type': 'bool', 'meaning': meaning, 'unit': 'truth value',
        'source_unit_ids': ['p1'], 'requires_judgment': False} for name, meaning in (
            ('gift', 'A distributor offers a gift'), ('discount', 'The gift is a discount of fees or charges'))],
        'scope': 'true', 'result': 'gift' if omitted else '(and gift (not discount))', 'result_type': 'bool'}
    return r


def fidelity(claims, candidates, labels=None):
    from legalmath.interpretation.assurance.semantics import representation
    labels = labels or {}
    return {'checks': [{'claim_id': c['claim_id'], 'candidate_id': cid,
        'label': labels.get(cid, 'ENTAILED'), 'source_evidence': deepcopy(c['evidence']),
        'representation_quotes': [representation(r)] if labels.get(cid, 'ENTAILED') == 'ENTAILED' else [],
        'rationale': 'Controlled test judgment, not an independent legal oracle.',
        'failing_stage': 'NONE' if labels.get(cid, 'ENTAILED') == 'ENTAILED' else 'FORMALIZATION',
        'question': None if labels.get(cid, 'ENTAILED') == 'ENTAILED' else 'Where is the fee exception represented?'}
        for c in claims if c['relevance'] != 'CONTEXT' for cid, r in candidates.items()], 'additional_concerns': []}
