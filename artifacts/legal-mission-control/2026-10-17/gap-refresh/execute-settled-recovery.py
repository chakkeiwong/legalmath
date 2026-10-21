"""Execute only the registered recovery, surviving editor disconnection."""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl, os, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import read, save, ref, require, verify, process_identity, process_alive
from scripts.legal_integration_master import BASE, PROGRAM, STATE
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery'
OUTPUT = WORK / 'execution'
LIVE = ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'live']

def check(name, command, outcomes):
    began = time.monotonic()
    with (OUTPUT / (name+'.stdout')).open('x') as out, (OUTPUT / (name+'.stderr')).open('x') as err:
        try:
            result = subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,timeout=900)
            row = dict(action=name,command=command,exit_code=result.returncode)
        except subprocess.TimeoutExpired:
            row = dict(action=name,command=command,timeout_seconds=900)
    row.update(wall_seconds=time.monotonic()-began,at_utc=datetime.now(timezone.utc).isoformat())
    outcomes.append(row); save(OUTPUT/'checks.json',outcomes)
    save(OUTPUT/'progress.json',dict(action=name,result=row,process=process_identity(os.getpid())))
    return row.get('exit_code') == 0

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with ExitStack() as stack:
        for path in (WORK.parent/'detached-worker.lock',OUTPUT/'worker.lock'):
            handle=stack.enter_context(path.open('a')); fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (OUTPUT/'worker-start.json').exists(),'Inspect existing worker; never duplicate execution')
        for name in ('worker-start.json','worker-live-process.json'):
            require(not process_alive(read(WORK.parent/'evidence-continuation'/name)['process']),'Prior worker survives')
        p=read(ROOT/PROGRAM); s=read(ROOT/STATE)
        require(p.get('settled_recovery',{}).get('work')==str(WORK.relative_to(ROOT)),'Recovery not registered')
        require(not any(t['status']=='RUNNING' for t in s['tasks'].values()),'Live owner already exists')
        for tid,attempts in (('acquire-evidence',6),('acquire-p10',8)):
            require(s['tasks'][tid]['status']=='PENDING' and len(s['tasks'][tid]['attempts'])==attempts,'Owner frontier changed')
        grant=read(ROOT/BASE/'live-grant.json')
        require(datetime.now(timezone.utc)<datetime.fromisoformat(grant['deadline_utc']),'Live deadline expired')
        start=dict(profile='settled-recovery-worker.v1',command=LIVE,process=process_identity(os.getpid()),
            at_utc=datetime.now(timezone.utc).isoformat(),program=ref(ROOT,PROGRAM),
            binding=ref(ROOT,BASE/'current-binding.json'),grant=ref(ROOT,BASE/'live-grant.json'),
            ledger_before=ref(ROOT,BASE/'live-calls.json'),review=p['settled_recovery']['review'],
            source=ref(ROOT,Path(__file__)),environment=str(ROOT/'.venv-context/bin/python'),
            git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            devices='CPU only; CUDA_VISIBLE_DEVICES=-1',seeds='N/A: no stochastic ranking',
            calls_added=0,attempts_reset=False,deadline_extended=False)
        save(OUTPUT/'worker-start.json',start)
        checks=[]; ready=True
        for name,command in (
            ('pre-refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
            ('pre-verify',['.venv/bin/python','scripts/legal_integration_master.py','verify']),
            ('pre-check',['.venv/bin/python','scripts/legal_mission_control.py','check']),
            ('pre-status',['.venv/bin/python','scripts/legal_mission_control.py','status']),
            ('pre-admit',['.venv/bin/python','scripts/legal_mission_control.py','admit'])):
            ready=check(name,command,checks) and ready
        code=None
        if ready:
            save(OUTPUT/'progress.json',dict(action='live',process=process_identity(os.getpid())))
            with (OUTPUT/'worker.log').open('x') as out:
                child=subprocess.Popen(LIVE,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
                save(OUTPUT/'worker-live-process.json',dict(process=process_identity(child.pid),command=LIVE))
                code=child.wait()
            for name,command in (
                ('post-refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                ('post-verify',['.venv/bin/python','scripts/legal_integration_master.py','verify'])):
                check(name,command,checks)
        save(OUTPUT/'worker-result.json',dict(preflight_passed=ready,live_exit_code=code,checks=checks,
            calls=len(read(ROOT/BASE/'live-calls.json')['calls']),start=ref(ROOT,OUTPUT/'worker-start.json'),
            finished_at_utc=datetime.now(timezone.utc).isoformat(),integration_complete=False,legal_acceptance=False))

if __name__=='__main__': main()
