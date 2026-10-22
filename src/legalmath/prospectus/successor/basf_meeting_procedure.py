"""Display supplied BASF meeting rules without finding actual compliance."""
from .anchors import bind
from .occurrences import segments


RULES = {
    'meeting_website': {
        'reading': 'From the calling of the holders’ meeting through meeting day, the issuer must make the call and exact participation and voting conditions available to holders on its website.',
        'scope': 'CALL_TO_MEETING_DAY', 'actor': 'issuer',
    },
    'requested_information': {
        'reading': 'At a holders’ meeting, the issuer must give a requesting holder information needed for proper assessment of an agenda item or proposed resolution.',
        'scope': 'REQUEST_AT_MEETING_AND_NECESSARY_INFORMATION', 'actor': 'issuer',
    },
    'shareholder_vote_rules': {
        'reading': 'The AktG rules on shareholder voting and vote counting at a general meeting apply correspondingly unless the holders’ meeting call provides otherwise.',
        'scope': 'DEFAULT_UNLESS_CALL_PROVIDES_OTHERWISE', 'actor': 'voting_process',
    },
    'resolution_publication': {
        'reading': 'The issuer must publicly announce holders’ resolutions in a suitable form at its own expense.',
        'scope': 'HOLDER_RESOLUTIONS', 'actor': 'issuer',
    },
    'german_seat_publication': {
        'reading': 'If the issuer has its seat in Germany, resolutions must be published without delay in the Bundesanzeiger and under contractual section 13; the publication prescribed by WpHG section 50(1) is sufficient instead.',
        'scope': 'ISSUER_SEAT_GERMANY_WITH_WPHG_ALTERNATIVE', 'actor': 'issuer',
    },
    'resolution_website': {
        'reading': 'The issuer must make holders’ resolutions, and the original terms if a resolution amends the terms, publicly available on its website for at least one month from the day after the meeting.',
        'scope': 'DAY_AFTER_MEETING_FOR_AT_LEAST_ONE_MONTH', 'actor': 'issuer',
    },
    'voting_window_stated': {
        'reading': 'The request for votes without a meeting must state the period in which votes may be cast.',
        'scope': 'VOTE_REQUEST_WITHOUT_MEETING', 'actor': 'vote_request',
    },
    'minimum_72_hours': {
        'reading': 'That voting period must last at least 72 hours.',
        'scope': 'VOTING_PERIOD_MINIMUM_72_HOURS', 'actor': 'vote_period',
    },
    'text_form_vote': {
        'reading': 'During that period, holders may cast votes to the voting chair in text form.',
        'scope': 'DURING_VOTING_PERIOD', 'actor': 'holder',
    },
    'alternative_forms': {
        'reading': 'The request for votes may also provide other forms of voting.',
        'scope': 'OTHER_FORMS_ONLY_IF_REQUEST_PROVIDES', 'actor': 'vote_request',
    },
    'counting_prerequisites': {
        'reading': 'The request for votes must state in detail the requirements for votes to be counted.',
        'scope': 'VOTE_REQUEST_COUNTING_REQUIREMENTS', 'actor': 'vote_request',
    },
}

REFERENCES = {
    'shareholder_vote_rules': ['historical-AktG-voting-rules'],
    'german_seat_publication': ['basf-notices:publication', 'historical-WpHG-50-1-publication'],
}


def validate(node):
    kind = node.get('procedure_kind')
    if not isinstance(kind, str) or kind not in RULES:
        raise ValueError('Unsupported BASF meeting procedure kind')
    rule = RULES[kind]
    if (node.get('legal_reading') != rule['reading'] or node.get('rule_scope') != rule['scope']
            or node['actor'] != rule['actor'] or node['affected'] != 'holder'
            or node['election'] != 'none' or node['assets'] != []
            or node['role'] != 'OPERATIVE' or node['polarity'] is not True
            or node['modality'] != 'statement' or node['conditions'] != []
            or node['exceptions'] != []):
        raise ValueError('BASF meeting rule cannot assert an exercise, fact or changed condition')
    targets = [r.get('target') for r in node.get('references', [])]
    if targets != REFERENCES.get(kind, []) or any(r.get('kind') != 'reference' for r in node.get('references', [])):
        raise ValueError('BASF meeting rule lost or changed its source dependencies')
    if any(k.startswith(('actual_', 'effective_', 'counted_')) or k == 'independent_legal_acceptance'
           for k in node):
        raise ValueError('A supplied meeting rule cannot attest actual compliance')


def explain(clauses, graph, assembly):
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for node in clauses['nodes']:
        if node['effect'] != 'basf_meeting_procedure':
            continue
        validate(node)
        sources = []
        for span in node['spans']:
            unit = units[span['unit']]
            cursor = span['start']
            for piece in segments(graph, unit):
                start, end = max(span['start'], piece['start']), min(span['end'], piece['end'])
                if start >= end:
                    continue
                if start != cursor:
                    raise ValueError('Meeting source spans are not contiguous')
                source = piece['source']
                raw_start = source['start'] + start - piece['start']
                sources.append(bind(graph, {**source, 'start': raw_start,
                    'end': raw_start + end - start, 'quote': unit['text'][start:end]}))
                cursor = end
            if cursor != span['end']:
                raise ValueError('Meeting source span lacks an exact source copy')
        references = [e for e in clauses['edges'] if e['from'] == node['id']]
        result.append({'id': node['id'], 'kind': node['procedure_kind'],
            'actor': node['actor'], 'reading': RULES[node['procedure_kind']]['reading'],
            'rule_scope': RULES[node['procedure_kind']]['scope'],
            'quote': node['quote'], 'sources': sources, 'references': references,
            'reading_status': 'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_compliance': 'NOT_ESTABLISHED',
            'meeting_and_vote_effectiveness': 'NOT_ESTABLISHED',
            'historical_statutory_requirements': 'NOT_ESTABLISHED',
            'independent_legal_acceptance': False})
    return result
