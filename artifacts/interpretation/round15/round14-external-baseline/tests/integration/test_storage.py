import sqlite3
import pytest
from legalmath.errors import LegalMathError
from legalmath.storage import Database


def test_atomic_idempotency_restart_and_corruption(db):
    op = lambda con: {"answer": 42}
    first = db.mutate("caller", "k", {"op": 1}, op)
    again = Database(db.root)
    assert again.mutate("caller", "k", {"op": 1}, lambda _: pytest.fail("reexecuted")) == first
    with pytest.raises(LegalMathError, match="Idempotency"):
        again.mutate("caller", "k", {"op": 2}, op)
    assert again.verify()
    with again.connect() as con:
        h = con.execute("SELECT hash FROM records LIMIT 1").fetchone()[0]
    again.blobs.path(h).write_bytes(b"corrupted")
    with pytest.raises(LegalMathError):
        again.verify()


def test_transaction_failure_leaves_no_references(db):
    def fail(con):
        db.put(con, "test", {"orphan": True})
        raise ValueError("interrupted")
    with pytest.raises(ValueError):
        db.mutate("caller", "bad", {}, fail)
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM records").fetchone()[0] == 0
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO streams VALUES('s','missing',1)")
    assert db.verify()
