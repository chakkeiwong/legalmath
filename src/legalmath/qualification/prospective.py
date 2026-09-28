"""Immutable prospective selection and development-contamination accounting.

Local publication metadata is a premise, not an authenticated publication clock.
This ledger never turns engineering observations into legal accuracy estimates.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import re

from ..canonical import canonical, digest, loads
from ..errors import LegalMathError
from . import POLICY


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def instant(value):
    try:
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
            raise ValueError
        return value
    except (ValueError, TypeError, AttributeError):
        raise LegalMathError('E_SCHEMA', details='Explicit UTC instant required') from None


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise LegalMathError('E_SCHEMA', details='SHA-256 identity required')
    return value


def put_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value))


@contextmanager
def locked(directory):
    with (Path(directory)/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def freeze(directory, method_hash, families, *, ends_at, development_sources=()):
    sha(method_hash)
    if (not isinstance(families, list) or not families or any(not isinstance(x, str) or not x for x in families)
            or len(set(families)) != len(families)):
        raise LegalMathError('E_SCHEMA')
    start = now()
    if instant(ends_at) <= instant(start):
        raise LegalMathError('E_SCHEMA', details='Confirmation window must end after the freeze')
    development = sorted({sha(x) for x in development_sources})
    out = Path(directory); out.mkdir(parents=True, exist_ok=False)
    spec = {'policy': POLICY, 'method_hash': method_hash, 'starts_at': start, 'ends_at': ends_at,
            'families': sorted(families), 'development_sources': development,
            'selection': 'All submitted sources from these families published and first encountered within the window; every submitted item is retained.',
            'quality_evidence': 'Machine-checked proof or explicit qualification only',
            'human_quality_evidence': 'FORBIDDEN',
            'clock_qualification': 'Local freeze and supplied publication metadata; publication authenticity and inventory completeness are not established.',
            'legal_generalization': 'NOT_ESTABLISHED'}
    spec['window_hash'] = digest(spec); put_new(out/'freeze.json', spec)
    (out/'events').mkdir()
    return spec


def load(directory, expected_hash):
    out = Path(directory); spec = loads((out/'freeze.json').read_bytes())
    if (spec['window_hash'] != expected_hash or spec['window_hash'] != digest({k: v for k, v in spec.items() if k != 'window_hash'})
            or spec['policy'] != POLICY):
        raise LegalMathError('E_INTEGRITY', details='Frozen protocol changed')
    events = []; previous = spec['window_hash']
    for i, path in enumerate(sorted((out/'events').glob('*.json'))):
        row = loads(path.read_bytes())
        if (path.name != f'{i:06d}.json' or row['previous'] != previous
                or row['event_hash'] != digest({k: v for k, v in row.items() if k != 'event_hash'})):
            raise LegalMathError('E_INTEGRITY', details='Broken immutable event history')
        previous = row['event_hash']; events.append(row)
    return spec, events


def append(directory, spec, events, payload):
    event = {'previous': events[-1]['event_hash'] if events else spec['window_hash'], 'at': now(), **payload}
    event['event_hash'] = digest(event)
    put_new(Path(directory)/'events'/f'{len(events):06d}.json', event)
    return event


def admit(directory, expected_hash, item, *, method_hash):
    required = {'task_id', 'family', 'source_hash', 'question_hash', 'published_at', 'first_seen_at'}
    if (not isinstance(item, dict) or set(item) != required or not isinstance(item['task_id'], str) or not item['task_id']
            or not isinstance(item['family'], str)):
        raise LegalMathError('E_SCHEMA', details='No human labels, expected answers, ratings or asserted quality may enter selection')
    sha(item['source_hash']); sha(item['question_hash']); sha(method_hash)
    published, seen = instant(item['published_at']), instant(item['first_seen_at'])
    with locked(directory):
        spec, events = load(directory, expected_hash)
        if any(e.get('item', {}).get('task_id') == item['task_id'] for e in events):
            raise LegalMathError('E_DUPLICATE_ID')
        reasons = []
        if item['family'] not in spec['families']: reasons.append('OUTSIDE_FROZEN_FAMILIES')
        if not instant(spec['starts_at']) < published <= instant(spec['ends_at']): reasons.append('OUTSIDE_PUBLICATION_WINDOW')
        if not instant(spec['starts_at']) < seen <= instant(now()) or seen < published: reasons.append('INVALID_ENCOUNTER_CHRONOLOGY')
        if item['source_hash'] in spec['development_sources']: reasons.append('DEVELOPMENT_SOURCE')
        if method_hash != spec['method_hash']: reasons.append('METHOD_CHANGED')
        if any(e['kind'] == 'REPAIR' for e in events): reasons.append('WINDOW_USED_FOR_REPAIR')
        return append(directory, spec, events, {'kind': 'SELECT', 'item': item, 'method_hash': method_hash,
                      'status': 'PENDING' if not reasons else 'INELIGIBLE', 'reasons': reasons})


def repair(directory, expected_hash, *, new_method_hash, reason):
    sha(new_method_hash)
    if not isinstance(reason, str) or not reason:
        raise LegalMathError('E_SCHEMA')
    with locked(directory):
        spec, events = load(directory, expected_hash)
        return append(directory, spec, events, {'kind': 'REPAIR', 'new_method_hash': new_method_hash, 'reason': reason,
                      'disposition': 'Subsequent work is development; use a later untouched confirmation window.'})


def observe(directory, expected_hash, task_id, qualification_directory, current_model, jdk, *, compiler=None):
    from .assurance import verify
    # Actual proof/runtime rechecking is mandatory; callers cannot submit a grade.
    result = verify(qualification_directory, current_model, jdk, compiler=compiler)
    with locked(directory):
        spec, events = load(directory, expected_hash)
        matches = [e for e in events if e['kind'] == 'SELECT' and e['item']['task_id'] == task_id]
        if len(matches) != 1 or any(e['kind'] == 'OBSERVE' and e['task_id'] == task_id for e in events):
            raise LegalMathError('E_REFERENCE')
        selected = matches[0]
        reading = current_model['review']['reading']
        packet = current_model['review']['packet']
        if (selected['status'] != 'PENDING' or result['identity']['method_hash'] != spec['method_hash']
                or result['identity']['source_hash'] != selected['item']['source_hash']
                or reading is None or digest(reading['statement']) != selected['item']['question_hash']
                or packet is None or packet['authority'] != 'RETAINED_SOURCE'
                or not result['summary']['selected_cases']):
            raise LegalMathError('E_STALE_REVIEW', details='Observation does not answer the frozen source/question/method task')
        if any(e['kind'] == 'REPAIR' for e in events):
            raise LegalMathError('E_STALE_REVIEW', details='Repaired window is development evidence')
        return append(directory, spec, events, {'kind': 'OBSERVE', 'task_id': task_id,
                      'qualification_hash': result['report_hash'], 'summary': result['summary'],
                      'legal_generalization': 'NOT_ESTABLISHED'})


def report(directory, expected_hash, *, expected_head=None):
    spec, events = load(directory, expected_hash)
    head=events[-1]['event_hash'] if events else spec['window_hash']
    if expected_head is not None and head != sha(expected_head):
        raise LegalMathError('E_INTEGRITY',details='History differs from the externally retained head')
    selected = [e for e in events if e['kind'] == 'SELECT']
    observed = {e['task_id']: e for e in events if e['kind'] == 'OBSERVE'}
    rows = [{**e['item'], 'status': 'OBSERVED_QUALIFIED' if e['item']['task_id'] in observed else e['status'],
             'reasons': e['reasons']} for e in selected]
    return {'window_hash': expected_hash, 'event_head':head,'external_head_checked':expected_head is not None,
            'history_qualification':None if expected_head is not None else 'Local hash chain only; retain the event head independently to detect truncation or a rewritten chain.',
            'method_hash': spec['method_hash'], 'submitted': len(rows),
            'eligible': sum(e['status'] == 'PENDING' for e in selected), 'observed': len(observed),
            'pending': sum(e['status'] == 'PENDING' and e['item']['task_id'] not in observed for e in selected),
            'ineligible': sum(e['status'] == 'INELIGIBLE' for e in selected), 'tasks': rows,
            'repaired': any(e['kind'] == 'REPAIR' for e in events),
            'window_closed': instant(now()) > instant(spec['ends_at']),
            'inventory_completeness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED',
            'human_quality_evidence': False}
