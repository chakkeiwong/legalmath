"""FastAPI is a transport over pure evaluators and transactional services."""
import base64
from pathlib import Path
from urllib.parse import urlsplit
import uuid

from fastapi import FastAPI, Request, Depends, Header, Body
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..canonical import canonical, loads, digest
from ..domain import timestamp, eligible
from ..errors import LegalMathError, BoundaryError, diagnostic
from ..storage import Database
from ..review.lifecycle import Lifecycle
from ..review.releases import Releases
from ..review.amendment import changes
from ..sources.intake import import_source, resolve_span
from ..sources.fetch import fetch
from ..ir.evaluate import evaluate
from ..ir.normalize import normalize
from ..ir.load import schema_errors
from ..ir.trace import verify_result
from ..events.records import create_stream, append_event
from ..events.replay import replay
from .jobs import Jobs
from . import models


def create_app(data_dir, identities=None, *, jdk=None, comparison_jar=None, run_jobs=True, search_provider=None):
    db, lc = Database(data_dir), None
    lc = Lifecycle(db)
    if identities: lc.register(identities)
    releases, jobs = Releases(db), Jobs(db)
    app = FastAPI(title="LegalMath public/synthetic workbench", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.db, app.state.jobs = db, jobs

    @app.middleware("http")
    async def bounded_json(request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 20 * 1024 * 1024:
                    return JSONResponse({"error": "E_RESOURCE_LIMIT", "diagnostics": [diagnostic("E_RESOURCE_LIMIT")]}, status_code=413)
                chunks.append(chunk)
            raw = b"".join(chunks)
            if raw:
                try: loads(raw)
                except LegalMathError as exc: return JSONResponse(exc.envelope(), status_code=422)
            request._body = raw
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-src 'self'; object-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'none'"
        return response

    @app.exception_handler(LegalMathError)
    async def legal_error(request, exc):
        code = 422
        if exc.code in ("E_IDEMPOTENCY", "E_STALE_REVIEW", "E_EVENT_ID_COLLISION", "E_SEQUENCE_COLLISION", "E_RELEASE_BLOCKED"): code = 409
        if exc.code == "E_AUTHORITY": code = 403
        if exc.code == "E_NOT_FOUND": code = 404
        if exc.code == "E_FETCH": code = 502
        return JSONResponse(exc.envelope(), status_code=code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(BoundaryError("E_SCHEMA").envelope(), status_code=422)

    def caller(authorization: str = Header()):
        if not authorization.startswith("Bearer "): raise LegalMathError("E_AUTHORITY")
        return lc.authenticate(authorization[7:])

    def key(idempotency_key: str = Header(alias="Idempotency-Key")):
        if not 1 <= len(idempotency_key) <= 200: raise LegalMathError("E_SCHEMA")
        return idempotency_key

    def require(c, role=None):
        with db.connect() as con: lc.require(con, c, role)

    @app.post("/v1/sources/import", status_code=201)
    def source_import(body: models.SourceImport, c=Depends(caller), k=Depends(key)):
        require(c, "author")
        if body.content_base64 is None:
            downloaded = fetch(body.official_url)
            if downloaded["media_type"] != body.media_type: raise LegalMathError("E_SCHEMA")
            raw = downloaded["data"]
            authority = "HKMA_PUBLIC_SOURCE" if urlsplit(downloaded["url"]).hostname == "www.hkma.gov.hk" else "SFC_PUBLIC_SOURCE"
        else:
            try: raw = base64.b64decode(body.content_base64, validate=True)
            except ValueError as exc: raise LegalMathError("E_SCHEMA") from exc
            authority = "UPLOADED_UNVERIFIED"
        return db.mutate(c, k, {"op": "source_import", **body.model_dump()}, lambda con: import_source(db, con, body.source_id, raw, body.media_type, body.official_url, body.retrieved_at, authority=authority))

    @app.post("/v1/bundles", status_code=201)
    def bundle_create(bundle: dict = Body(), c=Depends(caller), k=Depends(key)):
        return lc.create(c, k, bundle)

    @app.get("/v1/bundles/{bh}")
    def bundle_get(bh: str, c=Depends(caller)):
        with db.connect() as con:
            row = lc.state(con, bh)
            issues = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM issues WHERE bundle_hash=? ORDER BY id", (bh,))]
            return {"bundle": db.get(con, bh), "state": row["state"], "revision": row["revision"], "issues": issues}

    @app.post("/v1/bundles/{bh}/review")
    def review(bh: str, body: models.Review, c=Depends(caller), k=Depends(key)):
        return lc.transition(c, k, bh, body.decision, body.expected_revision, body.comment, body.manifest_hash)

    @app.post("/v1/bundles/{bh}/issues/{issue_id}")
    def issue_resolve(bh: str, issue_id: str, body: models.ResolveIssue, c=Depends(caller), k=Depends(key)):
        return lc.resolve_issue(c, k, bh, issue_id, body.resolution, body.resolved_at, body.expected_revision)

    @app.post("/v1/applicability", status_code=201)
    def applicability(body: dict = Body(), c=Depends(caller), k=Depends(key)):
        return lc.assess(c, k, body)

    @app.post("/v1/bundles/{bh}/coverage")
    def record_coverage(bh: str, body: models.Coverage, c=Depends(caller), k=Depends(key)):
        return lc.record_coverage(c, k, bh, body.inventory, body.expected_revision)

    @app.post("/v1/bundles/{bh}/build-java", status_code=201)
    def build(bh: str, body: models.Build, c=Depends(caller), k=Depends(key)):
        if jdk is None: raise LegalMathError("E_UNSUPPORTED_PROFILE")
        out = Path(data_dir) / "candidate-builds" / uuid.uuid4().hex
        return releases.build(c, k, bh, out, jdk, body.cases, body.event_cases)

    @app.post("/v1/release-manifests", status_code=201)
    def release_prepare(body: models.PrepareRelease, c=Depends(caller), k=Depends(key)):
        return releases.prepare(c, k, body.build_manifest_hash, body.verification_report_hash, body.applicability_hash, body.valid_from, body.valid_until)

    @app.post("/v1/bundles/{bh}/release", status_code=201)
    def release(bh: str, body: models.Release, c=Depends(caller), k=Depends(key)):
        return releases.release(c, k, bh, body.java_release_manifest_hash, body.expected_revision, body.activated_at)

    @app.post("/v1/evaluations")
    def evaluation(body: models.Evaluation, c=Depends(caller), k=Depends(key)):
        request = body.model_dump()
        def op(con):
            bundle = db.get(con, body.bundle_hash)
            lc.state(con, body.bundle_hash)
            if body.mode == "production":
                if not body.release_hash or not body.operational_at: raise LegalMathError("E_RELEASE_BLOCKED")
                row = con.execute("SELECT * FROM releases WHERE hash=?", (body.release_hash,)).fetchone()
                if not row or row["bundle_hash"] != body.bundle_hash: raise LegalMathError("E_RELEASE_BLOCKED")
                selected = releases.select(con, row["scope_key"], body.valid_at, body.operational_at)
                if selected["hash"] != body.release_hash: raise LegalMathError("E_RELEASE_BLOCKED")
                manifest = db.get(con, row["manifest_hash"])
                releases.check_evidence(con, body.bundle_hash, manifest["build_manifest_hash"], manifest["verification_report_hash"])
            elif body.release_hash:
                row = con.execute("SELECT bundle_hash FROM releases WHERE hash=?", (body.release_hash,)).fetchone()
                if not row or row["bundle_hash"] != body.bundle_hash: raise LegalMathError("E_REFERENCE")
            result = evaluate(bundle, body.snapshot, body.rule_id, body.valid_at, body.known_at, body.mode)
            verify_result(bundle, body.snapshot, body.rule_id, result)
            ident = db.put(con, "evaluation", {"request": request, "result": result})
            con.execute("INSERT OR IGNORE INTO evaluations VALUES(?,?,?,?)", (result["result_hash"], ident, body.bundle_hash, body.release_hash))
            return result
        return db.mutate(c, k, {"op": "evaluate", **request}, op)

    @app.get("/v1/evaluations/{ident}")
    def evaluation_get(ident: str, c=Depends(caller)):
        with db.connect() as con:
            row = con.execute("SELECT payload_hash FROM evaluations WHERE result_hash=?", (ident,)).fetchone()
            if not row: raise LegalMathError("E_NOT_FOUND")
            return db.get(con, row[0])

    @app.post("/v1/fact-records", status_code=201)
    def fact_record(body: dict = Body(), c=Depends(caller), k=Depends(key)):
        require(c, "author")
        def op(con):
            if schema_errors("fact-record", body): raise LegalMathError("E_SCHEMA")
            related = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM facts WHERE subject_id=? AND fact_name=?", (body["subject_id"], body["fact_name"]))]
            normalize(related + [body], [{"name": body["fact_name"], "type": body["type"]}], body["subject_id"], body["valid_from"], body["recorded_at"])
            ident = db.put(con, "fact", body)
            con.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?)", tuple(body[f] for f in ("record_id", "subject_id", "fact_name", "type", "valid_from", "valid_until", "recorded_at")) + (ident,))
            for predecessor in body["supersedes_record_ids"]: con.execute("INSERT INTO supersession VALUES(?,?)", (body["record_id"], predecessor))
            return {"fact_hash": ident}
        return db.mutate(c, k, {"op": "fact", "record": body}, op)

    @app.post("/v1/snapshots", status_code=201)
    def snapshot(body: models.Snapshot, c=Depends(caller), k=Depends(key)):
        def op(con):
            bundle = db.get(con, body.bundle_hash)
            rows = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM facts WHERE subject_id=?", (body.subject_id,))]
            data = normalize(rows, bundle["facts"], body.subject_id, body.valid_at, body.known_at)
            return {"snapshot_hash": db.put(con, "snapshot", data), "snapshot": data}
        return db.mutate(c, k, {"op": "snapshot", **body.model_dump()}, op)

    @app.post("/v1/event-streams", status_code=201)
    def stream_create(body: dict = Body(), c=Depends(caller), k=Depends(key)):
        require(c, "meaning" if body.get("initial_snapshot") else "author")
        return db.mutate(c, k, {"op": "stream", "header": body}, lambda con: create_stream(db, con, body, reviewer=c))

    @app.post("/v1/event-streams/{stream_id}/events", status_code=201)
    def event_append(stream_id: str, body: models.EventAppend, c=Depends(caller), k=Depends(key)):
        require(c, "author")
        return db.mutate(c, k, {"op": "append_event", "stream_id": stream_id, **body.model_dump()}, lambda con: append_event(db, con, stream_id, body.event, body.expected_revision))

    @app.post("/v1/event-streams/{stream_id}/replay")
    def replay_stream(stream_id: str, body: models.Replay, c=Depends(caller), k=Depends(key)):
        def op(con):
            row = con.execute("SELECT header_hash FROM streams WHERE id=?", (stream_id,)).fetchone()
            if not row: raise LegalMathError("E_NOT_FOUND")
            events = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM events WHERE stream_id=? ORDER BY sequence", (stream_id,))]
            request = {"header": db.get(con, row[0]), "events": events, "valid_at": body.valid_at, "known_at": body.known_at, "completeness": body.completeness}
            result = replay(request)
            rh = db.put(con, "replay", {"request": request, "result": result})
            con.execute("INSERT OR IGNORE INTO replays VALUES(?,?)", (rh, stream_id))
            return result
        return db.mutate(c, k, {"op": "replay", "stream": stream_id, **body.model_dump()}, op)

    @app.post("/v1/drafts", status_code=202)
    def draft(body: models.Draft, c=Depends(caller), k=Depends(key)):
        require(c, "author")
        spans = body.source_inventory.get("source_spans")
        if not isinstance(spans, list) or not spans or any(not isinstance(s, dict) for s in spans):
            raise LegalMathError("E_SCHEMA")
        with db.connect() as con:
            for span in spans:
                from ..ir.load import source_span_errors
                if source_span_errors(span): raise LegalMathError("E_SCHEMA")
                resolve_span(db, con, span)
        result = jobs.submit(c, k, "draft", body.model_dump())
        if run_jobs: jobs.start(result["job_id"])
        return result

    @app.post("/v1/comparisons", status_code=202)
    def comparison(body: models.Comparison, c=Depends(caller), k=Depends(key)):
        with db.connect() as con:
            request = {"old": db.get(con, body.old_hash), "new": db.get(con, body.new_hash), "rule_id": body.rule_id,
                "domain": body.domain, "valid_at": body.valid_at, "known_at": body.known_at, "budget_ms": body.budget_ms,
                "java_jar": str(comparison_jar) if comparison_jar else None, "jdk": str(jdk) if jdk else None}
        result = jobs.submit(c, k, "compare", request)
        if run_jobs: jobs.start(result["job_id"])
        return result

    @app.get("/v1/jobs/{ident}")
    def job_get(ident: str, c=Depends(caller)): return jobs.get(ident)

    @app.post("/v1/jobs/{ident}/cancel")
    def job_cancel(ident: str, c=Depends(caller), k=Depends(key)): return jobs.cancel(c, k, ident)

    @app.get("/v1/changes/{old_hash}/{new_hash}")
    def change_get(old_hash: str, new_hash: str, c=Depends(caller)):
        with db.connect() as con: return changes(db.get(con, old_hash), db.get(con, new_hash))

    from ..web.views import install_views
    install_views(app, db)
    from ..interpretation.api import install as install_interpretations
    install_interpretations(app, db, caller, key, run_jobs)
    from ..interpretation.search.api import install as install_search
    install_search(app,app.state.interpretations,caller,key,jdk,search_provider,run_jobs)
    from .openapi import install_contracts
    install_contracts(app)
    return app
