"""Summarize checked execution evidence without promoting unfinished studies."""
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import run_assurance_continuation as r
from assurance_continuation_checks import GRANT, OLD
from assurance_successor_audit import journal_receipt
from legalmath.interpretation.assurance.grants import GrantedAllowance
from pypdf import PdfReader

OUT=ROOT/'artifacts/assurance-continuation/2026-09-29'
ASSESS=OUT/'final-assessment/attempt-04'
started=time.monotonic()


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path):return str(Path(path).relative_to(ROOT))
def ref(path):return {'path':rel(path),'sha256':sha(path)}
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


assessment=read(ASSESS/'manifest.json')
if assessment['status']!='PASSED_ISOLATED_ASSESSMENT_WITH_LIVE_AND_CAPACITY_QUALIFICATIONS':
    raise RuntimeError('Final isolated assessment has not passed')
assert not assessment['input_changes']
assert all(sha(ASSESS/p)==h for p,h in assessment['outputs'].items())
assert all(assessment['regression'][k]==0 for k in ('failures','errors','skipped'))
isolation=read(OUT/'final-assessment/isolation-repair/manifest.json')
assert sha(OUT/'final-assessment/isolation-repair/manifest.json')==assessment['isolation_manifest_sha256']
with ZipFile(OUT/'final-assessment/isolation-repair/tested-inputs.zip') as archive:
    assert set(archive.namelist())==set(isolation['inputs'])
    assert all(hashlib.sha256(archive.read(p)).hexdigest()==h for p,h in isolation['inputs'].items())

grant=GrantedAllowance(GRANT).verify()
assert grant['used']==grant['maximum']==500
state=read(OUT/'state.json')
phases={}
for name,attempts in state['phases'].items():
    phases[name]=[]
    for item in attempts:
        assert sha(ROOT/item['path'])==item['sha256']
        m=read(ROOT/item['path'])
        assert all(sha(ROOT/p)==h for p,h in m['outputs'].items())
        phases[name].append({'manifest':item,'status':m['status'],'details':m.get('details')})
assert all(phases['C'+str(i)][-1]['status']=='PASSED' for i in range(6))
assert phases['C6'][-1]['status']=='FAILED' and not phases.get('C7')

live=read(OUT/'C6/attempt-02/result.json');scoped=live['new_scoped_result']
_,journal=journal_receipt(OUT/'C6/attempt-02/scoped/model/journal.json')
assert not any(a['status']=='RESERVED' for a in journal['actions'])
attempts=[a for b in scoped['batches'] for a in b['attempts']]
reference_reports=list((OUT/'C6/attempt-02/scoped/model').glob('action-*/source-references/validation.json'))
assert len(reference_reports)==36
assert all(read(p)['status']=='REFERENCE_INTEGRITY_CHECKED' for p in reference_reports)
reconciliations=[b['reconciliation'] for b in scoped['batches'] if b.get('reconciliation')]
disputes=sum(len(b['disputes']) for b in reconciliations)
assert live['combined_pairs_with_two_perspectives']==165 and len(live['remaining_pairs'])==60
assert disputes==42
live_summary={
    'grant':grant,'new_reservations_this_continuation':37,'last_attempt_new_reservations':live['new_calls'],
    'completed_response_reuses':9,'returned_responses':len(attempts),
    'response_statuses':dict(Counter(a['status'] for a in attempts)),
    'provider_stream_interruptions':1,'source_reference_resolution_count':len(reference_reports),
    'required_ucits_pairs':225,'prior_pairs_with_two_validated_perspectives':48,
    'combined_pairs_with_two_validated_perspectives':165,'remaining_pair_count':60,
    'remaining_pairs':live['remaining_pairs'],'continuation_selected_pairs':177,
    'continuation_pairs_with_two_validated_perspectives':scoped['pairs_with_two_validated_proposals'],
    'continuation_pairs_with_four_dimensions_assessed':scoped['pairs_with_four_dimensions_assessed'],
    'batch_reconciliation_statuses':dict(Counter(b['reconciliation']['status'] if b.get('reconciliation')
         else 'NO_RECONCILIATION' for b in scoped['batches'])),
    'retained_disputes':disputes,'status':scoped['status'],'stopped':scoped['stopped'],
    'raw_evidence':ref(OUT/'C6/attempt-02/result.json')}

qualification=read(OUT/'retained-reading-qualification/attempt-02/result.json')
assert len(qualification['rows'])==9 and qualification['runtime_cases_executed']==0
capacity=read(OUT/'split-capacity/result.json')
assert capacity['result']['execution_complete'] is False
arithmetic=read(OUT/'C4/attempt-03/result.json')
tasks=[]
for task in read(OLD/'unfamiliar-study/result.json')['tasks']:
    row={'task_id':task['task_id'],'whole_ensemble_investigation_complete':False,'arms':{}}
    for arm in ('ensemble','single'):
        budget=read(OLD/'unfamiliar-study'/task['task_id']/(arm+'-allowance.json'))
        row['arms'][arm]={'consumed_local_reservations':len(budget['reservations']),
            'maximum':budget['maximum'],
            'qualification':'Local slots are nonrefundable and may include an action stopped before global dispatch.'}
    tasks.append(row)
residual=read(OUT/'C5/attempt-03/result.json')
current=r.regression_inputs()
expected=assessment['inputs']
differences={p:{'tested':expected.get(p),'workspace':current.get(p)}
    for p in sorted(set(current)|set(expected)) if expected.get(p)!=current.get(p)}
write(OUT/'workspace-differences.json',{'at':r.now(),'snapshot':assessment['snapshot'],
     'scope':'Material application/test/script/manuscript inputs; generated reviews excluded.',
     'differences':differences,'live_workspace_verified':not differences})
documents={name:{**ref(ASSESS/'documents'/name),'pages':len(PdfReader(ASSESS/'documents'/name).pages)}
    for name in ('monograph.pdf','technical-companion.pdf','process-guide.pdf')}
report={
    'schema':'legalmath.assurance-continuation-assessment.v1','at':r.now(),
    'status':'ENGINEERING_SNAPSHOT_VERIFIED_LIVE_STUDY_INCOMPLETE',
    'master_C0_through_C7_complete':False,'master_C7_executed':False,
    'historical_study_complete':False,'completed_whole_ensemble_investigations':0,
    'legal_correctness':'NOT_ESTABLISHED','unknown_future_legal_generalization':'NOT_ESTABLISHED',
    'release_eligible':False,'human_quality_evidence':False,
    'baseline_commit':assessment['commit'],'phases':phases,
    'assessment':ref(ASSESS/'manifest.json'),'regression':assessment['regression'],
    'tested_input_archive':ref(OUT/'final-assessment/isolation-repair/tested-inputs.zip'),
    'tested_input_count':len(isolation['inputs']),
    'workspace_differences':ref(OUT/'workspace-differences.json'),
    'live_workspace_verified':not differences,
    'live':live_summary,'tasks':tasks,
    'arithmetic':{'evidence':ref(OUT/'C4/attempt-03/result.json'),
        'formal_lowering':arithmetic['machine_summary']['formal_lowering'],
        'qualified_product_cases_executed':arithmetic['machine_summary']['executed_target_cases'],
        'separate_conditional_backend_cases':arithmetic['conditional_backend_cases'],
        'dropped_operand_mutation':arithmetic['mutation_witness'],
        'scope':'Ordered exact integer and tagged-missing addition; original source premises retained.'},
    'retained_ucits_qualification':{'evidence':ref(OUT/'retained-reading-qualification/attempt-02/result.json'),
        'readings':9,'encoded_date_profiles_unsupported':8,'unencoded':1,'runtime_cases_executed':0},
    'split_capacity':{'evidence':ref(OUT/'split-capacity/result.json'),
        'synthetic_only':True,'source_units_retained':263,'concerns_retained':263,
        'final_wire_bytes':capacity['request_sizes'][-1]['wire_bytes'],
        'configured_limit_bytes':200000,'live_calls':0,'whole_source_check_completed':False},
    'authority_questions':residual['authority_questions'],
    'prospective':{'current_method_matches_frozen_window':False,
        'original_evidence':ref(OUT/'C5/attempt-03/result.json'),
        'qualification':'Development results are not eligible observations for the original frozen method.'},
    'documents':documents,'preservation':read(ASSESS/'manuscript-preservation.json'),
    'next_plan':ref(ROOT/'docs/implementation/assurance-continuation/next-phase-plan.md'),
    'finalizer':{'argv':[sys.executable,*sys.argv],'script_sha256':sha(__file__),
                 'cpu_only':True,'new_live_calls':0,'elapsed_seconds':round(time.monotonic()-started,3)}}
write(OUT/'final-report.json',report)
write(OUT/'assessed-next-phase-plan.json',{
    'at':r.now(),'final_report':ref(OUT/'final-report.json'),
    'plan':report['next_plan'],'implemented_phases':['C0','C1','C2','C3','C4','C5'],
    'master_C6_receipt':'FAILED_PRESERVED','master_C7_receipt':'NOT_EXECUTED',
    'separate_final_assessment':report['assessment'],
    'live_authorized_remaining':0,'next_offline_work':['D0','D1','D2','D3','D4'],
    'next_live_work':'D5_REQUIRES_AUTHORIZATION_AND_ELIGIBLE_ORIGINAL_ISSUES',
    'later_prospective_work':'D6_REQUIRES_NEW_FROZEN_METHOD_WINDOW',
    'no_old_attempt_or_issue_reset':True,'historical_study_complete':False,
    'legal_correctness':'NOT_ESTABLISHED'})
raw_next=OUT/'next-phase-plan-master-history.json'
if not raw_next.exists():
    raw_next.write_bytes((OUT/'next-phase-plan.json').read_bytes())
write(OUT/'next-phase-plan.json',{
    'at':r.now(),'status':'ASSESSED_CONTINUATION_REQUIRES_REVIEWED_NEXT_PROGRAM',
    'raw_master_refresh_preserved':ref(raw_next),
    'assessed_next_plan':ref(OUT/'assessed-next-phase-plan.json'),
    'next_phase':'D0','next_action':'Use the measured next-phase plan; preserve the verified snapshot and original issue histories.',
    'do_not_retry_old_master_past_phase_limits':True,
    'live_authorized_remaining':0,'historical_study_complete':False,
    'legal_correctness':'NOT_ESTABLISHED'})
print(json.dumps({k:report[k] for k in ('status','regression','tested_input_count','live_workspace_verified')},indent=2))
print('workspace differences:',len(differences))
