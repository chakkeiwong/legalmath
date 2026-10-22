"""Source-bound supplied payment terms, without findings about actual events."""
from .anchors import bind
from .occurrences import segments


# These are reviewed readings, not patterns for extracting meaning from new text.
RULES = {
    'coupon_rate': {
        'reading': 'The notes bear interest on their aggregate principal at 4.250% per year from and including 8 March 2023 to but excluding the maturity date defined in section 5(1).',
        'scope': 'SELECTED_FIXED_RATE_AND_STATED_ACCRUAL_ENDPOINTS', 'actor': 'issuer',
    },
    'coupon_dates': {
        'reading': 'Interest is payable in arrears on 8 March of each year, each such date being an interest payment date.',
        'scope': 'ANNUAL_CONTRACTUAL_DATES', 'actor': 'issuer',
    },
    'first_coupon': {
        'reading': 'The first interest payment date is 8 March 2024.',
        'scope': 'FIRST_CONTRACTUAL_INTEREST_PAYMENT_DATE', 'actor': 'issuer',
    },
    'late_interest': {
        'reading': 'If the issuer does not redeem the notes at maturity, interest runs from maturity until actual repayment at the statutory default-interest rate.',
        'scope': 'FAILURE_TO_REDEEM_AT_MATURITY_STATUTORY_RATE_UNRESOLVED', 'actor': 'issuer',
    },
    'partial_period': {
        'reading': 'Interest for a period shorter than one year is calculated using the defined day-count fraction.',
        'scope': 'INTEREST_PERIOD_SHORTER_THAN_ONE_YEAR', 'actor': 'terms',
    },
    'day_count': {
        'reading': 'For the selected annual Actual/Actual option excluding short or long coupons, the day-count fraction is actual days in the calculation period divided by actual days in the relevant interest period.',
        'scope': 'SELECTED_ANNUAL_ACTUAL_ACTUAL_WITHOUT_SHORT_OR_LONG_COUPONS', 'actor': 'terms',
    },
    'reference_period': {
        'reading': 'A reference period runs from and including interest commencement to but excluding the first interest payment date, or from and including one interest payment date to but excluding the next.',
        'scope': 'COMMON_ACTUAL_ACTUAL_REFERENCE_PERIOD_DEFINITION', 'actor': 'terms',
    },
    'principal_payment': {
        'reading': 'Subject to section 4(2), principal is paid to the clearing system or its order for credit to the accounts of its respective account holders.',
        'scope': 'PRINCIPAL_CLEARING_ROUTE_SUBJECT_TO_PAYMENT_QUALIFICATIONS', 'actor': 'issuer',
    },
    'interest_payment': {
        'reading': 'Subject to section 4(2), interest is paid to the clearing system or its order for credit to the accounts of its respective account holders.',
        'scope': 'INTEREST_CLEARING_ROUTE_SUBJECT_TO_PAYMENT_QUALIFICATIONS', 'actor': 'issuer',
    },
    'temporary_interest': {
        'reading': 'Interest on notes represented by a temporary global note follows that clearing-system route, subject to section 4(2) and proper certification under section 1(3)(b).',
        'scope': 'TEMPORARY_GLOBAL_NOTE_WITH_PROPER_CERTIFICATION', 'actor': 'issuer',
    },
    'payment_currency': {
        'reading': 'Payments are made in the specified currency, subject to applicable tax and other laws and regulations, and withholding or deduction under an IRC section 1471(b) agreement or otherwise imposed under sections 1471–1474, related regulations or agreements, official interpretations, or implementing intergovernmental-cooperation laws.',
        'scope': 'SPECIFIED_CURRENCY_SUBJECT_TO_LAW_AND_FATCA_WITHHOLDING', 'actor': 'issuer',
    },
    'clearing_discharge': {
        'reading': 'Payment to the clearing system or its order discharges the issuer from the corresponding payment obligation.',
        'scope': 'DISCHARGE_BY_PAYMENT_TO_CLEARING_SYSTEM_OR_ORDER', 'actor': 'issuer',
    },
    'deferred_payment': {
        'reading': 'If a payment falls due on a day that is not a payment day, the holder has no right to payment before the next payment day at the relevant place of business.',
        'scope': 'NON_PAYMENT_DAY_DUE_DATE_NEXT_PAYMENT_DAY', 'actor': 'holder',
    },
    'no_delay_interest': {
        'reading': 'The holder cannot claim additional interest or other payments for that payment-day delay.',
        'scope': 'ONLY_THE_DELAY_DESCRIBED_IN_PAYMENT_DAY_CLAUSE', 'actor': 'holder',
    },
    'payment_day': {
        'reading': 'For this purpose a payment day excludes Saturday and Sunday and requires the clearing system and all relevant parts of TARGET2 to be open to settle payments.',
        'scope': 'SELECTED_EUR_PAYMENT_DAY_CLEARING_AND_TARGET2', 'actor': 'terms',
    },
    'principal_definition': {
        'reading': 'References to principal include, where applicable, the redemption amount, early redemption amount, call redemption amount, premiums and other amounts payable on or in respect of the notes.',
        'scope': 'PRINCIPAL_REFERENCE_DEFINITION_WHERE_APPLICABLE', 'actor': 'terms',
    },
    'interest_definition': {
        'reading': 'References to interest include, where applicable, additional amounts payable under section 7.',
        'scope': 'INTEREST_REFERENCE_DEFINITION_WITH_SECTION7_QUALIFICATIONS', 'actor': 'terms',
    },
    'court_deposit': {
        'reading': 'The issuer may deposit principal or interest at the Amtsgericht Frankfurt am Main if holders have not claimed it within twelve months after its due date, even if the holders are not in default of acceptance.',
        'scope': 'TWELVE_MONTHS_UNCLAIMED_AND_NAMED_COURT', 'actor': 'issuer',
    },
    'deposit_discharge': {
        'reading': 'To the extent that such a deposit is made and the right of withdrawal is waived, the corresponding holder claims against the issuer are extinguished.',
        'scope': 'QUALIFYING_DEPOSIT_AND_WITHDRAWAL_WAIVER_ONLY_TO_EXTENT_DEPOSITED', 'actor': 'issuer',
    },
    'tax_withholding': {
        'reading': 'Amounts payable on the notes are paid without withholding or deduction for present or future taxes or charges imposed by or in Germany, on its behalf, or by or on behalf of a German political subdivision or tax authority, unless withholding or deduction is legally required.',
        'scope': 'SPECIFIED_GERMAN_TAXES_UNLESS_LEGALLY_REQUIRED', 'actor': 'issuer',
    },
    'gross_up': {
        'reading': 'When that withholding is legally required, the issuer pays additional amounts to preserve the otherwise receivable net amount, except for taxes or charges (a) paid through a holder custodian or collecting agent or otherwise than issuer withholding from principal or interest; (b) due to a present or former personal or business connection with Germany, beyond merely German-source or German-secured note payments; (c) withheld under EU interest-tax directives or regulations, relevant intergovernmental interest-tax agreements involving Germany or the EU, or implementing or complying laws; (d) due to a legal change effective more than thirty days after payment is due or, if later, all due amounts are properly made available and announced under section 13; or (e) due to holder residence in a non-cooperative jurisdiction under the Steueroasen-Abwehrgesetz of 25 June 2021 as amended, including regulations made under it.',
        'scope': 'GERMAN_WITHHOLDING_GROSS_UP_SUBJECT_TO_ALL_FIVE_EXCEPTIONS', 'actor': 'issuer',
    },
    'german_flat_tax': {
        'reading': 'German Abgeltungssteuer in force since 1 January 2009 and its solidarity surcharge are excluded from taxes or charges for which the issuer must pay those additional amounts.',
        'scope': 'SPECIFIED_FLAT_TAX_AND_SOLIDARITY_SURCHARGE_EXCLUSION', 'actor': 'issuer',
    },
    'presentment': {
        'reading': 'The terms shorten the presentment period specified in BGB section 801(1), sentence 1, to ten years for these notes.',
        'scope': 'CONTRACTUAL_PRESENTMENT_PERIOD_NOT_GENERAL_LIMITATION_VERDICT', 'actor': 'terms',
    },
}

REFERENCES = {
    'coupon_rate': ['basf-redemption:maturity'],
    'late_interest': ['historical-BGB-default-interest'],
    'partial_period': ['basf-payment:day_count'],
    'principal_payment': ['basf-payment:payment_currency'],
    'interest_payment': ['basf-payment:payment_currency'],
    'temporary_interest': ['basf-payment:payment_currency', 'basf-global:exchange-certification'],
    'payment_currency': ['applicable-payment-tax-and-other-law', 'historical-IRC-1471-1474'],
    'deferred_payment': ['basf-payment:payment_day'],
    'no_delay_interest': ['basf-payment:deferred_payment'],
    'interest_definition': ['basf-payment:tax_withholding', 'basf-payment:gross_up', 'basf-payment:german_flat_tax'],
    'deposit_discharge': ['basf-payment:court_deposit'],
    'gross_up': ['basf-payment:tax_withholding', 'basf-notices:publication',
                'historical-EU-and-intergovernmental-interest-tax-rules',
                'historical-Steueroasen-Abwehrgesetz'],
    'presentment': ['historical-BGB-801-1-sentence1'],
}


def validate(node):
    kind = node.get('payment_kind')
    if not isinstance(kind, str) or kind not in RULES:
        raise ValueError('Unsupported BASF payment rule kind')
    rule = RULES[kind]
    if (node.get('legal_reading') != rule['reading'] or node.get('rule_scope') != rule['scope']
            or node['actor'] != rule['actor'] or node['affected'] != 'holder'
            or node['election'] != 'none' or node['assets'] != []
            or node['role'] != 'OPERATIVE' or node['polarity'] is not True
            or node['modality'] != 'statement' or node['conditions'] != []
            or node['exceptions'] != []):
        raise ValueError('BASF payment reading or condition changed')
    references = node.get('references', [])
    if ([r.get('target') for r in references] != REFERENCES.get(kind, [])
            or any(r.get('kind') != 'reference' for r in references)):
        raise ValueError('BASF payment rule lost or changed its source dependencies')
    if any(k.startswith(('actual_', 'effective_', 'paid_', 'discharged_', 'computed_'))
           or k == 'independent_legal_acceptance' for k in node):
        raise ValueError('A supplied payment rule cannot attest actual events or calculations')


def explain(clauses, graph, assembly):
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for node in clauses['nodes']:
        if node['effect'] != 'basf_payment_terms':
            continue
        validate(node)
        groups = []
        for span in node['spans']:
            unit = units[span['unit']]
            cursor, sources = span['start'], []
            for piece in segments(graph, unit):
                start, end = max(span['start'], piece['start']), min(span['end'], piece['end'])
                if start >= end:
                    continue
                if start != cursor:
                    raise ValueError('Payment source spans are not contiguous')
                source = piece['source']
                raw_start = source['start'] + start - piece['start']
                sources.append(bind(graph, {**source, 'start': raw_start,
                    'end': raw_start + end - start, 'quote': unit['text'][start:end]}))
                cursor = end
            if cursor != span['end']:
                raise ValueError('Payment source span lacks an exact source copy')
            groups.append({'occurrence': dict(span), 'sources': sources})
        result.append({'id': node['id'], 'kind': node['payment_kind'],
            'actor': node['actor'], 'reading': node['legal_reading'],
            'rule_scope': node['rule_scope'], 'quote': node['quote'],
            'source_spans': groups,
            'sources': [s for g in groups for s in g['sources']],
            'references': [e for e in clauses['edges'] if e['from'] == node['id']],
            'reading_status': 'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_payment_tax_or_discharge': 'NOT_ESTABLISHED',
            'historical_law_applicability': 'NOT_ESTABLISHED',
            'independent_legal_acceptance': False})
    return result
