"""Supplemental actual-consumer solver compatibility check before sealing034."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_integrity as a

def main():
    a.frozen(True)
    a.costs()
    folder=a.HERE/'stages/solver-compatibility'
    a.save(folder/'started.json',{
        'command':['.venv/bin/python','-m','scripts.prospectus_question_integrity_solver_check'],
        'method_sha256':a.sha(Path(__file__)),
        'evidence_contract':{'question':'Does complete-question reconstruction preserve actual finite and optional-z3 consumer results?',
            'baseline':'Actual interpretation_product results for supplied synthetic 24-fact conjunction',
            'primary':'Complete Q1/Q2 equality on repeated consumer calls for known-true,false and open conditions',
            'veto':'Any rejected valid result or changed complete question',
            'explanatory_only':['Runtime','Case count'],
            'not_concluded':['Cross-version solver witness stability','Legal truth','General solver equivalence']},
        'skeptical_audit':'PASS bounded compatibility diagnostic. Direct original products, no mocked solver. Distinct input states and declared optional engine. Failure requires changed candidate; no acceptance from counts.'})
    started=time.monotonic()
    from legalmath.prospectus.successor import service,clause_graph,contract_assembly,source_graph
    from scripts.prospectus_closure_fixtures import request,PREFIX,LOSS
    rows=[]
    try:
        with tempfile.TemporaryDirectory(prefix='prospectus-question-solver-') as name:
            root=Path(name)
            for engine in ('finite','z3'):
                for label,observations in (('true',{'fact'+str(i):True for i in range(24)}),
                                           ('false',{'fact0':False}),('open',{})):
                    path=root/(engine+'-'+label);path.mkdir()
                    req=request(path,[PREFIX+LOSS])
                    graph=source_graph.build(req['bundle'],path)
                    clauses=clause_graph.build(contract_assembly.assemble(graph,req['assembly']))['nodes']
                    next(n for n in clauses if n['effect']=='principal_loss')['conditions']={'all':['fact'+str(i) for i in range(24)]}
                    req.update(clauses=clauses,predicate_engine=engine,observations=observations)
                    p1=service.source_product(req,path);p2=service.construction_product(p1,path)
                    p3=service.interpretation_product(p1,p2)
                    products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
                    for repeat in range(3):
                        answer=service.consume(products,path,mode='frozen')
                        for q in ('Q1','Q2'):assert answer['questions'][q]==p3['payload']['questions'][q]
                    rows.append({'engine':engine,'input':label,'status':p3['payload']['questions']['Q1']['status'],
                        'complete_questions_equal':True,'repetitions':3,'products_sha256':a.digest(products)})
        a.save(folder/'result.json',{'status':'PASS','wall_seconds':time.monotonic()-started,
            'rows':rows,'method_sha256':a.sha(Path(__file__)),
            'runtime_scope':'Same local runtime only','cross_version_solver_stability_proved':False})
        print(json.dumps({'status':'PASS','cases':len(rows),'consumer_replays':18,'resources':a.costs()}))
    except BaseException as exc:
        a.save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise

if __name__=='__main__':main()
