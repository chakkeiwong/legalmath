#!/usr/bin/env python3
"""Fixed, resumable round-13 executor. No arbitrary command arguments."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.assurance.diversity import save

OUT = ROOT/'artifacts/interpretation/round13'
DOC = ROOT/'docs/implementation/interpretation-round13'
PLAN = ROOT/'docs/plans/assurance-round13-execution.md'
PY = ROOT/'.venv/bin/python'
LEDGER = ROOT/'artifacts/interpretation/round7/live-allowance.json'
PHASES = ('P0','P1','P2','P3','P4','P5')
EXECUTION = OUT/'execution-reviewed'
CEILING = 400


def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return raw_digest(Path(path).read_bytes())


def binding():
    paths = [*ROOT.glob('src/legalmath/**/*.py'), *ROOT.glob('src/legalmath/**/*.java'),
             *ROOT.glob('src/legalmath/schemas/*.json'), *ROOT.glob('tests/**/*.py'),
             *ROOT.glob('scripts/decision_*.py'), ROOT/'scripts/run_decision_master.py', PLAN,
             *DOC.rglob('*.json'), DOC/'repair-executor.md']
    paths += [OUT/name for name in ('current-code.pdf','eip-predecessor.json','str-chinese.json','code-index.html')]
    paths += [*ROOT.glob('docs/monograph/chapters/*.tex'), *ROOT.glob('docs/monograph/*.tex'),
              ROOT/'docs/monograph/references.bib', *ROOT.glob('scripts/*monograph*.py'),
              ROOT/'docs/papers/monograph-citation-archive.json',
              ROOT/'docs/monograph/review/revision/citation-reading.json',
              ROOT/'docs/monograph/review/reader-facing/citation-occurrence-review.json']
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths)) if p.is_file()}


def commands(phase, out):
    check = [str(PY), '-m', 'pytest']
    route = [str(PY), str(ROOT/'scripts/decision_routes.py')]
    tests = ['tests/assurance/test_decision_controls.py','tests/assurance/test_decision_evidence.py']
    if phase == 'P0': return [('tests', check+tests+['-q','--junitxml='+str(out/'tests.xml')])]
    if phase == 'P1': return [('sources', route+['sources','--out',str(out/'sources')])]
    if phase == 'P2': return [('pdf', route+['pdf','--out',str(out/'pdf')])]
    if phase == 'P3': return [('live', route+['live','--out',str(out/'live')])]
    if phase == 'P4': return [('java', route+['java','--out',str(out/'java')])]
    return [('regression', check+['tests','-q','--junitxml='+str(out/'tests.xml')]),
            ('documents', route+['documents','--out',str(out/'documents')])]


def audit():
    successor = read(ROOT/'artifacts/interpretation/round12/successor-plan.json')
    for row in [successor['starting_evidence']['final_report'], successor['starting_evidence']['evaluation'],
                *successor['starting_evidence']['phase_manifests'].values()]:
        if sha(ROOT/row['path']) != row['sha256']: raise LegalMathError('E_INTEGRITY')
    policy = read(DOC/'allowlist.json')
    if policy['model_allowance']['round13_absolute_ceiling'] != CEILING: raise LegalMathError('E_RESOURCE_LIMIT')
    if not (DOC/'repair-executor.md').exists(): raise LegalMathError('E_REFERENCE')
    if len(read(LEDGER)['calls']) > 500: raise LegalMathError('E_INTEGRITY')
    for phase in PHASES:
        for _, vector in commands(phase, OUT/'audit-work'):
            if vector[0] != str(PY): raise LegalMathError('E_AUTHORITY')
            if vector[1] == '-m':
                if vector[2] != 'pytest' or not all(t in policy['subcommands']['pytest'] for t in vector[3:] if not t.startswith('-')):
                    raise LegalMathError('E_AUTHORITY')
            elif vector[1] != str(ROOT/'scripts/decision_routes.py'):
                raise LegalMathError('E_AUTHORITY')
    result = {'status':'REVIEWED', 'inputs':binding(), 'previous_final':successor['starting_evidence']['final_report'],
              'ledger_calls':len(read(LEDGER)['calls']), 'ceiling':CEILING,
              'review':'repair-executor.md; full accounting, actual dispatch and binaries, immutable attempts',
              'legal_promotion':False, 'release_eligible':False}
    save(OUT/'execution-audit.json', result)
    return result


def phase_evidence(phase, receipt):
    """Expose substantive findings for the next phase, not merely exit codes."""
    work=EXECUTION/('action-'+str(receipt['sequence']).zfill(4))
    names={'P1':'sources','P2':'pdf','P3':'live','P4':'java','P5':'documents'}
    result={'phase':phase,'action_directory':str(work.relative_to(ROOT)),'release_eligible':False}
    if phase in names:
        path=work/names[phase]/'result.json';value=read(path)
        result.update(result_path=str(path.relative_to(ROOT)),result_sha256=sha(path),status=value['status'])
        if phase=='P1':
            result.update(margin=value['margin'],bilingual_alignments=len(value['bilingual']),
                          priority_status=value['eip']['priority']['status'])
        elif phase=='P2':
            result.update({k:value[k] for k in ('pages','resolved_footer_issues','remaining_issues','checked_relations')})
        elif phase=='P3':
            cases=[]
            for case in value['cases']:
                r=case['result']
                cases.append({'case_id':case['case_id'],'status':r['status'],
                    'execution_complete':r['execution_complete'],
                    'full_pair_count':r['full_pair_count'],
                    'required_pairs':r.get('expected_pairs'),
                    'completed_pairs':r.get('completed_pairs',0),
                    'pending_pairs':r.get('pending_pairs',r.get('unexamined_pairs',0)),
                    'excluded_pairs':len(r.get('excluded_pairs',[])),
                    'label_counts':dict(Counter(x['label'] for x in r.get('checks',[]))),
                    'concern_occurrences':len(r.get('additional_concerns',[])),
                    'stopped_reason':r.get('stopped_reason'),
                    'missing_questions':r.get('missing_questions',[])})
            result.update(cases=cases,lowerings=[{'case_id':r['case_id'],'status':r['status']} for r in value['lowerings']],
                          independent_model_families=value['independent_model_families'],
                          source_correctness_established=False)
        elif phase=='P4':
            result.update(compiled_cases=value['compiled_cases'],cvc5_comparisons=value['independent_comparisons'],
                          original_STR_transfer_cases=value['original_STR_transfer_cases'],
                          independent_legal_reference=False)
        elif phase=='P5':
            result.update(previous_pages=value['previous_pages'],pages=value['pages'],
                          proposal_alias_identical=value['proposal_alias_identical'])
    if phase in ('P0','P5'):
        suites=ET.parse(work/'tests.xml').getroot()
        result['tests']={k:sum(int(s.get(k,0)) for s in suites.iter('testsuite'))
                         for k in ('tests','failures','errors','skipped')}
        if result['tests']['failures'] or result['tests']['errors']:raise LegalMathError('E_DEPENDENCY')
    return result


def execute():
    audit_result = audit()
    previous_journal=EvidenceJournal(OUT/'execution', {'program':'round13.repaired.v1','ledger':str(LEDGER),'ceiling':320},
                              maximum_actions=24, maximum_per_issue=3, deadline_seconds=21600)
    prior_actions=previous_journal.report()['actions']
    journal = EvidenceJournal(EXECUTION, {'program':'round13.completion.v1','ledger':str(LEDGER),'ceiling':CEILING,
                              'previous_journal_sha256':sha(previous_journal.path)},
                              maximum_actions=24, maximum_per_issue=3, deadline_seconds=21600)
    results = {}; dependencies = []; evidence={}
    for phase in PHASES:
        inputs = {'implementation':binding(), 'previous':dependencies}
        save(OUT/'next-phase-plan.json', {'phase':phase, 'inputs':inputs, 'commands':commands(phase,OUT/'planned'),
             'previous_evidence':evidence,'remaining_live_reservations':max(0,CEILING-len(read(LEDGER)['calls'])),
             'acceptance':{'P0':'focused fault checks','P1':'anchored new authority','P2':'actual located structure',
                           'P3':'full input and completed/pending model checks','P4':'actual Java and duty evidence',
                           'P5':'regression and book preservation'}[phase], 'release_eligible':False})
        def perform(work):
            began = time.monotonic()
            manifest = {'phase':phase,'inputs':inputs,'commands':[], 'git_commit':subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'python':str(PY),'cpu_only':True,
                'random_seed':'N/A: deterministic checks; provider randomness not controllable',
                'plan':str(PLAN.relative_to(ROOT)), 'ledger_start':len(read(LEDGER)['calls'])}
            save(work/'started.json', manifest)
            for label, vector in commands(phase,work):
                with (work/(label+'.log')).open('w') as log:
                    proc = subprocess.run(vector,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
                        'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1'},stdout=log,stderr=subprocess.STDOUT,
                        timeout=14400 if phase == 'P3' else 1800)
                manifest['commands'].append({'label':label,'argv':vector,'exit_code':proc.returncode})
                save(work/'progress.json',manifest)
                if proc.returncode: raise LegalMathError('E_DEPENDENCY', details='Failed '+phase+' '+label+'; inspect '+str(work))
            manifest.update(wall_seconds=time.monotonic()-began,ledger_end=len(read(LEDGER)['calls']),
                            status='EXECUTED',release_eligible=False)
            return manifest
        current_actions=journal.report()['actions']
        reusable=any(a['status']=='EXECUTED' and a['spec']['stage']=='phase.'+phase.lower()
                     and a['spec']['inputs']==inputs for a in current_actions)
        if not reusable and sum(a['spec']['issue']==phase for a in prior_actions+current_actions)>=3:
            raise LegalMathError('E_RESOURCE_LIMIT',details='Three phase attempts across both retained journals')
        value,receipt=journal.execute('phase.'+phase.lower(),inputs,perform,dependencies=dependencies,issue=phase)
        results[phase]={'manifest':value,'receipt':receipt}
        evidence[phase]=phase_evidence(phase,receipt)
        dependencies.append(receipt['result_hash'])
        save(OUT/'execution-progress.json',results)
        print(phase+' EXECUTED'+(' (reused)' if receipt['reused'] else ''),flush=True)
    live_complete=all(c['execution_complete'] for c in evidence['P3']['cases'])
    evaluation={'status':'ENGINEERING_CHECKS_PASSED_WITH_SOURCE_UNCERTAINTY' if live_complete else
                'ENGINEERING_CHECKS_PASSED_LIVE_EVIDENCE_INCOMPLETE',
                'evidence':evidence,'live_checks_complete':live_complete,
                'interpretation_settled':False,'independent_accuracy_evaluated':False,
                'calls_before_round':260,'calls_after_round':len(read(LEDGER)['calls']),
                'initial_increment_ceiling':320,'round_call_ceiling':CEILING,'release_eligible':False}
    final={'status':evaluation['status'],'phases':results,
           'ledger_calls':len(read(LEDGER)['calls']), 'ceiling':CEILING,
           'legal_correctness_established':False,'independent_accuracy_evaluated':False,
           'bank_integration':'DEFERRED_BY_USER','release_eligible':False}
    if any(r['manifest']['inputs']['implementation']!=binding() for r in results.values()):
        raise LegalMathError('E_STALE_REVIEW',details='Implementation changed during execution; resume to revalidate affected phases')
    save(OUT/'evaluation.json',evaluation)
    final['evaluation']={'path':str((OUT/'evaluation.json').relative_to(ROOT)),'sha256':sha(OUT/'evaluation.json')}
    save(OUT/'final-report.json',final)
    save(OUT/'next-phase-plan.json',{'status':'FOLLOW_UP_FROM_RESULTS','final_report_sha256':sha(OUT/'final-report.json'),
         'evidence':evidence,
         'requirements':['resolve remaining model/source concerns individually','independent source-family reference adjudication',
                         'second authorized model-family comparison','measured reviewer effort'], 'release_eligible':False})
    save(OUT/'delivery-manifest.json',{'files':{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*'))
         if p.is_file() and p.name not in ('delivery-manifest.json','.lock')},'release_eligible':False})
    return final


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=['audit','execute','repair','live','status'])
    args=parser.parse_args()
    if args.command=='audit': result=audit(); print(result['status'])
    elif args.command == 'live':
        audit()
        from decision_live import run
        run(OUT/'live-dispatch')
    elif args.command in ('execute','repair'):
        if args.command=='repair' and not (DOC/'repair-executor.md').exists(): raise LegalMathError('E_REFERENCE')
        result=execute(); print(result['status'])
    else:
        print(json.dumps(read(OUT/'execution-progress.json') if (OUT/'execution-progress.json').exists() else {}))

if __name__=='__main__':main()
