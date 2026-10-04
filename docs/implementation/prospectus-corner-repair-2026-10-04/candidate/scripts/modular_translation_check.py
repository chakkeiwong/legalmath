#!/usr/bin/env python3
"""Offline paired translation checks on frozen handwritten interpretations.

This measures compiler/runtime agreement, never source interpretation quality.
No provider, model allowance, source fetch, or production host is used.
"""
from pathlib import Path
import subprocess
import sys
import time
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.translation.model import from_reading
from legalmath.translation.native_compat import task as shared_task, snapshot as shared_snapshot
from legalmath.translation.pipeline import build,execute,translate,verify_build
from legalmath.translation.verification import verify_execution
from scripts.catala_reviewer_study import FORMULAS
from tests.catala.backend_support import JDK,TOOLCHAIN
from tests.catala.native.reference import q
from tests.translation.support import rich_model,snapshot,AT

ROOT=Path(__file__).resolve().parents[1]


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def ensure_build(model,target,directory):
    if (directory/'build.json').exists():
        existing,translation,_=verify_build(directory)
        if existing!=model or translation['target']!=target:raise AssertionError('Stale build')
    else:build(model,target,directory,JDK,catala_toolchain=TOOLCHAIN)


def run(out):
    started=time.monotonic()
    packet_path=ROOT/'artifacts/catala/gap-closure/source-review-successor/packet.json'
    packet=loads(packet_path.read_bytes());records=[]
    for row in packet['corpus']:
        native=row['task'];name=native['task_id'].split('.')[-1];task=shared_task(native)
        reading={'local_id':name,'family':'scope','subject':'Selected source control',
                 'statement':task['question'],'distinction':'Frozen handwritten compiler control',
                 'assumptions':[],'questions':[],
                 'citations':[{'unit_id':u['unit_id'],'quote':u['text']} for u in task['packet']['units']],
                 'formalization':{'facts':task['facts'],'types':task['types'],'result_type':task['result_type'],
                                  'scope':'true','result':FORMULAS[name][2]}}
        model=from_reading(reading,task['packet'],task['valid_from'],until=task['valid_until'],
                           profile=task['profile'],bounds=task['bounds'])
        pair={target:translate(model,target) for target in ('ruleir','catala')}
        if pair['ruleir']['model_hash']!=pair['catala']['model_hash'] or pair['ruleir']['interpretation_hash']!=pair['catala']['interpretation_hash']:
            raise AssertionError('Different interpretation commitments')
        for target in pair:ensure_build(model,target,out/name/target)
        cases=[]
        for case in row['cases']:
            s=shared_snapshot(case['snapshot'],model);expected=case['expected'];value=expected['value']['result']
            status=('TRUE' if value else 'FALSE') if type(value)is bool else expected['status']
            results={};checks={}
            for target in pair:
                directory=out/name/target
                result=execute(directory,s,'selected.control',case['snapshot']['valid_at'],case['snapshot']['known_at'],JDK)
                checks[target]=verify_execution(directory,s,result,{'status':status,'value':value},JDK,compiler=TOOLCHAIN['compiler'])
                results[target]=result
            cases.append({'id':case['id'],'snapshot':s,'expected':{'status':status,'value':value},'results':results,'checks':checks})
        write(out/name/'results.json',cases)
        records.append({'task_id':native['task_id'],'source_task_hash':digest(native),
                        'model_hash':digest(model),'interpretation_hash':pair['ruleir']['interpretation_hash'],
                        'policy':model['profile'],'cases':len(cases),'passed_both':len(cases),
                        'result_path':str((out/name/'results.json').relative_to(ROOT)),'result_hash':digest(cases),
                        'source_adjudication':row['adjudication']})
    model=rich_model();directory=out/'rich';ensure_build(model,'catala',directory)
    s=snapshot(model,{'entries':[{'amount':q(1,3),'active':True},{'amount':q(9),'active':False}],
                      'rate':{'present':q(2,3)},'choice':{'case':'Fixed','value':q(7,5)}})
    rich=[]
    for rule,value in [('selected.control',q(1)),('enum',q(7,5)),('optional',{'present':q(1,3)}),
                       ('none',None),('variant',{'case':'Fixed','value':q(2,3)}),('product',q(1,2)),('money','100')]:
        result=execute(directory,s,rule,AT,AT,JDK)
        checks=verify_execution(directory,s,result,{'status':'VALUE','value':value},JDK,compiler=TOOLCHAIN['compiler'])
        rich.append({'rule_id':rule,'result':result,'checks':checks})
    write(directory/'reference-snapshot.json',s);write(directory/'results.json',rich)
    unsupported=translate(model,'ruleir');write(directory/'ruleir-capabilities.json',unsupported)
    if unsupported['status']!='UNSUPPORTED':raise AssertionError('Rich input incorrectly admitted by RuleIR')
    files=sorted((ROOT/'src/legalmath/translation').glob('*.py'))+[ROOT/'scripts/modular_translation_check.py',
        ROOT/'tests/translation/support.py',ROOT/'scripts/catala_reviewer_study.py',
        ROOT/'tests/catala/backend_support.py',ROOT/'tests/catala/native/reference.py',
        ROOT/'src/legalmath/interpretation/search/formal.py',ROOT/'src/legalmath/interpretation/search/models.py',
        ROOT/'src/legalmath/catala/native/cli.py',ROOT/'src/legalmath/cli.py']
    report={'record_type':'ModularTranslationValidation','question':'Do both targets execute one frozen interpretation under the same policy?',
            'evidence':'Deterministic engineering checks; handwritten interpretations; zero model calls',
            'paired':records,'paired_cases':sum(r['cases'] for r in records),'rich_cases':len(rich),
            'rich_ruleir_status':unsupported['status'],'rich_results_hash':digest(rich),'passed':True,
            'not_concluded':['Conversion quality','Universal Catala superiority','Source correctness','Human approval','Production readiness'],
            'manifest':{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                        'working_tree':'Uncommitted refactor identified by source hashes',
                        'source_hashes':{str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in files},
                        'command':[sys.executable,'scripts/modular_translation_check.py'],
                        'environment':{'python':sys.version,'executable':sys.executable,'PYTHONPATH':'src:.',
                                       'jdk':str(JDK),'catala':{k:str(v) for k,v in TOOLCHAIN.items()}},
                        'cpu_gpu':'CPU; no numerical GPU library imported','data_hash':digest(packet),
                        'seeds':'N/A; deterministic','wall_milliseconds':round((time.monotonic()-started)*1000),
                        'plan':'docs/plans/modular-rule-translation.md','result':'docs/implementation/catala/modular-translation/results.md',
                        'artifacts':str(out.relative_to(ROOT))}}
    write(out/'validation.json',report)
    write(ROOT/'docs/implementation/catala/modular-translation/validation.json',report)
    print(canonical({'passed':True,'paired_cases':report['paired_cases'],'rich_cases':len(rich),'wall_milliseconds':report['manifest']['wall_milliseconds']}).decode())


if __name__=='__main__':
    run(ROOT/'artifacts/catala/modular-translation')
