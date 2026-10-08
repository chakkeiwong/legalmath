from itertools import product
from legalmath.interpretation.semantics.lower import expression,boolean
from legalmath.interpretation.semantics.render import across_extensions
from legalmath.interpretation.semantics.records import Outcome

def test_independent_truth_tables_exhaust_declared_binary_domain():
    # Literal truth tables are the declared three-valued specification, not
    # outcomes copied from the implementation or English-quality labels.
    names=("false","unknown","true")
    and_table=(("false","false","false"),("false","unknown","unknown"),("false","unknown","true"))
    or_table=(("false","unknown","true"),("unknown","unknown","true"),("true","true","true"))
    for i,j in product(range(3),repeat=2):
        values={"a":names[i],"b":names[j]}
        assert boolean(expression("(and a b)",set(values)),values)==and_table[i][j]
        assert boolean(expression("(or a b)",set(values)),values)==or_table[i][j]
        assert boolean(expression("(not a)",set(values)),values)==names[2-i]
        expect=names[j] if i==2 else "false" if i==0 else "unknown"
        assert boolean(expression("(if a b false)",set(values)),values)==expect

def test_all_extension_value_pairs_preserve_qualification():
    values=("true","false","unknown")
    for left,right in product(values,repeat=2):
        items=[Outcome(query_id="q",branch_id="a"*64,extension_ids=(str(i),),value=v,
            completion="complete",lowering="supported",reasons=("unknown-interpretation",),witnesses=(str(i),))
            for i,v in enumerate((left,right))]
        result=across_extensions(items)
        expected=left if left==right else "conflict" if {left,right}=={"true","false"} else "unknown"
        assert result.value==expected
        assert set(result.witnesses)=={"0","1"}
        assert "unknown-interpretation" in result.reasons
