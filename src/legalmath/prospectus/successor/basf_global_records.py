"""Selected BASF form/ICSD premises, without inferred balances or legal acceptance."""
from copy import deepcopy

from . import basf, basf_agents, basf_global_exchange as exchange, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

FORM = 'basf-records:form-authentication'
CLEARING = 'basf-records:clearing-definition'
CUSTODY = 'basf-records:ngn-custody'
RECORDS = 'basf-records:records-evidence'
ADJUSTMENTS = 'basf-records:record-adjustments'
PARTIAL = 'basf-records:partial-exchange'
lines = basf_notices.lines
PARAGRAPHS = {
    FORM: lines(108, 49, 58),
    CLEARING: lines(109, 1, 3) + lines(109, 5, 9),
    CUSTODY: lines(109, 14, 15),
    RECORDS: lines(109, 23, 37),
    ADJUSTMENTS: lines(109, 38, 46),
    PARTIAL: lines(109, 47, 50),
}
PRIOR_IDS = [*exchange.PRIOR_IDS, *exchange.PARAGRAPHS]
AUTHORITY_IDS = exchange.AUTHORITY_IDS
CONTEXT_IDS = lines(108, 7, 14) + lines(110, 1, 45)
COMPARISON_IDS = lines(90, 5, 16)
INCOMING_REFERENCE = basf.KEY + ':p108:l11:ref:49'
READINGS = {
    FORM: {
        'reading': 'The notes are initially represented by a temporary global note without coupons, exchangeable for notes in the specified denomination represented by a permanent global note without coupons. Both global notes bear signatures of duly authorized representatives of the issuer and authentication by or on behalf of the Fiscal Agent. Individual notes and coupons will not be issued.',
        'initial_form': 'TEMPORARY_GLOBAL_WITHOUT_COUPONS',
        'exchange_form': 'PERMANENT_GLOBAL_WITHOUT_COUPONS',
        'specified_denomination_required': True,
        'issuer_authorized_signatures_both_forms': True,
        'fiscal_agent_authentication_both_forms': 'BY_OR_ON_BEHALF_OF',
        'individual_notes_or_coupons_issued': False,
        'exchange_conditions_preserved': exchange.EXCHANGE,
        'actual_authentication_or_exchange': 'NOT_EVALUATED',
        'qualification': 'Form exchange does not waive the separate timing, certification and delivery conditions in section 1(3)(b), and does not convert the notes into equity or establish an actual exchange.',
    },
    CLEARING: {
        'reading': 'The global note is held by or on behalf of a Clearing System. The selected Clearing Systems are Clearstream Banking S.A., 42 Avenue JF Kennedy, 1855 Luxembourg, Grand Duchy of Luxembourg (CBL), and Euroclear Bank SA/NV, Boulevard du Roi Albert II, 1210 Brussels, Belgium (Euroclear), each an ICSD and together the ICSDs, and every functional successor.',
        'systems': ['Clearstream Banking S.A.', 'Euroclear Bank SA/NV'],
        'includes_functional_successors': True,
        'cbf_selected': False, 'cds_selected': False,
        'actual_custody_or_successor': 'NOT_EVALUATED',
        'qualification': 'The selected final terms identify these systems; the contractual successor provision does not prove an actual succession or custody arrangement.',
    },
    CUSTODY: {
        'reading': 'The notes are issued in New Global Note (NGN) form and held by a common safekeeper on behalf of both ICSDs.',
        'form': 'NGN', 'custodian_role': 'COMMON_SAFEKEEPER',
        'on_behalf_of_both_icsds': True,
        'actual_custody': 'NOT_EVALUATED',
        'qualification': 'The CGN common-depositary alternative is not selected. This contractual arrangement does not identify an actual custodian or prove custody.',
    },
    RECORDS: {
        'reading': 'The aggregate principal represented by the global note equals the aggregate amount recorded from time to time in both ICSDs records. These are the records each ICSD keeps for its customers concerning the amount of their shares in the notes. The records are stated to be authoritative evidence of the represented aggregate principal, and a statement issued by an ICSD for this purpose is stated to be authoritative evidence of that ICSDs records at the relevant time.',
        'aggregate_amount_basis': 'RECORDS_OF_BOTH_ICSDS_AT_RELEVANT_TIME',
        'records_definition': 'EACH_ICSD_CUSTOMER_SHARES',
        'records_contractual_evidence': 'AUTHORITATIVE',
        'statement_evidence_scope': 'ISSUING_ICSD_RECORDS_AT_RELEVANT_TIME',
        'actual_account_balance': 'NOT_EVALUATED',
        'procedural_law_evidentiary_effect': 'NOT_EVALUATED',
        'qualification': 'This preserves the contractual evidentiary language. No record or statement has been supplied, and the issue amount is not proof of a balance at another time. Court admissibility, conclusiveness under applicable law and individual entitlement are not adjudicated.',
    },
    ADJUSTMENTS: {
        'reading': 'On redemption, payment of interest, or purchase and cancellation of notes represented by the global note, the issuer must ensure that the details are entered in the ICSD records. Following entry, the German reduction sentence requires subtraction of the aggregate principal of the notes described as repurchased or purchased and cancelled. The English comparison instead says redeemed or purchased and cancelled; the effect of this wording discrepancy on redemption accounting remains unresolved.',
        'recording_triggers': ['REDEMPTION', 'INTEREST_PAYMENT', 'PURCHASE_AND_CANCELLATION'],
        'issuer_ensures_recording': True,
        'adjustment_after_record_entry': True,
        'german_reduction_words': 'zurückgekauften bzw. gekauften und entwerteten',
        'english_comparison_words': 'redeemed or purchased and cancelled',
        'controlling_language': 'GERMAN',
        'redemption_reduction_wording': 'UNRESOLVED_BILINGUAL_DISCREPANCY',
        'interest_payment_alone_reduces_principal': False,
        'independent_uncompensated_holder_write_down': False,
        'actual_event_or_balance': 'NOT_EVALUATED',
        'qualification': 'Preserve the controlling German wording without silently substituting English. Recording an interest payment does not by itself reduce principal; this record-adjustment provision alone supplies no uncompensated holder-loss power. No actual payment, redemption, purchase, cancellation or register adjustment is established.',
    },
    PARTIAL: {
        'reading': 'On an exchange of only part of the notes represented by the temporary global note, the issuer must ensure that the details of that exchange are entered in the ICSD records.',
        'trigger': 'PARTIAL_TEMPORARY_GLOBAL_EXCHANGE',
        'issuer_ensures_recording': True,
        'destination': 'ICSD_RECORDS',
        'actual_exchange_or_recording': 'NOT_EVALUATED',
        'qualification': 'The temporary NGN branch is selected. The duty concerns recording a partial exchange; it does not prove completion, replace the separate certification conditions or create compulsory equity conversion.',
    },
}


def spans(units, identity):
    return [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in PARAGRAPHS[identity]]


def prior_readings(clauses):
    result = [node for node in clauses if node['id'] in PRIOR_IDS]
    if [node['id'] for node in result] != PRIOR_IDS:
        raise ValueError('All eleven prior BASF readings must survive in order')
    return result


def prepare(graph, construction, assembly, request, packet):
    prior = prior_readings(request['clauses'])
    references = request['reference_admission']['references']
    if (packet.get('version') != 'basf-global-records-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('prior_clauses_sha256') != digest(prior) or
            packet.get('prior_references_sha256') != digest(references) or len(references) != 5):
        raise ValueError('BASF records baseline or prior meanings/references changed')
    review(packet['review'])
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in AUTHORITY_IDS]
    if (packet.get('authority_sources') != authority or
            packet.get('context_sources') != [anchor(raw[key]) for key in CONTEXT_IDS] or
            packet.get('comparison_sources') != [anchor(raw[key]) for key in COMPARISON_IDS]):
        raise ValueError('Exact form, language, boundary and bilingual comparison sources required')
    units = {unit['unit']: unit for unit in assembly['units']}
    expected_ids = [key for keys in PARAGRAPHS.values() for key in keys]
    if ([row['unit'] for row in packet['units']] != expected_ids or
            any(row['role'] != 'OPERATIVE' for row in packet['units'])):
        raise ValueError('Records dispositions must cover exactly the six selected paragraphs')
    for row in packet['units']:
        whole = [{'unit': row['unit'], 'start': 0, 'end': len(units[row['unit']]['text'])}]
        if row['sources'] != [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)]:
            raise ValueError('Records disposition must bind exact surviving source pieces')
    clauses = packet['clauses']
    if [node['id'] for node in clauses] != list(PARAGRAPHS):
        raise ValueError('Six complete form and ICSD records readings required')
    for node in clauses:
        expected = spans(units, node['id'])
        if (node['units'] != PARAGRAPHS[node['id']] or node['spans'] != expected or
                node['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in expected) or
                node['source_uses'] != basf_agents.source_pieces(graph, units, expected) or
                node.get('selection_authority') != authority):
            raise ValueError('Records paragraph or exact source/authority changed')
        if (node.get('records_reading') != READINGS[node['id']] or node['actor'] != 'issuer' or
                node['affected'] != 'holder' or node['role'] != 'OPERATIVE' or node['effect'] != 'none' or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['questions'] != ['Q1', 'Q2'] or
                node['modality'] != 'statement' or node['election'] != 'none' or node['assets'] != [] or
                node['polarity'] is not True or node['conditions'] != [] or node['exceptions'] != [] or
                not node.get('effect_explanation')):
            raise ValueError('Reviewed form/records meaning or qualification changed')
    result = deepcopy(request)
    rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    rows.update({row['unit']: row for row in packet['units']})
    result['reviewed_dispositions'].update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    previous = dispositions(graph, assembly, request['reviewed_dispositions'])
    # Disposition edits are confined to this package; all excluded and unknown
    # branches, prior meanings and source mappings outside it are preserved.
    before = {unit['unit']: unit for unit in previous['units']}
    if any(unit != before[unit['unit']] for unit in selected['units'] if unit['unit'] not in expected_ids):
        raise ValueError('Records admission changed an outside source disposition')
    result['reference_admission']['assembly_sha256'] = digest(selected)
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = basf_notices.overlay(selected, prior + clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def check_meanings(report, request, packet):
    actual = [node for node in report['clause_graph']['nodes'] if node['id'] in PARAGRAPHS]
    requested = [node for node in request['clauses'] if node['id'] in PARAGRAPHS]
    if (actual != packet['clauses'] or requested != packet['clauses'] or
            {node['id']: node['records_reading'] for node in actual} != READINGS):
        raise ValueError('Form or ICSD records meaning changed between review, request and P3')
    if (digest(prior_readings(report['clause_graph']['nodes'])) != packet['prior_clauses_sha256'] or
            digest(prior_readings(request['clauses'])) != packet['prior_clauses_sha256'] or
            digest(request['reference_admission']['references']) != packet['prior_references_sha256']):
        raise ValueError('Prior BASF readings or references changed downstream')
    incoming = [row for row in report['dependencies'] if row['id'].startswith(INCOMING_REFERENCE + '@')]
    if not incoming or any(row['status'] != 'UNRESOLVED' for row in incoming):
        raise ValueError('Unreviewed incoming NGN reference must remain unresolved')
    if report.get('independent_legal_acceptance') is not False:
        raise ValueError('Records development review cannot establish independent acceptance')
    return {'paragraphs': list(PARAGRAPHS), 'meanings_sha256': digest(actual),
            'reviewed_units': sum(map(len, PARAGRAPHS.values())),
            'prior_meanings_sha256': packet['prior_clauses_sha256'],
            'actual_balances_events_and_compliance': 'NOT_EVALUATED',
            'redemption_reduction_wording': 'UNRESOLVED_BILINGUAL_DISCREPANCY',
            'incoming_ngn_reference': 'UNRESOLVED', 'independent_holder_write_down': False}


def omitted_clauses(assembly, request, identity):
    if identity not in PARAGRAPHS:
        raise ValueError('Unknown records meaning omission')
    retained = prior_readings(request['clauses']) + [node for node in request['clauses']
                if node['id'] in PARAGRAPHS and node['id'] != identity]
    return basf_notices.overlay(assembly, retained)


matched_omission = basf_notices.matched_omission
