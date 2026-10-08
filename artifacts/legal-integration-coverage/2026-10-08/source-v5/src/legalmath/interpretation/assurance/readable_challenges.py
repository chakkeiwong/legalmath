"""Exact readable pooling for complete interpretation-challenge requests."""
from collections import Counter
from copy import deepcopy
from ...canonical import canonical, digest
from ...errors import LegalMathError
from . import readable_tables

PROFILE = 'readable-challenges.v1'
PROTOCOL = 'legalmath.readable-challenge-tables.v1'
FIELDS = ('candidates', 'questions', 'obligations', 'source_cues',
          'independent_formal_checks', 'declared_grammar_alternatives', 'prior_round_evidence')
COLUMNS = ['source_packet_hash', 'candidate_hash', 'question_hash', 'dimension',
           'candidate_id', 'obligation_id', 'candidate_ids']
INSTRUCTIONS = (
    'Additional lossless challenge tables. This extends the source-reference tables. '
    'The full source_packet and response_schema remain literal. In the declared fields, '
    'an object containing only text_ref is an exact string: read context_texts[text_ref], '
    'using a zero-based integer. Each stored text is the complete original, never a summary. '
    'obligations has named columns and rows; read each row by its column names, then resolve '
    'text_ref cells recursively. Candidates, questions, citations, formal certificates and '
    'all prior evidence keep their exact original meanings after this substitution. '
    'Copy the resolved original hashes and identifiers into responses; never return text_ref '
    'objects or calculate hashes. Read all retained candidates and context, including '
    'unselected obligations. These tables do not establish legal support.')


def fail(reason):
    raise LegalMathError('E_INTEGRITY', details='Readable challenge tables: '+reason)


def encode(request):
    if request.get('task') != 'INTERPRETATION_CHALLENGES':
        fail('Wrong request task')
    wire = readable_tables.encode(request)
    if 'challenge_encoding' in wire or 'context_texts' in wire:
        fail('Reserved encoding field')
    counts = Counter()
    def count(value):
        if isinstance(value, str) and len(value) >= 40:
            counts[value] += 1
        elif isinstance(value, dict):
            if set(value) == {'text_ref'}:
                fail('Ambiguous original text reference')
            for child in value.values(): count(child)
        elif isinstance(value, list):
            for child in value: count(child)
    for field in FIELDS:
        if field in wire: count(wire[field])
    texts = [text for text, count_ in counts.items() if count_ > 1]
    ids = {text: i for i, text in enumerate(texts)}
    def visit(value):
        if isinstance(value, str) and value in ids: return {'text_ref': ids[value]}
        if isinstance(value, dict): return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list): return [visit(v) for v in value]
        return deepcopy(value)
    for field in FIELDS:
        if field in wire: wire[field] = visit(wire[field])
    if not isinstance(wire.get('obligations'), list): fail('Missing obligations')
    if any(set(row) != set(COLUMNS) for row in wire['obligations']): fail('Unknown obligation fields')
    wire['obligations'] = {'columns': COLUMNS[:], 'rows': [[row[k] for k in COLUMNS] for row in wire['obligations']]}
    wire['context_texts'] = texts
    wire['challenge_encoding'] = {'protocol': PROTOCOL, 'fields': list(FIELDS), 'instructions': INSTRUCTIONS}
    if canonical(decode(wire, expected_request_hash=digest(request))) != canonical(request):
        fail('Round trip changed request')
    return wire


def decode(wire, *, expected_request_hash):
    result = deepcopy(wire)
    marker = result.pop('challenge_encoding', None)
    if marker != {'protocol': PROTOCOL, 'fields': list(FIELDS), 'instructions': INSTRUCTIONS}:
        fail('Unknown encoding marker')
    texts = result.pop('context_texts', None)
    if (not isinstance(texts, list) or any(not isinstance(t, str) for t in texts)
            or len(texts) != len(set(texts))): fail('Invalid text dictionary')
    table = result.get('obligations')
    if (not isinstance(table, dict) or set(table) != {'columns', 'rows'}
            or table['columns'] != COLUMNS or not isinstance(table['rows'], list)):
        fail('Invalid obligation table')
    if any(not isinstance(row, list) or len(row) != len(COLUMNS) for row in table['rows']):
        fail('Invalid obligation row')
    result['obligations'] = [dict(zip(COLUMNS, row)) for row in table['rows']]
    used = set()
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'text_ref'}:
                n = value['text_ref']
                if type(n) is not int or not 0 <= n < len(texts): fail('Invalid text reference')
                used.add(n)
                return texts[n]
            return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list): return [visit(v) for v in value]
        return value
    for field in FIELDS:
        if field in result: result[field] = visit(result[field])
    if used != set(range(len(texts))): fail('Unattached pooled text')
    return readable_tables.decode(result, expected_request_hash=expected_request_hash)
