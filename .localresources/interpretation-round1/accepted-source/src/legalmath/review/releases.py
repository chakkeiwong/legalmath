"""Candidate build, exact approved release, and historical replay selection."""
from pathlib import Path
import json

from ..canonical import canonical, digest, raw_digest, loads
from ..domain import eligible, interval, timestamp
from ..errors import LegalMathError
from ..ir.load import schema_errors
from ..java.manifest import build_candidate, verify_candidate
from .lifecycle import Lifecycle, scope_key


class Releases:
    def __init__(self, db):
        self.db = db
        self.lifecycle = Lifecycle(db)

    def build(self, caller, key, bundle_hash, output, jdk, cases, event_cases=None):
        with self.db.connect() as con:
            self.lifecycle.require(con, caller, "engineering")
            self.lifecycle.state(con, bundle_hash)
            bundle = self.db.get(con, bundle_hash)
        build = build_candidate(bundle, output, jdk)
        report = verify_candidate(build, cases, jdk, event_cases)
        results = loads((Path(output) / "verification-results.json").read_bytes())

        def op(con):
            self.lifecycle.require(con, caller, "engineering")
            self.lifecycle.state(con, bundle_hash)
            self.db.blobs.put(Path(build["jar"]).read_bytes())
            for name, payload in (("java-build-manifest", build["manifest"]), ("verification-report", report)):
                if schema_errors(name, payload):
                    raise LegalMathError("E_SCHEMA")
            bh = self.db.put(con, "build", build["manifest"])
            vh = self.db.put(con, "verification", report)
            self.db.put(con, "corpus", cases)
            self.db.put(con, "verification_results", results)
            if event_cases:
                self.db.put(con, "event_verification_results", loads((Path(output) / "event-verification-results.json").read_bytes()))
            con.execute("INSERT OR IGNORE INTO builds VALUES(?,?,?)", (bh, bundle_hash, report["jar_sha256"]))
            con.execute("INSERT OR IGNORE INTO verifications VALUES(?,?,?,1)", (vh, bh, bundle_hash))
            return {"build_manifest_hash": bh, "verification_report_hash": vh,
                    "jar_sha256": report["jar_sha256"], "class_name": build["class_name"]}
        return self.db.mutate(caller, key, {"op": "build", "bundle": bundle_hash, "cases": digest(cases), "event_cases": digest(event_cases)}, op)

    def prepare(self, caller, key, build_hash, verification_hash, applicability_hash, valid_from, valid_until):
        interval(valid_from, valid_until)

        def op(con):
            self.lifecycle.require(con, caller, "engineering")
            build = self.db.get(con, build_hash)
            report = self.db.get(con, verification_hash)
            app = self.db.get(con, applicability_hash)
            bh = build["bundle_hash"]
            self.check_evidence(con, bh, build_hash, verification_hash)
            bundle = self.db.get(con, bh)
            if app["bundle_hash"] != bh or app["conclusion"] != "in_scope" or valid_from < bundle["valid_from"] or valid_from < app["valid_from"]:
                raise LegalMathError("E_RELEASE_BLOCKED")
            for end in (bundle["valid_until"], app["valid_until"]):
                if end is not None and (valid_until is None or valid_until > end):
                    raise LegalMathError("E_RELEASE_BLOCKED")
            manifest = {"record_type": "JavaReleaseManifest", "bundle_hash": bh, "build_manifest_hash": build_hash,
                "verification_report_hash": verification_hash, "profile": "RuleIR-0.1", "applicability_hash": applicability_hash,
                "valid_from": valid_from, "valid_until": valid_until}
            ident = self.db.put(con, "release_manifest", manifest)
            con.execute("INSERT OR IGNORE INTO release_manifests VALUES(?,?,?,?)", (ident, build_hash, verification_hash, applicability_hash))
            return {"java_release_manifest_hash": ident}
        return self.db.mutate(caller, key, {"op": "prepare_release", "build": build_hash, "verification": verification_hash, "applicability": applicability_hash, "from": valid_from, "until": valid_until}, op)

    def check_evidence(self, con, bundle_hash, build_hash, verification_hash):
        b = self.db.get(con, build_hash)
        v = self.db.get(con, verification_hash)
        if not con.execute("SELECT 1 FROM verifications WHERE hash=? AND build_hash=? AND bundle_hash=? AND passed=1", (verification_hash, build_hash, bundle_hash)).fetchone():
            raise LegalMathError("E_RELEASE_BLOCKED")
        if b["bundle_hash"] != bundle_hash or v["bundle_hash"] != bundle_hash or v["build_manifest_hash"] != build_hash or v["jar_sha256"] != b["jar_sha256"] or not v["passed"] or not v["checks"] or not all(c["passed"] for c in v["checks"]):
            raise LegalMathError("E_RELEASE_BLOCKED")
        self.db.blobs.get(b["jar_sha256"])
        self.db.get(con, v["corpus_hash"])
        for check in v["checks"]:
            self.db.get(con, check["evidence_hash"])

    def release(self, caller, key, bundle_hash, manifest_hash, revision, activated_at):
        timestamp(activated_at)

        def op(con):
            self.lifecycle.require(con, caller, "engineering")
            state = self.lifecycle.state(con, bundle_hash, revision)
            if state["state"] != "APPROVED":
                raise LegalMathError("E_RELEASE_BLOCKED")
            m = self.db.get(con, manifest_hash)
            if m["bundle_hash"] != bundle_hash:
                raise LegalMathError("E_RELEASE_BLOCKED")
            self.check_evidence(con, bundle_hash, m["build_manifest_hash"], m["verification_report_hash"])
            self.lifecycle.check_open_issues(con, bundle_hash)
            approvals = con.execute("SELECT * FROM reviews WHERE bundle_hash=?", (bundle_hash,)).fetchall()
            if {r["role"] for r in approvals} != {"meaning", "engineering"} or len({r["reviewer"] for r in approvals}) != 2 or any(r["reviewer"] == state["author"] or self.db.get(con, r["record_hash"])["manifest_hash"] != manifest_hash for r in approvals):
                raise LegalMathError("E_RELEASE_BLOCKED")
            app = self.db.get(con, m["applicability_hash"])
            scope = scope_key(app)
            # Effective intervals cannot overlap even if a binary was retired;
            # retirement does not change what legal interval was reviewed.
            overlaps = con.execute("SELECT 1 FROM releases WHERE scope_key=? AND (valid_until IS NULL OR valid_until>?) AND (? IS NULL OR valid_from<?)", (scope, m["valid_from"], m["valid_until"], m["valid_until"])).fetchone()
            if overlaps:
                raise LegalMathError("E_RELEASE_BLOCKED")
            record = {"record_type": "ReleaseRecord", "bundle_hash": bundle_hash, "manifest_hash": manifest_hash,
                "approvals": sorted(r["record_hash"] for r in approvals), "authority": "LOCAL_SYNTHETIC",
                "activated_at": activated_at, "scope_key": scope, "valid_from": m["valid_from"], "valid_until": m["valid_until"]}
            ident = self.db.put(con, "release", record)
            con.execute("INSERT INTO releases VALUES(?,?,?,?,?,?,?,NULL)", (ident, bundle_hash, manifest_hash, scope, m["valid_from"], m["valid_until"], activated_at))
            con.execute("UPDATE bundles SET state='RELEASED',revision=revision+1 WHERE hash=?", (bundle_hash,))
            return {"release_hash": ident, "authority": "LOCAL_SYNTHETIC", "state": "RELEASED", "revision": revision + 1}
        return self.db.mutate(caller, key, {"op": "release", "bundle": bundle_hash, "manifest": manifest_hash, "revision": revision, "activated_at": activated_at}, op)

    def select(self, con, scope, valid_at, operational_at):
        timestamp(valid_at)
        timestamp(operational_at)
        rows = con.execute("SELECT * FROM releases WHERE scope_key=? AND valid_from<=? AND (valid_until IS NULL OR valid_until>?) AND activated_at<=? AND (retired_at IS NULL OR retired_at>?)", (scope, valid_at, valid_at, operational_at, operational_at)).fetchall()
        if len(rows) != 1:
            raise LegalMathError("E_RELEASE_BLOCKED")
        from ..interpretation.review import guard
        guard(self.db, con, rows[0]['bundle_hash'])
        return dict(rows[0])

    def retire(self, caller, key, release_hash, at, revision):
        timestamp(at)

        def op(con):
            self.lifecycle.require(con, caller, "engineering")
            row = con.execute("SELECT * FROM releases WHERE hash=?", (release_hash,)).fetchone()
            if not row:
                raise LegalMathError("E_NOT_FOUND")
            self.lifecycle.state(con, row["bundle_hash"], revision)
            if row["retired_at"] is not None or at < row["activated_at"]:
                raise LegalMathError("E_RELEASE_BLOCKED")
            con.execute("UPDATE releases SET retired_at=? WHERE hash=?", (at, release_hash))
            con.execute("UPDATE bundles SET state='RETIRED',revision=revision+1 WHERE hash=?", (row["bundle_hash"],))
            return {"release_hash": release_hash, "state": "RETIRED", "revision": revision + 1}
        return self.db.mutate(caller, key, {"op": "retire", "release": release_hash, "at": at, "revision": revision}, op)

    def export_java(self, release_hash, output):
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM releases WHERE hash=?", (release_hash,)).fetchone()
            if not row or row["retired_at"] is not None:
                raise LegalMathError("E_RELEASE_BLOCKED")
            release = self.db.get(con, release_hash)
            from ..interpretation.review import guard
            interpretation_reviews = guard(self.db, con, row['bundle_hash'])
            manifest = self.db.get(con, row["manifest_hash"])
            self.check_evidence(con, row["bundle_hash"], manifest["build_manifest_hash"], manifest["verification_report_hash"])
            build = self.db.get(con, manifest["build_manifest_hash"])
            out = Path(output)
            out.mkdir(parents=True, exist_ok=True)
            (out / "policy.jar").write_bytes(self.db.blobs.get(build["jar_sha256"]))
            for name, payload in (("release-record", release), ("release-manifest", manifest), ("build-manifest", build), ("verification-report", self.db.get(con, manifest["verification_report_hash"]))):
                (out / (name + ".json")).write_bytes(canonical(payload))
            if interpretation_reviews:
                (out / 'interpretation-reviews.json').write_bytes(canonical(interpretation_reviews))
        return {"directory": str(out), "jar_sha256": build["jar_sha256"], "authority": "LOCAL_SYNTHETIC"}
