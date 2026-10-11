"""Bounded BASF procedural reading, supplied premises rather than legal adjudication."""
from copy import deepcopy
from . import basf, clause_graph
from .admissions import dispositions, review
from .anchors import bind
from .contracts import digest
from .occurrences import uses
from .reviewed_references import admit


def lines(page, first, last):
    return [f'{basf.KEY}:p{page}:l{i}' for i in range(first, last + 1)]


PARAGRAPHS = {
    'basf-notices:publication': lines(132, 20, 23),
    'basf-notices:clearing-substitution': lines(132, 24, 29),
    'basf-notices:holder-notice': lines(132, 35, 39),
    'basf-notices:holding-proof': lines(132, 67, 86) + lines(133, 1, 10),
}


def overlay(assembly, clauses):
    """Replace exact reviewed spans, preserving every outside nomination character."""
    selected = {u['unit']: u for u in assembly['units']}
    covered = {}
    for node in clauses:
        for span in node['spans']:
            covered.setdefault(span['unit'], set()).update(range(span['start'], span['end']))
    retained = []
    for node in clause_graph.nominate(assembly):
        spans = []
        for span in node['spans']:
            start = None
            for pos in range(span['start'], span['end'] + 1):
                keep = pos < span['end'] and pos not in covered.get(span['unit'], ())
                if keep and start is None:
                    start = pos
                elif not keep and start is not None:
                    spans.append({'unit': span['unit'], 'start': start, 'end': pos})
                    start = None
        if spans:
            node.update(spans=spans, units=list(dict.fromkeys(s['unit'] for s in spans)),
                        quote=' '.join(selected[s['unit']]['text'][s['start']:s['end']] for s in spans))
            retained.append(node)
    return retained + deepcopy(clauses)


def prepare(graph, construction, assembly, request, packet):
    """Validate this reviewed edition before composing existing service interfaces."""
    if (packet.get('version') != 'basf-notices-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly)):
        raise ValueError('BASF notice packet baseline changed')
    review(packet['review'])
    for source in packet['authority_sources']:
        bind(graph, source)
    result = deepcopy(request)
    previous = result['reviewed_dispositions']
    rows = {row['unit']: row for row in previous['units']}
    if len({row['unit'] for row in packet['units']}) != len(packet['units']):
        raise ValueError('Duplicate notice disposition')
    rows.update({row['unit']: row for row in packet['units']})
    previous.update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, previous)
    units = {u['unit']: u for u in selected['units']}
    clauses = packet['clauses']
    if len(clauses) != len(PARAGRAPHS) or {c['id'] for c in clauses} != set(PARAGRAPHS):
        raise ValueError('Complete unique BASF notice paragraphs required')
    for node in clauses:
        expected = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}
                    for key in PARAGRAPHS[node['id']]]
        if (node['spans'] != expected or node['units'] != PARAGRAPHS[node['id']] or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['effect'] != 'none' or
                not node.get('effect_explanation') or node['role'] != 'OPERATIVE'):
            raise ValueError('Incomplete notice paragraph or changed effect scope')
        mapped = []
        for row in node['source_uses']:
            matches = uses(graph, {'units': [units[row['use']]]}, row['source'])
            if len(matches) != 1:
                raise ValueError('Notice source is not its exact operative occurrence')
            mapped.append({k: matches[0][k] for k in ('unit', 'start', 'end')})
        if mapped != expected:
            raise ValueError('Notice sources omit or change selected paragraph characters')
        meaning = node.get('procedural_reading', {})
        if not meaning.get('reading') or not meaning.get('qualification'):
            raise ValueError('Positive procedural reading and qualification required')
    meanings = {c['id'].split(':')[-1]: c['procedural_reading'] for c in clauses}
    if (meanings['holding-proof'].get('exclusive_route') is not False or
            not meanings['holding-proof'].get('alternative_route') or
            not meanings['holding-proof'].get('certificate_and_copy_route') or
            meanings['clearing-substitution'].get('substitution_requires_exchange_rules_permission') is not True or
            meanings['holder-notice'].get('proof_reference') != 'holder-notice-proof'):
        raise ValueError('Notice procedural qualification or holding-proof alternative missing')
    references = packet['references']
    notice_units = lines(132, 20, 29) + lines(132, 35, 39)
    if (len(references) != 1 or references[0]['id'] != 'make-whole-notices' or
            [r['use'] for r in references[0]['targets']] != notice_units or
            references[0]['from_use'] != basf.KEY + ':p121:l9'):
        raise ValueError('Complete selected notice reference required')
    for target in references[0]['targets']:
        mapped = uses(graph, {'units': [units[target['use']]]}, target['source'])
        if len(mapped) != 1 or mapped[0]['start'] != 0 or mapped[0]['end'] != len(units[target['use']]['text']):
            raise ValueError('Notice reference must retain the complete target occurrence')
    result['reference_admission'].update(assembly_sha256=digest(selected))
    result['reference_admission']['references'].extend(deepcopy(references))
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = overlay(selected, clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def check_meanings(report, request, expected_clauses):
    """Check actual P3 output, including qualifications not reflected by Q1/Q2 status."""
    actual = [n for n in report['clause_graph']['nodes'] if n['id'] in PARAGRAPHS]
    requested = [n for n in request['clauses'] if n['id'] in PARAGRAPHS]
    if actual != expected_clauses or requested != expected_clauses:
        raise ValueError('BASF procedural reading lost or changed between review, request and P3')
    if report.get('independent_legal_acceptance') is not False:
        raise ValueError('Development notice meanings cannot establish independent acceptance')
    return {'paragraphs': [n['id'] for n in actual], 'meanings_sha256': digest(actual),
            'reviewed_units': sum(len(n['units']) for n in actual),
            'procedural_law_decision': 'NOT_EVALUATED', 'exclusive_holding_proof_route': False}


def matched_omission(assembly, full_graph, omitted_graph, clauses):
    """Exact-character effect, with outside meanings held constant."""
    def characters(nodes, unknown_only=False):
        return {(s['unit'], i) for n in nodes if not unknown_only or n['effect'] == 'unknown'
                for s in n['spans'] for i in range(s['start'], s['end'])
                if not by_id[s['unit']]['text'][i].isspace()}
    by_id = {u['unit']: u for u in assembly['units']}
    reviewed = characters(clauses)
    full = characters(full_graph['nodes'], True)
    omitted = characters(omitted_graph['nodes'], True)
    if reviewed & full or not reviewed <= omitted or full - reviewed != omitted - reviewed:
        raise ValueError('Notice omission did not isolate the reviewed character meanings')
    if characters(full_graph['nodes']) != characters(omitted_graph['nodes']):
        raise ValueError('Notice overlay lost outside clause coverage')
    return {'reviewed_nonspace_characters': len(reviewed), 'unknown_with_reading': len(reviewed & full),
            'unknown_without_reading': len(reviewed & omitted), 'outside_unknown_characters_equal': True}
