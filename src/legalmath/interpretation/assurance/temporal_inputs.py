"""Attributed factual event questions; these functions invent no legal deadlines."""
from copy import deepcopy
from typing import Literal
from pydantic import Field

from ...canonical import digest
from ...domain import timestamp, interval, eligible
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, parse
from .legal_profile import verify_anchor

Kind = Literal['CONTACT', 'ORIGINAL_SUBMISSION', 'RESUBMISSION', 'SCHEMA_VALIDATION', 'LIAISON']


class Event(Strict):
    event_id: Id
    str_id: Id
    kind: Kind
    related_event_id: Id | None
    occurred_at: Text
    recorded_at: Text
    status: Literal['CONFIRMED', 'DISPUTED']
    evidence_ids: list[Id] = Field(min_length=1, max_length=32)


class Coverage(Strict):
    str_id: Id
    kinds: list[Kind] = Field(min_length=1, max_length=5)
    from_inclusive: Text
    through_inclusive: Text
    recorded_at: Text
    evidence_ids: list[Id] = Field(min_length=1, max_length=32)


def project(events, coverage, *, str_id, kind, since, assessment_at, known_at,
            original_event_id=None):
    """Existence by an instant; absence only over a declared complete interval.

    Coverage is a supplied completeness assertion with evidence, not a fact
    established by this function. Conflicting event IDs are rejected even when
    a witness would otherwise suffice. A disputed relevant event yields CONFLICT.
    """
    for t in (since, assessment_at, known_at):
        timestamp(t)
    if since > assessment_at:
        raise LegalMathError('E_TIME')
    if kind not in ('CONTACT', 'RESUBMISSION', 'SCHEMA_VALIDATION', 'LIAISON'):
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if (kind == 'RESUBMISSION') != (original_event_id is not None):
        raise LegalMathError('E_REFERENCE')
    if len(events) > 2000 or len(coverage) > 100:
        raise LegalMathError('E_RESOURCE_LIMIT')
    # Validate the subject with the same bounded identifier contract as events.
    class Subject(Strict):
        str_id: Id
        original_event_id: Id | None
    parse(Subject, {'str_id': str_id, 'original_event_id': original_event_id})
    values = [parse(Event, e) for e in events]
    covers = [parse(Coverage, c) for c in coverage]
    by_id = {}
    for e in values:
        timestamp(e['occurred_at']); timestamp(e['recorded_at'])
        if e['recorded_at'] < e['occurred_at']:
            raise LegalMathError('E_TIME', details='Observed-event evidence cannot precede the event')
        if len(set(e['evidence_ids'])) != len(e['evidence_ids']):
            raise LegalMathError('E_DUPLICATE_ID')
        if e['event_id'] in by_id and by_id[e['event_id']] != e:
            raise LegalMathError('E_EVENT_ID_COLLISION')
        if (e['kind'] == 'RESUBMISSION') != (e['related_event_id'] is not None):
            raise LegalMathError('E_EVENT_ATTRIBUTION')
        by_id[e['event_id']] = e
    for c in covers:
        for k in ('from_inclusive', 'through_inclusive', 'recorded_at'):
            timestamp(c[k])
        if c['from_inclusive'] > c['through_inclusive'] or c['recorded_at'] < c['through_inclusive']:
            raise LegalMathError('E_TIME')
        if len(set(c['kinds'])) != len(c['kinds']) or len(set(c['evidence_ids'])) != len(c['evidence_ids']):
            raise LegalMathError('E_DUPLICATE_ID')
    original = by_id.get(original_event_id)
    linkage_missing = kind == 'RESUBMISSION' and (original is None or
        original['recorded_at'] > known_at or original['occurred_at'] > assessment_at)
    if kind == 'RESUBMISSION' and original is not None and (
            original['kind'] != 'ORIGINAL_SUBMISSION' or original['str_id'] != str_id):
        raise LegalMathError('E_EVENT_ATTRIBUTION')
    relevant = [e for e in by_id.values() if e['str_id'] == str_id and e['kind'] == kind
                and since <= e['occurred_at'] <= assessment_at and e['recorded_at'] <= known_at
                and (kind != 'RESUBMISSION' or e['related_event_id'] == original_event_id)]
    if original is not None and any(e['occurred_at'] < original['occurred_at'] for e in relevant):
        raise LegalMathError('E_TIME', details='Resubmission precedes its linked original')
    complete = [c for c in covers if c['str_id'] == str_id and kind in c['kinds']
                and c['from_inclusive'] <= since and c['through_inclusive'] >= assessment_at
                and c['recorded_at'] <= known_at]
    conflict = any(e['status'] == 'DISPUTED' for e in relevant) or (
        kind == 'RESUBMISSION' and original is not None and original['recorded_at'] <= known_at
        and original['status'] == 'DISPUTED')
    if conflict:
        status, value = 'CONFLICT', None
    elif linkage_missing:
        status, value = 'UNKNOWN', None
    elif relevant:
        status, value = 'TRUE', True
    elif complete:
        status, value = 'FALSE', False
    else:
        status, value = 'UNKNOWN', None
    inputs = {'events': values, 'coverage': covers, 'str_id': str_id, 'kind': kind,
              'since': since, 'assessment_at': assessment_at, 'known_at': known_at,
              'original_event_id': original_event_id}
    return {'status': status, 'value': value, 'witness_event_ids': sorted(e['event_id'] for e in relevant),
        'coverage_evidence_ids': sorted({i for c in complete for i in c['evidence_ids']}),
        'missing_linked_original': linkage_missing, 'input_hash': digest(inputs),
        'question': {'kind': kind, 'str_id': str_id, 'since': since,
                     'assessment_at': assessment_at, 'known_at': known_at},
        'meaning': 'Existence in the stated factual interval, conditional on event and coverage evidence',
        'legal_performance_established': False, 'release_eligible': False}


def context(*, bundle_interval, source_interval, documents, assessment_at, known_at):
    """Separate declared bundle validity from a source-effectiveness assertion."""
    timestamp(assessment_at); timestamp(known_at)
    interval(bundle_interval['valid_from'], bundle_interval['valid_until'])
    bundle_ok = eligible(bundle_interval['valid_from'], bundle_interval['valid_until'], assessment_at)
    source_ok = None
    if source_interval is not None:
        if set(source_interval) != {'valid_from', 'valid_until', 'evidence', 'rationale'}:
            raise LegalMathError('E_SCHEMA')
        if not source_interval['evidence'] or not source_interval['rationale']:
            raise LegalMathError('E_REFERENCE')
        interval(source_interval['valid_from'], source_interval['valid_until'])
        for anchor in source_interval['evidence']:
            verify_anchor(anchor, documents)
        source_ok = eligible(source_interval['valid_from'], source_interval['valid_until'], assessment_at)
    status = ('BUNDLE_TIME_UNSUPPORTED' if not bundle_ok else 'SOURCE_EFFECTIVENESS_UNKNOWN'
              if source_ok is None else 'SOURCE_TIME_UNSUPPORTED' if not source_ok
              else 'CONDITIONALLY_TIME_APPLICABLE')
    return {'status': status, 'bundle_interval': deepcopy(bundle_interval),
        'source_interval': deepcopy(source_interval), 'assessment_at': assessment_at, 'known_at': known_at,
        'source_effectiveness_interpretation_proved': False, 'release_eligible': False}


def trigger_and_performance(trigger, performance):
    """Keep these questions distinct even when the duty's trigger is known."""
    states = {'TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT', 'ERROR', 'OUT_OF_SCOPE'}
    if trigger.get('status') not in states or (performance is not None and performance.get('status') not in states):
        raise LegalMathError('E_SCHEMA')
    return {'trigger': deepcopy(trigger), 'performance': deepcopy(performance),
            'status': 'PERFORMANCE_UNENCODED' if performance is None else 'SEPARATE_QUESTIONS_RECORDED',
            'overall_compliance': 'NOT_ESTABLISHED', 'release_eligible': False}
