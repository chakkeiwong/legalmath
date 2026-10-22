"""Reviewed links to inspected existing meanings, not inferred governing scopes."""

# Every relationship below was authored after reading the original declaration
# and the indicated current clause field. No search/overlap creates a link.
LINKS = {
    'D01': ('basf-amount:issue-amount', 'amount_reading', 'SERIES_IDENTITY_WITH_CONTEXT_EXCEPTIONS', 'This series is named in the issue clause; generic debt and further issues require separate use decisions.'),
    'D02': ('basf-amount:issue-amount', 'amount_reading', 'INITIAL_IDENTITY_WITH_SUCCESSION', 'BASF SE is the initial issuer; section10 succession cannot be replaced by a permanent name substitution.'),
    'D03': ('basf-amount:issue-amount', 'amount_reading.currency', 'DECLARATION_CONTENT_REPRESENTED', 'EUR is the specified currency; link payment and substitution uses separately.'),
    'D04': ('basf-amount:issue-amount', 'amount_reading.denomination', 'DECLARATION_CONTENT_REPRESENTED', 'The denomination is100000EUR, distinct from aggregate principal and actual holdings.'),
    'D05': ('basf-records:form-authentication', 'records_reading.initial_form', 'DECLARATION_CONTENT_REPRESENTED', 'Temporary global note without coupons; exchange and certification prerequisites remain separate.'),
    'D06': ('basf-records:form-authentication', 'records_reading.exchange_form', 'DECLARATION_CONTENT_REPRESENTED', 'Permanent global note is the specified exchange form, not the temporary certificate.'),
    'D07': ('basf-records:clearing-definition', 'records_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Named clearing systems and functional successors are represented; an actual successor is unproved.'),
    'D08': ('basf-records:clearing-definition', 'records_reading.reading', 'DECLARATION_CONTENT_REPRESENTED', 'The CBL alias occurs in the complete supplied clearing reading.'),
    'D09': ('basf-records:clearing-definition', 'records_reading.reading', 'DECLARATION_CONTENT_REPRESENTED', 'Euroclear names the bank in that reading; an account or current operator is not established.'),
    'D10': ('basf-records:clearing-definition', 'records_reading.reading', 'DECLARATION_CONTENT_REPRESENTED', 'Each system is an ICSD and the pair are ICSDs; register uses must preserve each versus both.'),
    'D11': ('basf-records:ngn-custody', 'records_reading', 'DECLARATION_CONTENT_REPRESENTED', 'NGN form and common-safekeeper arrangement are represented without actual custody.'),
    'D12': ('basf-amount:holder-definition', 'amount_reading', 'HOLDER_WITH_THIRD_PARTY_EXCEPTIONS', 'Co-ownership or a comparable right is represented; generic creditors and actual standing require separate treatment.'),
    'D13': ('basf-pledge:capital-market-debt', 'pledge_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Borrowed money, securities, original maturity and potential marketability conditions are present; no debt is factually classified.'),
    'D14': ('basf-payment:coupon_dates', 'legal_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Annual8March dates are represented separately from payment-day adjustment and maturity.'),
    'D15': ('basf-payment:day_count', 'legal_reading', 'FORMULA_WITH_UNDECLARED_DENOMINATOR', 'The day-count relation is represented; the meaning of Zinsperiode is not supplied by the declaration.'),
    'D16': ('basf-payment:day_count', 'legal_reading', 'DECLARATION_CONTENT_REPRESENTED', 'The calculation interval is represented; it is not by that fact the denominator period.'),
    'D17': ('basf-payment:payment_currency', 'legal_reading', 'CITATION_SUMMARY_NOT_LEGAL_APPLICATION', 'The IRC references are represented; the citation alias is not proof of applicable tax law.'),
    'D18': ('basf-payment:payment_day', 'legal_reading', 'PURPOSE_LIMITED_DECLARATION', 'Weekend, clearing and TARGET2 conditions are represented; calculation-day import requires a source-specific link.'),
    'D19': ('basf-payment:payment_day', 'legal_reading', 'SOURCE_LABEL_SUMMARY', 'TARGET2 is retained as named in the contract; this does not supply a current calendar.'),
    'D20': ('basf-redemption:maturity', 'legal_reading', 'MATURITY_WITH_GENERIC_DUE_DATE_EXCEPTIONS', '8March2032 maturity is represented; generic Fälligkeit elsewhere is not automatically this date.'),
    'D21': ('basf-redemption:nominal-amount-definition', 'amount_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Nominal redemption is represented; compounds and purpose-limited early amounts are distinct.'),
    'D22': ('basf-redemption:control_put', 'legal_reading', 'CONDITIONAL_EVENT_REPRESENTED', 'Control and causal rating together create the event; actual facts and exercise remain open.'),
    'D23': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'QUALIFIED_AGENCY_PREMISE_ONLY', 'The complete source lists agencies, successors and issuer-selected agencies; evaluation currently takes agency qualification as a premise.'),
    'D24': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'SOURCE_ALIAS_NOT_TYPED_AGENCY_MAPPING', 'S&P and its source scale are retained in the clause quotation, but this premise does not type the agency identity or classify raw rating symbols.'),
    'D25': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'SOURCE_ALIAS_NOT_TYPED_AGENCY_MAPPING', 'Moodys and its source scale are retained; raw rating classification is not established by the generic rating premise.'),
    'D26': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'SOURCE_ALIAS_NOT_TYPED_AGENCY_MAPPING', 'Fitch and its source scale are retained; two slash-adjacent names are withheld by standalone discovery, independently of conditional rating evaluation.'),
    'D27': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'CONDITIONAL_EVENT_REPRESENTED', 'Withdrawal/downgrade, window and causation are represented without asserting actual rating events.'),
    'D28': ('basf-redemption:control_put', 'scenario_premises.control_put.control.definition', 'CONDITIONAL_EVENT_REPRESENTED', 'More than50percent and attributed voting rights are represented; actual control and statutory attribution remain conditional.'),
    'D29': ('basf-redemption:control_put', 'scenario_premises.control_put.control.definition', 'CONDITIONAL_PERSON_SCOPE', 'Person/concert-party/third-party roles are in the control premise; no actual relevant person is identified.'),
    'D30': ('basf-redemption:control_put', 'scenario_premises.control_put.rating.definition', 'CONDITIONAL_PERIOD_REPRESENTED', 'The120day rating period is distinct from the45day exercise period.'),
    'D31': ('basf-redemption:control_put', 'scenario_premises.control_put.payment_day.definition', 'EXPLICIT_APPLICATION_AVAILABLE', 'The fifteenth-day relation is already bound only to holder-option uses by the application supplement.'),
    'D32': ('basf-redemption:control_put', 'scenario_premises.control_put.event_notice.definition', 'PURPOSE_LIMITED_NOTICE', 'Holder-option event notice is represented; issuer call notices are not the same notice.'),
    'D33': ('basf-redemption:control_put', 'scenario_premises.control_put.timely_exercise.definition', 'CONDITIONAL_PERIOD_REPRESENTED', '45days and17:00Frankfurt cutoff are represented with absent actual publication facts.'),
    'D34': ('basf-redemption:control_put', 'scenario_premises.control_put.valid_declaration.definition', 'PURPOSE_LIMITED_DECLARATION', 'Form, irrevocability, identifiers and receipt requirements are represented; office authority remains unresolved.'),
    'D35': ('basf-redemption:early_call', 'legal_reading', 'PURPOSE_LIMITED_CALL', 'The issuer make-whole call date remains distinct from holder-option and table-call dates.'),
    'D36': ('basf-redemption:makewhole-definition', 'amount_reading', 'BENCHMARK_READING_WITH_MISSING_INPUTS', 'Comparable German euro benchmark and spread are represented; selection, observations and office facts remain absent.'),
    'D37': ('basf-redemption:makewhole-definition', 'amount_reading', 'AMBIGUOUS_CALCULATION_DAY_TARGET', 'The third-payment-day relation exists, but Wahl-Rückzahlungstag versus Vorzeitiger Wahl-Rückzahlungstag is not adjudicated.'),
    'D38': ('basf-global:united-states-definition', 'global_reading', 'EXPRESS_TERMS_SCOPE', 'Contractual geography expressly applies throughout these terms and does not define U.S.-person status.'),
    'D39': ('basf-payment:gross_up', 'legal_reading', 'GROSS_UP_WITH_SEPARATE_FINAL_EXCLUSION', 'All(a)-(e)exceptions are represented; the separate German-flat-tax clause must also be retained.'),
    'D40': ('basf-governance:substitution', 'legal_reading', 'CONDITIONAL_SUCCESSION', 'Successor identity depends on all(a)-(e)conditions; contractual legal confirmations are actual-event premises, not a build prerequisite.'),
    'D41': ('basf-governance:affiliate', 'legal_reading', 'EXPLICIT_APPLICATION_AVAILABLE', 'Express section10 statutory-reference rule exists without proof of actual affiliation or historical application.'),
    'D42': ('basf-governance:amendment_agreement', 'legal_reading', 'CITATION_SUMMARY_NOT_LEGAL_APPLICATION', 'SchVG-based agreement is represented; historical scope and open sections5onward are not closed by the acronym.'),
    'D43': ('basf-governance:notice_publication', 'legal_reading', 'PURPOSE_LIMITED_NOTICE', 'Meeting-call content and publication exist; other notices and compound components need separate decisions.'),
    'D44': ('basf-governance:jurisdiction', 'legal_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Actions/proceedings and nonexclusive Frankfurt jurisdiction are represented with procedural-law uncertainty.'),
    'D45': ('basf-notices:holding-proof', 'procedural_reading', 'EXPLICIT_APPLICATION_AVAILABLE', 'Custodian criteria govern the express preceding enforcement context; earlier section7/11uses remain unresolved.'),
    'U01': ('basf-records:records-evidence', 'records_reading', 'DECLARATION_CONTENT_REPRESENTED', 'Each ICSD customer register and contractual evidential role are represented without balances or court effect.'),
    'U02': ('basf-payment:principal_definition', 'legal_reading', 'EXPRESS_TERMS_SCOPE', 'Principal categories are implemented in the payment-category profile; no actual payment amount follows.'),
    'U03': ('basf-payment:interest_definition', 'legal_reading', 'EXPRESS_TERMS_SCOPE', 'Applicable section7additional amounts are included; exceptions and amount classification remain conditional.'),
    'U04': ('basf-redemption:par_call', 'legal_reading', 'TABLE_CALL_WITH_AMBIGUOUS_REUSE', 'The source table window is represented; the later calculation-day wording is not thereby disambiguated.'),
    'U05': ('basf-redemption:par_call', 'amount_reading', 'PURPOSE_LIMITED_AMOUNT', 'The table call uses aggregate nominal of redeemed notes, distinct from make-whole value.'),
    'U06': ('basf-redemption:early-amount-definition', 'amount_reading', 'EXPLICIT_APPLICATION_AVAILABLE', 'Tax amount equality is already bound within its purpose; identical make-whole spelling cannot inherit it.'),
    'U07': ('basf-redemption:makewhole-definition', 'amount_reading', 'EXPLICIT_APPLICATION_AVAILABLE', 'Make-whole maximum is already bound within its purpose; tax contexts cannot inherit it.'),
    'U08': ('basf-agents:initial-agent', 'agent_reading', 'INITIAL_APPOINTMENT_WITH_CHANGE_RULE', 'Initial Fiscal Agent and designated office are represented; changes and actual appointment remain separate.'),
    'U09': ('basf-agents:initial-agent', 'agent_reading', 'INITIAL_APPOINTMENT_WITH_CHANGE_RULE', 'Initial Paying Agent is represented; shared institution does not collapse contractual roles.'),
    'U10': ('basf-agents:initial-agent', 'agent_reading', 'OFFICE_AND_CONSTRUCTION_UNRESOLVED', 'Final terms name NatWest, but the combined template name/office remains unresolved; do not fill it from another role.'),
    'U11': ('basf-payment:gross_up', 'legal_reading', 'CITATION_SUMMARY_NOT_LEGAL_APPLICATION', 'Tax-haven-act title/date and exclusion are represented without residence or actual jurisdiction facts.'),
    'U12': ('basf-redemption:control_put', 'scenario_premises.control_put.control.definition', 'CITATION_SUMMARY_NOT_LEGAL_APPLICATION', 'Section30(2)WpUEG reference is represented; statutory source/application remain separately qualified.'),
    'U13': ('basf-governance:representative_appointment', 'legal_reading', 'ROLE_WITH_SEPARATE_POWER_CONDITIONS', 'Appointment authority is represented; actual appointment and exercise powers depend on further rules and facts.'),
    'M01': ('basf-payment:day_count', 'legal_reading', 'MISSING_DECLARATION', 'The formula names a relevant interest period but supplies no source declaration for Zinsperiode; no historical definition may be imported.'),
    'M02': ('basf-global:exchange-certification', 'global_reading', 'EXTERNAL_STATUS_DEFINITION_MISSING', 'The certification condition and exceptions exist; contractual territory does not determine U.S.-person status.'),
    'M03': ('basf-governance:participation_proof', 'legal_reading', 'UNQUOTED_OPERATIONAL_DESCRIPTION', 'Voting-ticket agent and blocking/deposit route are represented despite absence from quoted-alias grammar.'),
    'M04': ('basf-governance:voting_chair', 'legal_reading', 'CONTEXTUAL_ROLE_LINK_REQUIRED', 'The chair-selection rule exists, but the later Abstimmungsleiter use needs a source-reasoned identity link.'),
}

RULE_FOR_RECORD = {'D31': 'holder', 'D41': 'affiliate', 'D45': 'custodian', 'U06': 'tax', 'U07': 'makewhole'}

# Independently enumerated from the selected prose and retained application
# source review, before the reconciliation or a binding implementation runs.
EXPECTED_USE_CLASSES = {
    'D31': {
        'EXISTING_CONDITIONAL_APPLICATION': [14004, 15619],
        'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': [17433, 17517, 17664, 17737, 18238, 19090, 19202, 19681, 21229, 22997],
    },
    'D41': {'EXISTING_CONDITIONAL_APPLICATION': [32403, 34040],
            'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': [34069]},
    'D45': {'EXISTING_CONDITIONAL_APPLICATION': [44711, 45051, 45657],
            'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': [26168, 38657]},
    'U06': {'EXISTING_CONDITIONAL_APPLICATION': [11831, 21403],
            'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': [10213], 'OTHER_PURPOSE_DEFINITION': [19119]},
    'U07': {'EXISTING_CONDITIONAL_APPLICATION': [19119],
            'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': [10213], 'OTHER_PURPOSE_DEFINITION': [11831, 21403]},
}


def field(node, path):
    # Premise names contain dots: split that namespace deliberately.
    if path.startswith('scenario_premises.'):
        return node['scenario_premises'][path[len('scenario_premises.'):-len('.definition')]]['definition']
    value = node
    for key in path.split('.'):
        value = value[key]
    return value


def use_disposition(record_id, application):
    expected = RULE_FOR_RECORD.get(record_id.split('-')[0])
    if application is None:
        return 'GOVERNING_USE_NOT_RECONCILED'
    if application['rule'] is None:
        return 'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE'
    if application['rule'] == expected:
        return 'EXISTING_CONDITIONAL_APPLICATION'
    return 'OTHER_PURPOSE_DEFINITION'
