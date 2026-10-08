from legalmath.interpretation.semantics.pyarg_adapter import availability
from legalmath.interpretation.semantics.arguments import Argument,Attack,Theory,evaluate

def test_archive_is_explicitly_unavailable():
    report=availability(".localresources/legal-interpretation-reuse-2026-10-05/sources/DaphneOdekerken__PyArg")
    assert report["status"]=="UNAVAILABLE" and report["missing"]
    assert report["equivalence_to_pyarg"]=="NOT_ESTABLISHED"

def test_independent_complete_extension_oracle_all_three_node_graphs():
    # Enumerate complete extensions using membership equivalence, independently
    # of the implementation's admissible-set maximality/grounded iteration.
    ids=("a","b","c")
    for mask in range(512):
        edges={(ids[i],ids[j]) for i in range(3) for j in range(3) if mask & (1<<(i*3+j))}
        complete=[]
        for bits in range(8):
            chosen={ids[i] for i in range(3) if bits & (1<<i)}
            if any(a in chosen and b in chosen for a,b in edges): continue
            defended={x for x in ids if all(any((d,a) in edges for d in chosen) for a,b in edges if b==x)}
            if chosen==defended: complete.append(chosen)
        minimal=set.intersection(*complete)
        maximal={tuple(sorted(s)) for s in complete if not any(s<t for t in complete)}
        t=Theory(tuple(Argument(i,i) for i in ids),tuple(Attack(a,b,"declared",b) for a,b in edges))
        assert evaluate(t,"grounded").extensions==(tuple(sorted(minimal)),)
        assert set(evaluate(t,"preferred").extensions)==maximal
