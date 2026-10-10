"""Verify actual pledge results and retain a bounded completion record."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'basf-status-pledge'
BASELINE='0705bb22af56c2eaafd4f82d3bfeeee6886d65de'
PLAN='docs/plans/prospectus-basf-status-pledge-execution-2026-10-10.md'
NEXT='docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.successor import closure_program

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def identity(p):
    return dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)

def save(p,value):
    p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def changed(method):
    return [p for p,h in method.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]

def suite(name,count,current):
    xml,manifest,log=[BASE/'checks'/(name+s) for s in ('.xml','-manifest.json','.log')]
    row=read(manifest)
    counts={k:sum(int(s.get(k,0)) for s in ET.parse(xml).getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    assert counts==dict(tests=count,failures=0,errors=0,skipped=0)==row['counts']
    assert row['status']=='PASS' and row['method_unchanged'] and row['git_commit']==BASELINE
    assert sha(xml)==row['result_sha256'] and row['wall_seconds']<=row['timeout_seconds']
    drift=changed(row['method'])
    expected=set() if current else {PLAN,'src/legalmath/prospectus/successor/closure_program.py'}
    assert set(drift)==expected,drift
    return dict(xml=identity(xml),manifest=identity(manifest),log=identity(log),counts=counts,
        wall_seconds=row['wall_seconds'],command=row['command'],timeout_seconds=row['timeout_seconds'],
        method_current=current,changed_since_run=drift,
        scope='Current method' if current else 'Successful early diagnostic before reviewed scheduling-only changes')

def exercise(folder):
    result,started,manifest=[read(folder/n) for n in ('result.json','started.json','manifest.json')]
    assert result['status']=='PASS' and result['git_commit']==BASELINE
    assert result['wall_seconds']<=started['timeout_seconds']
    assert result['evidence_payload_bytes']+started['metadata_reserve_bytes']<=started['evidence_limit_bytes']
    assert not changed(result['method'])
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
    assert actual==set(manifest['files'])
    assert all(sha(folder/p)==h for p,h in manifest['files'].items())
    return dict(directory=str(folder.relative_to(ROOT)),manifest=identity(folder/'manifest.json'),
        files_verified=len(actual),result=identity(folder/'result.json'),started=identity(folder/'started.json'),
        method_current=True,actual_commands=result.get('commands',result.get('command')),
        wall_seconds=result['wall_seconds'],evidence_payload_bytes=result['evidence_payload_bytes'],
        limits={k:started[k] for k in ('timeout_seconds','evidence_limit_bytes','metadata_reserve_bytes')},
        environment=result.get('environment',{'python':result.get('python')}),cpu_gpu=result['cpu_gpu'],seeds=result['seeds'])

def main():
    assert not (PACKAGE/'execution-manifest.json').exists()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASELINE
    suites={name:suite(name,count,current) for name,count,current in (
        ('basf-pledge-admission-001',47,False),('basf-pledge-smoke-001',2,False),
        ('basf-pledge-001',23,True),('successor-013',599,True))}
    exercises=[exercise(p) for p in (PACKAGE/'attempt-001',BASE/'installed/attempt-014')]
    consumer,packet=read(PACKAGE/'attempt-001/result.json'),read(PACKAGE/'review.json')
    assert all(sha(ROOT/p)==h for p,h in packet['images'].items())
    outcome=consumer['outcome']
    assert outcome['questions']==dict(Q1='UNKNOWN',Q2='UNKNOWN',Q3='PARTIAL')
    assert outcome['mode']=='ASSISTED' and outcome['independent_legal_review'] is False
    assert outcome['target_occurrences']==[34,30,4,15,15,42]
    assert outcome['status_pledge']['reviewed_units']==32 and len(consumer['matched_omission'])==3
    omissions=[]
    for key,row in consumer['matched_omission'].items():
        assert row['unknown_with_reading']==0 and row['unknown_without_reading']==row['reviewed_nonspace_characters']>0
        assert row['outside_unknown_characters_equal']
        omissions.append(f'| {key} | {row["reviewed_nonspace_characters"]} |')
    missing=consumer['matched_missing_definition']
    assert missing['other_meanings_equal'] and missing['direct_dependencies_equal']
    assert set(missing['question_evidence'])=={'Q1','Q2','Q2.compulsory_common','Q2.possible_common','Q2.common_only'}
    stages=[read(BASE/'installed/attempt-014'/n) for n in ('installed-results.json','relocated-results.json','restored-results.json')]
    assert stages[0]['questions']==stages[1]['questions']==stages[2]['questions']
    assert len(stages[0]['questions'])==9
    status=closure_program.status(ROOT)
    phases=[]
    for row in status['phases']:
        assert row['current'] and row['artifact_valid'] and row['engineering_checks']=='PASS' and row['execution']=='COMPLETED',row
        assert row['primary_criterion']==('PASS' if row['phase']=='R0' else 'PARTIAL')
        folder=ROOT/row['directory']
        started,result=read(folder/'started.json'),read(folder/'result.json')
        assert started['git_commit']==BASELINE and result['wall_seconds']<=started['timeout_seconds']
        assert result['test_counts']['tests']>0 and not any(result['test_counts'][k] for k in ('failures','errors','skipped'))
        phases.append({**row,'test_counts':result['test_counts'],'wall_seconds':result['wall_seconds'],
            'timeout_seconds':started['timeout_seconds'],'actual_test_argv':started['argv'],
            'dispatcher_command':['.venv/bin/python','-m','scripts.prospectus_delivery','--program','closure','phase','--phase',row['phase']],
            'artifacts':[identity(folder/n) for n in ('started.json','result.json','receipt.json','tests.xml','command.log')]})
    next_phase=read(BASE/'next-phase.json')
    assert next_phase['phases']==status['phases'] and next_phase['next_command'] is None
    assert next_phase['program_complete'] is False and len(next_phase['unfinished_capabilities'])==8
    r8=ROOT/status['phases'][-1]['directory']/'attribution.json'
    assert read(r8)==read(BASE/'final-attribution.json')
    phase_text=', '.join(r['phase']+'/'+r['directory'].rsplit('-',1)[-1] for r in phases)
    r4=next(p for p in phases if p['phase']=='R4')
    result=f'''# BASF status and negative pledge: bounded validation complete

The service and fresh, relocated and offline-restored installed CLI preserve
three complete supplied German readings: status, issuer negative pledge and
capital-market-debt definition. All twenty prior meanings, six raw references
and six scalar maps remain equal. The pledge's typed definition edge survives.
The selected issuer text includes its complete security alternative and Fiscal
Agent cutoff; excluded guarantor wording remains excluded. The construction,
fifteen markers, 537 intervals, B54 and incorporation alternatives remain.

The English comparison now binds fixed-rate Option I at 66:71–79 and 67:1–3,
under heading 65:49. The earlier page90 comparison belongs to Option II.
Historical packets remain immutable, and new output explicitly carries the
correction. Identical quoted reduction words do not make the wrong option
authority valid. The German/English discrepancy remains unresolved. English
equally-and-ratably wording is not imported as an adjudicated German rule.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept bounded engineering package | Three complete supplied readings, actual definition dependency and corrected comparison survive real and installed consumers; prior meanings equal | Source/meaning mutations, exact omissions, wrong-option substitution, excluded guarantor and downstream mutations pass | Supplied readings have no independent adjudication | Execute the reviewed original-coupon-anchor repair, then continue source obligations | Legal correctness, covenant compliance, statutory priority or recovery |

The isolated omissions restore these exact nonspace characters to unknown;
other meanings and outside unknown coverage remain equal:

| Omitted meaning | Characters |
|---|---:|
{chr(10).join(omissions)}

Removing only the debt definition retains pledge words and all earlier meanings,
keeps all raw dependencies equal, and exposes both the unresolved typed edge
and missing target in Q1, Q2 and all three Q2 subquestions. This is an observed
change in question evidence; unchanged UNKNOWN labels alone were insufficient.
Q1/Q2 remain UNKNOWN, Q3 PARTIAL and mode ASSISTED. Actual covenant compliance,
priority, recovery and independent legal acceptance are not established.

Admission 001 passed 47 controls in {suites['basf-pledge-admission-001']['wall_seconds']:.3f} seconds;
smoke 001 passed two controls in {suites['basf-pledge-smoke-001']['wall_seconds']:.3f} seconds. These retain
their historical methods before the reviewed scheduling changes. The remaining
23 focused controls passed in {suites['basf-pledge-001']['wall_seconds']:.3f} seconds. Consumer 001 passed in
{exercises[0]['wall_seconds']:.3f} seconds with {exercises[0]['evidence_payload_bytes']:,} payload bytes. Installed 014
passed nine cases in all three stages in {exercises[1]['wall_seconds']:.3f} seconds, with
{exercises[1]['evidence_payload_bytes']:,} payload bytes. The respective 20-MB/200-MB limits and
one-MiB metadata reserves passed. Full question/meaning identities agree.
The aggregate passed 599 controls in {suites['successor-013']['wall_seconds']:.3f} seconds. Passing suites
have zero failures, errors or skips and unchanged pre-run methods.

Receipts {phase_text} are current, valid, completed engineering PASS.
R4 passed {r4['test_counts']['tests']} checks in {r4['wall_seconds']:.3f} seconds under its 4,500-second bound.
R8 equals final attribution. R0's primary criterion is PASS; R1–R8 remain
PARTIAL, eight capability groups are unfinished and program_complete is false.
Test totals and receipt currentness do not establish legal completion.

Baseline commit: {BASELINE}. The execution index retains actual commands,
source/method identities, environment, CPU mode, limits, wall times and results.
GPU devices were intentionally hidden; retained offline inputs were used.
No new downloads, network or model calls were made. These deterministic controls
provide no stochastic ranking. Aggregate and phase manifests disclose Hypothesis.

Post-run review: supplied meanings can be preserved perfectly and still be
legally wrong. Independent qualified reading and adjudication remain necessary.
Contrary source authority, a lost qualification or unsupported question evidence
would reopen the bounded result. B54, incorporation and bilingual interpretation
remain unresolved. No fundamental third-party package limitation is established.

Continue directly to {NEXT}, after committing this comparator and recording
its final admission. The reproduced 30-August/February mismatch is a local
schedule/reference-validator defect. That next repair preserves historical
versions and requires independently listed dates and exact overlap fractions.
Its pass will not supply real-instrument conventions or actual entitlement.
'''
    (PACKAGE/'RESULT.md').write_text(result)
    heading='# Completed status/negative-pledge validation, 10 October 2026'
    summary=f'''{heading}

Worktree `.worktrees/bond-gap-closure`, branch `feature/prospectus-evidence-master`,
baseline `{BASELINE}`. Three complete German status/pledge/definition readings
join twenty earlier supplied meanings. Six raw references and six scalar maps
remain equal. The typed definition edge and its actual missing-target effect
pass, and installed output carries the corrected English Option I citation.
The bilingual interpretation discrepancy remains open.

Admission 47, smoke 2, remaining controls 23, consumer 001, installed 014 and
aggregate 599 pass. All nine installed cases agree fresh, relocated and restored.
Receipts {phase_text} are current engineering PASS; R4 took
{r4['wall_seconds']:.3f} seconds for {r4['test_counts']['tests']} checks. The final execution index verifies
consumer/installed manifests, method currentness and actual phase results.
No validation remains active at this checkpoint. The evidence index is
`basf-status-pledge/execution-manifest.json`; see its result note for scope.

Q1/Q2 remain UNKNOWN, Q3 PARTIAL, ASSISTED. Fifteen markers, 537 construction
intervals, B54 and incorporation alternatives remain. R1–R8 stay PARTIAL and
independent acceptance is NOT_ESTABLISHED. No actual covenant compliance,
statutory priority, recovery or broad legal completion follows from preservation.

Next executable design: `{NEXT}`. Commit the completed comparator, verify its
identities and admit the original-anchor repair, then continue. Do not repeat
passing checks merely because the full program is partial. No routine
checkpoint requires approval. Keep work in this prospectus worktree; main's
separate legal-interpretation work remains untouched.
'''
    for name in ('RESET.md','RESULT.md','NEXT-PROGRAM.md','EXECUTION.md'):
        path=BASE/name
        old=path.read_text()
        assert not old.startswith(heading)
        path.write_text(summary+'\n'+old)
    save(PACKAGE/'closure-status.json',status)
    progress=read(PACKAGE/'phase-progress.json')
    assert progress['active'] is None and progress['remaining']==[] and progress['status']=='ENGINEERING_VALIDATION_COMPLETE'
    record=dict(version='basf-pledge-execution-index.v1',recorded_at=datetime.now(timezone.utc).isoformat(),
        provenance='Post-run index; linked manifests retain actual pre-run identities and commands',baseline_git_commit=BASELINE,
        plan=identity(ROOT/PLAN),question='Preserve complete selected status, negative pledge, debt definition and dependency through real and installed consumers',
        comparator='Twenty-meaning amount/holder consumer 001 and installed 013; six raw references and six scalar maps',
        environment=dict(python=sys.executable,version=sys.version,CUDA_VISIBLE_DEVICES='-1',cpu_gpu='CPU; GPU intentionally hidden; no probe',network='Retained offline inputs; no new network/model calls'),
        random_seeds='N/A deterministic controls; aggregate/phase manifests disclose Hypothesis',
        data_version=dict(graph_sha256=packet['graph_sha256'],construction_sha256=packet['construction_sha256'],packet=identity(PACKAGE/'review.json'),images=packet['images']),
        suites=suites,exercises=exercises,consumer_outer_command=['timeout','1260','.venv/bin/python','-m','scripts.prospectus_closure_basf_status_pledge'],
        phases=phases,final_status=identity(PACKAGE/'closure-status.json'),next_phase=identity(BASE/'next-phase.json'),
        attribution=dict(final=identity(BASE/'final-attribution.json'),R8=identity(r8),json_equal=True),
        documents=[identity(p) for p in [PACKAGE/'RESULT.md',PACKAGE/'SOURCE-REVIEW.md',PACKAGE/'OPTION-COMPARISON-CORRECTION.md',*(BASE/n for n in ('RESET.md','RESULT.md','NEXT-PROGRAM.md','EXECUTION.md'))]],
        decision='PASS for bounded engineering validation',program_complete=False,unfinished_capability_groups=8,external_acceptance='NOT_ESTABLISHED',
        next_plan=identity(ROOT/NEXT),next_plan_status='Reviewed design; final execution admission pending committed comparator')
    save(PACKAGE/'execution-manifest.json',record)
    print(json.dumps(dict(status=record['decision'],phases=phase_text,verified_exercise_files=[r['files_verified'] for r in exercises],manifest=str((PACKAGE/'execution-manifest.json').relative_to(ROOT)))))

if __name__=='__main__':
    main()
