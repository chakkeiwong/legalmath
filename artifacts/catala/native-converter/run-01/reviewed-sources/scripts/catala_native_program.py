#!/usr/bin/env python3
"""Frozen development pilot; model requests never contain reference candidates/cases."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.catala.native.converter import convert, generation_request, criticism_request
from legalmath.catala.native.runtime import build, implementation_hash, verify_cases
from legalmath.interpretation.search.providers import Allowance, CodexProvider, verify_allowance_checkpoint
from legalmath.errors import LegalMathError
from tests.catala.backend_support import TOOLCHAIN,JDK
from tests.catala.native.reference import controls, retained_control

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/plans/catala-direct-converter.md'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp'); tmp.write_bytes(canonical(value)); tmp.replace(path)


def fingerprint():
    paths=[PLAN,Path(__file__),ROOT/'tests/catala/native/reference.py',ROOT/'examples/catala/native/control_sources.json',ROOT/'src/legalmath/interpretation/search/providers.py',TOOLCHAIN['lock']]
    return {'implementation_hash':implementation_hash(),'files':{str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in paths}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    parser.add_argument('--phase',choices=('controls','live','report'),required=True)
    parser.add_argument('--allowance')
    args=parser.parse_args(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    began=time.monotonic()
    if args.phase=='controls':
        if (out/'study.json').exists(): raise RuntimeError('Study already frozen; choose a new run')
        corpus=controls()+[retained_control()]
        taskhashes={}
        for task,candidate,cases in corpus:
            name=task['task_id']; directory=out/'controls'/name
            write(out/'tasks'/f'{name}.json',task)
            write(out/'references'/f'{name}.cases.json',cases)
            write(out/'references'/f'{name}.control.json',candidate)
            print('CONTROL',name,flush=True)
            manifest=build(task,candidate,directory,JDK,**TOOLCHAIN)
            report=verify_cases(directory,cases,JDK,compiler=TOOLCHAIN['compiler'])
            write(directory/'verification.json',report)
            taskhashes[name]={'task_hash':digest(task),'cases_hash':digest(cases),'control_hash':digest(candidate),'control_build_hash':digest(manifest)}
            print('PASS',len(cases),flush=True)
        # Retain the actual source edition, not just a quote with a hash.
        for name in ('23EC35-annex1.txt','23EC35-annex1.pdf'):
            target=out/'retained-source'/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'.localresources/sfc'/name,target)
        ledger=Path(args.allowance).resolve()
        allowance=loads(ledger.read_bytes()); before=len(allowance['calls'])
        provider=CodexProvider(allowance=Allowance(ledger,allowance['maximum'],reservation_ceiling=min(before+24,allowance['maximum'])))
        study={'record_type':'NativeDevelopmentStudy','frozen_at':datetime.now(timezone.utc).isoformat(),
               'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'working_tree_fingerprint':fingerprint(),'tasks':taskhashes,'task_order':list(taskhashes),
               'split':'DEVELOPMENT_ONLY_NO_HELDOUT_CLAIM','samples_per_task':1,'arms':['reviewed_direct_native'],
               'baseline':'independently specified exact reference; handwritten native runtime control',
               'primary':'all required exact behaviors and provisional source checks; retain uncertainty',
               'vetoes':['wrong behavior','unresolved source','corrupt commitments','incomplete evidence'],
               'nonclaims':['superiority','population accuracy','generalization','human review benefit','legal correctness','production readiness'],
               'environment':{'python':sys.executable,'jdk':str(JDK),'catala':str(TOOLCHAIN['compiler']),'gpu':'N/A; no GPU runtime','seeds':'N/A; fresh unseeded model contexts; deterministic reference cases'},
               'provider_routing':provider.routing,'maximum_new_calls':24,'maximum_revisions_per_task':1,
               'allowance_path':str(ledger),'allowance_before':before,'allowance_ceiling':min(before+24,allowance['maximum']),
               'allowance_checkpoint_hash':digest(allowance),'plan':str(PLAN.relative_to(ROOT)),
               'control_wall_ms':int((time.monotonic()-began)*1000),
               'command':sys.argv,'results_path':'results.json'}
        write(out/'allowance-before.json',allowance)
        write(out/'study.json',study)
        print('FROZEN',digest(study),flush=True)
        return
    study=loads((out/'study.json').read_bytes())
    if study['working_tree_fingerprint']!=fingerprint(): raise RuntimeError('Frozen implementation changed')
    for name, hashes in study['tasks'].items():
        for folder,suffix,key in [('tasks','.json','task_hash'),('references','.cases.json','cases_hash'),('references','.control.json','control_hash')]:
            if digest(loads((out/folder/(name+suffix)).read_bytes()))!=hashes[key]: raise RuntimeError('Frozen corpus changed')
    if args.phase=='live':
        ledger=Path(study['allowance_path']); verify_allowance_checkpoint(ledger,study['allowance_checkpoint_hash'])
        allowance=loads(ledger.read_bytes())
        provider=CodexProvider(allowance=Allowance(ledger,allowance['maximum'],reservation_ceiling=study['allowance_ceiling']))
        if provider.routing!=study['provider_routing']: raise RuntimeError('Frozen provider changed')
        for name in study['task_order']:
            task=loads((out/'tasks'/(name+'.json')).read_bytes())
            destination=out/'live'/name
            print('GENERATE',name,flush=True)
            state=convert(task,destination,provider,JDK,**TOOLCHAIN,resume=(destination/'state.json').exists())
            print('STATUS',name,state['status'],flush=True)
        write(out/'allowance-after.json',loads(ledger.read_bytes()))
        write(out/'live-manifest.json',{'command':sys.argv,'study_hash':digest(study),'wall_ms':int((time.monotonic()-began)*1000)})
    results=[]
    for name in study['task_order']:
        destination=out/'live'/name
        if not (destination/'state.json').exists():
            results.append({'task':name,'outcome':'NOT_RUN'}); continue
        state=loads((destination/'state.json').read_bytes())
        row={'task':name,'source_status':state['status'],'calls':len(state['calls']),'outcome':state['status']}
        if state['status']=='READY_FOR_BEHAVIOR_CHECK':
            cases=loads((out/'references'/(name+'.cases.json')).read_bytes())
            try:
                report=verify_cases(destination/state['build_directory'],cases,JDK,compiler=TOOLCHAIN['compiler'])
                write(destination/'verification.json',report)
                row.update(outcome='PASSED_DEVELOPMENT_SCREEN',cases=report['passed'])
            except LegalMathError as error:
                row.update(outcome='WRONG_BEHAVIOR_OR_RUNTIME_FAILURE',failure={'code':error.code,'details':error.details})
        if state.get('failure'): row['failure']=state['failure']
        results.append(row)
    result={'record_type':'NativeDevelopmentResults','study_hash':digest(study),'tasks':results,
            'strict_successes':sum(r['outcome']=='PASSED_DEVELOPMENT_SCREEN' for r in results),
            'denominator':len(results),'ranking':'NOT_ESTIMATED; one development sample per task, no paired comparator',
            'source_fidelity':'Provisional same-provider model criticism; human legal adjudication pending',
            'command':sys.argv,'wall_ms':int((time.monotonic()-began)*1000)}
    write(out/'results.json',result)
    print(canonical(result).decode(),flush=True)

if __name__=='__main__': main()
