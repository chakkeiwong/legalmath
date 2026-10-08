"""Bounded causal diagnostic; unchanged production code, synthetic inputs only."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import digest
from legalmath.interpretation.semantics import scoped_standards as ss, conditional_ir as ir, lower
from scripts.legal_interpretation_successor_data import retained_inputs, policy
from scripts import legal_interpretation_s4_execute as s4

OUT=Path(__file__).resolve().parent
S4=ROOT/'artifacts/legal-interpretation-program/successor-s4/attempt-1'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):
    with (OUT/name).open('x') as f: json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')

def main():
    start=time.monotonic(); started=datetime.now(timezone.utc).isoformat()
    baseline=read(OUT/'baseline-verification.json')
    assert baseline['status']=='PASS' and baseline['method']==s4.method()
    development=read(S4/'development-inputs.json')
    packet=development['packet']; initial=development['standards_input']
    cases=[]
    def compute(name,value):
        result=ss.compute(value,packet,{}, {},[])
        program,mapping=ir.lower(result)
        derived=ir.reference(program)
        assert derived==[i for i,r in enumerate(result['evaluation']['results']) if r['status']=='CONDITIONALLY_DERIVED']
        assert result['release_eligible'] is False and result['legal_correctness']=='NOT_ESTABLISHED'
        for r in result['evaluation']['results']:
            assert r['legal_correctness']=='NOT_ESTABLISHED'
            assert r['opposite_consequence']=='NOT_ESTABLISHED'
            if not r['rule_id'].startswith('diagnostic.'):
                assert any('not satisfaction, breach' in x for x in r['limits'])
        rows={r['rule_id']:r for r in result['evaluation']['results']}
        cases.append({'name':name,'inputs':deepcopy(value),'result':result,
            'lowering':mapping,'reference_derived_heads':[program.heads[i] for i in derived],
            'claim_scope':'Unchanged S4 component computation and declared conditional lowering, not a new full product or legal accuracy test'})
        return rows
    def set_state(value,key,state):
        model=next(p for p in initial['premises'] if p['requirement_id']==key)
        value['premises']=[p for p in value['premises'] if p['requirement_id']!=key]
        for positive in {'true':[True],'false':[False],'unknown':[],'conflict':[True,False]}[state]:
            p=deepcopy(model);p.update(id='probe.'+key+'.'+str(positive),positive=positive,
                scope=deepcopy(value['assessment']['scope']),provider=value['assessment']['provider'],
                jurisdiction=value['assessment']['jurisdiction'],basis='Explicit synthetic diagnostic state, not legal truth.')
            value['premises'].append(p)
    unchanged=compute('unchanged-S4-development',deepcopy(initial))
    assert cases[-1]['result']==read(S4/'development-computation.json')
    for state in ('true','false','unknown','conflict'):
        value=deepcopy(initial);set_state(value,'p10-responsibility.interpretation',state)
        rows=compute('p10-interpretation-'+state,value)
        r=rows['p10-responsibility']
        assert r['status']==('CONDITIONALLY_DERIVED' if state=='true' else 'NOT_DERIVED')
        assert r['question']=='Does this scope carry the proposed paragraph 10 retained-responsibility requirement?'
        assert r['consequence']==unchanged['p10-responsibility']['consequence']
    value=deepcopy(initial);set_state(value,'p10-responsibility.interpretation','true')
    value['assessment']['scope']['interval']={'start':None,'end':None}
    rows=compute('unknown-assessment-interval',value)
    assert all(r['status']=='NOT_DERIVED' for r in rows.values())
    request_summary=[]
    for q14,q15,q16 in itertools.product(('true','false','unknown','conflict'),('true','false'),('true','false')):
        value=deepcopy(initial)
        for k,state in (('p14-request',q14),('p15-request',q15),('p16-request',q16)): set_state(value,k,state)
        rows=compute('requests-'+q14+'-'+q15+'-'+q16,value)
        expected={'p14-confirmation':True,'p14-A-demonstration':q14=='true','fn5-B-demonstration':True,
            'fn5-C-demonstration':q14=='true','p15-audit':q15=='true','p16-opinion':q16=='true'}
        for k,want in expected.items():
            assert (rows[k]['status']=='CONDITIONALLY_DERIVED')==want,(k,q14,q15,q16)
            assert rows[k]['consequence']==unchanged[k]['consequence']
        assert rows['p14-A-demonstration']['consequence']!=rows['fn5-C-demonstration']['consequence']
        request_summary.append({'p14':q14,'p15':q15,'p16':q16,'derived':{k:r['status'] for k,r in rows.items() if k in expected}})
    # All observed events require an additional sufficiency premise. Positive
    # controls assert that premise explicitly and remain conditional hypotheses.
    for rule in initial['standards'][14:]:
        key=rule['id']; assert unchanged[key]['status']=='NOT_DERIVED'
        value=deepcopy(initial)
        template=deepcopy(initial['premises'][0])
        template.update(id='probe.'+key+'.sufficiency',requirement_id=key+'.sufficiency',kind='inference-premise',
            basis='Assume the diagnostic implication solely to check execution; not established by the source.',positive=True)
        value['premises'].append(template)
        rows=compute(key+'-explicit-sufficiency',value)
        expected=key in ('diagnostic.supervision','diagnostic.remediation','diagnostic.reconciliation')
        assert (rows[key]['status']=='CONDITIONALLY_DERIVED')==expected
        if not expected:
            # Missing access/acceptance and wrong relationship identity survive
            # even a supplied sufficiency premise.
            assert rows[key]['reasons']
    # Actual legacy reference outputs retain meaning qualifications.
    p,overlay,candidates,questions,comparisons=retained_inputs(ROOT)
    assignments={
        'registrar-defect-with-assessed-retention':{'selected_provider_in_scope':'true','responsibility_retained':'true','arrangement_sound':'true','ownership_records_proper':'false'},
        'nominal-only-no-retention-standard':{'selected_provider_in_scope':'true','responsibility_retained':'unknown','arrangement_sound':'true','ownership_records_proper':'true'},
        'assessed-retention-failure':{'selected_provider_in_scope':'true','responsibility_retained':'false','arrangement_sound':'true','ownership_records_proper':'true'},
        'unknown-scope':{'selected_provider_in_scope':'unknown','responsibility_retained':'true','arrangement_sound':'true','ownership_records_proper':'true'},
        'conflicting-retention':{'selected_provider_in_scope':'true','responsibility_retained':'conflict','arrangement_sound':'true','ownership_records_proper':'true'},
    }
    formula_results=[]
    for cid in ('node.210068a368d2d851d97f6b2c','deferred.744c4b5d99bc07afffce029b','node.77939279648de731412dc142'):
        reading=candidates[cid];branch=lower.from_legacy(p,reading,questions[cid],policy())
        variants=assignments if cid!='node.77939279648de731412dc142' else {
            'partial-responsibility-loss':{'is_product_provider':'true','is_primary_dealing_in_scope':'true','management_responsibility_retained':'true','operational_responsibility_retained':'true','recordkeeping_responsibility_retained':'false'}}
        for name,states in variants.items():
            facts={}
            for key,state in states.items():
                f={'status':'known' if state in ('true','false') else state,'valid_from':'2026-04-20','valid_until':None,
                    'recorded_at':'2026-04-20','complete':True}
                if state in ('true','false'): f['value']=state=='true'
                facts[key]=f
            case={'id':name,'snapshot':{'facts':facts},'valid_at':'2026-04-30','known_at':'2026-05-01'}
            result=lower.reference(branch,reading,case).model_dump(mode='json')
            assert 'unknown-interpretation' in result['reasons']
            expected={'registrar-defect-with-assessed-retention':'true' if cid.startswith('node.210') else 'false',
                'nominal-only-no-retention-standard':'unknown','assessed-retention-failure':'false',
                'unknown-scope':'unknown','conflicting-retention':'conflict','partial-responsibility-loss':'false'}[name]
            assert result['value']==expected,(cid,name,result)
            formula_results.append({'reading_id':cid,'reading_hash':digest(reading),'scenario':name,'synthetic_states':states,
                'original_formalization':reading['formalization'],'actual_reference_output':result})
    assert baseline['method']==s4.method(), 'Diagnostic changed baseline method'
    summary={'status':'PASS','scoped_variants':len(cases),'formula_variants':len(formula_results),
        'candidate':'Additional duty-versus-fulfillment guard','candidate_decision':'REJECT_AS_UNNECESSARY_FOR_INSPECTED_ROUTE',
        'engineering_finding':'S4 preserves duty questions, consequence text, non-fulfillment limits, unresolved meaning, distinct requests and missing sufficiency.',
        'production_code_edits':0,'legal_closures':0,'english_fidelity':'NOT_ESTABLISHED','release_eligible':False}
    save('diagnostic-results.json',{'summary':summary,'scoped_cases':cases,'request_matrix':request_summary,'legacy_formula_results':formula_results})
    save('diagnostic-manifest.json',{'command':'.venv/bin/python -c \'import runpy; runpy.run_path("artifacts/legal-interpretation-program/problem-led-follow-up/run_diagnostics.py",run_name="__main__")\'',
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'started_at':started,'wall_seconds':time.monotonic()-start,'environment':sys.executable,'python':sys.version,
        'cpu_gpu':'CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden','data_version':{'path':str((S4/'development-inputs.json').relative_to(ROOT)),'sha256':sha(S4/'development-inputs.json')},
        'seeds':'N/A: deterministic conditional examples','plan':'docs/implementation/legal-interpretation-program/follow-up/intervention-audit.md',
        'result_file':'artifacts/legal-interpretation-program/problem-led-follow-up/diagnostic-results.json','result_sha256':sha(OUT/'diagnostic-results.json'),
        'baseline_verification_sha256':sha(OUT/'baseline-verification.json'),'script_sha256':sha(Path(__file__)),
        'network_requests':0,'provider_calls':0,'source_test_driver_changes':0})
    save('question-provenance.json',{'source_overlay_sha256':sha(ROOT/'artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2/overlay.json'),
        'question_kinds':'Original reading statements and retained subsidiary questions remain original evidence; S1 adapter control questions were synthesized for conditional execution.',
        'readings':[{'reading_id':cid,'retained_statement':candidates[cid]['statement'],
            's1_synthesized_control_question':questions[cid],
            'role_question_records':[{'role':r['role'],'question_texts':r['operative']['question_texts'],'responses':r['operative']['questions']} for r in overlay['records'] if r['reading_id']==cid]}
            for cid in sorted(candidates)]})
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
