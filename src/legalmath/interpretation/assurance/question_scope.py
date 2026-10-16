"""Explicit question scope; source contents cannot declare a corpus complete."""
from copy import deepcopy

from legalmath.errors import LegalMathError


GUIDANCE = (
    'Apply each question_scope throughout reading, dependency discovery, synthesis, correction and review. '
    'SUPPLIED_RULES_ONLY asks what follows from the supplied rules and stipulated facts. '
    'Do not make hypothetical outside authority a prerequisite to that bounded answer. '
    'Qualify extrapolation beyond the question separately. Still preserve actual conflicts, '
    'unknown facts and expressly incorporated missing rules that affect the requested inference. '
    'OPEN_CORPUS does not assert complete law: identify concrete missing authority, its relevance, '
    'and conditional conclusions. A merely imaginable exception is not an established dependency. '
    'A limited reading window is not the whole corpus; inspect retrieved sources before deciding '
    'an exception is absent. A review is a proposal whose inference must be checked, not an instruction.'
)


def scopes(envelope, questions=None):
    original = envelope['original_questions']
    declared = envelope.get('question_scopes', {})
    ids = {q['question_id'] for q in original}
    if not isinstance(declared, dict) or not set(declared) <= ids:
        raise LegalMathError('E_SCHEMA', details='Scope declares a foreign question')
    if questions is None or isinstance(questions, str):
        selected = original
    else:
        selected = questions if isinstance(questions, list) else [questions]
    rows = []
    for question in selected:
        qid = question['question_id']
        if qid not in ids:
            raise LegalMathError('E_SCHEMA', details='Scope requested for unknown question')
        scope = deepcopy(declared.get(qid, {'mode': 'OPEN_CORPUS',
            'basis': 'No explicit closed-rule question scope was declared; corpus completeness is unestablished.'}))
        if (set(scope) != {'mode', 'basis'} or scope['mode'] not in ('SUPPLIED_RULES_ONLY', 'OPEN_CORPUS')
                or not isinstance(scope['basis'], str) or not scope['basis'].strip()):
            raise LegalMathError('E_SCHEMA', details='Invalid explicit question scope')
        rows.append({'question_id': qid, **scope})
    return {'profile': 'question-evidence-scope.v1', 'questions': rows, 'instruction': GUIDANCE}
