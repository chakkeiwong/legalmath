"""Lossless, readable request tables; preservation is not source entailment.

This optional input codec follows span preparation. Source text, questions and
the output schema stay literal. It tables only the closed coverage/reference
records. The decoder takes an independently held original-request hash; the
hash printed inside an untrusted message is never an authenticity anchor.
"""
from copy import deepcopy

from ...canonical import canonical, digest
from ...errors import LegalMathError
from . import source_references

PROFILE = 'readable-tables.v1'
PROTOCOL = 'legalmath.readable-request-tables.v1'
UNIT_COLUMNS = ['unit_id', 'disposition', 'question_ids', 'related_unit_ids', 'evidence', 'rationale']
CONCERN_COLUMNS = ['concern_id', 'question_ids', 'related_unit_ids', 'evidence', 'explanation', 'original_concern_id']
SPAN_COLUMNS = ['span_id', 'unit_id', 'start_codepoint', 'end_codepoint']
COVERAGE_KEYS = {'packet_hash', 'interpretation_hash', 'partition', 'piece_hashes', 'units', 'concerns'}
REFERENCE_KEYS = {'protocol', 'packet_hash', 'request_hash', 'coordinates', 'chunk_size', 'unit_hashes', 'spans'}
INSTRUCTIONS = (
    'Lossless input tables, version 1. All indices are zero-based. Read all source_packet.units in full. '
    'The source text, interpretation, questions, output_identity_contract and response_schema remain literal. '
    'In coverage.units and coverage.concerns, columns name the fields of each row in order. '
    'unit_id cells and every related_unit_ids or partition item are indices into source_packet.units; '
    'each names that unit\'s original unit_id. question_ids, concern_id and original_concern_id stay literal. '
    'Each evidence item is [unit_index, start_codepoint, end_codepoint]: the exact contiguous quote is '
    'source_packet.units[unit_index].text[start_codepoint:end_codepoint], using Unicode codepoints, '
    'half-open bounds, with no normalization. rationale and explanation cells are indices into coverage.texts; '
    'each indexed string is the complete original text, never a summary. '
    'In source_references.spans, columns name fields of each row; unit_id is a source unit index. '
    'source_references.unit_hashes is ordered like source_packet.units. All other fields keep their meanings. '
    'Return original object identities from output_identity_contract, and select the literal span_id values '
    'for output quotes using response_schema. Account for every unit, question and concern, including '
    'cross-piece dependencies. This encoding changes no proposal or uncertainty and establishes no legal support.')


def fail(detail):
    raise LegalMathError('E_INTEGRITY', details='Readable request tables: '+detail)


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        fail('Unexpected or missing record field')


def index(value, length):
    if type(value) is not int or not 0 <= value < length:
        fail('Out-of-range or non-integer index')
    return value


def rows(value, columns):
    exact_keys(value, {'columns', 'rows'})
    if value['columns'] != columns or not isinstance(value['rows'], list):
        fail('Unknown columns or row sequence')
    for row in value['rows']:
        if not isinstance(row, list) or len(row) != len(columns):
            fail('Row width differs from its declared columns')
    return value['rows']


def source_units(request):
    try:
        units = request['source_packet']['units']
        names = [u['unit_id'] for u in units]
        if not units or len(names) != len(set(names)) or any(not isinstance(u['text'], str) for u in units):
            fail('Invalid source units')
        return units, {name: n for n, name in enumerate(names)}
    except (KeyError, TypeError):
        fail('Missing source packet')


def encode(request):
    """Encode a prepared span request and check exact reconstruction locally."""
    if not isinstance(request, dict) or 'input_encoding' in request:
        fail('Already encoded or invalid request')
    units, ids = source_units(request)
    references = request.get('source_references')
    exact_keys(references, REFERENCE_KEYS)
    source_references.verify_table(references, request['source_packet'], references['request_hash'])
    wire = deepcopy(request)

    def unit_number(name):
        if not isinstance(name, str) or name not in ids:
            fail('Foreign source unit')
        return ids[name]

    def quote_range(quote):
        exact_keys(quote, {'unit_id', 'quote'})
        number = unit_number(quote['unit_id']); text = units[number]['text']
        value = quote['quote']
        if not isinstance(value, str) or not value or text.count(value) != 1:
            fail('Quote must occur exactly once in its unchanged source unit')
        start = text.index(value)
        return [number, start, start + len(value)]

    if 'coverage' in request:
        coverage = request['coverage']; exact_keys(coverage, COVERAGE_KEYS)
        encoded = deepcopy(coverage); texts = []; text_ids = {}

        def text_number(value):
            if not isinstance(value, str):
                fail('Rationale or explanation is not text')
            if value not in text_ids:
                text_ids[value] = len(texts); texts.append(value)
            return text_ids[value]

        for name, columns in (('units', UNIT_COLUMNS), ('concerns', CONCERN_COLUMNS)):
            table = []
            for record in coverage[name]:
                exact_keys(record, columns)
                row = deepcopy(record)
                if 'unit_id' in row:
                    row['unit_id'] = unit_number(row['unit_id'])
                row['related_unit_ids'] = [unit_number(n) for n in row['related_unit_ids']]
                row['evidence'] = [quote_range(q) for q in row['evidence']]
                key = 'rationale' if name == 'units' else 'explanation'
                row[key] = text_number(row[key])
                table.append([row[key] for key in columns])
            encoded[name] = {'columns': columns[:], 'rows': table}
        encoded['partition'] = [[unit_number(n) for n in piece] for piece in coverage['partition']]
        encoded['texts'] = texts
        wire['coverage'] = encoded
    wire['source_references']['unit_hashes'] = [references['unit_hashes'][u['unit_id']] for u in units]
    wire['source_references']['spans'] = {'columns': SPAN_COLUMNS[:], 'rows': [
        [s['span_id'], unit_number(s['unit_id']), s['start_codepoint'], s['end_codepoint']]
        for s in references['spans']]}
    wire['input_encoding'] = {'protocol': PROTOCOL, 'instructions': INSTRUCTIONS,
        'original_request_hash': digest(request), 'source_packet_hash': digest(request['source_packet']),
        'coverage_hash': digest(request['coverage']) if 'coverage' in request else None}
    restored = decode(wire, expected_request_hash=digest(request))
    if canonical(restored) != canonical(request):
        fail('Round trip changed the original request')
    return wire


def decode(wire, *, expected_request_hash):
    """Strict inverse with a trusted original-request identity supplied by caller.

    A verifier must obtain expected_request_hash from its retained original
    request/receipt, not from wire['input_encoding'].
    """
    try:
        return _decode(wire, expected_request_hash)
    except (KeyError, TypeError, ValueError, IndexError):
        fail('Malformed table structure')


def _decode(wire, expected_request_hash):
    if not isinstance(wire, dict):
        fail('Request is not an object')
    result = deepcopy(wire); marker = result.pop('input_encoding')
    exact_keys(marker, {'protocol', 'instructions', 'original_request_hash', 'source_packet_hash', 'coverage_hash'})
    if (marker['protocol'] != PROTOCOL or marker['instructions'] != INSTRUCTIONS or
            marker['original_request_hash'] != expected_request_hash):
        fail('Detached request identity or encoding instructions')
    units, _ = source_units(result)
    if marker['source_packet_hash'] != digest(result['source_packet']):
        fail('Source edition changed')

    def unit_name(number):
        return units[index(number, len(units))]['unit_id']

    def quote(value):
        if not isinstance(value, list) or len(value) != 3:
            fail('A quote reference has three coordinates')
        n, start, end = value; n = index(n, len(units)); text = units[n]['text']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            fail('Invalid quote range')
        selected = text[start:end]
        if text.count(selected) != 1:
            fail('Ambiguous quote range')
        return {'unit_id': units[n]['unit_id'], 'quote': selected}

    if 'coverage' in result:
        encoded = result['coverage']; exact_keys(encoded, COVERAGE_KEYS | {'texts'})
        texts = encoded.pop('texts')
        if not isinstance(texts, list) or any(not isinstance(v, str) for v in texts) or len(set(texts)) != len(texts):
            fail('Invalid exact-text dictionary')
        used = set()
        for name, columns in (('units', UNIT_COLUMNS), ('concerns', CONCERN_COLUMNS)):
            records = []
            for cells in rows(encoded[name], columns):
                record = dict(zip(columns, cells))
                if 'unit_id' in record:
                    record['unit_id'] = unit_name(record['unit_id'])
                record['related_unit_ids'] = [unit_name(n) for n in record['related_unit_ids']]
                record['evidence'] = [quote(q) for q in record['evidence']]
                key = 'rationale' if name == 'units' else 'explanation'
                n = index(record[key], len(texts)); used.add(n); record[key] = texts[n]
                records.append(record)
            encoded[name] = records
        if used != set(range(len(texts))):
            fail('Unused text could introduce unattached instructions')
        encoded['partition'] = [[unit_name(n) for n in piece] for piece in encoded['partition']]
        if marker['coverage_hash'] != digest(encoded):
            fail('Coverage identity changed')
    elif marker['coverage_hash'] is not None:
        fail('Missing coverage')
    references = result['source_references']; exact_keys(references, REFERENCE_KEYS)
    hashes = references['unit_hashes']
    if not isinstance(hashes, list) or len(hashes) != len(units):
        fail('Unit hash sequence changed')
    references['unit_hashes'] = {u['unit_id']: h for u, h in zip(units, hashes)}
    references['spans'] = [dict(zip(SPAN_COLUMNS, [s, unit_name(n), a, b]))
        for s, n, a, b in rows(references['spans'], SPAN_COLUMNS)]
    source_references.verify_table(references, result['source_packet'], references['request_hash'])
    if digest(result) != expected_request_hash:
        fail('Reconstructed request differs from the trusted original')
    return result
