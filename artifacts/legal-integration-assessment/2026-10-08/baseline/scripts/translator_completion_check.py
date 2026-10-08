#!/usr/bin/env python3
"""Replay frozen version-1 builds and retain the version-2 regression evidence."""
import argparse
import gzip
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.translation.pipeline import execute,verify_build
from legalmath.translation.verification import verify_execution
from tests.catala.backend_support import JDK,TOOLCHAIN

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/catala/translator-completion'
DOCS=ROOT/'docs/implementation/catala/translator-completion'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def manifest(command,seconds):
    paths=sorted((ROOT/'src/legalmath/translation').glob('*.py'))+sorted((ROOT/'tests/translation').glob('*.py'))
    paths += [ROOT/'src/legalmath/catala/native/cli.py',Path(__file__).resolve()]
    return {'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'working_tree':'Source checkpoint identified by hashes; edits may be uncommitted at execution',
        'source_hashes':{str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in paths},
        'command':command,'environment':{'python':sys.version,'executable':sys.executable,'PYTHONPATH':'src:.',
            'jdk':str(JDK),'catala':{k:str(v) for k,v in TOOLCHAIN.items()}},
        'cpu_gpu':'CPU; no numerical GPU libraries imported','seeds':'N/A; deterministic checks',
        'wall_milliseconds':round(seconds*1000),'plan':'docs/plans/catala-translator-completion.md',
        'result':'docs/implementation/catala/translator-completion/results.md'}


def baseline():
    started=time.monotonic();base=ROOT/'artifacts/catala/modular-translation';records=[];builds={}
    for path in sorted(base.glob('*/results.json')):
        rows=loads(path.read_bytes());name=path.parent.name
        for row in rows:
            if name=='rich':
                pairs={'catala':row['result']};s=loads((path.parent/'reference-snapshot.json').read_bytes())
                expected={k:row['result'][k] for k in ('status','value')};ident=row['rule_id']
            else:
                pairs=row['results'];s=row['snapshot'];expected=row['expected'];ident=row['id']
            for target,old in pairs.items():
                directory=path.parent if name=='rich' else path.parent/target
                model,translation,built=verify_build(directory)
                builds[str(directory.relative_to(ROOT))]=digest(built)
                result=execute(directory,s,old['rule_id'],old['valid_at'],old['known_at'],JDK)
                check=verify_execution(directory,s,result,expected,JDK,compiler=TOOLCHAIN['compiler'])
                if {k:result[k] for k in ('status','value')}!={k:old[k] for k in ('status','value')}:
                    raise AssertionError('Version-1 behavior changed')
                records.append({'id':ident,'target':target,'model_hash':digest(model),'result_hash':digest(result),
                                'baseline':str(path.relative_to(ROOT)),'expected':expected,'checks':check})
    report={'record_type':'TranslatorCompletionBaseline','passed':True,'builds':builds,'records':records,
            'paired_cases':sum(r['target']=='ruleir' for r in records),'rich_cases':sum(r['baseline'].endswith('/rich/results.json') for r in records),
            'manifest':manifest([sys.executable,'scripts/translator_completion_check.py','baseline'],round(time.monotonic()-started,3))}
    report['manifest']['data_hash']=digest({str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in base.glob('*/results.json')})
    report['manifest']['artifacts']=['artifacts/catala/translator-completion/baseline.json']
    write(OUT/'baseline.json',report)
    print(canonical({'passed':True,'paired_cases':report['paired_cases'],'rich_cases':report['rich_cases'],'builds':len(builds)}).decode())


def retain(args):
    root=Path(args.pytest_root).resolve();junit=Path(args.junit).resolve();log=Path(args.log).resolve()
    suites=ET.parse(junit).getroot();cases=suites.findall('.//testcase')
    if not cases or any(c.find('failure') is not None or c.find('error') is not None for c in cases):
        raise AssertionError('Regression did not pass')
    checks=[loads(p.read_bytes()) for p in sorted(root.glob('**/checks/*.json'))]
    if not checks: raise AssertionError('Missing exact execution records')
    if (OUT/'builds').exists(): raise AssertionError('Retained build directory already exists; use a fresh task run')
    identities={};required={c['model_hash'] for c in checks}
    for model_path in sorted(root.glob('**/model.json')):
        source=model_path.parent
        if not (source/'build.json').is_file(): continue
        model=loads(model_path.read_bytes());key=digest(model)
        if key not in required or key in identities: continue
        target=OUT/'builds'/key[:16];shutil.copytree(source,target)
        _,_,built=verify_build(target);identities[key]={'path':str(target.relative_to(ROOT)),'build_hash':digest(built)}
    if set(identities)!=required: raise AssertionError('An exact check has no retained build')
    packed=OUT/'checks.json.gz';packed.write_bytes(gzip.compress(canonical(checks),mtime=0))
    seconds=sum(float(s.get('time','0')) for s in suites.findall('.//testsuite'))
    full_source=loads((OUT/'regression-source.json').read_bytes())
    report={'record_type':'TranslatorCompletionValidation','passed':True,
        'tests':len(cases),'skipped':sum(c.find('skipped') is not None for c in cases),
        'exact_checks':len(checks),'builds':identities,'checks_sha256':raw_digest(packed.read_bytes()),
        'junit_sha256':raw_digest(junit.read_bytes()),'log_sha256':raw_digest(log.read_bytes()),
        'baseline_sha256':raw_digest((OUT/'baseline.json').read_bytes()),
        'test_ids':[c.get('classname','')+'::'+c.get('name','') for c in cases],
        'full_regression_source':full_source,
        'manifest':manifest(args.command,round(seconds,3)),
        'not_concluded':['Full Catala language coverage','Source interpretation quality','Universal target superiority','Production readiness']}
    if args.followup_junit:
        followup=Path(args.followup_junit).resolve();followlog=Path(args.followup_log).resolve()
        more=ET.parse(followup).getroot().findall('.//testcase')
        if not more or any(c.find('failure') is not None or c.find('error') is not None for c in more):
            raise AssertionError('Final focused checks did not pass')
        report['followup']={'tests':len(more),'command':args.followup_command,
            'junit':str(followup.relative_to(ROOT)),'junit_sha256':raw_digest(followup.read_bytes()),
            'log':str(followlog.relative_to(ROOT)),'log_sha256':raw_digest(followlog.read_bytes()),
            'test_ids':[c.get('classname','')+'::'+c.get('name','') for c in more],
            'source_hashes':report['manifest']['source_hashes']}
        report['unique_tests']=len(set(report['test_ids'])|set(report['followup']['test_ids']))
    repair_xml=OUT/'final-focused.xml';repair_log=OUT/'final-focused.log'
    if repair_xml.is_file():
        repair=ET.parse(repair_xml).getroot().findall('.//testcase')
        if any(c.find('failure') is not None or c.find('error') is not None for c in repair):
            raise AssertionError('Repair regression failed')
        ids=[c.get('classname','')+'::'+c.get('name','') for c in repair]
        report['repair_regression']={'tests':len(repair),'test_ids':ids,
            'command':'timeout 360 env PYTHONPATH=src:. '+sys.executable+' -m pytest -q tests/translation --basetemp=artifacts/catala/translator-completion/regression-work2 --junitxml=artifacts/catala/translator-completion/final-focused.xml -o faulthandler_timeout=90 > artifacts/catala/translator-completion/final-focused.log 2>&1',
            'junit_sha256':raw_digest(repair_xml.read_bytes()),'log_sha256':raw_digest(repair_log.read_bytes()),
            'source':loads((OUT/'repair-source.json').read_bytes())}
        report['unique_tests']=len(set(report['test_ids'])|set(ids)|set(report.get('followup',{}).get('test_ids',[])))
    report['manifest'].update(data_hash=digest([{'snapshot':c['snapshot'],'expected':c['expected']} for c in checks]),
        artifacts=[str(p.relative_to(ROOT)) for p in (OUT/'builds',packed,junit,log,OUT/'baseline.json')])
    write(OUT/'validation.json',report);write(DOCS/'validation.json',report)
    print(canonical({k:report[k] for k in ('passed','tests','skipped','exact_checks')}).decode())


if __name__=='__main__':
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='action',required=True)
    commands.add_parser('baseline')
    summary=commands.add_parser('retain')
    for name in ('pytest-root','junit','log','command'):summary.add_argument('--'+name,required=True)
    for name in ('followup-junit','followup-log','followup-command'):summary.add_argument('--'+name)
    args=parser.parse_args()
    baseline() if args.action=='baseline' else retain(args)
