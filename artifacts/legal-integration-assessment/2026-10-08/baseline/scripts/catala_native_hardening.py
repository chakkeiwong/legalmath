#!/usr/bin/env python3
"""Offline hardening of preserved live candidates; never a fresh model sample."""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.catala.native.contracts import validate_candidate
from legalmath.catala.native.runtime import build,evaluate,execute_values,implementation_hash,verify_build,verify_cases,verify_result
from legalmath.catala.native.boundary import prepare
from legalmath.errors import LegalMathError
from tests.catala.backend_support import ROOT,JDK,TOOLCHAIN
from tests.catala.native.reference import bounded_control


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(canonical(value))


def main():
    p=argparse.ArgumentParser();p.add_argument('--predecessor',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    before=Path(a.predecessor).resolve();out=Path(a.out).resolve()
    if out.exists(): raise RuntimeError('Choose a new evidence directory')
    out.mkdir(parents=True);began=time.monotonic()
    study=loads((before/'study.json').read_bytes())
    results=[];built=[]
    for name in study['task_order']:
        state=loads((before/'live'/name/'state.json').read_bytes())
        if state['status']!='READY_FOR_BEHAVIOR_CHECK': raise RuntimeError('Missing candidate')
        directory=before/'live'/name/state['build_directory']
        task,candidate,manifest=verify_build(directory,expected_hash=state['build_hash'])
        cases=loads((before/'references'/(name+'.cases.json')).read_bytes())
        if digest(task)!=study['tasks'][name]['task_hash'] or digest(cases)!=study['tasks'][name]['cases_hash']: raise RuntimeError('Predecessor changed')
        t,c,cs=bounded_control(task,candidate,cases)
        validate_candidate(t,c)
        target=out/'builds'/name; final=build(t,c,target,JDK,**TOOLCHAIN)
        if manifest['source_sha256']!=final['source_sha256']: raise RuntimeError('Hardening changed the generated computation')
        report=verify_cases(target,cs,JDK,compiler=TOOLCHAIN['compiler'])
        write(target/'cases.json',cs);write(target/'verification.json',report)
        migration={'record_type':'NativeInterfaceHardening','review_class':'ROOT_SOURCE_DOMAIN_AUDIT_NOT_FRESH_GENERATION',
                   'predecessor_build_hash':digest(manifest),'predecessor_candidate_hash':digest(candidate),
                   'predecessor_task_hash':digest(task),'task_hash':digest(t),'candidate_hash':digest(c),
                   'unchanged_program_sha256':final['source_sha256'],'bounds':t.get('bounds',[]),
                   'reason':'Enforce nonnegative admissibility explicitly stated in retained task text; native source and reading unchanged'}
        write(target/'interface-review.json',migration)
        results.append({'task':name,'cases':report['passed'],'build_hash':digest(final),'report_hash':report['report_hash'],'new_model_calls':0})
        built.append((t,c,cs,target))
        print('PASS',name,report['passed'],flush=True)
    mutations=[(0,'if holding.eligible then holding.amount else 0.0','holding.amount'),
               (1,'money of (','money of (100.0 * ('),
               (2,'date round down','date round up'),
               (3,'base * 2','base * 3'),
               (4,'age >= 18','age > 18'),
               (5,'licensed and suspended','licensed and not suspended')]
    witnesses=[]
    for index,old,new in mutations:
        t,c,cs,directory=built[index]; bad=deepcopy(c)
        if old not in bad['source']:
            # Models may choose different bound variable names or an equivalent
            # doubled expression. Mutate the exact observed program only.
            if index==0: old='if h.eligible then h.amount else 0.0';new='h.amount'
            if index==3 and '2 * base' in bad['source']: old='2 * base';new='3 * base'
        if old not in bad['source']: raise RuntimeError('Mutation does not match observed source: '+t['task_id'])
        bad['source']=bad['source'].replace(old,new)
        if index==1: bad['source']=bad['source'].replace('upperRate)','upperRate))')
        # Source excerpts must remain valid navigation after a deliberate mutation.
        for anchor in bad['anchors']: anchor['code_excerpt']='scope '+t['entry_scope']+':'
        target=out/'mutants'/t['task_id'];build(t,bad,target,JDK,**TOOLCHAIN)
        for case in cs:
            result=evaluate(target,case['snapshot'],JDK)
            if result['value']!=case['expected'].get('value') or result['status']!=case['expected']['status']:
                witness={'task':t['task_id'],'case':case,'observed':result,'mutation':{'old':old,'new':new},'detected':True}
                write(target/'witness.json',witness);witnesses.append(witness);break
        else: raise RuntimeError('Mutation has no independent distinguishing witness')
    t,c,cs,directory=built[0]
    snapshot=cs[1]['snapshot'];result=evaluate(directory,snapshot,JDK);faults=[]
    for key in ('trace','value','source_map','evidence'):
        altered=deepcopy(result);altered[key]=[] if key in ('trace','source_map') else {}
        altered['result_hash']=digest({k:v for k,v in altered.items() if k!='result_hash'})
        try: verify_result(directory,snapshot,altered,JDK)
        except LegalMathError as exc:
            faults.append({'field':key,'code':exc.code,'forged_result':altered,'rejected':True})
        else: raise RuntimeError('Forged execution evidence was accepted')
    write(out/'forged-evidence.json',{'snapshot':snapshot,'faults':faults})
    files=[*ROOT.glob('src/legalmath/catala/native/*.py'),*ROOT.glob('src/legalmath/catala/native/*.java'),
           ROOT/'tests/catala/native/reference.py',ROOT/'tests/catala/native/test_native.py',Path(__file__).resolve(),ROOT/'docs/plans/catala-direct-converter.md']
    hashes={}
    for path in files:
        name=path.relative_to(ROOT).as_posix();hashes[name]=raw_digest(path.read_bytes())
        target=out/'reviewed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    manifest={'record_type':'NativeHardeningResults','predecessor_study_hash':digest(study),'new_model_calls':0,
              'source_tasks':len(results),'cases':sum(r['cases'] for r in results),'results':results,
              'semantic_mutants_detected':len(witnesses),'forged_evidence_rejected':len(faults),
              'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'implementation_hash':implementation_hash(),'reviewed_inputs':hashes,
              'command':sys.argv,'environment':{'python':sys.executable,'jdk':str(JDK),'catala':str(TOOLCHAIN['compiler']),
                                             'gpu':'N/A; no GPU runtime','random_seeds':'N/A; deterministic offline checks'},
              'plan':'docs/plans/catala-direct-converter.md','result':'docs/implementation/catala/native-converter/results.md',
              'completed_at':datetime.now(timezone.utc).isoformat(),'wall_ms':int((time.monotonic()-began)*1000),
              'claim':'Engineering validation of retained candidates with explicit source-domain bounds; not fresh converter samples'}
    write(out/'results.json',manifest)
    print('COMPLETE',canonical({k:manifest[k] for k in ('source_tasks','cases','semantic_mutants_detected','forged_evidence_rejected','wall_ms')}).decode(),flush=True)

if __name__=='__main__':main()
