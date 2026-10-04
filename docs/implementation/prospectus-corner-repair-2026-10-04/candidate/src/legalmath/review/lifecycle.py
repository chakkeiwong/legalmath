"""Exact-hash, synthetic local review. Authority comes from the registry."""
from ..canonical import canonical, digest, raw_digest
from ..domain import interval
from ..errors import LegalMathError
from ..ir.load import schema_errors
from ..ir.typecheck import validate_bundle
from ..sources.intake import resolve_span


class Lifecycle:
    def __init__(self, db):
        self.db = db

    def register(self, identities):
        with self.db.transaction() as con:
            for caller, settings in identities.items():
                roles = canonical(sorted(set(settings["roles"]))).decode()
                token_hash = raw_digest(settings["token"].encode())
                old = con.execute("SELECT roles,token_hash FROM identities WHERE id=?", (caller,)).fetchone()
                if old and (old[0] != roles or old[1] != token_hash):
                    raise LegalMathError("E_AUTHORITY")
                con.execute("INSERT OR IGNORE INTO identities VALUES(?,?,?)", (caller, roles, token_hash))

    def authenticate(self, token):
        with self.db.connect() as con:
            row = con.execute("SELECT id FROM identities WHERE token_hash=?", (raw_digest(token.encode()),)).fetchone()
        if not row:
            raise LegalMathError("E_AUTHORITY")
        return row[0]

    def require(self, con, caller, role=None):
        from ..canonical import loads
        row = con.execute("SELECT roles FROM identities WHERE id=?", (caller,)).fetchone()
        if not row or (role and role not in loads(row[0])):
            raise LegalMathError("E_AUTHORITY")

    def state(self, con, bh, revision=None):
        row = con.execute("SELECT * FROM bundles WHERE hash=?", (bh,)).fetchone()
        if not row:
            raise LegalMathError("E_NOT_FOUND")
        if revision is not None and revision != row["revision"]:
            raise LegalMathError("E_STALE_REVIEW")
        return row

    def create(self, caller, key, bundle, parent=None):
        errors = validate_bundle(bundle)
        if errors:
            raise LegalMathError(errors[0]["code"], errors[0]["pointer"])

        def op(con):
            self.require(con, caller, "author")
            if parent:
                self.state(con, parent)
            ident = self.db.put(con, "bundle", bundle)
            old = con.execute("SELECT * FROM bundles WHERE hash=?", (ident,)).fetchone()
            if old:
                if old["author"] != caller:
                    raise LegalMathError("E_AUTHORITY")
                return {"bundle_hash": ident, "state": old["state"], "revision": old["revision"]}
            con.execute("INSERT INTO bundles VALUES(?,?,?,'DRAFT',1)", (ident, caller, parent))
            for issue_id in sorted({x for i in bundle["interpretations"] for x in i["issue_ids"]}):
                issue = {"id": issue_id, "bundle_hash": ident, "kind": "interpretation", "question": issue_id,
                    "affected_rule_ids": [r["id"] for r in bundle["rules"]], "alternatives": [], "resolution": None,
                    "resolved_by": None, "resolved_at": None, "authority": "LOCAL_SYNTHETIC"}
                ih = self.db.put(con, "issue", issue)
                con.execute("INSERT INTO issues VALUES(?,?,?,0)", (issue_id, ident, ih))
            return {"bundle_hash": ident, "state": "DRAFT", "revision": 1}
        return self.db.mutate(caller, key, {"op": "create_bundle", "bundle": bundle, "parent": parent}, op)

    def resolve_issue(self, caller, key, bundle_hash, issue_id, resolution, at, revision):
        from ..domain import timestamp
        timestamp(at)
        if not resolution:
            raise LegalMathError("E_SCHEMA")

        def op(con):
            self.require(con, caller, "meaning")
            state = self.state(con, bundle_hash, revision)
            if state["state"] not in ("DRAFT", "IN_REVIEW") or state["author"] == caller:
                raise LegalMathError("E_RELEASE_BLOCKED")
            old = con.execute("SELECT payload_hash FROM issues WHERE bundle_hash=? AND id=?", (bundle_hash, issue_id)).fetchone()
            if not old:
                raise LegalMathError("E_NOT_FOUND")
            value = {**self.db.get(con, old[0]), "resolution": resolution, "resolved_by": caller, "resolved_at": at}
            ih = self.db.put(con, "issue", value)
            con.execute("UPDATE issues SET payload_hash=?,resolved=1 WHERE bundle_hash=? AND id=?", (ih, bundle_hash, issue_id))
            con.execute("UPDATE bundles SET revision=revision+1 WHERE hash=?", (bundle_hash,))
            return {"issue_hash": ih, "revision": revision + 1}
        return self.db.mutate(caller, key, {"op": "resolve_issue", "bundle": bundle_hash, "issue": issue_id, "resolution": resolution, "at": at, "revision": revision}, op)

    def assess(self, caller, key, assessment):
        if schema_errors("applicability", assessment):
            raise LegalMathError("E_SCHEMA")
        interval(assessment["valid_from"], assessment["valid_until"])
        if assessment["reviewer_id"] != caller:
            raise LegalMathError("E_AUTHORITY")
        if assessment["conclusion"] == "in_scope" and any(assessment[k].strip().lower() in ("unknown", "unresolved", "tbd") for k in ("legal_entity", "regulated_role", "activity", "product_class", "client_class", "jurisdiction")):
            raise LegalMathError("E_RELEASE_BLOCKED")

        def op(con):
            self.require(con, caller, "meaning")
            row = self.state(con, assessment["bundle_hash"])
            if row["author"] == caller:
                raise LegalMathError("E_AUTHORITY")
            ident = self.db.put(con, "applicability", assessment)
            scope = scope_key(assessment)
            con.execute("INSERT OR IGNORE INTO applicability VALUES(?,?,?,?)", (ident, assessment["bundle_hash"], scope, caller))
            return {"applicability_hash": ident, "scope_key": scope}
        return self.db.mutate(caller, key, {"op": "applicability", "assessment": assessment}, op)

    def record_coverage(self, caller, key, bundle_hash, inventory, revision):
        from .coverage import coverage_report
        def op(con):
            self.require(con, caller, "meaning")
            state = self.state(con, bundle_hash, revision)
            if state["author"] == caller or state["state"] not in ("DRAFT", "IN_REVIEW"):
                raise LegalMathError("E_RELEASE_BLOCKED")
            report = coverage_report(self.db, con, self.db.get(con, bundle_hash), inventory)
            con.execute("DELETE FROM coverage WHERE bundle_hash=?", (bundle_hash,))
            for row in report["provisions"]:
                record = {**row, "bundle_hash": bundle_hash, "reviewer_id": caller, "authority": "LOCAL_SYNTHETIC"}
                ident = self.db.put(con, "coverage", record)
                con.execute("INSERT INTO coverage VALUES(?,?,?)", (bundle_hash, row["span_id"], ident))
            con.execute("DELETE FROM reviews WHERE bundle_hash=?", (bundle_hash,))
            con.execute("UPDATE bundles SET state='DRAFT',revision=revision+1 WHERE hash=?", (bundle_hash,))
            return {"bundle_hash": bundle_hash, "state": "DRAFT", "revision": revision + 1, "provisions": len(report["provisions"])}
        return self.db.mutate(caller, key, {"op": "coverage", "bundle_hash": bundle_hash, "inventory": inventory, "revision": revision}, op)

    def transition(self, caller, key, bundle_hash, decision, revision, comment="", manifest_hash=None):
        def op(con):
            row = self.state(con, bundle_hash, revision)
            self.require(con, caller)
            state = row["state"]
            if decision == "submit":
                if caller != row["author"] or state != "DRAFT":
                    raise LegalMathError("E_RELEASE_BLOCKED")
                self.check_sources(con, bundle_hash)
                target = "IN_REVIEW"
            elif decision == "reject":
                self.require(con, caller, "meaning")
                if state != "IN_REVIEW" or caller == row["author"]:
                    raise LegalMathError("E_RELEASE_BLOCKED")
                target = "DRAFT"
                con.execute("DELETE FROM reviews WHERE bundle_hash=?", (bundle_hash,))
            elif decision in ("approve_meaning", "approve_engineering"):
                role = decision.removeprefix("approve_")
                self.require(con, caller, role)
                if state != "IN_REVIEW" or row["author"] == caller or not manifest_hash:
                    raise LegalMathError("E_RELEASE_BLOCKED")
                if not con.execute("SELECT 1 FROM release_manifests WHERE hash=?", (manifest_hash,)).fetchone():
                    raise LegalMathError("E_RELEASE_BLOCKED")
                manifest = self.db.get(con, manifest_hash)
                if manifest["bundle_hash"] != bundle_hash:
                    raise LegalMathError("E_RELEASE_BLOCKED")
                others = con.execute("SELECT reviewer,role,record_hash FROM reviews WHERE bundle_hash=?", (bundle_hash,)).fetchall()
                if any(r["reviewer"] == caller or r["role"] == role or self.db.get(con, r["record_hash"])["manifest_hash"] != manifest_hash for r in others):
                    raise LegalMathError("E_RELEASE_BLOCKED")
                self.check_open_issues(con, bundle_hash)
                review = {"bundle_hash": bundle_hash, "reviewer": caller, "role": role, "comment": comment, "manifest_hash": manifest_hash, "authority": "LOCAL_SYNTHETIC"}
                rh = self.db.put(con, "review", review)
                con.execute("INSERT INTO reviews VALUES(?,?,?,?)", (bundle_hash, caller, role, rh))
                target = "APPROVED" if others else "IN_REVIEW"
            else:
                raise LegalMathError("E_SCHEMA")
            con.execute("UPDATE bundles SET state=?,revision=revision+1 WHERE hash=?", (target, bundle_hash))
            return {"bundle_hash": bundle_hash, "state": target, "revision": revision + 1}
        return self.db.mutate(caller, key, {"op": "review", "bundle": bundle_hash, "decision": decision, "revision": revision, "comment": comment, "manifest_hash": manifest_hash}, op)

    def check_sources(self, con, bh):
        bundle = self.db.get(con, bh)
        for span in bundle["source_spans"]:
            resolve_span(self.db, con, span)
        from ..sources.dependencies import closure
        revisions = {s["source_id"] + "/" + s["raw_sha256"] for s in bundle["source_spans"]}
        if closure(self.db, con, revisions)["unresolved"]:
            raise LegalMathError("E_DEPENDENCY")
        for revision in revisions:
            row = con.execute("SELECT payload_hash FROM sources WHERE revision_id=?", (revision,)).fetchone()
            if not row or self.db.get(con, row[0])["authority"] not in ("SFC_PUBLIC_SOURCE", "HKMA_PUBLIC_SOURCE", "RETAINED_PUBLIC_SOURCE"):
                raise LegalMathError("E_RELEASE_BLOCKED")

    def check_open_issues(self, con, bh):
        from ..interpretation.review import guard
        guard(self.db, con, bh)
        self.check_sources(con, bh)
        bundle = self.db.get(con, bh)
        rows = con.execute("SELECT span_id,payload_hash FROM coverage WHERE bundle_hash=?", (bh,)).fetchall()
        if not {s["id"] for s in bundle["source_spans"]} <= {row[0] for row in rows}:
            raise LegalMathError("E_RELEASE_BLOCKED")
        for row in rows:
            coverage = self.db.get(con, row[1])
            if coverage.get("bundle_hash") != bh or not coverage.get("reviewer_id"):
                raise LegalMathError("E_RELEASE_BLOCKED")
            self.require(con, coverage["reviewer_id"], "meaning")
        if con.execute("SELECT 1 FROM issues WHERE bundle_hash=? AND resolved=0 LIMIT 1", (bh,)).fetchone():
            raise LegalMathError("E_RELEASE_BLOCKED")


def scope_key(assessment):
    dimensions = {k: assessment[k] for k in ("legal_entity", "regulated_role", "activity", "product_class", "client_class", "jurisdiction")}
    return digest(dimensions)
