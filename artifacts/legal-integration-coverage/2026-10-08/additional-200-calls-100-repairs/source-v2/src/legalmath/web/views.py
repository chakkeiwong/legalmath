from importlib.resources import files
import json
from fastapi import Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..errors import LegalMathError
from ..sources.intake import resolve_span
from ..review.amendment import changes
from ..integer import parse as integer, decimal


def hkd(cents):
    amount = integer(cents)
    a = abs(amount)
    digits = decimal(a // 100)
    # Group from the right while preserving each digit's order.
    groups = [digits[max(0, i-3):i] for i in range(len(digits), 0, -3)]
    return ("−" if amount < 0 else "") + "HK$" + ",".join(reversed(groups)) + f".{a % 100:02d}"


def install_views(app, db):
    env = Environment(loader=FileSystemLoader(str(files("legalmath").joinpath("web/templates"))), autoescape=select_autoescape(["html"]))
    env.filters["json"] = lambda obj: json.dumps(obj, ensure_ascii=False, indent=2)
    env.filters["hkd"] = hkd

    def page(title, **context):
        return HTMLResponse(env.get_template("workbench.html").render(title=title, **context))

    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def api_workbench():
        return page("API workbench", view="api")

    @app.get("/static/api.js", include_in_schema=False)
    def api_script():
        return Response(files("legalmath").joinpath("web/static/api.js").read_bytes(), media_type="application/javascript")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index():
        with db.connect() as con:
            bundles = [dict(row) for row in con.execute("SELECT * FROM bundles ORDER BY rowid DESC")]
            decisions = [dict(row) for row in con.execute("SELECT * FROM evaluations ORDER BY rowid DESC LIMIT 100")]
        return page("Regulatory review workbench", view="index", bundles=bundles, decisions=decisions)

    @app.get("/review/{bh}", response_class=HTMLResponse, include_in_schema=False)
    def bundle_view(bh: str):
        with db.connect() as con:
            bundle = db.get(con, bh)
            row = con.execute("SELECT * FROM bundles WHERE hash=?", (bh,)).fetchone()
            if not row: raise LegalMathError("E_NOT_FOUND")
            passages = [{**s, "quote": resolve_span(db, con, s)} for s in bundle["source_spans"]]
            issues = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM issues WHERE bundle_hash=? ORDER BY id", (bh,))]
            examples = []
            for r in con.execute("SELECT hash FROM verifications WHERE bundle_hash=? ORDER BY rowid DESC LIMIT 1", (bh,)):
                report = db.get(con, r[0])
                examples = db.get(con, report["corpus_hash"])
        return page(bundle["bundle_id"], view="bundle", bundle=bundle, bh=bh, state=dict(row), passages=passages, issues=issues, examples=examples)

    @app.get("/decisions/{ident}", response_class=HTMLResponse, include_in_schema=False)
    def decision_view(ident: str):
        with db.connect() as con:
            row = con.execute("SELECT payload_hash FROM evaluations WHERE result_hash=?", (ident,)).fetchone()
            if not row: raise LegalMathError("E_NOT_FOUND")
            record = db.get(con, row[0])
            bundle = db.get(con, record["result"]["bundle_hash"])
            from ..ir.graph import walk
            labels = {}
            for rule in bundle["rules"]:
                for field in ("scope", "body"):
                    for node, _ in walk(rule[field], ""):
                        labels[node["node_id"]] = node.get("name", {"all": "All conditions", "any": "Any alternative", "compare": "Compare " + node.get("cmp", ""), "literal": "Specified value", "not": "Negation", "if": "Conditional branch", "default": "Base with exceptions"}.get(node["op"], node["op"]))
        return page("Decision and supporting evidence", view="decision", record=record, labels=labels)

    @app.get("/amendments/{old_hash}/{new_hash}", response_class=HTMLResponse, include_in_schema=False)
    def amendment_view(old_hash: str, new_hash: str):
        with db.connect() as con:
            report = changes(db.get(con, old_hash), db.get(con, new_hash))
        return page("Review an amendment", view="amendment", report=report)

    @app.get("/sources/{raw_hash}/original", include_in_schema=False)
    def original(raw_hash: str):
        with db.connect() as con:
            allowed = False
            for row in con.execute("SELECT payload_hash FROM sources"):
                source = db.get(con, row[0])
                if source["raw_sha256"] == raw_hash:
                    allowed = True
                    break
            if not allowed: raise LegalMathError("E_NOT_FOUND")
        data = db.blobs.get(raw_hash)
        media = "application/pdf" if data.startswith(b"%PDF-") else "text/plain"
        return Response(data, media_type=media)
