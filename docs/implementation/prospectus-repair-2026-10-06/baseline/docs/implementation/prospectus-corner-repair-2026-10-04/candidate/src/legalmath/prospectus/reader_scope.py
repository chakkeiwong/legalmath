"""Validate declared page scope and recognize a bounded paid-redemption relation."""
import re


def validate(selection, pages):
    occupied = {}
    for key in ("operative_pages", "shelf_pages", "evidence_priority_pages"):
        ranges = selection.get(key, [[1, pages]] if key == "operative_pages" else [])
        if not isinstance(ranges, list) or (key == "operative_pages" and not ranges):
            raise ValueError("Invalid document scope: " + key)
        seen = set()
        for interval in ranges:
            if (not isinstance(interval, list) or len(interval) != 2
                    or any(type(x) is not int for x in interval)
                    or not 1 <= interval[0] <= interval[1] <= pages):
                raise ValueError("Invalid document scope range: " + key)
            current = set(range(interval[0], interval[1]+1))
            if current & seen:
                raise ValueError("Overlapping document scope ranges: " + key)
            seen |= current
        occupied[key] = seen
    if occupied["operative_pages"] & occupied["shelf_pages"]:
        raise ValueError("Overlapping operative/shelf document scope")


def deferred_interest_forfeiture(text):
    # Only the source-reviewed deferred-interest relation. Incidental interest
    # in a share/asset forfeiture must not exempt that other subject.
    return re.fullmatch(
        r'Any interest not paid on an Optional Interest Payment Date shall, so long as the same '
        r'remains unpaid, constitute ["“]\s*Arrears of Interest["”], which term shall include interest '
        r'on such unpaid interest as referred to below, except if the relevant Final Terms specify '
        r'that any interest not paid on an Optional Interest Payment Date shall be forfeited and '
        r'accordingly not due or payable by the Issuer any longer\.?', text.strip(), re.I) is not None


def partial_redemption(text):
    return re.fullmatch(
        r"In the case of a partial redemption of, or a partial exercise (?:of|by the Issuer of) "
        r"(?:the|an) Issuer[’']s option in respect of, Dematerialised Notes, "
        r"the redemption will be effected,? by reducing the nominal amount of all such "
        r"Dematerialised Notes in a Series in proportion to the aggregate nominal amount redeemed, "
        r"subject to compliance with any other applicable laws and (?:requirements of the Regulated Market "
        r"on which the Notes are listed and admitted to trading|Regulated Market or stock exchange requirements)\.?",
        text.strip(), re.I) is not None




def paid_amortisation(text):
    """Recognize reduction caused by the same scheduled principal payment.

    Any separate loss wording defeats this clause-level exclusion. Scope still
    needs a caller-reviewed issue selection; programme options are not issues.
    """
    patterns = (
        r"upon payment of the relevant Amorti[sz]ation Amount\s+(?:the Notes:\s*)?"
        r"(?:the\s+)?outstanding principal amount of such Note shall be reduced "
        r"by the same proportion which the relevant Amorti[sz]ation Amount bears "
        r"to the aggregate of all Amorti[sz]ation Amounts",
        r"each Note outstanding on an Amorti[sz]ation Date shall be partially redeemed "
        r"on such Amorti[sz]ation Date at the specified Amorti[sz]ation Amount and "
        r"the outstanding principal amount of such Note shall be reduced "
        r"(?:accordingly|\[accordingly \(insert for Notes which are not Zero Coupon Notes\)\]"
        r"/\[in accordance with paragraph \[17\] above \(insert for Notes which are Zero Coupon Notes\)\])",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        remainder = text[:match.start()] + " " + text[match.end():]
        if re.search(r"\b(?:reduc\w*|cancel\w*|extinguish\w*|discharg\w*|unpaid|"
                     r"bail.in|write.down|written.down|convert\w*|loss)\b", remainder, re.I):
            continue
        return True
    return False


def redemption_floor(text, previous):
    return partial_redemption(previous) and re.fullmatch(
        r"In no event, the outstanding nominal amount of each Note (?:\d+ )?following such reduction "
        r"shall be below any amount which would prevent the Issuer from choosing its home Member State "
        r"\(as such term is defined in the Prospectus Regulation\)\.?", text.strip(), re.I) is not None
