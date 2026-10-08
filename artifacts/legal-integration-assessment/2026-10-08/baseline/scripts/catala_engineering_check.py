#!/usr/bin/env python3
"""Retain bounded envelope checks, frozen replay and one final regression."""
import argparse
import gzip
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.translation.pipeline import build,execute,execute_all,verify_build
from legalmath.translation.verification import verify_execution,verify_executions
from legalmath.translation.resources import preflight
from tests.translation.support import AT,snapshot
from tests.translation.v2_support import fixture_v2,as_model
from tests.catala.backend_support import JDK,TOOLCHAIN

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/catala/engineering-closure'
DOCS=ROOT/'docs/implementation/catala/engineering-closure'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def source_hashes():
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','src','tests','scripts','pyproject.toml'],cwd=ROOT,text=True).splitlines()
    return {p:raw_digest((ROOT/p).read_bytes()) for p in sorted(set(paths))}


def manifest(started,artifacts,source):
    return {'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_hashes':source,'working_tree':'Exact source files identified by hashes',
            'command':[sys.executable,*sys.argv],'environment':{'python':sys.version,'executable':sys.executable,
                'PYTHONPATH':os.environ.get('PYTHONPATH'),'jdk':str(JDK),'catala':{k:str(v) for k,v in TOOLCHAIN.items()},
                'trace_lock_sha256':raw_digest((DOCS/'trace-toolchain.json').read_bytes())},
            'cpu_gpu':'CPU only; no GPU libraries imported','seeds':'N/A; deterministic engineering checks',
            'wall_milliseconds':round((time.monotonic()-started)*1000),
            'plan':'docs/plans/catala-engineering-closure.md','result':'docs/implementation/catala/engineering-closure/results.md',
            'artifacts':artifacts}


def envelope():
    from legalmath.catala.native import runtime
    started=time.monotonic();source=source_hashes();rows=[]
    for count in (1,8,20,40):
        m=as_model(*fixture_v2([('x','integer')],
            [('out'+str(i),'integer','true','(+ x (integer '+str(i)+'))') for i in range(count)],
            text='Synthetic resource calculation: output i adds i to the observed integer x.'))
        report=preflight(m)
        if not report['supported']:raise AssertionError(report)
        out=OUT/'builds'/('outputs-'+str(count));build(m,'catala',out,JDK,catala_toolchain=TOOLCHAIN)
        s=snapshot(m,{'x':'7'});metrics=[];original=runtime.run_command

        def measured(command,cwd,**kwargs):
            if not str(command[0]).endswith('/bin/java'):return original(command,cwd,**kwargs)
            with tempfile.TemporaryDirectory(prefix='catala-rss-') as temp:
                usage=Path(temp)/'rss';before=time.monotonic()
                value=original(['/usr/bin/time','-f','%M','-o',usage,*command],cwd,**kwargs)
                metrics.append({'wall_microseconds':round((time.monotonic()-before)*1e6),
                                'peak_rss_kib':int(usage.read_text().strip())})
                return value

        runtime.run_command=measured
        try:
            before=time.monotonic();result=execute_all(out,s,AT,AT,JDK)
            batch_wall=round((time.monotonic()-before)*1e6)
            if len(metrics)!=1:raise AssertionError('Batch did not execute exactly once')
            batch_metric=metrics[:];metrics.clear();before=time.monotonic()
            for rule in m['rules']:
                if execute(out,s,rule['id'],AT,AT,JDK)!=result['results'][rule['id']]:
                    raise AssertionError('Batch and individual result differ')
            individual_wall=round((time.monotonic()-before)*1e6)
        finally:runtime.run_command=original
        expected={'out'+str(i):{'status':'VALUE','value':str(7+i)} for i in range(count)}
        checks=verify_executions(out,s,result,expected,JDK,compiler=TOOLCHAIN['compiler'])
        row={'outputs':count,'preflight':report,'snapshot':s,'expected':expected,'result':result,'checks':checks,
             'batch':{'calls':len(batch_metric),'total_wall_microseconds':batch_wall,'jvm':batch_metric},
             'individual':{'calls':len(metrics),'total_wall_microseconds':individual_wall,'jvm':metrics},
             'build':str(out.relative_to(ROOT))}
        packed=OUT/('outputs-'+str(count)+'.json.gz');packed.write_bytes(gzip.compress(canonical(row),mtime=0))
        rows.append({k:row[k] for k in ('outputs','preflight','batch','individual','build')})
        rows[-1].update(artifact=str(packed.relative_to(ROOT)),sha256=raw_digest(packed.read_bytes()))
    if source_hashes()!=source:raise AssertionError('Source changed during envelope checks')
    report={'passed':True,'rows':rows,'interpretation':'Exact engineering checks; timings and peak RSS descriptive only',
            'data_hash':digest([r['outputs'] for r in rows]),'manifest':manifest(started,[r['artifact'] for r in rows],source)}
    write(OUT/'envelope.json',report)
    print(canonical({'passed':True,'output_counts':[r['outputs'] for r in rows]}).decode())


def replay():
    started=time.monotonic();source=source_hashes();records=[];builds={}
    base=ROOT/'artifacts/catala/modular-translation'
    for path in sorted(base.glob('*/results.json')):
        name=path.parent.name
        for row in loads(path.read_bytes()):
            if name=='rich':
                pairs={'catala':row['result']};s=loads((path.parent/'reference-snapshot.json').read_bytes())
                expected={k:row['result'][k] for k in ('status','value')}
            else:pairs=row['results'];s=row['snapshot'];expected=row['expected']
            for target,old in pairs.items():
                directory=path.parent if name=='rich' else path.parent/target
                _,_,b=verify_build(directory);builds[str(directory.relative_to(ROOT))]=digest(b)
                result=execute(directory,s,old['rule_id'],old['valid_at'],old['known_at'],JDK)
                if result!=old:raise AssertionError('Frozen version-1 result changed')
                checked=verify_execution(directory,s,result,expected,JDK,compiler=TOOLCHAIN['compiler'])
                records.append({'version':'1','target':target,'build_hash':digest(b),'result_hash':digest(result),'checks':checked})
    retained=ROOT/'artifacts/catala/translator-completion'
    index=loads((retained/'validation.json').read_bytes())['builds']
    for row in loads(gzip.decompress((retained/'checks.json.gz').read_bytes())):
        directory=ROOT/index[row['model_hash']]['path'];old=row['result']
        _,_,b=verify_build(directory);builds[str(directory.relative_to(ROOT))]=digest(b)
        result=execute(directory,row['snapshot'],row['rule_id'],old['valid_at'],old['known_at'],JDK)
        if result!=old:raise AssertionError('Frozen version-2 result changed')
        checks=verify_execution(directory,row['snapshot'],result,row['expected'],JDK,compiler=TOOLCHAIN['compiler'])
        records.append({'version':'2','target':'catala','build_hash':digest(b),'result_hash':digest(result),'checks':checks})
    if source_hashes()!=source:raise AssertionError('Source changed during frozen replay')
    if not records or not any(r['version']=='2' for r in records):raise AssertionError('Frozen corpus missing')
    report={'passed':True,'builds':builds,'records':records,
            'data_hash':digest({str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in [*base.glob('*/results.json'),retained/'checks.json.gz']}),
            'manifest':manifest(started,['artifacts/catala/engineering-closure/replay.json'],source)}
    write(OUT/'replay.json',report)
    print(canonical({'passed':True,'checks':len(records),'builds':len(builds)}).decode())


def regression():
    started=time.monotonic();source=source_hashes()
    log=OUT/'regression.log';junit=OUT/'regression.xml'
    command=[sys.executable,'-m','pytest','-q','--basetemp='+str(OUT/'regression-work'),
             '--junitxml='+str(junit),'--hypothesis-seed=20260928','-o','faulthandler_timeout=90']
    with log.open('wb') as stream:
        run=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
    cases=ET.parse(junit).getroot().findall('.//testcase') if junit.exists() else []
    unchanged=source_hashes()==source
    passed=run.returncode==0 and bool(cases) and unchanged and all(c.find('failure') is None and c.find('error') is None for c in cases)
    report={'passed':passed,'exit_code':run.returncode,'source_unchanged':unchanged,'tests':len(cases),
        'skipped':sum(c.find('skipped') is not None for c in cases),'test_ids':[c.get('classname','')+'::'+c.get('name','') for c in cases],
        'pytest_command':command,'log_sha256':raw_digest(log.read_bytes()),'junit_sha256':raw_digest(junit.read_bytes()) if junit.exists() else None,
        'data_version':'Repository fixtures identified by source hashes and frozen replay data hash',
        'manifest':manifest(started,[str(log.relative_to(ROOT)),str(junit.relative_to(ROOT))],source)}
    report['manifest']['seeds']={'hypothesis':20260928,'comparison':'N/A; regression, not a stochastic method ranking'}
    write(OUT/'regression.json',report)
    print(canonical({k:report[k] for k in ('passed','exit_code','source_unchanged','tests','skipped')}).decode())
    if not passed:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['envelope','replay','regression']);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    {'envelope':envelope,'replay':replay,'regression':regression}[args.action]()
