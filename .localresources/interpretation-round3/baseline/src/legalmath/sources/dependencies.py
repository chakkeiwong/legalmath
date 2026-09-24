"""Persistent, reviewable source dependencies, including unresolved definitions."""
from ..canonical import digest
from ..errors import LegalMathError


def record_dependency(db, con, dependency):
    required = {"from_revision_id", "locator", "target_revision_id", "relation", "resolution_status", "resolution_note"}
    if set(dependency) != required or dependency["relation"] not in ("incorporates", "defines", "amends", "replaces", "interprets", "references"):
        raise LegalMathError("E_SCHEMA")
    resolved = dependency["resolution_status"] == "resolved"
    if resolved and dependency["target_revision_id"] is None:
        raise LegalMathError("E_DEPENDENCY")
    ident = db.put(con, "dependency", dependency)
    con.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?,?)", (digest(dependency), dependency["from_revision_id"], dependency["target_revision_id"], ident, int(resolved)))
    return ident


def closure(db, con, revisions):
    seen, unresolved, records = set(), [], []
    todo = list(revisions)
    while todo:
        ident = todo.pop()
        if ident in seen: continue
        seen.add(ident)
        for row in con.execute("SELECT * FROM dependencies WHERE from_revision_id=?", (ident,)):
            dep = db.get(con, row["payload_hash"])
            records.append(dep)
            if not row["resolved"] or dep["target_revision_id"] is None:
                unresolved.append(dep)
            else:
                todo.append(dep["target_revision_id"])
    return {"revision_ids": sorted(seen), "dependencies": records, "unresolved": unresolved}


def affected_bundles(db, con, revision_id):
    affected = []
    for row in con.execute("SELECT hash FROM bundles"):
        bundle = db.get(con, row[0])
        revisions = {s["source_id"] + "/" + s["raw_sha256"] for s in bundle["source_spans"]}
        if revision_id in closure(db, con, revisions)["revision_ids"]:
            affected.append(row[0])
    return sorted(affected)
