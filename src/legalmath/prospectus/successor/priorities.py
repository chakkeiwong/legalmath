"""Explicit reviewed defeat between comparable clauses; cycles are unresolved."""
from .admissions import review
from .anchors import fields
from .contracts import digest
from .occurrences import uses


def admit(source_graph, assembly, clauses, packet):
    fields(packet, {'version','assembly_sha256','review','edges'}, {'version','assembly_sha256','review','edges'})
    if packet['version'] != 'reviewed-priorities.v1' or packet['assembly_sha256'] != digest(assembly):
        raise ValueError('Priority admission assembly changed')
    review(packet['review'])
    nodes = {n['id']:n for n in clauses['nodes']}
    ids, edges = set(), []
    for row in packet['edges']:
        fields(row, {'id','higher','lower','authority','reason'}, {'id','higher','lower','authority','reason'})
        if (not row['id'] or row['id'] in ids or not row['reason'] or
                row['higher'] not in nodes or row['lower'] not in nodes or row['higher'] == row['lower']):
            raise ValueError('Distinct bound priority endpoints required')
        higher, lower = nodes[row['higher']], nodes[row['lower']]
        if (any(higher[k] != lower[k] for k in ('effect','actor','affected','questions')) or
                higher['effect'] in {'none','unknown'} or higher['role'] != 'OPERATIVE' or lower['role'] != 'OPERATIVE'):
            raise ValueError('Priority requires comparable operative effects and scope')
        for question in lower['questions']:
            if len(uses(source_graph, assembly, row['authority'], question=question)) != 1:
                raise ValueError('Priority authority is not an applicable selected occurrence')
        ids.add(row['id'])
        edges.append({'id':row['id'], 'from':row['lower'], 'to':row['higher'],
                      'kind':'priority', 'authority':row['authority'], 'resolved':True})
    return {**clauses, 'edges':clauses['edges']+edges, 'priorities':packet,
            'priority_semantics':'Active higher clause defeats lower clause; cycles remain UNKNOWN'}
