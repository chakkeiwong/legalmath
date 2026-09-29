"""Conditional Annex A calculations with explicit missing-event boundaries.

Dates have day precision. Intraday ordering is not guessed. Each input describes
a factual or hypothetical premise, not an independently certified legal event.
"""
from datetime import date, timedelta
from fractions import Fraction

from ..transaction.evidence import fields


def day(value):
    if not isinstance(value, str):
        raise ValueError("Canonical calendar date required")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Canonical calendar date required")
    return parsed


def amount(value, *, positive=False):
    if type(value) not in (str, int):
        raise ValueError("Exact decimal/rational text or integer required")
    number = Fraction(value)
    if number < 0 or (positive and number == 0):
        raise ValueError("Invalid nonnegative amount")
    return number


def boolean(value):
    if value is not None and type(value) is not bool:
        raise ValueError("Boolean or explicit unknown required")
    return value


class Calendar:
    """Complete day inventory, retrieved from content-addressed evidence."""
    def __init__(self, store, identity):
        self.identity = identity
        self.record = store.json(identity)
        fields(self.record, {"start", "end", "open_days", "premise_kind"})
        if self.record["premise_kind"] not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
            raise ValueError("Calendar provenance required")
        self.start, self.end = day(self.record["start"]), day(self.record["end"])
        if not 0 <= (self.end-self.start).days <= 3660:
            raise ValueError("Invalid or excessive covered calendar interval")
        fields(self.record["open_days"], {"Zurich", "Singapore"})
        self.open = {}
        for market, values in self.record["open_days"].items():
            if not isinstance(values, list) or len(values) != len(set(values)):
                raise ValueError("Unique covered opening dates required")
            parsed = {day(v) for v in values}
            if any(v < self.start or v > self.end or v.weekday() >= 5 for v in parsed):
                raise ValueError("Opening dates contradict interval or contractual weekend")
            self.open[market] = parsed

    def is_open(self, value, *, publication=False):
        value = day(value) if isinstance(value, str) else value
        if not self.start <= value <= self.end:
            raise ValueError("Date outside evidenced calendar coverage")
        return value in self.open["Zurich"] and (publication or value in self.open["Singapore"])

    def after(self, start, count):
        if type(count) is not int or not 0 <= count <= 366:
            raise ValueError("Bounded business-day count required")
        current = day(start)
        self.is_open(current)  # coverage check; the starting date need not be open
        while count:
            current += timedelta(days=1)
            if self.is_open(current):
                count -= 1
        return current.isoformat()


def notice_date(notice, *, effective_date=None):
    """Condition 14: first SIX publication, or delivery if no longer listed."""
    if notice is None:
        if effective_date is not None:
            raise ValueError("A dated notice still requires its actual contents")
        return None
    fields(notice, {"listed_on_six", "six_publications", "intermediary_delivery",
                    "declares_event", "conversion_date", "price", "depository", "offer"})
    boolean(notice["listed_on_six"]); boolean(notice["declares_event"]); boolean(notice["offer"])
    dates = notice["six_publications"]
    if not isinstance(dates, list):
        raise ValueError("Publication history required")
    for value in dates:
        day(value)
    delivery = notice["intermediary_delivery"]
    if delivery is not None:
        day(delivery)
    standard = min(dates) if dates else None
    if notice["listed_on_six"] is False:
        standard = delivery
    elif notice["listed_on_six"] is None:
        standard = None
    if effective_date is not None:
        day(effective_date)
        if notice["listed_on_six"] is not True or (standard is not None and standard != effective_date):
            raise ValueError("Alternative effective notice conflicts with listing/publication evidence")
        return effective_date
    return standard


def _result(values, issues):
    return {**values, "status": "QUALIFIED" if issues else "CONDITIONAL",
            "issues": sorted(set(issues)), "legal_event_truth": "NOT_ESTABLISHED"}


def _notice_details(notice, *, viability=False):
    problems = []
    if notice["declares_event"] is not True:
        problems.append("Notice does not establish its required event/conversion statement")
    if notice["price"] is None:
        problems.append("Notice price missing")
    else:
        amount(notice["price"], positive=True)
    if not isinstance(notice["depository"], str) or not notice["depository"]:
        problems.append("Settlement depository/arrangements missing")
    if notice["offer"] is None or (viability and notice["offer"] is not False):
        problems.append("Settlement Shares Offer is available only for a Trigger Event")
    return problems


def trigger(terms, publication, calendar, *, notice=None, higher=None, restoration=None, notice_effective_date=None):
    """Condition 7(a),(b),(d); never create a notice from a computed deadline.

    `higher=[]` explicitly asserts no outstanding higher-trigger instruments;
    `higher=None` is unknown. `restoration=False` explicitly asserts no exception;
    None is missing. Capital inputs are the publication snapshot, not revisions.
    """
    fields(publication, {"date", "kind", "cet1", "higher_amount", "rwa", "snapshot_sha256"})
    at = publication["date"]; day(at)
    if publication["kind"] not in {"ordinary", "extraordinary"}:
        raise ValueError("Publication kind required")
    if not calendar.is_open(at, publication=True):
        raise ValueError("Publication date is not a covered Zurich Business Day")
    if not isinstance(publication["snapshot_sha256"], str) or len(publication["snapshot_sha256"]) != 64:
        raise ValueError("Publication snapshot identity required")
    if any(publication[k] is None for k in ("cet1", "higher_amount", "rwa")):
        return _result({"trigger_event": None}, ["Missing publication capital components"])
    capital, addback, rwa = (amount(publication[k], positive=k == "rwa") for k in ("cet1", "higher_amount", "rwa"))
    ratio = (capital + addback) / rwa
    breach = ratio < amount(terms["threshold_percent"]) / 100
    actual = notice_date(notice, effective_date=notice_effective_date)
    ordinary = publication["kind"] == "ordinary"
    due = calendar.after(at, 5) if ordinary else at
    values = {"publication_snapshot": publication["snapshot_sha256"], "trigger_ratio": str(ratio),
              "ratio_breach": breach, "base_notice_deadline": due,
              "actual_notice_date": actual, "trigger_event": None, "restoration_exception": False}
    issues = []
    if not breach:
        if actual is not None:
            issues.append("Notice conflicts with the supplied non-breaching publication")
        return _result({**values, "notice_required_under_ratio": False}, issues)

    if ordinary:
        if restoration is None:
            issues.append("Restoration exception evidence missing")
        elif restoration is not False:
            fields(restoration, {"agreement_date", "requested_by_ubs", "written_finma_agreement",
                "restored_or_imminent", "pro_forma_cet1_ratio", "jointly_deemed_adequate", "no_conversion_notice"})
            keys = ("requested_by_ubs", "written_finma_agreement", "restored_or_imminent", "jointly_deemed_adequate")
            conditions = [boolean(restoration[k]) for k in keys]
            if None in conditions or restoration["agreement_date"] is None or restoration["pro_forma_cet1_ratio"] is None:
                issues.append("Incomplete restoration evidence")
            else:
                agreed = restoration["agreement_date"]; day(agreed)
                before = min(actual, due) if actual else due
                substantive = all(conditions) and amount(restoration["pro_forma_cet1_ratio"]) > amount(terms["threshold_percent"]) / 100
                if substantive and agreed == before:
                    issues.append("Intraday ordering of restoration agreement is unresolved")
                elif substantive and agreed < before:
                    values["restoration_exception"] = True
                    if actual is None:
                        # A missing conversion notice is not evidence that no
                        # earlier notice existed. Preserve the conditional
                        # substantive exception but qualify its chronology.
                        issues.append("Earlier conversion-notice history not established")
                    if actual:
                        issues.append("Conversion notice conflicts with restoration exception")
                    no_conversion = restoration["no_conversion_notice"]
                    if no_conversion is None or day(no_conversion) > day(due) or day(no_conversion) < day(agreed):
                        issues.append("Timely no-conversion notice not established")
                    return _result({**values, "notice_required_under_ratio": False if actual else None}, issues)
    values["notice_required_under_ratio"] = True
    if higher is None:
        return _result(values, issues + ["Higher-trigger outstanding/notice inventory missing"])
    if not isinstance(higher, list):
        raise ValueError("Higher-trigger inventory required")
    notices, conversions, ids = [], [], set()
    for row in higher:
        fields(row, {"id", "notice_date", "conversion_date"})
        if not isinstance(row["id"], str) or not row["id"] or row["id"] in ids:
            raise ValueError("Unique higher-trigger instrument identities required")
        ids.add(row["id"])
        if row["notice_date"] is None or row["conversion_date"] is None:
            return _result(values, issues + ["Higher-trigger notice/conversion is unresolved; no date invented"])
        if day(row["notice_date"]) > day(row["conversion_date"]):
            raise ValueError("Higher-trigger conversion precedes its notice")
        notices.append(row["notice_date"]); conversions.append(row["conversion_date"])
    latest_notice = max(notices) if notices else None
    if actual is None:
        return _result(values, issues + ["Actual issuer notice missing; a deadline is not a Trigger Event"])
    # Day-level equality with another instrument's notice cannot establish which
    # was first. The contract's deemed date is nonetheless that same date.
    if latest_notice and latest_notice > actual:
        issues.append("Issuer notice precedes all required higher-trigger notices")
    allowed_due = max(due, latest_notice) if latest_notice else due
    if not at <= actual <= allowed_due:
        issues.append("Issuer notice outside permitted publication/notice interval")
    if latest_notice and latest_notice > due and actual != latest_notice:
        issues.append("Postponed notice does not match deemed higher-trigger notice date")
    issues.extend(_notice_details(notice))
    limit = calendar.after(actual, 20)
    conversion = notice["conversion_date"]
    final_limit = max([limit] + conversions)
    if conversion is None:
        issues.append("Specified conversion date missing")
    else:
        day(conversion)
        if conversion <= actual or conversion > final_limit or (conversions and conversion < max(conversions)):
            issues.append("Conversion date violates notice/20-business-day/higher-trigger ordering")
        # A postponement beyond the ordinary limit must be to the latest higher
        # conversion date, not to any convenient day before the widened limit.
        if conversion > limit and conversions and conversion != max(conversions):
            issues.append("Conversion postponement must equal the latest higher-trigger date")
    values.update(notice_deadline=allowed_due, base_conversion_deadline=limit,
                  conversion_deadline=final_limit, specified_conversion_date=conversion,
                  trigger_event=True if not issues else None)
    return _result(values, issues)


def alternative_loss(calendar, record):
    fields(record, {"change_date", "joint_determination_date", "law_changed_after_issue",
                    "joint_ubs_finma_determination", "without_regulatory_event", "notice_date"})
    issues = []
    for key in ("law_changed_after_issue", "joint_ubs_finma_determination", "without_regulatory_event"):
        if boolean(record[key]) is not True:
            issues.append("Missing alternative-loss premise: " + key)
    if record["change_date"] is None or record["joint_determination_date"] is None:
        return _result({"alternative_loss_date": None}, issues + ["Change/determination dates missing"])
    changed, determined = day(record["change_date"]), day(record["joint_determination_date"])
    if not day("2024-06-24") < changed <= determined:
        issues.append("Alternative-loss change/determination chronology invalid")
    due = calendar.after(determined.isoformat(), 5)
    notice = record["notice_date"]
    if notice is None:
        issues.append("Actual alternative-loss notice missing")
    elif not determined <= day(notice) <= day(due):
        issues.append("Alternative-loss notice outside five-business-day interval")
    return _result({"notice_deadline": due, "alternative_loss_date": notice if not issues else None}, issues)


def viability(calendar, event, *, notice=None, alternative=False, notice_effective_date=None):
    fields(event, {"date", "customary_measures_inadequate", "finma_written_capital_absorption_essential",
        "irrevocable_public_support", "extraordinary_support", "capital_improved_or_imminent",
        "finma_written_without_support_nonviable"})
    at = event["date"]; day(at)
    vals = {k: boolean(v) for k, v in event.items() if k != "date"}
    issues = []
    a = vals["finma_written_capital_absorption_essential"]
    support = [vals[k] for k in ("irrevocable_public_support", "extraordinary_support",
                                "capital_improved_or_imminent", "finma_written_without_support_nonviable")]
    b = False if False in support else None if None in support else True
    necessary = vals["customary_measures_inadequate"]
    occurred = False if necessary is False or (a is False and b is False) else True if necessary is True and (a is True or b is True) else None
    if alternative is None:
        issues.append("Alternative-loss notice history missing")
    elif alternative is not False:
        alt = alternative_loss(calendar, alternative)
        if alt["issues"]:
            issues.extend(alt["issues"])
        elif at >= alt["alternative_loss_date"]:
            occurred = False
    if occurred is None:
        issues.append("Viability event premises incomplete")
    due = (day(at) + timedelta(days=3)).isoformat()
    limit = calendar.after(at, 20)
    actual = notice_date(notice, effective_date=notice_effective_date)
    values = {"viability_event": occurred if not issues else None, "notice_deadline": due,
        "conversion_deadline": limit, "actual_notice_date": actual, "specified_conversion_date": None,
        "notice_and_schedule_satisfied": False}
    if occurred is not True:
        if actual is not None:
            issues.append("Viability notice conflicts with missing/inactive event premises")
        return _result(values, issues)
    if actual is None:
        return _result(values, issues + ["Actual viability notice missing"])
    if not at <= actual <= due:
        issues.append("Viability notice outside three-calendar-day interval")
    issues.extend(_notice_details(notice, viability=True))
    conversion = notice["conversion_date"]
    if conversion is None:
        issues.append("Specified conversion date missing")
    elif not day(actual) < day(conversion) <= day(limit):
        issues.append("Viability conversion exceeds event-anchored deadline or precedes share creation")
    return _result({**values, "specified_conversion_date": conversion,
                    "notice_and_schedule_satisfied": not issues}, issues)


def share_entitlement(principals, price, denomination):
    """Condition 8(c),(g): aggregate by holder first, then floor once."""
    if not isinstance(principals, list) or not principals:
        raise ValueError("One holder's principal lots required")
    lots = [amount(v, positive=True) for v in principals]
    unit = amount(denomination, positive=True)
    if any((v/unit).denominator != 1 for v in lots):
        raise ValueError("Holding violates the stated minimum/increment")
    total, conversion_price = sum(lots), amount(price, positive=True)
    exact = total/conversion_price
    shares = exact.numerator // exact.denominator
    return {"principal": str(total), "conversion_price": str(conversion_price), "shares": shares,
        "fraction_discarded": str(exact-shares), "cash_for_fraction": "0",
        "market_value": "NOT_COMPUTED", "aggregation": "ONE_HOLDER"}


def settlement(schedule, entitlement, *, share_creation_date=None, depository_received_date=None):
    """Entitlement, share creation, discharge and holder delivery are distinct."""
    issues = list(schedule["issues"])
    actual = schedule.get("actual_notice_date")
    conversion = schedule.get("specified_conversion_date")
    if schedule["status"] != "CONDITIONAL" or not (schedule.get("trigger_event") is True or schedule.get("notice_and_schedule_satisfied") is True):
        issues.append("A checked conditional notice/schedule is required")
    if share_creation_date is None or depository_received_date is None:
        issues.append("Actual share creation and depository receipt evidence missing")
    elif not actual or not conversion or not day(actual) < day(share_creation_date) <= day(depository_received_date) <= day(conversion):
        issues.append("Share creation/receipt chronology invalid")
    return _result({"entitlement": entitlement, "issuer_obligation_discharged": True if not issues else None,
        "accrued_unpaid_interest_cancelled": True if not issues else None,
        "holder_delivery": "NOT_ESTABLISHED", "market_value": "NOT_COMPUTED"}, issues)
