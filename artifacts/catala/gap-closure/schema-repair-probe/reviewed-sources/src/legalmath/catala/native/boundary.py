"""Conservative complete-input semantics with field and collection-item evidence."""
from ...canonical import canonical, digest
from ...domain import eligible, interval, timestamp
from .contracts import fail, validate_task, validate_value, item_type, option_type, enum_cases, outside_domain


def paths(task, typ, value, path):
    yield path
    optional = option_type(typ)
    if optional is not None:
        if value is not None:
            yield from paths(task, optional, value['present'], path + '/present')
        return
    sub = item_type(typ)
    if sub is not None:
        for i, v in enumerate(value):
            yield from paths(task, sub, v, path + '/' + str(i))
    elif typ not in ('boolean', 'integer', 'decimal', 'money', 'date'):
        d = next(d for d in task['types'] if d['name'] == typ)
        if d['kind'] == 'record':
            for f in d['fields']:
                yield from paths(task, f['type'], value[f['name']], path + '/' + f['name'])
        elif isinstance(value, dict):
            c = next(c for c in enum_cases(d) if c['name'] == value['case'])
            if c['type']:
                yield from paths(task, c['type'], value['value'], path + '/value')


def prepare(task, snapshot):
    t = validate_task(task)
    if len(canonical(snapshot)) > 1_000_000:
        fail('E_RESOURCE_LIMIT')
    if set(snapshot) != {'record_type', 'subject_id', 'revision', 'valid_at', 'known_at', 'facts', 'evidence'} or snapshot['record_type'] != 'NativeFactSnapshot':
        fail()
    if any(type(snapshot[k]) is not str or not snapshot[k] for k in ('subject_id', 'revision')):
        fail()
    valid, known = timestamp(snapshot['valid_at']), timestamp(snapshot['known_at'])
    facts, evidence = snapshot['facts'], snapshot['evidence']
    if type(facts) is not dict or type(evidence) is not dict:
        fail()
    if set(facts) - {f['name'] for f in t['inputs']}:
        fail('E_REFERENCE')
    for path, ids in evidence.items():
        if not path.startswith('/') or type(ids) is not list or not ids or len(ids) != len(set(ids)) or any(type(v) is not str or not v for v in ids):
            fail('E_SCHEMA', 'Evidence IDs must be nonempty and unique')
    missing, conflicts, values, used_paths = [], [], {}, set()
    for f in t['inputs']:
        name = f['name']
        fact = facts.get(name, {'status': 'unknown', 'reason': 'MISSING'})
        if type(fact) is not dict:
            fail()
        status = fact.get('status')
        if status in ('unknown', 'conflict'):
            if set(fact) != {'status', 'reason'} or type(fact['reason']) is not str or not fact['reason']:
                fail()
            (missing if status == 'unknown' else conflicts).append(name)
            continue
        if status != 'known' or set(fact) != {'status', 'value', 'complete', 'valid_from', 'valid_until', 'recorded_at'} or type(fact['complete']) is not bool:
            fail()
        interval(fact['valid_from'], fact['valid_until'])
        timestamp(fact['recorded_at'])
        value = validate_value(t, f['type'], fact['value'])
        required = set(paths(t, f['type'], value, '/' + name))
        if required - evidence.keys():
            fail('E_REFERENCE', 'Field/item evidence is missing')
        used_paths.update(required)
        if not fact['complete'] or not eligible(fact['valid_from'], fact['valid_until'], valid) or fact['recorded_at'] > known:
            missing.append(name)
        else:
            values[name] = value
    # Evidence for unavailable/conflicting top-level fields may still be retained.
    allowed = used_paths | {'/' + f['name'] for f in t['inputs']}
    if evidence.keys() - allowed:
        fail('E_REFERENCE', 'Evidence path does not identify a supplied field/item')
    invalid = outside_domain(t, values)
    reason = None
    if not eligible(t['valid_from'], t['valid_until'], valid):
        reason = 'SOURCE_VERSION_TIME'
    elif any(d['source_hash'] is None for d in t['packet']['dependencies']):
        reason = 'UNRESOLVED_SOURCE_DEPENDENCY'
    elif conflicts:
        reason = 'CONFLICTING_INPUTS'
    elif missing:
        reason = 'INCOMPLETE_INPUTS'
    elif invalid:
        reason = 'OUTSIDE_DECLARED_DOMAIN'
    return {'status': 'ABSTAIN' if reason else 'READY', 'reason': reason,
            'missing_inputs': sorted(missing), 'blocking_inputs': sorted(conflicts), 'invalid_inputs': invalid,
            'inputs': values, 'snapshot_hash': digest(snapshot), 'evidence': evidence}


def make_snapshot(task, values, *, revision='0'):
    """Development fixture helper; callers must supply real evidence in host use."""
    evidence = {}
    for f in task['inputs']:
        for p in paths(task, f['type'], values[f['name']], '/' + f['name']):
            evidence[p] = ['synthetic' + p]
    return {'record_type': 'NativeFactSnapshot', 'subject_id': 'synthetic', 'revision': revision,
            'valid_at': '2026-09-25T00:00:00.000000Z', 'known_at': '2026-09-25T00:00:00.000000Z',
            'facts': {name: {'status': 'known', 'value': value, 'complete': True,
                            'valid_from': '2020-01-01T00:00:00.000000Z', 'valid_until': None,
                            'recorded_at': '2026-01-01T00:00:00.000000Z'} for name, value in values.items()},
            'evidence': evidence}
