#!/usr/bin/env python3
"""Bounded execution/checkpoint wrapper for the prospectus gap-closure plan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['PYTHONPATH']=str(ROOT/'src')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path.insert(0,str(ROOT/'src'))
from legalmath.prospectus.common import ROOT as IMPORT_ROOT
assert ROOT==IMPORT_ROOT
OUT=ROOT/'docs/implementation/prospectus-gap-closure'
PLAN='docs/plans/prospectus-gap-closure.md'


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def versions():
    paths=list((ROOT/'src/legalmath').rglob('*.py'))+list((ROOT/'tests/prospectus').glob('*.py'))
    paths += list((ROOT/'scripts').glob('*prospectus_gap*.py'))+[ROOT/'scripts/run_bond_loss_absorption_classification.py']
    paths += list((ROOT/'tests/compliance').glob('*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def execute(stage, inventory=None):
    OUT.mkdir(exist_ok=True)
    if stage=='baseline':
        target=OUT/'baseline';target.mkdir(exist_ok=False)
        for name in ['results.md','results.json','results.csv','results.pdf']:
            shutil.copyfile(ROOT/'docs/implementation/bond-loss-absorption-classification'/name,target/name)
        for name in ['loss_absorption_reader.py','loss_absorption_witnesses.py','loss_absorption_derivation.py']:
            shutil.copyfile(ROOT/'src/legalmath/prospectus'/name,target/name)
        combined={'documents':{},'issues':[],'scope':'The original 30 exposed development cases; no human answer labels. Source and legal completeness remain qualified.'}
        for group in ['classification-reader-v2-repair','classification-two-case-fresh']:
            data=json.loads((ROOT/'docs/prospectus'/group/'issue-inventory.json').read_text())
            for issue in data['issues']:issue['data_role']='exposed-development'
            combined['issues'].extend(data['issues']);combined['documents'].update(data['documents'])
        folder=ROOT/'docs/prospectus/gap-closure';folder.mkdir(exist_ok=True)
        write(folder/'development-inventory.json',combined)
        write(target/'manifest.json',{'recorded_at':stamp(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{p.name:sha(p) for p in target.iterdir() if p.is_file()},'environment':sys.executable,'root':str(ROOT),'source_versions':versions(),'plan':PLAN})
    folder=OUT/stage;folder.mkdir(exist_ok=True)
    attempt=folder/('attempt-'+str(len(list(folder.glob('attempt-*')))+1).zfill(3));attempt.mkdir()
    command=[sys.executable,'-m','pytest','tests/prospectus/test_gap_closure.py','-q','--junitxml='+str(attempt/'tests.xml')]
    if stage=='focused':
        command=[sys.executable,'-m','pytest','tests/prospectus/test_gap_closure.py','tests/prospectus/test_feature_investigation.py','tests/prospectus/test_loss_absorption.py','tests/prospectus/test_loss_absorption_repair.py','tests/prospectus/test_loss_absorption_two_case.py','-q','--junitxml='+str(attempt/'tests.xml')]
    elif stage=='regression':
        command=[sys.executable,'-m','pytest','tests/prospectus','tests/compliance','-q','--junitxml='+str(attempt/'tests.xml')]
    elif stage in ('corpus','fresh'):
        selected=inventory or 'docs/prospectus/gap-closure/development-inventory.json'
        command=[sys.executable,'scripts/run_bond_loss_absorption_classification.py','--inventory',selected,'--output',str(attempt/'run'),'--checks','--plan',PLAN]
    elif stage=='delivery':
        command=[sys.executable,'-c',"import sys;sys.path.insert(0,'scripts');from prospectus_gap_report import build;from pathlib import Path;build(Path(sys.argv[1]))",str(attempt)]
    elif stage in ('preview','integration'):
        command=[sys.executable,'scripts/prospectus_gap_actions.py',stage,'--inventory',inventory or 'docs/prospectus/gap-closure/development-inventory.json','--output',str(attempt)]
    elif stage not in ('baseline','focused','regression'):
        raise ValueError('Unknown bounded action')
    started=time.monotonic();before=versions()
    manifest={'stage':stage,'status':'RUNNING','started_at':stamp(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'command':command,'environment':sys.executable,'python':sys.version,'platform':platform.platform(),'cpu_gpu':'CPU only; CUDA_VISIBLE_DEVICES=-1; no GPU framework imported','seeds':'N/A deterministic','plan':PLAN,'source_hashes':before,'result':str(attempt.relative_to(ROOT)),'data_version':sha(ROOT/(inventory or 'docs/prospectus/gap-closure/development-inventory.json'))}
    write(attempt/'run-manifest.json',manifest)
    try:
        with (attempt/'command.log').open('w') as stream:
            p=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
        manifest.update(exit_code=p.returncode,status='COUNTEREXAMPLES_RECORDED' if stage=='baseline' and p.returncode==1 else 'PASS' if p.returncode==0 else 'FAILED')
        if versions()!=before:raise ValueError('Method changed during execution')
        if p.returncode and not(stage=='baseline' and p.returncode==1):raise RuntimeError('Phase failed; inspect preserved log')
        return manifest
    except BaseException as exc:
        manifest.update(status='FAILED',error=repr(exc));raise
    finally:
        manifest.update(finished_at=stamp(),wall_seconds=time.monotonic()-started)
        manifest['artifacts']={str(p.relative_to(attempt)):sha(p) for p in attempt.rglob('*') if p.is_file() and p.name!='run-manifest.json'}
        write(attempt/'run-manifest.json',manifest)
        print(json.dumps({k:manifest[k] for k in ['stage','status','result','wall_seconds']},indent=2))
        (OUT/'next-phase.md').write_text('# Execution checkpoint\n\nLast phase: '+stage+'; status '+manifest['status']+'. See '+str(attempt.relative_to(OUT))+'/run-manifest.json. Follow the reviewed plan; retain failures and repair causes before new attempts.\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['baseline','focused','regression','corpus','fresh','preview','integration','acquire','freeze','register','delivery'])
    parser.add_argument('--inventory')
    parser.add_argument('--url')
    parser.add_argument('--key')
    parser.add_argument('--purpose')
    args=parser.parse_args()
    if args.stage=='acquire':
        from prospectus_gap_actions import acquire
        acquire(args.key,args.url,args.purpose)
    elif args.stage=='register':
        from prospectus_gap_sources import register
        register(args.inventory)
    elif args.stage=='freeze':
        import zipfile
        folder=OUT/'freezes';folder.mkdir(exist_ok=True)
        target=folder/('candidate-'+str(len(list(folder.glob('candidate-*')))+1).zfill(3));target.mkdir()
        files=versions()
        files[PLAN]=sha(ROOT/PLAN)
        write(target/'freeze.json',{'at':stamp(),'files':files,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'fresh_family_order':{'capital':['Rabobank','KBC','Nationwide','Intesa Sanpaolo'],'corporate':['National Grid','Nestle','Mercedes-Benz','BMW']},'protocol':PLAN,'new_family_acquisitions_before_freeze':[str(p.relative_to(ROOT)) for p in (ROOT/'docs/prospectus/gap-closure/acquisitions').glob('*/receipt.json') if json.loads(p.read_text()).get('purpose','').startswith('fresh')]})
        with zipfile.ZipFile(target/'method.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in files:z.write(ROOT/name,name)
        print(target)
    else:execute(args.stage,args.inventory)
