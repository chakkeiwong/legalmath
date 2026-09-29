"""Bounded Dung graph semantics; legal acceptability of premises is a separate question."""
from itertools import combinations
from ...errors import LegalMathError


def evaluate_arguments(arguments, attacks, *, maximum=12):
    nodes=set(arguments)
    if len(nodes)!=len(arguments):raise LegalMathError('E_DUPLICATE_ID')
    if len(nodes)>maximum or maximum>16:raise LegalMathError('E_RESOURCE_LIMIT')
    edges={tuple(e) for e in attacks}
    if any(len(e)!=2 or not set(e)<=nodes for e in edges):raise LegalMathError('E_REFERENCE')
    attackers={n:{a for a,b in edges if b==n} for n in nodes}
    def attacked(s):return {b for a,b in edges if a in s}
    def characteristic(s):
        defeated=attacked(s)
        return {n for n in nodes if attackers[n]<=defeated}
    grounded=set()
    while True:
        updated=characteristic(grounded)
        if updated==grounded:break
        grounded=updated
    stable=[];ordered=sorted(nodes)
    for size in range(len(nodes)+1):
        for members in combinations(ordered,size):
            s=set(members)
            if not any(a in s and b in s for a,b in edges) and nodes-s<=attacked(s):stable.append(list(members))
    skeptical=set.intersection(*(set(e) for e in stable)) if stable else set()
    return {'grounded':sorted(grounded),'stable_extensions':stable,
            'skeptical_stable':sorted(skeptical),'stable_extension_exists':bool(stable),
            'undecided_grounded':sorted(nodes-grounded-attacked(grounded)),
            'legal_premises_verified':False,'semantics':'BOUNDED_DUNG_V1'}
