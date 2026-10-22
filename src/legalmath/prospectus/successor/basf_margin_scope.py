"""One reviewed BASF printed margin; no inference of unreviewed bar extents."""
from copy import deepcopy

from . import basf, basf_agents
from .admissions import structure
from .contracts import digest
from .occurrences import anchor


def admit(graph, assembly, request, packet):
    """Bind the page-132 listed branch to its independently fixed source extent."""
    if (packet.get('version') != 'basf-margin-page132.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('assembly_sha256') != digest(assembly) or
            packet.get('parent_request_sha256') != digest(request)):
        raise ValueError('BASF margin source, assembly or parent request changed')
    raw = {u['id']: u for u in graph['units']}
    selected = {u['unit']: u for u in assembly['units']}

    def ids(first, last):
        return [f'{basf.KEY}:p132:l{i}' for i in range(first, last + 1)]

    def sources(keys):
        return [anchor(raw[key]) for key in keys]

    governors = sources(ids(3, 11))
    target_ids = ids(20, 29)
    if any(selected[key]['role'] != 'OPERATIVE' for key in target_ids):
        raise ValueError('BASF listed-notice scope is not fully selected')
    spans = [{'unit': key, 'start': 0, 'end': len(selected[key]['text'])}
             for key in target_ids]
    targets = [p['source'] for p in basf_agents.source_pieces(graph, selected, spans)]
    excluded = ids(30, 34)
    if any(selected[key]['role'] != 'EXCLUDED' for key in excluded):
        raise ValueError('BASF unlisted alternative must remain excluded')
    premises = [f'basf-2032-final:p7:l{i}' for i in range(40, 48)]
    premises += [f'basf-2032-final:p13:l{i}' for i in range(44, 52)]
    expected = {'governors': governors, 'targets': targets,
                'premises': sources(premises),
                'excluded_unlisted_alternative': sources(excluded),
                'shared_outside_scope': sources(ids(35, 39)),
                'nonprinting_extracted_row': sources(ids(12, 12))[0]}
    for name, value in expected.items():
        if packet.get(name) != value:
            raise ValueError('BASF complete printed scope changed: ' + name)
    if (packet.get('automatic_scope') is not False or
            packet.get('whole_margin_inventory_complete') is not False):
        raise ValueError('BASF supplied scope cannot claim automatic or whole-inventory coverage')
    admission = packet['governing_admission']
    structure(graph, admission)
    if admission['documents'] or admission['review'] != packet['review']:
        raise ValueError('BASF margin admission review or projection changed')
    edges = admission['governing']
    if len(edges) != len(governors):
        raise ValueError('BASF complete margin condition required')
    for line, source, edge in zip(range(3, 12), governors, edges):
        if (edge['id'] != f'basf-listed-notices-margin-{line}' or
                edge['from'] != source or edge['to'] != targets or
                edge['questions'] != ['Q1', 'Q2'] or
                edge['reason'] != packet['review']['reason']):
            raise ValueError('BASF governing relationship differs from complete reviewed extent')
    return deepcopy(admission)
