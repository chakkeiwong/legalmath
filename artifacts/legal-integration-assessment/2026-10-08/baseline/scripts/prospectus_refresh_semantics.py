"""Bounded recognition of disclosed statutory powers, not legal applicability."""
import re
from scripts.prospectus_refresh_sources import norm, require
WRITE_DOWN = ("Under the relevant resolution laws and regulations as applicable to the Issuer "
              "from time to time, the Notes may be subject to the powers exercised by the "
              "competent resolution authority to: (a) write down, including writing down to zero, "
              "the claims for payment of the principal amount, the interest amount or any other "
              "amount in respect of the Notes;")
CONVERSION = ("(b) convert these claims into ordinary shares of (i) the Issuer or (ii) any group entity "
              "or (iii) any bridge bank or other instruments of ownership qualifying as Common Equity "
              "Tier 1 instruments (and issue or confer on the Holders such instruments); and/or")
QUALIFIERS = (
    "The Holders shall be bound by any Resolution Measure.",
    "the exercise of any Resolution Measure shall not constitute an event of default.",
    "to the exclusion of any other agreements, arrangements or understandings between the Holders "
    "and the Issuer relating to the subject matter of these Terms and Conditions.",
)
def passage(text):
    text=norm(text)
    start_marker="(7) Note on the possibility of statutory resolution measures."
    require(text.count(start_marker)==1,"Missing/ambiguous section 2(7)")
    start=text.index(start_marker)
    headings=list(re.finditer(r"§\s*3\s+Interest\b",text[start:]))
    require(len(headings)==1,"Missing/ambiguous next section")
    quote=text[start:start+headings[0].start()].rstrip()
    end=start+len(quote)
    require(text[start:end]==quote,"Passage offsets do not replay")
    return {"start":start,"end":end,"quote":quote}

def recognize(text):
    """Return no finding outside the explicitly qualified complete construction."""
    text=norm(text)
    expected = (
        "(7) Note on the possibility of statutory resolution measures. " + WRITE_DOWN + " " + CONVERSION +
        ' (c) apply any other resolution measure, including, but not limited to, (i) any transfer of the '
        'Notes to another entity, (ii) the amendment, modification or variation of the Terms and Conditions '
        'or (iii) the cancellation of the Notes, (each, a "Resolution Measure"). '
        'The Holders shall be bound by any Resolution Measure. No Holders shall have any claim or other '
        'right against the Issuer arising out of any Resolution Measure. In particular, the exercise of '
        'any Resolution Measure shall not constitute an event of default. Through purchase of the Notes, '
        'each Holder acknowledges and accepts the measures and their effects according to this § 2(7) '
        'and that this § 2(7) is exhaustive on the matters described herein to the exclusion of any other '
        'agreements, arrangements or understandings between the Holders and the Issuer relating to the '
        'subject matter of these Terms and Conditions.'
    )
    # Unreviewed additions, exceptions and rewordings abstain. This source-specific
    # construction is not a general entailment rule.
    if text != expected:
        return None
    return {
        "schema":"reviewed-statutory-disclosure.v1",
        "authority":"competent_resolution_authority",
        "modal":"may_be_subject_to",
        "basis":"relevant resolution laws and regulations as applicable to the Issuer from time to time",
        "principal_write_down_power_disclosed":True,
        "write_down_floor":"zero",
        "ordinary_share_conversion_alternative_disclosed":True,
        "other_cet1_ownership_alternative_disclosed":True,
        "mandatory_common_share_only_conversion":None,
        "disposition":"DISCLOSED_STATUTORY_POWERS_WITH_CONVERSION_ALTERNATIVES",
        "current_legal_applicability":None,
        "actual_resolution_measure":None,
        "certified_legal_answer":None,
        "source_review":"development_only",
        "quote":text,
        "qualification":"Disclosure recognition only; current law, instrument scope and actual action require separate evidence."
    }
