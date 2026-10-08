"""Durable, incrementally executable fidelity batches.

The old whole-matrix preflight stopped before useful small batches.  This ledger
keeps the exact universe, completed responses and pending pairs.  A failed batch
may be split, but no pair can disappear or be counted twice.
"""
from pathlib import Path
from ...canonical import canonical, digest, loads
from ...errors import LegalMathError


class FidelityBatches:
    def __init__(self, path, pairs, *, batch_size=12, max_pairs=4096):
        if type(batch_size) is not int or not 1 <= batch_size <= 64:
            raise LegalMathError('E_RESOURCE_LIMIT')
        expected = [tuple(p) for p in pairs]
        if len(expected) != len(set(expected)) or len(expected) > max_pairs:
            raise LegalMathError('E_REFERENCE')
        self.path = Path(path)
        self.expected = expected
        self.batch_size = batch_size
        self.max_pairs = max_pairs
        self.state = self._load()

    def _load(self):
        if not self.path.exists():
            value = {'version': 'fidelity-batches.v1', 'expected': [list(p) for p in self.expected],
                     'batch_size': self.batch_size, 'completed': {}, 'failed': [], 'release_eligible': False}
            self._save(value)
            return value
        value = loads(self.path.read_bytes())
        if value.get('expected') != [list(p) for p in self.expected] or value.get('batch_size') != self.batch_size:
            raise LegalMathError('E_STALE_REVIEW')
        complete = [tuple(p) for rows in value['completed'].values() for p in rows]
        if len(complete) != len(set(complete)) or not set(complete) <= set(self.expected):
            raise LegalMathError('E_INTEGRITY')
        return value

    def _save(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(canonical(value))

    @property
    def completed(self):
        return {tuple(p) for rows in self.state['completed'].values() for p in rows}

    @property
    def pending(self):
        return [p for p in self.expected if p not in self.completed]

    def batches(self):
        pending = self.pending
        return [pending[i:i + self.batch_size] for i in range(0, len(pending), self.batch_size)]

    def record(self, batch_id, pairs, *, status='COMPLETED'):
        pairs = [tuple(p) for p in pairs]
        if not pairs or len(pairs) > self.batch_size or len(set(pairs)) != len(pairs):
            raise LegalMathError('E_SCHEMA')
        if not set(pairs) <= set(self.pending):
            raise LegalMathError('E_REFERENCE', details='Batch repeats or invents a fidelity pair')
        if status not in ('COMPLETED', 'FAILED'):
            raise LegalMathError('E_SCHEMA')
        if status == 'COMPLETED':
            if str(batch_id) in self.state['completed']:
                raise LegalMathError('E_DUPLICATE_ID', details='A batch ID cannot replace completed pairs')
            self.state['completed'][str(batch_id)] = [list(p) for p in pairs]
        else:
            self.state['failed'].append({'batch_id': str(batch_id), 'pairs': [list(p) for p in pairs]})
        self._save(self.state)

    def split(self, pairs):
        pairs = [tuple(p) for p in pairs]
        if not pairs or not set(pairs) <= set(self.pending):
            raise LegalMathError('E_REFERENCE')
        if len(pairs) == 1:
            return [pairs]
        midpoint = len(pairs) // 2
        return [pairs[:midpoint], pairs[midpoint:]]

    def report(self):
        return {'expected_pairs': len(self.expected), 'completed_pairs': len(self.completed),
                'pending_pairs': len(self.pending), 'failed_batches': len(self.state['failed']),
                'status': 'COMPLETE' if not self.pending else 'INCOMPLETE',
                'release_eligible': False, 'ledger_hash': digest(self.state)}
