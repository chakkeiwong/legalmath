"""Finite context checks for inspected English reports, not general semantics.

Offsets refer to the complete unchanged retained reading, including extraction
noise. A changed extraction requires review; a matching digest is not proof of
source authenticity or of the truth of an auditor's statements.
"""
import re

from .contracts import digest

_AUDIT_CUE = re.compile(r"AUDITORS[’']\s*REPORT\s+CONSOLIDATED\s+FINANCIAL\s+STATEMENTS|"
                        r"REPORT\s+OF\s+THE\s+AUDIT\s+COMMITTEE\s+FOR\s+THE\s+YEAR\s+2010", re.I)
# Unknown source identities still need the inspected context safeguards when a
# whole line identifies an auditor or audit-committee report. This finite guard
# only withholds support; it never admits a new positive source profile. Keep
# the historical cue above intact so existing conservative refusals survive.
_REPORT_HEADING_CUE = re.compile(
    r"^[ \t]*(?:"
    r"(?:STATUTORY[ \t]+)?AUDITOR(?:S[’']?|[’']S)?[ \t]+REPORT"
    r"(?:[ \t]+(?:ON[ \t]+)?(?:THE[ \t]+)?(?:CONSOLIDATED[ \t]+)?FINANCIAL[ \t]+STATEMENTS)?"
    r"|(?:REPORT[ \t]+OF[ \t]+THE[ \t]+AUDIT[ \t]+COMMITTEE|"
    r"AUDIT[ \t]+COMMITTEE(?:[’']S)?[ \t]+REPORT)"
    r"(?:[ \t]+FOR[ \t]+THE[ \t]+YEAR[ \t]+[0-9]{4})?"
    r")[ \t\r]*$", re.I | re.M)
_PROFILES = {
    "c8693010d57558fe5573b3ed72195c1cfe499fbd6db6fa4b8f3a0417695d8e45": {
        "profile": "bes2009-english-statutory-context.v1",
        "source_sha256": "5a8e79459e2109bd43173320af39aa4bc4ee08392746772f3bf7e4ffac8027c8",
        "pages": {174, 175},
        "kind": "STATUTORY_FINANCIAL_AUDIT",
        "normalized_date": "2010-03-04",
        # Title; full paragraph1; scope4–6; accounting/audit/opinion criteria;
        # assurance in paragraph4; whole opinion7; free translation; closing.
        "required": {
            "identity": [(361, 472)],
            "subject": [(573, 1355)],
            "purpose": [(3188, 4832)],
            "criteria": [(1419, 2049), (3191, 3540), (5231, 5410)],
            "assurance_level": [(3425, 3540)],
            "conclusion": [(4844, 5410)],
            "translation_status": [(474, 555)],
            "report_date": [(5411, 5431)],
        },
    },
    "bc002a99b88b3d2ddc215c6e24b7cefa7cf451fe3a28a46f3d58fb047248977f": {
        "profile": "bes2010-english-statutory-context.v1",
        "source_sha256": "f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25",
        "pages": {190},
        "kind": "STATUTORY_FINANCIAL_AUDIT",
        "normalized_date": "2011-03-04",
        "required": {
            "identity": [(60, 171)], "subject": [(341, 1110)],
            "assurance_level": [(2751, 2866)], "purpose": [(2486, 4326)],
            "criteria": [(1174, 1877), (2486, 2866), (4725, 4904)],
            "conclusion": [(4335, 4904), (4940, 5269)],
            "translation_status": [(173, 254)], "report_date": [(5270, 5290)],
        },
        "distinct_source_statements": {
            "financial_statement_opinion": (4335, 4904),
            "other_legal_requirements": (4940, 5269),
        },
    },
    "fe807878866f6106ef0603d19dd3d3ffaebc551cd8d01eaa43050193decd3139": {
        "profile": "bes2010-english-committee-context.v1",
        "source_sha256": "f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25",
        "pages": {191},
        "kind": "COMMITTEE_REPORT",
        "normalized_date": "2011-03-07",
        # The native extractor places the introductory subject at the end.
        # Preserve that complete reading and bind each role explicitly.
        "required": {
            "identity": [(32, 79)], "subject": [(3688, 4225)],
            "addressee": [(80, 130)], "purpose": [(131, 941), (3170, 3615)],
            "conclusion": [(942, 1288), (1575, 2551), (2552, 3020)],
            "report_date": [(3021, 3041)],
        },
        "distinct_source_statements": {
            "auditor_concurrence": (942, 1288),
            "qualified_declaration": (1575, 2551),
            "approval_recommendation": (2552, 3020),
        },
    },
}


def _span(reading, start, end):
    return {"start": start, "end": end, "quote": reading["text"][start:end],
            "source_characters": [c for c in reading["characters"] if start <= c["output"] < end]}


def _covered(fact, text, start, end):
    return fact["status"] == "SUPPLIED" and all(
        c.isspace() or any(s["start"] <= i < s["end"] for s in fact["spans"])
        for i, c in enumerate(text[start:end], start))


def _provenance(reading):
    text = reading["text"]
    seen, origins = set(), set()
    for char in reading["characters"]:
        out, offset, unit = char["output"], char["source_offset"], char["unit"]
        if (type(out) is not int or not 0 <= out < len(text) or out in seen or
                type(offset) is not int or offset < 0 or not isinstance(unit, str) or not unit or
                (unit, offset) in origins or char["character"] != text[out]):
            raise ValueError("English report character provenance changed")
        seen.add(out)
        origins.add((unit, offset))
    if any(i not in seen for i, c in enumerate(text) if not c.isspace()):
        raise ValueError("English report has unmapped source characters")


def check(reading, facts):
    text = reading["text"]
    profile = _PROFILES.get(digest(text.encode()))
    if profile is None:
        known_source = any(reading["source_sha256"] == p["source_sha256"] and
                           bool({page["page"] for page in reading["pages"]} & p["pages"])
                           for p in _PROFILES.values())
        if not known_source and not (_AUDIT_CUE.search(text) or _REPORT_HEADING_CUE.search(text)):
            return None
        return {"profile": "inspected-english-report-context.v1",
                "status": "UNRECOGNIZED_OR_CHANGED_SOURCE_READING",
                "unresolved_fields": ["source_structure"], "checks": {},
                "general_semantic_truth_established": False}
    _provenance(reading)
    kind = facts["identity"].get("value")
    if kind is not None and kind != profile["kind"]:
        raise ValueError("Inspected English report contradicts supplied report category")
    checks = {}
    for field, intervals in profile["required"].items():
        fact = facts[field]
        consistent = all(_covered(fact, text, a, b) for a, b in intervals)
        status = "REQUIRED_SOURCE_LANGUAGE_RETAINED" if consistent else "REQUIRED_SOURCE_LANGUAGE_NOT_SUPPLIED"
        if field == "report_date" and consistent:
            a, b = intervals[0]
            # No competing accounting date or date quoted from another role.
            if any(not c.isspace() and not a <= i < b
                   for s in fact["spans"] for i, c in enumerate(text[s["start"]:s["end"]], s["start"])):
                consistent, status = False, "REPORT_DATE_QUOTES_OTHER_SOURCE_LANGUAGE"
        checks[field] = {"consistent": consistent, "status": status,
                         "required_spans": [_span(reading, a, b) for a, b in intervals]}
    unresolved = sorted(k for k, v in checks.items() if not v["consistent"])
    return {"profile": profile["profile"],
            "status": "SOURCE_CONSISTENT" if not unresolved else "INCOMPLETE_SOURCE_READING",
            "checks": checks, "normalized_closing_date": profile["normalized_date"],
            "unresolved_fields": unresolved, "general_semantic_truth_established": False,
            **({"distinct_source_statements": {name: _span(reading, a, b)
                 for name, (a, b) in profile["distinct_source_statements"].items()}}
               if "distinct_source_statements" in profile else {})}
