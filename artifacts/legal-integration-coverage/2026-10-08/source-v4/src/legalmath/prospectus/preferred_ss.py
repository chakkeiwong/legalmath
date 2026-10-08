"""Source-dependent Series SS profile; equity is not a UBS conversion note."""
from copy import deepcopy
from fractions import Fraction
from datetime import timedelta
import json
from pathlib import Path

from ..canonical import digest
from ..transaction.evidence import sha
from ..transaction import engine
from . import eligibility
from .instrument_terms import amount, day, _result
from .instrument_branches import cents

KEY = "bofa-series-ss-2022-issuer"
PDF_SHA = "c5af1b97efc33065fdf03a9303f9d1a983ee2e13ef856d48dd1f6f186df3b2d0"
TEXT_SHA = "430b4ff71fc23849e1c3849815dfbc1526e539194c3331c6cb48d2ee7e20315f"
CERT_SHA = "8dde59f8b5bafad0e2aed935ae0970a4f69d09806933b75accacfef755038470"


def dossier(root):
    root = Path(root)
    pdf = root/"docs/prospectus/originals"/(KEY+".pdf")
    text = root/"docs/prospectus/text"/(KEY+".json")
    cert = root/"docs/prospectus/supplemental/text/bofa-ss-certificate.web.txt"
    for path, expected in ((pdf, PDF_SHA), (text, TEXT_SHA), (cert, CERT_SHA)):
        if sha(path.read_bytes()) != expected:
            raise ValueError("Series SS source changed; reassessment required")
    pages = json.loads(text.read_text())["pages"]
    anchors = {"precedence": (16, "Certificate of Designations will control"),
        "equity": (16, "series of our authorized preferred stock"),
        "no_conversion": (16, "will not be convertible into"),
        "dividend_rate": (17, "4.750% per annum"),
        "noncumulative": (17, "will not cumulate"),
        "daycount": (17, "360-day year of twelve 30-day months"),
        "rounding": (17, "one-half cent being rounded upward"),
        "liquidation": (19, "satisfaction of other liabilities to creditors"),
        "redemption": (19, "February 17, 2027"),
        "notice": (20, "not less than 30"),
        "fractional_interest": (27, "1/1,000"),
        "holder_taxes": (27, "reduced by any amounts required to be withheld"),
        "redemption_lots": (28, "increments of 1,000 depositary shares")}
    for name, (page, quote) in anchors.items():
        if quote not in " ".join(pages[page-1]["text"].split()):
            raise ValueError("Missing Series SS source anchor: "+name)
    result = {"profile": "bofa-series-ss-2022.v1", "instrument": KEY,
        "pdf_sha256": PDF_SHA, "text_sha256": TEXT_SHA, "certificate_text_sha256": CERT_SHA,
        "certificate_representation": "WEB_TOOL_EXTRACTION_NOT_ORIGINAL_HTML",
        "anchors": {k: {"pdf_page": p, "quote": q} for k, (p,q) in anchors.items()},
        "terms": {"preferred_liquidation_usd": "25000", "depositary_fraction": "1/1000",
                  "annual_rate": "19/400", "regular_quarter_fraction": "1/4",
                  "ordinary_call_from": "2027-02-17", "issue_date": "2022-01-31"},
        "product_interpretation": {"debt_legal_form": False, "qualifying_wrapper": False,
                                  "loss_absorption_fund": False},
        "dependencies": {"deposit_agreement": "MISSING", "original_certificate": "MISSING",
            "certificate_extraction": "RETAINED", "amendment_history": "UNKNOWN",
            "actual_declaration_payment_and_ownership": "UNKNOWN", "applicable_law_and_bank_layers": "QUALIFIED"},
        "source_differences": ["Certificate section 6(a)(ii) places redemption within 90 days of a Capital Treatment Event; the supplement describes providing notice within 90 days. The conditional calculation follows the controlling certificate.",
            "Certificate section 4(b) addresses dividends not declared and paid; sections 5/6 also preserve specified declared unpaid dividends. No generic cancellation of all declared arrears is inferred."],
        "legal_entailment": "NOT_ESTABLISHED", "current_applicability": "NOT_ESTABLISHED", "human_quality_evidence": False}
    return {**result, "dossier_hash": digest(result)}


def regular_dividend(*, start, end, declared_fraction, funds_available, depositary_shares,
                     allocation_basis=None, withholding=None):
    """Regular scheduled periods only; stubs and rounding units stay explicit."""
    a, b = day(start), day(end)
    if type(depositary_shares) is not int or depositary_shares < 0:
        raise ValueError("Nonnegative integer depositary shares required")
    regular = a.day == b.day == 17 and a.month in (2,5,8,11) and (b.year-a.year)*12+b.month-a.month == 3 and a >= day("2022-05-17")
    issues = [] if regular else ["Initial/stub period requires an explicit month-end day-count convention"]
    if declared_fraction is None or funds_available is not True:
        issues.append("Declaration amount or legally available funds missing")
    fraction = amount(declared_fraction) if declared_fraction is not None else None
    if fraction is not None and fraction > 1:
        raise ValueError("Declared fraction must lie between zero and one")
    if issues:
        return _result({"gross_usd": None, "undeclared_carry": "0", "actual_payment": "NOT_ESTABLISHED"}, issues)
    exact_preferred = Fraction(25000)*Fraction(19,400)/4*fraction
    exact_holder = exact_preferred*depositary_shares/1000
    variants = {
        "round_preferred_then_holder": cents(str(cents(str(exact_preferred), "half_up")*depositary_shares/1000), "half_up"),
        "round_holder_allocation": cents(str(exact_holder), "half_up")}
    if fraction == 0:
        gross = Fraction(0)
    elif allocation_basis in variants:
        gross = variants[allocation_basis]
    elif allocation_basis is None:
        gross = None
        issues.append("Cash calculation/rounding unit must be evidenced; alternatives are not a legal selection")
    else:
        raise ValueError("Unknown cash allocation convention")
    if withholding is None:
        issues.append("Required tax withholding not supplied")
        net = None
    else:
        tax = amount(withholding)
        if gross is not None and tax > gross:
            raise ValueError("Withholding exceeds the calculated distribution")
        net = gross-tax if gross is not None else None
    return _result({"exact_holder_usd": str(exact_holder), "gross_usd": None if gross is None else str(gross),
        "net_usd": None if net is None else str(net), "rounding_scenarios": {k: str(v) for k,v in variants.items()},
        "undeclared_carry": "0", "actual_payment": "NOT_ESTABLISHED", "declared_arrears_treatment": "NOT_INFERRED"}, issues)


def dividend_payment_date(scheduled, *, new_york, charlotte):
    """Following business day, except crossing a year uses the preceding day."""
    nominal = day(scheduled)
    if new_york.record["market"] != "New York" or charlotte.record["market"] != "Charlotte" or any(
            c.record["purpose"] != "banks_not_authorized_or_required_closed" for c in (new_york,charlotte)):
        raise ValueError("Both contractual bank-closure calendars required")
    def opened(d):
        # Retrieve both records even on weekends to verify complete coverage.
        a,b = new_york.is_open(d.isoformat()), charlotte.is_open(d.isoformat())
        return d.weekday()<5 and a and b
    current = nominal
    while not opened(current): current += timedelta(days=1)
    if current.year != nominal.year:
        current=nominal-timedelta(days=1)
        while not opened(current): current -= timedelta(days=1)
    return {"scheduled_date":scheduled,"payment_date":current.isoformat(),
            "period_adjusted":False,"additional_dividend_for_delay":"0","actual_payment":"NOT_ESTABLISHED"}


def redemption(*, date, notice_date, ordinary, capital_event_date, full_redemption,
               issuer_elected, funds_available, regulator_approval, notice_complete,
               depositary_shares):
    when, notice = day(date), day(notice_date)
    if type(depositary_shares) is not int or depositary_shares <= 0 or depositary_shares % 1000:
        raise ValueError("Redemption must use positive multiples of 1,000 depositary shares")
    issues = []
    if ordinary is True:
        timing = when >= day("2027-02-17")
    elif ordinary is False:
        timing = capital_event_date is not None and 0 <= (when-day(capital_event_date)).days <= 90 and full_redemption is True
    else:
        timing = False
    if not timing: issues.append("Redemption date or whole-issue condition does not satisfy the selected branch")
    if not 30 <= (when-notice).days <= 60: issues.append("Notice must precede redemption by 30 through 60 calendar days")
    if any(v is not True for v in (issuer_elected, funds_available, regulator_approval, notice_complete)):
        issues.append("Issuer election, lawful funds, approval or complete notice missing")
    return _result({"date_conditions_satisfied": timing and 30 <= (when-notice).days <= 60,
        "principal_usd": str(Fraction(25)*depositary_shares), "actual_redemption": "NOT_ESTABLISHED",
        "current_period_dividend_and_record_holder": "SEPARATE_REQUIRED_CALCULATION"}, issues)


def liquidation(*, available_after_senior_claims, own_preference, own_declared_unpaid, parity_claims):
    available, own, declared, parity = map(amount, (available_after_senior_claims, own_preference, own_declared_unpaid, parity_claims))
    claim = own+declared
    total = claim+parity
    paid = min(available,total)*claim/total if total else Fraction(0)
    return {"own_distribution": str(paid), "junior_residual": str(max(Fraction(0), available-total)),
        "undeclared_dividends_included": False, "actual_liquidation": "NOT_ESTABLISHED",
        "senior_and_parity_inventory": "EXPLICIT_INPUT_PREMISE"}


def investigate(joined_request, store, root):
    if (joined_request["bank_request"]["context"]["instrument_id"] != KEY
            or joined_request["prospectus_source_ids"] != [KEY]):
        raise ValueError("Series SS profile cannot be transferred to another issue")
    packet = dossier(root)
    joined = eligibility.investigate(joined_request, store)
    observations = deepcopy(joined["observations"])
    for name, value in packet["product_interpretation"].items():
        row = observations[name]
        conflict = row["status"] == "CONFLICT" or (row["status"] == "KNOWN" and row["value"] != value)
        row.update(status="CONFLICT" if conflict else "KNOWN", value=None if conflict else value,
                   truth_of_assertion="SOURCE_DEPENDENT_PROPOSAL")
        row["sources"] = sorted(set(row["sources"]+[packet["dossier_hash"]]))
    calculations, observations = eligibility.calculate(observations)
    result = {"profile": packet["profile"], "dossier": packet, "joined": joined,
        "observations": observations, "calculations": calculations, "inventory": joined["inventory"],
        "method_hash": engine.method_identity(), "request_hash": digest(joined_request),
        "decision": "QUALIFIED", "may_execute_transaction": False, "human_quality_evidence": False,
        "conversion": "NO_CONTRACTUAL_CONVERSION_IN_THIS_PROFILE", "legal_entailment": "NOT_ESTABLISHED"}
    return {**result, "receipt_hash": digest(result)}
