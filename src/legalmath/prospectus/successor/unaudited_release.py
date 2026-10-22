"""Two inspected English BES release headings; no assurance engagement inferred."""
import re

KIND = "UNAUDITED_FINANCIAL_RELEASE"
PROFILE = "bes-english-fy2010-release.v1"
_TITLE = "BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN 2010"
_QUALIFICATION = "Unaudited financial information under IFRS as implemented by the European Union"
def _header(title, date):
    return re.compile(
        r"\A\s*(?P<identity>MATERIAL EVENT)\s+"
        r"(?P<subject>" + re.escape(title) + r")\s+"
        r"\((?P<criteria>(?P<assurance>Unaudited) financial information under IFRS as implemented by the European Union)\)\s+"
        r"\(BES; Bloomberg: BES PL; Reuters: BES\.LS\)\s+"
        r"(?P<date>" + re.escape(date) + r")(?=\s|$)")


_HEADERS = (
    (PROFILE, '2011-01-31', _header(_TITLE, 'Lisbon, 31 January 2011')),
    ('bes-english-q12011-release.v1', '2011-05-02', _header(
        'BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN 1Q11', 'Lisbon, 2 May 2011')),
)


def _covered(fact, text, start, end):
    return fact["status"] == "SUPPLIED" and all(
        c.isspace() or any(s["start"] <= i < s["end"] for s in fact["spans"])
        for i, c in enumerate(text[start:end], start))


def check(reading, facts):
    text = reading["text"]
    profile, date, header = PROFILE, None, None
    for candidate, printed_date, pattern in _HEADERS:
        match = pattern.match(text)
        if match:
            profile, date, header = candidate, printed_date, match
            break
    kind = facts["identity"].get("value")
    if header:
        if kind is not None and kind != KIND:
            raise ValueError("Unaudited issuer-release heading contradicts supplied report category")
        if facts["assurance_level"]["status"] == "SUPPLIED" and facts["assurance_level"]["value"] != "UNAUDITED":
            raise ValueError("Unaudited issuer-release heading does not supply audit or review assurance")
        if facts["conclusion"]["status"] != "UNKNOWN":
            raise ValueError("Issuer-release profile does not supply an independent opinion conclusion")
    # Incomplete recognized releases must not acquire another report's support.
    known_cover = reading.get("source_sha256") in {
        "b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f",
        "4c7067274ff3eb8f812a8a98d23c4fd2d4b159ed0259f066069b2416ae2e75ec",
    } and any(page.get("page") == 1 for page in reading.get("pages", []))
    release_title = re.search(
        r"^BANCO ESPÍRITO SANTO GROUP ACTIVITY AND RESULTS IN[^\n]*$",
        text, re.M) is not None
    if kind != KIND and not known_cover and not release_title:
        return None
    if kind == KIND and facts["conclusion"]["status"] != "UNKNOWN":
        raise ValueError("Issuer-release profile requires unknown independent opinion conclusion")
    if not header:
        return {"profile": PROFILE, "status": "UNRECOGNIZED_OR_INCOMPLETE_SOURCE_HEADER",
                "checks": {}, "unresolved_fields": ["source_header"],
                "general_semantic_truth_established": False}
    checks = {}
    for field, group in (("identity", "identity"), ("subject", "subject"),
                         ("assurance_level", "assurance"), ("criteria", "criteria"),
                         ("report_date", "date")):
        a, b = header.span(group)
        covered = _covered(facts[field], text, a, b)
        # Date evidence must identify this header occurrence, without importing
        # another date role or a coincidentally identical footer occurrence.
        if field == "report_date" and covered:
            covered = all(not text[s['start']:s['end']].strip() or
                          a <= s['start'] < s['end'] <= b for s in facts[field]['spans'])
        checks[field] = {"consistent": covered,
            "status": "PRINTED_HEADER_LANGUAGE_RETAINED" if covered else "PRINTED_HEADER_LANGUAGE_NOT_SUPPLIED",
            "required_span": {"start": a, "end": b, "quote": text[a:b],
                "source_characters": [c for c in reading["characters"] if a <= c["output"] < b]}}
    unresolved = sorted(k for k, v in checks.items() if not v["consistent"])
    return {"profile": profile, "status": "SOURCE_CONSISTENT" if not unresolved else "INCOMPLETE_SOURCE_READING",
            "checks": checks, "unresolved_fields": unresolved,
            "printed_release_date": date, "publication_date_established": False,
            "independent_opinion_established": False, "general_semantic_truth_established": False}
