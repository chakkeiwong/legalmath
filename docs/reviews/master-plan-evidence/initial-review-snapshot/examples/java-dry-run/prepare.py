"""Rebuild synthetic, source-anchored inputs; never record fictitious approval."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AT = "2026-09-21T02:00:00.000000Z"  # 10:00 Hong Kong
EARLY = "2026-09-01T00:00:00.000000Z"
LATE = "2026-10-01T00:00:00.000000Z"


def save(name, value):
    (HERE / "spec" / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def build():
    source = ROOT / ".localresources/sfc/23EC35-annex1.txt"
    text = source.read_text().removeprefix("\ufeff").replace("\r\n", "\n")
    pdf = source.with_suffix(".pdf")
    sha = lambda b: hashlib.sha256(b).hexdigest()
    headings = list(re.finditer(r"(?m)^[ \t\f]*(\d{1,2}\.\d|\d{1,2}\.)(?= |\n)", text))
    spans = {}
    for i, h in enumerate(headings):
        key = h.group(1).rstrip(".")
        start, end = h.start(1), headings[i+1].start() if i+1 < len(headings) else len(text)
        spans[key] = dict(id="spi.annex1."+key, source_id="23EC35/annex1",
                          raw_sha256=sha(pdf.read_bytes()), text_sha256=sha(text.encode()),
                          page=text[:start].count("\f")+1, start=start, end=end,
                          quote_sha256=sha(text[start:end].encode()))
    faq_path = ROOT / ".localresources/sfc/23EC35-annex2.txt"
    faq = faq_path.read_text().removeprefix("\ufeff").replace("\r\n", "\n")
    faq_headings = list(re.finditer(r"(?m)^[ \t\f]*([1-7])\.(?=\s)", faq))
    for i,h in enumerate(faq_headings):
        key = "faq." + h.group(1)
        start, end = h.start(1), faq_headings[i+1].start() if i+1<len(faq_headings) else len(faq)
        spans[key] = dict(id="spi.annex2."+h.group(1), source_id="23EC35/annex2",
                         raw_sha256=sha(faq_path.with_suffix(".pdf").read_bytes()), text_sha256=sha(faq.encode()),
                         page=faq[:start].count("\f")+1, start=start, end=end,
                         quote_sha256=sha(faq[start:end].encode()))
    used, facts, rules = set(), {}, []
    counter = 0

    def node(op, **kwargs):
        nonlocal counter
        counter += 1
        return dict(node_id=f"n{counter}", op=op, **kwargs)

    def f(name, typ="bool"):
        facts[name] = typ
        return node("fact", name=name)

    def lit(value, typ="bool"):
        return node("literal", type=typ, value=value)

    def ref(name):
        return node("rule", name="spi."+name)

    def group(op, *args):
        return node(op, args=list(args))

    def ge(left, right):
        return node("compare", cmp="ge", left=left, right=right)

    def rule(name, body, paragraphs, scope=None, interpretation="meaning.demo"):
        used.update(paragraphs)
        rules.append(dict(id="spi."+name, type="bool", scope=scope or lit(True),
                          body=body, interpretation_id=interpretation,
                          source_span_ids=[spans[p]["id"] for p in paragraphs]))

    rule("financial", group("any", ge(f("portfolio", "money_hkd"), lit("4000000000", "money_hkd")),
                            ge(f("net_assets_ex_home", "money_hkd"), lit("8000000000", "money_hkd"))), ["3.1", "3.2", "3.3", "3.4"])
    rule("category_qualification", group("any", f("relevant_degree"), f("professional_qualification"),
         f("relevant_year_of_work"), ge(f("category_transactions_3y", "integer"), lit("5", "integer"))), ["4.1", "7.3", "faq.2", "faq.3"])
    rule("assessment", group("all", f("individual_pi"), ref("financial"), ref("category_qualification"),
         f("reasonable_sophistication_assessment"), f("non_conservative_objectives"), f("written_assessment_retained")), ["1", "4.1", "5.1", "12.1", "12.2", "faq.1"])
    rule("threshold", ge(f("streamlining_threshold", "money_hkd"), f("projected_gross_exposure", "money_hkd")), ["6", "8.1", "8.3", "faq.6", "faq.7"])
    rule("explanation", group("any", node("not", arg=f("explanation_requested_or_material_query")), f("explanation_delivered")), ["10.3"])
    rule("warning", group("all", f("transaction_materiality_assessed"), group("any", node("not", arg=f("outsize_or_material_transaction")), f("material_warning_delivered"))), ["8.4"])
    rule("retained_information", group("all", f("current_offering_documents_delivered"), ref("explanation"), ref("warning")), ["8.4", "10.3"])
    rule("review_policy", f("annual_review_current"), ["8.5", "14.1", "14.2"],
         interpretation="meaning.annual_review_policy")
    rule("arrangement", group("all", f("category_selected"), f("category_information_delivered"),
         f("category_explanation_resolved"), f("prior_written_acknowledgment_complete"), f("active_consent"),
         f("threshold_rationale_retained"), ref("review_policy")), ["7.2", "8.2", "8.5", "12.3", "13.1", "13.2", "14.1", "14.2", "faq.4", "faq.5"])
    rule("streamlining", group("all", ref("assessment"), ref("arrangement"), ref("threshold"), ref("retained_information")),
         ["1", "6", "9", "10.1", "10.2", "10.3", "10.4"],
         scope=group("all", f("profile_individual"), f("profile_solicited"), f("profile_execution_monitoring")))
    bundle = dict(spec_version="0.1", bundle_id="spi.demonstration", valid_from=EARLY, valid_until=LATE,
                  source_spans=[spans[p] for p in sorted(used)],
                  interpretations=[dict(id="meaning.demo", statement="Synthetic individual/solicited/8.3(a) profile. Annual-review gating is a proposed bank restriction. Evidence composites and applicability need bank approval. No production authority.",
                       basis="reviewer_interpretation", source_span_ids=[spans[p]["id"] for p in sorted(used)],
                       issue_ids=["issue.bank_review", "issue.imported_definitions", "issue.currency_policy", "issue.host_mapping", "issue.calendar_policy"]),
                       dict(id="meaning.annual_review_policy", statement="Proposed additional bank restriction: suspend the streamlined route unless the annual review, reminder and threshold-compliance obligations are confirmed current. The circular requires those duties; it does not prescribe this automatic suspension consequence.",
                            basis="bank_policy", source_span_ids=[spans[p]["id"] for p in ["8.5","14.1","14.2"]], issue_ids=["issue.bank_review", "issue.calendar_policy"])],
                  facts=[dict(name=n, type=t, description=n.replace("_", " ")) for n,t in sorted(facts.items())], rules=rules)
    save("spi-control.bundle.json", bundle)
    disposition = {
        "1":"Individual qualification decision with reviewed imported PI status",
        "2":"Outside profile: investment-holding corporations need separate ownership rules",
        "3.1":"Executable inclusive wealth alternatives",
        "3.2":"Reviewed portfolio ownership normalization; every subparagraph retained",
        "3.3":"Reviewed assets minus liabilities minus primary residence normalization",
        "3.4":"Reviewed net-asset attribution; every ownership subparagraph retained",
        "4.1":"Qualification alternatives plus owned sophistication assessment",
        "5.1":"Owned objectives assessment; conservative clients excluded",
        "6":"Root category/threshold restriction",
        "7.1":"Bank-owned product-category taxonomy and mapping",
        "7.2":"Documented selection, information and requested category explanation",
        "7.3":"Category-specific qualification routes",
        "8.1":"Agreed threshold; percentage/AUM conversion is a reviewed input mapping",
        "8.2":"Recorded client circumstances and threshold rationale",
        "8.3":"Execute (a); (b) designated-account profile explicitly excluded",
        "8.4":"Assessment and conditional transaction warning",
        "8.5":"Continuing review/alert task; current status is a reviewed input",
        "9":"Select solicited profile; unsolicited complex product profile excluded",
        "10.1":"Identify scoped relief for host matching controls; no blanket waiver",
        "10.2":"Identify scoped transaction assessment relief for the host",
        "10.3":"Retain offering documents and request/material-query explanation",
        "10.4":"Identify scoped recommendation-rationale relief for the host",
        "11.1":"Outside profile; retain document alternatives and footnote dependencies",
        "11.2":"Outside profile: unsolicited complex-product matching relief",
        "11.3":"Outside profile: unsolicited complex-product assessment relief",
        "11.4":"Outside profile: retained information and request/material-query explanation",
        "11.5":"Outside profile: annual complex-product warning",
        "12.1":"Owned reasonable-satisfaction assessment",
        "12.2":"Written assessment evidence",
        "12.3":"Category/threshold correspondence record",
        "13.1":"Prior written agreement/checklist and withdrawal rights; all items (a)-(d)",
        "13.2":"Consequences/explanations checklist: every numbered and lettered item retained",
        "14.1":"Annual continued-qualification/agreement review task; date mapping unresolved",
        "14.2":"Annual written reminders and required breach alerts; all items retained",
        "faq.1":"Admissible disclosures and inconsistency follow-up evidence policy",
        "faq.2":"Attribute qualification to client; preserve permitted POA/joint transaction evidence",
        "faq.3":"Bank-owned category distinctions and VA footnote dependency",
        "faq.4":"Category information and requested explanation evidence",
        "faq.5":"Threshold assessment/rationale; no invented universal percentage",
        "faq.6":"Execution monitoring in scope; preserve all designated-account/top-up distinctions",
        "faq.7":"Leverage-inclusive gross exposure input mapping"
    }
    structural = {"3","4","5","7","8","10","11","12","13","14"}
    assert set(spans) <= set(disposition) | structural, set(spans)-set(disposition)-structural
    inventory=[dict(locator=k, source_span=span, disposition=disposition.get(k,"Section heading; detailed provisions listed separately"),
                    rule_ids=[r["id"] for r in rules if span["id"] in r["source_span_ids"]])
               for k,span in spans.items()]
    save("circular-disposition.json", dict(status="DRAFT_REQUIRES_BANK_REVIEW", main_text="Authority and attachment/dependency register; not a standalone eligibility rule", opening="Conduct/red-flag controls and imported Professional Investor Rules/Code definitions remain dependencies", numbered_provisions=inventory))

    def known(typ, value):
        return dict(status="known", type=typ, value=value, evidence_ids=["synthetic.case"],
                    valid_from=EARLY, valid_until=LATE, recorded_at=EARLY)

    baseline = {n: known(t, True if t == "bool" else "0") for n,t in facts.items()}
    values = dict(portfolio="4000000000", net_assets_ex_home="7500000000", category_transactions_3y="5",
                  relevant_degree=False, professional_qualification=False, relevant_year_of_work=False,
                  streamlining_threshold="1000000000", projected_gross_exposure="1000000000",
                  explanation_requested_or_material_query=False, explanation_delivered=False,
                  outsize_or_material_transaction=False, material_warning_delivered=False)
    for n, v in values.items():
        baseline[n]["value"] = v
    cases = []

    def case(name, edits, expected, blockers=(), **times):
        snap = deepcopy(baseline)
        for key, value in edits.items():
            snap[key] = value if isinstance(value, dict) else known(facts[key], value)
        cases.append(dict(id=name, snapshot=dict(subject_id="client.synthetic.lee", facts=snap),
                          valid_at=times.get("valid_at", AT), known_at=times.get("known_at", AT),
                          expected_status=expected, expected_blocking_inputs=sorted(blockers)))

    unknown = lambda n: dict(status="unknown", type=facts[n], reason="MISSING")
    case("boundary_both_limits", {}, "TRUE")
    case("portfolio_one_cent_below", {"portfolio":"3999999999"}, "FALSE")
    case("net_asset_alternative", {"portfolio":"3500000000", "net_assets_ex_home":"9000000000"}, "TRUE")
    case("net_asset_exact_boundary", {"portfolio":"0", "net_assets_ex_home":"8000000000"}, "TRUE")
    case("unknown_portfolio_sufficient_assets", {"portfolio":unknown("portfolio"), "net_assets_ex_home":"9000000000"}, "TRUE")
    case("unknown_portfolio_insufficient_assets", {"portfolio":unknown("portfolio"), "net_assets_ex_home":"7000000000"}, "UNKNOWN", ["portfolio"])
    case("wealth_conflict", {"portfolio":dict(status="conflict", type="money_hkd", evidence_ids=["report.a","report.b"])}, "CONFLICT", ["portfolio"])
    case("conservative_objectives", {"non_conservative_objectives":False}, "FALSE")
    case("assessment_unreviewed", {"reasonable_sophistication_assessment":unknown("reasonable_sophistication_assessment")}, "UNKNOWN", ["reasonable_sophistication_assessment"])
    case("four_transactions_no_other_qualification", {"category_transactions_3y":"4"}, "FALSE")
    case("degree_alternative", {"category_transactions_3y":"0", "relevant_degree":True}, "TRUE")
    case("wrong_category", {"category_selected":False}, "FALSE")
    case("missing_category_statement", {"category_information_delivered":False}, "FALSE")
    case("missing_written_acknowledgment", {"prior_written_acknowledgment_complete":False}, "FALSE")
    case("withdrawn_consent", {"active_consent":False}, "FALSE")
    case("incomplete_consent_history", {"active_consent":unknown("active_consent")}, "UNKNOWN", ["active_consent"])
    case("one_cent_over_exposure", {"projected_gross_exposure":"1000000001"}, "FALSE")
    case("missing_threshold_rationale", {"threshold_rationale_retained":False}, "FALSE")
    case("review_overdue_bank_restriction", {"annual_review_current":False}, "FALSE")
    case("offering_documents_required", {"current_offering_documents_delivered":False}, "FALSE")
    case("explanation_requested_unfulfilled", {"explanation_requested_or_material_query":True}, "FALSE")
    case("explanation_requested_fulfilled", {"explanation_requested_or_material_query":True, "explanation_delivered":True}, "TRUE")
    case("material_transaction_warning_absent", {"outsize_or_material_transaction":True}, "FALSE")
    case("material_transaction_warning_delivered", {"outsize_or_material_transaction":True, "material_warning_delivered":True}, "TRUE")
    case("materiality_not_assessed", {"transaction_materiality_assessed":unknown("transaction_materiality_assessed")}, "UNKNOWN", ["transaction_materiality_assessed"])
    case("corporate_outside_profile", {"profile_individual":False}, "OUT_OF_SCOPE")
    case("unsolicited_outside_profile", {"profile_solicited":False}, "OUT_OF_SCOPE")
    case("designated_account_outside_profile", {"profile_execution_monitoring":False}, "OUT_OF_SCOPE")
    case("unknown_profile", {"profile_solicited":unknown("profile_solicited")}, "UNKNOWN", ["profile_solicited"])
    stale = known("money_hkd", "4000000000"); stale["valid_until"] = AT
    case("evidence_expires_at_boundary", {"portfolio":stale}, "UNKNOWN", ["portfolio"])
    future = known("money_hkd", "4000000000"); future["recorded_at"] = LATE
    case("future_evidence_not_known", {"portfolio":future}, "UNKNOWN", ["portfolio"])
    case("huge_exact_integer", {"portfolio":"999999999999999999999999999999999999"}, "TRUE")
    save("decision-cases.json", cases)
    save("host-snapshot.json", cases[0]["snapshot"])

    grant = dict(id="consent.grant.1", kind="GRANTED", occurred_at=EARLY, recorded_at=EARLY, sequence=1)
    withdraw = dict(id="consent.withdraw.1", kind="WITHDRAWN", occurred_at="2026-09-21T02:05:00.000000Z", recorded_at="2026-09-21T02:06:00.000000Z", sequence=2)
    at_after = "2026-09-21T02:10:00.000000Z"
    consent_cases = []
    def cc(ident, events, expected, at=AT, known=AT, complete=None, complete_recorded=None):
        complete = at if complete is None else complete
        complete_recorded = known if complete_recorded is None else complete_recorded
        consent_cases.append(dict(id=ident, events=events, valid_at=at, known_at=known,
                complete_through=complete, completeness_recorded_at=complete_recorded, expected=expected))
    cc("before_withdrawal", [grant,withdraw], "TRUE")
    cc("after_withdrawal", [grant,withdraw], "FALSE", at_after, at_after)
    # Knowledge at 10:05 is incomplete; never reuse an obsolete completeness seal.
    cc("withdrawal_arriving_late", [grant,withdraw], "UNKNOWN", at_after, "2026-09-21T02:05:00.000000Z", complete="2026-09-21T02:04:00.000000Z")
    cc("duplicate_is_idempotent", [grant,grant], "TRUE")
    collision = dict(grant,kind="WITHDRAWN")
    cc("event_id_collision", [grant,collision], "CONFLICT")
    cc("no_consent_complete_history", [], "FALSE")
    cc("incomplete_history", [grant], "UNKNOWN", complete=EARLY)
    cc("future_completeness_not_known", [grant], "UNKNOWN", complete_recorded=LATE)
    cc("impossible_future_watermark", [grant], "UNKNOWN", complete=LATE, complete_recorded=AT)
    cc("equal_time_authoritative_sequence", [grant,dict(collision,id="consent.w",sequence=2)], "FALSE")
    cc("equal_time_unresolved_order", [grant,dict(collision,id="consent.w")], "UNKNOWN")
    save("consent-cases.json", consent_cases)


if __name__ == "__main__":
    build()
