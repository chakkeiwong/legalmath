"""Supplied report readings and scope; separate from contractual construction.

Source binding checks integrity, not semantic truth or reviewer qualification.
The finite categories below describe reviewed examples, not all assurance law.
"""
from collections import Counter
from copy import deepcopy

from .admissions import review
from .anchors import fields
from .contracts import digest

FACTS = {"identity", "subject", "assurance_level", "criteria", "conclusion", "addressee",
         "purpose", "reliance_limits", "translation_status", "translation_priority", "report_date",
         "publication_date", "historical_availability", "edition_authenticity"}
EXTERNAL = {"publication_date", "historical_availability", "edition_authenticity"}
PROFILES = {
    "STATUTORY_FINANCIAL_AUDIT": {
        "subject": "FINANCIAL_STATEMENTS", "assurance_level": "REASONABLE",
        "conclusion": "AFFIRMATIVE_FINANCIAL_OPINION"},
    "COMMITTEE_REPORT": {
        "subject": "FINANCIAL_STATEMENTS_AND_PROFIT_APPROPRIATION",
        "conclusion": "CONCURRENCE_WITH_AUDITORS"},
    "LIMITED_SUSTAINABILITY_ASSURANCE": {
        "subject": "SUSTAINABILITY_INFORMATION", "assurance_level": "LIMITED",
        "conclusion": "NEGATIVE_ASSURANCE"},
    "LIMITED_FINANCIAL_REVIEW": {
        "subject": "INTERIM_CONSOLIDATED_FINANCIAL_INFORMATION", "assurance_level": "MODERATE",
        "conclusion": "NEGATIVE_ASSURANCE"},
    "UNAUDITED_FINANCIAL_RELEASE": {
        "subject": "CONSOLIDATED_FINANCIAL_RESULTS", "assurance_level": "UNAUDITED"},
}
CODED = {"identity": set(PROFILES),
         **{key: {profile[key] for profile in PROFILES.values() if key in profile}
            for key in ("subject", "assurance_level", "conclusion")}}


def readings(graph, admission):
    """Select whole retained pages, including all margin words, for report reading."""
    keys = {"version", "graph_sha256", "review", "reports"}
    fields(admission, keys, keys)
    if admission["version"] != "source-report-readings.v1" or admission["graph_sha256"] != digest(graph):
        raise ValueError("Report reading source graph changed")
    review(admission["review"])
    if not isinstance(admission["reports"], list) or not admission["reports"]:
        raise ValueError("Nonempty report reading inventory required")
    result, ids = [], set()
    for row in admission["reports"]:
        keys = {"id", "document", "source_sha256", "pages", "text_sha256"}
        fields(row, keys, keys)
        if not isinstance(row["id"], str) or not row["id"] or row["id"] in ids:
            raise ValueError("Distinct report identity required")
        ids.add(row["id"])
        if not isinstance(row["pages"], list) or not row["pages"]:
            raise ValueError("Explicit nonempty report page order required")
        numbers = []
        for page in row["pages"]:
            fields(page, {"page", "mode", "items"}, {"page", "mode"})
            if type(page["page"]) is not int or page["page"] < 1:
                raise ValueError("Positive source page required")
            if page["mode"] == "raw":
                fields(page, {"page", "mode"}, {"page", "mode"})
            elif page["mode"] == "layout":
                if (not isinstance(page.get("items"), list) or not page["items"] or
                        any(not isinstance(item, str) for item in page["items"]) or
                        len(set(page["items"])) != len(page["items"])):
                    raise ValueError("Distinct supplied region order required")
            else:
                raise ValueError("Unsupported report page reading mode")
            numbers.append(page["page"])
        if numbers != sorted(set(numbers)):
            raise ValueError("Report pages must be unique in source order")
        units = [u for u in graph["units"] if u["document"] == row["document"]
                 and u["page"] in numbers and u["visible"]]
        by_id = {u["id"]: u for u in units}
        if not units or len(by_id) != len(units) or any(u["source_sha256"] != row["source_sha256"] for u in units):
            raise ValueError("Report source edition or occurrence identity changed")
        chunks, characters, offset = [], [], 0
        for page in row["pages"]:
            page_units = [u for u in units if u["page"] == page["page"]]
            if not page_units:
                raise ValueError("Selected report page unavailable")
            if page["mode"] == "raw":
                parts = [{"text": u["raw"], "characters": [
                    {"output": i, "unit": u["id"], "source_offset": i, "character": c}
                    for i, c in enumerate(u["raw"])]} for u in page_units]
            else:
                projections = [p for p in graph.get("layout", {}).get("projections", [])
                               if p["document"] == row["document"]]
                if len(projections) != 1 or projections[0].get("failures"):
                    raise ValueError("Unique successful P1 layout projection required")
                mappings = [m for m in projections[0]["mappings"] if m["page"] == page["page"]]
                indexed = {m["item"]: m for m in mappings}
                if len(indexed) != len(mappings) or set(page["items"]) - set(indexed):
                    raise ValueError("Report region unavailable or ambiguous")
                parts = [indexed[item] for item in page["items"]]
            for part in parts:
                if chunks:
                    offset += 1
                seen = set()
                for char in part["characters"]:
                    out, position = char["output"], char["source_offset"]
                    unit = by_id.get(char["unit"])
                    if (type(out) is not int or type(position) is not int or unit is None or
                            unit["page"] != page["page"] or not 0 <= out < len(part["text"]) or
                            not 0 <= position < len(unit["raw"]) or out in seen or
                            char["character"] != part["text"][out] or
                            char["character"] != unit["raw"][position]):
                        raise ValueError("Report source character map changed")
                    seen.add(out)
                    characters.append({**char, "output": out + offset})
                if any(i not in seen for i, char in enumerate(part["text"]) if not char.isspace()):
                    raise ValueError("Unmapped report reading character")
                chunks.append(part["text"])
                offset += len(part["text"])
        text = "\n".join(chunks)
        expected = Counter((u["id"], i) for u in units for i, c in enumerate(u["raw"]) if not c.isspace())
        actual = Counter((c["unit"], c["source_offset"]) for c in characters if not c["character"].isspace())
        if expected != actual:
            raise ValueError("Report reading must retain every selected source word character exactly once")
        if row["text_sha256"] != digest(text.encode()):
            raise ValueError("Reviewed report text or region order changed")
        body = {"id": row["id"], "document": row["document"], "source_sha256": row["source_sha256"],
                "pages": deepcopy(row["pages"]), "text": text, "characters": characters,
                "coverage": "All nonspace characters of selected retained visible P1 units exactly once"}
        result.append({**body, "sha256": digest(body)})
    return {"version": "admitted-report-readings.v1", "graph_sha256": digest(graph),
            "input_sha256": digest(admission), "review": deepcopy(admission["review"]), "reports": result}


def admit(selected, admission):
    """Bind supplied semantics to exact P2 report spans; retain unknowns explicitly."""
    keys = {"version", "readings_sha256", "review", "reports"}
    fields(admission, keys | {"context_profile"}, keys)
    from .report_context import SUPPORTED_PROFILES, check
    contextual = admission["version"] == "source-report-scope.v2"
    if contextual:
        if (not isinstance(admission.get("context_profile"), str) or
                admission["context_profile"] not in SUPPORTED_PROFILES):
            raise ValueError("Explicit supported report context profile required")
    elif "context_profile" in admission:
        raise ValueError("Report context profile requires source-report-scope.v2")
    if (not selected or selected.get("version") != "admitted-report-readings.v1" or
            admission["version"] not in ("source-report-scope.v1", "source-report-scope.v2") or
            admission["readings_sha256"] != digest(selected)):
        raise ValueError("Source-report readings changed or unavailable")
    review(admission["review"])
    readings_by_id = {r["id"]: r for r in selected["reports"]}
    if not isinstance(admission["reports"], list):
        raise ValueError("Report scope inventory required")
    ids, reports = set(), []
    for row in admission["reports"]:
        fields(row, {"id", "reading_sha256", "facts"}, {"id", "reading_sha256", "facts"})
        reading = readings_by_id.get(row["id"])
        if reading is None or row["id"] in ids or row["reading_sha256"] != reading["sha256"]:
            raise ValueError("Report scope reading identity changed")
        if reading["sha256"] != digest({k: v for k, v in reading.items() if k != "sha256"}):
            raise ValueError("Report reading content changed")
        ids.add(row["id"])
        fields(row["facts"], FACTS, FACTS)
        facts = {}
        for name, fact in row["facts"].items():
            fields(fact, {"status", "spans", "value", "reason"}, {"status"})
            if fact["status"] == "UNKNOWN":
                fields(fact, {"status", "reason"}, {"status", "reason"})
                if not isinstance(fact["reason"], str) or not fact["reason"].strip():
                    raise ValueError("Unknown report fact requires reason")
                facts[name] = deepcopy(fact)
                continue
            if fact["status"] != "SUPPLIED" or name in EXTERNAL:
                raise ValueError("External source authority/date requires separate evidence; keep UNKNOWN")
            required = {"status", "spans"} | ({"value"} if name in CODED else set())
            fields(fact, required, required)
            if name in CODED and fact["value"] not in CODED[name]:
                raise ValueError("Unsupported reviewed report classification")
            if not isinstance(fact["spans"], list) or not fact["spans"]:
                raise ValueError("Report fact requires exact source spans")
            spans = []
            for span in fact["spans"]:
                fields(span, {"start", "end", "quote"}, {"start", "end", "quote"})
                a, b = span["start"], span["end"]
                if (type(a) is not int or type(b) is not int or
                        not 0 <= a < b <= len(reading["text"]) or
                        reading["text"][a:b] != span["quote"] or not span["quote"].strip()):
                    raise ValueError("Report fact quote or interval changed")
                origins = [c for c in reading["characters"] if a <= c["output"] < b]
                spans.append({**span, "source_characters": origins})
            facts[name] = {**deepcopy(fact), "spans": spans}
        kind = facts["identity"].get("value")
        for name, expected in PROFILES.get(kind, {}).items():
            if facts[name]["status"] == "SUPPLIED" and facts[name]["value"] != expected:
                raise ValueError("Report category, subject, assurance and conclusion disagree")
        if kind == "COMMITTEE_REPORT" and facts["assurance_level"]["status"] != "UNKNOWN":
            raise ValueError("Committee concurrence does not supply its own assurance level")
        from .interim_review import check as check_interim_review
        interim = check_interim_review(reading, facts)
        from .unaudited_release import check as check_unaudited_release
        release = check_unaudited_release(reading, facts)
        from .english_report_context import check as check_english_report
        english = check_english_report(reading, facts)
        reports.append({"id": row["id"], "reading_sha256": reading["sha256"],
                        "document": reading["document"], "source_sha256": reading["source_sha256"],
                        "facts": facts, **({"context_review": check(reading, facts, admission["context_profile"])} if contextual else {}),
                        **({"interim_review_context": interim} if interim else {}),
                        **({"unaudited_release_context": release} if release else {}),
                        **({"english_report_context": english} if english else {})})
    if ids != set(readings_by_id):
        raise ValueError("Every selected report needs a scope record, including unknown facts")
    return {"version": "admitted-report-scope.v2" if contextual else "admitted-report-scope.v1",
            "readings_sha256": digest(selected), "input_sha256": digest(admission),
            "review": deepcopy(admission["review"]), "reports": reports,
            **({"context_profile": admission["context_profile"]} if contextual else {})}


def explain(scopes):
    """Answer report-use questions from admitted evidence, not debt-clause roles."""
    explanations = {
        "STATUTORY_FINANCIAL_AUDIT": "The supplied reading gives an affirmative opinion on the stated financial statements, subject to its accounting criteria and materiality wording.",
        "COMMITTEE_REPORT": "The committee concurs with the statutory auditors' opinions; this is the committee's report and does not supply a separate statutory audit opinion.",
        "LIMITED_SUSTAINABILITY_ASSURANCE": "The supplied reading concerns sustainability information with limited assurance, a negative-assurance conclusion and express purpose and third-party limits.",
        "LIMITED_FINANCIAL_REVIEW": "The supplied report reviews interim consolidated financial information with the source's stated moderate assurance and a negative-assurance conclusion, subject to its IAS 34 and CVM wording and described review procedures.",
        "UNAUDITED_FINANCIAL_RELEASE": "The issuer's release describes consolidated financial results as unaudited under IFRS as implemented by the European Union. Its printed release date and qualification are retained; this reading establishes no audit opinion or independent assurance conclusion.",
    }
    result = []
    for report in scopes["reports"]:
        facts = report["facts"]
        kind = facts["identity"].get("value")
        essential = {"identity", "subject", "conclusion", "report_date"}
        if kind in {"STATUTORY_FINANCIAL_AUDIT", "LIMITED_SUSTAINABILITY_ASSURANCE"}:
            essential |= {"criteria", "assurance_level"}
        if kind == "LIMITED_SUSTAINABILITY_ASSURANCE":
            essential |= {"addressee", "purpose", "reliance_limits"}
        if kind == "LIMITED_FINANCIAL_REVIEW":
            essential |= {"criteria", "assurance_level", "purpose"}
        if kind == "UNAUDITED_FINANCIAL_RELEASE":
            essential = {"identity", "subject", "assurance_level", "criteria", "report_date"}
        missing = sorted(name for name in essential if facts[name]["status"] == "UNKNOWN")
        context = report.get("context_review")
        context_missing = context["unresolved_fields"] if context else []
        interim = report.get("interim_review_context")
        interim_missing = interim["unresolved_fields"] if interim else []
        if kind == "LIMITED_FINANCIAL_REVIEW" and interim is None:
            interim_missing = ["source_structure"]
        release = report.get("unaudited_release_context")
        release_missing = release["unresolved_fields"] if release else []
        if kind == "UNAUDITED_FINANCIAL_RELEASE" and release is None:
            release_missing = ["source_header"]
        english = report.get("english_report_context")
        english_missing = english["unresolved_fields"] if english else []
        ready = not missing and not context_missing and not interim_missing and not release_missing and not english_missing and kind in PROFILES
        explanation = explanations[kind] if ready else "Essential report facts or qualifications remain unknown; no complete scope finding is available."
        if context_missing:
            explanation = "The supplied facts conflict with, or omit, required report context; no complete scope finding is available."
        if interim_missing:
            explanation = "The supplied interim-review facts omit required source language or the complete reviewed report structure; no complete scope finding is available."
        if release_missing:
            explanation = "The supplied issuer-release facts omit required header language or its reviewed source form; no complete release reading is available."
        if english_missing:
            explanation = "The supplied English report facts omit required context or do not match the complete inspected reading; no complete scope finding is available."
        result.append({"id": report["id"], "document": report["document"],
            "reading_sha256": report["reading_sha256"],
            "status": "CONDITIONAL_SUPPLIED_READING" if ready else "INCOMPLETE_SOURCE_READING",
            "explanation": explanation,
            "use_assessment": {
                "financial_statement_audit_opinion": "SUPPLIED_SOURCE_SUPPORT" if ready and kind == "STATUTORY_FINANCIAL_AUDIT" else "NOT_ESTABLISHED_BY_THIS_READING",
                "committee_concurrence": "SUPPLIED_SOURCE_SUPPORT" if ready and kind == "COMMITTEE_REPORT" else "NOT_ESTABLISHED_BY_THIS_READING",
                "limited_sustainability_assurance": "SUPPLIED_SOURCE_SUPPORT" if ready and kind == "LIMITED_SUSTAINABILITY_ASSURANCE" else "NOT_ESTABLISHED_BY_THIS_READING",
                "unrestricted_third_party_reliance": "EXPRESS_LIMIT_RETAINED" if facts["reliance_limits"]["status"] == "SUPPLIED" else "NOT_ESTABLISHED_BY_THIS_READING",
                "bond_repayment_or_conversion": "NOT_ESTABLISHED_BY_THIS_READING",
                "historical_availability": "NOT_ESTABLISHED_BY_THIS_READING"},
            "facts": deepcopy(facts), "missing_essential_facts": missing,
            "unresolved": sorted(name for name, fact in facts.items() if fact["status"] == "UNKNOWN"),
            "independent_legal_acceptance": False,
            **({"context_review": deepcopy(context), "unresolved_context_fields": context_missing} if context else {}),
            **({"interim_review_context": deepcopy(interim),
                "unresolved_interim_review_fields": interim_missing} if interim else {}),
            **({"unaudited_release_context": deepcopy(release),
                "unresolved_unaudited_release_fields": release_missing} if release else {}),
            **({"english_report_context": deepcopy(english),
                "unresolved_english_report_fields": english_missing} if english else {})})
        if kind == "LIMITED_FINANCIAL_REVIEW":
            result[-1]["use_assessment"]["financial_interim_review"] = (
                "SUPPLIED_SOURCE_SUPPORT" if ready else "NOT_ESTABLISHED_BY_THIS_READING")
        if kind == "UNAUDITED_FINANCIAL_RELEASE":
            result[-1]["use_assessment"]["unaudited_financial_release"] = (
                "SUPPLIED_SOURCE_DESCRIPTION" if ready else "NOT_ESTABLISHED_BY_THIS_READING")
    return result
