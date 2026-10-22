"""Display supplied BASF section-12 rules without asserting an actual event."""
from .anchors import bind
from .occurrences import segments


RULES = {
    'additional_issue': {
        'reading': 'The issuer may issue further notes without holder consent if they have the same terms, except possibly the issue date, interest commencement date or issue price, so that they form one series.',
        'scope': 'SAME_TERMS_WITH_STATED_EXCEPTIONS',
    },
    'purchase': {
        'reading': 'The issuer may purchase notes in the market or otherwise at any price.',
        'scope': 'ISSUER_PURCHASE_POWER',
    },
    'after_purchase': {
        'reading': 'Notes acquired by the issuer may, at its election, be held, resold or submitted to the Fiscal Agent for cancellation.',
        'scope': 'ACQUIRED_NOTES_ONLY',
    },
    'public_offer': {
        'reading': 'If those purchases are made through a public offer, the offer must be made to all holders.',
        'scope': 'PUBLIC_PURCHASE_OFFER_ONLY',
    },
    'full_repayment': {
        'reading': 'All fully repaid notes must be cancelled without delay and may not be reissued or resold.',
        'scope': 'FULLY_REPAID_NOTES_ONLY',
    },
}


def validate(node):
    kind = node.get('lifecycle_kind')
    if not isinstance(kind, str) or kind not in RULES:
        raise ValueError('Unsupported BASF section-12 rule kind')
    rule = RULES[kind]
    if node.get('legal_reading') != rule['reading'] or node.get('rule_scope') != rule['scope']:
        raise ValueError('BASF section-12 supplied reading or condition changed')
    if (node['actor'] != 'issuer' or node['affected'] != 'holder'
            or node['election'] != 'none' or node['assets'] != []
            or node['role'] != 'OPERATIVE' or node['polarity'] is not True
            or node['modality'] != 'statement' or node['conditions'] != []
            or node['exceptions'] != []):
        raise ValueError('BASF section-12 rule cannot assert an exercise or event')
    if any(k.startswith(('actual_', 'outstanding_')) or k == 'independent_legal_acceptance'
           for k in node):
        raise ValueError('A supplied section-12 rule cannot attest actual facts')


def explain(clauses, graph, assembly):
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for node in clauses['nodes']:
        if node['effect'] != 'basf_note_lifecycle':
            continue
        validate(node)
        sources = []
        for span in node['spans']:
            unit = units[span['unit']]
            cursor = span['start']
            for piece in segments(graph, unit):
                start = max(span['start'], piece['start'])
                end = min(span['end'], piece['end'])
                if start >= end:
                    continue
                if start != cursor:
                    raise ValueError('Section-12 source spans are not contiguous')
                source = piece['source']
                raw_start = source['start'] + start - piece['start']
                sources.append(bind(graph, {**source, 'start': raw_start,
                    'end': raw_start + end - start, 'quote': unit['text'][start:end]}))
                cursor = end
            if cursor != span['end']:
                raise ValueError('Section-12 source span lacks an exact source copy')
        result.append({
            'id': node['id'], 'kind': node['lifecycle_kind'],
            'reading': RULES[node['lifecycle_kind']]['reading'],
            'rule_scope': RULES[node['lifecycle_kind']]['scope'],
            'quote': node['quote'], 'sources': sources,
            'reading_status': 'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_event': 'NOT_ESTABLISHED',
            'actual_outstanding_balance': 'NOT_ESTABLISHED',
            'independent_legal_acceptance': False,
        })
    return result
