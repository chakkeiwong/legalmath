"""Development host transactions for a distinct native release profile.

Caller identities/roles are supplied by the embedding trusted host. This module
is not an authentication service and does not confer production authorization.
"""
import sqlite3
from pathlib import Path
from ...canonical import canonical, digest, loads
from .contracts import fail
from .runtime import evaluate, verify_build, verify_cases, verify_result


class NativeHost:
    def __init__(self, path, identities, jdk):
        self.path = Path(path)
        self.identities = identities
        self.jdk = jdk
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS releases(hash TEXT PRIMARY KEY, directory TEXT NOT NULL, verification BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals(release TEXT, caller TEXT, role TEXT, PRIMARY KEY(release,role));
                CREATE TABLE IF NOT EXISTS active(slot INTEGER PRIMARY KEY CHECK(slot=1), release TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, revision TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, release TEXT NOT NULL, snapshot BLOB NOT NULL, result BLOB NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def require(self, caller, role):
        if role not in self.identities.get(caller, []):
            fail('E_AUTHORITY')

    def stage(self, caller, directory, cases, *, compiler):
        self.require(caller, 'engineering')
        directory = Path(directory).resolve()
        _, candidate, manifest = verify_build(directory)
        if candidate['unresolved']:
            fail('E_RELEASE_BLOCKED', 'Unresolved source reading')
        report = verify_cases(directory, cases, self.jdk, compiler=compiler)
        key = digest(manifest)
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO releases VALUES(?,?,?)', (key,str(directory),canonical(report)))
        return key

    def approve(self, caller, release, role):
        if role not in ('engineering','legal'):
            fail('E_AUTHORITY')
        self.require(caller, role)
        with self.connect() as db:
            row = db.execute('SELECT directory FROM releases WHERE hash=?',(release,)).fetchone()
            if row is None:
                fail('E_NOT_FOUND')
            verify_build(row[0], expected_hash=release)
            db.execute('INSERT OR REPLACE INTO approvals VALUES(?,?,?)',(release,caller,role))

    def activate(self, caller, release, *, expected_active):
        self.require(caller, 'engineering')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT release FROM active WHERE slot=1').fetchone()
            if (current[0] if current else None) != expected_active:
                fail('E_STALE_REVIEW')
            row = db.execute('SELECT directory FROM releases WHERE hash=?',(release,)).fetchone()
            if row is None:
                fail('E_NOT_FOUND')
            verify_build(row[0], expected_hash=release)
            approvals = dict(db.execute('SELECT role,caller FROM approvals WHERE release=?',(release,)))
            if set(approvals) != {'engineering','legal'} or len(set(approvals.values())) != 2:
                fail('E_RELEASE_BLOCKED', 'Two distinct trusted host reviewers are required')
            db.execute('INSERT OR REPLACE INTO active VALUES(1,?)',(release,))

    def set_revision(self, caller, subject, revision, *, expected):
        self.require(caller, 'operations')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision FROM subjects WHERE id=?',(subject,)).fetchone()
            if (row[0] if row else None) != expected:
                fail('E_STALE_REVIEW')
            db.execute('INSERT OR REPLACE INTO subjects VALUES(?,?)',(subject,revision))

    def transact(self, caller, request_id, snapshot, *, expected_release):
        self.require(caller, 'operations')
        with self.connect() as db:
            old = db.execute('SELECT release,snapshot,result FROM receipts WHERE id=?',(request_id,)).fetchone()
            if old:
                if old[0] != expected_release or loads(old[1]) != snapshot:
                    fail('E_IDEMPOTENCY')
                return loads(old[2])
            current = db.execute('SELECT release FROM active WHERE slot=1').fetchone()
            row = db.execute('SELECT directory FROM releases WHERE hash=?',(expected_release,)).fetchone()
            revision = db.execute('SELECT revision FROM subjects WHERE id=?',(snapshot['subject_id'],)).fetchone()
        if current is None or current[0] != expected_release or revision is None or revision[0] != snapshot['revision']:
            fail('E_STALE_REVIEW')
        if row is None:
            fail('E_NOT_FOUND')
        verify_build(row[0], expected_hash=expected_release)
        result = evaluate(row[0], snapshot, self.jdk)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT release FROM active WHERE slot=1').fetchone()
            revision = db.execute('SELECT revision FROM subjects WHERE id=?',(snapshot['subject_id'],)).fetchone()
            if current is None or current[0] != expected_release or revision is None or revision[0] != snapshot['revision']:
                fail('E_STALE_REVIEW', 'Host state changed during computation')
            verify_build(row[0], expected_hash=expected_release)
            old = db.execute('SELECT release,snapshot,result FROM receipts WHERE id=?',(request_id,)).fetchone()
            if old:
                if old[0] != expected_release or loads(old[1]) != snapshot:
                    fail('E_IDEMPOTENCY')
                return loads(old[2])
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(request_id,expected_release,canonical(snapshot),canonical(result)))
        return result

    def replay(self, caller, request_id):
        self.require(caller, 'operations')
        with self.connect() as db:
            row = db.execute('SELECT r.release,r.snapshot,r.result,b.directory FROM receipts r JOIN releases b ON r.release=b.hash WHERE r.id=?',(request_id,)).fetchone()
        if row is None:
            fail('E_NOT_FOUND')
        release,snapshot,result,directory = row
        verify_build(directory, expected_hash=release)
        verify_result(directory, loads(snapshot), loads(result), self.jdk)
        return loads(result)
