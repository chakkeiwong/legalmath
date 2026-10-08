"""Bounded local scheduler and immutable snapshots of an operator's registry."""
from copy import deepcopy
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Literal
from pydantic import Field
from ...canonical import canonical,digest,loads,raw_digest
from ...domain import timestamp
from ...errors import LegalMathError
from ..contracts import Strict,Id,Text,Hash,parse
from .examples import ExampleScope
from .sources import official_url
from .monitor import immutable,save


class Document(Strict):
    url: Text
    media_type: Literal['text/plain','text/html','application/json','application/pdf']
    path: Text | None = None
    sha256: Hash | None = None
    aliases: list[Text] = Field(default_factory=list,max_length=30)


class Control(Strict):
    control_id: Id
    source: Text
    dependencies: list[Text] = Field(max_length=100)
    selected_slice: Text
    authority_provisions: list[Id] = Field(default_factory=list,max_length=100)
    example_scope: ExampleScope | None = None


class Registry(Strict):
    documents: list[Document] = Field(min_length=1,max_length=100)
    controls: list[Control] = Field(min_length=1,max_length=20)
    cadence_seconds: int = Field(ge=1,le=604800)
    max_attempts: int = Field(ge=1,le=6)
    fact_schema_hash: Text
    authority_registry: Text | None = None
    example_registry: Text | None = None


def snapshot_registry(path,out,resource_root):
    path=Path(path).resolve();root=Path(resource_root).resolve();out=Path(out)
    original=path.read_bytes();config=parse(Registry,loads(original));files={};total=0
    def retain(location,name):
        nonlocal total
        source=(path.parent/location).resolve()
        if not source.is_relative_to(root):raise LegalMathError('E_REFERENCE',details='Resource outside configured registry root')
        data=source.read_bytes();total+=len(data)
        if len(data)>10000000 or total>64000000:raise LegalMathError('E_RESOURCE_LIMIT')
        files[name]=data;return data
    for index,doc in enumerate(config['documents']):
        official_url(doc['url'])
        if doc['path'] is None:
            if doc['sha256'] is not None:raise LegalMathError('E_SCHEMA',details='Pinned remote documents must be retained before scheduling')
            doc.pop('path');doc.pop('sha256');continue
        name='sources/'+str(index)+'.bin';data=retain(doc['path'],name)
        if doc['sha256'] is not None and doc['sha256']!=raw_digest(data):raise LegalMathError('E_HASH_MISMATCH')
        doc.update(path=name,sha256=raw_digest(data))
    if len({c['control_id'] for c in config['controls']})!=len(config['controls']):raise LegalMathError('E_DUPLICATE_ID')
    urls={d['url'] for d in config['documents']}
    if len(urls)!=len(config['documents']):raise LegalMathError('E_DUPLICATE_ID')
    for control in config['controls']:
        if not {control['source'],*control['dependencies']}<=urls:raise LegalMathError('E_REFERENCE')
        if control['authority_provisions'] and not config['authority_registry']:raise LegalMathError('E_REFERENCE')
        if control['example_scope'] and not config['example_registry']:raise LegalMathError('E_REFERENCE')
    if config['authority_registry']:
        catalog_location=config['authority_registry'];catalog_bytes=retain(catalog_location,'authority/catalog.json')
        catalog=loads(catalog_bytes);catalog_path=(path.parent/catalog_location).resolve()
        for edition in catalog['editions']:
            if Path(edition['path']).is_absolute():raise LegalMathError('E_REFERENCE')
            source=(catalog_path.parent/edition['path']).resolve()
            if not source.is_relative_to(catalog_path.parent):raise LegalMathError('E_REFERENCE')
            if source.exists():
                data=retain(str(source),'authority/'+edition['path'])
                if raw_digest(data)!=edition['raw_sha256']:raise LegalMathError('E_HASH_MISMATCH')
        config['authority_registry']='authority/catalog.json'
    if config['example_registry']:
        if not config['authority_registry']:raise LegalMathError('E_REFERENCE')
        retain(config['example_registry'],'example-registry.json');config['example_registry']='example-registry.json'
    config={k:v for k,v in config.items() if v is not None}
    if path.read_bytes()!=original:raise LegalMathError('E_STALE_REVIEW')
    manifest={'original_registry_hash':raw_digest(original),'config_hash':digest(config),
              'files':{name:raw_digest(data) for name,data in files.items()}}
    key=digest(manifest);directory=out/key
    if directory.exists():
        old=loads((directory/'manifest.json').read_bytes())
        if old!=manifest or raw_digest((directory/'registry.json').read_bytes())!=raw_digest(canonical(config)):
            raise LegalMathError('E_INTEGRITY')
        for name,data in files.items():
            if (directory/name).read_bytes()!=data:raise LegalMathError('E_INTEGRITY')
    else:
        directory.mkdir(parents=True)
        for name,data in files.items():
            dest=directory/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        save(directory/'registry.json',config);save(directory/'manifest.json',manifest)
    return {'snapshot_id':key,'directory':str(directory),'config':str(directory/'registry.json'),
            'registry_hash':manifest['original_registry_hash']}


def command(args,config,out):
    argv=[sys.executable,'-m','legalmath.cli','assurance-monitor','--config',str(config),
          '--out',str(out),'--jdk',str(args.jdk),'--at',args.at]
    if args.settings:argv+=['--settings',str(Path(args.settings).resolve())]
    if args.replay_responses:argv+=['--replay-responses',str(Path(args.replay_responses).resolve())]
    else:
        if not args.allowance:raise LegalMathError('E_AUTHORITY')
        argv+=['--allowance',str(Path(args.allowance).resolve()),'--total-calls',str(args.total_calls)]
    return argv


def snapshot_dispatch_inputs(args,out):
    retained=deepcopy(args);files={}
    for key in ('settings','replay_responses'):
        location=getattr(args,key,None)
        if location:
            data=Path(location).read_bytes()
            if len(data)>16000000:raise LegalMathError('E_RESOURCE_LIMIT')
            files[key+'.json']=data
    manifest={'files':{name:raw_digest(data) for name,data in files.items()},
              'at':args.at,'jdk':str(Path(args.jdk).resolve()),'python':sys.executable,'total_calls':args.total_calls}
    key=digest(manifest);directory=Path(out)/key
    if directory.exists():
        if loads((directory/'manifest.json').read_bytes())!=manifest:raise LegalMathError('E_INTEGRITY')
        if any((directory/name).read_bytes()!=data for name,data in files.items()):raise LegalMathError('E_INTEGRITY')
    else:
        directory.mkdir(parents=True)
        for name,data in files.items():(directory/name).write_bytes(data)
        save(directory/'manifest.json',manifest)
    for name in files:setattr(retained,name[:-5],str(directory/name))
    return retained,{'snapshot_id':key,'directory':str(directory),'manifest':manifest}


def attention(result):
    findings=[]
    if result.get('overdue'):findings.append({'kind':'MISSED_CADENCE'})
    for item in result.get('results',[]):
        if item['status'] not in ('COMPLETED','UNCHANGED'):
            findings.append({'kind':item['status'],'control_id':item['control_id']})
        elif item.get('assurance_status')=='UNRESOLVED' or item.get('unresolved_findings',0):
            findings.append({'kind':'INTERPRETATION_UNRESOLVED','control_id':item['control_id']})
    return findings


def terminate_tree(process):
    """Stop only this dispatch's descendants, including new-session model workers."""
    def identity(pid):
        try:
            fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            return int(fields[1]),fields[19]
        except (OSError,ValueError,IndexError):return None
    root=identity(process.pid)
    if root is None:return []
    tracked={process.pid:root[1]}
    # Freeze parents before discovering children again; a child created during
    # the first scan is captured before any frozen parent is terminated.
    while True:
        for pid,start in list(tracked.items()):
            current=identity(pid)
            if current and current[1]==start:
                try:os.kill(pid,signal.SIGSTOP)
                except ProcessLookupError:pass
        added=False
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():continue
            pid=int(path.name);current=identity(pid)
            if current and current[0] in tracked and pid not in tracked:
                tracked[pid]=current[1];added=True
        if not added:break
    for pid,start in reversed(list(tracked.items())):
        current=identity(pid)
        if current and current[1]==start:
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
    process.wait();return sorted(tracked)


def bounded_process(argv,directory,timeout):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();reason=None;terminated=[]
    with (directory/'stdout.json').open('wb') as stdout,(directory/'stderr.log').open('wb') as stderr:
        process=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True,
                                 env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'})
        save(directory/'reservation.json',{'argv':argv,'pid':process.pid,'status':'DISPATCHED','at_ns':str(time.time_ns())})
        try:
            while process.poll() is None:
                if time.monotonic()-started>timeout:reason='TICK_TIMEOUT';break
                if any(p.stat().st_size>16000000 for p in (directory/'stdout.json',directory/'stderr.log')):
                    reason='OUTPUT_LIMIT';break
                try:process.wait(timeout=.2)
                except subprocess.TimeoutExpired:pass
        finally:
            if process.poll() is None:terminated=terminate_tree(process)
    record={'exit_code':process.returncode,'reason':reason,'wall_seconds':str(time.monotonic()-started),
            'terminated_dispatch_pids':terminated,
            'status':'RETURNED' if process.returncode==0 and reason is None else 'FAILED'}
    if any(p.stat().st_size>16000000 for p in (directory/'stdout.json',directory/'stderr.log')):
        record.update(status='FAILED',reason='OUTPUT_LIMIT')
    if record['status']=='RETURNED':
        try:
            result=loads((directory/'stdout.json').read_bytes())
            if result.get('release_eligible') is not False:raise LegalMathError('E_AUTHORITY')
            record['result']=result
        except (ValueError,LegalMathError):record.update(status='FAILED',reason='INVALID_MONITOR_RESULT')
    save(directory/'result.json',record);return record


def execute(args):
    timestamp(args.at)
    if (type(args.ticks)is not int or not 1<=args.ticks<=100 or type(args.interval_seconds)is not int
            or not 0<=args.interval_seconds<=604800 or not 1<=args.tick_timeout_seconds<=7200):
        raise LegalMathError('E_RESOURCE_LIMIT')
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True);results=[]
    with (out/'.scheduler.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise LegalMathError('E_JOB_STATE')
        for index in range(args.ticks):
            sequence=len(list((out/'dispatches').glob('*')))
            directory=out/'dispatches'/f'tick-{sequence:06}'
            try:
                registry=snapshot_registry(args.config,out/'registries',args.resource_root)
                retained,inputs=snapshot_dispatch_inputs(args,out/'dispatch-inputs')
                argv=command(retained,registry['config'],out/'runtime')
                result=bounded_process(argv,directory,args.tick_timeout_seconds)
                result['registry']=registry;result['inputs']=inputs
                result['attention']=attention(result['result']) if result['status']=='RETURNED' else []
            except (LegalMathError,OSError,ValueError) as exc:
                result={'status':'REGISTRY_OR_DISPATCH_FAILED','error':getattr(exc,'code',type(exc).__name__),
                        'details':str(exc)[:500],'release_eligible':False}
                save(directory/'result.json',result)
            result['event_hash']=immutable(out/'events',result);results.append(result)
            if index+1<args.ticks:
                # Interruptible by normal SIGINT/SIGTERM; no daemon installation.
                until=time.monotonic()+args.interval_seconds
                while time.monotonic()<until:time.sleep(min(1.,until-time.monotonic()))
    status=('SCHEDULE_HAS_FAILURES' if any(r['status']!='RETURNED' for r in results) else
            'SCHEDULE_REQUIRES_ATTENTION' if any(r.get('attention') for r in results) else 'BOUNDED_SCHEDULE_COMPLETED')
    return {'status':status,
            'ticks':results,'release_eligible':False,
            'institution_deployment_accepted':False}
