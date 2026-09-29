"""One bounded scheduler tick with immutable revision histories and retry limits."""
from copy import deepcopy
import fcntl
from pathlib import Path
from ...canonical import canonical, digest, loads
from ...errors import LegalMathError


def immutable(directory, value):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    key = digest(value); path = directory / (key + '.json')
    if path.exists():
        if path.read_bytes() != canonical(value):
            raise LegalMathError('E_INTEGRITY')
    else:
        with path.open('xb') as stream: stream.write(canonical(value))
    return key


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_bytes(canonical(value)); tmp.replace(path)


def fingerprint(control, versions, method, fact_schema, evaluation_at=None):
    dependencies = set(control['dependencies']) | {control['source']}
    return {'control_hash': digest(control), 'sources': {s: versions.get(s) for s in sorted(dependencies)},
            'method': method, 'fact_schema': fact_schema, 'evaluation_at': evaluation_at}


class Monitor:
    def __init__(self, directory, *, cadence_seconds=86400, max_attempts=2, max_controls=20):
        if (type(cadence_seconds) is not int or not 1 <= cadence_seconds <= 604800
                or type(max_attempts) is not int or not 1 <= max_attempts <= 6
                or type(max_controls) is not int or not 1 <= max_controls <= 100):
            raise LegalMathError('E_SCHEMA')
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.cadence, self.maximum, self.max_controls = cadence_seconds, max_attempts, max_controls

    def tick(self, controls, versions, method, fact_schema, now, investigate, *, acquisition_findings=(), evaluation_at=None):
        if type(now) is not int or now < 0 or len(controls) > self.max_controls:
            raise LegalMathError('E_RESOURCE_LIMIT')
        ids = [c['control_id'] for c in controls]
        if len(ids) != len(set(ids)):
            raise LegalMathError('E_DUPLICATE_ID')
        with (self.directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state_path = self.directory / 'state.json'
            state = loads(state_path.read_bytes()) if state_path.exists() else {'last_tick': None, 'controls': {}, 'history': []}
            if state['last_tick'] is not None and now < state['last_tick']:
                raise LegalMathError('E_TIME')
            overdue = state['last_tick'] is not None and now - state['last_tick'] > self.cadence
            tick = {'at': now, 'overdue': overdue, 'cadence_seconds': self.cadence, 'results': [],
                    'acquisition_findings': list(acquisition_findings)}
            for control in controls:
                cid = control['control_id']; scope = fingerprint(control, versions, method, fact_schema, evaluation_at); revision = digest(scope)
                entry = state['controls'].setdefault(cid, {'current': None, 'revisions': {}})
                record = entry['revisions'].setdefault(revision, {'scope': scope, 'attempts': [], 'status': 'PENDING'})
                previous = entry['current']; entry['current'] = revision
                missing = [url for url, version in scope['sources'].items() if version is None]
                if missing:
                    record['status'] = 'SOURCE_UNAVAILABLE'
                    tick['results'].append({'control_id': cid, 'status': 'SOURCE_UNAVAILABLE', 'missing': missing,
                                            'previous_revision': previous, 'revision': revision})
                    continue
                if record['status'] == 'COMPLETED':
                    rh=record['attempts'][-1]['result_hash']
                    evidence=loads((self.directory/'results'/(rh+'.json')).read_bytes())
                    if digest(evidence)!=rh:raise LegalMathError('E_INTEGRITY')
                    tick['results'].append({'control_id': cid, 'status': 'UNCHANGED', 'revision': revision,
                                            'result_hash': rh,'assurance_status':evidence['result'].get('status'),
                                            'unresolved_findings':len(evidence['result'].get('findings',[]))})
                    continue
                if len(record['attempts']) >= self.maximum:
                    tick['results'].append({'control_id': cid, 'status': 'REVISION_RETRY_LIMIT', 'revision': revision})
                    continue
                reservation = {'sequence': len(record['attempts']), 'at': now, 'status': 'RESERVED'}
                record['attempts'].append(reservation)
                immutable(self.directory / 'events', {'control_id': cid, 'revision': revision, **reservation})
                save(state_path, state)  # a crash consumes a reservation and cannot reuse its result
                try:
                    result = investigate(deepcopy(control), deepcopy(scope))
                    if not isinstance(result, dict) or result.get('release_eligible') is not False:
                        raise LegalMathError('E_AUTHORITY', details='Monitoring callbacks cannot grant release authority')
                    status = ('FAILED' if result.get('status') in ('FAILED_INTEGRITY','INVESTIGATION_FAILED')
                              or result.get('execution_complete') is False else 'COMPLETED')
                except Exception as exc:
                    result = {'status': 'INVESTIGATION_FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
                              'release_eligible': False}
                    status = 'FAILED'
                evidence = {'control_id': cid, 'revision': revision, 'previous_revision': previous,
                            'attempt': reservation['sequence'], 'at': now, 'scope': scope, 'result': result}
                rh = immutable(self.directory / 'results', evidence)
                reservation.update(status=status, result_hash=rh); record['status'] = status
                tick['results'].append({'control_id': cid, 'status': status, 'revision': revision, 'result_hash': rh,
                    'assurance_status':result.get('status'),'unresolved_findings':len(result.get('findings',[]))})
                save(state_path, state)
            state['last_tick'] = now
            th = immutable(self.directory / 'ticks', tick); state['history'].append(th); save(state_path, state)
            return {**tick, 'tick_hash': th, 'release_eligible': False}


def changed_sources(previous, current):
    return sorted(key for key in set(previous) | set(current) if previous.get(key) != current.get(key))
