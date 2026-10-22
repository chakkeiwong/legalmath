"""Atomic budgets for explicit supervised Popen calls, not tool-internal forks."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def checked(path):
    value = json.loads(Path(path).read_text())
    expected = value.pop('sha256')
    if (checksum(value) != expected or value.get('version') != 'supervised-process-budget.v1'
            or type(value.get('limit')) is not int or value['limit'] <= 0
            or type(value.get('historical_lower_bound')) is not int or value['historical_lower_bound'] < 0
            or not isinstance(value.get('reservations'), list)
            or len(value['reservations']) > value['limit']):
        raise ValueError('Invalid supervised process ledger')
    for index, row in enumerate(value['reservations']):
        if (row['index'] != index or row['state'] not in {'RESERVED', 'STARTED', 'SPAWN_FAILED'}
                or row['argv_sha256'] != checksum(row['argv'])):
            raise ValueError('Invalid process reservation')
    return value


def save(path, value, *, exclusive=False):
    path = Path(path)
    data = json.dumps({**value, 'sha256': checksum(value)}, indent=2) + '\n'
    if exclusive:
        with path.open('x') as stream: stream.write(data)
        return
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def create(path, limit, historical_lower_bound, scope):
    if (type(limit) is not int or limit <= 0 or type(historical_lower_bound) is not int
            or historical_lower_bound < 0 or not isinstance(scope, str) or not scope):
        raise ValueError('Invalid process budget')
    save(path, {'version': 'supervised-process-budget.v1', 'limit': limit,
                'historical_lower_bound': historical_lower_bound, 'scope': scope,
                'reservations': []}, exclusive=True)


@contextmanager
def locked(path):
    with Path(str(path) + '.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def reserve(path, argv):
    if (not isinstance(argv, (list, tuple)) or not argv
            or any(not isinstance(arg, (str, os.PathLike)) for arg in argv)):
        raise ValueError('Supervised processes require explicit argv, not shell code')
    argv = [os.fspath(arg) for arg in argv]
    with locked(path):
        value = checked(path)
        index = len(value['reservations'])
        if index >= value['limit']:
            raise ValueError('Supervised process budget exhausted before launch')
        value['reservations'].append({'index': index, 'state': 'RESERVED', 'argv': argv,
            'argv_sha256': checksum(argv), 'reserved_at': datetime.now(timezone.utc).isoformat()})
        save(path, value)
    return index


def transition(path, index, *, pid=None, error=None):
    with locked(path):
        value = checked(path)
        row = value['reservations'][index]
        if row['state'] != 'RESERVED':
            raise ValueError('Process reservation already used')
        row.update(state='SPAWN_FAILED' if error else 'STARTED', pid=pid, error=error)
        save(path, value)


@contextmanager
def observe(path):
    """Single-threaded driver context; nested tools must opt in to this ledger."""
    path = Path(path).resolve(strict=True)
    checked(path)
    original = subprocess.Popen
    def counted(*args, **kwargs):
        if kwargs.get('shell'):
            raise ValueError('Shell subprocesses are not supported by this ledger')
        argv = args[0] if args else kwargs['args']
        index = reserve(path, argv)
        try:
            child = original(*args, **kwargs)
        except BaseException as error:
            transition(path, index, error=type(error).__name__)
            raise
        transition(path, index, pid=child.pid)
        return child
    subprocess.Popen = counted
    try:
        yield
    finally:
        subprocess.Popen = original
