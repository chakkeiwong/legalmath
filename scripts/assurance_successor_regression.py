"""Full current-source regression; reusable only with exact retained identities."""
import os
import platform
import subprocess
import time
import xml.etree.ElementTree as ET
from run_assurance_successor import ROOT,OUT,read,save,sha,rel,now


def material_hashes():
    return {rel(p):sha(p) for base in ('src','tests','scripts') for p in sorted((ROOT/base).rglob('*'))
        if p.is_file() and p.suffix in ('.py','.java','.lean','.json') and '__pycache__' not in p.parts}


def counts(path):
    tree=ET.parse(path).getroot();suites=[tree] if tree.tag=='testsuite' else list(tree)
    return {k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}


def current_receipt():
    path=OUT/'regression-preflight/result.json'
    if not path.exists():return None
    value=read(path)
    if value.get('status')!='FULL_CURRENT_REGRESSION_PASSED' or value['material_inputs']!=material_hashes():return None
    for ref in value['files'].values():
        if not (ROOT/ref['path']).is_file() or sha(ROOT/ref['path'])!=ref['sha256']:return None
    actual=counts(ROOT/value['files']['xml']['path'])
    if actual!=value['counts'] or actual['tests']<1029 or any(actual[k] for k in ('failures','errors','skipped')):return None
    return {'path':rel(path),'sha256':sha(path),'counts':actual,'result':value}


def run():
    from assurance_successor_phases import command
    directory=OUT/'regression-preflight';directory.mkdir(exist_ok=True)
    work=directory/f'attempt-{len(list(directory.glob("attempt-*")))+1:02}'
    work.mkdir(exist_ok=False);before=material_hashes();begun=time.monotonic()
    record={'started_at':now(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':{'python':platform.python_version(),'cpu':'CPU-only; CUDA_VISIBLE_DEVICES=-1','seed':'N/A deterministic regression'},
        'material_inputs':before,'plan':'docs/plans/assurance-successor-regression-preflight.md',
        'new_model_calls':0,'status':'RUNNING'}
    save(work/'start.json',record)
    try:
        command([ROOT/'.venv/bin/python','-m','pytest','tests','-q','-o','faulthandler_timeout=0',
            '--junitxml='+str(work/'full-regression.xml')],work,'full-regression',timeout=3600)
        value=counts(work/'full-regression.xml')
        if value['tests']<1029 or any(value[k] for k in ('failures','errors','skipped')):raise RuntimeError('Not a full no-skip pass')
        if before!=material_hashes():raise RuntimeError('Material implementation changed during regression')
        record.update(status='FULL_CURRENT_REGRESSION_PASSED',counts=value)
    except BaseException as exc:
        record.update(status='FAILED',error=str(exc));raise
    finally:
        record.update(finished_at=now(),wall_seconds=round(time.monotonic()-begun,3),
            files={k:{'path':rel(p),'sha256':sha(p)} for k,p in
                [('xml',work/'full-regression.xml'),('log',work/'full-regression.log'),('command',work/'full-regression.command.json')]
                if p.exists()})
        save(work/'result.json',record);save(directory/'result.json',record)
    return {k:record[k] for k in ('status','counts','wall_seconds','new_model_calls')}
