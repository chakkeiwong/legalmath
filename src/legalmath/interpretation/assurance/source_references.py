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


def resolve_response(value, schema, wire_schema, references, packet, request_hash, *, maximum=16777216):
    verify_table(references, packet, request_hash)
    error = next(Draft202012Validator(wire_schema).iter_errors(value), None)
    if error:
        raise LegalMathError('E_SCHEMA', details={'field': list(error.absolute_path),
                                                'reason': error.message[:1500]})

    remaining = maximum
    visits = 0
    def charge(n):
        nonlocal remaining
        remaining -= n
        if remaining < 0:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Source quotation expansion exceeds expanded response limit')

    def visit(item, shape, *, build=True, depth=0):
        nonlocal visits
        if not build:
            visits += 1
            if depth > 96 or visits > 250000:
                raise LegalMathError('E_RESOURCE_LIMIT', details='Source response expansion structure limit')
        if '$ref' in shape:
            ref = shape['$ref']
            if ref == '#/$defs/Quote':
                # Only one bounded quotation is allocated during preflight;
                # the repeated expanded response graph is not constructed yet.
                quote = _resolve(item, references, packet)
                if not build:
                    charge(len(canonical(quote)))
                    return None
                return quote
            if not ref.startswith('#/$defs/'):
                raise LegalMathError('E_UNSUPPORTED_PROFILE')
            return visit(item, schema['$defs'][ref.split('/')[-1]], build=build, depth=depth+1)
        if item is None:
            if not build:charge(4)
            return None
        if 'anyOf' in shape:
            # The wire schema has already validated shape; choose by JSON type.
            options = [s for s in shape['anyOf'] if s.get('type') != 'null']
            if len(options) != 1:
                raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Ambiguous quotation-bearing union')
            return visit(item, options[0], build=build, depth=depth+1)
        if shape.get('type') == 'array':
            if not build:
                charge(2+max(0,len(item)-1))
                for x in item:visit(x,shape['items'],build=False,depth=depth+1)
                return None
            return [visit(x, shape['items'], depth=depth+1) for x in item]
        if shape.get('type') == 'object':
            if not build:
                charge(2+max(0,len(item)-1)+sum(len(canonical(k))+1 for k in item))
                for k,v in item.items():visit(v,shape['properties'][k],build=False,depth=depth+1)
                return None
            return {k: visit(v, shape['properties'][k], depth=depth+1) for k, v in item.items()}
        if not build:
            charge(len(canonical(item)))
            return None
        return deepcopy(item)

    visit(value, schema, build=False)
    result = visit(value, schema)
    if not Draft202012Validator(schema).is_valid(result):
        raise LegalMathError('E_SCHEMA', details='Resolved response violates the original contract')
    return result


def complete(provider, request, schema, settings, directory, *, input_profile='literal', response_profile='literal'):
    from .source_context import before_cache
    request = before_cache(request, getattr(provider, 'source_context', None))
    from . import candidate_responses
    candidate_responses.validate_configuration(response_profile,
        reference_protocol=request.get('executable_reference_protocol'), input_profile=input_profile)
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    from .evidence_tables import bounded_size
    # The request has already passed source_context; encoded profiles must be
    # measured after encoding, while the expanded graph keeps a finite cap.
    bounded_size(request, settings.max_logical_input_bytes or (16777216 if input_profile!='literal' else settings.max_input_bytes))
    if 'Quote' in schema.get('$defs', {}):
        wire, wire_schema, references = prepare(request, schema)
    elif input_profile != 'literal' and response_profile == 'literal':
        wire, wire_schema, references = deepcopy(request), deepcopy(schema), None
        wire['response_schema'] = wire_schema
    else:
        raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Source references require a Quote schema')
    output_schema = wire_schema
    response_provenance = {}
    if response_profile != 'literal':
        response_original = deepcopy(wire)
        wire, output_schema, response_binding = candidate_responses.prepare(response_original, wire_schema)
        save(out/'candidate-original-request.json', response_original)
        save(out/'candidate-original-schema.json', wire_schema)
        save(out/'candidate-response-binding.json', response_binding)
        response_provenance = {'candidate_response_profile': response_profile,
            'candidate_response_binding_hash': digest(response_binding)}
    encoding_provenance = {}
    if input_profile != 'literal':
        from . import readable_tables, readable_challenges, evidence_tables
        codecs = {c.PROFILE: c for c in (readable_tables, readable_challenges, evidence_tables)}
        if input_profile not in codecs:
            raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Unknown request encoding')
        codec = codecs[input_profile]
        original_wire = wire
        save(out/'expanded-wire-request.json', original_wire)
        wire = codec.encode(original_wire)
        decode_args = {'expected_request_hash': digest(original_wire)}
        if codec is evidence_tables:
            decode_args['expected_packet_hash'] = digest(original_wire['source_packet'])
        restored = codec.decode(wire, **decode_args)
        if canonical(restored) != canonical(original_wire):
            raise LegalMathError('E_INTEGRITY', details='Request encoding changed source or evidence')
        encoding_provenance = {'input_encoding_protocol': codec.PROTOCOL,
            'expanded_request_hash': digest(original_wire), 'encoded_request_hash': digest(wire)}
        save(out/'encoding-validation.json', {**encoding_provenance,
            'status': 'EXACT_REQUEST_ROUND_TRIP_CHECKED',
            'expanded_bytes': len(canonical(original_wire)), 'encoded_bytes': len(canonical(wire)),
            'max_input_bytes': settings.max_input_bytes, 'semantic_support': 'NOT_ESTABLISHED'})
    save(out/'original-request.json', request); save(out/'original-schema.json', schema)
    save(out/'references.json', references); save(out/'wire-request.json', wire)
    save(out/'wire-schema.json', output_schema)
    if len(canonical(wire)) > settings.max_input_bytes:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Source-reference request exceeds bounded input bytes')
    answer = provider.complete(wire, output_schema, settings)
    save(out/'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
    try:
        if len(canonical(answer.value)) > settings.max_output_bytes:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Source-reference response exceeds bounded output bytes')
        expanded = answer.value
        if response_profile != 'literal':
            expanded = candidate_responses.resolve(answer.value, response_original, wire_schema, response_binding)
            if len(canonical(expanded)) > settings.max_output_bytes:
                raise LegalMathError('E_RESOURCE_LIMIT', details='Expanded candidate response exceeds bounded output bytes')
            save(out/'candidate-expanded-response.json', expanded)
        value = (resolve_response(expanded, schema, wire_schema, references,
                                 request['source_packet'], references['request_hash'],
                                 maximum=settings.max_expanded_output_bytes or settings.max_output_bytes)
                 if references is not None else expanded)
        bounded_size(value, settings.max_expanded_output_bytes or settings.max_output_bytes)
        if not Draft202012Validator(schema).is_valid(value):
            raise LegalMathError('E_SCHEMA', details='Response violates its original contract')
        save(out/'resolved-response.json', value)
        save(out/'validation.json', {'status': 'REFERENCE_INTEGRITY_CHECKED',
            'semantic_support': 'NOT_ESTABLISHED', 'references_hash': digest(references),
            'raw_hash': digest(answer.value), 'resolved_hash': digest(value), **response_provenance})
    except LegalMathError as exc:
        save(out/'validation.json', {'status': 'REJECTED', 'error': exc.code, 'details': exc.details})
        raise
    return Completion(value, {**answer.provenance, **encoding_provenance, **response_provenance, 'source_reference_protocol': PROTOCOL,
        'source_reference_table_hash': digest(references), 'source_reference_raw_hash': digest(answer.value),
        'source_reference_request_hash': references['request_hash'] if references is not None else None, 'semantic_support': 'NOT_ESTABLISHED'})
