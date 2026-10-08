"""Short response identities expanded against caller-held original requests.

Only pair and quotation identities are encoded. Every model judgment and all
free text remain unchanged. The normal source/executable validators still run.
"""
from copy import deepcopy

from jsonschema import Draft202012Validator

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.schema import validate_output_schema

PROFILE = 'legalmath.scoped-response-aliases.v2'


def fail(reason):
    raise LegalMathError('E_REFERENCE', details={'response_aliases': reason})


def prepare(request, schema):
    if request.get('task') != 'SCOPED_SOURCE_FIDELITY' or request.get('response_schema') != schema:
        fail('Only the exact prepared scoped request is supported')
    questions = {r['candidate_id']: r['question_hash'] for r in request['candidates']}
    claim_ids = [c['claim_id'] for c in request['claims']]
    candidate_ids = [c['candidate_id'] for c in request['candidates']]
    claim_index = {value: i for i, value in enumerate(claim_ids)}
    candidate_index = {value: i for i, value in enumerate(candidate_ids)}
    required = request['required_pairs']
    pairs = {f'p{i}': [claim_index[pair['claim_id']], candidate_index[pair['candidate_id']]]
             for i, pair in enumerate(required)}
    if not pairs or len(set(map(tuple, pairs.values()))) != len(pairs):
        fail('Duplicate or empty required pairs')
    quotes = schema['$defs']['Quote']['properties']['span_ids']['items']['enum']
    expressions = schema['$defs']['Correspondence']['properties']['representation_quotes']['items'].get('enum', [])
    references = {'profile': PROFILE, 'request_hash': digest(request), 'schema_hash': digest(schema),
                  'pairs': pairs, 'source_spans': list(quotes),
                  'executable_spans': list(expressions)}
    if len(set(quotes)) != len(quotes) or len(set(expressions)) != len(expressions):
        fail('Duplicate original spans')
    output_schema = deepcopy(schema)
    row = output_schema['$defs']['ScopedCheck']
    for key in ('claim_id', 'candidate_id'):
        del row['properties'][key]; row['required'].remove(key)
    row['properties']['pair'] = {'type': 'string', 'enum': list(pairs)}
    row['required'].append('pair')
    relation = output_schema['$defs']['QuestionRelation']
    del relation['properties']['question_hash']; relation['required'].remove('question_hash')
    output_schema['$defs']['Quote']['properties']['span_ids']['items']['enum'] = [f's{i}' for i in range(len(quotes))]
    # Each source unit already has a selectable full-unit span. Separate
    # provisions must be separate quotes, never a manufactured concatenation.
    output_schema['$defs']['Quote']['properties']['span_ids']['maxItems'] = 1
    if expressions:
        output_schema['$defs']['Correspondence']['properties']['representation_quotes']['items']['enum'] = [f'e{i}' for i in range(len(expressions))]
    validate_output_schema(output_schema)
    wire = deepcopy(request)
    wire.pop('required_pairs', None)
    wire['required_pair_keys'] = list(pairs)
    # Keep the source packet, typed questions and candidate context literal.
    # Only repeated response identities are shortened in the model-facing wire.
    source_refs = deepcopy(wire.get('source_references', {}))
    if isinstance(source_refs.get('spans'), list):
        source_refs['spans'] = [{**span, 'span_id': f's{i}'}
                                for i, span in enumerate(source_refs['spans'])]
    wire['source_references'] = source_refs
    executable_refs = deepcopy(wire.get('executable_references', {}))
    if isinstance(executable_refs.get('spans'), list):
        executable_refs['spans'] = [{**span, 'span_id': f'e{i}'}
                                    for i, span in enumerate(executable_refs['spans'])]
    wire['executable_references'] = executable_refs
    wire['task'] = 'SCOPED_SOURCE_FIDELITY_WITH_RESPONSE_ALIASES'
    wire['profile'] = PROFILE
    wire['response_identity_aliases'] = references
    wire['response_schema'] = output_schema
    wire['instructions'] = (request['instructions'] +
            ' Response identity encoding: return each required pair exactly once using its p key from '
            'response_identity_aliases.pairs; the pair table indexes the literal claims and candidates in this request. '
            'Select s keys for source span_ids and e keys for executable representation_quotes. '
            'Each source evidence entry selects exactly ONE s key. Use a full-unit span when more '
            'context is needed, and separate evidence entries for separate quotations or provisions. '
            'The caller expands these keys against the unchanged request before validation. Do not truncate reasoning, '
            'infer support from an alias, change a question or remove uncertainty. '
            'Before returning, check every UNAVAILABLE or BLOCKED row has [] representation_quotes and at least '
            'one substantive followup question identifying what is needed. Followups belong to each affected row; '
            'a followup on another row does not complete this one. Do not change a judgment merely to pass validation.')
    return wire, output_schema, references


def resolve(value, request, schema, references):
    _, output_schema, expected = prepare(request, schema)
    if references != expected: fail('Detached or changed caller-held alias table')
    error = next(Draft202012Validator(output_schema).iter_errors(value), None)
    if error: fail('Invalid alias response: ' + error.message[:1000])
    selected = [r['pair'] for r in value['checks']]
    if len(selected) != len(set(selected)) or set(selected) != set(expected['pairs']):
        fail('Every original pair must be selected exactly once')
    result = deepcopy(value)
    claim_ids = [c['claim_id'] for c in request['claims']]
    candidate_rows = request['candidates']
    for row in result['checks']:
        key = row.pop('pair')
        try:
            claim_number, candidate_number = expected['pairs'][key]
            candidate = candidate_rows[candidate_number]
            target = {'claim_id': claim_ids[claim_number], 'candidate_id': candidate['candidate_id'],
                      'question_hash': candidate['question_hash']}
        except (KeyError, IndexError, TypeError):
            fail('Pair alias does not identify a caller-held claim/candidate')
        row['claim_id'] = target['claim_id']; row['candidate_id'] = target['candidate_id']
        row['question_relation']['question_hash'] = target['question_hash']
        for key in ('source_support', 'question_relation'):
            for quote in row[key]['evidence']:
                if len(quote['span_ids']) != len(set(quote['span_ids'])): fail('Duplicate source span')
                expanded = []
                for s in quote['span_ids']:
                    if (not isinstance(s, str) or not s.startswith('s') or not s[1:].isdigit()
                            or int(s[1:]) >= len(expected['source_spans'])):
                        fail('Foreign source span alias')
                    expanded.append(expected['source_spans'][int(s[1:])])
                quote['span_ids'] = expanded
        expr = row['executable_correspondence']['representation_quotes']
        if len(expr) != len(set(expr)): fail('Duplicate executable span')
        expanded = []
        for s in expr:
            if (not isinstance(s, str) or not s.startswith('e') or not s[1:].isdigit()
                    or int(s[1:]) >= len(expected['executable_spans'])):
                fail('Foreign executable span alias')
            expanded.append(expected['executable_spans'][int(s[1:])])
        row['executable_correspondence']['representation_quotes'] = expanded
    if not Draft202012Validator(schema).is_valid(result): fail('Expanded response fails original schema')
    return result


def encode_response(value, request, schema):
    """Offline exact round-trip diagnostic; never manufactures a live proposal."""
    if not Draft202012Validator(schema).is_valid(value): fail('Invalid original response')
    _, _, references = prepare(request, schema)
    claim_ids = [c['claim_id'] for c in request['claims']]
    candidates = request['candidates']
    inverse = {(claim_ids[ci], candidates[ri]['candidate_id'], candidates[ri]['question_hash']): key
               for key, (ci, ri) in references['pairs'].items()}
    sources = {v: f's{i}' for i, v in enumerate(references['source_spans'])}
    expressions = {v: f'e{i}' for i, v in enumerate(references['executable_spans'])}
    result = deepcopy(value)
    try:
        for row in result['checks']:
            row['pair'] = inverse[(row.pop('claim_id'), row.pop('candidate_id'), row['question_relation'].pop('question_hash'))]
            for key in ('source_support', 'question_relation'):
                for quote in row[key]['evidence']: quote['span_ids'] = [sources[s] for s in quote['span_ids']]
            expr = row['executable_correspondence']['representation_quotes']
            row['executable_correspondence']['representation_quotes'] = [expressions[s] for s in expr]
    except KeyError: fail('Original response refers to another source or question')
    if resolve(result, request, schema, references) != value: fail('Round trip changed a proposal')
    return result
