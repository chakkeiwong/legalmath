"""Run the bounded BES onward-source disposition consumer.

The 11 financial records and three agency agreements are named in retained
prospectus passages, but their authenticated original bytes are absent.  This
consumer binds that absence explicitly, then exercises the source-specific
agency applicability passages through the real service.  It is source and
engineering evidence, not a legal conclusion.
"""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
OUTPUT = PACKAGE / "attempt-002"
BASE = ROOT / "docs/implementation/prospectus-integration-closure"
PLAN = ROOT / "docs/plans/prospectus-bes-onward-source-disposition-2026-10-11.md"
COMPARATOR = BASE / "bes-source-chain/consumer/attempt-007/assisted-report.json.gz"
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(BASE / "bes-source-chain")]

from legalmath.prospectus.successor import service  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402
import consumer as prior_consumer  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_gzip(path, value):
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(value):
    return " ".join(str(value).split()).lower()


def source_metadata(path):
    """Return hash-bound metadata from the nearest retained source manifest."""
    for parent in (path.parent, *path.parents):
        manifest = parent / "manifest.json"
        if not manifest.exists():
            continue
        try:
            row = read(manifest)
        except (OSError, json.JSONDecodeError):
            continue
        return {
            "manifest": manifest.relative_to(ROOT).as_posix(),
            "source_key": row.get("key"),
            "source_status": row.get("status"),
            "source_original": row.get("original"),
            "source_sha256": row.get("sha256"),
            "source_media": row.get("media"),
            "source_complete": row.get("source_complete"),
            "source_pages": row.get("pages"),
            "source_text": row.get("text"),
            "source_text_sha256": row.get("text_sha256"),
            "extraction_status": row.get("extraction_status"),
        }
    return {"manifest": None}


def decode_for_search(path):
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return None, "PDF_BYTES_NOT_DECODED"
    if suffix in {".txt", ".json", ".html"}:
        return raw.decode("utf-8", errors="replace"), "UTF8_TEXT"
    if suffix == ".bin":
        decoded = raw.decode("utf-8", errors="ignore")
        printable = sum(ch.isprintable() or ch.isspace() for ch in decoded)
        if decoded and printable / len(decoded) >= 0.75:
            return decoded, "UTF8_BINARY_RESPONSE"
        return None, "BINARY_NOT_TEXT"
    return None, "UNSUPPORTED_SUFFIX"


DEPENDENCY_SEARCH_PATTERNS = {
    "BES-DEP-01": ["2nd November, 2010", "9M 2010", "press release of the Bank"],
    "BES-DEP-02": ["six months ended 30th June, 2010", "BES Finance", "interim financial"],
    "BES-DEP-03": ["financial year ended 31st December, 2009", "BES Finance", "audited annual"],
    "BES-DEP-04": ["31st December, 2008", "BES Finance", "financial statements and Notes"],
    "BES-DEP-05": ["six months ended 30th June, 2010", "consolidated and non-consolidated", "Bank"],
    "BES-DEP-06": ["financial year ended 31st December, 2009", "consolidated and non-consolidated", "Bank"],
    "BES-DEP-07": ["financial year ended 31st December, 2008", "consolidated and non-consolidated", "Bank"],
    "BES-DEP-08": ["31 January 2011", "unaudited", "press release"],
    "BES-DEP-09": ["audited consolidated annual financial statements", "2010", "Bank"],
    "BES-DEP-10": ["audited annual financial statements of BES Finance", "2010", "BES Finance"],
    "BES-DEP-11": ["2 May, 2011", "press release", "first quarter"],
    "BES-DEP-AGENCY-01": ["Principal Agency Agreement", "18th January, 2008"],
    "BES-DEP-AGENCY-02": ["Interbolsa Notes Agency Agreement", "18 February, 2009"],
    "BES-DEP-AGENCY-03": ["Common Representative Appointment Agreement", "3rd November, 2010"],
}


def anchor(graph, unit_id):
    matches = [u for u in graph["units"] if u["id"] == unit_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one exact source unit: {unit_id}")
    return prior_consumer.anchor(matches[0])


def retained_search_manifest():
    roots = [
        ROOT / "docs/prospectus/corner-cases-2026-10-04/sources",
        ROOT / "docs/prospectus/closure-2026-10-05/derivatives",
        ROOT / "docs/prospectus/jurisdiction-2026-10-04/sources",
        BASE / "bes-source-chain/source-review-001",
    ]
    allowed = {".pdf", ".txt", ".json", ".html", ".bin"}
    files = []
    searchable = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in allowed:
                continue
            rel = path.relative_to(ROOT).as_posix()
            text, decode_status = decode_for_search(path)
            row = {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha(path),
                "metadata": source_metadata(path),
                "searchable": text is not None,
                "decode_status": decode_status,
            }
            files.append(row)
            searchable[rel] = text or ""
    if not files:
        raise ValueError("Retained source corpus is empty")
    dependency_search = {}
    for dependency, patterns in DEPENDENCY_SEARCH_PATTERNS.items():
        hits = []
        for row in files:
            text = searchable[row["path"]]
            if not text:
                continue
            folded = normalized(text)
            matched = [pattern for pattern in patterns if normalized(pattern) in folded]
            if not matched:
                continue
            first = min(folded.find(normalized(pattern)) for pattern in matched)
            hits.append({
                "path": row["path"],
                "sha256": row["sha256"],
                "matched_patterns": matched,
                "snippet": folded[max(0, first - 180):first + 420],
                "metadata": row["metadata"],
            })
        dependency_search[dependency] = hits
    unsearched = [row["path"] for row in files if not row["searchable"]]
    manifest = {
        "version": "bes-retained-corpus-search.v2",
        "scope": "retained repository files under the four named roots; no network or internet claim",
        "roots": [p.relative_to(ROOT).as_posix() for p in roots],
        "file_count": len(files),
        "files": files,
        "dependency_search": dependency_search,
        "unsearched_files": unsearched,
        "candidate_rule": "Content or metadata hits are search leads only. A candidate becomes an authenticated original only after separate bytes, source identity, expected date/issuer/scope and provenance are bound.",
        "network": "NOT_USED",
    }
    path = OUTPUT / "search-manifest.json"
    write(path, manifest)
    return manifest, sha(path)


def validate_introducer(anchor_row):
    """Check the retained introducer bytes and quoted page before disposition."""
    original = ROOT / anchor_row["original"]
    text_path = ROOT / anchor_row["text"]
    if not original.exists() or sha(original) != anchor_row["source_sha256"]:
        raise ValueError("Introducer source hash changed: " + anchor_row["document"])
    if not text_path.exists() or sha(text_path) != anchor_row["text_sha256"]:
        raise ValueError("Introducer text hash changed: " + anchor_row["document"])
    payload = read(text_path)
    pages = payload.get("pages", payload) if isinstance(payload, dict) else payload
    page = next((p for p in pages if p.get("page") == anchor_row["page"]), None)
    if page is None:
        raise ValueError("Introducer page missing: " + anchor_row["document"])
    page_text = normalized(page.get("text", ""))
    quote = normalized(anchor_row["quote"])
    position = page_text.find(quote)
    if position < 0:
        raise ValueError("Introducer quote not found: " + anchor_row["document"])
    quote_status = "EXACT_NORMALIZED_MATCH" if position == anchor_row["start"] else "EXACT_NORMALIZED_MATCH_OFFSET_REPAIRED"
    return {
        "original_sha256": sha(original),
        "text_sha256": sha(text_path),
        "page": anchor_row["page"],
        "quote_status": quote_status,
    }


def search_row(search_manifest, dependency):
    hits = search_manifest["dependency_search"].get(dependency, [])
    return {
        "search_hits": hits,
        "search_hit_count": len(hits),
        "search_disposition": (
            "TEXT_OR_METADATA_LEADS_ONLY_NO_AUTHENTICATED_ORIGINAL_BOUND"
            if hits else "NO_SEARCHABLE_CONTENT_OR_METADATA_LEAD"
        ),
        "unsearched_file_count": len(search_manifest["unsearched_files"]),
        "candidate_paths": [],
    }


def disposition_specs(dossier, search_manifest):
    # The retained closure dossier contains 29 historical dependencies.  This
    # phase is scoped to the eleven financial records that the BES source-chain
    # request actually carries forward; later prior-base and post-2011 rows are
    # separate future work and must not be silently relabelled here.
    included = {f"BES-DEP-{i:02d}" for i in range(1, 12)}
    dates_issuers = {
        "BES-DEP-01": ("2010-11-02", "Banco Espírito Santo, S.A. (Bank)", "9M 2010 press release"),
        "BES-DEP-02": ("2010-06-30", "BES Finance Ltd.", "six-month interim statements"),
        "BES-DEP-03": ("2009-12-31", "BES Finance Ltd.", "audited annual statements"),
        "BES-DEP-04": ("2008-12-31", "BES Finance Ltd.", "audited annual statements"),
        "BES-DEP-05": ("2010-06-30", "Banco Espírito Santo, S.A. (Bank)", "six-month interim statements"),
        "BES-DEP-06": ("2009-12-31", "Banco Espírito Santo, S.A. (Bank)", "audited annual statements"),
        "BES-DEP-07": ("2008-12-31", "Banco Espírito Santo, S.A. (Bank)", "audited annual statements"),
        "BES-DEP-08": ("2011-01-31", "Banco Espírito Santo, S.A. (Bank)", "unaudited release"),
        "BES-DEP-09": ("2010-12-31", "Banco Espírito Santo, S.A. (Bank)", "audited annual statements"),
        "BES-DEP-10": ("2010-12-31", "BES Finance Ltd.", "audited annual statements"),
        "BES-DEP-11": ("2011-05-02", "Banco Espírito Santo, S.A. (Bank)", "Q1 2011 press release"),
    }
    rows = []
    for item in dossier["dependencies"]:
        if item["id"] not in included:
            continue
        date, issuer, kind = dates_issuers[item["id"]]
        row = {
            "id": item["id"],
            "kind": "incorporated_financial_record",
            "title": item["title"],
            "expected_date": date,
            "expected_issuer": issuer,
            "expected_scope": item["incorporated_scope"],
            "introduced_by": item["introduced_by"],
            "introducer_anchor": item["anchor"],
            **search_row(search_manifest, item["id"]),
            "introducer_validation": validate_introducer(item["anchor"]),
            "original_bytes_sha256": None,
            "acquisition_status": "MISSING_FROM_RETAINED_CORPUS",
            "authenticity_status": "UNAUTHENTICATED",
            "disposition": "UNRESOLVED",
            "reason": f"The retained corpus has searchable leads and the {kind} introducer, but no separately authenticated original bytes bound to this issuer and date.",
        }
        rows.append(row)
    return rows


def paragraph_record(graph, unit_id):
    unit = unit_by_id(graph, unit_id)
    siblings = sorted((u for u in graph["units"] if u.get("parent") == unit.get("parent")), key=lambda u: u.get("order", 0))
    text = " ".join(u["raw"] for u in siblings)
    return {
        "parent": unit.get("parent"),
        "unit_ids": [u["id"] for u in siblings],
        "page": unit.get("page"),
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def paragraph_units(graph, unit_id):
    unit = unit_by_id(graph, unit_id)
    return [u["id"] for u in sorted((x for x in graph["units"] if x.get("parent") == unit.get("parent")), key=lambda x: x.get("order", 0))]


def graph_source_validation(graph, unit_id):
    unit = unit_by_id(graph, unit_id)
    document = next(d for d in graph["documents"] if d["id"] == unit["document"])
    original = ROOT / document["path"]
    if not original.exists() or sha(original) != document["sha256"]:
        raise ValueError("Applicability source hash changed: " + unit_id)
    return {
        "document": document["id"],
        "path": document["path"],
        "source_sha256": document["sha256"],
        "unit": unit_id,
        "unit_text_sha256": unit["text_sha256"],
        "source_authenticity": document.get("authority"),
        "source_acquisition_status": document.get("acquisition_status"),
    }


def build_dispositions(graph, search_manifest, search_hash, dossier):
    rows = disposition_specs(dossier, search_manifest)
    agency = [
        ("BES-DEP-AGENCY-01", "Principal Agency Agreement dated 18 January 2008", "2008-01-18", "Banco Espírito Santo, S.A. programme parties", "bes-base-2010:p76:l43", "Principal Agency Agreement; executed parties and amendments"),
        ("BES-DEP-AGENCY-02", "Interbolsa Notes Agency Agreement dated 18 February 2009", "2009-02-18", "Banco Espírito Santo, S.A. programme parties and Portuguese paying agent", "bes-base-2010:p76:l48", "Interbolsa amendment; exact operative terms and parties"),
        ("BES-DEP-AGENCY-03", "Common Representative Appointment Agreement dated 3 November 2010", "2010-11-03", "Banco Espírito Santo, S.A. and named common representative (as described in the base)", "bes-base-2010:p77:l4", "Common Representative appointment; executed agreement and later amendments"),
    ]
    for ident, title, date, issuer, unit, scope in agency:
        rows.append({
            "id": ident,
            "kind": "agency_agreement",
            "title": title,
            "expected_date": date,
            "expected_issuer": issuer,
            "expected_scope": scope,
            "introduced_by": "jur-more-bes-1217215",
            "introducer_anchor": anchor(graph, unit),
            "introducer_paragraph": paragraph_record(graph, unit),
            "introducer_validation": graph_source_validation(graph, unit),
            **search_row(search_manifest, ident),
            "original_bytes_sha256": None,
            "acquisition_status": "MISSING_FROM_RETAINED_CORPUS",
            "authenticity_status": "UNAUTHENTICATED",
            "disposition": "UNRESOLVED",
            "reason": "The retained corpus has searchable agency-language leads and the base introducer, but the executed agreement bytes are not authenticated or bound as a separate original.",
        })
    if len(rows) != 14 or {r["id"] for r in rows} != {f"BES-DEP-{i:02d}" for i in range(1, 12)} | {"BES-DEP-AGENCY-01", "BES-DEP-AGENCY-02", "BES-DEP-AGENCY-03"}:
        raise ValueError("Disposition inventory must contain exactly 11 financial and 3 agency rows")
    result = {
        "version": "bes-onward-source-disposition.v2",
        "search_manifest_sha256": search_hash,
        "corpus_scope": "Retained repository only; no exhaustive internet search",
        "rows": rows,
        "all_original_bytes_bound": False,
        "missing_or_unauthenticated_remain_unresolved": True,
    }
    path = OUTPUT / "source-disposition.json"
    write(path, result)
    return result, sha(path)


def applicability(graph):
    def a(unit):
        return anchor(graph, unit)
    def p(unit):
        return paragraph_record(graph, unit)
    def v(unit):
        return graph_source_validation(graph, unit)
    rows = [
        {
            "id": "agency-instruments-and-precedence",
            "category": "named_agency_instruments",
            "status": "CONDITIONAL_UNRESOLVED",
            "anchors": [a("bes-base-2010:p76:l43"), a("bes-base-2010:p76:l48"), a("bes-base-2010:p77:l4"), a("bes-base-2010:p78:l22")],
            "paragraphs": [p("bes-base-2010:p76:l43"), p("bes-base-2010:p77:l4"), p("bes-base-2010:p78:l22")],
            "source_validations": [v("bes-base-2010:p76:l43"), v("bes-base-2010:p77:l4"), v("bes-base-2010:p78:l22")],
            "reading": "The complete retained paragraphs name the Principal Agency Agreement, its Interbolsa amendment, the named parties and the Common Representative Appointment Agreement, and state the Interbolsa precedence rule. The absent agreement bytes prevent a complete operative-agreement reading.",
        },
        {
            "id": "portuguese-law-and-forum",
            "category": "portuguese_law_and_jurisdiction",
            "status": "CONDITIONAL_UNRESOLVED",
            "anchors": [a("bes-base-2010:p111:l17"), a("bes-base-2010:p112:l6"), a("bes-base-2010:p112:l30")],
            "paragraphs": [p("bes-base-2010:p111:l17"), p("bes-base-2010:p112:l6"), p("bes-base-2010:p112:l30")],
            "source_validations": [v("bes-base-2010:p111:l17"), v("bes-base-2010:p112:l6"), v("bes-base-2010:p112:l30")],
            "reading": "The complete retained Condition 22 paragraphs state the English-law branch, the Portuguese-law branch, the conflicts qualification for BES Finance and the Bank, Portuguese courts for Interbolsa proceedings, and the separate right to sue in another competent court. This is a retained contractual statement, not an independent conflicts or forum conclusion.",
        },
        {
            "id": "book-entry-and-common-representative",
            "category": "interbolsa_book_entry_and_representation",
            "status": "CONDITIONAL_UNRESOLVED",
            "anchors": [a("bes-final-terms-2011:p3:ocr17"), a("bes-base-2010:p78:l36"), a("bes-base-2010:p112:l43")],
            "paragraphs": [p("bes-final-terms-2011:p3:ocr17"), p("bes-base-2010:p78:l36"), p("bes-base-2010:p112:l43")],
            "source_validations": [v("bes-final-terms-2011:p3:ocr17"), v("bes-base-2010:p78:l36"), v("bes-base-2010:p112:l43")],
            "reading": "The final terms select registered book-entry Interbolsa Notes; the complete base paragraphs describe the registered/bearer alternatives and the holder power to appoint or dismiss a Common Representative, subject to the absent appointment agreement.",
        },
        {
            "id": "generic-icsd-safekeeper",
            "category": "generic_icsd_safekeeper",
            "status": "CONDITIONAL_UNRESOLVED",
            "anchors": [a("bes-final-terms-2011:p6:ocr43"), a("bes-base-2010:p75:l53")],
            "paragraphs": [p("bes-final-terms-2011:p6:ocr43"), p("bes-base-2010:p75:l53")],
            "source_validations": [v("bes-final-terms-2011:p6:ocr43"), v("bes-base-2010:p75:l53")],
            "reading": "The complete final-terms and base disclaimer paragraphs say that the common-safekeeper designation does not necessarily establish Eurosystem collateral recognition and depends on the eligibility criteria. They remain separate from Interbolsa agency and Portuguese-law passages and do not prove actual eligibility or a holding chain.",
        },
    ]
    result = {
        "version": "bes-agency-applicability-review.v2",
        "reviewer": {"type": "executor_source_review", "independent_legal_acceptance": False},
        "rows": rows,
        "legal_conclusions": "NOT_PROVIDED",
    }
    path = OUTPUT / "agency-applicability.json"
    write(path, result)
    return result, sha(path)


def unit_by_id(graph, ident):
    rows = [u for u in graph["units"] if u["id"] == ident]
    if len(rows) != 1:
        raise ValueError("Missing source unit: " + ident)
    return rows[0]


def add_onward_edges(req, graph):
    refs = {ident: anchor(graph, ident) for ident in (
        "bes-base-2010:p76:l43", "bes-base-2010:p76:l48", "bes-base-2010:p77:l4",
        "bes-base-2010:p78:l22", "bes-base-2010:p78:l36", "bes-base-2010:p111:l17",
        "bes-base-2010:p112:l6", "bes-base-2010:p112:l30", "bes-base-2010:p112:l43",
        "bes-base-2010:p75:l53", "bes-final-terms-2011:p3:ocr17",
        "bes-final-terms-2011:p6:ocr43")}
    edge_units = {
        "onward-agency-precedence": sum((paragraph_units(graph, ident) for ident in (
            "bes-base-2010:p76:l43", "bes-base-2010:p77:l4", "bes-base-2010:p78:l22")), []),
        "onward-portuguese-law-forum-representative": sum((paragraph_units(graph, ident) for ident in (
            "bes-base-2010:p111:l17", "bes-base-2010:p112:l6", "bes-base-2010:p112:l30")), []),
        "onward-book-entry": sum((paragraph_units(graph, ident) for ident in (
            "bes-final-terms-2011:p3:ocr17", "bes-base-2010:p78:l36", "bes-base-2010:p112:l43")), []),
        "onward-generic-icsd-safekeeper": sum((paragraph_units(graph, ident) for ident in (
            "bes-final-terms-2011:p6:ocr43", "bes-base-2010:p75:l53")), []),
    }
    edges = [
        {"id": "onward-agency-precedence", "kind": "governs", "from": refs["bes-base-2010:p76:l43"],
         "to": [anchor(graph, x) for x in edge_units["onward-agency-precedence"]],
         "questions": ["Q1", "Q2"], "reason": "Reviewed named-agreement and precedence passages; absent agreement bytes remain an explicit dependency."},
        {"id": "onward-portuguese-law-forum-representative", "kind": "governs", "from": refs["bes-base-2010:p111:l17"],
         "to": [anchor(graph, x) for x in edge_units["onward-portuguese-law-forum-representative"]],
         "questions": ["Q1", "Q2"], "reason": "Keep Portuguese-law, forum and Common Representative references together while withholding an independent legal conclusion."},
        {"id": "onward-book-entry", "kind": "governs", "from": refs["bes-final-terms-2011:p3:ocr17"],
         "to": [anchor(graph, x) for x in edge_units["onward-book-entry"]],
         "questions": ["Q1", "Q2"], "reason": "Final Terms select registered Interbolsa book-entry form; the base passage is retained as contextual contract text."},
        {"id": "onward-generic-icsd-safekeeper", "kind": "governs", "from": refs["bes-final-terms-2011:p6:ocr43"],
         "to": [anchor(graph, x) for x in edge_units["onward-generic-icsd-safekeeper"]],
         "questions": ["Q1", "Q2"], "reason": "Generic ICSD/common-safekeeper wording is a separate contextual category and does not establish collateral eligibility."},
    ]
    req["layout_admission"]["governing"].extend(edges)
    existing = {row["unit"] for row in req["assembly"]["operations"]}
    all_onward_units = []
    for units in edge_units.values():
        all_onward_units.extend(units)
    for ident in dict.fromkeys(all_onward_units):
        if ident in existing:
            continue
        u = unit_by_id(graph, ident)
        req["assembly"]["operations"].append({
            "unit": ident, "source_text_sha256": u["text_sha256"], "role": "OPERATIVE",
            "reason": "Reviewed onward applicability passage; absent agreement bytes remain unresolved",
            "context": u["parent"], "questions": ["Q1", "Q2"],
        })
    # The annotation packet covers the original final-terms readings.  Its
    # assembly binding must be refreshed after the extra operative passages are
    # admitted; no new meaning is invented for those passages.
    p1 = service.source_product(req, ROOT)
    p2 = service.construction_product(p1, ROOT)
    req["annotation_admission"]["assembly_sha256"] = digest(p2["payload"]["assembly"])
    return req, edges


def omission_variant(req, edge, omit_unit):
    variant = deepcopy(req)
    for row in variant["assembly"]["operations"]:
        if row["unit"] == omit_unit:
            row["role"] = "EXCLUDED"
            row["reason"] = "Matched onward-applicability omission control"
            break
    else:
        raise ValueError("Omission unit was not in assembly: " + omit_unit)
    p1 = service.source_product(variant, ROOT)
    p2 = service.construction_product(p1, ROOT)
    variant["annotation_admission"]["assembly_sha256"] = digest(p2["payload"]["assembly"])
    return variant


def expect_rejection(req, marker):
    try:
        service.assess(req, ROOT)
    except (ValueError, KeyError) as exc:
        message = str(exc)
        if marker not in message:
            raise ValueError(f"Unexpected adverse rejection: {message}") from exc
        return {"status": "PASS", "message": message}
    raise ValueError("Adverse input was accepted: " + marker)


def main():
    if len(sys.argv) != 1 or sys.flags.optimize:
        raise ValueError("Exact invocation with assertions enabled required")
    if read(BASE / "real-scan/validation-001/result.json")["status"] != "PASS":
        raise ValueError("Protected real-scan validation must pass")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), OUTPUT / "consumer.py")
    dossier = read(ROOT / "docs/implementation/prospectus-closure-2026-10-05/dossier-review.json")
    manifest, manifest_hash = retained_search_manifest()
    review, template, graph, selected = prior_consumer.review_and_graph()
    dispositions, disposition_hash = build_dispositions(graph, manifest, manifest_hash, dossier)
    applicability_review, applicability_hash = applicability(graph)
    by_id = {row["id"]: row for row in dispositions["rows"]}
    for dep in template["bundle"]["dependencies"]:
        if dep["id"] not in by_id:
            continue
        row = by_id[dep["id"]]
        dep.update({
            "expected_date": row["expected_date"],
            "expected_issuer": row["expected_issuer"],
            "expected_scope": row["expected_scope"],
            "candidate_paths": row["candidate_paths"],
            "original_bytes_sha256": row["original_bytes_sha256"],
            "acquisition_status": row["acquisition_status"],
            "authenticity_status": row["authenticity_status"],
            "disposition": row["disposition"],
            "disposition_sha256": disposition_hash,
        })
    req = prior_consumer.request_for(review, template, graph, selected)
    req, edges = add_onward_edges(req, graph)
    baseline = json.load(gzip.open(COMPARATOR, "rt", encoding="utf-8"))
    started = {
        "version": "bes-onward-source-consumer.v2",
        "command": ["timeout", "1200", ".venv/bin/python", str(Path(__file__).relative_to(ROOT))],
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "plan": str(PLAN.relative_to(ROOT)),
        "environment": {"python": sys.executable, "CUDA_VISIBLE_DEVICES": "-1"},
        "cpu_gpu": "CPU; GPU intentionally hidden; no OCR rerun",
        "comparator": {"path": str(COMPARATOR.relative_to(ROOT)), "sha256": sha(COMPARATOR)},
        "documents": [d["id"] for d in template["bundle"]["documents"]],
        "source_disposition_sha256": disposition_hash,
        "applicability_sha256": applicability_hash,
        "resource_bound_seconds": 1200,
    }
    started["consumer_source_sha256"] = sha(Path(__file__))
    started["attempt"] = "attempt-002"
    write(OUTPUT / "started.json", started)
    tick = time.monotonic()
    try:
        write(OUTPUT / "request.json", req)
        full = service.assess(req, ROOT)
        write_gzip(OUTPUT / "report.json.gz", full)
        if len(full["source_map"]["documents"]) != 8 or full["source_map"]["units"] != baseline["source_map"]["units"]:
            raise ValueError("Actual report changed the retained eight-document source map")
        if {k: v["status"] for k, v in full["questions"].items()} != {k: v["status"] for k, v in baseline["questions"].items()}:
            raise ValueError("Onward applicability passages changed question statuses")
        if full["mode"] != "ASSISTED" or full["independent_legal_acceptance"]:
            raise ValueError("Assistance or independent-acceptance boundary changed")
        source_edges = [d for d in full["dependencies"] if d["id"].startswith("governing:source-chain-")]
        onward_edges = [d for d in full["dependencies"] if d["id"].startswith("governing:onward-")]
        missing = [d for d in full["dependencies"] if d["id"] in by_id]
        if len(source_edges) != 14 or any(d["status"] != "RESOLVED" for d in source_edges):
            raise ValueError("Earlier seven source-chain edges were not preserved")
        if len(onward_edges) != 8 or any(d["status"] != "RESOLVED" for d in onward_edges):
            raise ValueError("New onward applicability edges did not resolve")
        if len(missing) != 14 or any(d["status"] != "UNRESOLVED" or d.get("disposition") != "UNRESOLVED" for d in missing):
            raise ValueError("Missing onward documents were promoted")
        omission_checks = []
        omission_units = {
            "onward-agency-precedence": "bes-base-2010:p76:l43",
            "onward-portuguese-law-forum-representative": "bes-base-2010:p112:l6",
            "onward-book-entry": "bes-base-2010:p112:l43",
            "onward-generic-icsd-safekeeper": "bes-base-2010:p75:l53",
        }
        for edge_id, unit in omission_units.items():
            changed = service.assess(omission_variant(req, next(e for e in edges if e["id"] == edge_id), unit), ROOT)
            unresolved = [d["id"] for d in changed["dependencies"] if d["id"].startswith("governing:" + edge_id + ":") and d["status"] == "UNRESOLVED"]
            if len(unresolved) != 2:
                raise ValueError("Omitted onward representative remained resolved: " + edge_id)
            omission_checks.append({"edge": edge_id, "omitted_unit": unit, "omitted_parent": unit_by_id(graph, unit).get("parent"), "unresolved": unresolved})
        adverse = {}
        wrong_edition = deepcopy(req)
        wrong_edition["layout_admission"]["governing"][0]["to"][0]["source_sha256"] = "0" * 64
        adverse["wrong-edition"] = expect_rejection(wrong_edition, "Source edition mismatch")
        wrong_date = deepcopy(req)
        wrong_date["bundle"]["documents"] = [dict(d) for d in wrong_date["bundle"]["documents"]]
        for document in wrong_date["bundle"]["documents"]:
            if document["id"] == "bes-base-2010":
                document["valid_until"] = "2011-07-15T00:00:00Z"
        adverse["wrong-date"] = expect_rejection(wrong_date, "Corrected-text source graph changed")
        checks = {"onward_omissions": omission_checks, "adverse_controls": adverse}
        write(OUTPUT / "checks.json", checks)
        result = {
            "status": "PASS",
            "documents_consumed": 8,
            "retained_source_units": len(full["source_map"]["units"]),
            "prior_source_chain_edges": 7,
            "new_applicability_edges": 4,
            "new_applicability_dependencies": 8,
            "unresolved_onward_documents": 14,
            "disposition_rows": len(dispositions["rows"]),
            "original_onward_bytes_bound": False,
            "source_map_equal_to_comparator": True,
            "question_statuses": {k: v["status"] for k, v in full["questions"].items()},
            "onward_omission_controls": len(omission_checks),
            "adverse_controls": len(adverse),
            "categories_kept_separate": [row["category"] for row in applicability_review["rows"]],
            "independent_acceptance": "NOT_ESTABLISHED",
            "legal_completion": "NOT_ESTABLISHED",
            "source_authenticity": "CONDITIONAL_ON_RETAINED_ACQUISITION",
            "scope": "Retained-source disposition and agency applicability passages; absent agreements and financial records remain unresolved",
            "wall_seconds": time.monotonic() - tick,
        }
    except Exception as exc:
        result = {"status": "FAIL", "error": type(exc).__name__ + ": " + str(exc), "wall_seconds": time.monotonic() - tick}
        write(OUTPUT / "result.json", result)
        raise
    write(OUTPUT / "result.json", result)
    files = {
        str(path.relative_to(OUTPUT)): sha(path)
        for path in OUTPUT.rglob("*")
        if path.is_file()
        and path.name != "manifest.json"
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    payload = sum((OUTPUT / name).stat().st_size for name in files)
    if payload + 1_048_576 > 100_000_000:
        raise ValueError("Onward-source evidence cap exceeded")
    write(OUTPUT / "manifest.json", {"files": files, "payload_bytes": payload, "evidence_limit_bytes": 100_000_000})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
