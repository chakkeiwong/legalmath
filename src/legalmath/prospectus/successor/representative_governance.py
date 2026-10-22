"""Expose supplied representative clauses without finding actual authority."""
from .anchors import bind
from .occurrences import segments

READINGS = {
    'powers': 'The common representative has the tasks and powers conferred by law or by the holders through majority resolution.',
    'instructions': 'The common representative must follow the holders\' instructions.',
    'reporting': 'The common representative must report to the holders on its activities.',
    'statutory_reference': 'Removal and the common representative\'s other rights and duties are governed by the applicable SchVG provisions.',
}


def validate(node):
    kind = node.get('governance_kind')
    if not isinstance(kind, str) or kind not in READINGS or node.get('legal_reading') != READINGS[kind]:
        raise ValueError('Unsupported representative governance kind or supplied reading')
    if (node['actor'] != 'common_representative' or node['affected'] != 'holder'
            or node['election'] != 'none' or node['assets'] != [] or node['role'] != 'OPERATIVE'
            or node['polarity'] is not True or node['modality'] != 'statement'
            or node['conditions'] != [] or node['exceptions'] != []):
        raise ValueError('Representative governance requires an operative rule, not an exercise/compliance claim')
    if any(k in node for k in ('actual_authority', 'actual_compliance', 'independent_legal_acceptance')):
        raise ValueError('A supplied representative reading cannot attest actual authority or compliance')
    if kind == 'statutory_reference' and not any(r.get('kind') == 'reference' and r.get('target')
                                                for r in node.get('references', [])):
        raise ValueError('Representative statutory reference requires its explicit onward dependency')


def explain(clauses, graph, assembly):
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for node in clauses['nodes']:
        if node['effect'] != 'representative_governance':
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
                    raise ValueError('Representative source spans do not form an exact contiguous copy')
                source = piece['source']
                raw_start = source['start'] + start - piece['start']
                sources.append(bind(graph, {**source, 'start': raw_start,
                    'end': raw_start + end - start, 'quote': unit['text'][start:end]}))
                cursor = end
            if cursor != span['end']:
                raise ValueError('Representative source span lacks an exact source copy')
        references = [e for e in clauses['edges'] if e['from'] == node['id']]
        result.append({'id': node['id'], 'kind': node['governance_kind'],
            'reading': READINGS[node['governance_kind']], 'quote': node['quote'],
            'sources': sources, 'references': references,
            'reading_status': 'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_authority': 'NOT_ESTABLISHED', 'actual_compliance': 'NOT_ESTABLISHED',
            'applicable_statutory_requirements': 'NOT_ESTABLISHED',
            'independent_legal_acceptance': False})
    return result
