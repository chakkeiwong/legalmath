"""Bounded, resumable local assurance work; never dispatches a model/provider."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from resolution_support import read, save, sha, LEDGER
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal

OUT = ROOT/'artifacts/interpretation/round16'
OLD = ROOT/'artifacts/interpretation/round15'
PLAN = ROOT/'docs/plans/assurance-round16-execution.md'
PHASES = ['N0', 'N1', 'N2', 'N3', 'N4', 'N5']


def code_binding():
    paths = [p for folder in ('src', 'tests') for p in (ROOT/folder).rglob('*')
             if p.is_file() and p.suffix in ('.py','.java','.json') and '__pycache__' not in p.parts]
    paths += [Path(__file__), ROOT/'scripts/assurance_round16_checks.py',
              ROOT/'scripts/assurance_round15_witnesses.py', ROOT/'scripts/resolution_support.py',
              PLAN, ROOT/'docs/implementation/interpretation-round16/plan-review.md',
              ROOT/'docs/implementation/interpretation-round16/allowlist.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}


def audit():
    b = read(OUT/'baseline.json'); m = read(OLD/'delivery-manifest.json')
    if sha(OLD/'delivery-manifest.json') != b['predecessor_manifest_sha256']:
        raise LegalMathError('E_INTEGRITY')
    for name, h in m['files'].items():
        if sha(OLD/name) != h:
            raise LegalMathError('E_INTEGRITY', details=name)
    if m['external_files'] != b['predecessor_external_files']:
        raise LegalMathError('E_INTEGRITY')
    for name, h in m['external_files'].items():
        if sha(OUT/'predecessor-external'/name) != h:
            raise LegalMathError('E_INTEGRITY', details=name)
    for name, h in b['manuscript_files'].items():
        if sha(OUT/'manuscript-baseline'/name) != h:
            raise LegalMathError('E_INTEGRITY', details=name)
    if sha(LEDGER) != b['ledger_sha256'] or read(LEDGER) != b['ledger']:
        raise LegalMathError('E_INTEGRITY', details='Shared allowance changed; this local round authorizes no calls')
    if len(b['ledger']['calls']) != 500 or b['ledger']['maximum'] != 500:
        raise LegalMathError('E_RESOURCE_LIMIT')
    rows = read(OLD/'remaining-work.json')['restored_pair_rows']
    if len(rows) != 232 or len({(r['case_id'],r['claim_id'],r['candidate_id']) for r in rows}) != 232:
        raise LegalMathError('E_INTEGRITY')
    if sha(PLAN) != b['plan_sha256']:
        raise LegalMathError('E_STALE_REVIEW', details='Execution plan changed after baseline capture')
    return {'status':'BASELINE_VERIFIED','prior_files':len(m['files']),'archived_external_files':len(m['external_files']),
            'restored_pairs':232,'live_calls_used':500,'live_calls_authorized_this_round':0,'release_eligible':False}


def journal():
    return EvidenceJournal(OUT/'execution', {'baseline_sha256':sha(OUT/'baseline.json'), 'plan_sha256':sha(PLAN)},
                           maximum_actions=18, maximum_per_issue=3, deadline_seconds=21600)


def phase_inputs(phase, preceding):
    return {'phase':phase,'implementation':code_binding(),'preceding':deepcopy(preceding),
            'remaining_work_sha256':sha(OLD/'remaining-work.json'),'ledger_sha256':sha(LEDGER)}


def run_phase(phase, work):
    started=time.monotonic();before=code_binding()
    command=[str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/assurance_round16_checks.py'),phase,str(work)]
    manifest={'phase':phase,'command':command,'plan':str(PLAN.relative_to(ROOT)),
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'python':sys.version,'environment':str(ROOT/'.venv'),'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1',
        'seeds':'N/A: deterministic checks; property tests retain their existing configuration',
        'data_version':sha(OLD/'remaining-work.json'),'implementation':before,
        'started_at':datetime.now(timezone.utc).isoformat(),'release_eligible':False}
    if phase=='N0':
        output=audit();status='PASS';command=[]
    else:
        with (work/'phase.log').open('w') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1'})
            try:
                code=process.wait(timeout=1900 if phase=='N5' else 1200)
                status='PASS' if code==0 else 'FAILED'
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                code=None;status='TIMEOUT'
        output=read(work/'phase-output.json') if (work/'phase-output.json').exists() else None
        manifest['exit_code']=code
        if status=='PASS' and output is None:status='MISSING_OUTPUT'
    manifest.update(command=command,wall_seconds=time.monotonic()-started,
                    finished_at=datetime.now(timezone.utc).isoformat(),code_unchanged=before==code_binding())
    if not manifest['code_unchanged']:status='STALE_CODE'
    return {'status':status,'output':output,'manifest':manifest}


def refresh(results, failure=None):
    completed=[p for p in PHASES if p in results and results[p]['result']['status']=='PASS']
    remaining=[p for p in PHASES if p not in completed]
    pending=read(OLD/'remaining-work.json')
    value={'completed_phases':completed,'remaining_phases':remaining,'repair_required':failure,
        'next_phase':remaining[0] if remaining else 'DOCUMENTS_AND_DELIVERY_REVIEW',
        'phase_result_hashes':{p:r['receipt']['result_hash'] for p,r in results.items()},
        'unresolved':{'restored_pairs':232,'new_scoped_judgments':0,'legacy_pending_pairs':91,
                      'legacy_unencoded_pair':1,'retained_parents':len(pending['parents']),
                      'pdf_materiality_pending':len(pending['pdf_pending_ids']),
                      'authority_questions':len(pending['authority_questions'])},
        'model_calls_available':0,'independent_legal_accuracy_estimate':False,'release_eligible':False}
    save(OUT/'phase-results.json',results);save(OUT/'next-phase-plan.json',value)
    return value


def execute(through='N5'):
    audit();j=journal();results={};preceding=[]
    for phase in PHASES[:PHASES.index(through)+1]:
        inputs=phase_inputs(phase,preceding)
        try:
            result,receipt=j.execute(phase.lower(),inputs,lambda work:run_phase(phase,work),
                dependencies=deepcopy(preceding),issue=phase.lower(),retry_if=lambda r:r['status']!='PASS')
        except LegalMathError as e:
            refresh(results,{'phase':phase,'code':e.code,'details':e.details});raise
        results[phase]={'result':result,'receipt':receipt}
        if result['status']!='PASS':
            refresh(results,{'phase':phase,'status':result['status'],
                             'action_sequence':receipt['sequence'],'instruction':'Inspect preserved log, repair, then resume; no budget reset.'})
            raise LegalMathError('E_INTEGRITY',details=f'{phase} failed; repair details in next-phase-plan.json')
        preceding.append(receipt['result_hash']);refresh(results)
    return {'status':'LOCAL_PHASES_EXECUTED' if through=='N5' else 'CHECKPOINT',
            'completed':list(results),'new_model_calls':0,'release_eligible':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['audit','execute','repair','status'])
    parser.add_argument('--through',choices=PHASES,default='N5');args=parser.parse_args()
    if args.action=='audit':value=audit()
    elif args.action=='status':value={'journal':journal().report(),'next':read(OUT/'next-phase-plan.json') if (OUT/'next-phase-plan.json').exists() else None}
    else:value=execute(args.through)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
