"""Short response identities expanded against caller-held original requests.

Only pair and quotation identities are encoded. Every model judgment and all
free text remain unchanged. The normal source/executable validators still run.
"""
from copy import deepcopy

from jsonschema import Draft202012Validator

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.schema import validate_output_schema

PROFILE = 'legalmath.scoped-response-aliases.v1'


def fail(reason):
    raise LegalMathError('E_REFERENCE', details={'response_aliases': reason})


def prepare(request, schema):
    if request.get('task') != 'SCOPED_SOURCE_FIDELITY' or request.get('response_schema') != schema:
        fail('Only the exact prepared scoped request is supported')
    questions = {r['candidate_id']: r['question_hash'] for r in request['candidates']}
    required = request['required_pairs']
    pairs = {f'p{i}': {**pair, 'question_hash': questions[pair['candidate_id']]}
             for i, pair in enumerate(required)}
    if not pairs or len({(p['claim_id'], p['candidate_id']) for p in pairs.values()}) != len(pairs):
        fail('Duplicate or empty required pairs')
    quotes = schema['$defs']['Quote']['properties']['span_ids']['items']['enum']
    expressions = schema['$defs']['Correspondence']['properties']['representation_quotes']['items'].get('enum', [])
    references = {'profile': PROFILE, 'request_hash': digest(request), 'schema_hash': digest(schema),
                  'pairs': pairs, 'source_spans': {f's{i}': v for i, v in enumerate(quotes)},
                  'executable_spans': {f'e{i}': v for i, v in enumerate(expressions)}}
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
    output_schema['$defs']['Quote']['properties']['span_ids']['items']['enum'] = list(references['source_spans'])
    if expressions:
        output_schema['$defs']['Correspondence']['properties']['representation_quotes']['items']['enum'] = list(references['executable_spans'])
    validate_output_schema(output_schema)
    wire = {'task': 'SCOPED_SOURCE_FIDELITY_WITH_RESPONSE_ALIASES', 'profile': PROFILE,
            'original_request': deepcopy(request), 'response_identity_aliases': references,
            'response_schema': output_schema,
            'instructions': 'Read the whole original_request unchanged, including each typed question and all source units. '
            'Return every required pair exactly once using its p key from response_identity_aliases.pairs. '
            'That key fixes the claim_id, candidate_id and question_hash together; do not return those three long strings. '
            'For source evidence span_ids select the s keys that map to the original source span IDs. '
            'For executable representation_quotes select the e keys that map to the original executable span IDs. '
            'These identity spelling rules supersede only the original request instructions for spelling those identities. '
            'All source interpretation, statuses, rationales, dependency_ids, followup_questions and additional_concerns '
            'retain the original meanings and requirements. Use the response_schema at this outer level. '
            'Do not truncate legal reasoning, infer support from an alias, change a question or remove uncertainty.'}
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
    for row in result['checks']:
        target = expected['pairs'][row.pop('pair')]
        row['claim_id'] = target['claim_id']; row['candidate_id'] = target['candidate_id']
        row['question_relation']['question_hash'] = target['question_hash']
        for key in ('source_support', 'question_relation'):
            for quote in row[key]['evidence']:
                if len(quote['span_ids']) != len(set(quote['span_ids'])): fail('Duplicate source span')
                quote['span_ids'] = [expected['source_spans'][s] for s in quote['span_ids']]
        expr = row['executable_correspondence']['representation_quotes']
        if len(expr) != len(set(expr)): fail('Duplicate executable span')
        row['executable_correspondence']['representation_quotes'] = [expected['executable_spans'][s] for s in expr]
    if not Draft202012Validator(schema).is_valid(result): fail('Expanded response fails original schema')
    return result


def encode_response(value, request, schema):
    """Offline exact round-trip diagnostic; never manufactures a live proposal."""
    if not Draft202012Validator(schema).is_valid(value): fail('Invalid original response')
    _, _, references = prepare(request, schema)
    inverse = {tuple(p[k] for k in ('claim_id', 'candidate_id', 'question_hash')): key
               for key, p in references['pairs'].items()}
    sources = {v: k for k, v in references['source_spans'].items()}
    expressions = {v: k for k, v in references['executable_spans'].items()}
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
