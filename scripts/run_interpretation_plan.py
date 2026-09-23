"""Fixed-command, hash-bound phase execution with durable repair and refresh records."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/interpretation/round1'
PLAN = ROOT / 'docs/implementation/interpretation-round1/master-plan.json'
BASE = ROOT / '.localresources/interpretation-round1/baseline'
PYTHON = ROOT / '.venv/bin/python'
PHASES = ('P0', 'P1', 'P2', 'P3', 'P4')
COMMAND_TIMEOUT_SECONDS = 600
PREDECESSORS = None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def now():
    return datetime.now(timezone.utc).isoformat()


def inputs():
    paths = []
    for directory in ['src', 'tests', 'scripts', 'docs/monograph/contracts']:
        paths += [p for p in (ROOT/directory).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and '.egg-info' not in str(p)]
    paths += [PLAN, PLAN.with_suffix('.md'), ROOT/'pyproject.toml', ROOT/'requirements-dev.lock']
    files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}
    return {'files': files, 'digest': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def protect():
    baseline = read(BASE/'manifest.json')
    errors = []
    for name, rec in baseline['files'].items():
        if sha(BASE/name) != rec['sha256']:
            errors.append('Frozen baseline changed: '+name)
    for name, expected in baseline['protected_in_place'].items():
        if not (ROOT/name).is_file() or sha(ROOT/name) != expected:
            errors.append('Retained evidence changed: '+name)
    if errors:
        raise ValueError('\n'.join(errors))
    return {'frozen_files': len(baseline['files']), 'protected_evidence_files':len(baseline['protected_in_place'])}


def state():
    return read(OUT/'state.json', {'version':1, 'phases':{p:{'status':'PLANNED','attempts':[]} for p in PHASES}})


def commands(phase, attempt):
    py = str(PYTHON)
    junit = str(attempt/'tests.xml')
    checks = {
        'P0': [('baseline', [py,'-m','pytest','tests/unit','tests/conformance','tests/integration','tests/security','-q','--junitxml='+junit]),
               ('contracts',[py,'scripts/check_interpretation_contracts.py'])],
        'P1': [('models',[py,'-m','pytest','tests/interpretation/test_contracts.py','tests/interpretation/test_inventory.py','tests/interpretation/test_candidates.py','tests/interpretation/test_issues.py','tests/interpretation/test_master.py','-q','--junitxml='+junit])],
        'P2': [('controller',[py,'-m','pytest','tests/interpretation','-q','--junitxml='+junit])],
        'P3': [('api-contracts',[py,'scripts/export_openapi.py']),
               ('integration',[py,'-m','pytest','tests/interpretation','tests/integration/test_api.py','tests/integration/test_release.py','tests/integration/test_review.py','tests/integration/test_storage.py','-q','--junitxml='+junit])],
        'P4': [('regression',[py,'-m','pytest','-q','--junitxml='+junit]),
               ('api-contracts',[py,'scripts/export_openapi.py']),
               ('contracts',[py,'scripts/check_contracts.py']),
               ('conformance',[py,'scripts/check_spec_pack.py','--runtime','legalmath.conformance:evaluate_case']),
               ('demonstration',[py,'scripts/interpretation_acceptance.py','--out',str(attempt/'demonstration')]),
               ('browser',[py,'scripts/interpretation_browser.py','--out',str(attempt/'browser')]),
               ('package',[py,'scripts/interpretation_package_check.py','--out',str(attempt/'package')])],
    }
    return checks[phase]


def refresh(phase, s):
    ix=PHASES.index(phase)
    predecessors={p:s['phases'][p] for p in PHASES[:ix]}
    record={'phase':phase,'created_at':now(),'source':inputs(),'master_plan_hash':sha(PLAN),
            'predecessors':predecessors,'acceptance':read(PLAN)['phases'][ix]['acceptance'],
            'tasks':read(PLAN)['phases'][ix]['tasks'],
            'repairs':s['phases'][phase].get('repairs',[]),
            'required_before_execution':['exact-current-code author review','all preceding phases passed','protected evidence intact'],
            'limits':['LOCAL_SYNTHETIC','scripted members only','no legal-accuracy or bank-approval claim']}
    write(OUT/phase/'next-plan.json',record)
    return record


def note(path):
    p=Path(path).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():
        raise ValueError('Review/repair note must be an existing project-local JSON file')
    value=read(p)
    if not value.get('summary') or len(value['summary'])<40 or not value.get('findings'):
        raise ValueError('Review/repair needs a substantive summary and findings')
    return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'content':value}


def run(phase,s):
    ps=s['phases'][phase]
    if ps['status']=='PASSED':raise ValueError('Phase already passed; do not overwrite acceptance')
    required=PREDECESSORS[phase] if PREDECESSORS is not None else PHASES[:PHASES.index(phase)]
    if any(s['phases'][p]['status']!='PASSED' for p in required):
        raise ValueError('Predecessor has not passed')
    if ps['status']=='REPAIR_REQUIRED':raise ValueError('Record an executed repair before rerunning')
    if ps['status']=='RUNNING':raise ValueError('Interrupted supervisor: recover the existing attempt first')
    if sum(a['status']!='PASSED' for a in ps['attempts']) >= read(PLAN)['max_failed_attempts_per_phase']:
        raise ValueError('Explicit repair budget exhausted; revise the plan instead of resetting counts')
    plan=read(OUT/phase/'next-plan.json');review=read(OUT/phase/'review.json')
    current=inputs()
    if not plan or not review or plan['source']['digest']!=current['digest'] or review['source_digest']!=current['digest'] or review['plan_sha256']!=sha(OUT/phase/'next-plan.json'):
        raise ValueError('Missing/stale plan or review: refresh and review the current implementation')
    if sha(ROOT/review['note']['path'])!=review['note']['sha256']:
        raise ValueError('The reviewed note changed')
    protect()
    attempt=OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    attempt.mkdir(parents=True,exist_ok=False)
    record={'phase':phase,'started_at':now(),'status':'RUNNING','input_sha256':current['files'],
            'plan_sha256':sha(OUT/phase/'next-plan.json'),'review_sha256':sha(OUT/phase/'review.json'),
            'environment':{'python':sys.version,'executable':str(PYTHON),'platform':platform.platform(),
                           'device':'CPU; no GPU framework','context':'approved project phase runner'},
            'commands':[],'authority':'LOCAL_SYNTHETIC','git_commit':None}
    write(attempt/'run-manifest.json',record)
    ps['status']='RUNNING';write(OUT/'state.json',s)
    began=time.monotonic()
    try:
        for name,cmd in commands(phase,attempt):
            print(f'{phase}: {name}',flush=True)
            started=time.monotonic()
            with (attempt/(name+'.log')).open('w') as log:
                proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                                      env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'})
                record['running_process']={'pid':proc.pid,'proc_start':Path(f'/proc/{proc.pid}/stat').read_text().split()[21]}
                write(attempt/'run-manifest.json',record)
                try:code=proc.wait(timeout=COMMAND_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
            record['commands'].append({'name':name,'argv':cmd,'exit_code':code,'wall_seconds':round(time.monotonic()-started,3),'log':str((attempt/(name+'.log')).relative_to(ROOT))})
            record.pop('running_process',None)
            write(attempt/'run-manifest.json',record)
            if code:
                print((attempt/(name+'.log')).read_text()[-16000:],flush=True)
                raise ValueError(f'{name} failed with exit {code}')
        protect()
        if inputs()['digest']!=current['digest']:
            raise ValueError('Source inputs changed during acceptance; refresh and rerun')
        record['status']='PASSED'
    except (Exception,KeyboardInterrupt) as exc:
        record['status']='FAILED';record['failure']=str(exc)
    record.update(finished_at=now(),wall_seconds=round(time.monotonic()-began,3))
    record['artifact_sha256']={str(p.relative_to(attempt)):sha(p) for p in attempt.rglob('*') if p.is_file() and p.name!='run-manifest.json'}
    write(attempt/'run-manifest.json',record)
    ps['attempts'].append({'path':str((attempt/'run-manifest.json').relative_to(ROOT)),'sha256':sha(attempt/'run-manifest.json'),'status':record['status'],'failure':record.get('failure')})
    ps['status']='PASSED' if record['status']=='PASSED' else 'REPAIR_REQUIRED'
    write(OUT/'state.json',s)
    if ps['status']=='REPAIR_REQUIRED':
        write(OUT/phase/'repair-request.json',{'phase':phase,'attempt':ps['attempts'][-1],
              'action':'Diagnose the actual failure, repair implementation/harness, record changes and regression cases, then refresh/review/rerun.','may_advance':False})
        raise SystemExit(1)
    ix=PHASES.index(phase)
    if ix+1<len(PHASES):refresh(PHASES[ix+1],s)
    print(json.dumps({'phase':phase,'status':'PASSED','next_plan_refreshed':PHASES[ix+1] if ix+1<len(PHASES) else None}),flush=True)


def recover(phase,s):
    ps=s['phases'][phase]
    if ps['status']!='RUNNING':raise ValueError('No interrupted phase to recover')
    attempt=OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    record=read(attempt/'run-manifest.json')
    process=record.get('running_process')
    if process:
        stat=Path(f"/proc/{process['pid']}/stat")
        if stat.exists() and stat.read_text().split()[21]==process['proc_start']:
            os.killpg(process['pid'],signal.SIGKILL)
    record.update(status='FAILED',failure='SUPERVISOR_INTERRUPTED',finished_at=now())
    write(attempt/'run-manifest.json',record)
    ps['attempts'].append({'path':str((attempt/'run-manifest.json').relative_to(ROOT)),'sha256':sha(attempt/'run-manifest.json'),'status':'FAILED','failure':'SUPERVISOR_INTERRUPTED'})
    ps['status']='REPAIR_REQUIRED';write(OUT/'state.json',s)
    write(OUT/phase/'repair-request.json',{'phase':phase,'attempt':ps['attempts'][-1],'action':'Diagnose interruption and partial artifacts; record repair before retry.','may_advance':False})
    print('Recovered interrupted attempt as a counted failure; repair required')


def main():
    ap=ArgumentParser(description=__doc__)
    ap.add_argument('operation',choices=['preflight','refresh','review','repair','recover','run','status'])
    ap.add_argument('phase',nargs='?',choices=PHASES)
    ap.add_argument('--note')
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        s=state()
        if args.operation=='preflight':
            print(json.dumps({'status':'PASS','protection':protect(),'python':str(PYTHON),'jdk_exists':(ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1/bin/java').is_file(),'phases':list(PHASES),'fixed_commands':True},indent=2));return
        if args.operation=='status':print(json.dumps(s,indent=2));return
        if args.phase is None:ap.error('phase required')
        phase=args.phase
        if args.operation=='refresh':
            refresh(phase,s);print('Refreshed '+phase)
        elif args.operation=='review':
            n=note(args.note or '')
            if n['content'].get('verdict')!='PASS_WITH_LIMITS':raise ValueError('Review has unresolved blockers')
            plan=read(OUT/phase/'next-plan.json')
            if not plan or plan['source']['digest']!=inputs()['digest']:raise ValueError('Refresh before review')
            write(OUT/phase/'review.json',{'created_at':now(),'source_digest':inputs()['digest'],'plan_sha256':sha(OUT/phase/'next-plan.json'),'note':n,'independent_review':False})
            print('Recorded author review '+phase)
        elif args.operation=='repair':
            if s['phases'][phase]['status']!='REPAIR_REQUIRED':raise ValueError('No failed attempt to repair')
            n=note(args.note or '')
            if not n['content'].get('changes') or not n['content'].get('regression'):raise ValueError('Record the executed changes and regression')
            s['phases'][phase].setdefault('repairs',[]).append({'at':now(),'note':n,'source_digest':inputs()['digest']})
            s['phases'][phase]['status']='REPAIRED_PENDING_REVIEW';write(OUT/'state.json',s);refresh(phase,s)
            print('Recorded repair and refreshed '+phase)
        elif args.operation=='run':run(phase,s)
        elif args.operation=='recover':recover(phase,s)


if __name__=='__main__':main()
