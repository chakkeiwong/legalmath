#!/usr/bin/env python3
"""Fixed round-14 executor with audited repair lineage and immutable attempts."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from resolution_support import *
from legalmath.interpretation.assurance.workflow import EvidenceJournal

PHASES=tuple('R'+str(i) for i in range(8))
PLAN=ROOT/'docs/plans/assurance-round14-execution.md'
REPAIR=DOC/'repair-review.md'
EXECUTION=OUT/'execution-reviewed'

def binding(phase):
    files=[PLAN,REPAIR,ROOT/'scripts/run_resolution_master.py',ROOT/'scripts/resolution_support.py',
           ROOT/'scripts/resolution_routes.py',DOC/'allowlist.json']
    module={'R1':'sources','R3':'live','R4':'pdf','R5':'new','R6':'verify','R7':'documents'}.get(phase)
    if module:files.append(ROOT/('scripts/resolution_'+module+'.py'))
    if phase in ('R2','R3','R4','R5','R6'):
        files += list(ROOT.glob('src/legalmath/**/*.py'))+list(ROOT.glob('src/legalmath/**/*.java'))+list(ROOT.glob('src/legalmath/schemas/*.json'))
    if phase in ('R2','R6'):files+=list(ROOT.glob('tests/**/*.py'))
    if phase in ('R1','R3','R5'):
        files+=list((OUT/'sources-official').glob('*'))
    if phase=='R7':
        # This phase generates its new prose unit from the frozen results.
        files += [p for p in ROOT.glob('docs/monograph/chapters/*.tex') if p.name not in ('06-ensemble.tex','06d-invariant-decisions.tex')]
        files += [ROOT/'docs/monograph/references.bib',ROOT/'scripts/resolution_citations.py',
                  ROOT/'docs/papers/monograph-citation-archive.json']+list(ROOT.glob('scripts/*monograph*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files)) if p.is_file()}

def vectors(phase,work):
    pytest=[str(PY),'-m','pytest']
    route=[str(PY),str(ROOT/'scripts/resolution_routes.py'),phase,'--out',str(work/'evidence')]
    if phase=='R2':return [('focused',pytest+['tests/assurance/test_invariant_decisions.py','tests/assurance/test_resolution_round14.py','-q','--junitxml='+str(work/'tests.xml')])]
    if phase=='R6':return [('independent',route),('regression',pytest+['tests','-q','--junitxml='+str(work/'tests.xml')])]
    return [('phase',route)]

def audit():
    base=baseline();grant=read(LEDGER);prefix=base['ledger_prefix']
    if grant['maximum']!=500 or grant['calls'][:len(prefix['calls'])]!=prefix['calls'] or used()>500:
        raise LegalMathError('E_INTEGRITY',details='Shared allowance history changed')
    if read(DOC/'allowlist.json')['absolute_model_ceiling']!=CEILING:raise LegalMathError('E_RESOURCE_LIMIT')
    repair=read(DOC/'repair-checkpoint.json')
    for path,h in repair['rejected_journals'].items():
        if sha(ROOT/path)!=h:raise LegalMathError('E_INTEGRITY',details='Rejected evidence changed: '+path)
    if grant['calls'][:len(repair['ledger_calls'])]!=repair['ledger_calls']:
        raise LegalMathError('E_INTEGRITY',details='Rejected calls were refunded or changed')
    value={'status':'AUDITED_REPAIR','plan_sha256':sha(PLAN),'repair_review_sha256':sha(REPAIR),
           'baseline_sha256':sha(DOC/'baseline.json'),'calls':used(),'ceiling':CEILING,
           'phase_bindings':{p:binding(p) for p in PHASES},'release_eligible':False}
    save(OUT/'audit-reviewed.json',value);return value

def execute(through,start='R0'):
    audit()
    journal=EvidenceJournal(EXECUTION,{'program':'round14.reviewed.v2','baseline':sha(DOC/'baseline.json'),
        'repair_checkpoint':sha(DOC/'repair-checkpoint.json'),'ceiling':CEILING},
        maximum_actions=24,maximum_per_issue=3,deadline_seconds=28800)
    results={};dependencies=[]
    if start!='R0':
        # A continuation validates the immutable journal and exact current code,
        # never trusts a path or hash copied into a mutable summary alone.
        actions=journal.report()['actions']; retained=read(OUT/'phase-results.json')
        for phase in PHASES[:PHASES.index(start)]:
            r=retained[phase];a=next((a for a in actions if a['sequence']==r['receipt']['sequence']),None)
            if not a or a['status']!='EXECUTED' or a['result_hash']!=r['receipt']['result_hash']:
                raise LegalMathError('E_INTEGRITY')
            manifest=read(EXECUTION/a['result_file'])
            if manifest!=r['manifest'] or manifest['inputs']!={'implementation':binding(phase),'dependencies':list(dependencies)}:
                raise LegalMathError('E_STALE_REVIEW',details='Predecessor changed: '+phase)
            results[phase]=r;dependencies.append(a['result_hash'])
    for phase in PHASES[PHASES.index(start):PHASES.index(through)+1]:
        inputs={'implementation':binding(phase),'dependencies':list(dependencies)}
        save(OUT/'next-phase-plan.json',{'phase':phase,'inputs':inputs,'preceding_findings':
            {p:r['manifest'].get('findings',r['manifest'].get('tests')) for p,r in results.items()},
            'remaining_authorized_calls':500-used(),'remaining_increment_calls':max(0,CEILING-used()),
            'commands':vectors(phase,OUT/'planned'),'release_eligible':False})
        def perform(work):
            began=time.monotonic();manifest={'phase':phase,'inputs':inputs,'commands':[],
                'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'python':str(PY),'CPU_GPU':'CPU; CUDA_VISIBLE_DEVICES=-1',
                'seeds':'N/A; provider randomness not controlled','data_version':sha(DOC/'baseline.json'),
                'plan':str(PLAN.relative_to(ROOT)),'repair':str(REPAIR.relative_to(ROOT)),'calls_before':used()}
            save(work/'started.json',manifest)
            for label,cmd in vectors(phase,work):
                with (work/(label+'.log')).open('w') as log:
                    process=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
                        'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1'},stdout=log,stderr=subprocess.STDOUT,
                        timeout=21600 if phase in ('R3','R5') else 1800)
                manifest['commands'].append({'argv':cmd,'exit_code':process.returncode,'log':str(work/(label+'.log'))})
                save(work/'progress.json',manifest)
                if process.returncode:raise LegalMathError('E_DEPENDENCY',details='Inspect '+str(work/(label+'.log')))
            if phase in ('R2','R6'):
                suites=ET.parse(work/'tests.xml').getroot()
                manifest['tests']={k:sum(int(s.get(k,0)) for s in suites.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
                if any(manifest['tests'][k] for k in ('failures','errors','skipped')):
                    raise LegalMathError('E_DEPENDENCY',details='Regression incomplete or failed')
            if phase!='R2':
                path=work/'evidence/result.json';result=read(path)
                manifest.update(result_path=str(path.relative_to(ROOT)),result_sha256=sha(path))
                manifest['findings']={k:v for k,v in result.items() if k in (
                    'status','execution_complete','counts','unlocated','restored_pairs','exclusion_labels','encoded_children',
                    'unencoded_parents_retained','useful_decision_criterion','source_review_concerns','compiled_candidates',
                    'reference_case_count','comparisons','pages','unmet_dependencies','stopped_reason')}
            if inputs['implementation']!=binding(phase):
                raise LegalMathError('E_STALE_REVIEW',details='Phase inputs changed during execution')
            manifest.update(wall_seconds=time.monotonic()-began,calls_after=used(),status='EXECUTED',release_eligible=False)
            return manifest
        manifest,receipt=journal.execute('phase.'+phase.lower(),inputs,perform,dependencies=dependencies,issue=phase)
        directory=EXECUTION/('action-'+str(receipt['sequence']).zfill(4))/'evidence'
        results[phase]={'manifest':manifest,'receipt':receipt,'directory':str(directory.relative_to(ROOT))}
        save(OUT/'phase-results.json',results);dependencies.append(receipt['result_hash'])
        print(phase+' EXECUTED'+(' (reused)' if receipt['reused'] else ''),flush=True)
    if through!='R7':return {'status':'CHECKPOINT','through':through}
    fresh=read(ROOT/results['R5']['manifest']['result_path']);live=read(ROOT/results['R3']['manifest']['result_path'])
    status='ENGINEERING_PASSED_WITH_RETAINED_SOURCE_UNCERTAINTY'
    if not fresh.get('useful_decision_criterion'):status='USEFUL_DECISION_TARGET_NOT_MET'
    if not live.get('execution_complete'):status='LIVE_INVESTIGATION_INCOMPLETE'
    final={'status':status,'phases':results,'calls_before':read(DOC/'baseline.json')['ledger_start'],
           'calls_after':used(),'ceiling':CEILING,'useful_decision_criterion':fresh.get('useful_decision_criterion',False),
           'legal_accuracy_established':False,'release_eligible':False}
    save(OUT/'final-report.json',final)
    remaining={'status':'REFRESHED_FROM_ACTUAL_RESULTS','final_report_sha256':sha(OUT/'final-report.json'),
        'retained_repair_findings':live['exclusion_labels'],'restored_pairs':live['restored_pairs'],
        'unreviewed_exclusions':len(live['unreviewed_exclusions']),
        'source_review_concerns':fresh.get('source_review_concerns'),
        'remaining_authorized_calls':500-used(),'release_eligible':False}
    save(OUT/'next-phase-plan.json',remaining)
    save(OUT/'delivery-manifest.json',{'files':{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*'))
        if p.is_file() and p.name not in ('delivery-manifest.json','.lock')},'release_eligible':False})
    return final

def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=['audit','execute','repair','status'])
    parser.add_argument('--through',choices=PHASES,default='R7');parser.add_argument('--from',dest='start',choices=PHASES,default='R0')
    args=parser.parse_args()
    if PHASES.index(args.start)>PHASES.index(args.through):parser.error('from must precede through')
    if args.command=='audit':value=audit()
    elif args.command=='status':value=read(OUT/'phase-results.json') if (OUT/'phase-results.json').exists() else {}
    else:value=execute(args.through,args.start)
    print(json.dumps(value if args.command=='status' else {'status':value['status']},indent=2))
if __name__=='__main__':main()
