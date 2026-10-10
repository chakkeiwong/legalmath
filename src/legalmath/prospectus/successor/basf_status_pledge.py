"""Selected BASF status and issuer covenant; supplied readings remain premises."""
from copy import deepcopy

from . import basf, basf_agents, basf_amount_holder as amount, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

STATUS = 'basf-pledge:status'
PLEDGE = 'basf-pledge:issuer-negative-pledge'
DEFINITION = 'basf-pledge:capital-market-debt'
lines = basf_notices.lines
PARAGRAPHS = {STATUS: lines(110, 49, 53), PLEDGE: lines(110, 54, 75),
              DEFINITION: lines(110, 76, 80)}
PRIOR_IDS = [*amount.PRIOR_IDS, *amount.PARAGRAPHS]
AUTHORITY_IDS = ['basf-2032-final:p2:l10'] + [f'basf-2032-final:p2:l{i}' for i in range(42, 49)] + [f'basf-2032-final:p7:l{i}' for i in range(48, 54)]
CONTEXT_IDS = lines(108, 1, 4) + lines(110, 46, 85) + lines(111, 1, 21)
EXCLUDED_IDS = lines(110, 48, 48) + lines(110, 84, 85) + lines(111, 5, 21)
DEFINITION_REFERENCE = {'target': DEFINITION, 'kind': 'definition',
    'reason': 'The issuer covenant uses Kapitalmarktverbindlichkeiten with the complete definition immediately following at German Option I 110:76–80.'}
READINGS = {
    STATUS: {
        'reading': 'The notes constitute unsecured and unsubordinated obligations of the issuer, ranking equally with each other and with the issuers other unsecured and unsubordinated obligations, except where mandatory statutory provisions accord those obligations priority.',
        'security': 'UNSECURED', 'subordination': 'UNSUBORDINATED',
        'ranking': 'EQUAL_WITH_OTHER_UNSECURED_UNSUBORDINATED_ISSUER_OBLIGATIONS',
        'exception': 'MANDATORY_STATUTORY_PRIORITY',
        'actual_statutory_priority': 'NOT_EVALUATED', 'actual_recovery': 'NOT_EVALUATED',
        'qualification': 'Contractual rank does not guarantee payment, equal recovery or the absence of a statutory priority. The exception does not itself identify or adjudicate any statute.',
    },
    PLEDGE: {
        'reading': 'While notes remain outstanding, but only until all principal and interest amounts have been placed at the disposal of the Fiscal Agent, the issuer undertakes not to secure present or future capital-market indebtedness or guarantees or other assurances for that indebtedness through Grund- oder Mobiliarpfandrechte over its assets (security rights over land or movable property) without having holders participate at the same time and with the same rank in that security or other security recognized as equivalent by an internationally recognized independent auditor.',
        'duration': 'WHILE_NOTES_OUTSTANDING_UNTIL_ALL_PRINCIPAL_AND_INTEREST_AVAILABLE_TO_FISCAL_AGENT',
        'debt_scope': ['PRESENT_OR_FUTURE_CAPITAL_MARKET_INDEBTEDNESS', 'GUARANTEES_OR_OTHER_ASSURANCES_FOR_THAT_DEBT'],
        'debt_definition': DEFINITION,
        'restricted_security': 'GRUND_ODER_MOBILIARPFANDRECHTE_OVER_ISSUER_ASSETS',
        'holder_participation': 'SIMULTANEOUS_AND_SAME_RANK',
        'security_alternative': 'SAME_SECURITY_OR_OTHER_RECOGNIZED_EQUIVALENT_SECURITY',
        'equivalence_reviewer': 'INTERNATIONALLY_RECOGNIZED_INDEPENDENT_AUDITOR',
        'guarantor_branch_selected': False, 'english_proportionality_adjudicated': False,
        'actual_covenant_compliance': 'NOT_EVALUATED', 'actual_holder_receipt': 'NOT_EVALUATED',
        'qualification': 'This preserves the controlling German issuer covenant, including its limited debt scope and equivalent-security alternative. Funding the Fiscal Agent is not proof of receipt by holders. It does not import the excluded guarantor wording about allowing security to subsist, a proportionality rule from another wording, or section 328 BGB enforcement rights. Actual security, compliance and remedies are not evaluated.',
    },
    DEFINITION: {
        'reading': 'Capital-market indebtedness means an obligation to repay borrowed money represented or evidenced by bonds or other securities with an original maturity of more than one year that are, or can be, listed or traded on a stock exchange or another recognized securities market.',
        'obligation': 'REPAYMENT_OF_BORROWED_MONEY',
        'representation': 'BONDS_OR_OTHER_SECURITIES',
        'maturity_basis': 'ORIGINAL', 'maturity_threshold': 'STRICTLY_GREATER_THAN_ONE_YEAR',
        'market_condition': 'LISTED_OR_TRADED_OR_CAPABLE_OF_LISTING_OR_TRADING',
        'market': 'STOCK_EXCHANGE_OR_OTHER_RECOGNIZED_SECURITIES_MARKET',
        'actual_debt_classification': 'NOT_EVALUATED',
        'qualification': 'The definition is narrower than all borrowed money and broader than securities currently listed or traded. The original maturity, strict greater-than-one-year threshold and potential marketability are retained; no actual obligation is classified here.',
    },
}


def spans(units, identity):
    return [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in PARAGRAPHS[identity]]


def prior_readings(clauses):
    result = [node for node in clauses if node['id'] in PRIOR_IDS]
    if [node['id'] for node in result] != PRIOR_IDS:
        raise ValueError('All twenty prior BASF meanings must survive in order')
    return result


def source_comparison(graph):
    raw = {unit['id']: unit for unit in graph['units']}
    def sources(ids):
        return [anchor(raw[key]) for key in ids]
    return {'version': 'basf-option-i-comparison.v1', 'selected_option': 'I',
        'controlling_language': 'GERMAN',
        'option_authority': sources(lines(65, 49, 49) + lines(108, 1, 4) + lines(89, 1, 3)),
        'records_citation_correction': {
            'historical_option': 'II_FLOATING_RATE',
            'historical_sources': sources(lines(90, 5, 16)),
            'corrected_option': 'I_FIXED_RATE',
            'corrected_sources': sources(lines(66, 71, 79) + lines(67, 1, 3)),
            'german_sources': sources(lines(109, 38, 50)),
            'status': 'WRONG_OPTION_CITATION_CORRECTED; WORDING_DISCREPANCY_REMAINS_UNRESOLVED',
        },
        'pledge_comparison_sources': sources(lines(68, 4, 19)),
        'interpretation': 'Selected German issuer wording controls this supplied reading. English equally and ratably is retained for comparison; no proportionality adjudication or imported guarantor obligation follows.',
        'independent_legal_acceptance': False}


def check_boundary(assembly):
    units = {u['unit']: u for u in assembly['units']}
    if units[basf.KEY + ':p110:l47']['text'] != 'STATUS, NEGATIVVERPFLICHTUNG':
        raise ValueError('Selected issuer status heading changed')
    if any(units[key]['text'] or units[key]['role'] != 'EXCLUDED' for key in EXCLUDED_IDS):
        raise ValueError('Excluded guarantor branch revived')


def prepare(graph, construction, assembly, request, packet):
    prior = prior_readings(request['clauses'])
    references = request['reference_admission']['references']
    if (packet.get('version') != 'basf-status-pledge-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('prior_clauses_sha256') != digest(prior) or
            packet.get('prior_references_sha256') != digest(references) or len(references) != 6):
        raise ValueError('BASF pledge baseline or prior meanings/references changed')
    review(packet['review'])
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in AUTHORITY_IDS]
    comparison = source_comparison(graph)
    if (packet.get('authority_sources') != authority or
            packet.get('context_sources') != [anchor(raw[key]) for key in CONTEXT_IDS] or
            packet.get('source_comparison') != comparison):
        raise ValueError('Exact selected option, issuer, language and comparison sources required')
    check_boundary(assembly)
    units = {unit['unit']: unit for unit in assembly['units']}
    expected_ids = [key for keys in PARAGRAPHS.values() for key in keys]
    if ([row['unit'] for row in packet['units']] != expected_ids or
            any(row['role'] != 'OPERATIVE' for row in packet['units'])):
        raise ValueError('Pledge dispositions must cover exactly the three complete paragraphs')
    for row in packet['units']:
        whole = [{'unit': row['unit'], 'start': 0, 'end': len(units[row['unit']]['text'])}]
        if row['sources'] != [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)]:
            raise ValueError('Pledge disposition must bind exact surviving source pieces')
    clauses = packet['clauses']
    if [node['id'] for node in clauses] != list(PARAGRAPHS):
        raise ValueError('Complete unique status, pledge and definition required')
    for node in clauses:
        expected = spans(units, node['id'])
        if (node['units'] != PARAGRAPHS[node['id']] or node['spans'] != expected or
                node['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in expected) or
                node.get('source_uses') != basf_agents.source_pieces(graph, units, expected) or
                node.get('selection_authority') != authority):
            raise ValueError('Pledge paragraph or exact source/authority changed')
        if (node.get('pledge_reading') != READINGS[node['id']] or node['actor'] != 'issuer' or
                node['affected'] != 'holder' or node['role'] != 'OPERATIVE' or node['effect'] != 'none' or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['questions'] != ['Q1', 'Q2'] or
                node['modality'] != 'statement' or node['election'] != 'none' or node['assets'] != [] or
                node['polarity'] is not True or node['conditions'] != [] or node['exceptions'] != [] or
                not node.get('effect_explanation') or
                node.get('references') != ([DEFINITION_REFERENCE] if node['id'] == PLEDGE else []) or
                node.get('source_comparison') != (comparison if node['id'] == STATUS else None)):
            raise ValueError('Reviewed status/pledge qualification or definition edge changed')
    result = deepcopy(request)
    rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    rows.update({row['unit']: row for row in packet['units']})
    result['reviewed_dispositions'].update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    previous = dispositions(graph, assembly, request['reviewed_dispositions'])
    before = {unit['unit']: unit for unit in previous['units']}
    if any(unit != before[unit['unit']] for unit in selected['units'] if unit['unit'] not in expected_ids):
        raise ValueError('Pledge admission changed an outside source disposition')
    check_boundary(selected)
    result['reference_admission']['assembly_sha256'] = digest(selected)
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = basf_notices.overlay(selected, prior + clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def definition_edge(resolved):
    return {'from': PLEDGE, 'to': DEFINITION, 'kind': 'definition',
            'resolved': resolved, 'authority': None}


def check_meanings(report, request, packet):
    actual = [node for node in report['clause_graph']['nodes'] if node['id'] in PARAGRAPHS]
    requested = [node for node in request['clauses'] if node['id'] in PARAGRAPHS]
    if (actual != packet['clauses'] or requested != packet['clauses'] or
            {node['id']: node['pledge_reading'] for node in actual} != READINGS):
        raise ValueError('Status, pledge or definition changed between review, request and P3')
    if (digest(prior_readings(report['clause_graph']['nodes'])) != packet['prior_clauses_sha256'] or
            digest(prior_readings(request['clauses'])) != packet['prior_clauses_sha256'] or
            len(request['reference_admission']['references']) != 6 or
            digest(request['reference_admission']['references']) != packet['prior_references_sha256']):
        raise ValueError('Prior BASF meanings or six references changed downstream')
    edges = [e for e in report['clause_graph']['edges'] if e['from'] in PARAGRAPHS]
    if edges != [definition_edge(True)]:
        raise ValueError('Resolved exact pledge definition edge required')
    comparison = source_comparison(report['source_map'])
    if packet['source_comparison'] != comparison or actual[0].get('source_comparison') != comparison:
        raise ValueError('Correct selected-option comparison and correction required downstream')
    check_boundary(report['assembly'])
    if report.get('independent_legal_acceptance') is not False:
        raise ValueError('Development pledge reading cannot establish independent acceptance')
    return {'paragraphs': list(PARAGRAPHS), 'meanings_sha256': digest(actual),
            'reviewed_units': sum(map(len, PARAGRAPHS.values())),
            'prior_meanings_sha256': packet['prior_clauses_sha256'],
            'definition_edge': edges[0], 'source_comparison': comparison,
            'actual_compliance_priority_and_recovery': 'NOT_EVALUATED'}


def omitted_clauses(assembly, request, identity):
    if identity not in PARAGRAPHS:
        raise ValueError('Unknown pledge meaning omission')
    retained = prior_readings(request['clauses']) + [node for node in request['clauses']
                if node['id'] in PARAGRAPHS and node['id'] != identity]
    return basf_notices.overlay(assembly, retained)


def matched_missing_definition(report, omitted):
    edges = [e for e in omitted['clauses']['edges'] if e['from'] in PARAGRAPHS]
    if edges != [definition_edge(False)]:
        raise ValueError('Missing debt definition did not expose exact unresolved edge')
    expected = {'Unresolved reference: ' + PLEDGE + ':' + DEFINITION,
                'Missing reference target: ' + DEFINITION}
    findings = {}
    baseline = {'Q1': report['questions']['Q1'], 'Q2': report['questions']['Q2']}
    baseline.update({'Q2.' + name: value for name, value in report['questions']['Q2']['subquestions'].items()})
    rows = [('Q1', omitted['questions']['Q1']), ('Q2', omitted['questions']['Q2'])]
    rows.extend(('Q2.' + name, value) for name, value in omitted['questions']['Q2']['subquestions'].items())
    if set(omitted['questions']['Q2']['subquestions']) != {'compulsory_common', 'possible_common', 'common_only'}:
        raise ValueError('Missing definition control lost a Q2 subquestion')
    for label, question in rows:
        if (question['status'] != 'UNKNOWN' or not expected <= set(question['unresolved']) or
                expected & set(baseline[label]['unresolved'])):
            raise ValueError('Missing definition not exposed in affected question evidence')
        findings[label] = sorted(expected)
    kept = set(PRIOR_IDS) | {STATUS, PLEDGE}
    if ([n for n in omitted['clauses']['nodes'] if n['id'] in kept] !=
            [n for n in report['clause_graph']['nodes'] if n['id'] in kept] or
            omitted['dependencies'] != report['dependencies']):
        raise ValueError('Missing definition changed retained meanings or raw dependencies')
    return {'edge':edges[0], 'question_evidence':findings,
            'other_meanings_equal':True,'direct_dependencies_equal':True}


matched_omission = basf_notices.matched_omission
