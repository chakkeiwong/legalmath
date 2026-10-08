"""Source-bound unpaid-cancellation constructions and condition evaluation.

These are bounded English readings, not findings that a condition occurred.
"""
import re


def find(pattern, text):
    return re.search(pattern, text, re.I | re.S)


def slot(match, kind):
    return {"kind": kind, "start": match.start(), "end": match.end(), "quote": match.group()}


def cancellation_features(text):
    action = find(r"\b(?:such\s+unpaid\s+amounts|any\s+amount\s+outstanding|"
                  r"any\s+amount\s+in\s+respect\s+of\s+principal|"
                  r"(?:the\s+)?unpaid\s+(?:principal|balance|amounts?))\b"
                  r"(?:(?!\b(?:shall|will|must)\b).){0,260}?\b(?:shall|will|must)\s+"
                  r"(?:\([^)]{1,200}\)\s*)?be\s+(?:(?:finally|and|definitively|permanently)\s+)*"
                  r"(?:cancelled|canceled|extinguished|discharged)\b"
                  r"(?:\s+and\s+discharged\s+in\s+full)?", text)
    if not action:
        # Do not silently treat negated redemption or failed payment as paid cancellation.
        unpaid = find(r"insufficient\s+(?:\w+\s+){0,4}funds|cannot\s+be\s+redeemed"
                      r"|unpaid\s+(?:principal|amounts?|balance)|amounts?\s+unpaid", text)
        loss = find(r"\b(?:cancelled|canceled|discharged|extinguished)\b", text)
        if unpaid and loss and find(r"\b(?:notes?|principal|noteholders)\b", text):
            return [{"kind": "candidate", "disposition": "unresolved_unpaid_cancellation",
                     "origin": None, "cancellation_context": text}]
        return []
    before = text[max(0, action.start() - 140):action.start()]
    if find(r"\b(?:whether|hypothetically|would|could|notify|report|headed|entitled)\b", before):
        return [{"kind": "candidate", "disposition": "unresolved_reported_cancellation",
                 "origin": None, "cancellation_context": text}]
    # Interest-only arrears are outside the principal-loss relation.
    if not find(r"\bprincipal\b", action.group()) and not (
        find(r"\bunpaid\s+amounts\b", action.group()) and
        find(r"outstanding\s+under\s+the\s+Transaction\s+Documents\s+or\s+the\s+Notes", text)):
        return [{"kind": "candidate", "disposition": "unresolved_unpaid_cancellation",
                 "origin": None, "cancellation_context": text}]
    requirements, exceptions = [], []
    def required(kind, pattern):
        match = find(pattern, text)
        if match:
            requirements.append(slot(match, kind))
        return bool(match)
    def excepted(kind, pattern):
        match = find(pattern, text)
        if match:
            exceptions.append(slot(match, kind))
        return bool(match)

    insufficient = required("insufficient_funds", r"\binsufficient\s+(?:\w+\s+){0,4}funds\b")
    final = required("at_final_maturity", r"\bon\s+the\s+Final\s+Maturity\s+Date\b")
    later = required("at_cancellation_date", r"\buntil\s+the\s+Cancellation\s+Date,\s+at\s+which\s+date\b")
    certificate = required("servicer_certificate",
                           r"\bif\s+the\s+Servicer\s+has\s+certified\s+to\s+the\s+Representative\s+of\s+the\s+Noteholders\b")
    exhausted = required("no_further_recoveries",
                         r"\bno\s+(?:\d+\s+)?reasonable\s+likelihood\s+of\s+there\s+being\s+any\s+further\s+realisations\b")
    notice = required("representative_notice",
                      r"\bthe\s+Representative\s+of\s+the\s+Noteholders\s+has\s+given\s+notice\s+on\s+the\s+basis\s+of\s+such\s+certificate\b")
    withholding = excepted("improper_withholding_or_refusal",
                           r"\bunless\s+payment\s+of\s+such\s+amounts\s+is\s+being\s+improperly\s+withheld\s+or\s+refused\b")
    misconduct = find(r"\bin\s+the\s+absence\s+of\s+gross\s+negligence\s*(?:\([^)]*\)\s*)?"
                      r"or\s+wilful\s+misconduct\s*(?:\([^)]*\)\s*)?on\s+the\s+part\s+of\s+the\s+Issuer\b", text)
    if misconduct:
        exceptions += [slot(misconduct, "issuer_gross_negligence"),
                       slot(misconduct, "issuer_wilful_misconduct")]
    if insufficient and final and withholding:
        construction = "insufficient_funds_final_cancellation"
        complete = True
    elif insufficient and later and misconduct:
        construction = "deferred_cancellation"
        complete = True
    elif certificate and exhausted and notice:
        construction = "certified_exhaustion"
        complete = True
    elif not find(r"\b(?:if|unless|except|subject\s+to|provided|until)\b", text):
        construction = "unconditional_unpaid_cancellation"
        complete = True
    else:
        construction = "unresolved_cancellation_conditions"
        complete = False
    # Qualifiers outside the supported constructions veto an unconditional reading.
    known_exception_ranges = [(s["start"], s["end"]) for s in exceptions]
    extra_exception = any(not any(a <= m.start() < b for a,b in known_exception_ranges)
                          for m in re.finditer(r"\b(?:unless|except|in the absence of)\b", text, re.I))
    if extra_exception or len(re.findall(r"\bif\b", text, re.I)) > 1:
        complete = False
    if construction == "unconditional_unpaid_cancellation" and not find(r"\b(?:the|these)\s+Notes\b", text):
        complete = False
    if find(r"\b(?:subject\s+to|provided\s+that|except\s+(?:where|when|if))\b", text):
        complete = False
    witness = {"rule": "unpaid_cancellation", "construction": construction,
               "relation": {"start": action.start(), "end": action.end(), "quote": action.group()},
               "requirements": requirements, "exceptions": exceptions,
               "source_clause": text, "conditions_complete": complete,
               "mapping_status": "BOUNDED_ENGLISH_CONSTRUCTION_NOT_LEGAL_PROOF"}
    return [{"kind": "principal_write_down" if complete else "candidate",
             "disposition": "applicable" if complete else "unresolved_cancellation_conditions",
             "origin": "contractual", "semantic_witness": witness}]


def valid_cancellation_witness(item):
    return any(f.get("semantic_witness") == item.get("semantic_witness") and
               f["kind"] == item.get("kind") and f["disposition"] == item.get("disposition")
               for f in cancellation_features(item["quote"]))


def evaluate_cancellation(witness, facts):
    """Three-valued evaluation of reviewed conditions; missing facts stay unknown."""
    if not isinstance(facts, dict) or any(type(v) is not bool and v is not None for v in facts.values()):
        raise ValueError("Cancellation facts must be true, false or unknown")
    if not witness.get("conditions_complete"):
        return None
    expected = next((f["semantic_witness"] for f in cancellation_features(witness.get("source_clause", ""))
                     if f.get("semantic_witness") == witness), None)
    if expected is None:
        raise ValueError("Cancellation witness does not replay")
    requirements = [facts.get("unpaid_principal")] + [
        facts.get(s["kind"]) for s in witness["requirements"]]
    exceptions = [facts.get(s["kind"]) for s in witness["exceptions"]]
    if False in requirements or True in exceptions:
        return False
    return True if all(v is True for v in requirements) and all(v is False for v in exceptions) else None
