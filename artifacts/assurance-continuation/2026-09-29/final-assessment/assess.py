"""Downstream assessment; retains failed orchestration and resource outcomes."""
import sys
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import run_assurance_continuation as r
from assurance_continuation_checks import documents, GRANT, baseline
from assurance_successor_audit import journal_receipt
from legalmath.interpretation.assurance.grants import GrantedAllowance

work=r.OUT/'final-assessment/attempt-02'
work.mkdir(exist_ok=False)
started=time.monotonic();before=r.regression_inputs();state=r.read(r.OUT/'state.json')
reviewed=r.read(r.OUT/'reviewed-implementation.json')
plan=r.ROOT/'docs/plans/assurance-continuation-final-assessment.md'
manifest={'status':'RUNNING','started_at':r.now(),
    'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'argv':[sys.executable,*sys.argv], 'script_sha256':r.sha(__file__),
    'python':str(r.PYTHON),'cpu_only':True,'seed':'N/A: deterministic assessment',
    'inputs':before,'plan':r.relative(plan),'plan_sha256':r.sha(plan),'commands':[]}
r.save(work/'manifest.json',manifest)
try:
    if any(r.sha(r.ROOT/p)!=h for p,h in reviewed['inputs'].items()):
        raise RuntimeError('Reviewed source changed')
    for phase,attempts in state['phases'].items():
        for ref in attempts:
            if r.sha(r.ROOT/ref['path'])!=ref['sha256']:raise RuntimeError('Changed phase manifest')
            m=r.read(r.ROOT/ref['path'])
            if any(r.sha(r.ROOT/p)!=h for p,h in m['outputs'].items()):raise RuntimeError('Changed phase evidence')
    if GrantedAllowance(GRANT).verify()['used']!=500:raise RuntimeError('Unexpected allowance usage')
    _,live_journal=journal_receipt(r.OUT/'C6/attempt-02/scoped/model/journal.json')
    if any(a['status']=='RESERVED' for a in live_journal['actions']):raise RuntimeError('Live worker remains active')
    manifest['baseline_check']=baseline(work/'baseline-check')
    def run(argv,directory,label,**kwargs):
        result=r.command(argv,directory,label,**kwargs)
        manifest['commands'].append(result)
        r.save(work/'manifest.json',manifest)
        return result
    manifest['documents']=documents(work,run)
    run([str(r.PYTHON),'-m','pytest','-q','--junitxml='+str(work/'full-regression.xml')],
        work,'full-regression',timeout=3600)
    tree=ET.parse(work/'full-regression.xml').getroot()
    counts={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    manifest['regression']=counts
    if not counts['tests'] or any(counts[k] for k in ('failures','errors','skipped')):raise RuntimeError(str(counts))
    after=r.regression_inputs()
    manifest['input_changes']={p:{'before':before.get(p),'after':after.get(p)} for p in set(before)|set(after) if before.get(p)!=after.get(p)}
    if manifest['input_changes']:raise RuntimeError('Final-assessment inputs changed during verification')
    manifest['status']='PASSED_ASSESSMENT_WITH_LIVE_AND_CAPACITY_QUALIFICATIONS'
except BaseException as exc:
    manifest.update(status='FAILED',error=type(exc).__name__,details=str(exc)[:6000])
manifest.update(finished_at=r.now(),elapsed_seconds=round(time.monotonic()-started,3),
                historical_study_complete=False,legal_correctness='NOT_ESTABLISHED')
manifest['outputs']={r.relative(p):r.sha(p) for p in sorted(work.rglob('*')) if p.is_file() and p.name!='manifest.json'}
r.save(work/'manifest.json',manifest)
print(manifest['status']);print(manifest.get('regression'));print(manifest.get('details',''))
if manifest['status']=='FAILED':raise SystemExit(1)
