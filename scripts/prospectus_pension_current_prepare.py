"""Prepare current pension evidence with the exact previously reviewed plan append."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True;os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from scripts import prospectus_component_revalidation as c

def main():
    start=time.monotonic();auth=Authority(ROOT);old,tasks,_=auth.spec();revision=old['revision']+1
    kind='pension';task=tasks['basf-references'];review_name=REL+'/reviews/pension-current-'+str(revision)
    folder=ROOT/review_name;folder.mkdir(parents=True,exist_ok=False)
    donor_name=REL+'/attempts/source-bes-dep-06/attempt-012';donor=ROOT/donor_name
    original=c.baseline(ROOT,kind);plan='docs/plans/prospectus-post-validation-installed-2026-10-17.md'
    previous=REL+'/reviews/component-217-r2'
    try:
        proof=read(ROOT/previous/'append-proof.json');raw=(ROOT/proof['path']).read_bytes()
        require=c.require
        require(file_hash(ROOT/proof['path'])==proof['current_hash'] and
            hashlib.sha256(raw[:proof['original_bytes']]).hexdigest()==proof['original_hash'] and
            len(raw)-proof['original_bytes']==proof['appended_bytes'],'Original reviewed append differs')
        original_admission=read(original/'admission.json')
        require(original_admission['binding'][proof['path']]==proof['original_hash'],'Pension original plan binding differs')
        deltas={n:{'old':h,'current':file_hash(ROOT/n)} for n,h in original_admission['binding'].items() if file_hash(ROOT/n)!=h}
        require(all(n==proof['path'] or n=='pyproject.toml' or n.startswith(('src/','scripts/','tests/')) for n in deltas),'Unexpected original non-code change')
        historical=c.historic(kind);write(folder/'history.json',historical,exclusive=True)
        write(folder/'append-proof.json',proof,exclusive=True)
        require(read(donor/'source-package.json')==c.package_files(ROOT/'src/legalmath')==c.package_files(donor/'installed/legalmath'),'Shared wheel differs')
        event=next(e for e in reversed(auth.events()) if e.get('attempt')==donor_name and e['kind'] in {'RECORD','ACCEPT'})
        require(auth.retained_evidence_valid(event),'Shared installed donor changed')
        h=c.helper(ROOT,kind);tests=sorted(set(h.TESTS)|{c.TEST})
        argv=[sys.executable,'-m','pytest',*tests,'-q','--junitxml='+str(folder/'tests.xml')]
        with (folder/'tests.log').open('x') as log:
            subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'},
                stdout=log,stderr=subprocess.STDOUT,timeout=max(1,90-(time.monotonic()-start)),check=True)
        count=c.checked_tests(folder/'tests.xml',1)
        mf=c.methods();inputs=set(task['inputs'])-set(mf)
        inputs|={str((original/n).relative_to(ROOT)) for n in read(original/'outputs.json')}
        inputs|={str((original/'outputs.json').relative_to(ROOT)),c.RUNTIME_ATTEMPT+'/workspace.json',plan,str(Path(__file__).relative_to(ROOT))}
        inputs|={previous+'/'+n for n in ('append-proof.json','REVIEW.md','preparation.json')}
        inputs|={donor_name+'/'+n for n in read(donor/'outputs.json')}|{donor_name+'/outputs.json'}
        write(folder/'preparation.json',{'seconds':time.monotonic()-start,'tests':count,'status':'PASS',
            'command':[sys.executable,str(Path(__file__).relative_to(ROOT))],'test_command':argv,
            'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
            'historical_unrecorded_seconds':'UNKNOWN; prior failed217 preparation retained with its charged3.5985871427692473seconds'},exclusive=True)
        inputs|={str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()}
        frozen={'methods':mf,'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},
            'runtime_files':c.runtime_files(),'history':historical,'package':c.package_files(ROOT/'src/legalmath')}
        write(folder/'frozen.json',frozen,exclusive=True)
        admissions=[e['attempt'] for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
        before=old['budgets'][task['budget_key']]['maximum_new_attempts'];require(len(admissions)==before,'Allowance not exhausted')
        new=deepcopy(old);new['revision']=revision;t=next(t for t in new['tasks'] if t['id']==task['id'])
        t.update(dossier=c.PLAN,reason='Revalidate complete installed pension009 on the current shared wheel; preserve the exact reviewed plan append and all original evidence',
            current_component_validation={'version':'current-installed-component.v1','kind':kind,'review':review_name,
                'baseline':str(original.relative_to(ROOT)),'wheel_attempt':donor_name,'bounds':c.BOUNDS},timeout_seconds=210)
        t['inputs']=sorted(set(t['inputs'])|set(mf)|inputs|{review_name+'/frozen.json',review_name+'/preflight.json'})
        new['budgets'][task['budget_key']]['maximum_new_attempts']=before+1
        attempt=REL+'/attempts/'+task['id']+'/attempt-'+f'{before+1:03d}'
        write(folder/'preflight.json',{'revision':revision,'expected_attempt':attempt,'changed_original_methods':deltas,
            'exact_append_review':review_name+'/append-proof.json','prior_task_attempt_bytes':sum(p.stat().st_size for p in original.parent.rglob('*') if p.is_file()),
            'new_ceiling':c.BOUNDS['new_bytes'],'reserve':c.BOUNDS['reserve_bytes'],'forecast_new_bytes':40*1024**2},exclusive=True)
        audit={'baseline':digest(old),'changes':['Current installed pension after five shared validation repairs','Preserve exact original plan prefix and all historical failures'],
            'skeptical_audit':{'verdict':'PASS','plan':plan,'original_plan':c.PLAN,'append_proof':review_name+'/append-proof.json'},
            'evidence_contract':{'question':'Does the current shared wheel preserve complete pension outputs and controls?',
                'baseline':historical,'primary':'Complete current/installed equality, integer oracle and all original refusals',
                'veto':'Changed sources,wrong imports,missing refusal,resource ceiling','explanatory':['runtime','tests'],
                'not_concluded':['source authenticity','actual rounding','full source coverage','whole build']},
            'scope_unchanged':True,'budget_unchanged':False,'budget_revision':{'budget_key':task['budget_key'],
                'previous_maximum':before,'new_maximum':before+1,'retained_attempts':admissions,
                'reason':'Shared production changes make historical installed proof stale',
                'next_discriminating_check':'Full pension009 installed answer and all22 original controls',
                'stop_condition':c.BOUNDS,'same_scope_authorization':'User-directed general build and continued local verification'}}
        write(ROOT/REL/'proposals'/('component-'+str(revision)+'.json'),new,exclusive=True)
        write(ROOT/REL/'proposals'/('component-'+str(revision)+'-review.json'),audit,exclusive=True)
        require(time.monotonic()-start<90,'Cumulative preparation ceiling');c.usage(t,ROOT/attempt)
        print(json.dumps({'revision':revision,'attempt':attempt,'tests':count,'seconds':time.monotonic()-start}))
    except Exception as exc:
        write(folder/'failure.json',{'error':type(exc).__name__+': '+str(exc),'seconds':time.monotonic()-start},exclusive=True)
        raise

if __name__=='__main__':main()
