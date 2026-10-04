"""Independent solver/graph fixtures with existing generated Java witness replay."""
from copy import deepcopy
from itertools import product
from pathlib import Path

from legalmath.interpretation.assurance.diversity import cvc5_compare,clingo_extensions,conclusion_support,save
from legalmath.interpretation.search.arguments import evaluate_arguments
from legalmath.interpretation.search.formal import Comparisons,expression,bundle,RULE,project
from legalmath.ir.evaluate import evaluate
from legalmath.java.manifest import run_java

ROOT=Path(__file__).resolve().parents[1]


def run(out):
    from tests.assurance.support import reading,packet
    out.mkdir(parents=True,exist_ok=False)
    a=reading();a['formalization']['facts'] += [
        {'name':n,'type':'bool','meaning':meaning,'unit':'truth value','source_unit_ids':['p1'],'requires_judgment':True}
        for n,meaning in [('specific','Promotion concerns a specific product'),('type_link','Promotion concerns a particular product type')]]
    a['formalization']['result']='(and gift (not discount) (or specific type_link))'
    checker=Comparisons(out/'work',ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1','2026-09-25T00:00:00.000000Z')
    formulas={'same':a['formalization']['result'],'missing-exception':'(and gift (or specific type_link))',
              'missing-type':'(and gift (not discount) specific)','wrong-polarity':'(not (and gift (not discount) (or specific type_link)))'}
    comparisons=[]
    for name,text in formulas.items():
        b=deepcopy(a);b['formalization']['result']=text
        external=cvc5_compare(expression(a['formalization']['result'],'a'),expression(text,'b'),[f['name'] for f in a['formalization']['facts']])
        existing=checker.compare(a,b,packet())
        expected='EQUIVALENT_WITHIN_DOMAIN' if name=='same' else 'DIFFERENT'
        if external['status']!=expected or existing['status']!=expected:raise ValueError('Cross-solver mismatch: '+name)
        if external['witness'] is not None:
            at=checker.at
            snapshot={'subject_id':'cvc5.witness','facts':{n:(
                {'type':'bool','status':'unknown','reason':'MISSING'} if v=='U' else
                {'type':'bool','status':'known','value':v=='T','evidence_ids':['synthetic.cvc5'],
                 'valid_from':at,'valid_until':None,'recorded_at':at}) for n,v in external['witness'].items()}}
            replay=[]
            for candidate in (a,b):
                compiled=bundle(candidate,packet(),at);built=checker.build(compiled)
                case={'bundle':compiled,'snapshot':snapshot,'rule_id':RULE,'valid_at':at,'known_at':at}
                python=project(evaluate(compiled,snapshot,RULE,at,at))
                java=project(run_java(built['jar'],[case],checker.jdk,built['class_name'])[0])
                if python!=java:raise ValueError('cvc5 witness Java/Python mismatch')
                replay.append({'python':python,'java':java})
            if replay[0]['python']==replay[1]['python']:raise ValueError('cvc5 witness does not distinguish actual engines')
            external.update(snapshot=snapshot,replays=replay)
        comparisons.append({'case':name,'cvc5':external,'z3_java':existing,'expected':expected})
    # Numerical boundary is a separate, explicitly scoped obligation.
    import cvc5
    from cvc5 import Kind as K
    import z3
    tm=cvc5.TermManager();solver=cvc5.Solver(tm);solver.setOption('produce-models','true');solver.setLogic('QF_LIA')
    x=tm.mkConst(tm.getIntegerSort(),'months');six=tm.mkInteger(6)
    solver.assertFormula(tm.mkTerm(K.DISTINCT,tm.mkTerm(K.GEQ,x,six),tm.mkTerm(K.GT,x,six)))
    status=solver.checkSat();witness=int(str(solver.getValue(x))) if status.isSat() else None
    z=z3.Int('months');zs=z3.Solver();zs.add((z>=6)!=(z>6));zstatus=zs.check()
    if witness!=6 or zstatus!=z3.sat or zs.model()[z].as_long()!=6:raise ValueError('Threshold boundary mismatch')
    graphs=[]
    # Every directed graph on up to three arguments, including self attacks.
    for n in range(4):
        names=[str(i) for i in range(n)];possible=list(product(names,repeat=2))
        for bits in product((False,True),repeat=len(possible)):
            edges=[list(e) for e,yes in zip(possible,bits) if yes]
            actual=clingo_extensions(names,edges);baseline=evaluate_arguments(names,edges)
            if not actual['complete'] or sorted(actual['extensions'])!=sorted(baseline['stable_extensions']):
                raise ValueError('Argument solver mismatch: '+str(edges))
            graphs.append({'arguments':names,'attacks':edges,'extensions':actual['extensions'],'complete':True})
    mutual=clingo_extensions(['a','b'],[['a','b'],['b','a']])
    skeptical=conclusion_support(mutual['extensions'],{'a':'p','b':'p'},mutual['complete'])
    limited=clingo_extensions(['a','b'],[['a','b'],['b','a']],maximum_models=1)
    if skeptical['skeptical_conclusions']!=['p'] or limited['complete']:raise ValueError('Quantifier/truncation control failed')
    save(out/'formula-comparisons.json',comparisons);save(out/'graph-comparisons.json',graphs)
    result={'engineering_status':'PASS','boolean_comparisons':len(comparisons),'integer_boundary':witness,
            'directed_graphs':len(graphs),'conclusion_skepticism':skeptical,'truncation':limited,
            'scope':'Four illustrative candidate bodies, one integer boundary, all graphs up to three nodes',
            'shared_inputs':['Parsed expressions','Assumed identical fact definitions','Graph facts supplied by caller'],
            'legal_correctness_established':False,'release_eligible':False}
    save(out/'result.json',result);return result
