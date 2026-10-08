from ..canonical import digest
from ..domain import timestamp
from ..errors import LegalMathError
from ..ir.load import schema_errors


def validate_header(header):
    if schema_errors("stream-header", header):
        raise LegalMathError("E_SCHEMA")
    timestamp(header["inception"])
    if header["profile"] == "achievement" and not header["obligation_id"]:
        raise LegalMathError("E_EVENT_ATTRIBUTION")
    initial = header["initial_snapshot"]
    if initial:
        timestamp(initial["as_of"])
        timestamp(initial["recorded_at"])
        if header["profile"] != "consent" or initial["as_of"] < header["inception"] or initial["as_of"] > initial["recorded_at"]:
            raise LegalMathError("E_TIME")


def validate_events(header, events):
    validate_header(header)
    by_id, sequences = {}, {}
    for e in events:
        if schema_errors("event", e):
            raise LegalMathError("E_SCHEMA")
        timestamp(e["occurred_at"])
        timestamp(e["recorded_at"])
        if e["stream_id"] != header["stream_id"] or any(e[k] != header[k] for k in ("subject", "category", "actor", "action")):
            raise LegalMathError("E_EVENT_ATTRIBUTION")
        if header["profile"] == "achievement" and e["obligation_id"] != header["obligation_id"]:
            raise LegalMathError("E_EVENT_ATTRIBUTION")
        allowed = ("consent.granted", "consent.withdrawn", "transaction.observed") if header["profile"] == "consent" else ("obligation.opened", "obligation.performed", "watermark")
        if e["kind"] not in allowed:
            raise LegalMathError("E_UNSUPPORTED_PROFILE")
        if e["id"] in by_id:
            if digest(e) != digest(by_id[e["id"]]):
                raise LegalMathError("E_EVENT_ID_COLLISION")
            continue
        if e["sequence"] in sequences:
            raise LegalMathError("E_SEQUENCE_COLLISION")
        by_id[e["id"]], sequences[e["sequence"]] = e, e["id"]
        if e["kind"] == "obligation.opened":
            if not {"activation", "deadline", "source_bundle_hash"} <= set(e):
                raise LegalMathError("E_SCHEMA")
            timestamp(e["activation"])
            if e["deadline"] is not None and timestamp(e["deadline"]) <= e["activation"]:
                raise LegalMathError("E_TIME")
        if e["kind"] == "watermark":
            if not {"complete_from", "complete_through"} <= set(e):
                raise LegalMathError("E_SCHEMA")
            timestamp(e["complete_from"])
            timestamp(e["complete_through"])
    return list(by_id.values())


def create_stream(db, con, header, reviewer=None):
    validate_header(header)
    if header["initial_snapshot"] is not None:
        from ..review.lifecycle import Lifecycle
        if reviewer != header["initial_snapshot"]["reviewer_id"]:
            raise LegalMathError("E_AUTHORITY")
        Lifecycle(db).require(con, reviewer, "meaning")
    ident = db.put(con, "stream_header", header)
    existing = con.execute("SELECT header_hash,revision FROM streams WHERE id=?", (header["stream_id"],)).fetchone()
    if existing:
        if existing[0] != ident:
            raise LegalMathError("E_EVENT_ID_COLLISION")
        return {"stream_id": header["stream_id"], "revision": existing[1]}
    con.execute("INSERT INTO streams VALUES(?,?,1)", (header["stream_id"], ident))
    return {"stream_id": header["stream_id"], "revision": 1}


def append_event(db, con, stream_id, event, expected_revision):
    row = con.execute("SELECT * FROM streams WHERE id=?", (stream_id,)).fetchone()
    if not row:
        raise LegalMathError("E_NOT_FOUND")
    header = db.get(con, row["header_hash"])
    validate_events(header, [event])
    if event["kind"] == "obligation.opened" and not con.execute("SELECT 1 FROM bundles WHERE hash=?", (event["source_bundle_hash"],)).fetchone():
        raise LegalMathError("E_REFERENCE")
    ident = digest(event)
    old = con.execute("SELECT payload_hash FROM events WHERE id=?", (event["id"],)).fetchone()
    if old:
        if old[0] != ident:
            raise LegalMathError("E_EVENT_ID_COLLISION")
        return {"event_hash": ident, "revision": row["revision"]}
    if row["revision"] != expected_revision:
        raise LegalMathError("E_STALE_REVIEW")
    if con.execute("SELECT 1 FROM events WHERE stream_id=? AND sequence=?", (stream_id, event["sequence"])).fetchone():
        raise LegalMathError("E_SEQUENCE_COLLISION")
    db.put(con, "event", event)
    con.execute("INSERT INTO events VALUES(?,?,?,?)", (event["id"], stream_id, event["sequence"], ident))
    con.execute("UPDATE streams SET revision=revision+1 WHERE id=?", (stream_id,))
    return {"event_hash": ident, "revision": row["revision"] + 1}
