"""Original-object-bound executable expressions; never a meaning oracle.

V1 remains available for historical replay. V2 requires caller-held readings and
questions, and selects only the parsed scope/result expressions. Fact meanings,
runtime prose and the entire representation are context, not expression spans.
"""
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from ...canonical import canonical, digest
from ...errors import LegalMathError
from ..contracts import parse
from ..search.models import Reading
from ..search.providers import Completion
from ..search.schema import validate_output_schema
from . import source_references, fidelity_v2
from .diversity import save
from .semantics import representation, expression, render_node

PROTOCOL = 'legalmath.source-and-executable-spans.v2'


def reject(code, detail, *, row=None, field=None):
    details = {'reason': detail}
    if row is not None:
        details.update(claim_id=row.get('claim_id'), candidate_id=row.get('candidate_id'))
    if field: details['field'] = field
    raise LegalMathError(code, details=details)


def table(request, schema, *, readings, questions):
    """Compare transmitted identities/text against independently held originals."""
    if canonical(schema) != canonical(fidelity_v2.FidelityV2.model_json_schema()) or request.get('task') != 'SCOPED_SOURCE_FIDELITY':
        reject('E_UNSUPPORTED_PROFILE', 'Executable v2 requires the scoped fidelity contract')
    if not isinstance(readings, dict) or not isinstance(questions, dict):
        reject('E_REFERENCE', 'Original readings and questions are required')
    rows = request.get('candidates')
    if not isinstance(rows, list) or not rows:
        reject('E_SCHEMA', 'Candidates must be a nonempty list')
    seen = set(); originals = {}
    for candidate in rows:
        if not isinstance(candidate, dict): reject('E_SCHEMA', 'Invalid candidate entry')
        ident = candidate.get('candidate_id')
        if not isinstance(ident, str) or ident in seen or ident not in readings or ident not in questions:
            reject('E_REFERENCE', 'Unknown or duplicate original candidate')
        seen.add(ident)
        original = readings[ident]; parse(Reading, original)
        expected = {'candidate_id': ident, 'reading_hash': digest(original), 'question': questions[ident],
            'question_hash': digest(questions[ident]), 'representation': representation(original)}
        if canonical(candidate) != canonical(expected):
            reject('E_INTEGRITY', 'Request reading, question or representation differs from originals')
        originals[ident] = {'reading_hash': digest(original), 'question_hash': digest(questions[ident])}
    pairs = request.get('required_pairs')
    if (not isinstance(pairs, list) or not pairs or
            any(not isinstance(p, dict) or set(p) != {'claim_id', 'candidate_id'} or
                not isinstance(p['claim_id'], str) or not isinstance(p['candidate_id'], str) for p in pairs)):
        reject('E_REFERENCE', 'Invalid required pairs')
    if len({(p['claim_id'], p['candidate_id']) for p in pairs}) != len(pairs) or {p['candidate_id'] for p in pairs} != seen:
        reject('E_REFERENCE', 'Required pairs do not match the candidate context')
    binding = digest({'protocol': PROTOCOL, 'request': request, 'schema': schema, 'originals': originals})
    result = {'protocol': PROTOCOL, 'request_hash': binding, 'originals_hash': digest(originals),
        'coordinates': 'unicode-codepoints-half-open', 'candidates': [], 'spans': []}
    for candidate in rows:
        ident = candidate['candidate_id']; original = readings[ident]
        formal = original['formalization']; text = candidate['representation']
        unavailable = text.startswith('UNAVAILABLE_EXECUTABLE_MEANING:')
        availability = 'UNENCODED' if formal is None else ('UNSUPPORTED' if unavailable else 'ENCODED')
        identity = {'candidate_id': ident, **originals[ident], 'formalization_hash': digest(formal),
                    'representation_hash': digest(text)}
        result['candidates'].append({**identity, 'availability': availability,
            'executable_available': availability == 'ENCODED'})
        if unavailable: continue
        scope = render_node(expression(formal['scope'], 'scope'))
        body = render_node(expression(formal['result'], 'body'))
        # The rendered program block follows all user-supplied fact descriptions.
        # Derive its exact text from the parsed reading and anchor its final
        # occurrence before the fixed runtime explanation. Regex matches over
        # fact descriptions cannot create executable selections.
        block = '\nScope: '+scope+'\nResult: '+body+'\nResult type: '+formal['result_type']+'\nSupplied classifications requiring judgment:'
        start = text.rfind(block)
        if start < 0: reject('E_INTEGRITY', 'Renderer program block cannot be located')
        scope_start = start + len('\nScope: ')
        body_start = scope_start + len(scope) + len('\nResult: ')
        for kind, value, offset in (('scope', scope, scope_start), ('result', body, body_start)):
            row = {**identity, 'expression_kind': kind, 'expression_hash': digest(value),
                'start_codepoint': offset, 'end_codepoint': offset+len(value)}
            if text[offset:offset+len(value)] != value: reject('E_INTEGRITY', 'Expression range mismatch')
            result['spans'].append({**row, 'span_id': 'exec2.'+digest({'request': binding, **row})})
    return result


def prepare(request, schema, *, readings, questions):
    references = table(request, schema, readings=readings, questions=questions)
    wire, wire_schema = deepcopy(request), deepcopy(schema)
    quotes = wire_schema['$defs']['Correspondence']['properties']['representation_quotes']
    ids = [s['span_id'] for s in references['spans']]
    quotes['items'] = {'type': 'string', 'enum': ids} if ids else {'type': 'string'}
    if not ids: quotes['maxItems'] = 0
    validate_output_schema(wire_schema)
    wire['executable_reference_protocol'] = PROTOCOL
    wire['executable_references'] = references
    wire['executable_reference_instructions'] = (
        'In representation_quotes select exec2 span IDs belonging to this candidate and exact question. '
        'Each ID selects the parsed scope or result expression, not a fact description or runtime explanation. '
        'Read all representation context. ENCODED means selectable expressions exist, not that meaning is correct. '
        'UNENCODED or UNSUPPORTED means no executable quotation exists: do not assert PRESERVES, CONFLICTS '
        'or OMITS. Retain UNASSESSED, or NOT_APPLICABLE only with an independently justified '
        'NOT_APPLICABLE_TO_THIS_QUESTION proposal. Never relabel a judgment to satisfy validation. '
        'Select each ID at most once; use [] if there is no executable quotation. '
        'This instruction supersedes literal copying of executable quotes. Source quote span_ids use the '
        'separate source-reference table. Neither reference type proves semantic support.')
    wire['response_schema'] = wire_schema
    return wire, wire_schema, references


def resolve(value, request, schema, references, *, readings, questions):
    _, wire_schema, expected = prepare(request, schema, readings=readings, questions=questions)
    if canonical(references) != canonical(expected):
        reject('E_INTEGRITY', 'Executable table changed or belongs to other original objects')
    error = next(Draft202012Validator(wire_schema).iter_errors(value), None)
    if error:
        details = {'field': list(error.absolute_path), 'reason': error.message[:1200]}
        raise LegalMathError('E_SCHEMA', details=details)
    result = deepcopy(value)
    spans = {s['span_id']: s for s in references['spans']}
    candidates = {c['candidate_id']: c for c in references['candidates']}
    original_text = {c['candidate_id']: c['representation'] for c in request['candidates']}
    required = {(p['claim_id'], p['candidate_id']) for p in request['required_pairs']}
    pairs = [(r['claim_id'], r['candidate_id']) for r in result['checks']]
    if len(set(pairs)) != len(pairs) or set(pairs) != required:
        reject('E_REFERENCE', 'Response must retain every original required pair exactly once')
    for row in result['checks']:
        ident = row['candidate_id']; candidate = candidates[ident]
        if row['question_relation']['question_hash'] != candidate['question_hash']:
            reject('E_STALE_REVIEW', 'Response uses a different question', row=row, field='question_relation.question_hash')
        executable = row['executable_correspondence']; field = 'executable_correspondence.representation_quotes'
        if len(set(executable['representation_quotes'])) != len(executable['representation_quotes']):
            reject('E_REFERENCE', 'Duplicate executable selection', row=row, field=field)
        if not candidate['executable_available'] and executable['status'] in ('PRESERVES', 'CONFLICTS', 'OMITS'):
            reject('E_REFERENCE', 'No executable expression exists; original judgment is rejected unchanged',
                   row=row, field='executable_correspondence.status')
        quotes = []
        for span_id in executable['representation_quotes']:
            span = spans.get(span_id)
            if span is None or any(span[key] != candidate[key] for key in
                    ('candidate_id', 'reading_hash', 'question_hash', 'formalization_hash', 'representation_hash')):
                reject('E_REFERENCE', 'Foreign executable expression', row=row, field=field)
            text = original_text[ident][span['start_codepoint']:span['end_codepoint']]
            if digest(text) != span['expression_hash']: reject('E_INTEGRITY', 'Expression digest mismatch')
            quotes.append(text)
        executable['representation_quotes'] = quotes
    if not Draft202012Validator(schema).is_valid(result): reject('E_SCHEMA', 'Decoded response violates original schema')
    return result


def complete(provider, request, schema, settings, directory, *, readings, questions, input_profile='literal'):
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    # Freeze the caller-held context across dispatch; a provider cannot change
    # which original objects validate its eventual response.
    originals, assigned = deepcopy(readings), deepcopy(questions)
    wire, wire_schema, references = prepare(request, schema, readings=originals, questions=assigned)
    save(out/'executable-original-request.json', request); save(out/'executable-original-schema.json', schema)
    save(out/'executable-original-context.json', {'readings': originals, 'questions': assigned})
    save(out/'executable-references.json', references)
    try:
        answer = source_references.complete(provider, wire, wire_schema, settings, out, input_profile=input_profile)
        value = resolve(answer.value, request, schema, references, readings=originals, questions=assigned)
    except LegalMathError as exc:
        save(out/'executable-validation.json', {'status': 'REJECTED', 'error': exc.code, 'details': exc.details,
            'protocol': PROTOCOL, 'semantic_support': 'NOT_ESTABLISHED'})
        raise
    save(out/'executable-resolved-response.json', value)
    save(out/'executable-validation.json', {'status': 'REFERENCE_INTEGRITY_CHECKED', 'protocol': PROTOCOL,
        'table_hash': digest(references), 'request_hash': references['request_hash'],
        'raw_resolved_source_hash': digest(answer.value), 'resolved_hash': digest(value),
        'semantic_support': 'NOT_ESTABLISHED'})
    return Completion(value, {**answer.provenance, 'executable_reference_protocol': PROTOCOL,
        'executable_table_hash': digest(references), 'executable_originals_hash': references['originals_hash'],
        'semantic_support': 'NOT_ESTABLISHED'})
