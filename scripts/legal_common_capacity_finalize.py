"""Seal reviewed local capacity evidence and the exact fixed deployment manifest."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import difflib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
STAGE = WORK/'staging'
os.environ['CUDA_VISIBLE_DEVICES']='-1'


def read(p): return json.loads(p.read_text())
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2)+'\n')
def ref(p): return dict(path=str(p.relative_to(ROOT)),sha256=sha256(p.read_bytes()).hexdigest())


def prepare():
    baseline=read(WORK/'baseline-files.json')
    for path in (ROOT/'scripts').glob('legal_common_capacity_*.py'):
        shutil.copy2(path,STAGE/'scripts'/path.name)
    plan='docs/plans/legal-integration-master-2026-10-13.md'
    (STAGE/plan).parent.mkdir(parents=True,exist_ok=True)
    (STAGE/plan).write_text((ROOT/plan).read_text()+(WORK/'master-amendment.md').read_text())
    paths=[]
    for folder in ('src','scripts','tests'):
        for path in (STAGE/folder).rglob('*.py'):
            name=str(path.relative_to(STAGE))
            if baseline.get(name)!=sha256(path.read_bytes()).hexdigest():
                owned_helper = name.startswith('scripts/legal_common_capacity_') and (ROOT/name).read_bytes()==path.read_bytes()
                if name in baseline and not owned_helper and sha256((ROOT/name).read_bytes()).hexdigest()!=baseline[name]:
                    raise ValueError('Unrelated production edit: '+name)
                paths.append(name)
    paths += [str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('legal_common_capacity_*.py')]
    paths=sorted(set(paths))
    save(WORK/'implementation-files.json',paths)
    diff=[]
    for name in paths+[plan]:
        before=(ROOT/name).read_text().splitlines(True) if (ROOT/name).exists() else []
        diff.extend(difflib.unified_diff(before,(STAGE/name).read_text().splitlines(True),fromfile=name,tofile='reviewed/'+name))
    (WORK/'source.diff').write_text(''.join(diff))
    return dict(files=len(paths),provider_calls=0)


def seal():
    report=read(WORK/'test-run.json')
    replay=read(WORK/'production-replay.json')
    assert report['returncode']==0 and replay['verdict']=='PASS' and replay['provider_calls']==0
    tests=ET.parse(WORK/'tests.xml').getroot()
    suites=list(tests) if tests.tag=='testsuites' else [tests]
    totals={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','errors','failures','skipped')}
    assert totals['tests']>=173 and totals['failures']==totals['errors']==0
    sys.path[:0]=[str(STAGE/'src'),str(STAGE)]
    from legalmath.interpretation.assurance.phased.capacity_policy import STAGES,NATIVE,PROFILE
    from dataclasses import asdict
    inventory=dict(profile=PROFILE,model_stages={k:asdict(v) for k,v in STAGES.items()},
        native_stages=sorted(NATIVE),routing='BoundDispatch.call and phased.execute; native complete-input checks',
        limits='Task-specific input bounds retained; stage output policies measured at transport and validation',
        limitation='Atomic coupled graphs and bridges may remain too large; source qualification and legal acceptance are separate')
    save(WORK/'stage-inventory.json',inventory)
    manifest=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        created_at_utc=datetime.now(timezone.utc).isoformat(),environment='.venv-context; isolated staging',
        cpu_mode=report['cpu_mode'],gpu='Intentionally hidden; not used',random_seeds='N/A: deterministic controls and retained replay',
        test_run=ref(WORK/'test-run.json'),test_totals=totals,wall_seconds=report['wall_seconds'],
        commands=[report['command'],['.venv-context/bin/python','scripts/legal_common_capacity_replay.py']],
        data=[ref(WORK/'replay-checkpoint.json'),ref(WORK/'baseline-replay-checkpoint.json')],
        plan=ref(ROOT/'docs/plans/legal-common-capacity-interface-2026-10-20.md'),
        result_path=str((WORK/'local-result.json').relative_to(ROOT)),provider_calls=0)
    save(WORK/'run-manifest.json',manifest)
    evidence=[ref(WORK/name) for name in ('test-run.json','tests.stdout','tests.stderr','tests.xml',
        'production-replay.json','stage-inventory.json','source.diff','review.md','run-manifest.json','implementation-files.json')]
    if (WORK/'registration-probe.json').exists():
        assert read(WORK/'registration-probe.json')['verdict']=='PASS'
        evidence.append(ref(WORK/'registration-probe.json'))
    save(WORK/'local-result.json',dict(verdict='PASS',provider_calls=0,legal_acceptance=False,
        tests=totals,model_stages=len(STAGES),native_stages=len(NATIVE),evidence=evidence,
        limitations=['Atomic fixed context may not fit','No live legal or tool-benefit promotion from local tests',
            'Adoption requires authenticated predecessor settlement and unchanged reviewed files']))
    paths=read(WORK/'implementation-files.json')+['docs/plans/legal-integration-master-2026-10-13.md']
    old=ROOT/'artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry'
    writes=[dict(target=name,before=ref(ROOT/name) if (ROOT/name).exists() else None,
        replacement=ref(STAGE/name)) for name in paths]
    save(WORK/'deployment-manifest.json',dict(profile='common-capacity-deployment.v1',
        deadline_utc='2026-10-20T18:55:16+00:00',provider_calls_added=0,
        predecessor_program=ref(ROOT/'docs/implementation/legal-mission-control/integration-master.json'),
        predecessor_worker=read(old/'execution/worker.json')['process'],
        evidence=[ref(WORK/'local-result.json'),*evidence,manifest['plan']],writes=writes))
    return dict(verdict='PASS',tests=totals,files=len(writes),provider_calls=0)


def checkpoint():
    path=ROOT/'docs/implementation/legal-mission-control/mission.json'
    with path.with_name('mission.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        value=read(path)
        identity='common-capacity-isolated-validation-2026-10-20'
        if any(r['id']==identity for r in value['history']): return dict(already_recorded=True)
        reason=('Common capacity implementation reviewed and locally validated in isolation. '
            'Complete the authenticated candidate retry, then checked adoption registers the same master '
            'and continues missing original work. Successful answers and attempts stay retained; no deadline/call reset.')
        value['next_task_reason']=reason
        value['history'].append(dict(id=identity,task_id='product-contribution',kind='product_evaluation',
            outcome='no_advance',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            decision='Local capacity implementation complete; adoption pending predecessor settlement; legal acceptance unchanged.',
            next_task='product-contribution',next_task_reason=reason,
            result_evidence=[ref(WORK/'local-result.json'),ref(WORK/'deployment-manifest.json')]))
        save(path,value)
    return dict(recorded=True,provider_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','seal','checkpoint'])
    args=parser.parse_args()
    print(json.dumps(dict(prepare=prepare,seal=seal,checkpoint=checkpoint)[args.action](),indent=2))
