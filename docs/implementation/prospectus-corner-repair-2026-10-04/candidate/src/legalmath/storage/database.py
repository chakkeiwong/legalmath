"""One-writer SQLite persistence with atomic idempotency and audit."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from ..canonical import canonical, digest, loads
from ..errors import LegalMathError
from .blobs import BlobStore


class Database:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs = BlobStore(self.root / "blobs")
        self.path = self.root / "legalmath.sqlite3"
        with self.connect() as con:
            version = con.execute("PRAGMA user_version").fetchone()[0]
            for migration in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                number = int(migration.stem)
                if number > version:
                    con.executescript("BEGIN IMMEDIATE;\n" + migration.read_text() + f"\nPRAGMA user_version={number};\nCOMMIT;")

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def transaction(self):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    def put(self, con, kind, value):
        ident = self.blobs.put(canonical(value))
        old = con.execute("SELECT kind FROM records WHERE hash=?", (ident,)).fetchone()
        if old and old[0] != kind:
            # Identical JSON may be referenced in several contexts; its original
            # storage kind is descriptive, never a grant of authority.
            return ident
        con.execute("INSERT OR IGNORE INTO records VALUES(?,?,?)", (ident, kind, ident))
        return ident

    def get(self, con, ident):
        row = con.execute("SELECT blob_hash FROM records WHERE hash=?", (ident,)).fetchone()
        if not row:
            raise LegalMathError("E_NOT_FOUND")
        return loads(self.blobs.get(row[0]))

    def audit(self, con, payload):
        previous = con.execute("SELECT hash FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        prev = previous[0] if previous else None
        obj = {"previous_hash": prev, "payload": payload}
        ident = self.put(con, "audit", obj)
        con.execute("INSERT INTO audit(previous_hash,hash,payload_hash) VALUES(?,?,?)", (prev, ident, ident))

    def mutate(self, caller, key, request, operation):
        if not key or len(key) > 200:
            raise LegalMathError("E_SCHEMA")
        request_hash = digest(request)
        with self.transaction() as con:
            old = con.execute("SELECT request_hash,response_hash FROM idempotency WHERE caller=? AND key=?", (caller, key)).fetchone()
            if old:
                if old[0] != request_hash:
                    raise LegalMathError("E_IDEMPOTENCY")
                return self.get(con, old[1])
            result = operation(con)
            ident = self.put(con, "response", result)
            self.audit(con, {"caller": caller, "request_hash": request_hash, "response_hash": ident})
            con.execute("INSERT INTO idempotency VALUES(?,?,?,?)", (caller, key, request_hash, ident))
            return result

    def verify(self):
        with self.connect() as con:
            if con.execute("PRAGMA foreign_key_check").fetchall():
                raise LegalMathError("E_INTEGRITY")
            for row in con.execute("SELECT hash,blob_hash,kind FROM records"):
                if row[0] != row[1]:
                    raise LegalMathError("E_INTEGRITY")
                payload = loads(self.blobs.get(row[1]))
                fields = {"source": ("raw_sha256",), "derivative": ("raw_sha256", "text_sha256"), "build": ("jar_sha256",), "discovery_page": ("raw_sha256",)}.get(row[2], ())
                for field in fields:
                    self.blobs.get(payload[field])
            prev = None
            for row in con.execute("SELECT * FROM audit ORDER BY sequence"):
                payload = self.get(con, row["payload_hash"])
                if payload["previous_hash"] != prev or row["previous_hash"] != prev or digest(payload) != row["hash"]:
                    raise LegalMathError("E_INTEGRITY")
                prev = row["hash"]
        return True
