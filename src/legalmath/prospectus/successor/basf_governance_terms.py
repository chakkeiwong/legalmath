"""Supplied governance readings with no finding of an effective legal event."""
from .anchors import bind
from .occurrences import segments

RULES = {
    'substitution': {
        'reading': 'While not in default of principal or interest payment, the issuer may substitute an affiliate as principal debtor without holder consent, provided (a) the successor assumes all note obligations; (b) it has the required permissions and may pay the Fiscal Agent in the specified currency without withholding taxes or charges imposed in the successor or issuer seat or tax-residence jurisdiction; (c) it undertakes to indemnify holders for taxes, charges or official burdens imposed because of substitution; (d) the issuer programme guarantee and negative-pledge obligations extend to the successor notes, with the note section 11 provisions applying correspondingly; and (e) the Fiscal Agent receives confirmations from recognised lawyers in the affected jurisdictions that (a)–(d) are satisfied.',
        'scope': 'NO_PAYMENT_DEFAULT_AND_ALL_FIVE_SUBSTITUTION_PREREQUISITES', 'actor': 'issuer'},
    'affiliate': {
        'reading': 'For section 10, an affiliate means an affiliated enterprise within AktG section 15.',
        'scope': 'SECTION10_AKTG15_DEFINITION', 'actor': 'terms'},
    'substitution_notice': {
        'reading': 'Every substitution must be announced under section 13.',
        'scope': 'SUBSTITUTION_NOTICE_UNDER_CONTRACT_SECTION13', 'actor': 'issuer'},
    'substitution_changes': {
        'reading': 'Following such a substitution, the issuer may amend the global note and terms without holder consent only to the extent necessary to reflect the changes resulting from substitution.',
        'scope': 'ONLY_NECESSARY_CHANGES_RESULTING_FROM_QUALIFYING_SUBSTITUTION', 'actor': 'issuer'},
    'substitution_deposit': {
        'reading': 'The correspondingly amended global note and terms are deposited with the clearing system.',
        'scope': 'AMENDED_DOCUMENTS_FOLLOWING_SUBSTITUTION', 'actor': 'issuer'},
    'amendment_agreement': {
        'reading': 'Under the SchVG as amended, holders may agree with the issuer to amend the terms by a resolution on a subject permitted by the SchVG, using the majority specified in section 11(2).',
        'scope': 'SCHVG_PERMITTED_SUBJECT_AND_ISSUER_AGREEMENT_AND_REQUIRED_MAJORITY', 'actor': 'holders'},
    'binding_majority': {
        'reading': 'Majority resolutions of holders bind all holders equally, within the stated amendment framework.',
        'scope': 'EQUAL_BINDING_EFFECT_OF_QUALIFYING_MAJORITY_RESOLUTION', 'actor': 'holders'},
    'unequal_treatment': {
        'reading': 'A majority resolution that does not provide equal conditions for all holders is ineffective unless the disadvantaged holders expressly consent to their disadvantage.',
        'scope': 'UNEQUAL_CONDITIONS_REQUIRE_DISADVANTAGED_HOLDERS_EXPRESS_CONSENT', 'actor': 'holders'},
    'qualified_majority': {
        'reading': 'The terms prescribe at least 75% of the voting rights participating in the vote, subject to the stated simple-majority exception.',
        'scope': 'AT_LEAST75_PERCENT_PARTICIPATING_VOTING_RIGHTS_NOT_QUORUM', 'actor': 'holders'},
    'simple_majority': {
        'reading': 'A simple majority of participating voting rights suffices only for resolutions that both leave the material content of the terms unchanged and concern none of the subjects in SchVG section 5(3), numbers 1–8.',
        'scope': 'BOTH_NON_MATERIAL_CHANGE_AND_NO_SCHVG5_3_1_TO8_SUBJECT', 'actor': 'holders'},
    'resolution_method': {
        'reading': 'At the issuer’s choice, holders resolve by a vote without a meeting under SchVG section 18 and sections 5 onward, or by a holders’ meeting under sections 5 onward.',
        'scope': 'ISSUER_CHOICE_OF_TWO_STATUTORY_PROCEDURES', 'actor': 'issuer'},
    'voting_chair': {
        'reading': 'A vote without a meeting is chaired by a notary commissioned by the issuer, or by the common representative if that representative requested the vote.',
        'scope': 'NOTARY_OR_REQUESTING_COMMON_REPRESENTATIVE', 'actor': 'voting_process'},
    'voting_weight': {
        'reading': 'Each holder participates in voting according to the nominal amount or mathematical proportion of its interest in the outstanding notes.',
        'scope': 'CONTRACTUAL_NOMINAL_OR_PROPORTIONAL_VOTING_WEIGHT', 'actor': 'holder'},
    'representative_appointment': {
        'reading': 'Holders may appoint a common representative for all holders by majority resolution to exercise their rights.',
        'scope': 'REPRESENTATIVE_APPOINTMENT_BY_HOLDER_MAJORITY', 'actor': 'holders'},
    'notice_registration': {
        'reading': 'A meeting must be called at least fourteen days before meeting day. If the call requires prior registration for participation or voting, the registration deadline replaces meeting day for computing that call period. Registration must arrive at the address stated in the call notice no later than the third day before the meeting.',
        'scope': 'FOURTEEN_DAY_CALL_WITH_REGISTRATION_DEADLINE_SHIFT_AND_THIRD_DAY_RECEIPT', 'actor': 'meeting_process'},
    'participation_proof': {
        'reading': 'The call may specify proof of participation entitlement. Unless it provides otherwise, a voting ticket issued by an issuer-appointed agent entitles its holder to participate and vote. The holder can obtain the ticket by, at least six days before the meeting time, either depositing notes with or as directed by that agent, or blocking notes with a custodian under its procedures and delivering evidence of holding and blocking to the agent. The call may also require identification of the person voting.',
        'scope': 'NOTICE_ALTERNATIVES_AND_SIX_DAY_DEPOSIT_OR_BLOCKING_PLUS_DELIVERED_PROOF', 'actor': 'holder'},
    'notice_publication': {
        'reading': 'The call must state the issuer name and seat, meeting time and place, and participation and voting conditions including the registration and proof conditions. It must be published without delay in the Bundesanzeiger and additionally under section 13. The issuer bears publication costs.',
        'scope': 'SPECIFIED_NOTICE_CONTENTS_AND_BOTH_PUBLICATION_CHANNELS_AND_ISSUER_COST', 'actor': 'issuer'},
    'governing_law': {
        'reading': 'The terms choose German law in every respect for the form and content of the notes and the rights and duties of holders and issuer.',
        'scope': 'CONTRACTUAL_GERMAN_LAW_CHOICE', 'actor': 'terms'},
    'jurisdiction': {
        'reading': 'The Landgericht Frankfurt am Main has non-exclusive jurisdiction for actions or other proceedings arising in connection with the notes.',
        'scope': 'NON_EXCLUSIVE_FRANKFURT_REGIONAL_COURT', 'actor': 'terms'},
    'language': {
        'reading': 'The terms are written in German with an English translation attached. The German text is binding and governing; the English translation is nonbinding.',
        'scope': 'SELECTED_GERMAN_TEXT_AND_NONBINDING_ENGLISH_TRANSLATION', 'actor': 'terms'},
}

REFERENCES = {
    'substitution': ['basf-governance:affiliate', 'unresolved-programme-guarantee-negative-pledge', 'basf-governance:amendment_agreement'],
    'affiliate': ['historical-AktG15-affiliation'],
    'substitution_notice': ['basf-notices:publication'],
    'substitution_changes': ['basf-governance:substitution'],
    'substitution_deposit': ['basf-governance:substitution_changes'],
    'amendment_agreement': ['historical-SchVG-amendment-law', 'basf-governance:qualified_majority', 'basf-governance:simple_majority'],
    'binding_majority': ['basf-governance:amendment_agreement'],
    'unequal_treatment': ['basf-governance:amendment_agreement'],
    'qualified_majority': ['basf-governance:simple_majority'],
    'simple_majority': ['historical-SchVG5-3-subjects1-to8'],
    'resolution_method': ['historical-SchVG18-and5-onward'],
    'voting_chair': ['basf-governance:resolution_method'],
    'voting_weight': ['historical-SchVG-voting-eligibility-and-suspension'],
    'representative_appointment': ['historical-SchVG-common-representative'],
    'notice_registration': ['historical-SchVG-notice-law'],
    'participation_proof': ['basf-governance:notice_registration', 'historical-SchVG-proof-requirements'],
    'notice_publication': ['basf-notices:publication', 'basf-governance:notice_registration', 'basf-governance:participation_proof'],
    'governing_law': ['applicable-German-conflict-and-mandatory-law'],
    'jurisdiction': ['applicable-jurisdiction-rules'],
}


def validate(node):
    kind = node.get('governance_kind')
    if not isinstance(kind, str) or kind not in RULES:
        raise ValueError('Unsupported BASF governance rule kind')
    rule = RULES[kind]
    if (node.get('legal_reading') != rule['reading'] or node.get('rule_scope') != rule['scope']
            or node['actor'] != rule['actor'] or node['affected'] != 'holder'
            or node['election'] != 'none' or node['assets'] != []
            or node['role'] != 'OPERATIVE' or node['polarity'] is not True
            or node['modality'] != 'statement' or node['conditions'] != [] or node['exceptions'] != []):
        raise ValueError('BASF governance reading or condition changed')
    refs = node.get('references', [])
    if ([r.get('target') for r in refs] != REFERENCES.get(kind, [])
            or any(r.get('kind') != 'reference' for r in refs)):
        raise ValueError('BASF governance rule lost or changed its source dependencies')
    if any(k.startswith(('actual_', 'effective_', 'counted_', 'computed_', 'appointed_'))
           or k == 'independent_legal_acceptance' for k in node):
        raise ValueError('A supplied governance rule cannot attest actual legal events')


def explain(clauses, graph, assembly):
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for node in clauses['nodes']:
        if node['effect'] != 'basf_governance_terms':
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
                    raise ValueError('Governance source spans are not contiguous')
                source = piece['source']
                raw_start = source['start'] + start - piece['start']
                sources.append(bind(graph, {**source, 'start':raw_start,
                    'end':raw_start + end - start, 'quote':unit['text'][start:end]}))
                cursor = end
            if cursor != span['end']:
                raise ValueError('Governance source span lacks an exact source copy')
            groups.append({'occurrence':dict(span), 'sources':sources})
        result.append({'id':node['id'], 'kind':node['governance_kind'], 'actor':node['actor'],
            'reading':node['legal_reading'], 'rule_scope':node['rule_scope'], 'quote':node['quote'],
            'source_spans':groups, 'sources':[s for g in groups for s in g['sources']],
            'references':[e for e in clauses['edges'] if e['from'] == node['id']],
            'reading_status':'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_substitution_vote_or_amendment':'NOT_ESTABLISHED',
            'historical_law_applicability':'NOT_ESTABLISHED', 'independent_legal_acceptance':False})
    return result
