#!/usr/bin/env python3
"""Fixed, bounded supervisor for the consolidated assurance successor."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile
import signal
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
OUT = ROOT/'artifacts/assurance-successor/2026-09-28'
DOC = ROOT/'docs/implementation/assurance-successor'
PLAN = ROOT/'docs/plans/assurance-successor-execution.md'
PHASES = tuple('S'+str(i) for i in range(12))
OLD_LEDGER = ROOT/'artifacts/interpretation/round7/live-allowance.json'
GRANT = OUT/'grant.json'
PY = ROOT/'.venv/bin/python'
MAX_ATTEMPTS = 3
PHASE_ATTEMPT_OVERRIDES = {'S6':6,'S8':9}
ASSESSMENT_PHASES = ('S9','S10','S11')


def attempt_limit(name):return PHASE_ATTEMPT_OVERRIDES.get(name,MAX_ATTEMPTS)


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n'); tmp.replace(p)
def rel(p): return Path(p).resolve().relative_to(ROOT).as_posix()


def phase_result(manifest):
    if isinstance(manifest.get('result'),dict):return manifest['result']
    # Earlier failed versions retained the structured result in the phase work
    # directory but omitted it from the top-level manifest.
    name=f"artifacts/assurance-successor/2026-09-28/{manifest['phase']}/attempt-{manifest['attempt']:02}/result.json"
    if name not in manifest.get('outputs',{}) or sha(ROOT/name)!=manifest['outputs'][name]:
        raise RuntimeError('Missing bound structured phase result')
    return read(ROOT/name)


def incomplete_assessment_basis(current):
    row=current['phases']['S8']
    if row['status']!='FAILED' or not row['attempts']:raise RuntimeError('Assessment requires terminal failed S8')
    ref=row['attempts'][-1];path=ROOT/ref['manifest']
    if sha(path)!=ref['sha256']:raise RuntimeError('Changed failed-study manifest')
    manifest=read(path)
    if manifest.get('phase')!='S8' or manifest.get('status')!='FAILED':raise RuntimeError('Wrong failed-study receipt')
    for name,h in manifest.get('outputs',{}).items():
        if sha(ROOT/name)!=h:raise RuntimeError('Changed failed-study output')
    result=phase_result(manifest);freeze=read(OUT/'task-freeze.json')
    ids=[r['task_id'] for r in result['tasks']]
    if len(ids)!=len(set(ids)) or set(ids)!={r['task_id'] for r in freeze['tasks']} or result.get('execution_complete') is not False:
        raise RuntimeError('Failed study lost tasks or was relabelled complete')
    resource=[]
    for task in result['tasks']:
        for arm in ('single','ensemble'):
            r=task[arm]
            if r.get('error') in ('E_INTEGRITY','E_AUTHORITY'):raise RuntimeError('Integrity failure cannot be assessed as valid study evidence')
            if r.get('error')=='E_RESOURCE_LIMIT':resource.append({'task':task['task_id'],'arm':arm,'evidence':r})
            if r.get('dossier'):
                dref=r['dossier']
                if sha(ROOT/dref['path'])!=dref['sha256']:raise RuntimeError('Changed failed-study dossier')
                d=read(ROOT/dref['path']);stopped=d.get('scoped',{}).get('stopped')
                if stopped and stopped.get('error')=='E_RESOURCE_LIMIT':
                    resource.append({'task':task['task_id'],'arm':arm,'evidence':stopped})
    if not resource:raise RuntimeError('Assessment exception requires an explicit resource veto')
    return {'profile':'incomplete-study-assessment.v1','study_attempt':ref,
        'resource_vetoes':resource,'all_frozen_tasks_retained':True,
        'study_execution_complete':False,'changes_study_status':False}


def state():
    return read(OUT/'state.json') if (OUT/'state.json').exists() else {
        'protocol': 'assurance-successor.v1', 'started_at': now(), 'started_epoch': time.time(),
        'phases': {p: {'status': 'PLANNED', 'attempts': []} for p in PHASES}}


def baseline(work):
    previous = read(OLD_LEDGER)
    if previous['maximum'] != 500 or len(previous['calls']) != 500:
        raise RuntimeError('Unexpected predecessor allowance')
    grant = {'schema':'legalmath.additional-grant.v1', 'grant_id':'user.2026-09-28.additional500',
        'authorized_calls':500,
        'authorization':'User: you have another 500 allowance. Ensure successor covers all issues, review thoroughly and execute.',
        'predecessor':{'path':'../../interpretation/round7/live-allowance.json','sha256':sha(OLD_LEDGER)},
        'ledger':'live-allowance.json'}
    if GRANT.exists() and read(GRANT) != grant: raise RuntimeError('Grant identity mismatch')
    save(GRANT, grant)
    ledger = OUT/'live-allowance.json'
    if not ledger.exists(): save(ledger, {'maximum':500,'calls':[]})
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    checked = GrantedAllowance(GRANT).verify()
    files = []
    for directory in ('src','scripts','tests','docs/plans','docs/implementation','docs/monograph','docs/proposal'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and
            p.suffix in ('.py','.java','.json','.md','.tex','.bib') and '__pycache__' not in p.parts
            and 'review' not in p.parts)
    files += [OLD_LEDGER, ROOT/'artifacts/interpretation/round15/remaining-work.json',
              ROOT/'artifacts/interpretation/round16/phase-results.json',
              ROOT/'artifacts/proof-carrying-assurance/verified-execution-v3/final-report.json']
    hashes = {rel(p):sha(p) for p in sorted(set(files))}
    with zipfile.ZipFile(work/'baseline.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in hashes: archive.write(ROOT/name, name)
    save(work/'inputs.json', hashes)
    remaining = read(ROOT/'artifacts/interpretation/round15/remaining-work.json')
    save(work/'remaining-work.json', remaining)
    rows = remaining['restored_pair_rows']
    if len(rows) != 232 or len({(r['case_id'],r['claim_id'],r['candidate_id']) for r in rows}) != 232:
        raise RuntimeError('Inherited pair universe changed')
    return {'status':'BASELINE_AND_NEW_GRANT_BOUND', 'grant':checked, 'material_files':len(hashes),
            'backlog_pairs':len(rows), 'release_eligible':False}


def refresh(current, *, persist=True):
    used = len(read(OUT/'live-allowance.json')['calls']) if (OUT/'live-allowance.json').exists() else 0
    changed={};invalid=[]
    for p,r in current['phases'].items():
        if r['status']!='PASSED' or not r['attempts']:continue
        ref=r['attempts'][-1];path=ROOT/ref['manifest']
        if not path.is_file() or sha(path)!=ref['sha256']:
            invalid.append(p);continue
        manifest=read(path)
        if manifest.get('phase')!=p or manifest.get('status')!='PASSED':
            invalid.append(p);continue
        basis=manifest.get('incomplete_study_assessment')
        if basis and basis['study_attempt']!=current['phases']['S8']['attempts'][-1]:
            invalid.append(p);continue
        if any(not (ROOT/name).is_file() or sha(ROOT/name)!=h for name,h in manifest.get('outputs',{}).items()):
            invalid.append(p)
        deltas=[name for name,h in manifest.get('implementation',{}).items()
                if not (ROOT/name).is_file() or sha(ROOT/name)!=h]
        if deltas:changed[p]=deltas
    if invalid:
        first=min(map(PHASES.index,invalid))
        for p in PHASES[first:]:
            if current['phases'][p]['status']=='PASSED':
                current['phases'][p]['status']='STALE_EVIDENCE' if p in invalid else 'STALE_DEPENDENCY'
    final=OUT/'final-report.json'
    if final.exists():
        report=read(final)
        if report.get('status')!='STALE_REVALIDATION_REQUIRED':
            changed_final=[n for key in ('material_inputs','retained_evidence') for n,h in report.get(key,{}).items()
                           if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
            if changed_final or invalid or 'S11' in changed:
                archive=OUT/'superseded-final-reports'/f'{sha(final)}.json'
                if persist:
                    archive.parent.mkdir(exist_ok=True);archive.write_bytes(final.read_bytes())
                    save(final,{'status':'STALE_REVALIDATION_REQUIRED','superseded_report':rel(archive),
                                'changed_files':changed_final,'invalid_phases':invalid,'release_eligible':False})
                if current['phases']['S11']['status']=='PASSED':current['phases']['S11']['status']='STALE_SOURCE'
    if persist and (OUT/'state.json').exists():save(OUT/'state.json',current)
    next_phase = next((p for p in PHASES if current['phases'][p]['status'] != 'PASSED'), None)
    value = {'at':now(), 'next_phase':next_phase, 'live_used':used,'live_remaining':500-used,
        'historical_phase_code_changes':changed,'invalid_evidence_phases':invalid,
        'current_implementation_revalidation':'Required by the final no-skip regression; old phase receipts remain evidence only of their recorded versions' if changed else 'No recorded phase implementation changed',
        'phases':{p:{'status':r['status'],'attempts_consumed':len(r['attempts']),
                     'attempts_remaining':attempt_limit(p)-len(r['attempts'])} for p,r in current['phases'].items()},
        'open_evidence':{p:r.get('open_evidence',[]) for p,r in current['phases'].items() if r.get('open_evidence')},
        'next_action':'Repair current failed phase before retry' if next_phase and current['phases'][next_phase]['status']=='FAILED'
                      else 'Observe running '+next_phase+'; do not start a duplicate phase' if next_phase and current['phases'][next_phase]['status']=='RUNNING'
                      else 'Execute '+next_phase if next_phase else 'Review per-gap outcome and remaining external evidence',
        'release_eligible':False}
    if persist:save(OUT/'next-phase-plan.json', value)
    return value


def status_report():
    """A status reader cannot overwrite the active writer's completed phase."""
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'.master.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**refresh(state(),persist=False),'active_phase_writer':True}
        return {**refresh(state()),'active_phase_writer':False}


def phase(name,*,assessment=False):
    policy=read(DOC/'allowlist.json')
    if (policy['phases']!=list(PHASES) or policy['additional_model_calls']!=500 or
            policy['max_attempts_per_phase']!=MAX_ATTEMPTS or
            policy.get('phase_attempt_overrides',{})!=PHASE_ATTEMPT_OVERRIDES or policy['old_ledger_mutation'] or
            policy['shell_fragments'] or policy['release_eligible']):
        raise RuntimeError('Controller and command policy differ')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.master.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = state(); row = current['phases'][name]
        if assessment and (name not in ASSESSMENT_PHASES or policy.get('assessment_phases')!=list(ASSESSMENT_PHASES)):
            raise RuntimeError('Assessment action is limited to evaluation, documents and final verification')
        assessment_basis=incomplete_assessment_basis(current) if assessment else None
        if time.time()-current['started_epoch'] > 48*3600: raise RuntimeError('Campaign deadline exhausted')
        for p in PHASES[:PHASES.index(name)]:
            if p=='S8' and assessment:continue
            if current['phases'][p]['status'] != 'PASSED': raise RuntimeError('Predecessor incomplete: '+p)
            prior = current['phases'][p]['attempts'][-1]
            if sha(ROOT/prior['manifest']) != prior['sha256']: raise RuntimeError('Changed predecessor manifest')
            record = read(ROOT/prior['manifest'])
            if record.get('phase')!=p or record.get('status')!='PASSED':raise RuntimeError('Wrong predecessor phase receipt: '+p)
            previous_basis=record.get('incomplete_study_assessment')
            if previous_basis and previous_basis!=assessment_basis:raise RuntimeError('Assessment belongs to an earlier or different failed study')
            for f,h in record['outputs'].items():
                if sha(ROOT/f) != h: raise RuntimeError('Changed predecessor evidence: '+f)
        if row['status'] == 'PASSED': return read(ROOT/row['attempts'][-1]['manifest'])['result']
        if len(row['attempts']) >= attempt_limit(name): raise RuntimeError('Fixed phase attempt ceiling exhausted')
        if row['attempts']:
            repair = DOC/f'{name}-repair-{len(row["attempts"])}.json'
            if not repair.exists() or read(repair).get('focused_check_passed') is not True:
                raise RuntimeError('Executed focused repair record required before retry')
            check=repair.with_suffix('.xml');receipt=read(repair)
            if not check.exists() or receipt.get('focused_xml_sha256')!=sha(check):
                raise RuntimeError('Repair requires exact executed focused-test XML')
            root=ET.parse(check).getroot();suites=[root] if root.tag=='testsuite' else list(root)
            if (not sum(int(s.get('tests','0')) for s in suites) or
                any(int(s.get(k,'0')) for s in suites for k in ('failures','errors','skipped'))):
                raise RuntimeError('Focused repair tests did not pass without skips')
        attempt = len(row['attempts'])+1; work = OUT/name/f'attempt-{attempt:02}'
        work.mkdir(parents=True,exist_ok=False)
        row['attempts'].append({'status':'RESERVED','directory':rel(work)})
        row['status']='RUNNING'; save(OUT/'state.json',current)
        begun=time.monotonic()
        record={'phase':name,'attempt':attempt,'owner_pid':os.getpid(),'started_at':now(),'plan':rel(PLAN),'plan_sha256':sha(PLAN),
            'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':sys.version,'executable':str(Path(sys.executable).resolve()),
            'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1','seeds':'N/A for deterministic checks; provider sampling is external',
            'command':[str(PY),str(Path(__file__)), 'assess' if assessment else 'phase',name],
            'incomplete_study_assessment':assessment_basis,
            'controller_sha256':sha(__file__),
            'implementation':{rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
                              if p.is_file() and p.suffix in ('.py','.java','.json','.lean')},
            'phase_driver_sha256':sha(ROOT/'scripts/assurance_successor_phases.py')
                                 if (ROOT/'scripts/assurance_successor_phases.py').exists() else None,
            'phase_sources':{rel(p):sha(p) for p in sorted((ROOT/'scripts').glob('assurance_successor_*.py'))},
            'result':None}
        archive=work/'implementation-sources.zip'
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for filename in sorted(set(record['implementation'])|set(record['phase_sources'])):
                z.write(ROOT/filename,filename)
            z.write(Path(__file__),'controller/run_assurance_successor.py')
        record['implementation_archive']={'path':rel(archive),'sha256':sha(archive)}
        save(work/'start-manifest.json',record)
        os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['HF_HUB_OFFLINE']='1'
        try:
            if name=='S0': result=baseline(work)
            else:
                from assurance_successor_phases import execute
                result=execute(name,work)
            record['result']=result
            if not isinstance(result,dict) or result.get('execution_complete') is False:
                raise RuntimeError('Phase execution incomplete; structured result retained in '+str(work))
            record.update(status='PASSED',result=result)
            row['status']='PASSED';row['open_evidence']=result.get('open_evidence',[])
        except BaseException as exc:
            record.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
            row['status']='FAILED'
            raise
        finally:
            record.update(finished_at=now(),wall_seconds=round(time.monotonic()-begun,3),
                outputs={rel(p):sha(p) for p in work.rglob('*') if p.is_file() and p.name!='manifest.json'})
            save(work/'manifest.json',record)
            row['attempts'][-1]={'manifest':rel(work/'manifest.json'),'sha256':sha(work/'manifest.json'),'status':record['status']}
            save(OUT/'state.json',current);refresh(current)
        return result


def halt_owned_phase(name):
    """Stop only this repository's exact active phase; preserve interrupted work."""
    current=state();row=current['phases'][name]
    if row['status']!='RUNNING':raise RuntimeError('No running phase to halt')
    matches=[];processes={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            argv=[v.decode() for v in (p/'cmdline').read_bytes().split(b'\0') if v]
            status=(p/'status').read_text();parent=int(re.search(r'^PPid:\s+(\d+)',status,re.M)[1])
            processes[int(p.name)]={'argv':argv,'parent':parent}
            if (len(argv)==4 and Path(argv[1]).name=='run_assurance_successor.py' and argv[2:]==['phase',name]
                and (p/'cwd').resolve()==ROOT):matches.append(int(p.name))
        except (OSError,ValueError,TypeError,UnicodeDecodeError):continue
    if len(matches)!=1:raise RuntimeError('Expected exactly one owned phase process: '+str(matches))
    pid=matches[0];owned={pid}
    while True:
        children={p for p,r in processes.items() if r['parent'] in owned}
        if children<=owned:break
        owned|=children
    work=ROOT/row['attempts'][-1]['directory'];retained=[]
    for child in sorted(owned-{pid}):
        args=processes[child]['argv']
        if '--cd' not in args:continue
        directory=Path(args[args.index('--cd')+1])
        if directory.parent!=Path('/tmp') or not directory.name.startswith('legalmath-codex-'):continue
        target=work/'interrupted-transport'/str(child);target.mkdir(parents=True,exist_ok=True)
        for f in ('request.json','schema.json','events.jsonl','stderr.txt','result.json'):
            source=directory/f
            if source.exists():
                data=source.read_bytes()
                if f=='stderr.txt':data=re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|token)\s*[=:]\s*)[^\s,\"]+',r'\1[REDACTED]',data.decode(errors='replace')).encode()
                (target/f).write_bytes(data)
        retained.append(rel(target))
    os.kill(pid,signal.SIGTERM)
    for child in sorted(owned-{pid},reverse=True):
        try:os.kill(child,signal.SIGTERM)
        except ProcessLookupError:pass
    with (OUT/'.master.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=state();row=current['phases'][name]
        record=read(work/'start-manifest.json') if (work/'start-manifest.json').exists() else {}
        record.update({'phase':name,'attempt':len(row['attempts']),'status':'FAILED',
            'error':'CONTROLLED_IMPLEMENTATION_REPAIR_HALT','finished_at':now(),
            'reason':read(DOC/f'{name}-interruption-request.json')['reason'] if (DOC/f'{name}-interruption-request.json').exists()
                     else 'Repeated identifier-contract failures require clearer diagnostics before further dispatch.',
            'interrupted_owned_processes':sorted(owned),'transport_retained':retained,
            'original_in_memory_start_manifest':'Retained in start-manifest.json and implementation archive' if (work/'start-manifest.json').exists()
                else 'Unavailable after controlled halt; per-action request and implementation identities remain retained',
            'result':None,'outputs':{rel(p):sha(p) for p in work.rglob('*') if p.is_file() and p.name!='manifest.json'}})
        save(work/'manifest.json',record)
        row['status']='FAILED';row['attempts'][-1]={'manifest':rel(work/'manifest.json'),'sha256':sha(work/'manifest.json'),'status':'FAILED'}
        save(OUT/'state.json',current);refresh(current)
    return record


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['phase','status','run','halt','assess','preflight'])
    parser.add_argument('phase',nargs='?',choices=PHASES); args=parser.parse_args()
    if args.action=='status': result=status_report()
    elif args.action=='preflight':
        if args.phase or 'preflight' not in read(DOC/'allowlist.json')['actions']:parser.error('Invalid preflight action')
        from assurance_successor_regression import run
        result=run()
    elif args.action=='halt':
        if not args.phase:parser.error('phase required')
        result=halt_owned_phase(args.phase)
    elif args.action in ('phase','assess'):
        if not args.phase:parser.error('phase required')
        result=phase(args.phase,assessment=args.action=='assess')
    else:
        for p in PHASES:
            print('Executing '+p,flush=True);phase(p)
        result=refresh(state())
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
