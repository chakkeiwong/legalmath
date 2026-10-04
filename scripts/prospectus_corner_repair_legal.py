"""Declared legal-rule fixtures tied to the independently preserved source passages."""
from copy import deepcopy
from pathlib import Path
from collections import Counter
import json
from legalmath.prospectus.external_law import evaluate_rule, investigate
from scripts.prospectus_corner_repair_worker import ROOT, OUT, DATA, OLD, read, write

def fact(name):return {"fact":name}
def both(*nodes):return {"all":list(nodes)}
def not_(node):return {"not":node}

def run(folder):
    specs={r["id"]:r for r in read(OLD/"test-specifications.json")["cases"]}
    sources={r["key"]:r for r in read(DATA/"source-index.json")["sources"]}
    new_data=ROOT/"docs/prospectus/corner-repair-2026-10-04"
    extra=read(new_data/"source-index.json")["sources"]
    historic=next(s for s in extra if s["key"]=="jur-repair-italy-130-art4")
    sources[historic["key"]]=historic
    article4_anchor={"source_key":historic["key"],"source_sha256":historic["sha256"],
        "method":"retained_official_html",
        "quote":"Ai pagamenti effettuati dai debitori ceduti alla società cessionaria non si applica l' articolo 67 del regio decreto 16 marzo 1942, n. 267"}
    scenarios=[]
    def add(case, stage, conclusion, condition, facts, *, scope=None, context=None,
            expected_status="CONDITIONAL", expected_value=True, arithmetic=None):
        scope=scope or {"forum":["declared_relevant_forum"],"claim_type":["declared_relevant_claim"]}
        ctx={k:v[0] for k,v in scope.items()}
        ctx.update(known_at="2026-10-04",requested_stage=stage,facts={k:[v] for k,v in facts.items()})
        ctx.update(context or {})
        # CC02's scan is preserved in the full specification. Its OCR is not silently
        # substituted here: the judgment anchor and unknown identifier premise remain.
        anchors=[a for a in specs[case]["anchors"] if a["method"]!="rendered_transcription"]
        rule={"id":case+"-declared-rule","stage":stage,"conclusion":conclusion,
              "condition":condition,"anchors":anchors,"scope":scope,"source_date":"2026-10-04",
              "source_date_basis":"Availability of the locally reviewed corpus; not the law's effective date or externally attested historical possession",
              "interpretation_status":"SOURCE_REVIEWED_INDEPENDENT_ADJUDICATION_PENDING"}
        if arithmetic:rule["arithmetic"]=arithmetic
        scenarios.append({"case":case,"rule":rule,"context":ctx,
                          "expected":{"status":expected_status,"value":expected_value},
                          "scope":"Declared-premise engineering scenario; not an observed complete legal outcome"})
    add("CC02","identity","exact_identifier_link",
        fact("annex_identifier_verified"),{"annex_identifier_verified":None},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC06","recognition","publication_omission_does_not_itself_bar_pre_suit_recognition",
        both({"before":["measure_date","suit_date"]},fact("recognition_regime_applies"),fact("effective_appeal_access_preserved")),
        {"measure_date":"2015-12-29","suit_date":"2017-01-01","recognition_regime_applies":True,
         "effective_appeal_access_preserved":True})
    add("CC07","recognition","unconditional_retroactive_recognition_precluded",
        both({"before":["suit_date","retransfer_date"]},fact("favourable_prior_decision"),
             fact("retroactive_defendant_removal")),
        {"suit_date":"2015-02-04","retransfer_date":"2015-12-29","favourable_prior_decision":True,
         "retroactive_defendant_removal":True},scope={"claim_type":["share_sale_liability"],"forum":["ES"]})
    add("CC08","liability_perimeter","oak_liability_never_transferred",
        fact("applicable_perimeter_decision"),{"applicable_perimeter_decision":True},
        scope={"claim_type":["Oak_loan"],"forum":["UK"]},context={"claim_type":"BES_bond"},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC09","administrative_effect","act_continues_under_unsuspended_unannulled_premises",
        both(not_(fact("annulled")),not_(fact("suspended"))),
        {"challengeable":True,"annulled":False,"suspended":None},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC10","issuer_report","reported_maturity_stay",
        both(fact("notice_reports_maturity_change"),fact("claim_within_described_bucket")),
        {"notice_reports_maturity_change":True,"claim_within_described_bucket":True})
    add("CC11","issuer_report","reported_remaining_nonsubordinated_bucket",
        both(fact("nonsubordinated_bucket"),fact("interest_bucket_through_2015_02_28")),
        {"nonsubordinated_bucket":True,"interest_bucket_through_2015_02_28":True,"remaining":"46.02"},
        arithmetic={"remaining_percent":"remaining"})
    add("CC12","entity_identity","renamed_legal_entity",
        fact("same_legal_entity"),{"same_legal_entity":None},
        scope={"issuer":["HETA Asset Resolution AG"]},context={"issuer":"Adriano Lease Sec. S.R.L."},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC13","holding","english_purchase_undertaking_enforceable_under_judgment",
        both(fact("purchase_undertaking"),fact("english_law_obligation"),fact("judgment_risk_allocation_applies")),
        {"purchase_undertaking":True,"english_law_obligation":True,"judgment_risk_allocation_applies":True},
        scope={"obligation":["English purchase undertaking"]})
    add("CC14","assumption","uae_invalidity_assumed_for_preliminary_issue",
        fact("assumed_for_argument"),{"assumed_for_argument":True},
        context={"requested_stage":"finding_of_illegality"},expected_status="UNRESOLVED",expected_value=None)
    add("CC15","regulatory_call","optional_early_redemption_enabled",
        fact("capital_disqualification_event"),{"capital_disqualification_event":True},
        scope={"provision":["regulatory_call"],"voice":["majority"]})
    add("CC16","holding","trustee_appeal_dismissed",
        fact("capital_disqualification_event"),{"capital_disqualification_event":True},
        scope={"voice":["majority"]},context={"voice":"dissent"},expected_status="UNRESOLVED",expected_value=None)
    add("CC17","procedural","specified_duress_defence_may_proceed",
        fact("arguable_force_based_duress"),{"arguable_force_based_duress":True},
        context={"requested_stage":"debt_discharge"},expected_status="UNRESOLVED",expected_value=None)
    add("CC18","national_authority","national_burden_sharing_power_established",
        fact("independent_national_authority_established"),{"commission_communication_present":True,
        "independent_national_authority_established":None},expected_status="UNRESOLVED",expected_value=None)
    add("CC19","official_reorganisation","authority_adopted_reorganisation",
        fact("administrative_or_judicial_action"),{"administrative_or_judicial_action":False,"private_arrangement":True},
        expected_value=False)
    add("CC20","jurisdiction_classification","outside_civil_commercial_matters",
        fact("specified_sovereign_act"),{"specified_sovereign_act":True},
        context={"requested_stage":"haircut_merits"},expected_status="UNRESOLVED",expected_value=None)
    add("CC21","share_remedies","specified_post_resolution_share_remedy_limit",
        both(fact("total_share_write_down"),fact("specified_prospectus_or_nullity_claim")),
        {"total_share_write_down":True,"specified_prospectus_or_nullity_claim":True},
        scope={"security_class":["shares"]},context={"security_class":"bonds"},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC22","deposit_exclusion","negotiable_certificate_exclusion_under_national_option",
        both(fact("negotiable"),fact("national_exclusion_option_exercised")),
        {"negotiable":None,"national_exclusion_option_exercised":True},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC23","investor_compensation","investment_service_return_failure_condition",
        both(fact("covered_investment_service"),fact("inability_to_return_client_money_or_instruments")),
        {"covered_investment_service":True,"inability_to_return_client_money_or_instruments":False,
         "issuer_credit_default":True},expected_value=False)
    add("CC04","guarantee_scope","BES_guarantee_supports_BES_Finance_issuance",
        fact("guarantee_clause_selected"),{"guarantee_clause_selected":True},
        scope={"issuer":["BES Finance Ltd."]},context={"issuer":"Banco Espírito Santo, S.A."},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC24","credit_support","regional_receivable_does_not_supply_note_guarantee",
        fact("express_note_guarantee"),{"regional_receivable":True,"express_note_guarantee":False},
        expected_value=False)
    add("CC25","enforcement","specified_public_funds_attachable",
        both(fact("attachment_requirements_met"),not_(fact("protected_fund_conditions_hold"))),
        {"pari_passu":True,"attachment_requirements_met":None,"protected_fund_conditions_hold":None},
        expected_status="UNRESOLVED",expected_value=None)
    add("CC26","enforcement_timing","disclosed_120_day_wait_satisfied",
        both({"elapsed_days_at_least":["notification","proposed_execution",120]},
             fact("enforceable_instrument_and_payment_request_served")),
        {"notification":"2011-01-01","proposed_execution":"2011-05-01",
         "enforceable_instrument_and_payment_request_served":True})
    add("CC27","receivable_timing","regional_delegations_accelerated",
        fact("underlying_debt_accelerated"),
        {"issuer_acceleration_notice":True,"underlying_debt_accelerated":False},expected_value=False)
    add("CC30","clawback","article65_exemption_follows_from_article67",
        fact("specific_article65_exemption"),
        {"article67_exemption":True,"specific_article65_exemption":False},expected_value=False)
    next(s for s in scenarios if s["case"]=="CC30")["rule"]["anchors"].append(article4_anchor)
    write(folder/"rule-scenarios.json",scenarios)
    write(folder/"source-registry.json",sources)
    rows=[]
    for scenario in scenarios:
        value=evaluate_rule(scenario["rule"],scenario["context"],sources,ROOT)
        expected=scenario["expected"]
        checked=(value["status"]==expected["status"] and
                 value["value_under_declared_premises"] is expected["value"])
        rows.append({"case":scenario["case"],"engineering_check":"PASS" if checked else "FAIL","result":value})
    write(folder/"legal-results.json",rows)
    assert len(rows)==25
    return {"status":"PASS" if all(r["engineering_check"]=="PASS" for r in rows) else "FAIL",
            "declared_scenarios":len(rows),"checks_passed":sum(r["engineering_check"]=="PASS" for r in rows),
            "rule_results":dict(Counter(r["result"]["status"] for r in rows)),
            "independent_legal_adjudication":False,"legal_accuracy":"NOT_MEASURED",
            "meaning":"Executable scope/date/premise checks over reviewed source interpretations, not autonomous legal reading."}
