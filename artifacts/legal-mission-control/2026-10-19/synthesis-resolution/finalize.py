"""Aggregate actual passing replays; never manufacture a successful checkpoint."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
from scripts.legal_integration_synthesis_resolution import ROOT, WORK, QUESTIONS, IMPLEMENTATION, REVIEW
from scripts.legal_mission_execution import read, ref, verify, require
from legalmath.interpretation.assurance.phased.evidence_store import save_exact

RESULTS = WORK/'validation-2'
implementation = {p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)}
tests = read(ROOT/RESULTS/'tests.json')
require(tests['verdict']=='PASS' and tests['exit_code']==0 and tests['provider_calls']==0,
    'Focused checks did not pass')
require(tests['implementation']==implementation, 'Tests used different implementation')
for pointer in [*tests['tests'].values(),tests['stdout'],tests['stderr']]: verify(ROOT,pointer)
reports = {q:read(ROOT/RESULTS/('replay-'+q+'.json')) for q in QUESTIONS}
roots = dict(p10=85,evidence=86,p14=8,gatecoin=4)
levels = dict(p10=5,evidence=4,p14=0,gatecoin=0)
protected = reports['p10']['protected']
review = ref(ROOT,WORK/'completion-review.md')
for q,r in reports.items():
    require(r['verdict']=='PASS' and r['provider_calls']==0 and r['legal_acceptance'] is False
        and r['roots']==roots[q] and len(r['completed'])==levels[q]
        and len(r['boundaries'])==1 and r['boundaries'][0]['missing_count']>0,
        'Incomplete actual production replay '+q)
    require(r['implementation']==implementation and r['protected']==protected
        and r['completion_review']==review and r['plan']==ref(ROOT,REVIEW),
        'Replay used different sources, authority or review '+q)
    for pointer in (r['details'],r['result']): verify(ROOT,pointer)
    require(not (ROOT/RESULTS/('replay-'+q+'-failure.json')).exists(), 'Replay has unsettled failure '+q)
for path,pointer in protected.items():
    require(ref(ROOT,path)==pointer, 'Replay changed live state or authority '+path)
baseline = read(ROOT/WORK/'baseline.json')
checkpoint_refs = [ref(ROOT,RESULTS/('replay-'+q+'.json')) for q in QUESTIONS]
aggregate = dict(verdict='PASS', production_replay=True, provider_calls=0, ledger_unchanged=True,
    implementation=implementation, protected=protected,
    questions={q:ref(ROOT,RESULTS/('replay-'+q+'.json')) for q in QUESTIONS},
    legal_acceptance=False)
save_exact(ROOT/RESULTS/'replay.json',aggregate)
evidence = [ref(ROOT,RESULTS/'tests.json'),ref(ROOT,RESULTS/'replay.json'),*checkpoint_refs,
    ref(ROOT,WORK/'checkpoints.json'),review,ref(ROOT,WORK/'replay.py'),ref(ROOT,WORK/'validate.py'),
    ref(ROOT,WORK/'finalize.py'),ref(ROOT,WORK/'frontier-configured-p10-1-contracts.json'),
    ref(ROOT,WORK/'frontier-configured-evidence-1-contracts.json')]
result = dict(verdict='PASS',production_replay=True,provider_calls=0,ledger_unchanged=True,
    legal_acceptance=False,implementation=implementation,evidence=evidence,
    git_commit=baseline['git_commit'],plan=ref(ROOT,REVIEW),command=[sys.executable,*sys.argv],
    environment='.venv-context',gpu='Intentionally hidden with CUDA_VISIBLE_DEVICES=-1',
    seeds='N/A: deterministic engineering checks',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    decision='Register the reviewed same-master repair; live provider capacity and legal acceptance remain open.')
save_exact(ROOT/WORK/'local-result.json',result)
print(__import__('json').dumps(dict(verdict='PASS',provider_calls=0,questions=list(reports),
    result=str(WORK/'local-result.json'))))
