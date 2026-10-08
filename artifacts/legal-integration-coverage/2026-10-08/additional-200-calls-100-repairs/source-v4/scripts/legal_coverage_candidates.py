"""Candidate-bound response choices; existing validators remain authoritative."""
from copy import deepcopy

from jsonschema import Draft202012Validator

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.schema import validate_output_schema
from scripts import legal_coverage_aliases as aliases

PROFILE = 'legalmath.candidate-bound-response.v1'


def fail(message):
    raise LegalMathError('E_REFERENCE', details={'candidate_response': message})


def prepare(request, schema):
    wire, output_schema, references = aliases.prepare(request, schema)
    templates = output_schema['$defs']['ScopedCheck']['anyOf']
    executable = request['executable_references']
    candidates = {c['candidate_id']: c for c in executable['candidates']}
    spans = {s['span_id']: s for s in executable['spans']}
    branches, pair_descriptions = [], []
    for ci, candidate in enumerate(request['candidates']):
        ident = candidate['candidate_id']
        bound = candidates[ident]
        if any(bound[k] != candidate[k] for k in ('candidate_id', 'question_hash', 'reading_hash')):
            fail('Executable candidate identity differs from the original target')
        keys = [key for key, (_, ri) in references['pairs'].items() if ri == ci]
        if not keys:
            continue
        permitted = [f'e{i}' for i, span in enumerate(references['executable_spans'])
                     if spans[span]['candidate_id'] == ident and
                     spans[span]['question_hash'] == candidate['question_hash'] and
                     spans[span]['reading_hash'] == candidate['reading_hash']]
        available = bound['executable_available']
        if bool(permitted) != available:
            fail('Executable availability does not match the selectable expressions')
        for key in keys:
            claim_index, _ = references['pairs'][key]
            claim = request['claims'][claim_index]
            pair_descriptions.append({'pair': key, 'claim_id': claim['claim_id'],
                'claim_statement': claim['statement'], 'candidate_id': ident,
                'question': candidate['question']['question'],
                'question_result_kind': candidate['question']['result_kind'],
                'executable_available': available, 'permitted_expression_keys': permitted})
        for template in templates:
            branch = deepcopy(template)
            branch['properties']['pair']['enum'] = keys
            correspondence = branch['properties']['executable_correspondence']
            selections = correspondence['properties']['representation_quotes']
            selections['items'] = {'type': 'string', 'enum': permitted} if permitted else {'type': 'string'}
            if not permitted:
                selections['maxItems'] = 0
            statuses = correspondence['properties']['status']['enum']
            statuses[:] = [s for s in statuses if
                           s not in (['UNAVAILABLE'] if available else ['PRESERVES', 'CONFLICTS', 'OMITS'])]
            if statuses == ['NOT_APPLICABLE']:
                branches.append(branch)
                continue
            # Give each correspondence state the same necessary conditions
            # already required by fidelity_v2, never a preselected legal label.
            for status in statuses:
                state = deepcopy(branch)
                props = state['properties']
                corr = props['executable_correspondence']['properties']
                corr['status']['enum'] = [status]
                if status in ('UNAVAILABLE', 'BLOCKED'):
                    corr['representation_quotes']['maxItems'] = 0
                    props['followup_questions']['minItems'] = 1
                if status in ('PRESERVES', 'CONFLICTS', 'OMITS'):
                    support = deepcopy(output_schema['$defs']['SourceSupport'])
                    support['properties']['status']['enum'] = ['SUPPORTED']
                    support['properties']['evidence']['minItems'] = 1
                    props['source_support'] = support
                    relation = deepcopy(output_schema['$defs']['QuestionRelation'])
                    relation['properties']['status']['enum'] = ['RELEVANT']
                    relation['properties']['evidence']['minItems'] = 1
                    props['question_relation'] = relation
                    if status != 'OMITS':
                        corr['representation_quotes']['minItems'] = 1
                branches.append(state)
    if not branches or len(pair_descriptions) != len(references['pairs']):
        fail('Required pair coverage changed')
    output_schema['$defs']['ScopedCheck'] = {'anyOf': branches}
    validate_output_schema(output_schema)
    wire['task'] = 'SCOPED_SOURCE_FIDELITY_WITH_CANDIDATE_BOUND_RESPONSES'
    wire['candidate_response_profile'] = PROFILE
    wire['pair_targets'] = pair_descriptions
    wire['response_schema'] = output_schema
    wire['instructions'] += (
        ' For EACH pair consult pair_targets and that candidate\'s literal question and representation. '
        'A neighboring candidate\'s question or executable availability never applies to this pair. '
        'Select only its permitted_expression_keys; [] means no executable quotation is available. '
        'The explicit pair table is navigation to the original targets, not evidence for a legal judgment. '
        'Retain uncertainty and missing meanings; do not infer that a structurally valid judgment is true.')
    binding = {'profile': PROFILE, 'base_alias_references': references,
               'request_hash': digest(request), 'output_schema_hash': digest(output_schema)}
    return wire, output_schema, binding


def resolve(value, request, schema, binding):
    _, output_schema, expected = prepare(request, schema)
    if binding != expected:
        fail('Candidate response binding changed')
    error = next(Draft202012Validator(output_schema).iter_errors(value), None)
    if error:
        fail('Response violates candidate-bound schema: ' + error.message[:1200])
    return aliases.resolve(value, request, schema, binding['base_alias_references'])
