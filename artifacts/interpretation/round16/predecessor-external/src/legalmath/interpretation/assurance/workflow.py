"""Persistent evidence actions with input invalidation and non-refundable limits.

An executed action is not a legal approval. The journal retains both an action's
technical outcome and its semantic result, including inconclusive results.
"""
from copy import deepcopy
from pathlib import Path
import fcntl
import hashlib
import json
import re
import time

from ...errors import LegalMathError
from ..search.providers import Completion
from .diversity import identity, save


def loads(data):
    def invalid(value):
        raise LegalMathError('E_SCHEMA', details='Nonfinite evidence value')
    return json.loads(data, parse_constant=invalid)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvidenceJournal:
    def __init__(self, directory, binding, *, maximum_actions=200, maximum_per_issue=3,
                 deadline_seconds=7200):
        if (type(maximum_actions) is not int or not 1 <= maximum_actions <= 1000 or
            type(maximum_per_issue) is not int or not 1 <= maximum_per_issue <= 6 or
            type(deadline_seconds) is not int or not 1 <= deadline_seconds <= 86400):
            raise LegalMathError('E_RESOURCE_LIMIT')
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'journal.json'
        self.binding = {'inputs': binding, 'maximum_actions': maximum_actions,
                        'maximum_per_issue': maximum_per_issue, 'deadline_seconds': deadline_seconds}

    def _load(self):
        if not self.path.exists():
            return {'binding': self.binding, 'started_ms': time.time_ns() // 1000000,
                    'actions': [], 'release_eligible': False}
        envelope = loads(self.path.read_bytes())
        value = envelope['value']
        if envelope['sha256'] != identity(value) or value['binding'] != self.binding:
            raise LegalMathError('E_INTEGRITY', details='Evidence journal changed or binding differs')
        if len(value['actions']) > self.binding['maximum_actions']:
            raise LegalMathError('E_INTEGRITY')
        for i, row in enumerate(value['actions']):
            if row['sequence'] != i or row['key'] != identity(row['spec']):
                raise LegalMathError('E_INTEGRITY')
            if row['status'] == 'EXECUTED':
                p = (self.directory / row['result_file']).resolve()
                if not p.is_relative_to(self.directory.resolve()):
                    raise LegalMathError('E_INTEGRITY')
                if not p.is_file() or identity(loads(p.read_bytes())) != row['result_hash']:
                    raise LegalMathError('E_INTEGRITY', details='Action evidence missing or changed')
                for name, expected in row.get('artifacts', {}).items():
                    artifact = (self.directory / name).resolve()
                    if (not artifact.is_relative_to(self.directory.resolve()) or not artifact.is_file()
                            or file_hash(artifact) != expected):
                        raise LegalMathError('E_INTEGRITY', details='Action artifact changed')
            elif row['status'] not in ('RESERVED', 'FAILED', 'INTERRUPTED'):
                raise LegalMathError('E_INTEGRITY')
        return value

    def _save(self, value):
        save(self.path, {'value': value, 'sha256': identity(value)})

    def report(self):
        value = self._load()
        return {**deepcopy(value), 'consumed_actions': len(value['actions']),
                'remaining_actions': self.binding['maximum_actions'] - len(value['actions']),
                'deadline_exhausted': time.time_ns() // 1000000 - value['started_ms'] >=
                    1000 * self.binding['deadline_seconds']}

    def execute(self, stage, inputs, callback, *, dependencies=(), issue=None, retry_if=None):
        if not re.fullmatch(r'[a-z][a-z0-9_.-]{0,100}', stage):
            raise LegalMathError('E_SCHEMA')
        spec = {'stage': stage, 'inputs': inputs, 'dependencies': list(dependencies),
                'issue': issue or stage}
        key = identity(spec)
        with (self.directory / '.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise LegalMathError('E_JOB_STATE', details='Evidence worker already holds the journal')
            state = self._load()
            for row in state['actions']:
                if row['status'] == 'RESERVED':
                    row['status'] = 'INTERRUPTED'
            self._save(state)
            for row in reversed(state['actions']):
                if row['key'] == key and row['status'] == 'EXECUTED':
                    cached = loads((self.directory / row['result_file']).read_bytes())
                    if retry_if is not None and retry_if(cached):
                        # Reinvestigation consumes another reservation. Keep the
                        # earlier incomplete result and all its original files.
                        break
                    return cached, {
                        'sequence': row['sequence'], 'key': key, 'reused': True,
                        'result_hash': row['result_hash']}
            if (len(state['actions']) >= self.binding['maximum_actions'] or
                sum(r['spec']['issue'] == spec['issue'] for r in state['actions']) >=
                    self.binding['maximum_per_issue'] or
                time.time_ns() // 1000000 - state['started_ms'] >=
                    1000 * self.binding['deadline_seconds']):
                raise LegalMathError('E_RESOURCE_LIMIT', details='Persistent action, issue or deadline limit')
            sequence = len(state['actions'])
            row = {'sequence': sequence, 'spec': spec, 'key': key, 'status': 'RESERVED',
                   'started_ms': time.time_ns() // 1000000,
                   'supersedes': [r['sequence'] for r in state['actions']
                                 if r['spec']['stage'] == stage and r['key'] != key]}
            state['actions'].append(row)
            self._save(state)
            work = self.directory / f'action-{sequence:04}'
            work.mkdir(exist_ok=False)
            try:
                result = callback(work)
                path = work / 'result.json'
                save(path, result)
                row.update(status='EXECUTED', result_file=str(path.relative_to(self.directory)),
                           result_hash=identity(result), artifacts={
                               str(p.relative_to(self.directory)): file_hash(p)
                               for p in sorted(work.rglob('*')) if p.is_file() and
                               p.name != '.lock' and not p.name.endswith(('-wal', '-shm'))})
            except BaseException as exc:
                row.update(status='FAILED' if isinstance(exc, Exception) else 'INTERRUPTED',
                           error=getattr(exc, 'code', type(exc).__name__),
                           details=str(getattr(exc, 'details', None) or exc)[:2000])
                self._save(state)
                raise
            row['finished_ms'] = time.time_ns() // 1000000
            self._save(state)
            return result, {'sequence': sequence, 'key': key, 'reused': False,
                            'result_hash': row['result_hash']}


class CachedEvidenceProvider:
    """Replay exact completed proposals; new/failed attempts still use the ledger.

Replayed output is evidence reuse, not another independent model judgment.
"""
    def __init__(self, provider, directory, binding, *, maximum_actions=120,
                 deadline_seconds=14400):
        self.provider = provider
        self.provider_id = provider.provider_id
        self.live = provider.live
        self.routing = getattr(provider, 'routing', provider.provider_id)
        cache_binding = {'case': binding, 'route': self.routing}
        path = Path(directory) / 'journal.json'
        if path.exists():
            envelope = loads(path.read_bytes())
            value = envelope['value']
            if envelope['sha256'] != identity(value):
                raise LegalMathError('E_INTEGRITY', details='Cached evidence journal changed')
            previous = value['binding']['inputs']
            # Existing v1 journals bound orchestration settings globally. Exact
            # requests, schemas and provider settings are already bound per
            # action. Permit only those settings to vary, keeping the original
            # binding, counters and deadline; changed source requests cannot hit
            # an old response. No historical record is rewritten.
            def stable(case):
                return {k: v for k, v in case.items() if k != 'settings'}
            if (previous.get('route') != self.routing or
                    stable(previous.get('case', {})) != stable(binding)):
                raise LegalMathError('E_INTEGRITY', details='Case or provider route changed')
            cache_binding = previous
        self.journal = EvidenceJournal(directory, cache_binding,
            maximum_actions=maximum_actions, deadline_seconds=deadline_seconds)
        self.journal.report()  # Validate history and resource binding before use.

    def complete(self, request, schema, settings):
        inputs = {'request': request, 'schema': schema, 'settings': settings.model_dump()}
        def dispatch(work):
            save(work / 'request.json', request)
            response = self.provider.complete(request, schema, settings)
            return {'value': response.value, 'provenance': response.provenance}
        # Timeout reductions are scheduling limits, not different meanings of a
        # cached answer. Output/input limits and provider route remain bound.
        inputs['settings'].pop('timeout_seconds', None)
        from .transport import transient_service_failure
        for attempt in range(2):
            try:
                value, receipt = self.journal.execute('model', inputs, dispatch,
                    issue='request.' + identity({'request': request, 'schema': schema}))
                break
            except LegalMathError as exc:
                if attempt or not transient_service_failure(exc):
                    raise
        return Completion(value['value'], {**value['provenance'],
            'workflow_receipt': receipt, 'new_live_invocation': not receipt['reused'],
            'evidence_reused': receipt['reused']})
