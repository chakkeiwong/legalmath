"""Selected BASF issue amount and holder definition, without inferred holdings."""
from copy import deepcopy

from . import basf, basf_agents, basf_global_records as records, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

AMOUNT = 'basf-amount:issue-amount'
BEARER = 'basf-amount:bearer-form'
HOLDER = 'basf-amount:holder-definition'
lines = basf_notices.lines
PARAGRAPHS = {AMOUNT: lines(108, 7, 13), BEARER: lines(108, 14, 14),
              HOLDER: lines(110, 40, 41) + lines(110, 44, 45)}
PRIOR_IDS = [*records.PRIOR_IDS, *records.PARAGRAPHS]
AUTHORITY_IDS = (['basf-2032-final:p2:l10'] +
                 [f'basf-2032-final:p3:l{i}' for i in range(5, 56)] +
                 [f'basf-2032-final:p7:l{i}' for i in range(48, 54)])
TARGET_IDS = [key for identity, keys in records.PARAGRAPHS.items()
              if identity != records.FORM for key in keys]
CONTEXT_IDS = lines(109, 1, 50) + lines(110, 1, 45)
REFERENCE_ID = 'amount-ngn-records'
READINGS = {
    AMOUNT: {
        'reading': 'This series of notes of BASF SE (BASF or the issuer) is issued in euro with an aggregate principal amount of EUR 500,000,000 (EUR five hundred million), subject to section 1(4), in denominations of EUR 100,000.',
        'issuer': 'BASF SE', 'issuer_shorthand': 'BASF', 'currency': 'EUR',
        'issue_amount': '500000000', 'issue_amount_words': 'EUR fünfhundert Millionen',
        'denomination': '100000', 'amount_subject_to': 'SECTION_1_4',
        'ngn_reference': REFERENCE_ID, 'actual_outstanding_balance': 'NOT_EVALUATED',
        'qualification': 'The stated issue amount is qualified by the selected NGN records provisions. It does not establish the represented balance on another date, actual issuance, payment, purchase, cancellation or any persons holding.',
    },
    BEARER: {
        'reading': 'The notes are in bearer form.', 'form': 'BEARER',
        'actual_entitlement': 'NOT_EVALUATED',
        'qualification': 'Bearer form does not waive the selected global-note custody, certification or proof-of-holding requirements and does not identify an actual holder.',
    },
    HOLDER: {
        'reading': 'For these terms, holder means each holder of a co-ownership share or another comparable right in the notes.',
        'scope': 'THESE_TERMS_AND_CONDITIONS',
        'rights': ['CO_OWNERSHIP_SHARE', 'OTHER_COMPARABLE_RIGHT'],
        'cds_qualification_selected': False, 'actual_ownership': 'NOT_EVALUATED',
        'proprietary_law_classification': 'NOT_EVALUATED', 'procedural_standing': 'NOT_EVALUATED',
        'qualification': 'The contractual definition does not prove actual ownership, equate every beneficial interest with a qualifying right, settle proprietary-law classification or establish standing in a particular proceeding. The CDS-specific qualification is not selected.',
    },
}


def spans(units, identity):
    return [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in PARAGRAPHS[identity]]


def prior_readings(clauses):
    result = [node for node in clauses if node['id'] in PRIOR_IDS]
    if [node['id'] for node in result] != PRIOR_IDS:
        raise ValueError('All seventeen prior BASF readings must survive in order')
    return result


def expected_reference(graph, assembly):
    raw = {unit['id']: unit for unit in graph['units']}
    units = {unit['unit']: unit for unit in assembly['units']}
    source = anchor(raw[basf.KEY + ':p108:l11'], 49, 63)
    if source['quote'] != '§ 1 Absatz (4)':
        raise ValueError('NGN qualification source changed')
    selected = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in TARGET_IDS]
    targets = [{**piece, 'language': raw[piece['source']['unit']]['language']}
               for piece in basf_agents.source_pieces(graph, units, selected)]
    return {'id': REFERENCE_ID, 'form': 'relative', 'source': source,
            'authority': source, 'from_use': source['unit'], 'language': raw[source['unit']]['language'],
            'targets': targets, 'questions': ['Q1', 'Q2'],
            'discovery_ids': [records.INCOMING_REFERENCE],
            'reason': 'Original pages 108–110: the issue-amount qualification imports complete selected section 1(4), including definition, custody, records, adjustments and partial-exchange recording.'}


def check_ngn_reference(report, reference, reference_review):
    """Bind the new expectation to a real complete source/target and dependency."""
    if reference != expected_reference(report['source_map'], report['assembly']):
        raise ValueError('Complete exact NGN qualification and target required')
    expected, _ = admit(report['source_map'], report['assembly'], {
        'version': 'reviewed-references.v2', 'assembly_sha256': digest(report['assembly']),
        'review': reference_review, 'references': [reference]})
    actual = [row for row in report['dependencies'] if row['id'] == 'reviewed-reference:' + REFERENCE_ID]
    if actual != expected or any(row['id'].startswith(records.INCOMING_REFERENCE + '@')
                                 for row in report['dependencies']):
        raise ValueError('NGN dependency missing, changed or original proposal not replaced')
    return expected[0]


def prepare(graph, construction, assembly, request, packet):
    prior = prior_readings(request['clauses'])
    references = request['reference_admission']['references']
    if (packet.get('version') != 'basf-amount-holder-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('prior_clauses_sha256') != digest(prior) or
            packet.get('prior_references_sha256') != digest(references) or len(references) != 5):
        raise ValueError('BASF amount baseline or prior meanings/references changed')
    review(packet['review'])
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in AUTHORITY_IDS]
    if (packet.get('authority_sources') != authority or
            packet.get('context_sources') != [anchor(raw[key]) for key in CONTEXT_IDS]):
        raise ValueError('Exact amount, issuer, language and selected target sources required')
    units = {unit['unit']: unit for unit in assembly['units']}
    expected_ids = [key for keys in PARAGRAPHS.values() for key in keys]
    if ([row['unit'] for row in packet['units']] != expected_ids or
            any(row['role'] != 'OPERATIVE' for row in packet['units'])):
        raise ValueError('Amount dispositions must cover exactly the three selected paragraphs')
    for row in packet['units']:
        whole = [{'unit': row['unit'], 'start': 0, 'end': len(units[row['unit']]['text'])}]
        if row['sources'] != [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)]:
            raise ValueError('Amount disposition must bind exact surviving source pieces')
    clauses = packet['clauses']
    if [node['id'] for node in clauses] != list(PARAGRAPHS):
        raise ValueError('Three complete amount, form and holder readings required')
    for node in clauses:
        expected = spans(units, node['id'])
        if (node['units'] != PARAGRAPHS[node['id']] or node['spans'] != expected or
                node['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in expected) or
                node['source_uses'] != basf_agents.source_pieces(graph, units, expected) or
                node.get('selection_authority') != authority):
            raise ValueError('Amount paragraph or exact source/authority changed')
        if (node.get('amount_reading') != READINGS[node['id']] or node['actor'] != 'issuer' or
                node['affected'] != 'holder' or node['role'] != 'OPERATIVE' or node['effect'] != 'none' or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['questions'] != ['Q1', 'Q2'] or
                node['modality'] != 'statement' or node['election'] != 'none' or node['assets'] != [] or
                node['polarity'] is not True or node['conditions'] != [] or node['exceptions'] != [] or
                not node.get('effect_explanation')):
            raise ValueError('Reviewed amount, form or holder qualification changed')
    result = deepcopy(request)
    rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    rows.update({row['unit']: row for row in packet['units']})
    result['reviewed_dispositions'].update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    previous = dispositions(graph, assembly, request['reviewed_dispositions'])
    before = {unit['unit']: unit for unit in previous['units']}
    if any(unit != before[unit['unit']] for unit in selected['units'] if unit['unit'] not in expected_ids):
        raise ValueError('Amount admission changed an outside source disposition')
    if packet.get('references') != [expected_reference(graph, selected)]:
        raise ValueError('Complete exact NGN qualification and target required')
    result['reference_admission']['assembly_sha256'] = digest(selected)
    result['reference_admission']['references'].extend(deepcopy(packet['references']))
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = basf_notices.overlay(selected, prior + clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def check_meanings(report, request, packet):
    actual = [node for node in report['clause_graph']['nodes'] if node['id'] in PARAGRAPHS]
    requested = [node for node in request['clauses'] if node['id'] in PARAGRAPHS]
    if (actual != packet['clauses'] or requested != packet['clauses'] or
            {node['id']: node['amount_reading'] for node in actual} != READINGS):
        raise ValueError('Amount, form or holder meaning changed between review, request and P3')
    references = request['reference_admission']['references']
    if (digest(prior_readings(report['clause_graph']['nodes'])) != packet['prior_clauses_sha256'] or
            digest(prior_readings(request['clauses'])) != packet['prior_clauses_sha256'] or
            len(references) != 6 or digest(references[:5]) != packet['prior_references_sha256'] or
            references[5:] != packet['references']):
        raise ValueError('Prior BASF meanings or reviewed references changed downstream')
    check_ngn_reference(report, references[-1], request['reference_admission']['review'])
    if report.get('independent_legal_acceptance') is not False:
        raise ValueError('Amount development review cannot establish independent acceptance')
    return {'paragraphs': list(PARAGRAPHS), 'meanings_sha256': digest(actual),
            'reviewed_units': sum(map(len, PARAGRAPHS.values())),
            'prior_meanings_sha256': packet['prior_clauses_sha256'],
            'incoming_ngn_reference': 'RESOLVED_UNDER_SUPPLIED_REVIEW',
            'actual_balance_ownership_and_standing': 'NOT_EVALUATED'}


def omitted_clauses(assembly, request, identity):
    if identity not in PARAGRAPHS:
        raise ValueError('Unknown amount meaning omission')
    retained = prior_readings(request['clauses']) + [node for node in request['clauses']
                if node['id'] in PARAGRAPHS and node['id'] != identity]
    return basf_notices.overlay(assembly, retained)


def matched_missing_link(report, omitted):
    incoming = [row for row in omitted['dependencies'] if row['id'].startswith(records.INCOMING_REFERENCE + '@')]
    if (len(incoming) != 1 or incoming[0]['status'] != 'UNRESOLVED' or incoming[0]['targets'] or
            incoming[0]['questions'] != ['Q1', 'Q2'] or
            any(row['id'] == 'reviewed-reference:' + REFERENCE_ID for row in omitted['dependencies']) or
            omitted['clauses'] != report['clause_graph'] or
            [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] != ['UNKNOWN', 'UNKNOWN', 'PARTIAL']):
        raise ValueError('Missing NGN link did not retain its exact unresolved dependency and meanings')
    def outside(rows):
        return [row for row in rows if row['id'] != 'reviewed-reference:' + REFERENCE_ID and
                not row['id'].startswith(records.INCOMING_REFERENCE + '@') and
                not row['id'].startswith('reference-closure:')]
    if outside(omitted['dependencies']) != outside(report['dependencies']):
        raise ValueError('Missing NGN link changed another direct dependency')
    return {'incoming': incoming[0], 'other_direct_dependencies_equal': True,
            'all_meanings_equal': True, 'questions': ['UNKNOWN', 'UNKNOWN', 'PARTIAL']}


matched_omission = basf_notices.matched_omission
