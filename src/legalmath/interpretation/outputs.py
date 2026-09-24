"""Proposed result meanings; predicate satisfaction is not compliance authority."""
from typing import Literal
from ..canonical import digest
from ..errors import LegalMathError

OutputMeaning = Literal['TRUE_IS_PROHIBITED','TRUE_IS_COMPLIANT','TRUE_IS_SATISFIED','VALUE']
BOOLEAN_MEANINGS = ('TRUE_IS_PROHIBITED','TRUE_IS_COMPLIANT','TRUE_IS_SATISFIED')
MEANINGS = (*BOOLEAN_MEANINGS,'VALUE')

CONVENTION = (
    ' Declare the actual question answered by the result. For Boolean compliance '
    'or prohibition decisions begin statement with [TRUE_IS_COMPLIANT] or '
    '[TRUE_IS_PROHIBITED] respectively. For a Boolean condition, trigger or '
    'eligibility predicate use [TRUE_IS_SATISFIED] and explain precisely what '
    'true and false mean. Never relabel a licensing trigger as compliance, '
    'prohibition or licence possession. For non-Boolean results use [VALUE] '
    'and state the units. These meanings are proposals, not approvals.'
)


def convention(reading):
    return next((meaning for meaning in MEANINGS
                 if reading['statement'].startswith('['+meaning+']')),None)


def descriptor(reading, question):
    meaning=convention(reading);formal=reading['formalization']
    if not formal or meaning is None:raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if (formal['result_type']=='bool')!=(meaning in BOOLEAN_MEANINGS):
        raise LegalMathError('E_TYPE',details='Result type and output meaning disagree')
    if not isinstance(question,str) or not question.strip():raise LegalMathError('E_SCHEMA')
    return {'version':'proposed-output.v1','question':question,'meaning':meaning,
            'subject':reading['subject'],'statement':reading['statement'],
            'reading_hash':digest(reading),'type':formal['result_type'],
            'authority':'PROPOSED_INTERPRETATION','release_eligible':False}


def validate_descriptor(value,reading,question):
    if value!=descriptor(reading,question):raise LegalMathError('E_STALE_REVIEW')
    return value
