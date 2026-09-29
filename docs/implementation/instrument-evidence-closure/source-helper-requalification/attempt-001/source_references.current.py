"""Request-bound Unicode spans; integrity is independent of proposed support.

The model selects identifiers, never hashes, offsets or replacement text. The
unchanged source remains in the request. Internal Quote objects and their
semantic validators are deliberately unchanged.
"""
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from ...canonical import canonical, digest
from ...errors import LegalMathError
from ..contracts import Packet, parse
from ..search.providers import Completion
from ..search.schema import validate_output_schema
from .diversity import save

PROTOCOL = 'legalmath.source-spans.v1'
COORDINATES = 'unicode-codepoints-half-open'


def table(packet, request_hash, *, chunk_size=512):
    parse(Packet, packet)
    if (type(chunk_size) is not int or not 32 <= chunk_size <= 20000 or
            not isinstance(request_hash, str) or len(request_hash) != 64):
        raise LegalMathError('E_SCHEMA')
    units = packet['units']
    if len({u['unit_id'] for u in units}) != len(units):
        raise LegalMathError('E_DUPLICATE_ID')
    packet_hash = digest(packet)
    result = {'protocol': PROTOCOL, 'packet_hash': packet_hash,
              'request_hash': request_hash, 'coordinates': COORDINATES,
              'chunk_size': chunk_size, 'unit_hashes': {}, 'spans': []}
    for unit in units:
        name, text = unit['unit_id'], unit['text']
        result['unit_hashes'][name] = digest(text)
        ranges = [(0, len(text))]
        if len(text) > chunk_size:
            ranges.extend((i, min(i + chunk_size, len(text))) for i in range(0, len(text), chunk_size))
        for start, end in ranges:
            entry = {'unit_id': name, 'start_codepoint': start, 'end_codepoint': end}
            ident = 'span.' + digest({'protocol': PROTOCOL, 'packet': packet_hash,
                                     'request': request_hash, 'text': digest(text), **entry})
            result['spans'].append({'span_id': ident, **entry})
    return result


def verify_table(value, packet, request_hash):
    if not isinstance(value, dict) or canonical(value) != canonical(table(packet, request_hash, chunk_size=value.get('chunk_size'))):
        raise LegalMathError('E_INTEGRITY', details='Source reference table differs from the exact packet/request')


def resolve(selection, references, packet, request_hash):
    verify_table(references, packet, request_hash)
    return _resolve(selection, references, packet)


def _resolve(selection, references, packet):
    if not isinstance(selection, dict) or set(selection) != {'span_ids'}:
        raise LegalMathError('E_SCHEMA', details='A quotation selects span_ids only')
    ids = selection['span_ids']
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 64 or
            any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids)):
        raise LegalMathError('E_REFERENCE')
    spans = {r['span_id']: r for r in references['spans']}
    if any(i not in spans for i in ids):
        raise LegalMathError('E_REFERENCE', details='Foreign or absent source span identifier')
    selected = [spans[i] for i in ids]
    if (len({r['unit_id'] for r in selected}) != 1 or
            any(a['end_codepoint'] != b['start_codepoint'] for a, b in zip(selected, selected[1:]))):
        raise LegalMathError('E_REFERENCE', details='Spans must adjoin in source order within one unit')
    text = next(u['text'] for u in packet['units'] if u['unit_id'] == selected[0]['unit_id'])
    quote = text[selected[0]['start_codepoint']:selected[-1]['end_codepoint']]
    # Preserve the existing unique-contiguous-quotation contract.
    if text.count(quote) != 1:
        raise LegalMathError('E_REFERENCE', details='Selected text repeats; select adjoining context or the full unit')
    return {'unit_id': selected[0]['unit_id'], 'quote': quote}


def prepare(request, schema):
    packet = request.get('source_packet')
    if packet is None or 'Quote' not in schema.get('$defs', {}):
        raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Span transport requires a packet and the internal Quote contract')
    quote = schema['$defs']['Quote']
    if set(quote.get('properties', {})) != {'unit_id', 'quote'}:
        raise LegalMathError('E_SCHEMA', details='Unrecognized quotation schema')
    binding = digest({'request': request, 'schema': schema, 'protocol': PROTOCOL})
    references = table(packet, binding)
    wire_schema = deepcopy(schema)
    wire_schema['$defs']['Quote'] = {'type': 'object', 'additionalProperties': False,
        'properties': {'span_ids': {'type': 'array', 'minItems': 1, 'maxItems': 64,
            'items': {'type': 'string', 'enum': [r['span_id'] for r in references['spans']]}}},
        'required': ['span_ids']}
    for name in ('UnitAccount', 'Disposition'):
        definition = wire_schema.get('$defs', {}).get(name)
        if definition and 'unit_id' in definition.get('properties', {}):
            definition['properties']['unit_id'] = {'type': 'string', 'enum': [u['unit_id'] for u in packet['units']]}
    validate_output_schema(wire_schema)
    wire = deepcopy(request)
    wire['source_reference_protocol'] = PROTOCOL
    wire['source_references'] = references
    wire['source_reference_instructions'] = (
        'For every source quotation in your response, select span_ids from this request. '
        'Do not copy text, supply offsets, or invent an ID. Multiple spans must adjoin in source order '
        'within one unit; use separate evidence entries for different units. Full units are selectable. '
        'Read the whole supplied source, including qualifications outside the chosen spans. '
        'These identifiers prove location only, never support or legal correctness. '
        'This response protocol replaces older instructions to copy source quotations. '
        + ('Executable quotations follow executable_reference_instructions in this request.'
         if 'executable_references' in request else
         'Executable representation_quotes remain exact executable text, not source span identifiers.'))
    wire['response_schema'] = wire_schema
    return wire, wire_schema, references


def resolve_response(value, schema, wire_schema, references, packet, request_hash):
    verify_table(references, packet, request_hash)
    error = next(Draft202012Validator(wire_schema).iter_errors(value), None)
    if error:
        raise LegalMathError('E_SCHEMA', details={'field': list(error.absolute_path),
                                                'reason': error.message[:1500]})

    def visit(item, shape):
        if '$ref' in shape:
            ref = shape['$ref']
            if ref == '#/$defs/Quote':
                return _resolve(item, references, packet)
            if not ref.startswith('#/$defs/'):
                raise LegalMathError('E_UNSUPPORTED_PROFILE')
            return visit(item, schema['$defs'][ref.split('/')[-1]])
        if item is None:
            return None
        if 'anyOf' in shape:
            # The wire schema has already validated shape; choose by JSON type.
            options = [s for s in shape['anyOf'] if s.get('type') != 'null']
            if len(options) != 1:
                raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Ambiguous quotation-bearing union')
            return visit(item, options[0])
        if shape.get('type') == 'array':
            return [visit(x, shape['items']) for x in item]
        if shape.get('type') == 'object':
            return {k: visit(v, shape['properties'][k]) for k, v in item.items()}
        return deepcopy(item)

    result = visit(value, schema)
    if not Draft202012Validator(schema).is_valid(result):
        raise LegalMathError('E_SCHEMA', details='Resolved response violates the original contract')
    return result


def complete(provider, request, schema, settings, directory, *, input_profile='literal'):
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    wire, wire_schema, references = prepare(request, schema)
    encoding_provenance = {}
    if input_profile != 'literal':
        from . import readable_tables
        if input_profile != readable_tables.PROFILE:
            raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Unknown request encoding')
        original_wire = wire
        save(out/'expanded-wire-request.json', original_wire)
        wire = readable_tables.encode(original_wire)
        restored = readable_tables.decode(wire, expected_request_hash=digest(original_wire))
        if canonical(restored) != canonical(original_wire):
            raise LegalMathError('E_INTEGRITY', details='Request encoding changed source or evidence')
        encoding_provenance = {'input_encoding_protocol': readable_tables.PROTOCOL,
            'expanded_request_hash': digest(original_wire), 'encoded_request_hash': digest(wire)}
        save(out/'encoding-validation.json', {**encoding_provenance,
            'status': 'EXACT_REQUEST_ROUND_TRIP_CHECKED',
            'expanded_bytes': len(canonical(original_wire)), 'encoded_bytes': len(canonical(wire)),
            'max_input_bytes': settings.max_input_bytes, 'semantic_support': 'NOT_ESTABLISHED'})
    save(out/'original-request.json', request); save(out/'original-schema.json', schema)
    save(out/'references.json', references); save(out/'wire-request.json', wire)
    save(out/'wire-schema.json', wire_schema)
    if len(canonical(wire)) > settings.max_input_bytes:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Source-reference request exceeds bounded input bytes')
    answer = provider.complete(wire, wire_schema, settings)
    save(out/'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
    try:
        if len(canonical(answer.value)) > settings.max_output_bytes:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Source-reference response exceeds bounded output bytes')
        value = resolve_response(answer.value, schema, wire_schema, references,
                                 request['source_packet'], references['request_hash'])
        save(out/'resolved-response.json', value)
        save(out/'validation.json', {'status': 'REFERENCE_INTEGRITY_CHECKED',
            'semantic_support': 'NOT_ESTABLISHED', 'references_hash': digest(references),
            'raw_hash': digest(answer.value), 'resolved_hash': digest(value)})
    except LegalMathError as exc:
        save(out/'validation.json', {'status': 'REJECTED', 'error': exc.code, 'details': exc.details})
        raise
    return Completion(value, {**answer.provenance, **encoding_provenance, 'source_reference_protocol': PROTOCOL,
        'source_reference_table_hash': digest(references), 'source_reference_raw_hash': digest(answer.value),
        'source_reference_request_hash': references['request_hash'], 'semantic_support': 'NOT_ESTABLISHED'})
