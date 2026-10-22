"""Measured local preparation; never admits or executes a substantive package."""
import argparse
from copy import deepcopy
import os
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from scripts.prospectus_bes_cash_flow import (REVIEW,FIXTURE,TESTS,SELECTOR,METHODS,PLAN,MASTER,
    NORMAL,PRIOR,SOURCE,compressed,small_fixture,products,make_profile,storage,load)
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from legalmath.prospectus.successor.contracts import digest as product_digest

def freeze():
    authority=Authority(ROOT);program,tasks,_=authority.spec()
    if program['revision']!=209: raise ValueError('Expected209 retained failure baseline')
    folder=ROOT/REVIEW
    preparation=read(folder/'preparation.json')
    if preparation['stages'][-1]['status']!='PASS': raise ValueError('Focused preparation has not passed')
    ps=products(ROOT)
    profile=make_profile(ROOT,ps['P1']['payload']['graph'])
    inputs={NORMAL+'/original-P1.json.gz',NORMAL+'/candidate-P2-P5.json.gz',
            NORMAL+'/candidate-answer.json.gz',PRIOR+'/profile.json.gz',PRIOR+'/source-units.json.gz',
            REVIEW+'/preparation.json',PLAN,MASTER,NORMAL+'/reading-input.json',
            SOURCE+'/attempt-009/run-manifest.json',SOURCE+'/attempt-009/result.json'}
    for e in profile['editions']: inputs.add(e['image']['path'])
    original=load(ROOT/NORMAL/'original-P1.json.gz')
    inputs.update(d['path'] for d in original['payload']['request']['bundle']['documents'])
    def composition(path):
        inputs.add(path);spec=read(ROOT/path)
        inputs.add(spec['overlay']['path'])
        if 'predecessor' in spec: composition(spec['predecessor']['path'])
        else: inputs.add(spec['baseline']['path'])
    composition(PRIOR+'/answer-composition.json')
    write(folder/'profile.json',profile,exclusive=True)
    inputs.add(REVIEW+'/profile.json')
    frozen={'selector':SELECTOR,'methods':{n:file_hash(ROOT/n) for n in METHODS},
            'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},
            'original_graph_product_sha256':product_digest(original['payload']['graph']),
            'original_graph_authority_sha256':digest(original['payload']['graph']),
            'historical_seconds':948.8160658078269,
            'minimum_focused_tests':182,
            'selected_parent_sha256':ps['P1']['sha256'],
            'normal_comparator':'Entire original003 answer; all subsequent complete compositions retained',
            'current_extraction_claim':False}
    write(folder/'frozen.json',frozen,exclusive=True)
    state=storage(ROOT,ROOT/REL/'attempts/source-bes-dep-07/attempt-010')
    if state['combined_bytes']+12*1024**2+SELECTOR['reserve_bytes']>=SELECTOR['combined003_onward_bytes']:
        raise ValueError('Compact outputs plus12MiB proposal/admission support exceeds cumulative allowance')
    write(folder/'resource-preflight.json',{**state,'additional_forecast_bytes':12*1024**2,
        'new_package_seconds':SELECTOR['new_seconds'],'historical_seconds':948.8160658078269,
        'preparation_seconds':preparation['seconds'],'copies_of_large_answers':0,
        'exclusions':'No duplicate answers or PDFs; measured command clock excludes agent authoring and read-only discovery.'},exclusive=True)
    proposal=deepcopy(program);proposal['revision']=210
    task=next(t for t in proposal['tasks'] if t['id']=='source-bes-dep-07')
    previous_dossier=task['dossier'];task['dossier']=PLAN
    task['inputs']=sorted(set(task['inputs'])|set(METHODS)|inputs|{previous_dossier,REVIEW+'/frozen.json',REVIEW+'/resource-preflight.json'})
    task['cash_flow_integration']=SELECTOR;task['timeout_seconds']=240
    task['reason']='Integrate the original bilingual individual cash-flow discrepancy into the real frozen consumer; preserve complete003 answer and later008 compositions, unknown dashes, Note46 and original acceptance.'
    proposal['budgets'][task['budget_key']]['maximum_new_attempts']=10
    proposal['build_contract']['criteria']['source-bes-dep-07']=[
        {'id':'individual-cash-flow','basis':'NAMED_CONDITIONAL_CHECK','validator':'bes-cash-flow.v1',
         'description':'Original bilingual individual cash-flow source binding, arithmetic and normal frozen-answer integration'},
        {'id':'remaining-source-coverage','basis':'ORIGINAL_TASK_ACCEPTANCE','validator':None,
         'description':'All original source07 requirements; finite cash-flow analysis cannot complete the task'}]
    attempts=[e['attempt'] for e in authority.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
    review={'baseline':digest(program),'changes':[
        'Repair reproduced mismatch between raw P1 and saved selected P2; reconstruct exact historical request using original reading-input; retain failed009',
        'Integrate supplied page170 cash flow through normal P3/consumer; preserve Note46 and entire predecessor answers',
        'Named conditional criterion separate from original source acceptance'],
        'skeptical_audit':{'verdict':'PASS_AFTER_CORRECTIONS','plan':PLAN,'findings':[
            'Correct baseline:individual170; consolidated74 agrees and is not the failing case',
            '182 focused tests pass including selected-parent request reconstruction and authority-serialized historical composition',
            'Actual failed009 stopped at P2 parent check; historical original-pair loader adds retained reading-input before sealing P1. Saved child hashes remain unchanged.',
            'Freeze checks all actual P1-P5 parent bindings before admission;18.714471699204296 failed-run seconds remain charged to original240second package ceiling',
            'Authority/program and historical composition use compact JSON hashes; normal service uses spaced JSON hashes. Keep explicit separate functions.',
            'English investing residual+40; incomplete net-change known-part residual-40 thousand EUR',
            'Actual003 baseline uses frozen v3 products and complete artifacts, not embedded changed products',
            'Real permissive-verifier control and typed zero/False rejection; no automatic discovery/current extraction claim',
            'Freeze original PDFs, images, source map, methods and all full-answer composition references',
            'Measured preparation and historical time retained; compact retention fits forecast and failure reserve',
            'Shared-code changes stale earlier conditional checks; final current-method revalidation remains pending']},
        'evidence_contract':{'question':'Can the normal frozen answer preserve and explain the original bilingual cash-flow discrepancy without unsupported correction?',
            'baseline':NORMAL+'/candidate-answer.json.gz','primary':'Whole normal-answer on/off preservation, separate source/arithmetic verification, original008 complete composition preservation',
            'promotion_veto':'Changed source/row/year/unit, missing evidence, unknown-to-zero, output alteration or unrelated answer change accepted',
            'continuation_veto':'Corrupt original source, changed frozen method,240second new/1320second cumulative clock or32MiB new/200MiB cumulative retention exceeded',
            'explanatory':['test counts','runtime','sizes','control totals'],
            'not_concluded':['official correction','controlling edition','accounting cause','automatic discovery','current re-extraction','original task or build completion'],
            'command':'.venv/bin/python -m scripts.prospectus_bes_cash_flow --attempt '+SOURCE+'/attempt-010',
            'artifacts':SOURCE+'/attempt-010'},'scope_unchanged':True,'budget_unchanged':False,
        'delivery_scope_changed':True,'delivery_authorization':proposal['build_contract']['authorization'],
        'original_obligations_preserved':True,
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':9,'new_maximum':10,
            'retained_attempts':attempts,'reason':'One changed repair of reproduced baseline-loader defect; previous failed009 remains sealed and charged;240seconds/200MiB ceilings unchanged',
            'next_discriminating_check':'Original real frozen consumer, separate source arithmetic and full-answer preservation',
            'stop_condition':'Invalid original source/frozen methods or finite cumulative resource limits; no unchanged retry',
            'same_scope_authorization':'User requests refresh master and continue general build without external advisor opinion; all original obligations remain'}}
    prefix=ROOT/REL/'proposals'
    write(prefix/'bes-cash-flow-210.json',proposal,exclusive=True)
    write(prefix/'bes-cash-flow-210-review.json',review,exclusive=True)
    print({'stage':'freeze','status':'PREPARED_NOT_ADMITTED','inputs':len(inputs),'methods':len(METHODS),
           'historical_bytes':state['historical_bytes'],'charged_bytes_before_proposal':state['combined_bytes']})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['fixture','tests','freeze']);args=p.parse_args()
    if args.stage=='freeze':
        freeze();return 0
    folder=ROOT/REVIEW;folder.mkdir(parents=True,exist_ok=True)
    ledger=folder/'preparation.json'
    predecessor=ROOT/REL/'reviews/bes-cash-flow-209/preparation.json'
    state=read(ledger) if ledger.exists() else read(predecessor)
    remaining=SELECTOR['preparation_seconds']-state['seconds']
    if remaining<=0: raise ValueError('Preparation allowance exhausted')
    start=time.monotonic();status='PASS';error=None;code=0
    try:
        if args.stage=='fixture':
            if (ROOT/FIXTURE).exists(): raise ValueError('Fixture already exists; preserve it')
            compressed(ROOT/FIXTURE,small_fixture(ROOT))
        else:
            i=len(state['stages']);log=folder/f'preparation-tests-{i:02d}.log';xml=folder/f'preparation-tests-{i:02d}.xml'
            with log.open('x') as stream:
                subprocess.run([sys.executable,'-m','pytest',*TESTS,'-q','--junitxml='+str(xml)],
                    cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'CUDA_VISIBLE_DEVICES':'-1',
                    'PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT,timeout=remaining,check=True)
    except Exception as exc:
        status='FAIL';error=type(exc).__name__+': '+str(exc);code=1
    elapsed=time.monotonic()-start;state['seconds']+=elapsed
    state['stages'].append({'stage':args.stage,'seconds':elapsed,'status':status,'error':error,
        'command':[sys.executable,'-m','scripts.prospectus_bes_cash_flow_prepare',args.stage]})
    write(ledger,state)
    print({'stage':args.stage,'status':status,'seconds':elapsed,'cumulative_preparation_seconds':state['seconds']})
    return code

if __name__=='__main__':raise SystemExit(main())
