"""Bound output accounting while every request retains the entire source/context."""
from copy import deepcopy

from ...canonical import digest
from ...errors import LegalMathError
from . import single_reader

PROFILE = 'legalmath.reconciliation-output-batches.v1'


def batches(coverage, maximum=66):
    ids = [row['concern_id'] for row in coverage['concerns']]
    if type(maximum) is not int or not 1 <= maximum <= 500: raise LegalMathError('E_RESOURCE_LIMIT')
    if not ids or len(ids) != len(set(ids)): raise LegalMathError('E_REFERENCE')
    return [ids[i:i+maximum] for i in range(0, len(ids), maximum)]


def request(original, selected):
    expected = {row['concern_id'] for row in original['coverage']['concerns']}
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= expected:
        raise LegalMathError('E_REFERENCE')
    value = deepcopy(original)
    identities = value.setdefault('output_identity_contract', {})
    identities['question_hashes'] = {q['control_id']: digest(q) for q in original['interpretation']['questions']}
    value['reconciliation_batch'] = {'profile': PROFILE, 'selected_concern_ids': list(selected),
        'original_coverage_hash': digest(original['coverage']), 'total_concerns': len(expected),
        'instruction': 'All source units, concerns, questions and the original interpretation remain visible. '
            'Return dispositions for exactly selected_concern_ids in this response, and retain every original question. '
            'Consider cross-concern interactions using the entire context. Do not silently revise another batch. '
            'Keep the original packet/interpretation/coverage hashes. Retain uncertainty and proposed revisions. '
            'Copy each question_hash from output_identity_contract.question_hashes; do not compute or invent a digest. '
            'The joining check accounts for other concerns in separate responses; this response alone cannot complete the whole task.'}
    schema = single_reader.Reconciliation.model_json_schema()
    schema['properties']['concerns']['minItems'] = len(selected)
    schema['properties']['concerns']['maxItems'] = len(selected)
    schema['$defs']['QuestionDisposition']['properties']['question_hash']['enum'] = list(identities['question_hashes'].values())
    schema['$defs']['QuestionDisposition']['properties']['question_id']['enum'] = list(identities['question_hashes'])
    return value, schema


def join(packet, interpretation, coverage, pieces):
    """Return incompleteness and divergent questions/revisions, never a consensus."""
    expected = {row['concern_id'] for row in coverage['concerns']}
    if len(expected) != len(coverage['concerns']): raise LegalMathError('E_DUPLICATE_ID')
    seen = set(); checked = []
    for piece in pieces:
        selected = piece['selected_concern_ids']
        if seen & set(selected): raise LegalMathError('E_DUPLICATE_ID')
        value = single_reader.validate_reconciliation(piece['value'], packet, interpretation, coverage,
                                                       required_concerns=selected)
        seen.update(selected); checked.append(value)
    question_ids = [q['control_id'] for q in interpretation['questions']]
    differences = []
    for ident in question_ids:
        variants = {r['status'] for v in checked for r in v['questions'] if r['question_id'] == ident}
        if len(variants) > 1: differences.append({'question_id': ident, 'statuses': sorted(variants)})
    revisions = {digest(v['revised_interpretation']) for v in checked if v['revised_interpretation'] is not None}
    return {'profile': PROFILE, 'coverage_hash': digest(coverage), 'total_concerns': len(expected),
        'addressed_concerns': sorted(seen), 'missing_concerns': sorted(expected-seen),
        'accounting_complete': seen == expected, 'question_disagreements': differences,
        'proposed_revision_hashes': sorted(revisions),
        'pieces': checked, 'legal_correctness': 'NOT_ESTABLISHED',
        'cross_batch_semantic_consistency': 'NOT_ESTABLISHED',
        'automatic_revision_applied': False}
