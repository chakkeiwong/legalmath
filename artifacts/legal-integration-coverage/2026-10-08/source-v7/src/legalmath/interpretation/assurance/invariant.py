"""Conditional decisions over an explicitly complete *retained* hypothesis set.

This module proves no English interpretation. It refuses to omit a retained
branch, compare different questions, or infer a fact alignment from its name.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from ...canonical import digest
from ...errors import LegalMathError
from ...ir.evaluate import evaluate
from ..contracts import Packet, parse
from ..search.models import Reading
from ..search.formal import bundle, project, RULE
from ..outputs import convention
from .controls import check_controls, assert_same_question


def prepare(packet, question, alternatives, retained_ids, at):
    parse(Packet, packet)
    check_controls([question], packet)
    if (not retained_ids or len(set(retained_ids)) != len(retained_ids)
            or set(alternatives) != set(retained_ids)):
        raise LegalMathError('E_REFERENCE', details='Every retained hypothesis is required exactly once')
    rows = {}; shared = None
    for ident in sorted(alternatives):
        item = alternatives[ident]
        assert_same_question(question, item['question'])
        reading = parse(Reading, item['reading'])
        compiled = None; failure = None
        try:
            compiled = bundle(reading, packet, at)
        except LegalMathError as exc:
            failure = {'code': exc.code, 'details': exc.details}
        if compiled is not None:
            required = {'PROHIBITED':'TRUE_IS_PROHIBITED','COMPLIANT':'TRUE_IS_COMPLIANT',
                        'DUTY_STATE':None}.get(question['result_kind'],'TRUE_IS_SATISFIED')
            if required is None or convention(reading) != required:
                raise LegalMathError('E_TYPE', details='Reading polarity does not match typed question')
            if reading['formalization']['result_type'] != 'bool':
                raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Boolean question required')
            facts = sorted(reading['formalization']['facts'], key=lambda f: f['name'])
            if shared is not None and facts != shared:
                raise LegalMathError('E_TYPE', details='Fact definitions differ; explicit reviewed alignment required')
            shared = facts
        rows[ident] = {'reading': reading, 'bundle': compiled, 'encoding_failure': failure}
    result = {'question': deepcopy(question), 'source_packet_hash': digest(packet),
              'retained_ids': sorted(retained_ids), 'alternatives': rows,
              'shared_facts': shared or [], 'compiled_at': at,
              'hypothesis_completeness_proved': False, 'release_eligible': False}
    result['set_hash'] = digest(result)
    return result


def validate_prepared(prepared):
    if digest({k: v for k, v in prepared.items() if k != 'set_hash'}) != prepared['set_hash']:
        raise LegalMathError('E_INTEGRITY')
    if (not prepared['retained_ids'] or
            sorted(prepared['alternatives']) != prepared['retained_ids']):
        raise LegalMathError('E_REFERENCE')


def aggregate(outcomes):
    """No vote, score threshold, majority, or unknown-to-false conversion."""
    if not outcomes:
        raise LegalMathError('E_REFERENCE')
    if any(v is None for v in outcomes.values()):
        return 'UNENCODED_ALTERNATIVE', None
    values = list(outcomes.values())
    if all(v['status'] == 'OUT_OF_SCOPE' for v in values):
        return 'INVARIANT_NOT_APPLICABLE', None
    # Known Boolean results use TRUE/FALSE in RuleIR. Different scope
    # outcomes are a disagreement, even if all emitted truth values are false.
    if any(v['status'] not in ('TRUE', 'FALSE', 'OUT_OF_SCOPE') for v in values):
        return 'UNKNOWN_OR_CONFLICT', None
    if len({digest(v) for v in values}) != 1:
        return 'INTERPRETATION_DISAGREEMENT', None
    first = values[0]
    if type(first.get('value')) is not bool:
        return 'UNKNOWN_OR_CONFLICT', None
    return 'INVARIANT_KNOWN', first['value']


def decide(prepared, snapshot, source_packet_hash, at, known_at):
    validate_prepared(prepared)
    if source_packet_hash != prepared['source_packet_hash']:
        status, value, outcomes = 'SOURCE_CHANGED', None, {}
    else:
        outcomes = {ident: project(evaluate(row['bundle'], snapshot, RULE, at, known_at))
                    if row['bundle'] is not None else None
                    for ident, row in prepared['alternatives'].items()}
        status, value = aggregate(outcomes)
    return {'status': status, 'value': value, 'outcomes': outcomes,
            'question_hash': digest(prepared['question']), 'set_hash': prepared['set_hash'],
            'source_packet_hash': source_packet_hash, 'snapshot_hash': digest(snapshot),
            'conditional_on_retained_hypotheses': True, 'release_eligible': False}


def str_time_facts(iso_timestamp):
    """Explicit Hong Kong local-time interpretation, preserving two start readings."""
    if iso_timestamp is None:
        return dict(blackout=None, calendar_start=None, operational_start=None)
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError('Timezone required')
    except (ValueError, TypeError, AttributeError) as exc:
        raise LegalMathError('E_SCHEMA', details='An explicit timezone is required') from exc
    hk = ZoneInfo('Asia/Hong_Kong'); dt = dt.astimezone(hk)
    start = datetime(2026, 1, 28, tzinfo=hk)
    midnight = datetime(2026, 2, 2, tzinfo=hk)
    launch = datetime(2026, 2, 2, 9, tzinfo=hk)
    return dict(blackout=start <= dt < launch, calendar_start=dt >= midnight,
                operational_start=dt >= launch)


def report_history(event_triggers, *, history_complete):
    """Existence has a witness; absence requires a complete history."""
    if type(history_complete) is not bool or any(v is not None and type(v) is not bool for v in event_triggers):
        raise LegalMathError('E_SCHEMA')
    if any(v is True for v in event_triggers):
        return True
    if not history_complete or any(v is None for v in event_triggers):
        return None
    return False
