"""Issue-bound source admission and dependency decisions; no legal certification."""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from .common import digest
from .loss_absorption_reader import load_document
from ..transaction.evidence import instant

ROLES = {"agent", "independent_adjudicator", "human_legal_reviewer"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_binding(meta):
    # Metadata includes edition, origin, extraction and any discovered amendment.
    return digest(meta)


def assessment(effective_at, known_at):
    instant(effective_at)
    instant(known_at)
    return {"effective_at": effective_at, "known_at": known_at}


def reviewer(value):
    require(isinstance(value, dict) and value.get("role") in ROLES and
            isinstance(value.get("name"), str) and value["name"].strip(), "Identified reviewer and role required")


def check_quote(anchor, documents, root):
    require(isinstance(anchor, dict) and anchor.get("document") in documents, "Unknown quote document")
    meta = documents[anchor["document"]]
    require(anchor.get("source_binding") == source_binding(meta), "Stale quote source binding")
    pages = load_document(meta, root)["pages"]
    page = anchor.get("page")
    require(type(page) is int and 1 <= page <= len(pages), "Invalid quote page")
    text = pages[page - 1]["text"]
    quote = anchor.get("quote")
    require(isinstance(quote, str) and quote.strip() and quote in text, "Quote absent from exact extracted page")
    return page


def admission(review, issue, documents, root, dates):
    """Validate the recorded review's bindings, not the reviewer's legal judgment."""
    key = review.get("document")
    require(key in documents, "Admission document absent")
    meta = documents[key]
    require(review.get("issue_id") == issue["id"] and review.get("issue_binding") == digest(issue),
            "Wrong issue, selection or newly discovered dependency")
    require(review.get("source_binding") == source_binding(meta), "Changed source edition or derivative")
    require(review.get("assessment") == dates, "Assessment dates changed")
    reviewer(review.get("reviewer"))
    reviewed = instant(review["reviewed_at"])
    require(reviewed <= instant(dates["known_at"]), "Review not known at assessment time")
    require(review.get("stage") in {"final", "executed"}, "Document stage not established")
    if review.get("execution_required"):
        require(review["stage"] == "executed", "Executed document required")
    for name in ("edition", "option", "controlling_language", "precedence", "amendment_scope", "scope"):
        require(isinstance(review.get(name), str) and review[name].strip(), "Missing review field: " + name)
    cutoff = instant(review["amendment_cutoff"])
    require(instant(dates["effective_at"]) <= cutoff <= instant(dates["known_at"]),
            "Amendment cutoff does not cover assessment or claims future knowledge")
    provenance = review.get("provenance", {})
    require(provenance.get("kind") in {"official_retrieval", "supplied"}, "Actual source provenance required")
    require(instant(provenance["observed_at"]) <= instant(dates["known_at"]), "Source not yet observed")
    require(provenance.get("evidence"), "Provenance evidence required")
    for proof in provenance["evidence"]:
        retained = (Path(root) / proof["path"]).resolve()
        require(retained.is_relative_to(Path(root).resolve()), "Provenance path escapes checkout")
        from .master_control import sha
        require(retained.is_file() and sha(retained) == proof["sha256"], "Changed provenance evidence")
    pages = load_document(meta, root)["pages"]
    scope = review.get("reviewed_pages")
    require(isinstance(scope, list) and scope and all(type(p) is int and 1 <= p <= len(pages) for p in scope)
            and len(scope) == len(set(scope)), "Unique valid reviewed pages required")
    selected = next((s for s in issue["documents"] if s["id"] == key), None)
    needed = set(range(1, len(pages) + 1)) if selected is None else {
        p for a, b in selected.get("operative_pages", [[1, len(pages)]]) for p in range(a, b + 1)}
    require(needed <= set(scope), "Decisive operative pages are not all reviewed")
    omission = review.get("omission_check", {})
    require(omission.get("page_hashes") == [digest(p["text"]) for p in pages] and
            omission.get("reason") and omission.get("verdict") == "PASS", "Document-wide omission check missing or stale")
    visual = review.get("page_reviews", [])
    require(len(visual) == len(scope) and {r.get("page") for r in visual} == set(scope),
            "Each scope page needs its own fidelity review")
    from .master_control import sha
    for row in visual:
        require(row.get("text_sha256") == digest(pages[row["page"] - 1]["text"]) and
                row.get("verdict") == "PASS" and row.get("reason"), "Unverified or stale page extraction")
        render = (Path(root) / row["render_path"]).resolve()
        require(render.is_relative_to(Path(root).resolve()) and render.is_file() and
                sha(render) == row.get("render_sha256"), "Missing or changed rendered page")
    findings = review.get("findings", {})
    for name in ("edition", "stage", "option", "language", "precedence", "amendments"):
        require(findings.get(name, {}).get("reason") and findings[name].get("anchors"),
                "Source-bound finding required: " + name)
        for anchor in findings[name]["anchors"]:
            check_quote(anchor, documents, root)
    return {"document": key, "review_sha256": digest(review), "reviewer_role": review["reviewer"]["role"],
            "status": "ADMITTED_UNDER_RECORDED_REVIEW", "human_acceptance": False}


def packet_binding(packet, issue, dates):
    return digest({"issue": issue, "references": packet["references"], "bindings": packet["bindings"], "assessment": dates})


def resolve(packet, issue, documents, root, dates, admissions=(), decisions=()):
    """Resolve each recorded candidate separately; unknown and stale decisions stay open."""
    require(packet["issue_id"] == issue["id"], "Packet belongs to another issue")
    assessment(**dates)
    refs = {row["id"]: row for row in packet["references"]}
    require(len(refs) == len(packet["references"]), "Duplicate reference identity")
    relevant = [r for r in admissions if r.get("issue_id") == issue["id"]]
    admitted, problems = {}, {}
    counts = Counter(r.get("document") for r in relevant)
    for row in relevant:
        key = row.get("document")
        try:
            require(counts[key] == 1, "Conflicting/duplicate admission reviews")
            admitted[key] = admission(row, issue, documents, root, dates)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            problems[key] = str(exc)
    chosen, duplicate = {}, set()
    for row in decisions:
        if row.get("issue_id") != issue["id"]:
            continue
        key = row.get("reference_id")
        if key in chosen:
            duplicate.add(key)
        chosen[key] = row
    # A decision pointing at a retired/unknown reference never transfers by similarity.
    orphaned = sorted(str(k) for k in chosen if k not in refs)
    active, results = set(), {}
    bound = packet_binding(packet, issue, dates)

    def visit(key):
        if key in active:
            raise ValueError("Unsupported dependency cycle")
        if key in results:
            return results[key]
        base = {"reference_id": key, "issue_id": issue["id"], "status": "OPEN", "reason": "No current decision"}
        row = chosen.get(key)
        if row is None:
            results[key] = base
            return base
        active.add(key)
        try:
            require(key in refs and key not in duplicate, "Unknown or duplicate reference decision")
            require(row.get("packet_binding") == bound and row.get("reference_binding") == digest(refs[key]),
                    "Reference, issue, dependency set or assessment changed")
            reviewer(row.get("reviewer"))
            require(instant(row["reviewed_at"]) <= instant(dates["known_at"]), "Decision not yet known")
            require(row.get("disposition") in {"SATISFIED", "INAPPLICABLE"} and row.get("reason"),
                    "Explicit reviewed disposition and reason required")
            require(row.get("admission_bindings"), "Decision needs admitted source evidence")
            for doc, expected in row["admission_bindings"].items():
                require(doc in admitted and admitted[doc]["review_sha256"] == expected,
                        "Missing, invalid or changed admission: " + doc)
            require(row.get("anchors"), "Decision needs exact source quotes")
            for anchor in row["anchors"]:
                require(anchor.get("document") in row["admission_bindings"], "Quote is not admitted for this decision")
                check_quote(anchor, documents, root)
            dependencies = row.get("dependencies", {})
            require(isinstance(dependencies, dict), "Bound dependency decisions required")
            for dep, expected in dependencies.items():
                require(dep in refs and dep in chosen and digest(chosen[dep]) == expected, "Changed/missing dependency decision")
                require(visit(dep)["status"] != "OPEN", "Dependency remains open")
            base.update(status=row["disposition"] + "_UNDER_RECORDED_REVIEW", reason=row["reason"],
                        decision_sha256=digest(row), reviewer_role=row["reviewer"]["role"])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            base["reason"] = str(exc)
        finally:
            active.remove(key)
        results[key] = base
        return base

    for key in refs:
        visit(key)
    body = {"version": "source-closure.v1", "issue_id": issue["id"], "packet_binding": bound,
            "assessment": dates, "admissions": admitted, "admission_problems": problems,
            "references": [results[key] for key in refs], "orphaned_decisions": orphaned,
            "open_references": sum(r["status"] == "OPEN" for r in results.values()),
            "all_dependencies_found": False, "legal_completeness": "NOT_ESTABLISHED",
            "human_acceptance": False, "may_execute_transaction": False}
    return {**body, "sha256": digest(body)}


def revalidate(prior, *args, **kwargs):
    current = resolve(*args, **kwargs)
    require(prior == current, "Closure inputs or review changed; reopen dependent decisions")
    return current




def candidate_inventory(baseline, bundle, admissions, root, dates):
    """Admit versioned additions without mutating historical documents or decisions."""
    from . import reader_scope
    require(isinstance(bundle, dict) and set(bundle) <= {"documents", "issues"}, "Unexpected source intake fields")
    result = deepcopy(baseline)
    added = bundle.get("documents", {})
    require(isinstance(added, dict), "Document metadata map required")
    for key, meta in added.items():
        require(key not in result["documents"] and meta.get("id") == key, "Use a new document identity for a new edition")
        for field in ("original", "text"):
            path = (Path(root) / meta[field]).resolve()
            require(path.is_relative_to(Path(root).resolve()), "Source path escapes checkout")
        load_document(meta, root)
        result["documents"][key] = deepcopy(meta)
    changes = bundle.get("issues", [])
    require(isinstance(changes, list), "Issue changes must be a list")
    by_id = {i["id"]: i for i in result["issues"]}
    seen = set()
    for entry in changes:
        require(set(entry) == {"id", "before_sha256", "issue", "review"}, "Incomplete issue amendment")
        key, issue, review = entry["id"], entry["issue"], entry["review"]
        require(key in by_id and key not in seen and issue["id"] == key, "Unknown or duplicate issue amendment")
        seen.add(key)
        prior = by_id[key]
        require(digest(prior) == entry["before_sha256"], "Stale issue amendment")
        permitted = {"documents", "unresolved_operative_dependencies", "source_language_qualification", "dependency_boundary"}
        require({k for k in set(prior) | set(issue) if prior.get(k) != issue.get(k)} <= permitted,
                "Source intake cannot change instrument identity")
        reviewer(review.get("reviewer"))
        require(review.get("before_sha256") == digest(prior) and review.get("after_sha256") == digest(issue)
                and review.get("reason") and review.get("anchors"), "Unbound source selection review")
        require(instant(review["reviewed_at"]) <= instant(dates["known_at"]), "Source selection review not yet known")
        for anchor in review["anchors"]:
            check_quote(anchor, result["documents"], root)
        selections = issue["documents"]
        require(selections and len({s["id"] for s in selections}) == len(selections), "Unique selected documents required")
        for selection in selections:
            meta = result["documents"][selection["id"]]
            reader_scope.validate(selection, meta["pages"])
            reviews = [r for r in admissions if r.get("issue_id") == key and r.get("document") == selection["id"]]
            require(len(reviews) == 1, "Changed issue requires one current admission per selected source")
            admission(reviews[0], issue, result["documents"], root, dates)
        by_id[key] = deepcopy(issue)
    # Unselected additions can support reference review, but cannot affect a feature decision.
    result["issues"] = [by_id[i["id"]] for i in baseline["issues"]]
    return result


def apply_fact_intake(request, store, root, bundle, issue_id):
    """Join supplied evidence to the existing typed bank intake; no invented facts."""
    from ..transaction.evidence import Registry
    from .master_control import sha
    require(isinstance(bundle, dict) and set(bundle) <= {"sources", "issues"}, "Unexpected factual intake fields")
    result = deepcopy(request)
    registry = store.json(request["registry_sha256"])
    for entry in bundle.get("sources", []):
        expected = {"id", "path", "sha256", "kind", "origin", "observed_at", "provenance",
                    "effective_from", "effective_until", "fresh_until", "dependencies", "media_type"}
        require(set(entry) == expected, "Incomplete factual source record")
        key = entry["id"]
        require(key not in registry, "Cannot overwrite an existing registry source")
        path = (Path(root) / entry["path"]).resolve()
        require(path.is_relative_to(Path(root).resolve()) and path.is_file() and sha(path) == entry["sha256"],
                "Supplied factual source missing, changed or outside checkout")
        registry[key] = intake_record(store, path.read_bytes(), kind=entry["kind"], origin=entry["origin"],
            observed_at=entry["observed_at"], provenance=entry["provenance"], effective_from=entry["effective_from"],
            effective_until=entry["effective_until"], fresh_until=entry["fresh_until"], dependencies=entry["dependencies"], media_type=entry["media_type"])
    Registry(store, registry)
    result["registry_sha256"] = store.put(registry)
    item = bundle.get("issues", {}).get(issue_id, {})
    require(set(item) <= {"facts", "product_assertions", "context", "route", "policy", "capacity"}, "Unexpected issue intake fields")
    context = item.get("context", {})
    require(set(context) <= {"client_id", "booking_entity_id", "establishment_id"}, "Intake cannot overwrite derived issue or assessment")
    require(all(isinstance(v, str) and v for v in context.values()), "Explicit context identifiers required")
    result["context"].update(context)
    for field in ("facts", "route", "policy"):
        if field in item:
            require(isinstance(item[field], dict), "Structured source-bound assertions required")
            result["context"][field + "_sha256"] = store.put(item[field])
    if "capacity" in item:
        require(item["capacity"] in {"unresolved", "principal", "agent"}, "Unknown capacity")
        result["capacity"] = item["capacity"]
    product = item.get("product_assertions", {})
    require(isinstance(product, dict), "Structured product assertions required")
    return result, store.put(product)


def intake_record(store, source, *, kind, origin, observed_at, provenance, effective_from=None,
                  effective_until=None, fresh_until=None, dependencies=(), media_type="text/plain"):
    """The observation time is mandatory; an assessment time is never a default."""
    from ..transaction.intake import record
    instant(observed_at)
    require(provenance in {"official_retrieval", "supplied", "synthetic"}, "Unknown provenance")
    for value in (effective_from, effective_until, fresh_until):
        if value is not None:
            instant(value)
    require(not (effective_from is not None and effective_until is not None and
                 instant(effective_from) >= instant(effective_until)), "Reversed effective interval")
    return record(store.put(source), kind, origin, observed_at, provenance=provenance, media_type=media_type,
                  effective_from=effective_from, effective_until=effective_until,
                  fresh_until=fresh_until, dependencies=dependencies)
