"""Native package host with persistent reviews and a distinct authenticated adapter.

String callers are reserved for the trusted embedding application. Public callers
use NativeAuth; tokens resolve to named people, never to extra reviewer identities.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import time
from ...canonical import canonical, digest, loads
from .contracts import fail
from .runtime import evaluate, verify_build, verify_cases, verify_result
from .package import prepare as prepare_package, verify as verify_package


@dataclass(frozen=True)
class Principal:
    name: str
    credential: str


class NativeHost:
    def __init__(self, path, identities, jdk):
        self.path = Path(path)
        self.identities = identities  # trusted, named identity registry
        self.jdk = jdk
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS releases(hash TEXT PRIMARY KEY, directory TEXT NOT NULL, verification BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS active(slot INTEGER PRIMARY KEY CHECK(slot=1), release TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, revision TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, release TEXT NOT NULL, snapshot BLOB NOT NULL, result BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS release_state(release TEXT PRIMARY KEY, package_hash TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, reason TEXT);
                CREATE TABLE IF NOT EXISTS package_approvals(release TEXT, caller TEXT, role TEXT, review_hash TEXT, credential TEXT, expires_ns TEXT, PRIMARY KEY(release,role));
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, release TEXT, actor TEXT NOT NULL, request_id TEXT, details BLOB NOT NULL, created_ns TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS credentials(token_hash TEXT PRIMARY KEY, caller TEXT NOT NULL, roles BLOB NOT NULL, expires_ns TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def require(self, caller, role, db=None):
        if db is None:
            with self.connect() as connection:
                return self.require(caller, role, connection)
        name = caller.name if isinstance(caller, Principal) else caller
        if role not in self.identities.get(name, []):
            fail('E_AUTHORITY')
        if isinstance(caller, Principal):
            row = db.execute('SELECT caller,roles,expires_ns,revoked FROM credentials WHERE token_hash=?', (caller.credential,)).fetchone()
            if row is None or row[0] != name or row[3] or int(row[2]) <= time.time_ns() or role not in loads(row[1]):
                fail('E_AUTHORITY', 'Expired, revoked or changed credential')
        return name

    def audit(self, db, event, caller, *, release=None, request_id=None, details=None):
        actor = caller.name if isinstance(caller, Principal) else caller
        db.execute('INSERT INTO audit(event,release,actor,request_id,details,created_ns) VALUES(?,?,?,?,?,?)',
                   (event, release, actor, request_id, canonical(details or {}), str(time.time_ns())))

    def _package(self, db, release, *, active_review=False):
        row = db.execute('SELECT directory FROM releases WHERE hash=?', (release,)).fetchone()
        if row is None: fail('E_NOT_FOUND')
        review = verify_package(row[0], expected_hash=release)
        if active_review:
            state = db.execute('SELECT revoked FROM release_state WHERE release=?', (release,)).fetchone()
            if state is None or state[0]: fail('E_RELEASE_BLOCKED', 'Revoked or legacy release requires new staging')
            approvals = db.execute('SELECT caller,role,review_hash,credential,expires_ns FROM package_approvals WHERE release=?', (release,)).fetchall()
            if {a[1] for a in approvals} != {'engineering','legal'} or len({a[0] for a in approvals}) != 2:
                fail('E_RELEASE_BLOCKED', 'Two distinct named reviewers are required')
            for name,role,review_hash,credential,expires in approvals:
                if review_hash != digest(review) or (expires is not None and int(expires) <= time.time_ns()):
                    fail('E_STALE_REVIEW', 'Review expired or package changed')
                self.require(Principal(name,credential) if credential else name, role, db)
        return row[0], review

    def stage(self, caller, directory, cases, *, compiler, sources=()):
        self.require(caller, 'engineering')
        _, candidate, _ = verify_build(directory)
        if candidate['unresolved']: fail('E_RELEASE_BLOCKED', 'Unresolved source reading')
        report = verify_cases(directory, cases, self.jdk, compiler=compiler)
        store = self.path.parent / 'native-packages';store.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.stage-',dir=store) as temporary:
            staging = Path(temporary)/'package'
            key = prepare_package(directory, staging, cases, report, sources=sources)
            installed = store/key
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                self.require(caller,'engineering',db)
                if installed.exists(): verify_package(installed, expected_hash=key)
                else:
                    staging.rename(installed)
                    for p in installed.rglob('*'):
                        if p.is_file(): p.chmod(0o444)
                    # Parent remains writable for atomic installation of new packages.
                    for p in sorted(installed.rglob('*'), reverse=True):
                        if p.is_dir(): p.chmod(0o555)
                    installed.chmod(0o555)
                db.execute('INSERT OR IGNORE INTO releases VALUES(?,?,?)', (key,str(installed),canonical(report)))
                db.execute('INSERT OR IGNORE INTO release_state VALUES(?,?,0,NULL)', (key,key))
                self.audit(db,'stage',caller,release=key,details={'review_hash':digest(loads((installed/'review.json').read_bytes()))})
        return key

    def review(self, caller, release, role):
        with self.connect() as db:
            self.require(caller,role,db)
            _, review = self._package(db,release)
            return review

    def stage_package(self, caller, directory, *, expected_hash, compiler):
        """Re-execute an imported package's retained cases before local approval."""
        self.require(caller,'engineering')
        review=verify_package(directory,expected_hash=expected_hash)
        directory=Path(directory)
        return self.stage(caller,directory,loads((directory/'cases.json').read_bytes()),compiler=compiler,
                          sources=[(directory/'sources'/(sha+'.bin')).read_bytes() for sha in review['source_blobs']])

    def approve(self, caller, release, role, *, expected_review=None, expires_ns=None):
        if role not in ('engineering','legal'): fail('E_AUTHORITY')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            name = self.require(caller,role,db)
            _, review = self._package(db,release)
            state = db.execute('SELECT revoked FROM release_state WHERE release=?',(release,)).fetchone()
            if state is None or state[0]: fail('E_RELEASE_BLOCKED')
            if expected_review is not None and expected_review != digest(review): fail('E_STALE_REVIEW')
            if isinstance(caller,Principal) and expected_review is None: fail('E_STALE_REVIEW','Authenticated review requires the displayed commitment')
            if expires_ns is not None and (type(expires_ns) is not str or not expires_ns.isdigit() or int(expires_ns)<=time.time_ns()): fail('E_SCHEMA')
            credential=caller.credential if isinstance(caller,Principal) else None
            db.execute('INSERT OR REPLACE INTO package_approvals VALUES(?,?,?,?,?,?)', (release,name,role,digest(review),credential,expires_ns))
            self.audit(db,'approve',caller,release=release,details={'role':role,'review_hash':digest(review),'expires_ns':expires_ns})

    def activate(self, caller, release, *, expected_active, rollback=False):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require(caller,'engineering',db)
            current=db.execute('SELECT release FROM active WHERE slot=1').fetchone()
            if (current[0] if current else None) != expected_active: fail('E_STALE_REVIEW')
            self._package(db,release,active_review=True)
            if rollback and db.execute("SELECT 1 FROM audit WHERE event IN ('activate','rollback') AND release=?",(release,)).fetchone() is None:
                fail('E_RELEASE_BLOCKED','Rollback requires a previously active package')
            db.execute('INSERT OR REPLACE INTO active VALUES(1,?)',(release,))
            self.audit(db,'rollback' if rollback else 'activate',caller,release=release,details={'previous':expected_active})

    def rollback(self, caller, release, *, expected_active):
        return self.activate(caller,release,expected_active=expected_active,rollback=True)

    def revoke(self, caller, release, reason):
        if type(reason) is not str or not reason.strip(): fail('E_SCHEMA')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.require(caller,'legal',db)
            self._package(db,release)
            db.execute('UPDATE release_state SET revoked=1,reason=? WHERE release=?',(reason,release))
            self.audit(db,'revoke',caller,release=release,details={'reason':reason})

    def withdraw(self, caller, release, role):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');name=self.require(caller,role,db)
            db.execute('DELETE FROM package_approvals WHERE release=? AND role=? AND caller=?',(release,role,name))
            self.audit(db,'withdraw_review',caller,release=release,details={'role':role})

    def set_revision(self, caller, subject, revision, *, expected):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.require(caller,'operations',db)
            row=db.execute('SELECT revision FROM subjects WHERE id=?',(subject,)).fetchone()
            if (row[0] if row else None) != expected: fail('E_STALE_REVIEW')
            db.execute('INSERT OR REPLACE INTO subjects VALUES(?,?)',(subject,revision))
            self.audit(db,'revision',caller,details={'subject':subject,'revision':revision,'previous':expected})

    def _receipt(self, db, request_id, snapshot=None, expected_release=None):
        old=db.execute('SELECT release,snapshot,result FROM receipts WHERE id=?',(request_id,)).fetchone()
        if old is None:return None
        if snapshot is not None and (old[0]!=expected_release or loads(old[1])!=snapshot):fail('E_IDEMPOTENCY')
        directory,_=self._package(db,old[0])
        verify_result(directory,loads(old[1]),loads(old[2]),self.jdk)
        return loads(old[2])

    def _current(self, db, release, snapshot):
        current=db.execute('SELECT release FROM active WHERE slot=1').fetchone()
        revision=db.execute('SELECT revision FROM subjects WHERE id=?',(snapshot['subject_id'],)).fetchone()
        if current is None or current[0]!=release or revision is None or revision[0]!=snapshot['revision']:fail('E_STALE_REVIEW')
        return self._package(db,release,active_review=True)

    def transact(self, caller, request_id, snapshot, *, expected_release):
        with self.connect() as db:
            self.require(caller,'operations',db)
            old=self._receipt(db,request_id,snapshot,expected_release)
            if old is not None:return old
            directory,review=self._current(db,expected_release,snapshot)
        result=evaluate(directory,snapshot,self.jdk)
        if result['build_hash']!=review['build_hash']:fail('E_INTEGRITY')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require(caller,'operations',db)
            self._current(db,expected_release,snapshot)
            old=self._receipt(db,request_id,snapshot,expected_release)
            if old is not None:return old
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(request_id,expected_release,canonical(snapshot),canonical(result)))
            self.audit(db,'transact',caller,release=expected_release,request_id=request_id,details={'result_hash':result['result_hash']})
        return result

    def replay(self, caller, request_id):
        with self.connect() as db:
            self.require(caller,'operations',db)
            result=self._receipt(db,request_id)
            if result is None:fail('E_NOT_FOUND')
            return result


class NativeAuth:
    """Bearer adapter; identity registry and TLS are supplied by the institution."""
    def __init__(self, host):self.host=host

    @staticmethod
    def _hash(token):
        if type(token) is not str or not 32<=len(token)<=4096:fail('E_AUTHORITY')
        return hashlib.sha256(token.encode()).hexdigest()

    def provision(self, admin, subject, token, roles, *, expires_ns):
        with self.host.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.host.require(admin,'admin',db)
            if type(roles) is not list or not roles or not set(roles)<=set(self.host.identities.get(subject,[])):fail('E_AUTHORITY')
            if type(expires_ns) is not str or not expires_ns.isdigit() or int(expires_ns)<=time.time_ns():fail('E_SCHEMA')
            key=self._hash(token)
            if db.execute('SELECT 1 FROM credentials WHERE token_hash=?',(key,)).fetchone():fail('E_IDEMPOTENCY','Credentials cannot be rebound or revived')
            db.execute('INSERT INTO credentials VALUES(?,?,?,?,0)',(key,subject,canonical(sorted(set(roles))),expires_ns))
            self.host.audit(db,'credential_provision',admin,details={'subject':subject,'roles':roles,'expires_ns':expires_ns})

    def revoke(self, admin, token):
        with self.host.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.host.require(admin,'admin',db)
            key=self._hash(token)
            row=db.execute('SELECT caller FROM credentials WHERE token_hash=?',(key,)).fetchone()
            if row is None:fail('E_NOT_FOUND')
            db.execute('UPDATE credentials SET revoked=1 WHERE token_hash=?',(key,))
            self.host.audit(db,'credential_revoke',admin,details={'subject':row[0]})

    def principal(self, token):
        key=self._hash(token)
        with self.host.connect() as db:row=db.execute('SELECT caller FROM credentials WHERE token_hash=?',(key,)).fetchone()
        if row is None:fail('E_AUTHORITY')
        return Principal(row[0],key)

    def transact(self, token, *args, **kwargs):return self.host.transact(self.principal(token),*args,**kwargs)
    def approve(self, token, *args, **kwargs):return self.host.approve(self.principal(token),*args,**kwargs)
    def activate(self, token, *args, **kwargs):return self.host.activate(self.principal(token),*args,**kwargs)
    def replay(self, token, *args, **kwargs):return self.host.replay(self.principal(token),*args,**kwargs)
    def review(self, token, *args, **kwargs):return self.host.review(self.principal(token),*args,**kwargs)
    def withdraw(self, token, *args, **kwargs):return self.host.withdraw(self.principal(token),*args,**kwargs)
    def rollback(self, token, *args, **kwargs):return self.host.rollback(self.principal(token),*args,**kwargs)
    def stage_package(self, token, *args, **kwargs):return self.host.stage_package(self.principal(token),*args,**kwargs)
    def revoke_release(self, token, *args, **kwargs):return self.host.revoke(self.principal(token),*args,**kwargs)
    def set_revision(self, token, *args, **kwargs):return self.host.set_revision(self.principal(token),*args,**kwargs)
