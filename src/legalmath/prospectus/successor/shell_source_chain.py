"""Explicit source reading for one retained Shell final-terms/memorandum pair."""
from copy import deepcopy
from importlib.resources import files
import json

from .anchors import bind, fields
from .contracts import digest

VERSION = 'shell-contract-source-chain.v1'


def admit(graph, bundle, profile):
    fields(profile, {'version'}, {'version'})
    if profile['version'] != VERSION:
        raise ValueError('Unsupported contractual source-chain reading')
    spec = json.loads(files(__package__).joinpath('shell_source_chain_spec.json').read_text())
    if (graph.get('instrument_id') != spec['instrument_id']
            or bundle.get('instrument_id') != spec['instrument_id']
            or graph.get('bundle_sha256') != digest(bundle)):
        raise ValueError('Source-chain instrument or source bundle changed')
    documents = []
    for expected in spec['documents']:
        requested = [d for d in bundle['documents'] if d.get('id') == expected['id']]
        retained = [d for d in graph['documents'] if d.get('id') == expected['id']]
        if len(requested) != 1 or len(retained) != 1:
            raise ValueError('Source chain requires exactly one of each original edition')
        if any(d.get(k) != expected[k] for d in (requested[0], retained[0])
               for k in ('sha256', 'document_date')) or retained[0].get('visible') is not True:
            raise ValueError('Source-chain edition/date is changed or unavailable')
        if requested[0]['path'] != retained[0]['path']:
            raise ValueError('Source-chain document path differs from supplied bundle')
        documents.append({'document': expected['id'], 'sha256': expected['sha256'],
                          'printed_document_date': expected['document_date'][:10],
                          'date_basis': 'PRINTED_DOCUMENT_DATE',
                          'authenticity': 'NOT_ESTABLISHED',
                          'first_publication': 'NOT_ESTABLISHED'})
    groups = {name: [bind(graph, source) for source in sources]
              for name, sources in spec['groups'].items()}
    # This is an explicit reviewed reading, not date-based automatic inference.
    # Binding every complete source group preserves the qualifications that
    # support the following narrowly stated relationships.
    return {
        'version': VERSION, 'source_graph_sha256': digest(graph),
        'scope': 'NAMED_SUPPLIED_SHELL_2030_SOURCE_PAIR',
        'reading_kind': 'EXPOSED_SOURCE_INTERPRETATION',
        'documents': documents, 'sources': groups,
        'instrument': {'issuer': 'Shell International Finance B.V.',
                       'guarantor': 'Royal Dutch Shell plc',
                       'currency': 'GBP', 'nominal': '500000000',
                       'annual_rate': '1.000 per cent.', 'maturity': '2030-12-10'},
        'edition_link': {
            'status': 'PRINTED_REFERENCE_MATCH',
            'from_document': 'shell-2030-final', 'to_document': 'shell-2020-base',
            'referenced_date': '2020-08-13',
            'basis': ['final_identity_and_reference', 'base_identity'],
            'meaning': 'Part A says to read these Final Terms with the Information Memorandum dated 13 August 2020; the supplied memorandum prints that date and the same issuer identities.',
            'historical_publication': 'NOT_ESTABLISHED',
            'publication_statement': 'The Final Terms state that the memorandum has been published on the named Shell website; this is a document statement, not an independently observed historical retrieval.'},
        'construction': {
            'part_a_relation': 'SUPPLEMENTS_CONDITIONS',
            'global_note': 'The Conditions state incorporation by reference and attachment or endorsement of applicable Final Terms.',
            'definitive_note': 'Incorporation by reference requires the stated listing permission and issuer/dealer agreement; otherwise Conditions are endorsed or attached.',
            'exempt_note_branch': 'The applicable Pricing Supplement may replace or modify Conditions to the stated extent for Exempt Notes; that branch is not selected here.',
            'basis': ['conditions_and_agreements'],
            'all_source_roles_established': False},
        'precedence': {
            'condition': 'ONLY_IN_THE_EVENT_OF_INCONSISTENCY',
            'rules': [
                {'prevails': 'TRUST_DEED', 'over': 'AGENCY_AGREEMENT'},
                {'prevails': 'APPLICABLE_FINAL_TERMS', 'over': 'AGENCY_AGREEMENT'},
                {'prevails': 'APPLICABLE_FINAL_TERMS', 'over': 'TRUST_DEED'}],
            'basis': ['agreement_access_and_precedence'],
            'mandatory_law_overridden': False,
            'actual_inconsistency_decided': False},
        'trustee_history': {
            'original_deed_date': '2005-07-22',
            'original_deed_named_trustee': 'Citicorp Trustee Company Limited',
            'successors_included_in_definition': True,
            'programme_named_trustee': 'Deutsche Trustee Company Limited',
            'office_statement_date': '2020-08-13',
            'relationship': 'DIFFERENT_DATED_CONTEXTS_WITH_SUCCESSOR_DEFINITION',
            'contradiction_established': False,
            'actual_succession_established': False,
            'basis': ['conditions_and_agreements', 'programme_trustee', 'agreement_access_and_precedence']},
        'onward_documents': [
            {'document': 'TRUST_DEED', 'described_date': '2005-07-22',
             'includes': 'MODIFICATIONS_SUPPLEMENTS_AND_RESTATEMENTS',
             'status': 'EXECUTED_CONTENT_NOT_SUPPLIED_IN_REVIEWED_PAIR'},
            {'document': 'AGENCY_AGREEMENT', 'described_date': '2020-08-13',
             'named_agent': 'Deutsche Bank AG, London Branch',
             'includes': 'MODIFICATIONS_SUPPLEMENTS_AND_RESTATEMENTS',
             'status': 'EXECUTED_CONTENT_NOT_SUPPLIED_IN_REVIEWED_PAIR'},
            {'document': 'GLOBAL_NOTE', 'described_date': None,
             'status': 'EXECUTED_CONTENT_NOT_SUPPLIED_IN_REVIEWED_PAIR'}],
        'note_form': {
            'printed_form': 'TEMPORARY_GLOBAL_EXCHANGEABLE_FOR_PERMANENT_GLOBAL',
            'definitive_exchange': 'AT_ISSUER_REQUEST_AND_IN_LIMITED_CIRCUMSTANCES_SET_OUT_IN_NOTE',
            'actual_exchange_established': False,
            'basis': ['note_form_and_fixed_selection']},
        'financial_selections': {
            'interest_payment_basis': 'FIXED_RATE',
            'issuer_call_option': 'NOT_APPLICABLE', 'noteholder_put_option': 'NOT_APPLICABLE',
            'final_redemption_amount_per_calculation_amount': 'GBP 1000',
            'early_redemption_amount_per_calculation_amount': 'GBP 1000',
            'equal_amounts_make_triggers_equivalent': False,
            'alternative_payment_day_definition': 'NOT_APPLICABLE',
            'basis': ['note_form_and_fixed_selection', 'redemption_and_payment_selection']},
        'payment_recipient': {
            'printed_rule': 'GLOBAL_NOTE_HOLDER_OR_TRUSTEE_AS_PROVIDED_IN_TRUST_DEED',
            'clearing_participants': 'LOOK_TO_CLEARING_SYSTEM_FOR_THEIR_SHARE',
            'actual_recipient_established': False, 'basis': ['global_recipient']},
        'unresolved': [
            'Authenticity and first publication/earlier legal availability of the supplied copies.',
            'Executed Trust Deed, Agency Agreement, Global Note, applicable amendments and trustee succession evidence are not supplied in this reviewed pair.',
            'Any actual inconsistency between those instruments and the Final Terms.',
            'Complete contract construction, mandatory-law application, actual note form, ownership and events.'],
        'legal_applicability_established': False, 'assembly_roles_changed': False,
        'independent_legal_acceptance': False,
    }


def verify(graph, bundle, request, selected):
    if 'contract_source_chain' in request:
        expected = admit(graph, bundle, request['contract_source_chain'])
        if digest(selected.get('contract_source_chain')) != digest(expected):
            raise ValueError('Contractual source-chain reading differs from its source evidence')
        return deepcopy(expected)
    if 'contract_source_chain' in selected:
        raise ValueError('Contractual source-chain reading has no request')
    return None
