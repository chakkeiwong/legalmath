"""Optional request-bound executable quotation transport, not a meaning oracle."""
from copy import deepcopy
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from ...canonical import digest
from ...errors import LegalMathError
from ..search.providers import Completion
from . import source_references
from .diversity import save

PROTOCOL = 'legalmath.source-and-executable-spans.v1'


def table(request, schema):
    binding = digest({'protocol': PROTOCOL, 'request': request, 'schema': schema})
    result = {'protocol': PROTOCOL, 'request_hash': binding,
              'coordinates': 'unicode-codepoints-half-open', 'candidates': [], 'spans': []}
    seen = set()
    for candidate in request['candidates']:
        ident = candidate['candidate_id']
        if ident in seen or not re.fullmatch('[a-f0-9]{64}', candidate.get('reading_hash', '')):
            raise LegalMathError('E_REFERENCE', details='Distinct reading-bound candidates required')
        seen.add(ident)
        if digest(candidate['question']) != candidate['question_hash']:
            raise LegalMathError('E_STALE_REVIEW', details='Question hash differs')
        text = candidate['representation']
        available = not text.startswith('UNAVAILABLE_EXECUTABLE_MEANING:')
        identity = {k: candidate[k] for k in ('candidate_id', 'question_hash', 'reading_hash')}
        identity['representation_hash'] = digest(text)
        result['candidates'].append({**identity, 'executable_available': available})
        if not available:
            continue
        ranges = [('whole_representation', 0, len(text))]
        for kind in ('Scope', 'Result'):
            for match in re.finditer(r'^' + kind + r': (.+)$', text, re.MULTILINE):
                ranges.append((kind.lower(), match.start(1), match.end(1)))
        for kind, start, end in ranges:
            row = {**identity, 'expression_kind': kind, 'start_codepoint': start, 'end_codepoint': end}
            result['spans'].append({**row, 'span_id': 'exec.' + digest({'request': binding, **row})})
    return result


def prepare(request, schema):
    refs = table(request, schema)
    wire, wire_schema = deepcopy(request), deepcopy(schema)
    quote_schema = wire_schema['$defs']['Correspondence']['properties']['representation_quotes']
    ids = [s['span_id'] for s in refs['spans']]
    quote_schema['items'] = {'type': 'string', 'enum': ids} if ids else {'type': 'string'}
    if not ids:
        quote_schema['maxItems'] = 0
    wire['executable_references'] = refs
    wire['executable_reference_instructions'] = (
        'Select executable span IDs in representation_quotes for the same candidate, reading and question. '
        'This instruction supersedes literal-copy instructions for executable quotes only. '
        'Read the entire representation. Scope and result IDs select exact expressions. '
        'For executable_available=false no executable quotation exists: PRESERVES, CONFLICTS and OMITS '
        'are unavailable judgments. Retain UNASSESSED or a separately justified NOT_APPLICABLE. '
        'Never change a source or question judgment merely to satisfy a schema. IDs prove location only.')
    wire['response_schema'] = wire_schema
    return wire, wire_schema, refs


def resolve(value, request, schema, references):
    if references != table(request, schema):
        raise LegalMathError('E_INTEGRITY', details='Executable references differ from reading/question/request')
    _, wire_schema, _ = prepare(request, schema)
    if not Draft202012Validator(wire_schema).is_valid(value):
        raise LegalMathError('E_SCHEMA', details='Invalid executable-reference response')
    result = deepcopy(value)
    spans = {r['span_id']: r for r in references['spans']}
    candidates = {r['candidate_id']: r for r in request['candidates']}
    availability = {r['candidate_id']: r['executable_available'] for r in references['candidates']}
    for row in result['checks']:
        ident = row['candidate_id']
        executable = row['executable_correspondence']
        if ident not in candidates:
            raise LegalMathError('E_REFERENCE')
        if not availability[ident] and executable['status'] in ('PRESERVES', 'CONFLICTS', 'OMITS'):
            raise LegalMathError('E_REFERENCE', details='No executable meaning exists for ' + ident)
        quotes = []
        for span_id in executable['representation_quotes']:
            span = spans.get(span_id)
            if span is None or span['candidate_id'] != ident:
                raise LegalMathError('E_REFERENCE', details='Foreign executable quotation')
            text = candidates[ident]['representation']
            quotes.append(text[span['start_codepoint']:span['end_codepoint']])
        executable['representation_quotes'] = quotes
    if not Draft202012Validator(schema).is_valid(result):
        raise LegalMathError('E_SCHEMA')
    return result


def complete(provider, request, schema, settings, directory, *, input_profile='literal'):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    wire, wire_schema, references = prepare(request, schema)
    save(out/'executable-original-request.json', request)
    save(out/'executable-references.json', references)
    answer = source_references.complete(provider, wire, wire_schema, settings, out, input_profile=input_profile)
    try:
        value = resolve(answer.value, request, schema, references)
    except LegalMathError as exc:
        save(out/'executable-validation.json', {'status': 'REJECTED', 'error': exc.code, 'details': exc.details})
        raise
    save(out/'executable-resolved-response.json', value)
    save(out/'executable-validation.json', {'status': 'REFERENCE_INTEGRITY_CHECKED',
        'table_hash': digest(references), 'semantic_support': 'NOT_ESTABLISHED'})
    return Completion(value, {**answer.provenance, 'executable_reference_protocol': PROTOCOL,
                              'executable_table_hash': digest(references)})
