#!/usr/bin/env python3
"""Execute the reviewed continuation with bounded repairs and refreshed plans."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
OUT = ROOT/'artifacts/assurance-continuation/2026-09-29'
DOC = ROOT/'docs/implementation/assurance-continuation'
PLAN = ROOT/'docs/plans/assurance-continuation-execution.md'
PYTHON = ROOT/'.venv/bin/python'
PHASES = tuple('C'+str(i) for i in range(8))
MAX_ATTEMPTS = 3
TESTS = {
    'C1': ['tests/assurance/test_continuation_references.py', 'tests/assurance/test_successor_protocol.py'],
    'C2': ['tests/assurance/test_continuation_scheduling.py', 'tests/assurance/test_successor_resume.py', 'tests/assurance/test_successor_grants.py'],
    'C3': ['tests/assurance/test_continuation_coverage.py', 'tests/assurance/test_continuation_integration.py'],
    'C4': ['tests/translation/test_continuation_addition.py', 'tests/translation/test_continuation_schema_cost.py', 'tests/translation/test_qualification_proof.py'],
    'C5': ['tests/assurance/test_continuation_qualification.py', 'tests/assurance/test_continuation_master.py'],
}


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');temporary.replace(path)
def relative(path): return str(Path(path).resolve().relative_to(ROOT))


def inputs():
    paths = [PLAN, *ROOT.glob('scripts/*continuation*.py')]
    paths += list(ROOT.glob('scripts/assurance_successor*.py'))+[ROOT/'scripts/run_assurance_successor.py']
    paths += [p for prefix in ('src/legalmath', 'tests') for p in (ROOT/prefix).rglob('*')
              if p.is_file() and p.suffix in ('.py', '.java', '.lean', '.json') and
              not relative(p).startswith(('src/legalmath/prospectus/','tests/prospectus/'))]
    return {relative(p): sha(p) for p in sorted(set(paths))}


def regression_inputs():
    paths=[p for prefix in ('src/legalmath','tests','scripts','docs/monograph')
           for p in (ROOT/prefix).rglob('*') if p.is_file() and
           p.suffix in ('.py','.java','.lean','.json','.tex','.bib') and
           not relative(p).startswith('docs/monograph/review/')]
    return {relative(p):sha(p) for p in sorted(paths)}


def valid(receipt, *, current=True):
    manifest=read(ROOT/receipt['path'])
    if sha(ROOT/receipt['path'])!=receipt['sha256']:return False
    if manifest['status']!='PASSED':return False
    if current and manifest['inputs']!=inputs():return False
    if current and 'regression_inputs' in manifest and manifest['regression_inputs']!=regression_inputs():return False
    return all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in manifest['outputs'].items())


def retry_evidence(attempts):
    if not attempts:return {'kind':'INITIAL_EXECUTION'}
    prior=attempts[-1]
    # A successful, intact receipt can become stale when implementation changes.
    # Revalidate it, retaining both attempts; do not invent a failed command.
    if valid(prior,current=False):
        return {'kind':'SOURCE_REVALIDATION','prior_manifest':prior}
    repair=DOC/(read(ROOT/prior['path'])['phase']+'-repair-'+str(len(attempts))+'.json')
    r=read(repair)
    if (r.get('prior_manifest')!=prior or not r.get('change') or
            not r.get('focused_command') or not r.get('focused_result') or
            sha(ROOT/r['focused_result']['path'])!=r['focused_result']['sha256']):
        raise RuntimeError('Missing bound repair and executed focused reproducer')
    focused=read(ROOT/r['focused_result']['path'])
    if focused.get('exit_code')!=0:raise RuntimeError('Focused repair did not pass')
    return {'kind':'IMPLEMENTATION_REPAIR','prior_manifest':prior,'repair':relative(repair),'repair_sha256':sha(repair)}


def status():
    path=OUT/'state.json';state=read(path) if path.exists() else {'phases':{}}
    rows={}
    for phase in PHASES:
        attempts=state['phases'].get(phase,[])
        current = bool(attempts and valid(attempts[-1]))
        exhausted = not current and len(attempts) >= MAX_ATTEMPTS
        rows[phase]={'attempts':len(attempts),
            'attempts_remaining':max(0,MAX_ATTEMPTS-len(attempts)),
            'retry_allowed':not current and not exhausted,
            'status':'PASSED' if current else ('ATTEMPTS_EXHAUSTED' if exhausted else
                ('STALE_OR_FAILED' if attempts else 'PENDING'))}
    return {'phases':rows,'engineering_execution_complete':all(r['status']=='PASSED' for r in rows.values()),
            'overall_execution_complete':False,
            'historical_study_complete':False,'legal_correctness':'NOT_ESTABLISHED'}


def refresh(state):
    report=status();pending=[p for p in PHASES if report['phases'][p]['status']!='PASSED']
    previous=state['phases'].get(pending[0],[]) if pending else []
    exhausted=bool(pending and report['phases'][pending[0]]['status']=='ATTEMPTS_EXHAUSTED')
    revalidation=bool(previous and valid(previous[-1],current=False))
    result={'at':now(),'phase_status':report['phases'],'next_phase':pending[0] if pending else None,
        'repair_required':bool(previous and not revalidation and not exhausted),
        'source_revalidation_required':revalidation and not exhausted,
        'retry_exhausted':exhausted,
        'action':'Phase attempts exhausted. Preserve all receipts and use a separately reviewed successor; do not retry or reset this phase.'
            if exhausted else ('Inspect the exact failed command; repair and execute its focused reproducer before retry.'
            if previous and not revalidation else ('Revalidate the successful predecessor against current implementation; preserve its old receipt.'
            if revalidation else ('Execute the next reviewed phase.' if pending else 'Engineering phases executed; report remaining source and resource qualifications.'))),
        'original_ledger_and_issue_limits':'UNCHANGED','historical_S8_status':'FAILED',
        'engineering_execution_complete':report['engineering_execution_complete'],
        'overall_execution_complete':False,'legal_correctness':'NOT_ESTABLISHED'}
    save(OUT/'next-phase-plan.json',result)
    return result


def command(argv, work, label, *, timeout=3600):
    start=time.monotonic();log=work/(label+'.log')
    with log.open('w') as stream:
        try:
            result=subprocess.run(argv,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},
                stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
            code=result.returncode
        except subprocess.TimeoutExpired:code=124
    receipt={'argv':list(map(str,argv)),'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),
             'log':relative(log),'log_sha256':sha(log),'cpu_only':True}
    save(work/(label+'-command.json'),receipt)
    if code:raise RuntimeError('Command failed: '+str(receipt))
    return receipt


def phase(name):
    from assurance_continuation_checks import baseline, residuals, real_source_replay, live, documents
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(OUT/'state.json') if (OUT/'state.json').exists() else {'phases':{}}
        attempts=state['phases'].setdefault(name,[])
        if attempts and valid(attempts[-1]):return read(ROOT/attempts[-1]['path'])
        if len(attempts)>=MAX_ATTEMPTS:raise RuntimeError('Phase attempt limit reached; no automatic reset')
        retry=retry_evidence(attempts)
        for predecessor in PHASES[:PHASES.index(name)]:
            prev=state['phases'].get(predecessor,[])
            if not prev or not valid(prev[-1]):raise RuntimeError('Predecessor needs current verification: '+predecessor)
        work=OUT/name/('attempt-'+str(len(attempts)+1).zfill(2));work.mkdir(parents=True,exist_ok=False)
        before=inputs();start=time.monotonic()
        manifest={'phase':name,'attempt':len(attempts)+1,'started_at':now(),'status':'RUNNING','inputs':before,
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':str(PYTHON),'cpu_only':True,'random_seed':'N/A: deterministic checks; model route retained if dispatched',
            'plan':relative(PLAN),'commands':[],'retry_evidence':retry}
        save(work/'manifest.json',manifest)
        try:
            if name=='C0':manifest['result']=baseline(work)
            if name in TESTS:
                manifest['commands'].append(command([str(PYTHON),'-m','pytest','-q',*TESTS[name],
                    '--junitxml='+str(work/'tests.xml')],work,'tests',timeout=1200))
            if name=='C4':manifest['result']=real_source_replay(work)
            if name=='C5':manifest['result']=residuals(work)
            if name=='C6':manifest['result']=live(work)
            if name=='C7':
                regression_before=regression_inputs()
                manifest['result']=documents(work,command)
                manifest['commands'].append(command([str(PYTHON),'-m','pytest','-q',
                    '--junitxml='+str(work/'full-regression.xml')],work,'full-regression',timeout=3600))
                suites=ET.parse(work/'full-regression.xml').getroot()
                counts={k:sum(int(s.get(k,0)) for s in suites.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
                if not counts['tests'] or any(counts[k] for k in ('failures','errors','skipped')):raise RuntimeError(counts)
                if regression_inputs()!=regression_before:raise RuntimeError('Whole-tree regression inputs changed during verification')
                manifest['regression']=counts
                manifest['regression_inputs']=regression_before
            if inputs()!=before:raise RuntimeError('Material implementation changed during phase')
            manifest['status']='PASSED'
        except BaseException as exc:
            manifest.update(status='FAILED',error=type(exc).__name__,details=str(exc)[:6000])
        manifest['finished_at']=now();manifest['elapsed_seconds']=round(time.monotonic()-start,3)
        manifest['outputs']={relative(p):sha(p) for p in sorted(work.rglob('*')) if p.is_file() and p.name!='manifest.json'}
        save(work/'manifest.json',manifest)
        attempts.append({'path':relative(work/'manifest.json'),'sha256':sha(work/'manifest.json')})
        save(OUT/'state.json',state);refresh(state)
        print(json.dumps({'phase':name,'status':manifest['status'],'manifest':relative(work/'manifest.json') }),flush=True)
        if manifest['status']!='PASSED':raise RuntimeError(manifest.get('details','Phase failed'))
        return manifest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','status','phase']);parser.add_argument('phase',nargs='?',choices=PHASES)
    args=parser.parse_args()
    if args.action=='status':print(json.dumps(status(),indent=2));return
    if args.action=='phase':
        if args.phase is None:parser.error('phase is required')
        phase(args.phase)
    else:
        for p in PHASES:phase(p)


if __name__=='__main__':main()
