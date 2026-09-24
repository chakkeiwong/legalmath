"""Portable, integrity-checked local history. Login tokens are never exported."""
from pathlib import Path
import zipfile

from ..canonical import canonical, digest, loads, raw_digest
from ..errors import LegalMathError
from .database import Database

TABLES = ("records", "identities", "bundles", "reviews", "issues", "sources", "derivatives", "dependencies", "coverage", "facts", "supersession", "applicability", "builds", "verifications", "release_manifests", "releases", "evaluations", "streams", "events", "replays", "jobs", "idempotency", "audit")
LEGACY_TABLES = TABLES
TABLES += ('interpretation_runs', 'interpretation_records', 'interpretation_history', 'interpretation_bindings', 'interpretation_sources', 'interpretation_outbox', 'interpretation_workers')


def export_history(db, path):
    db.verify()
    with db.transaction() as con:
        tables = {name: [dict(r) for r in con.execute("SELECT * FROM " + name)] for name in TABLES}
        for identity in tables["identities"]:
            identity["token_hash"] = raw_digest(("IMPORTED_DISABLED:" + identity["id"]).encode())
        files = {"history.json": canonical({"profile": "LOCAL_SYNTHETIC_HISTORY_0.1", "tables": tables})}
        for prefix in sorted(db.blobs.root.iterdir()):
            if prefix.is_dir():
                for blob in sorted(prefix.iterdir()):
                    ident = prefix.name + blob.name
                    if len(ident) == 64 and not blob.name.startswith("."):
                        files["blobs/" + ident] = db.blobs.get(ident)
    manifest = {"files": {name: raw_digest(data) for name, data in sorted(files.items())}, "authority": "LOCAL_SYNTHETIC", "tokens_exported": False}
    files["archive-manifest.json"] = canonical(manifest)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    return {"archive_hash": raw_digest(path.read_bytes()), "manifest_hash": digest(manifest)}


def import_history(path, destination):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise LegalMathError("E_INTEGRITY")
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > 200 * 1024 * 1024 or len(z.namelist()) != len(set(z.namelist())):
            raise LegalMathError("E_RESOURCE_LIMIT")
        manifest = loads(z.read("archive-manifest.json"))
        if set(z.namelist()) != set(manifest["files"]) | {"archive-manifest.json"}:
            raise LegalMathError("E_INTEGRITY")
        data = {}
        for name, expected in manifest["files"].items():
            if name != "history.json" and not (name.startswith("blobs/") and len(name) == 70 and all(c in "0123456789abcdef" for c in name[6:])):
                raise LegalMathError("E_SCHEMA")
            payload = z.read(name)
            if raw_digest(payload) != expected:
                raise LegalMathError("E_HASH_MISMATCH")
            data[name] = payload
    history = loads(data["history.json"])
    if history["profile"] != "LOCAL_SYNTHETIC_HISTORY_0.1" or set(history["tables"]) not in (set(TABLES), set(LEGACY_TABLES)):
        raise LegalMathError("E_SCHEMA")
    db = Database(destination)
    for name, payload in data.items():
        if name.startswith("blobs/") and db.blobs.put(payload) != name[6:]:
            raise LegalMathError("E_HASH_MISMATCH")
    with db.transaction() as con:
        con.execute("PRAGMA defer_foreign_keys=ON")
        for table in TABLES:
            columns = [r[1] for r in con.execute("PRAGMA table_info(" + table + ")")]
            for row in history["tables"].get(table, []):
                if set(row) != set(columns):
                    raise LegalMathError("E_SCHEMA")
                con.execute("INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in columns) + ")", tuple(row[k] for k in columns))
    db.verify()
    return db
