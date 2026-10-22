"""One admitted agent-notice attempt, bounded stages and immutable results."""
from datetime import datetime, timezone
from pathlib import Path
import difflib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
from legalmath.prospectus.execution_authority import Authority,REL,read,write,digest,file_hash
from scripts.prospectus_agent_window_prepare import PLAN,REVIEW,CHANGED,BOUNDS
from scripts import prospectus_agent_window_evidence as evidence

ATTEMPT=REL+'/attempts/basf-office/attempt-003'
HERE=ROOT/ATTEMPT
TESTS=['tests/prospectus_successor/'+n+'.py' for n in ('test_agent_notice_window','test_minimal_explanations',
    'test_calendar_facts','test_ratio_facts','test_law_assistance_mode','test_successor')]
SUPPORT=[PLAN,*TESTS,*['scripts/prospectus_agent_window_'+n+'.py' for n in ('prepare','run','evidence')],
    'scripts/prospectus_calendar_evidence.py','scripts/prospectus_calendar_oracle.py','scripts/prospectus_law_mode_evidence.py','scripts/prospectus_explanation_evidence.py','scripts/prospectus_explanation_oracle.py']
STAGES=('tests','notice','original','calendar','seal')


def methods():
    paths={str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath').rglob('*')
           if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    return {n:file_hash(ROOT/n) for n in sorted(paths|set(SUPPORT))}


def size():
    paths=[HERE,ROOT/REVIEW,*[ROOT/n for n in SUPPORT],
        ROOT/REL/'revisions/0237.json']
    paths.extend((ROOT/REL/'proposals').glob('agent-window-237*.json'))
    paths.extend((ROOT/REL).glob('closure-routes-2026-10-17-agent-window-237*.json'))
    files=set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    return sum(p.stat().st_size for p in files if p.exists())


def freeze():
    a=Authority(ROOT);program,tasks,_=a.spec();task=tasks['basf-office']
    ad=read(HERE/'admission.json')
    event=next(e for e in reversed(a.events()) if e.get('task')=='basf-office')
    evidence.require(program['revision']==237 and ad['program_sha256']==digest(program)
        and ad['binding']==a.binding(task) and event['kind']=='ADMIT' and event['attempt']==ATTEMPT
        and task['agent_window']['bounds']==BOUNDS,'Unchanged notice-window admission required')
    current=methods();before=read(ROOT/REVIEW/'before-methods.json')
    production={k:v for k,v in current.items() if k.startswith('src/')}
    evidence.require(set(production)==set(before)
        and {k for k in before if before[k]!=production[k]}==set(CHANGED),'Unrelated production mutation')
    if (HERE/'methods.json').exists():
        evidence.require(read(HERE/'methods.json')==current,'Frozen explanation methods changed')
    else:
        write(HERE/'methods.json',current,exclusive=True)
        for n in [*CHANGED,*SUPPORT]:
            dest=HERE/'methods'/n;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as out:out.write((ROOT/n).read_bytes())
        diff=[]
        for n in CHANGED:
            diff.extend(difflib.unified_diff((ROOT/REVIEW/'before'/n).read_text().splitlines(True),
                (ROOT/n).read_text().splitlines(True),fromfile='before/'+n,tofile='after/'+n))
        with (HERE/'production.patch').open('x') as out:out.write(''.join(diff))
    return ad,current


def tests():
    argv=[sys.executable,'-c',
        'import sys;sys.dont_write_bytecode=True;sys.path[:0]=[sys.argv[1],sys.argv[2]];import pytest;raise SystemExit(pytest.main(sys.argv[3:]))',
        str(ROOT/'src'),str(ROOT),'-q','-p','no:cacheprovider',*TESTS,'--junitxml='+str(HERE/'tests.xml')]
    write(HERE/'test-command.json',{'argv':argv,'timeout_seconds':100},exclusive=True)
    with (HERE/'tests.stdout').open('xb') as out,(HERE/'tests.stderr').open('xb') as err:
        proc=subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=out,stderr=err,timeout=100)
    suites=list(ET.parse(HERE/'tests.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    evidence.require(proc.returncode==0 and counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped')),
                     'Notice-window tests failed; inspect retained logs')
    return counts


def seal(status,error=None):
    write(HERE/'result.json',{'task':'basf-office','status':status,'error':error,
        'scope':'CONDITIONAL_SOURCE_BOUND_AGENT_NOTICE_WINDOW',
        'whole_task_complete':False,'whole_program_complete':False},exclusive=True)
    write(HERE/'outputs.json',{str(p.relative_to(HERE)):file_hash(p) for p in sorted(HERE.rglob('*'))
        if p.is_file() and p.name not in {'outputs.json','admission.json'}},exclusive=True)


def main(stage):
    evidence.require(stage in STAGES and not (HERE/'outputs.json').exists(),'Unknown or sealed stage')
    index=STAGES.index(stage)
    started={p.parent.name for p in (HERE/'stages').glob('*/started.json')}
    ended={p.parent.name for p in (HERE/'stages').glob('*/result.json')}
    evidence.require(started==ended==set(STAGES[:index]),'Repeated, skipped or interrupted stage')
    evidence.require(all(read(HERE/'stages'/s/'result.json')['status']=='PASS' for s in STAGES[:index]),'Failed predecessor')
    folder=HERE/'stages'/stage;folder.mkdir(parents=True,exist_ok=False)
    command=['.venv/bin/python','scripts/prospectus_agent_window_run.py',stage]
    write(folder/'started.json',{'at':datetime.now(timezone.utc).isoformat(),'command':command,'plan':PLAN},exclusive=True)
    tick=time.monotonic()
    def expired(*args):raise TimeoutError('Notice-window stage time limit')
    signal.signal(signal.SIGALRM,expired);signal.alarm(110)
    try:
        ad,frozen=freeze()
        guard={'blocked':0}
        if stage!='tests':
            def audit(event,args):
                if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.exec','os.posix_spawn','os.spawn','pty.spawn'}:
                    guard['blocked']+=1;raise RuntimeError('Explanation evidence forbids process/network')
            sys.addaudithook(audit)
        if stage=='tests':details=tests()
        elif stage=='notice':details=evidence.cohort(ROOT,HERE)
        elif stage in {'original','calendar'}:details=evidence.regression(ROOT,HERE,stage)
        else:
            evidence.require((HERE/'RESULT.md').is_file(),'Actual result review required')
            details={s:read(HERE/'stages'/s/'result.json')['details'] for s in STAGES[:index]}
        evidence.require(frozen==methods() and guard['blocked']==0,'Method drift or forbidden action')
        seconds=time.monotonic()-tick
        total=seconds+read(ROOT/REVIEW/'preparation-time.json')['seconds']+sum(read(HERE/'stages'/s/'result.json')['seconds'] for s in STAGES[:index])
        used=size()
        evidence.require(total<600 and used+BOUNDS['reserve_bytes']<BOUNDS['new_bytes'],'Incremental budget exhausted')
        write(folder/'result.json',{'status':'PASS','details':details,'seconds':seconds,'cumulative_seconds':total,
            'cumulative_bytes':used,'guard':guard},exclusive=True)
        if stage=='seal':
            write(HERE/'run-manifest.json',{'git_commit':ad['git_commit'],'plan':PLAN,'result':ATTEMPT+'/RESULT.md',
                'interpreter':sys.executable,'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','seeds':'N/A deterministic',
                'commands':[read(HERE/'stages'/s/'started.json') for s in STAGES],
                'test_command':read(HERE/'test-command.json'),'sources':REVIEW+'/review.json',
                'methods':frozen,'cumulative_seconds':total,'cumulative_bytes':used,
                'historical_unmeasured_seconds':'UNKNOWN','preparation_note':'Original base124 source reviewed; historical authoring/acquisition costs UNKNOWN; no new source extraction'},exclusive=True)
            seal('PASS')
        print(json.dumps({'stage':stage,'status':'PASS','details':details,'seconds':seconds,'cumulative_seconds':total}))
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        write(folder/'failure.json',{'error':error,'traceback':traceback.format_exc()},exclusive=True)
        if not (folder/'result.json').exists():write(folder/'result.json',{'status':'FAIL','error':error,'seconds':time.monotonic()-tick},exclusive=True)
        seal('FAIL',error)
        raise
    finally:signal.alarm(0)


if __name__=='__main__':main(sys.argv[1])
