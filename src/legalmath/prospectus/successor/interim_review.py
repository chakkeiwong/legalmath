"""Source consistency for the inspected English BES interim-review form.

This finite form preserves literal moderate assurance. It neither authenticates
a report nor equates assurance terminology across standards or jurisdictions.
Other forms remain incomplete when supplied as this category.
"""
from datetime import date
import re

PROFILE = "bes-english-interim-review.v1"
KIND = "LIMITED_FINANCIAL_REVIEW"
SUBJECT = "INTERIM_CONSOLIDATED_FINANCIAL_INFORMATION"
_MONTHS = {name: i for i, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"), 1)}
_DATE = r"(?P<day>\d{1,2}) (?P<month>" + "|".join(_MONTHS) + r") (?P<year>\d{4})"
_DATES = re.compile(_DATE)
_HEADER = re.compile(
    r"\A\s*(?:BANCO ESPÍRITO SANTO[ \t]*\n)?"
    r"(?P<title>LIMITED REVIEW REPORT)[ \t]*\n"
    r"ON INTERIM CONSOLIDATED FINANCIAL INFORMATION[ \t]*\n"
    r"ISSUED BY THE CMVM REGISTERED AUDITOR[ \t]*\n")
_HEADINGS = re.compile(r"^(Introduction|Responsibilities|Scope|Conclusion)[ \t]*$", re.M)
_CLOSING = re.compile(
    r"^Lisbon, (?P<date>" + _DATE + r")[ \t]*\n"
    r"KPMG & Associados, SROC, S\.A\.[ \t]*(?=\n|$)", re.M)


def _phrase(words):
    """Allow retained line breaks without discarding source offsets."""
    return re.compile(r"\s+".join(re.escape(word) for word in words.split()))


# Conservative, reviewed wording of the inspected form. Other procedures or
# added qualifications need review instead of inheriting this form's support.
_SCOPE = _phrase(
    "The work that we have performed was conducted with the objective of obtaining a moderate "
    "level of assurance that the financial information mentioned above is free of material "
    "misstatements. Our work was performed based on the technical standards and review/audit "
    "guidelines issued by the ‘Ordem dos Revisores Oficiais de Contas’ (the Portuguese Institute of "
    "Chartered Accountants), and planned in accordance with that objective and included the "
    "following procedures: 5. a) mainly, inquiries and analytical procedures performed to review: "
    "• the reliability of the assertions included in the interim consolidated financial information; "
    "• the adequacy of the accounting policies adopted, considering the circumstances and the "
    "consistency of their application; • the application of the going concern principle; "
    "• the presentation of the interim consolidated financial information; "
    "• if the interim consolidated financial information is complete, true, current, clear, "
    "objective and lawful; and b) substantive tests on material non current transactions. "
    "6. Our review also included the verification that the interim consolidated financial information "
    "contained in interim the Report of the Board of Directors is consistent with the remaining "
    "documents mentioned above. 7. We believe that our work provides a reasonable basis to issue "
    "our report on the interim consolidated financial information.")


def _covered(fact, text, start, end):
    return fact["status"] == "SUPPLIED" and all(
        c.isspace() or any(s["start"] <= i < s["end"] for s in fact["spans"])
        for i, c in enumerate(text[start:end], start))


def _span(reading, start, end):
    return {"start": start, "end": end, "quote": reading["text"][start:end],
            "source_characters": [c for c in reading["characters"] if start <= c["output"] < end]}


def _structure(text):
    """Recognize complete, ordered sections, not incidental words elsewhere."""
    header = _HEADER.match(text)
    headings = list(_HEADINGS.finditer(text))
    closing = list(_CLOSING.finditer(text))
    if (not header or [h[1] for h in headings] !=
            ["Introduction", "Responsibilities", "Scope", "Conclusion"] or
            text[header.end():headings[0].start()].strip() or len(closing) != 1 or
            closing[0].start() <= headings[-1].end()):
        return None
    intro, responsibilities, scope, conclusion = headings
    end = closing[0]
    try:
        normalized = date(int(end["year"]), _MONTHS[end["month"]], int(end["day"])).isoformat()
    except ValueError:
        return None
    # Keep the whole paragraph about issuer, period and statements. A title
    # alone cannot substitute for this subject description.
    subject = re.search(r"\s*1\.\s*\n(?P<body>[\s\S]+?)\n2\.\s*\n",
                        text[intro.end():responsibilities.start()])
    if not subject or not _phrase("interim consolidated financial information for the six-months period ended").search(subject["body"]):
        return None
    criteria = re.search(
        r"^b\)[ \t]*(?P<body>[\s\S]+?);\s*\nc\)",
        text[responsibilities.end():scope.start()], re.M)
    if (not criteria or not _phrase(
            "maintaining historical financial information, prepared in accordance with "
            "IAS 34 - Interim Financial Reporting which is complete, true, current, clear, "
            "objective and lawful as required by the CVM").fullmatch(criteria["body"])):
        return None
    scope_text = text[scope.end():conclusion.start()]
    scope_assurance = _phrase("objective of obtaining a moderate level of assurance").search(scope_text)
    if not scope_assurance or not _SCOPE.fullmatch(scope_text.strip()):
        return None
    conclusion_text = text[conclusion.end():end.start()]
    negative = _phrase(
        "Based on our review, which was performed with the objective of obtaining moderate assurance, "
        "nothing has come to our attention that causes us to believe that the interim consolidated "
        "financial information for the six-months period ended")
    body = re.fullmatch(r"\s*8\.\s*\n(?P<body>[\s\S]+?)\s*", conclusion_text)
    if (not body or not negative.match(body["body"]) or not _phrase(
            "is not free of material misstatements that affects its compliance with the "
            "IAS 34 - Interim Financial Reporting and that is not complete, true, current, "
            "clear, objective and lawful.").search(body["body"])):
        return None
    # A qualifier appended to the inspected conclusion is not silently omitted.
    expected = negative.pattern + r"\s+" + _DATES.pattern + r",\s+" + _phrase(
        "is not free of material misstatements that affects its compliance with the "
        "IAS 34 - Interim Financial Reporting and that is not complete, true, current, "
        "clear, objective and lawful.").pattern
    if not re.fullmatch(expected, body["body"]):
        return None
    conclusion_assurance = _phrase("objective of obtaining moderate assurance").search(conclusion_text)
    return {
        "identity": [header.span("title")],
        "subject": [(intro.end() + subject.start("body"), intro.end() + subject.end("body"))],
        "criteria": [(responsibilities.end() + criteria.start("body"),
                      responsibilities.end() + criteria.end("body") + 1)],
        "assurance_level": [
            (scope.end() + scope_assurance.start(), scope.end() + scope_assurance.end()),
            (conclusion.end() + conclusion_assurance.start(), conclusion.end() + conclusion_assurance.end())],
        "purpose": [(scope.end(), conclusion.start())],
        "conclusion": [(conclusion.end() + body.start("body"), conclusion.end() + body.end("body"))],
        "report_date": [end.span("date")],
        "normalized_date": normalized,
    }


def check(reading, facts):
    """Refuse known false labels; withhold new-profile support if evidence lacks."""
    text = reading["text"]
    required = _structure(text)
    kind = facts["identity"].get("value")
    if required:
        if kind is not None and kind != KIND:
            raise ValueError("Source interim review contradicts supplied report category")
        for field, expected in (("assurance_level", "MODERATE"), ("conclusion", "NEGATIVE_ASSURANCE")):
            if facts[field]["status"] == "SUPPLIED" and facts[field]["value"] != expected:
                raise ValueError("Source interim review contradicts supplied " + field)
    # Applicability must survive failure of the stricter positive matcher.
    # A qualification or damaged extraction cannot turn this source into
    # a different report category merely through supplied codes.
    known_source = (reading.get('source_sha256') ==
        'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
        and any(p.get('page') in {172, 173} for p in reading.get('pages', [])))
    interim_title = re.search(r'^LIMITED REVIEW REPORT[ \t]*$', text, re.M) is not None
    if kind != KIND and not known_source and not interim_title:
        return None
    if required is None:
        return {"profile": PROFILE, "status": "UNRECOGNIZED_OR_INCOMPLETE_SOURCE_STRUCTURE",
                "unresolved_fields": ["source_structure"], "checks": {},
                "general_semantic_truth_established": False}
    checks = {}
    for field, intervals in required.items():
        if field == "normalized_date":
            continue
        consistent = all(_covered(facts[field], text, a, b) for a, b in intervals)
        status = "REQUIRED_SOURCE_LANGUAGE_RETAINED" if consistent else "REQUIRED_SOURCE_LANGUAGE_NOT_SUPPLIED"
        if field == "report_date" and consistent:
            a, b = intervals[0]
            if any(m.span() != (a, b) and any(s["start"] < m.end() and m.start() < s["end"]
                   for s in facts[field]["spans"]) for m in _DATES.finditer(text)):
                consistent, status = False, "REPORT_DATE_QUOTES_COMPETING_EVENTS"
        checks[field] = {"consistent": consistent, "status": status,
                         "required_spans": [_span(reading, a, b) for a, b in intervals]}
    unresolved = sorted(field for field, value in checks.items() if not value["consistent"])
    return {"profile": PROFILE, "status": "SOURCE_CONSISTENT" if not unresolved else "INCOMPLETE_SOURCE_READING",
            "checks": checks, "normalized_closing_date": required["normalized_date"],
            "unresolved_fields": unresolved, "general_semantic_truth_established": False}
