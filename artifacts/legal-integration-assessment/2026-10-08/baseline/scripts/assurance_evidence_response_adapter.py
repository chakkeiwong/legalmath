"""Lossless acceptance of one explicitly identified, conservative response shape."""
from copy import deepcopy
from typing import Literal
from pydantic import Field
from legalmath.interpretation.contracts import Strict, parse
from legalmath.interpretation.search.models import Quote
import assurance_evidence_core as c


class Reading(Strict):
    id: str
    disposition: Literal['conditional', 'unformalized', 'challenged']
    reason: str = Field(min_length=1, max_length=1800)
    evidence: list[Quote] = Field(min_length=1, max_length=8)
    assumptions: list[str] = Field(max_length=12)
    remaining: list[str] = Field(max_length=20)
    repairs: list[str] = Field(max_length=6)


class Question(Strict):
    ids: list[str] = Field(min_length=1, max_length=64)
    status: Literal['unresolved']
    reason: str = Field(min_length=1, max_length=1800)
    evidence: list[Quote] = Field(max_length=8)


class Response(Strict):
    binding_hash: str
    kind: Literal['propagation']
    role: Literal['structure-reader', 'exception-challenger']
    readings: list[Reading] = Field(min_length=1, max_length=2)
    questions: list[Question] = Field(min_length=1, max_length=64)


def validate(value, task, aliases):
    import assurance_evidence_protocol as p
    request = task['request']
    if request['kind'] != 'propagation' or request['obligations']:
        c.fail('E_REFERENCE', 'Adapter cannot infer omitted obligation dispositions')
    raw = p.translate(parse(Response, value), aliases['tokens'])
    if raw['binding_hash'] != request['binding_hash'] or raw['role'] != task['role']:
        c.fail('E_REFERENCE', 'Adapter response binding/role mismatch')
    c.verify_packet(request['source_packet'])
    selected = request['selected']
    ids = [r['id'] for r in raw['readings']]
    if len(ids) != len(set(ids)) or set(ids) != set(selected):
        c.fail('E_REFERENCE', 'Adapter needs exactly the original selected readings')
    readings = []
    for r in raw['readings']:
        c.check_quotes(r['evidence'], request['source_packet'])
        before = request['prior_assessments'][r['id']]
        disposition = r['disposition']
        if disposition == 'conditional' and before['formalization'] is None:
            c.fail('E_REFERENCE', 'Adapter cannot retain a missing program')
        if disposition == 'unformalized' and before['formalization'] is not None:
            c.fail('E_REFERENCE', 'Adapter cannot silently remove a program')
        remaining, repairs = list(r['remaining']), list(r['repairs'])
        if repairs and disposition == 'conditional':
            disposition = 'challenged'
        elif repairs and disposition == 'unformalized':
            remaining += ['Future formalization condition: '+x for x in repairs]
            repairs = []
        readings.append({'reading_id': r['id'], 'reading_hash': request['reading_hashes'][r['id']],
            'disposition': {'conditional': 'RETAIN_CONDITIONAL', 'unformalized': 'RETAIN_UNFORMALIZED', 'challenged': 'CHALLENGED'}[disposition],
            'explanation': r['reason'], 'evidence': r['evidence'], 'added_assumptions': r['assumptions'],
            'remaining_questions': remaining, 'required_program_repairs': repairs})
    questions = []
    mapping = aliases['questions']
    for group in raw['questions']:
        if not set(group['ids']) <= set(mapping):
            c.fail('E_REFERENCE', 'Foreign question in adapter response')
        if len({mapping[q]['reading_id'] for q in group['ids']}) != 1:
            c.fail('E_REFERENCE', 'Adapter group crosses readings')
        c.check_quotes(group['evidence'], request['source_packet'])
        for q in group['ids']:
            identity = mapping[q]
            questions.append({'reading_id': identity['reading_id'], 'question_id': identity['question_id'],
                'status': 'REMAINS_OPEN', 'evidence': group['evidence'], 'explanation': group['reason']})
    expected = {(q['reading_id'], q['question_id']) for q in request['question_inventory']}
    actual = [(q['reading_id'], q['question_id']) for q in questions]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        c.fail('E_REFERENCE', 'Adapter lost or repeated an original question')
    # No source text, quote, reason, assumption or question is truncated. The
    # missing non-claim is supplied as a system restriction, not a model finding.
    return {'binding_hash': raw['binding_hash'], 'reading_updates': readings,
            'question_updates': questions, 'obligation_updates': [],
            'legal_correctness': 'NOT_ESTABLISHED'}
