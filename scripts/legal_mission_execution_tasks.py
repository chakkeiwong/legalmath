#!/usr/bin/env python3
"""Fixed local workers for the registered legal mission dependency graph."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import Execution, read, ref, save, safe, verify, require

ARTIFACTS = Path('artifacts/legal-mission-control/2026-10-11/continuous-execution')
CONTRACTS = ('p10-evidence-contract', 'p14-contract', 'gatecoin-contract')


def source_verification(folder):
    mission = read(ROOT/'docs/implementation/legal-mission-control/mission.json')
    questions = {q['id']: q['question'] for q in mission['questions']}
    packet = read(ROOT/'artifacts/legal-interpretation-program/successor-s4/attempt-1/development-inputs.json')['packet']
    units = {u['unit_id']: u['text'] for u in packet['units']}
    context = read(ROOT/'artifacts/assurance-gap-continuation/2026-10-01/authority-context.json')
    units.update({u['unit_id']: u['text'] for u in context['units']})
    checked, ids = [], []
    evidence = []
    for tid in CONTRACTS:
        path = ROOT/ARTIFACTS/'contracts'/(tid+'.json')
        contract = read(path)
        require(contract['task_id'] == tid, 'Wrong source contract')
        require(contract['review_status'] == 'EXECUTOR_REVIEWED_CONDITIONAL', 'Unsupported review status')
        for q in contract['questions']:
            require(questions[q['question_id']] == q['text'], 'Changed original question')
            ids.append(q['question_id'])
        require(contract['answer'] and contract['contrary_reasoning'] and contract['missing_evidence'], 'Incomplete answer contract')
        require(len(contract['acceptance_cases']) >= 3, 'Missing substantive counterexamples')
        for case in contract['acceptance_cases']:
            require(all(case.get(k) for k in ('id','facts','required_reasoning','reject')), 'Incomplete counterexample')
        verify(ROOT, contract['excerpt_reference'])
        excerpt = read(safe(ROOT, contract['excerpt_reference']['path']))
        for source in excerpt['sources']:
            verify(ROOT, source)
        for row in excerpt['excerpts']:
            if 'source' in row:
                verify(ROOT, row['source'])
                text = safe(ROOT, row['source']['path']).read_text()
                # Offsets address the retained projection, including any literal
                # backslash-n characters. Never silently normalize evidence.
                quote = row['quote']
            else:
                text = units[row['unit_id']]
                quote = row['quote']
            require(text[row['start']:row['end']] == quote, 'Source slice mismatch: '+row['locator'])
        locators = {r['locator'] for r in excerpt['excerpts']}
        require(set(contract['support_locators']) <= locators, 'Unknown source support')
        checked.append({'task_id':tid,'questions':contract['questions'],'exact_excerpts':len(excerpt['excerpts']),
                        'counterexamples':len(contract['acceptance_cases'])})
        evidence += [ref(ROOT,path), contract['excerpt_reference']]
    require(sorted(ids) == sorted(questions), 'Missing or duplicated original question')
    check = folder/'source-checks.json'
    save(check, {'status':'PASS','checks':checked,'review_scope':'Source identity, exact quotations, original questions and presence of executor-reviewed reasoning. This validator does not establish legal entailment.'})
    return 'SUCCEEDED', 'All four original questions and exact retained source excerpts verified; conditional reasoning and failure controls retained.', [ref(ROOT,check), *evidence]


def product_regression(folder):
    argv = ['.venv/bin/python','-m','pytest','-q',
        'tests/assurance/test_question_first_successor.py',
        'tests/assurance/test_source_restart.py',
        'tests/assurance/test_integration_repair.py',
        'tests/assurance/test_integration.py',
        'tests/assurance/test_staged_source_review.py',
        '--junitxml='+str(folder/'product-tests.xml')]
    log = folder/'tests.log'
    with log.open('w') as output:
        proc = subprocess.run(argv,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},
                              stdout=output,stderr=subprocess.STDOUT,timeout=800)
    manifest = folder/'test-command.json'
    save(manifest, {'command':argv,'returncode':proc.returncode,'device_policy':'GPU devices intentionally hidden; CPU-only checks.'})
    files = [ref(ROOT,log),ref(ROOT,manifest)]
    if (folder/'product-tests.xml').exists(): files.append(ref(ROOT,folder/'product-tests.xml'))
    return ('SUCCEEDED' if proc.returncode == 0 else 'FAILED'), 'Focused source-restart and product regression exit '+str(proc.returncode)+'.', files


def execution_report(folder):
    execution = Execution()
    view = execution.summary()
    other = {t:r for t,r in view['tasks'].items() if t!='execution-report'}
    require(not any(r['status'] in {'READY','RUNNING','WAITING'} for r in other.values()), 'Independent work remains')
    with execution.locked() as state:
        receipts = {tid:row.get('result') for tid,row in state['tasks'].items() if tid!='execution-report'}
    manifest = folder/'execution-report.json'
    save(manifest, {'recorded_at_utc':datetime.now(timezone.utc).isoformat(), 'tasks':other,
        'receipts':receipts,'blocked':view['blocked'],'recovered':view['recovered'],
        'mission_complete':False,'original_questions_open':4,'original_obligations':46,
        'original_readings':35,'selected_tools_fully_evaluated':0,
        'interpretation':'Graph outputs and blockers are retained. Task completion does not close legal questions or establish tool benefit.'})
    lines = ['# Continuous execution result','',
        'The ready frontier has been executed. Each blocked branch is listed below; independent branches continued.', '',
        '| Item | Result | Finding |','|---|---|---|']
    for tid,row in other.items():
        lines.append('| '+tid+' | '+row['status']+' | '+row['reason'].replace('|','/')+' |')
    lines += ['', 'All four legal questions, 46 obligations and 35 readings remain in the mission register. Six selected tools still require complete answer-level evaluation.','']
    report = folder/'execution-report.md'; report.write_text('\n'.join(lines))
    return 'SUCCEEDED', 'All ready branches executed or concretely blocked; consolidated report retained, mission remains open.', [ref(ROOT,manifest),ref(ROOT,report), *[r for r in receipts.values() if r]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task',choices=['source-verification','product-regression','execution-report'])
    parser.add_argument('--result',required=True)
    args=parser.parse_args()
    output=Path(args.result).resolve()
    require(output.is_relative_to(ROOT/ARTIFACTS), 'Worker output outside registered artifact directory')
    folder=output.parent; folder.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    worker={'source-verification':source_verification,'product-regression':product_regression,'execution-report':execution_report}[args.task]
    status,conclusion,evidence=worker(folder)
    save(output, {'task_id':args.task,'status':status,'conclusion':conclusion,
        'next_action':'Continue every ready independent item; inspect exact blockers in execution status.',
        'evidence':evidence+[ref(ROOT,Path(__file__))], 'wall_seconds':round(time.monotonic()-started,3),
        'nonclaims':['Local verification and program execution do not establish legal correctness or product readiness.']})
    return 0


if __name__=='__main__':
    raise SystemExit(main())
