"""Exact original-answer questions, kept separate from proposed candidate questions."""
from copy import deepcopy

from ...canonical import digest
from ...errors import LegalMathError


def validate(questions, selected_slice=None):
    # Import lazily: the answer module itself uses the investigation transport.
    from .investigation_answer import exact_questions, question_text
    result = exact_questions(questions)
    if selected_slice is not None and question_text(result) != selected_slice:
        raise LegalMathError('E_REFERENCE', details='Original questions differ from selected source slice')
    return result


def attach(request, questions):
    """Give each model stage the same bound answer target without rewriting law."""
    if questions is None:
        return request
    parsed = validate(questions)
    packet = request.get('source_packet')
    if isinstance(packet, dict) and 'selected_slice' in packet:
        validate(parsed, packet['selected_slice'])
    if 'original_questions' in request and request['original_questions'] != parsed:
        raise LegalMathError('E_STALE_REVIEW', details='Model request changed original questions')
    return {**deepcopy(request), 'original_questions': deepcopy(parsed),
        'original_question_binding': digest(parsed),
        'original_question_instruction':
            'These are the original answer questions, distinct from proposed candidate questions. '
            'Preserve each actor, condition, conduct, outcome, time and source qualification. '
            'A duty trigger alone cannot answer fulfillment; a quoted source does not by itself '
            'establish the legal warrant. Record contrary evidence and unresolved standards.'}
