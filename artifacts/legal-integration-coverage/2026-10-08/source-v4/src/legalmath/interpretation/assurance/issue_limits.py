"""Nonrefundable per-source-unit spending independent of work partitions."""
import fcntl
from pathlib import Path
import time

from ...canonical import digest, loads
from ...errors import LegalMathError
from .diversity import save


class IssueLimits:
    def __init__(self, path, binding, *, maximum_attempts=3, deadline_seconds=86400, inherited=None):
        if (type(maximum_attempts) is not int or not 1 <= maximum_attempts <= 6 or
                type(deadline_seconds) is not int or not 1 <= deadline_seconds <= 86400):
            raise LegalMathError('E_RESOURCE_LIMIT')
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.binding = {'inputs': binding, 'maximum_attempts': maximum_attempts,
                        'deadline_seconds': deadline_seconds, 'inherited': inherited or {}}
        for item in self.binding['inherited'].values():
            if (set(item) != {'spent', 'started_ms', 'evidence_hash'} or type(item['spent']) is not int or
                    item['spent'] < 0 or type(item['started_ms']) is not int or item['started_ms'] < 0 or
                    not isinstance(item['evidence_hash'], str) or len(item['evidence_hash']) != 64):
                raise LegalMathError('E_SCHEMA')

    def _load(self):
        if not self.path.exists(): return {'binding': self.binding, 'reservations': []}
        record = loads(self.path.read_bytes()); value = record['value']
        if record['sha256'] != digest(value) or value['binding'] != self.binding:
            raise LegalMathError('E_INTEGRITY', details='Issue history or limits changed')
        return value

    def report(self):
        value = self._load(); issues = {k: {a: v[a] for a in ('spent', 'started_ms')}
                                      for k, v in self.binding['inherited'].items()}
        for reservation in value['reservations']:
            for key in reservation['issues']:
                row = issues.setdefault(key, {'spent': 0, 'started_ms': reservation['at_ms']})
                row['spent'] += 1; row['started_ms'] = min(row['started_ms'], reservation['at_ms'])
        return issues

    def reserve(self, issues, request_hash):
        if (not issues or any(not isinstance(i, str) for i in issues) or len(set(issues)) != len(issues)):
            raise LegalMathError('E_REFERENCE')
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            value = self._load(); rows = self.report(); now = time.time_ns() // 1000000
            for key in issues:
                row = rows.get(key, {'spent': 0, 'started_ms': now})
                if (row['spent'] >= self.binding['maximum_attempts'] or
                        now - row['started_ms'] >= 1000 * self.binding['deadline_seconds']):
                    raise LegalMathError('E_RESOURCE_LIMIT', details={'issue': key, **row,
                        'reason': 'Original unit issue attempt/deadline limit; no refund on repartition'})
            reservation = {'issues': sorted(issues), 'request_hash': request_hash, 'at_ms': now}
            value['reservations'].append(reservation)
            save(self.path, {'value': value, 'sha256': digest(value)})
            return {'reservation': len(value['reservations']), 'sha256': digest(reservation)}
