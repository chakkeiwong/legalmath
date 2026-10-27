"""Freeze reviewed deployment inputs and build exact continuation checkpoints."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import sys
ROOT=Path('/home/chakwong/python/legalmath')
CANDIDATE=Path('/tmp/legalmath-p14-repair-20261023')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(CANDIDATE/'src'),str(CANDIDATE)]
from scripts import legal_review_deployment as deployment
from scripts.legal_mission_execution import read,save,ref,require,digest,verify
from legalmath.interpretation.assurance.phased.review_checkpoint import PROFILE
deployment.ROOT=ROOT
HERE,WORK=deployment.HERE,deployment.WORK

def prepare():
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=CANDIDATE,text=True).splitlines()
    added=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=CANDIDATE,text=True).splitlines()
    implementation=sorted(p for p in changed+added if p.startswith(('scripts/','src/','tests/')))
    save(ROOT/HERE/'implementation-files.json',implementation)
    if not (ROOT/HERE/'baseline.json').exists():
        deployment.freeze()
    # Additive archive for the two defects found after the original freeze.
    # The original frozen baseline remains byte-for-byte intact.
    archived={r['previous']['path'] for r in read(ROOT/HERE/'baseline.json')['archived']}
    extra=HERE/'additional-before.json'
    value=read(ROOT/extra) if (ROOT/extra).exists() else dict(archived=[],
        reason='Additive archive for reviewed context-need, scope and admission repairs; no baseline rewrite.')
    rows=value['archived']
    for row in rows: verify(ROOT,row['archive'])
    archived.update(r['previous']['path'] for r in rows)
    for relative in implementation:
        if relative in archived or not (ROOT/relative).exists(): continue
        target=HERE/'additional-before'/relative
        (ROOT/target).parent.mkdir(parents=True,exist_ok=True)
        with (ROOT/target).open('xb') as stream: stream.write((ROOT/relative).read_bytes())
        rows.append(dict(previous=ref(ROOT,relative),archive=ref(ROOT,target)))
    save(ROOT/extra,value)
    prior=read(ROOT/deployment.PROGRAM)
    repair=prior['review_repair']
    budget=deepcopy(read(ROOT/repair['budget']['path']))
    budget['protected_calls']['service']+=200
    budget['shared_pool']-=200
    budget['service_replacements_remaining']+=200
    budget['amendment']=ref(ROOT,HERE/'authority.json')
    save(ROOT/HERE/'budget.json',budget)
    arm_checkpoints=deepcopy(repair['arm_checkpoints'])
    count=0
    for question,source in [('p14',WORK/'recovered-live/arms/p14/baseline'),
                            ('gatecoin',WORK/'continued-live/arms/gatecoin/baseline')]:
        checkpoint=deepcopy(read(ROOT/arm_checkpoints[question]['baseline']['path']))
        journal=source/'calls/dispatch.json'
        if not (ROOT/journal).exists(): continue
        saved=read(ROOT/journal)
        require(not any(r['status']=='RESERVED' for r in saved['calls'].values()), 'Uncertain dispatch')
        all_calls={}
        for key,row in saved['calls'].items():
            folder=source/'calls'/key
            pointers={n:ref(ROOT,folder/(n+'.json')) for n in ('request','schema','result')}
            pointers['dispatch']=ref(ROOT,journal)
            for name,file in [('raw','raw.json'),('reference_binding','reference-binding.json')]:
                if (ROOT/folder/file).exists(): pointers[name]=ref(ROOT,folder/file)
            result=read(ROOT/pointers['result']['path'])
            require(digest(result)==row['result_hash'] and result['status']==row['status'], 'Changed settled result')
            all_calls[key]=pointers
            task=read(ROOT/pointers['request']['path'])['task']
            if result['status']=='VALIDATED' and task!='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
                checkpoint['calls'][key]={**pointers,'mode':'VALIDATED'}
        if question=='p14':
            population=source/'contextual-group-review-p14.json'
            reviews=read(ROOT/population)
            failed=[];repairs={};requests={}
            for review in reviews['reviews']:
                if review['status']=='VALIDATED':
                    evidence=review.get('group_evidence') or review['repair_evidence']
                    key=evidence['key']
                else:
                    identity,=review['assigned_ids']
                    key='repair-review-p14-'+digest(identity)[:24]
                    failed.append(identity)
                    repairs[identity]=dict(key=key)
                pointers=all_calls.get(key) or checkpoint['review_groups'][key]
                requests[key]=pointers
            first=read(ROOT/next(iter(requests.values()))['request']['path'])
            continuation=dict(profile=PROFILE,question_id=question,input_hash=checkpoint['input_hash'],
                answer_hash=digest(first['payload']['answer']),population=ref(ROOT,population),
                source_store=ref(ROOT,source/'source-store.json'),review=ref(ROOT,deployment.REVIEW),
                calls=requests,repairs=repairs,failed_ids=failed,
                mapping_needs=ref(ROOT,Path('artifacts/legal-mission-control/2026-10-23/p14-decisions/mapping-only-needs.json')),
                retained_source_needs=ref(ROOT,Path('artifacts/legal-mission-control/2026-10-23/p14-decisions/retained-source-needs.json')),
                validated_count=sum(r['status']=='VALIDATED' for r in reviews['reviews']))
            require(len(failed)==52 and continuation['validated_count']==1699,'Wrong review population')
            save(ROOT/HERE/'individual-reviews.json',continuation)
            checkpoint['individual_reviews']=ref(ROOT,HERE/'individual-reviews.json')
        target=HERE/'checkpoints'/question/'baseline.json'
        save(ROOT/target,checkpoint)
        arm_checkpoints[question]['baseline']=ref(ROOT,target)
        count+=len(checkpoint['calls'])
    save(ROOT/HERE/'checkpoints.json',dict(arm_checkpoints=arm_checkpoints,provider_calls=0,
        original_results_unchanged=True,validated_calls=count,validated_individual_reviews=1699,
        failed_individual_continuations=52))
    print(json.dumps(dict(prepared=True,files=len(implementation),calls=4027,
        replacements_before=88,replacements_after=288,validated_calls=count),indent=2))

if __name__=='__main__': prepare()
