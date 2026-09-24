from legalmath.interpretation.search.questions import behavioral_groups


def test_equivalence_clustering_does_not_assume_unchecked_transitivity():
    nodes=[{'node_id':n} for n in ('a','b','c')]
    comparisons=[{'pair':['a','b'],'result':{'status':'EQUIVALENT_WITHIN_DOMAIN'}},
                 {'pair':['b','c'],'result':{'status':'EQUIVALENT_WITHIN_DOMAIN'}}]
    result=behavioral_groups(nodes,comparisons)
    assert result['groups']==[['a','b'],['c']] and result['distinct_source_commitments_preserved']
